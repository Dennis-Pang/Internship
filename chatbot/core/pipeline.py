"""Core pipeline components and analysis helpers."""
from __future__ import annotations

import atexit
import random
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# Shared thread pool executor for parallel operations (avoids creation overhead)
_shared_executor: Optional[ThreadPoolExecutor] = None


def get_shared_executor() -> ThreadPoolExecutor:
    """Get or create shared thread pool executor."""
    global _shared_executor
    if _shared_executor is None:
        _shared_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pipeline")
        atexit.register(_shared_executor.shutdown, wait=False)
    return _shared_executor

from .config import (
    DEFAULT_HISTORY_WINDOW,
    DEFAULT_MAX_CONTEXT_SIZE,
    DEFAULT_SPEAKER,
    GREETING_MESSAGES,
    MAX_PARALLEL_WORKERS,
    SPEECH_EMOTION_WEIGHT,
    STATUS_GENERATING,
    STATUS_IDLE,
    STATUS_TRANSCRIBING,
    TEXT_EMOTION_WEIGHT,
    WHISPER_WARMUP_SAMPLES,
)
from .logger import StructuredLogger, get_logger
from .performance import get_tracker
from .notifications import get_default_service
from .memory import (
    append_chat_to_cache,
    ensure_memobase_user,
    fetch_memobase_context,
    flush_cache_to_disk,
    prepare_recent_chats,
    string_to_uuid,
)
from .database import store_personality_traits
from audio import TTSEngine, cleanup_audio_file, transcribe_audio
from models.emotion import TEXT_EMOTION_LABELS, predict_speech_emotion, predict_text_emotion
from models.emotion.base import get_default_emotion_scores
from models.personality import predict_personality
from models.llm import chat


# ---------- Analysis helpers (used by pipeline and benchmarking scripts) ----------
def analyze_speech_emotion(
    audio_file: str,
    *,
    return_logits: bool = False,
    logger: Optional[StructuredLogger] = None,
) -> Dict[str, float]:
    """Analyze emotion from speech audio."""
    log = logger or get_logger("speech_emotion")
    tracker = get_tracker()
    with tracker.start("speech2emotion_analysis"):
        try:
            return predict_speech_emotion(audio_file, return_logits=return_logits)
        except Exception as exc:
            log.error(f"Speech emotion analysis failed: {exc}")
            return get_default_emotion_scores(return_logits)


def analyze_text_emotion(
    text: str,
    *,
    return_logits: bool = False,
    logger: Optional[StructuredLogger] = None,
) -> Dict[str, float]:
    """Analyze emotion from text content."""
    log = logger or get_logger("text_emotion")
    tracker = get_tracker()
    with tracker.start("text2emotion_analysis"):
        try:
            return predict_text_emotion(text, return_logits=return_logits)
        except Exception as exc:
            log.error(f"Text emotion analysis failed: {exc}")
            return get_default_emotion_scores(return_logits)


def analyze_personality(text: str, logger: Optional[StructuredLogger] = None) -> pd.DataFrame:
    """Analyze personality traits from text."""
    log = logger or get_logger("personality_analysis")
    tracker = get_tracker()
    with tracker.start("personality_analysis"):
        try:
            predictions = predict_personality(text)
            return pd.DataFrame(
                {
                    "r": predictions,
                    "theta": [
                        "Extraversion",
                        "Neuroticism",
                        "Agreeableness",
                        "Conscientiousness",
                        "Openness",
                    ],
                }
            )
        except Exception as exc:
            log.error(f"Personality analysis failed: {exc}")
            return pd.DataFrame({"r": [], "theta": []})


def fuse_emotions(
    speech_emotion: Dict[str, float],
    text_emotion: Dict[str, float],
    speech_weight: float = SPEECH_EMOTION_WEIGHT,
    text_weight: float = TEXT_EMOTION_WEIGHT,
) -> Dict[str, float]:
    """Fuse speech and text emotion probabilities using weighted averaging."""
    total_weight = speech_weight + text_weight
    if total_weight == 0:
        uniform = 1.0 / len(TEXT_EMOTION_LABELS)
        return {label: uniform for label in TEXT_EMOTION_LABELS}

    lambda_speech = speech_weight / total_weight
    lambda_text = text_weight / total_weight

    return {
        label: lambda_speech * speech_emotion.get(label, 0.0) + lambda_text * text_emotion.get(label, 0.0)
        for label in TEXT_EMOTION_LABELS
    }


