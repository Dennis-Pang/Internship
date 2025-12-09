"""AI-powered voice chatbot with personality analysis and long-term memory."""
import argparse
import json
import random
import threading
import time as time_module
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import time
import numpy as np
import pandas as pd
import torch
import requests

from modules.config import (
    DEFAULT_SPEAKER,
    DEFAULT_HISTORY_WINDOW,
    AUDIO_FILE,
    GREETING_MESSAGES,
    SPEECH_EMOTION_WEIGHT,
    TEXT_EMOTION_WEIGHT,
    DEFAULT_MAX_CONTEXT_SIZE,
    USE_PIPER_TTS,
    logger,
    OLLAMA_MODEL,
    MAX_PARALLEL_WORKERS,
    STATUS_IDLE,
    STATUS_RECORDING,
    STATUS_TRANSCRIBING,
    STATUS_GENERATING,
)
from modules.audio import record_audio, select_input_device, cleanup_audio_file, TTSEngine, PiperTTSEngine
from modules.database import init_db, store_personality_traits
from modules.llm import chat
from modules.memory import (
    append_chat_to_cache,
    format_short_term_memory,
    flush_cache_to_disk,
    ensure_memobase_user,
    fetch_memobase_context,
    prepare_recent_chats,
    string_to_uuid,
)
from modules.personality import predict_personality, load_personality_model
from modules.audio import load_whisper_pipeline, transcribe_audio
from modules.emotion import (
    load_speech_emotion_model, predict_speech_emotion,
    load_text_emotion_model, predict_text_emotion,
    TEXT_EMOTION_LABELS
)
from modules.timing import timing, timing_context, clear_timings, print_timings, _record_timing


# Thread pool for background HTTP notifications (avoid creating threads repeatedly)
_http_notification_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="http-notifier")


@dataclass
class ConversationState:
    """Conversation state for a speaker."""
    history: List[Dict[str, str]] = field(default_factory=list)
    greeting_played: bool = False


@dataclass
class ApplicationState:
    """Global application state."""
    current_speaker: str = DEFAULT_SPEAKER
    preferences: Dict[str, Any] = field(default_factory=dict)
    history_window_size: int = DEFAULT_HISTORY_WINDOW
    whisper_pipeline: Any = None
    selected_device_index: Optional[int] = None
    debug_mode: bool = False
    conversation_states: Dict[str, ConversationState] = field(default_factory=dict)
    speech_emotion_weight: float = SPEECH_EMOTION_WEIGHT
    text_emotion_weight: float = TEXT_EMOTION_WEIGHT
    streaming_tts: bool = False

    def get_conversation_state(self, speaker_key: str) -> ConversationState:
        """Get or create conversation state for a speaker.

        Args:
            speaker_key: Speaker identifier.

        Returns:
            ConversationState for the speaker.
        """
        if speaker_key not in self.conversation_states:
            self.conversation_states[speaker_key] = ConversationState()
        return self.conversation_states[speaker_key]


def say_greeting(tts_engine: TTSEngine, speaker: str) -> None:
    """Say greeting message.

    Args:
        tts_engine: TTS engine instance
        speaker: Current speaker name
    """
    greeting = (
        f"Hello {speaker}. {random.choice(GREETING_MESSAGES)}"
        if speaker
        else f"Sorry, I couldn't recognize you. {random.choice(GREETING_MESSAGES)}"
    )
    tts_engine.say(greeting)


def warm_up_tts(tts_engine: TTSEngine) -> None:
    """Warm up TTS to avoid first-round cold start latency."""
    try:
        # Piper: Skip warm-up in some environments due to ONNX Runtime teardown issues
        if isinstance(tts_engine, PiperTTSEngine):
            # In some environments ONNX Runtime warm-up triggers malloc errors, skip for stability
            logger.info("Skipping Piper TTS warm-up to avoid potential ONNX/CUDA teardown issues")
            return

        # pyttsx3: Reduce volume and do a short streaming playback to initialize driver/threads
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
        logger.debug(f"TTS warm-up skipped: {exc}")


