"""Interactive voice chatbot entrypoint using the core pipeline."""

# Set environment variables BEFORE heavy imports (avoids ONNX/PyTorch conflicts)
import os
import threading
import argparse
from typing import Any, Optional, Tuple

import torch

from core.config import (
    AUDIO_FILE,
    DEFAULT_HISTORY_WINDOW,
    DEFAULT_SPEAKER,
    OLLAMA_MODEL,
    SPEECH_EMOTION_WEIGHT,
    STATUS_IDLE,
    STATUS_RECORDING,
    TEXT_EMOTION_WEIGHT,
    USE_KOKORO,
    KOKORO_DEVICE,
)
from core.database import init_db
from core.logger import get_logger
from core.memory import flush_cache_to_disk
from core.notifications import get_default_service
from core.performance import PerformanceTracker
from core.pipeline import ApplicationState, AudioProcessingPipeline, AudioProcessor
from audio import (
    TTSEngine,
    KokoroTTSEngine,
    load_whisper_pipeline,
    record_audio,
    select_input_device,
)
from models.emotion import load_speech_emotion_model, load_text_emotion_model
from models.llm import client as llm_client
from models.personality import load_personality_model


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

        tts_engine.say("warm up")

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
    """Initialize dependencies and return pipeline + resources.

    Optimized startup sequence:
    - TTS runs in background thread
    - GPU models load sequentially while TTS loads in parallel
    - Total time: max(TTS, GPU_models) instead of sum
    """
    startup_tracker = PerformanceTracker("Startup")

    # Container for TTS engine (set by background thread or main thread)
    tts_result: dict = {"engine": None, "error": None}
    tts_thread: Optional[threading.Thread] = None

    def _tts_uses_gpu() -> bool:
        if not USE_KOKORO or not torch.cuda.is_available():
            return False
        device = (KOKORO_DEVICE or "").lower()
        if device in {"cpu"}:
            return False
        return True

    def _init_tts_background():
        """Initialize TTS engine (optionally in background for CPU loading)."""
        try:
            if USE_KOKORO:
                logger.info("Initializing Kokoro TTS engine")
                engine = KokoroTTSEngine()
                if engine.model is None or engine.pipeline is None:
                    logger.warning("Kokoro initialization failed, falling back to pyttsx3")
                    engine = TTSEngine()
                tts_result["engine"] = engine
            else:
                logger.info("Using pyttsx3 TTS engine")
                tts_result["engine"] = TTSEngine()
        except Exception as e:
            logger.error(f"TTS initialization failed: {e}")
            tts_result["error"] = e
            tts_result["engine"] = TTSEngine()  # Fallback

    # === PHASE 1: Start TTS in background (CPU-only, no GPU conflict) ===
    if USE_KOKORO and not _tts_uses_gpu():
        with startup_tracker.start("TTS engine initialization (background start)"):
            tts_thread = threading.Thread(target=_init_tts_background, daemon=True)
            tts_thread.start()
            logger.info("Kokoro loading in background thread while GPU models load...")
    else:
        # Non-Kokoro engines are fast, load synchronously
        with startup_tracker.start("TTS engine initialization"):
            _init_tts_background()

    # === PHASE 2: Load GPU models sequentially (while TTS loads in parallel) ===

    # Database (fast)
    with startup_tracker.start("Database initialization"):
        Session = init_db()
        db_session = Session()

    # GPU Models (sequential to avoid VRAM spikes)
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

    # Whisper (large model, keep sequential)
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

    # LLM warm-up (external service, no local GPU usage)
    with startup_tracker.start("Ollama LLM warm-up"):
        warm_up_llm()

    # === PHASE 3: Wait for TTS background thread to complete ===
    if tts_thread is not None:
        with startup_tracker.start("TTS engine initialization (wait for completion)"):
            tts_thread.join()
            if tts_result["error"]:
                logger.warning(f"TTS had error: {tts_result['error']}")

    tts_engine = tts_result["engine"]

    # TTS warm-up (after engine is ready)
    with startup_tracker.start("TTS warm-up"):
        warm_up_tts(tts_engine)

    # Log startup summary
    startup_tracker.log_summary("System Initialization", logger.logger)

    pipeline = AudioProcessingPipeline(app_state, db_session, tts_engine)
    return pipeline, db_session, tts_engine


def interactive_loop(pipeline: AudioProcessingPipeline, app_state: ApplicationState, logger) -> None:
    """Run the interactive record → process loop."""
    notification_service = get_default_service()

    print("Type 'r' to record 5 seconds of audio, 'q' to quit.")

    try:
        while True:
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

            success = record_audio(
                device_index=app_state.selected_device_index,
                duration=5,  # Fixed 5 second recording
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
        streaming_tts=False,
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