def log_emotion_scores(
    speech_emotion: Dict[str, float],
    text_emotion: Dict[str, float],
    logger: Optional[StructuredLogger] = None,
) -> None:
    """Log speech/text emotion scores for debugging."""
    if not speech_emotion and not text_emotion:
        return

    log = logger or get_logger("emotion_fusion")

    def fmt(value: Optional[float]) -> str:
        return f"{value:+.3f}" if isinstance(value, (int, float)) else "N/A"

    log.info("Emotion analysis (speech vs text logits):")
    for label in TEXT_EMOTION_LABELS:
        speech_val = speech_emotion.get(label)
        text_val = text_emotion.get(label)
        if speech_val is None and text_val is None:
            continue
        log.info("  %-14s speech=%s | text=%s", f"{label}:", fmt(speech_val), fmt(text_val))


# ---------- State management ----------
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
    streaming_tts: bool = False
    speech_emotion_weight: float = SPEECH_EMOTION_WEIGHT
    text_emotion_weight: float = TEXT_EMOTION_WEIGHT

    def __post_init__(self) -> None:
        self._conversation_states: Dict[str, ConversationState] = {}

    def get_conversation_state(self, speaker_key: str) -> ConversationState:
        """Get or create conversation state for a speaker."""
        if speaker_key not in self._conversation_states:
            self._conversation_states[speaker_key] = ConversationState()
        return self._conversation_states[speaker_key]


class ConversationManager:
    """Manages conversation history and state."""

    def __init__(self, app_state: ApplicationState):
        self.app_state = app_state
        self.logger = get_logger("conversation_manager")

    def get_current_state(self) -> ConversationState:
        speaker_key = self.app_state.current_speaker or "anonymous"
        return self.app_state.get_conversation_state(speaker_key)

    def add_exchange(self, user_text: str, assistant_response: str) -> None:
        state = self.get_current_state()
        state.history.append({"role": "user", "content": user_text})
        state.history.append({"role": "assistant", "content": assistant_response})

        if self.app_state.history_window_size > 0:
            max_items = 2 * self.app_state.history_window_size
            if len(state.history) > max_items:
                state.history = state.history[-max_items:]

        self.logger.debug(f"Added exchange to history. Total messages: {len(state.history)}")

    def get_recent_history(self) -> List[Dict[str, str]]:
        return self.get_current_state().history

    def should_play_greeting(self) -> bool:
        return not self.get_current_state().greeting_played

    def mark_greeting_played(self) -> None:
        self.get_current_state().greeting_played = True


# ---------- Core components ----------
class AudioProcessor:
    """Handles audio transcription and emotion analysis with parallel processing."""

    def __init__(self, whisper_pipeline: Any, notification_service: Any = None):
        self.whisper_pipeline = whisper_pipeline
        self.notification_service = notification_service
        self.performance_tracker = get_tracker()
        self.logger = get_logger("audio_processor")

    def warm_up_whisper(self) -> None:
        """Warm up Whisper pipeline to eliminate first-load overhead."""
        try:
            silent = np.zeros(WHISPER_WARMUP_SAMPLES, dtype=np.float32)
            self.whisper_pipeline({"array": silent, "sampling_rate": 16000})
            self.logger.debug("Whisper warm-up completed")
        except Exception as exc:
            self.logger.debug(f"Whisper warm-up skipped: {exc}")

    def transcribe_audio_file(self, audio_file: str) -> str:
        """Transcribe audio file to text."""
        with self.performance_tracker.start("transcription"):
            transcription = transcribe_audio(audio_file, self.whisper_pipeline)
            text = transcription.strip()
            if not text:
                raise ValueError("Transcription is empty")
            return text

    def analyze_speech_emotion(self, audio_file: str) -> Dict[str, float]:
        """Analyze emotion from speech audio."""
        return analyze_speech_emotion(audio_file, logger=self.logger)

    def process_audio_parallel(self, audio_file: str) -> Dict[str, Any]:
        """Process audio file with parallel transcription and emotion analysis."""
        with self.performance_tracker.start("parallel_audio_processing"):
            executor = get_shared_executor()
            transcription_future = executor.submit(self.transcribe_audio_file, audio_file)
            speech_emotion_future = executor.submit(self.analyze_speech_emotion, audio_file)

            text = transcription_future.result()
            self.logger.info(f"User input: {text}")
            speech_emotion = speech_emotion_future.result()

            return {"text": text, "speech_emotion": speech_emotion}