def warm_up_whisper(pipe: Any) -> None:
    """Run a short silent inference to eliminate first-load and graph compilation overhead."""
    try:
        silent = np.zeros(1600, dtype=np.float32)  # 0.1s @16k
        pipe({"array": silent, "sampling_rate": 16000})
    except Exception as exc:
        logger.debug(f"Whisper warm-up skipped: {exc}")


def warm_up_llm() -> None:
    """Make a minimal call to Ollama to avoid first-round TTFT cold start."""
    try:
        from modules.llm import client

        client.chat.completions.create(
            messages=[{"role": "user", "content": "ping"}],
            model=OLLAMA_MODEL,
            stream=False,
            max_tokens=1,
        )
    except Exception as exc:
        logger.debug(f"LLM warm-up skipped: {exc}")


@timing("transcription")
def transcribe_audio_file(audio_file: str, whisper_pipeline: Any) -> str:
    """Transcribe audio file to text.

    Args:
        audio_file: Path to audio file
        whisper_pipeline: Whisper pipeline instance

    Returns:
        Transcribed text

    Raises:
        ValueError: If transcription is empty
    """
    transcription = transcribe_audio(audio_file, whisper_pipeline)
    text = transcription.strip()

    if not text:
        raise ValueError("Transcription is empty")

    return text


@timing("personality_analysis")
def analyze_personality(text: str) -> pd.DataFrame:
    """Analyze personality from text.

    Args:
        text: Input text

    Returns:
        DataFrame with personality scores
    """
    predictions = predict_personality(text)
    return pd.DataFrame({
        "r": predictions,
        "theta": ["Extraversion", "Neuroticism", "Agreeableness", "Conscientiousness", "Openness"]
    })


@timing("speech2emotion_analysis")
def analyze_speech_emotion(audio_file: str, return_logits: bool = False) -> Dict[str, float]:
    """Analyze emotion from speech audio.

    Args:
        audio_file: Path to audio file
        return_logits: If True, return logits instead of probabilities

    Returns:
        Dictionary with emotion logits or probabilities
    """
    try:
        return predict_speech_emotion(audio_file, return_logits=return_logits)
    except Exception as e:
        logger.error(f"Speech emotion analysis failed: {e}")
        if return_logits:
            return {label: 0.0 for label in TEXT_EMOTION_LABELS}
        else:
            uniform = 1.0 / len(TEXT_EMOTION_LABELS)
            return {label: uniform for label in TEXT_EMOTION_LABELS}


@timing("text2emotion_analysis")
def analyze_text_emotion(text: str, return_logits: bool = False) -> Dict[str, float]:
    """Analyze emotion from text content.

    Args:
        text: Input text
        return_logits: If True, return logits instead of probabilities

    Returns:
        Dictionary with emotion logits or probabilities
    """
    try:
        return predict_text_emotion(text, return_logits=return_logits)
    except Exception as e:
        logger.error(f"Text emotion analysis failed: {e}")
        if return_logits:
            return {label: 0.0 for label in TEXT_EMOTION_LABELS}
        else:
            uniform = 1.0 / len(TEXT_EMOTION_LABELS)
            return {label: uniform for label in TEXT_EMOTION_LABELS}


def fuse_emotions(
    speech_emotion: Dict[str, float],
    text_emotion: Dict[str, float],
    speech_weight: float,
    text_weight: float,
) -> Dict[str, float]:
    """Fuse speech and text emotions using probability averaging: p = λ * p_speech + (1-λ) * p_text

    Args:
        speech_emotion: Speech emotion logits
        text_emotion: Text emotion logits
        speech_weight: Weight for speech emotion (0.0-1.0)
        text_weight: Weight for text emotion (0.0-1.0)

    Returns:
        Fused emotion probabilities (normalized, sum=1.0)
    """
    # Normalize weights
    total_weight = speech_weight + text_weight
    if total_weight == 0:
        # If both weights are 0, return uniform distribution
        uniform = 1.0 / len(TEXT_EMOTION_LABELS)
        return {label: uniform for label in TEXT_EMOTION_LABELS}

    lambda_speech = speech_weight / total_weight
    lambda_text = text_weight / total_weight

    # Convert logits to probabilities via softmax
    speech_logits_array = np.array([speech_emotion[label] for label in TEXT_EMOTION_LABELS])
    speech_exp = np.exp(speech_logits_array - np.max(speech_logits_array))
    speech_probs = speech_exp / np.sum(speech_exp)

    text_logits_array = np.array([text_emotion[label] for label in TEXT_EMOTION_LABELS])
    text_exp = np.exp(text_logits_array - np.max(text_logits_array))
    text_probs = text_exp / np.sum(text_exp)

    # Weighted average
    fused_probs = lambda_speech * speech_probs + lambda_text * text_probs

    return {TEXT_EMOTION_LABELS[i]: float(fused_probs[i]) for i in range(len(TEXT_EMOTION_LABELS))}


