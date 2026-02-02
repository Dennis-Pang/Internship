"""Text-to-Speech engines with streaming support."""
import base64
import hashlib
import logging
import os
import threading
import time
from fractions import Fraction
from typing import Optional

import numpy as np
import pyttsx3
import torch
from scipy.signal import resample_poly

from core.config import (
    TTS_RATE,
    TTS_VOLUME,
    KOKORO_REPO_ID,
    KOKORO_LANG,
    KOKORO_VOICE,
    KOKORO_SPEED,
    KOKORO_DEVICE,
    KOKORO_OUTPUT_DEVICE_INDEX,
    KOKORO_OUTPUT_SAMPLE_RATE,
)
from core.notifications import get_default_service

logger = logging.getLogger(__name__)


class TTSEngine:
    """Simple blocking pyttsx3 wrapper (fallback)."""

    def __init__(self):
        self.engine: Optional[pyttsx3.Engine] = None
        self._engine_lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', TTS_RATE)
            self.engine.setProperty('volume', TTS_VOLUME)
            voices = self.engine.getProperty('voices')
            if len(voices) > 1:
                self.engine.setProperty('voice', voices[0].id)
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
            self.engine = None

    def say(self, text: str, user_id: Optional[str] = None) -> tuple[bool, float]:
        if not self.engine:
            return False, 0.0
        try:
            with self._engine_lock:
                self.engine.say(text)
                playback_start = time.perf_counter()
                self.engine.runAndWait()
            return True, playback_start
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return False, 0.0

    def say_streaming(self, text: str, user_id: Optional[str] = None) -> tuple[bool, float]:
        return self.say(text, user_id=user_id)

    def cleanup(self):
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
            self.engine = None


