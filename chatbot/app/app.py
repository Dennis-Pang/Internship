"""Interactive voice chatbot entrypoint using the core pipeline."""

# Set environment variables BEFORE heavy imports (avoids ONNX/PyTorch conflicts)
import os

import argparse
from typing import Any, Tuple

import torch

try:
    import keyboard  # type: ignore
    _KEYBOARD_AVAILABLE = True
except Exception:
    keyboard = None  # type: ignore
    _KEYBOARD_AVAILABLE = False

from core.config import (
    AUDIO_FILE,
    DEFAULT_HISTORY_WINDOW,
    DEFAULT_SPEAKER,
    OLLAMA_MODEL,
    SPEECH_EMOTION_WEIGHT,
    STATUS_IDLE,
    STATUS_RECORDING,
    TEXT_EMOTION_WEIGHT,
    USE_NEUTTS,
    USE_PIPER_TTS,
)
from core.database import init_db
from core.logger import get_logger
from core.memory import flush_cache_to_disk
from core.notifications import get_default_service
from core.performance import PerformanceTracker
from core.pipeline import ApplicationState, AudioProcessingPipeline, AudioProcessor
from audio import (
    NeuTTSEngine,
    PiperTTSEngine,
    TTSEngine,
    load_whisper_pipeline,
    record_audio,
    record_audio_hold_to_talk,
    select_input_device,
)
from models.emotion import load_speech_emotion_model, load_text_emotion_model
from models.llm import client as llm_client
from models.personality import load_personality_model


HOLD_KEY = "r"
MAX_HOLD_SECONDS = 30.0


def warm_up_tts(tts_engine: TTSEngine) -> None:
    """Warm up TTS to avoid first-round cold start latency."""
    try:
        engine = getattr(tts_engine, "engine", None)
        if engine is None:
            return

        original_volume = engine.getProperty("volume")
        try:
            engine.setProperty("volume", 0.0)
        except Exception:
            pass

        tts_engine.start_streaming()
        tts_engine.stream_text("warm up")
        tts_engine.finish_streaming(wait=True)

        try:
            engine.setProperty("volume", original_volume)
        except Exception:
            pass
    except Exception as exc:
        get_logger("app").debug(f"TTS warm-up skipped: {exc}")


def warm_up_llm() -> None:
    """Minimal LLM call to reduce first-token latency."""
    try:
        llm_client.chat.completions.create(
            messages=[{"role": "user", "content": "ping"}],
            model=OLLAMA_MODEL,
            stream=False,
            max_tokens=1,
        )
    except Exception as exc:
        get_logger("app").debug(f"LLM warm-up skipped: {exc}")


def initialize_system(app_state: ApplicationState, logger) -> Tuple[AudioProcessingPipeline, Any, Any]:
    """Initialize dependencies and return pipeline + resources."""
    startup_tracker = PerformanceTracker("Startup")

    # Database
    with startup_tracker.start("Database initialization"):
        Session = init_db()
        db_session = Session()

    # TTS
    with startup_tracker.start("TTS engine initialization"):
        if USE_NEUTTS:
            logger.info("Initializing NeuTTS engine (PyTorch-based)")
            tts_engine = NeuTTSEngine()
            if tts_engine.tts is None:
                logger.warning("NeuTTS initialization failed, falling back to pyttsx3")
                tts_engine = TTSEngine()
        elif USE_PIPER_TTS:
            logger.info("Initializing Piper TTS engine")
            tts_engine = PiperTTSEngine()
            if tts_engine.engine is None:
                logger.warning("Piper TTS initialization failed, falling back to pyttsx3")
                tts_engine = TTSEngine()
        else:
            logger.info("Using pyttsx3 TTS engine")
            tts_engine = TTSEngine()

    with startup_tracker.start("TTS warm-up"):
        warm_up_tts(tts_engine)

    # Models
    with startup_tracker.start("Big5 personality model & tokenizer"):
        try:
            load_personality_model()
        except Exception as exc:
            logger.error(f"Failed to load personality model: {exc}")
            logger.warning("Continuing without personality analysis")

    if app_state.speech_emotion_weight > 0:
        with startup_tracker.start("Speech2Emotion recognition model"):
            try:
                load_speech_emotion_model()
            except Exception as exc:
                logger.error(f"Failed to load speech emotion model: {exc}")
                logger.warning("Continuing without speech emotion analysis")

    if app_state.text_emotion_weight > 0:
        with startup_tracker.start("Text2Emotion DeBERTa model"):
            try:
                load_text_emotion_model()
            except Exception as exc:
                logger.error(f"Failed to load text emotion model: {exc}")
                logger.warning("Continuing without text emotion analysis")

    # Whisper
    use_gpu = torch.cuda.is_available()
    with startup_tracker.start("Whisper speech-to-text model"):
        try:
            app_state.whisper_pipeline = load_whisper_pipeline(use_gpu)
            logger.info(f"Whisper pipeline loaded successfully (GPU: {use_gpu})")
        except Exception as exc:
            logger.error(f"Failed to load Whisper pipeline: {exc}")
            raise

    with startup_tracker.start("Whisper warm-up"):
        AudioProcessor(app_state.whisper_pipeline).warm_up_whisper()

    # LLM warm-up
    with startup_tracker.start("Ollama LLM warm-up"):
        warm_up_llm()

    # Log startup summary
    startup_tracker.log_summary("System Initialization", logger.logger)

    pipeline = AudioProcessingPipeline(app_state, db_session, tts_engine)
    return pipeline, db_session, tts_engine