def log_emotion_scores(speech_emotion: Dict[str, float], text_emotion: Dict[str, float]) -> None:
    """Log speech/text emotion scores using the standard logger format."""
    if not speech_emotion and not text_emotion:
        return

    def fmt(value: Optional[float]) -> str:
        return f"{value:+.3f}" if isinstance(value, (int, float)) else "N/A"

    logger.info("Emotion analysis (speech vs text logits):")
    for label in TEXT_EMOTION_LABELS:
        speech_val = speech_emotion.get(label)
        text_val = text_emotion.get(label)
        if speech_val is None and text_val is None:
            continue
        logger.info("  %-14s speech=%s | text=%s", f"{label}:", fmt(speech_val), fmt(text_val))


def fetch_memory_context_wrapper(
    current_speaker: str,
    history: List[Dict[str, str]],
) -> str:
    """Fetch MemoBase context for parallel execution.

    Args:
        current_speaker: Current speaker name
        history: Conversation history

    Returns:
        MemoBase context string (empty string if error)
    """
    from modules.timing import _record_timing
    import time

    fetch_start = time.perf_counter()

    try:
        user_uuid = string_to_uuid(current_speaker)
        ensure_memobase_user(user_uuid)

        # Build messages for context retrieval
        messages = history.copy()
        chats_for_context = prepare_recent_chats(messages)

        context_text = fetch_memobase_context(
            user_uuid,
            DEFAULT_MAX_CONTEXT_SIZE,
            chats=chats_for_context,
        )

        _record_timing("llm_memory_fetch", time.perf_counter() - fetch_start)
        return context_text or ""

    except Exception as exc:
        logger.error(f"Failed to fetch MemoBase context for {current_speaker}: {exc}")
        _record_timing("llm_memory_fetch", time.perf_counter() - fetch_start)
        return ""


def build_prompt_context(
    text: str,
    personality_df: pd.DataFrame,
    speech_emotion: Dict[str, float],
    text_emotion: Dict[str, float],
    history: List[Dict[str, str]],
    preferences: Dict[str, Any],
    history_window_size: int,
) -> List[Dict[str, str]]:
    """Build chat prompt with context.

    Args:
        text: User input text
        personality_df: Personality analysis dataframe
        speech_emotion: Speech-based emotion probabilities/logits
        text_emotion: Text-based emotion probabilities/logits
        history: Conversation history
        preferences: User preferences
        history_window_size: Number of conversation rounds to include

    Returns:
        List of chat messages
    """
    # Extract recent history
    recent_history = history[-2 * history_window_size:] if history_window_size > 0 else history

    # Format contexts
    personality_traits = ", ".join([f"{row['theta']}: {row['r']:.2f}" for _, row in personality_df.iterrows()])
    personality_context = f"user's personality: {personality_traits}"
    preferences_context = json.dumps(preferences) if preferences else "None."
    memory_context = format_short_term_memory(recent_history)

    # Format emotion context for both modalities
    def _format_emotions(name: str, data: Dict[str, float]) -> str:
        if not data:
            return f"{name}: unavailable"
        ordered = ", ".join(
            [f"{label}: {data[label]:.2f}" for label in sorted(data.keys())]
        )
        return f"{name}: {ordered}"

    speech_context = _format_emotions("speech emotion", speech_emotion)
    text_context = _format_emotions("text emotion", text_emotion)
    emotion_context = f"user's detected emotions => {speech_context}; {text_context}"

    # Build system prompt
    system_prompt = "\n\n".join([
        (
            "You are Hackcelerate, a helpful healthcare assistant. "
            "Use the provided memory, personality, emotion, and preference context to craft concise, empathetic replies. "
            "Never repeat or expose these context blocks verbatim; respond as a natural assistant speaking directly to the user."
        ),
        memory_context,
        f"--# USER PERSONALITY TRAITS #--\n{personality_context}\n--# END OF PERSONALITY TRAITS #--",
        f"--# USER EMOTIONAL STATE #--\n{emotion_context}\n--# END OF EMOTIONAL STATE #--",
        f"--# USER PREFERENCES #--\nKnown user preferences:\n{preferences_context}\n--# END OF PREFERENCES #--",
    ])

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]