class TextAnalyzer:
    """Handles text-based analysis including emotion, personality, and memory."""

    def __init__(self, current_speaker: str, conversation_history: List[Dict[str, str]]):
        self.current_speaker = current_speaker
        self.conversation_history = conversation_history
        self.performance_tracker = get_tracker()
        self.logger = get_logger("text_analyzer")

    def fetch_memory_context(self, user_text: str) -> str:
        """Fetch MemoBase context for the current speaker."""
        with self.performance_tracker.start("memory_context_fetch"):
            if not self.current_speaker:
                return ""

            try:
                user_uuid = string_to_uuid(self.current_speaker)
                ensure_memobase_user(user_uuid)

                temp_messages = self.conversation_history.copy()
                temp_messages.append({"role": "user", "content": user_text})
                chats_for_context = prepare_recent_chats(temp_messages)

                context_text = fetch_memobase_context(
                    user_uuid,
                    DEFAULT_MAX_CONTEXT_SIZE,
                    chats=chats_for_context,
                )
                return context_text or ""
            except Exception as exc:
                self.logger.error(f"Failed to fetch MemoBase context: {exc}")
                return ""

    def analyze_text_emotion(self, text: str) -> Dict[str, float]:
        return analyze_text_emotion(text, logger=self.logger)

    def analyze_personality(self, text: str) -> pd.DataFrame:
        return analyze_personality(text, logger=self.logger)

    def analyze_text_parallel(self, text: str) -> Dict[str, Any]:
        """Perform parallel text analysis (emotion, personality, memory)."""
        with self.performance_tracker.start("parallel_text_analysis"):
            executor = get_shared_executor()
            text_emotion_future = executor.submit(self.analyze_text_emotion, text)
            personality_future = executor.submit(self.analyze_personality, text)
            memory_future = executor.submit(self.fetch_memory_context, text)

            text_emotion = text_emotion_future.result()
            personality_df = personality_future.result()
            memory_context = memory_future.result()

            return {
                "text_emotion": text_emotion,
                "personality_df": personality_df,
                "memory_context": memory_context,
            }


class EmotionFusion:
    """Handles fusion of speech and text emotions."""

    def __init__(self, speech_weight: float = 0.5, text_weight: float = 0.5):
        self.speech_weight = speech_weight
        self.text_weight = text_weight
        self.logger = get_logger("emotion_fusion")

    def fuse_emotions(self, speech_emotion: Dict[str, float], text_emotion: Dict[str, float]) -> Dict[str, float]:
        return fuse_emotions(speech_emotion, text_emotion, self.speech_weight, self.text_weight)

    def log_emotion_scores(self, speech_emotion: Dict[str, float], text_emotion: Dict[str, float]) -> None:
        log_emotion_scores(speech_emotion, text_emotion, logger=self.logger)