def interactive_loop(pipeline: AudioProcessingPipeline, app_state: ApplicationState, logger) -> None:
    """Run the interactive record → process loop."""
    notification_service = get_default_service()
    hold_mode = _KEYBOARD_AVAILABLE

    if hold_mode:
        print(f"Hold '{HOLD_KEY}' to record (max {int(MAX_HOLD_SECONDS)}s). Release to stop. Press 'q' to quit.")
    else:
        print("keyboard package not installed; fallback to command mode (pip install keyboard for hold-to-talk).")
        print("Type 'r' to record, 'q' to quit.")

    try:
        while True:
            if hold_mode:
                try:
                    event = keyboard.read_event()  # type: ignore[attr-defined]
                except Exception as exc:
                    logger.warning(f"keyboard read failed; falling back to text commands: {exc}")
                    hold_mode = False
                    print("Type 'r' to record, 'q' to quit.")
                    continue

                if event.event_type != "down":
                    continue

                key_name = (event.name or "").lower()
                if key_name == "q":
                    break
                if key_name != HOLD_KEY:
                    continue
            else:
                command = input().strip().lower()
                if command == "q":
                    break
                if command != "r":
                    continue

            if app_state.selected_device_index is None:
                print("\nFirst time setup - select your audio input device:")
                app_state.selected_device_index = select_input_device()
                print("Device selected for this session.\n")

            notification_service.push_status(DEFAULT_SPEAKER, STATUS_RECORDING)

            if hold_mode:
                def _is_holding() -> bool:
                    try:
                        return bool(keyboard.is_pressed(HOLD_KEY))  # type: ignore[attr-defined]
                    except Exception:
                        return False

                success = record_audio_hold_to_talk(
                    is_holding_key=_is_holding,
                    device_index=app_state.selected_device_index,
                    max_duration=MAX_HOLD_SECONDS,
                )
            else:
                success = record_audio(
                    device_index=app_state.selected_device_index,
                    duration=int(MAX_HOLD_SECONDS),
                )

            if not success:
                notification_service.push_status(DEFAULT_SPEAKER, STATUS_IDLE)
                continue

            app_state.current_speaker = DEFAULT_SPEAKER
            try:
                pipeline.process_audio(AUDIO_FILE)
            except Exception as exc:
                logger.error(f"Audio processing failed: {exc}")
                notification_service.push_status(DEFAULT_SPEAKER, STATUS_IDLE)

    except KeyboardInterrupt:
        logger.info("Stopping chatbot...")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audio processing with personality analysis")
    parser.add_argument(
        "--history-window",
        type=int,
        default=DEFAULT_HISTORY_WINDOW,
        help="Number of recent conversation rounds to retain for short-term memory (0 disables).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print the complete prompt payload sent to the LLM each round.",
    )
    parser.add_argument(
        "--speech-emotion-weight",
        type=float,
        default=SPEECH_EMOTION_WEIGHT,
        help=f"Weight for speech-based emotion analysis (0.0-1.0, default: {SPEECH_EMOTION_WEIGHT}).",
    )
    parser.add_argument(
        "--text-emotion-weight",
        type=float,
        default=TEXT_EMOTION_WEIGHT,
        help=f"Weight for text-based emotion analysis (0.0-1.0, default: {TEXT_EMOTION_WEIGHT}).",
    )
    args = parser.parse_args()

    logger = get_logger("app")
    app_state = ApplicationState(
        history_window_size=max(0, args.history_window),
        debug_mode=args.debug,
        speech_emotion_weight=args.speech_emotion_weight,
        text_emotion_weight=args.text_emotion_weight,
    )

    pipeline = None
    db_session = None
    tts_engine = None

    try:
        pipeline, db_session, tts_engine = initialize_system(app_state, logger)
        interactive_loop(pipeline, app_state, logger)
    finally:
        flush_cache_to_disk()
        if tts_engine:
            tts_engine.cleanup()
        if db_session:
            db_session.close()
        if app_state.whisper_pipeline is not None:
            del app_state.whisper_pipeline
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