def get_llm_response(
    chat_messages: List[Dict[str, str]],
    speaker: str,
    debug_mode: bool = False,
    memobase_context: Optional[str] = None,
    on_chunk: Optional[Callable[[str, bool], None]] = None,
) -> tuple:
    """Get LLM response.

    Note: Timing is handled inside llm.chat() for detailed TTFT metrics.

    Args:
        chat_messages: Chat messages
        speaker: Current speaker
        debug_mode: Enable verbose prompt logging
        memobase_context: Pre-fetched MemoBase context (optional)
        on_chunk: Optional callback fired for every streamed token with (text_delta, is_final)

    Returns:
        Tuple of (response_content, user_uuid)
    """
    start = time.perf_counter()
    response_content, user_uuid = chat(
        chat_messages,
        current_speaker=speaker,
        close_session=False,
        use_users=bool(speaker),
        debug=debug_mode,
        memobase_context=memobase_context,
        on_chunk=on_chunk,
    )
    _record_timing('llm_total', time.perf_counter() - start)

    if not response_content:
        raise ValueError("LLM response empty")

    return response_content, user_uuid


def save_conversation_data(speaker: str, predictions: List[float], user_uuid: str,
                          user_text: str, response: str, db_session,
                          speech_emotion: Optional[dict] = None, text_emotion: Optional[dict] = None) -> None:
    """Save conversation data to database.

    Args:
        speaker: Current speaker
        predictions: Personality predictions
        user_uuid: User UUID
        user_text: User input text
        response: Assistant response
        db_session: Database session
        speech_emotion: Speech emotion probabilities
        text_emotion: Text emotion probabilities
    """
    # Store personality traits
    store_personality_traits(speaker, predictions, db_session)

    # Cache conversation (with dummy durations for now)
    if user_uuid and response:
        append_chat_to_cache(
            user_uuid,
            speaker or DEFAULT_SPEAKER,
            user_text,
            response,
            0.0,  # speech_duration - handled separately
            0.0,  # llm_duration - handled separately
            speech_emotion=speech_emotion,
            text_emotion=text_emotion,
        )


@timing("response_tts")
def say_response(tts_engine: TTSEngine, response: str):
    """Speak the response.

    Args:
        tts_engine: TTS engine
        response: Response text
    """
    tts_engine.say(response)


def build_streaming_tts_callback(
    tts_engine: TTSEngine,
) -> Callable[[str, bool], None]:
    """Build callback for true streaming TTS with token-level processing.

    Directly passes LLM tokens to PiperTTS, which handles sentence splitting
    and streaming synthesis internally.
    """
    def on_chunk(text_delta: str, is_final: bool):
        """Pass token directly to streaming TTS engine."""
        if text_delta:
            # Send token directly to TTS - PiperTTS handles sentence splitting internally
            tts_engine.stream_text(text_delta)

    return on_chunk


def notify_dashboard_update(user_id: str, backend_url: str = "http://localhost:5000") -> None:
    """Notify backend API that dashboard data should be updated.

    Args:
        user_id: User identifier
        backend_url: Backend API base URL
    """
    try:
        response = requests.post(
            f"{backend_url}/api/notify/{user_id}",
            timeout=1.0  # Quick timeout, don't block chatbot
        )
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Dashboard notified: {result.get('status')} ({result.get('clients', 0)} clients)")
        else:
            logger.warning(f"Dashboard notification failed: {response.status_code}")
    except requests.exceptions.Timeout:
        logger.debug("Dashboard notification timeout (backend may not be running)")
    except requests.exceptions.ConnectionError:
        logger.debug("Dashboard notification failed (backend not reachable)")
    except Exception as e:
        logger.debug(f"Dashboard notification error: {e}")