class LLMResponseGenerator:
    """Handles LLM response generation with streaming TTS."""

    def __init__(self, tts_engine: TTSEngine, debug_mode: bool = False):
        self.tts_engine = tts_engine
        self.debug_mode = debug_mode
        self.performance_tracker = get_tracker()
        self.logger = get_logger("llm_response_generator")
        self.notification_service = get_default_service()

    def build_prompt_context(
        self,
        text: str,
        personality_df: pd.DataFrame,
        fused_emotion: Dict[str, float],
        conversation_history: List[Dict[str, str]],
        preferences: Dict[str, Any],
        history_window_size: int,
    ) -> List[Dict[str, str]]:
        trait_order = ["Extraversion", "Neuroticism", "Agreeableness", "Conscientiousness", "Openness"]
        emotion_order = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

        recent_history = (
            conversation_history[-2 * history_window_size :] if history_window_size > 0 else conversation_history
        )
        conversation_history_filtered = list(recent_history)
        conversation_history_filtered.append({"role": "user", "content": text})

        trait_scores = {row["theta"]: row["r"] for _, row in personality_df.iterrows()}
        personality_parts = []
        for trait in trait_order:
            score = trait_scores.get(trait)
            if score is None:
                personality_parts.append(f"{trait}=N/A")
            else:
                personality_parts.append(f"{trait}={float(score):.2f}")
        personality_context = ", ".join(personality_parts) if personality_parts else "Unavailable."

        if not fused_emotion:
            emotion_context = "Unavailable."
        else:
            emotion_parts = [
                f"{label}={float(fused_emotion.get(label, 0.0)):.2f}" for label in emotion_order
            ]
            emotion_context = ", ".join(emotion_parts)

        if isinstance(preferences, dict) and preferences:
            preferences_parts = [f"{key}={value}" for key, value in preferences.items()]
            preferences_context = ", ".join(preferences_parts)
        else:
            preferences_context = "None."

        conversation_lines = []
        for entry in conversation_history_filtered:
            content = (entry.get("content") or "").strip()
            if not content:
                continue
            role = entry.get("role")
            label = "User" if role == "user" else "Assistant"
            conversation_lines.append(f"{label}: {content}")
        conversation_context = "\n".join(conversation_lines) if conversation_lines else "None."

        prompt_header_lines = [
            "You are Hackcelerate, a health companion who chats naturally with users. You adapt your responses to the moment: sometimes you ask questions, sometimes you share thoughts, sometimes you just listen. When something connects to what you know about the user, you reference it naturally to make the conversation personal.",
            "",
            "INSTRUCTIONS:",
            "- Use EMOTION_LOGITS to adjust emotional tone and USER_PERSONALITY to adjust interaction style",
            "- Reference KNOWN_PREFERENCES directly when relevant (e.g., \"your blood pressure pill,\" \"your weekend mornings\")",
            "- 2-5 sentences, conversational tone, no meta-talk about context/memory/prompts",
            "- User wants help -> offer 1-2 small steps | User is sharing -> respond supportively",
            "- Write ONLY your reply as Assistant, no analysis or commentary",
            "",
            "EXAMPLES:",
            "",
            "Example 1:",
            "KNOWN_PREFERENCES: medication=insulin, struggle=lunch_dose_at_work",
            "User: \"Forgot my insulin again at work\"",
            "Assistant: \"That lunch dose is tricky. Does your work routine vary a lot day to day?\"",
            "",
            "Example 2:",
            "KNOWN_PREFERENCES: goal=walking_habit, milestone=walked_3_days",
            "User: \"Hit 3 days of walking!\"",
            "Assistant: \"Nice! How's your energy feeling? Notice any difference yet?\"",
            "",
            "---",
        ]

        context_section_lines = [
            "CONTEXT:",
            "",
            f"USER_PERSONALITY: {personality_context}",
            "",
            f"EMOTION_LOGITS: {emotion_context}",
            "",
            f"KNOWN_PREFERENCES: {preferences_context}",
            "",
            "CONVERSATION:",
            conversation_context,
        ]

        system_prompt = "\n\n".join(
            [
                "\n".join(prompt_header_lines),
                "\n".join(context_section_lines),
            ]
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

    def build_streaming_tts_callback(self) -> Callable[[str, bool], None]:
        """Build callback for streaming TTS."""
        def on_chunk(text_delta: str, is_final: bool):
            if text_delta:
                self.tts_engine.stream_text(text_delta)

        return on_chunk

    def generate_response(
        self,
        chat_messages: List[Dict[str, str]],
        current_speaker: str,
        memobase_context: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """Generate LLM response with streaming TTS."""
        with self.performance_tracker.start("llm_response_generation"):
            self.tts_engine.start_streaming()
            tts_callback = self.build_streaming_tts_callback()

            def on_chunk_callback(chunk: str, is_final: bool):
                self.notification_service.push_streaming_chunk(
                    current_speaker or DEFAULT_SPEAKER, chunk, is_final
                )
                tts_callback(chunk, is_final)

            response_content, user_uuid = chat(
                chat_messages,
                current_speaker=current_speaker,
                close_session=False,
                use_users=bool(current_speaker),
                debug=self.debug_mode,
                memobase_context=memobase_context,
                on_chunk=on_chunk_callback,
            )

            if not response_content:
                raise ValueError("LLM response empty")

            return response_content, user_uuid

    def finish_streaming(self) -> Optional[float]:
        """Finish streaming TTS and return first playback time."""
        return self.tts_engine.finish_streaming(wait=True)


class DataPersister:
    """Handles data persistence to database and cache."""

    def __init__(self, db_session):
        self.db_session = db_session
        self.notification_service = get_default_service()
        self.logger = get_logger("data_persister")
        self._pending_future: Optional[Future] = None

    def save_conversation_data(
        self,
        speaker: str,
        personality_df: pd.DataFrame,
        user_uuid: str,
        user_text: str,
        response: str,
        speech_emotion: Optional[Dict] = None,
        text_emotion: Optional[Dict] = None,
        fused_emotion: Optional[Dict] = None,
    ) -> None:
        try:
            predictions = personality_df["r"].tolist()
            store_personality_traits(speaker, predictions, self.db_session)

            if user_uuid and response:
                append_chat_to_cache(
                    user_uuid,
                    speaker or "presentation",
                    user_text,
                    response,
                    0.0,
                    0.0,
                    speech_emotion=speech_emotion,
                    text_emotion=text_emotion,
                    fused_emotion=fused_emotion,
                )

            self.logger.debug("Conversation data saved successfully")
        except Exception as exc:
            self.logger.error(f"Failed to save conversation data: {exc}")
            raise

    def flush_and_notify(self, speaker: str) -> None:
        try:
            flush_cache_to_disk()
            self.notification_service.notify_dashboard_update(speaker or "presentation")
            self.logger.debug("Cache flushed and dashboard notified")
        except Exception as exc:
            self.logger.error(f"Failed to flush cache and notify: {exc}")

    def save_and_notify_background(
        self,
        speaker: str,
        personality_df: pd.DataFrame,
        user_uuid: str,
        user_text: str,
        response: str,
        speech_emotion: Optional[Dict] = None,
        text_emotion: Optional[Dict] = None,
        fused_emotion: Optional[Dict] = None,
    ) -> Future:
        """Save conversation data and notify in background thread.

        Returns Future that can be awaited if needed.
        """
        def _persist():
            try:
                self.save_conversation_data(
                    speaker, personality_df, user_uuid, user_text, response,
                    speech_emotion, text_emotion, fused_emotion
                )
                self.flush_and_notify(speaker)
            except Exception as exc:
                self.logger.error(f"Background persistence failed: {exc}")

        executor = get_shared_executor()
        self._pending_future = executor.submit(_persist)
        return self._pending_future

    def wait_for_pending(self, timeout: float = 5.0) -> None:
        """Wait for any pending background persistence to complete."""
        if self._pending_future is not None:
            try:
                self._pending_future.result(timeout=timeout)
            except Exception as exc:
                self.logger.error(f"Pending persistence failed: {exc}")
            finally:
                self._pending_future = None


class AudioProcessingPipeline:
    """Main pipeline coordinating audio processing through all stages."""

    def __init__(self, app_state: ApplicationState, db_session, tts_engine: TTSEngine):
        self.app_state = app_state
        self.db_session = db_session
        self.tts_engine = tts_engine

        self.audio_processor = AudioProcessor(
            whisper_pipeline=app_state.whisper_pipeline,
            notification_service=get_default_service(),
        )
        self.conversation_manager = ConversationManager(app_state)
        self.emotion_fusion = EmotionFusion(
            speech_weight=app_state.speech_emotion_weight,
            text_weight=app_state.text_emotion_weight,
        )
        self.llm_generator = LLMResponseGenerator(
            tts_engine=tts_engine,
            debug_mode=app_state.debug_mode,
        )
        self.data_persister = DataPersister(db_session)

        self.performance_tracker = get_tracker()
        self.logger = get_logger("audio_processing_pipeline")
        self.notification_service = get_default_service()

    def say_greeting(self) -> None:
        if self.conversation_manager.should_play_greeting():
            greeting = (
                f"Hello {self.app_state.current_speaker}. {random.choice(GREETING_MESSAGES)}"
                if self.app_state.current_speaker
                else f"Sorry, I couldn't recognize you. {random.choice(GREETING_MESSAGES)}"
            )
            self.tts_engine.say(greeting)
            self.conversation_manager.mark_greeting_played()

    def process_audio(self, audio_file: str) -> None:
        """Process audio file through the complete pipeline."""
        self.performance_tracker.clear()
        total_processing_start = time.perf_counter()
        self.logger.info("Starting audio processing for %s", audio_file)

        try:
            self.say_greeting()
            self.notification_service.push_status(
                self.app_state.current_speaker or DEFAULT_SPEAKER, STATUS_TRANSCRIBING
            )

            with self.performance_tracker.start("total_processing"):
                audio_results = self.audio_processor.process_audio_parallel(audio_file)
                user_text = audio_results["text"]
                speech_emotion = audio_results["speech_emotion"]

                self.notification_service.push_user_input(
                    self.app_state.current_speaker or DEFAULT_SPEAKER, user_text
                )
                self.logger.info("Transcription complete")

                text_analyzer = TextAnalyzer(
                    self.app_state.current_speaker,
                    self.conversation_manager.get_recent_history(),
                )

                temp_history = self.conversation_manager.get_recent_history() + [
                    {"role": "user", "content": user_text}
                ]
                text_analyzer.conversation_history = temp_history

                text_results = text_analyzer.analyze_text_parallel(user_text)
                text_emotion = text_results["text_emotion"]
                personality_df = text_results["personality_df"]
                memory_context = text_results["memory_context"]
                self.logger.info("Text analysis complete")

                fused_emotion = self.emotion_fusion.fuse_emotions(speech_emotion, text_emotion)
                self.emotion_fusion.log_emotion_scores(speech_emotion, text_emotion)

                self.notification_service.push_status(
                    self.app_state.current_speaker or DEFAULT_SPEAKER, STATUS_GENERATING
                )

                chat_messages = self.llm_generator.build_prompt_context(
                    user_text,
                    personality_df,
                    fused_emotion,
                    self.conversation_manager.get_recent_history(),
                    self.app_state.preferences,
                    self.app_state.history_window_size,
                )

                response_content, user_uuid = self.llm_generator.generate_response(
                    chat_messages,
                    self.app_state.current_speaker,
                    memobase_context=memory_context,
                )

                # Update conversation history immediately (fast, needed for next turn)
                self.conversation_manager.add_exchange(user_text, response_content)

                # Start data persistence in background (runs while TTS finishes)
                self.data_persister.save_and_notify_background(
                    self.app_state.current_speaker,
                    personality_df,
                    user_uuid,
                    user_text,
                    response_content,
                    speech_emotion=speech_emotion,
                    text_emotion=text_emotion,
                    fused_emotion=fused_emotion,
                )

                first_playback_time = self.llm_generator.finish_streaming()
                if first_playback_time:
                    user_perceived_latency = first_playback_time - total_processing_start
                    self.logger.info(
                        "User-perceived latency: %.4fs (audio end → first TTS playback)",
                        user_perceived_latency,
                    )
                    self.performance_tracker.record("🎯 USER PERCEIVED LATENCY", user_perceived_latency)
                else:
                    total_processing_time = time.perf_counter() - total_processing_start
                    self.logger.info("Processing completed in %.4fs", total_processing_time)
                    self.performance_tracker.record("Total processing (fallback)", total_processing_time)

                # Wait for background persistence before logging summary
                self.data_persister.wait_for_pending(timeout=2.0)

                self.performance_tracker.log_summary("Audio Processing Performance", self.logger.logger)
                self.notification_service.push_status(
                    self.app_state.current_speaker or DEFAULT_SPEAKER, STATUS_IDLE
                )
        except Exception as exc:
            self.logger.error(f"Audio processing failed: {exc}")
            self.notification_service.push_status(
                self.app_state.current_speaker or DEFAULT_SPEAKER, STATUS_IDLE
            )
            raise
        finally:
            cleanup_audio_file(audio_file)