class KokoroTTSEngine:
    """Kokoro TTS engine (non-streaming, high quality)."""

    def __init__(self):
        self.model = None
        self.pipeline = None
        self.voice = KOKORO_VOICE
        self.speed = KOKORO_SPEED
        self.sample_rate = 24000
        self.output_rate = 24000
        self.output_device_index = None
        self._output_rate_override = None
        self._stream_to_frontend = True  # Always push full audio to frontend when user_id is provided
        self._engine_lock = threading.Lock()
        self._pyaudio = None
        self._notification_service = None
        self._init_engine()
        self._load_output_config()

    def _load_output_config(self):
        device_env = (KOKORO_OUTPUT_DEVICE_INDEX or "").strip()
        if device_env:
            try:
                self.output_device_index = int(device_env)
            except ValueError:
                logger.warning("Invalid KOKORO_OUTPUT_DEVICE_INDEX: %s", device_env)
        rate_env = (KOKORO_OUTPUT_SAMPLE_RATE or "").strip()
        if rate_env:
            try:
                self._output_rate_override = int(rate_env)
            except ValueError:
                logger.warning("Invalid KOKORO_OUTPUT_SAMPLE_RATE: %s", rate_env)

    def _resolve_device(self) -> str:
        pref = (KOKORO_DEVICE or "auto").strip().lower()
        if pref == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if pref == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA requested for Kokoro but not available; falling back to CPU.")
            return "cpu"
        return pref

    def _init_engine(self):
        try:
            import pyaudio
            from kokoro import KModel, KPipeline

            self._pyaudio = pyaudio
            device = self._resolve_device()

            # Enforce the configured language and voice
            lang_code = KOKORO_LANG
            voice = self.voice
            if not (voice.startswith("a") or voice.startswith("b")):
                logger.warning("Non-English voice requested (%s); falling back to af_heart.", voice)
                voice = "af_heart"
            self.voice = voice

            self.model = KModel(repo_id=KOKORO_REPO_ID).to(device).eval()
            self.pipeline = KPipeline(
                lang_code=lang_code,
                repo_id=KOKORO_REPO_ID,
                model=self.model,
            )
            logger.info(
                "Kokoro initialized (repo=%s, lang=%s, voice=%s, device=%s)",
                KOKORO_REPO_ID,
                lang_code,
                self.voice,
                device,
            )
        except Exception as e:
            logger.exception(f"Failed to initialize Kokoro TTS: {e}")
            self.model = None
            self.pipeline = None
            self._pyaudio = None

    def _select_output_rate(self, p, device_index: Optional[int]) -> int:
        candidates = []
        if self._output_rate_override:
            candidates.append(self._output_rate_override)
        candidates.extend([self.sample_rate, 48000, 44100, 32000, 24000, 22050, 16000])

        try:
            dev_info = (
                p.get_device_info_by_index(device_index)
                if device_index is not None
                else p.get_default_output_device_info()
            )
            default_rate = int(dev_info.get("defaultSampleRate", 48000))
        except Exception:
            default_rate = 48000

        if default_rate not in candidates:
            candidates.append(default_rate)

        seen = set()
        for rate in candidates:
            if rate in seen:
                continue
            seen.add(rate)
            try:
                p.is_format_supported(
                    rate,
                    output_device=device_index,
                    output_channels=1,
                    output_format=self._pyaudio.paInt16,
                )
                return int(rate)
            except Exception:
                continue

        return int(default_rate)

    def _open_output_stream(self):
        if not self._pyaudio:
            raise RuntimeError("PyAudio is not available.")
        p = self._pyaudio.PyAudio()
        device_index = self.output_device_index
        output_rate = self._select_output_rate(p, device_index)
        try:
            stream = p.open(
                format=self._pyaudio.paInt16,
                channels=1,
                rate=output_rate,
                output=True,
                output_device_index=device_index,
            )
        except Exception:
            if device_index is not None:
                logger.warning(
                    "Output device %s failed at %s Hz; retrying default device.",
                    device_index,
                    output_rate,
                )
                device_index = None
                output_rate = self._select_output_rate(p, device_index)
                stream = p.open(
                    format=self._pyaudio.paInt16,
                    channels=1,
                    rate=output_rate,
                    output=True,
                )
            else:
                raise
        self.output_rate = output_rate
        return p, stream

    def _resample_if_needed(self, audio: np.ndarray) -> np.ndarray:
        if self.output_rate == self.sample_rate:
            return audio
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        ratio = Fraction(int(self.output_rate), int(self.sample_rate)).limit_denominator(1000)
        return resample_poly(audio, ratio.numerator, ratio.denominator)

    def _close_output_stream(self, p, stream):
        try:
            stream.stop_stream()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass
        try:
            p.terminate()
        except Exception:
            pass

    def _synthesize(self, text: str) -> Optional[np.ndarray]:
        if not self.pipeline or not self.model:
            return None
        audio_chunks: list[np.ndarray] = []
        try:
            for result in self.pipeline(text, voice=self.voice, speed=self.speed, model=self.model):
                audio = result.audio
                if audio is None:
                    continue
                if isinstance(audio, torch.Tensor):
                    audio = audio.detach().cpu().float().numpy()
                else:
                    audio = np.asarray(audio, dtype=np.float32)
                audio_chunks.append(audio.reshape(-1))
        except Exception as e:
            logger.error(f"Kokoro synthesis failed: {e}")
            return None
        if not audio_chunks:
            return None
        return np.concatenate(audio_chunks)

    def say(self, text: str, user_id: Optional[str] = None) -> tuple[bool, float]:
        if not self.pipeline or not self.model:
            return False, 0.0
        if self._stream_to_frontend and user_id:
            return self._send_full_audio_to_frontend(user_id, text)
        if not self._pyaudio:
            return False, 0.0
        try:
            with self._engine_lock:
                wav = self._synthesize(text)
                if wav is None:
                    return False, 0.0
                playback_start = time.perf_counter()
                self._play_audio(wav)
            return True, playback_start
        except Exception as e:
            logger.error(f"Kokoro TTS failed: {e}")
            return False, 0.0

    def say_streaming(self, text: str, user_id: Optional[str] = None) -> tuple[bool, float]:
        return self.say(text, user_id=user_id)

    def _play_audio(self, wav: np.ndarray):
        p, stream = self._open_output_stream()
        try:
            resampled = self._resample_if_needed(wav)
            audio = (np.clip(resampled, -1.0, 1.0) * 32767).astype(np.int16)
            stream.write(audio.tobytes())
        finally:
            self._close_output_stream(p, stream)

    def _send_full_audio_to_frontend(self, user_id: str, text: str) -> tuple[bool, float]:
        if not self.pipeline or not self.model:
            return False, 0.0

        text_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
        text_preview = (text or "")[:120]

        playback_start = 0.0
        if self._notification_service is None:
            self._notification_service = get_default_service()

        try:
            with self._engine_lock:
                wav = self._synthesize(text)
                if wav is None:
                    return False, 0.0
                playback_start = time.perf_counter()
                audio = (np.clip(wav, -1.0, 1.0) * 32767).astype(np.int16)
                chunk_b64 = base64.b64encode(audio.tobytes()).decode("ascii")
                self._notification_service.push_audio_chunk(
                    user_id,
                    chunk_b64,
                    self.sample_rate,
                    True,
                    text_hash=text_hash,
                    text_preview=text_preview,
                )
            return True, playback_start
        except Exception as e:
            logger.error(f"Kokoro send-to-frontend failed: {e}")
            return False, 0.0

    def cleanup(self):
        self.model = None
        self.pipeline = None
        self._pyaudio = None