def _fire_and_forget_post(url: str, payload: dict, timeout: float, fail_log: str) -> None:
    """Send POST request in background thread to avoid blocking the hot path."""
    def _send():
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            if response.status_code != 200:
                logger.debug(f"{fail_log}: {response.status_code}")
        except requests.exceptions.Timeout:
            logger.debug(f"{fail_log}: timeout")
        except requests.exceptions.ConnectionError:
            logger.debug(f"{fail_log}: connection error")
        except Exception as exc:
            logger.debug(f"{fail_log}: {exc}")

    # Use thread pool instead of creating new threads
    _http_notification_pool.submit(_send)


def push_user_input(user_id: str, text: str, backend_url: str = "http://localhost:5000") -> None:
    """Push user input text to backend API immediately after transcription.

    Args:
        user_id: User identifier
        text: User input text
        backend_url: Backend API base URL
    """
    from datetime import datetime

    _fire_and_forget_post(
        f"{backend_url}/api/user-input/{user_id}",
        {"text": text, "timestamp": datetime.now().isoformat()},
        timeout=0.5,
        fail_log="User input push failed",
    )


def push_streaming_chunk(user_id: str, chunk: str, is_final: bool, backend_url: str = "http://localhost:5000") -> None:
    """Push streaming text chunk to backend API for real-time frontend updates.

    Args:
        user_id: User identifier
        chunk: Text chunk to push
        is_final: Whether this is the final chunk
        backend_url: Backend API base URL
    """
    _fire_and_forget_post(
        f"{backend_url}/api/stream-chunk/{user_id}",
        {"chunk": chunk, "is_final": is_final},
        timeout=0.5,
        fail_log="Stream chunk push failed",
    )


def push_status(user_id: str, status: str, backend_url: str = "http://localhost:5000") -> None:
    """Push processing status to backend API for real-time frontend updates.

    Args:
        user_id: User identifier
        status: Status message (e.g., "recording", "transcribing", "generating", "idle")
        backend_url: Backend API base URL
    """
    _fire_and_forget_post(
        f"{backend_url}/api/status/{user_id}",
        {"status": status},
        timeout=0.5,
        fail_log="Status push failed",
    )


def process_audio(
    audio_file: str,
    tts_engine: TTSEngine,
    db_session,
    app_state: ApplicationState,
) -> None:
    """Process audio file through the full pipeline.

    Args:
        audio_file: Path to audio file.
        tts_engine: TTS engine instance.
        db_session: Database session.
        app_state: Application state object.
    """
    # Clear previous session timing
    clear_timings()

    # Get conversation state
    speaker_key = app_state.current_speaker or "anonymous"
    state = app_state.get_conversation_state(speaker_key)

    # Say greeting only once per speaker/session
    if not state.greeting_played:
        say_greeting(tts_engine, app_state.current_speaker)
        state.greeting_played = True

    try:
        # Start measuring total processing time (from audio input to TTS output)
        total_processing_start = time.perf_counter()

        # Push "transcribing" status before starting transcription
        push_status(app_state.current_speaker or DEFAULT_SPEAKER, STATUS_TRANSCRIBING)

        # Step 1: Start Whisper transcription AND speech emotion analysis in parallel
        # This overlaps the two most time-consuming tasks
        parallel_audio_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
            # Both work on the same audio file simultaneously
            transcription_future = executor.submit(
                transcribe_audio_file, audio_file, app_state.whisper_pipeline
            )
            speech_emotion_future = executor.submit(
                analyze_speech_emotion, audio_file, return_logits=False
            )

            # Wait for transcription to complete (needed for text-based analysis)
            text = transcription_future.result()
            print("Q:", text)

            # Push user input to frontend immediately after transcription
            push_user_input(app_state.current_speaker or DEFAULT_SPEAKER, text)

            # Build messages for memory retrieval (needs current text)
            temp_messages = state.history.copy()
            temp_messages.append({"role": "user", "content": text})

            # Start text-based analysis, personality, AND memory retrieval in parallel
            text_emotion_future = executor.submit(
                analyze_text_emotion, text, return_logits=False
            )
            personality_future = executor.submit(analyze_personality, text)
            memory_future = executor.submit(
                fetch_memory_context_wrapper, app_state.current_speaker, temp_messages
            )

            # Wait for all results
            speech_emotion = speech_emotion_future.result()
            text_emotion = text_emotion_future.result()
            personality_df = personality_future.result()
            memobase_context = memory_future.result()

        # Record parallel block wall clock time
        _record_timing("[Parallel] Audio processing (Whisper + speech2emotion + text2emotion + personality + memory)",
                      time.perf_counter() - parallel_audio_start)

        # Step 3: Provide both emotion sources to the prompt (fusion disabled)
        log_emotion_scores(speech_emotion, text_emotion)

        # Build context and get LLM response
        chat_messages = build_prompt_context(
            text,
            personality_df,
            speech_emotion,
            text_emotion,
            state.history,
            app_state.preferences,
            app_state.history_window_size,
        )

        # Push "generating" status before starting LLM generation
        push_status(app_state.current_speaker or DEFAULT_SPEAKER, STATUS_GENERATING)

        # Start streaming TTS (GPU-accelerated background synthesis)
        tts_engine.start_streaming()

        # Create combined callback for frontend push + streaming TTS
        tts_callback = build_streaming_tts_callback(tts_engine)

        def on_chunk_callback(chunk: str, is_final: bool):
            """Callback fired for each streaming chunk from LLM."""
            # Push to frontend dashboard
            push_streaming_chunk(
                app_state.current_speaker or DEFAULT_SPEAKER,
                chunk,
                is_final
            )
            # Feed to streaming TTS (synthesizes and plays in background)
            tts_callback(chunk, is_final)

        response_content, user_uuid = get_llm_response(
            chat_messages,
            app_state.current_speaker,
            app_state.debug_mode,
            memobase_context=memobase_context,
            on_chunk=on_chunk_callback,
        )

        # Save to database
        predictions = personality_df["r"].tolist()
        save_conversation_data(
            app_state.current_speaker,
            predictions,
            user_uuid,
            text,
            response_content,
            db_session,
            speech_emotion=speech_emotion,
            text_emotion=text_emotion,
        )
        # Persist updated memory cache immediately so the dashboard backend sees new data
        flush_cache_to_disk()

        # Notify dashboard backend to push updates to frontend (push-based, no polling)
        notify_dashboard_update(app_state.current_speaker or DEFAULT_SPEAKER)

        # Update conversation history
        state.history.append({"role": "user", "content": text})
        state.history.append({"role": "assistant", "content": response_content})

        if app_state.history_window_size > 0:
            max_items = 2 * app_state.history_window_size
            if len(state.history) > max_items:
                del state.history[:-max_items]

        # Wait for streaming TTS to finish and get first playback time
        first_playback_time = tts_engine.finish_streaming(wait=True)

        # Calculate user-perceived latency (audio input end → first TTS playback)
        if first_playback_time:
            user_perceived_latency = first_playback_time - total_processing_start
            print(f"\n[User-perceived latency: {user_perceived_latency:.4f}s (audio end → first TTS playback)]")
            _record_timing('🎯 USER PERCEIVED LATENCY', user_perceived_latency)
        else:
            # Fallback: LLM generation complete time
            total_processing_time = time.perf_counter() - total_processing_start
            print(f"\n[Processing completed in {total_processing_time:.4f}s]")
            _record_timing('Total processing (fallback)', total_processing_time)

        # Print full timing summary
        print_timings("Audio Processing Performance")

        # Push "idle" status after processing is complete
        push_status(app_state.current_speaker or DEFAULT_SPEAKER, STATUS_IDLE)

    except Exception as e:
        logger.error(f"Audio processing failed: {e}")
        # Push "idle" status on error
        push_status(app_state.current_speaker or DEFAULT_SPEAKER, STATUS_IDLE)

    finally:
        # Cleanup
        cleanup_audio_file(audio_file)


def print_startup_timings(timings: Dict[str, float]) -> None:
    """Print initialization timing summary at startup.

    Args:
        timings: Dictionary of initialization step names and durations
    """
    print("\n" + "=" * 60)
    print("System Initialization")
    print("=" * 60)
    print(f"{'Component':<40} {'Duration':>10}")
    print("-" * 60)

    total = 0.0
    for name, duration in timings.items():
        print(f"{name:<40} {duration:>9.4f}s")

        # Only add to total if not a parallel sub-task (sub-tasks start with "  ├─")
        if not name.startswith("  ├─"):
            total += duration

    print("-" * 60)
    print(f"{'TOTAL INITIALIZATION TIME':<40} {total:>9.4f}s")
    print("=" * 60)
    print()


def main():
    """Main program loop."""
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

    # Initialize application state
    app_state = ApplicationState(
        history_window_size=max(0, args.history_window),
        debug_mode=args.debug,
        speech_emotion_weight=args.speech_emotion_weight,
        text_emotion_weight=args.text_emotion_weight,
    )

    # Track initialization timings
    init_timings = {}

    # Sequential: Database initialization (fast)
    start = time_module.perf_counter()
    Session = init_db()
    db_session = Session()
    init_timings["Database initialization"] = time_module.perf_counter() - start

    # Sequential: TTS engine initialization (fast)
    start = time_module.perf_counter()
    if USE_PIPER_TTS:
        # CRITICAL: Initialize PyTorch CUDA context before ONNX Runtime
        # This prevents malloc() errors when both libraries try to manage CUDA
        if torch.cuda.is_available():
            logger.info("Pre-initializing PyTorch CUDA context for ONNX Runtime compatibility")
            _ = torch.zeros(1, device='cuda')  # Force CUDA context creation
            torch.cuda.synchronize()  # Ensure context is fully initialized

        logger.info("Initializing GPU-accelerated Piper TTS engine")
        tts_engine = PiperTTSEngine()
        # Check if initialization succeeded, fallback to pyttsx3 if needed
        if tts_engine.engine is None:
            logger.warning("Piper TTS initialization failed, falling back to pyttsx3")
            tts_engine = TTSEngine()
    else:
        logger.info("Using pyttsx3 TTS engine")
        tts_engine = TTSEngine()
    init_timings["TTS engine initialization"] = time_module.perf_counter() - start

    # Warm up TTS to remove first-round TTS cold start
    start = time_module.perf_counter()
    warm_up_tts(tts_engine)
    init_timings["TTS warm-up"] = time_module.perf_counter() - start

    # Sequential: Load personality model (has issues with parallel loading)
    start = time_module.perf_counter()
    try:
        load_personality_model()
        init_timings["Big5 personality model & tokenizer"] = time_module.perf_counter() - start
    except Exception as e:
        init_timings["Big5 personality model & tokenizer (FAILED)"] = time_module.perf_counter() - start
        logger.error(f"Failed to load personality model: {e}")
        logger.warning("Continuing without personality analysis")

    # Parallel: Load emotion models only (speech2emotion + text2emotion)
    parallel_tasks = []
    parallel_task_timings = {}

    def speech_emotion_task():
        """Load speech emotion model."""
        task_start = time_module.perf_counter()
        try:
            load_speech_emotion_model()
            return True, time_module.perf_counter() - task_start
        except Exception as e:
            logger.error(f"Failed to load speech emotion model: {e}")
            logger.warning("Continuing without speech emotion analysis")
            return False, time_module.perf_counter() - task_start

    def text_emotion_task():
        """Load text emotion model."""
        task_start = time_module.perf_counter()
        try:
            load_text_emotion_model()
            return True, time_module.perf_counter() - task_start
        except Exception as e:
            logger.error(f"Failed to load text emotion model: {e}")
            logger.warning("Continuing without text emotion analysis")
            return False, time_module.perf_counter() - task_start

    # Conditionally load emotion models based on weights
    if app_state.speech_emotion_weight > 0:
        parallel_tasks.append(("Speech2Emotion recognition model", speech_emotion_task))

    if app_state.text_emotion_weight > 0:
        parallel_tasks.append(("Text2Emotion DeBERTa model", text_emotion_task))

    # Execute parallel tasks and measure wall clock time
    if parallel_tasks:
        parallel_block_start = time_module.perf_counter()
        with ThreadPoolExecutor(max_workers=len(parallel_tasks)) as executor:
            futures = {name: executor.submit(task) for name, task in parallel_tasks}

            # Wait for all tasks to complete and collect individual timings
            for name, future in futures.items():
                try:
                    success, duration = future.result()
                    if success:
                        parallel_task_timings[name] = duration
                    else:
                        parallel_task_timings[f"{name} (FAILED)"] = duration
                except Exception as e:
                    parallel_task_timings[f"{name} (FAILED)"] = 0.0
                    logger.error(f"Failed to load {name}: {e}")

        # Record actual wall clock time for the parallel block
        parallel_block_duration = time_module.perf_counter() - parallel_block_start
        init_timings["[Parallel] Emotion models (speech + text)"] = parallel_block_duration

        # Also store individual timings for detailed view
        for name, duration in parallel_task_timings.items():
            init_timings[f"  ├─ {name}"] = duration

    # Sequential: Load Whisper pipeline (large model, avoid GPU conflicts)
    use_gpu = torch.cuda.is_available()
    start = time_module.perf_counter()
    try:
        logger.info(f"Loading Whisper pipeline (GPU: {use_gpu})...")
        app_state.whisper_pipeline = load_whisper_pipeline(use_gpu)
        logger.info("Whisper pipeline loaded successfully")
        init_timings["Whisper speech-to-text model"] = time_module.perf_counter() - start
    except Exception as e:
        init_timings["Whisper speech-to-text model (FAILED)"] = time_module.perf_counter() - start
        logger.error(f"Failed to load Whisper pipeline: {e}")
        return

    # Warm up Whisper to eliminate first-round inference overhead
    start = time_module.perf_counter()
    warm_up_whisper(app_state.whisper_pipeline)
    init_timings["Whisper warm-up"] = time_module.perf_counter() - start

    # Sequential: Test Ollama connection (fast check)
    start = time_module.perf_counter()
    try:
        from modules.llm import client
        # Simple test to see if Ollama is responsive
        models = client.models.list()
        init_timings["Ollama LLM connection check"] = time_module.perf_counter() - start
    except Exception as e:
        init_timings["Ollama LLM connection check (FAILED)"] = time_module.perf_counter() - start
        logger.warning(f"Ollama connection test failed: {e}")

    # Warm up LLM to reduce first-token latency
    start = time_module.perf_counter()
    warm_up_llm()
    init_timings["Ollama LLM warm-up"] = time_module.perf_counter() - start

    # Print startup timings
    print_startup_timings(init_timings)

    # Main interactive loop
    print("Type 'r' to record, 'q' to quit.")

    try:
        while True:
            command = input().strip().lower()

            if command == 'q':
                break

            if command == 'r':
                # Select device only on first recording
                if app_state.selected_device_index is None:
                    print("\nFirst time setup - please select your audio input device:")
                    app_state.selected_device_index = select_input_device()
                    print(f"Device selected. This will be used for all recordings in this session.\n")

                # Push "recording" status before recording starts
                push_status(DEFAULT_SPEAKER, STATUS_RECORDING)

                # Use the remembered device for recording
                success = record_audio(device_index=app_state.selected_device_index)

                if success:
                    app_state.current_speaker = DEFAULT_SPEAKER
                    process_audio(AUDIO_FILE, tts_engine, db_session, app_state)
                else:
                    # Recording failed, reset to idle
                    push_status(DEFAULT_SPEAKER, STATUS_IDLE)

    except KeyboardInterrupt:
        pass

    finally:
        # Flush memory cache to disk before exit
        flush_cache_to_disk()

        # Cleanup resources
        tts_engine.cleanup()
        db_session.close()

        # Cleanup Whisper pipeline
        if app_state.whisper_pipeline is not None:
            del app_state.whisper_pipeline
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
