"""Audio recording and text-to-speech module."""
import logging
import os
import queue
import threading
from typing import Optional, Iterator

import numpy as np
import pyttsx3
import sounddevice as sd
import scipy.io.wavfile as wavfile

from modules.config import (
    SAMPLE_RATE,
    RECORD_DURATION,
    AUDIO_FILE,
    TTS_RATE,
    TTS_VOLUME,
    AUDIO_TIMEOUT_MARGIN,
    AUDIO_MAX_RETRIES,
    USE_PIPER_TTS,
    PIPER_MODEL_PATH,
    PIPER_CONFIG_PATH,
    PIPER_USE_GPU,
    PIPER_SENTENCE_MIN_WORDS,
)

logger = logging.getLogger(__name__)


class TTSEngine:
    """Text-to-speech engine wrapper."""

    def __init__(self):
        """Initialize TTS engine."""
        self.engine: Optional[pyttsx3.Engine] = None
        self._engine_lock = threading.Lock()
        self._stream_queue: queue.Queue = queue.Queue()
        self._stream_thread: Optional[threading.Thread] = None
        self._streaming_active = False
        self._first_playback_time: Optional[float] = None  # Track first audio playback
        self._init_engine()

    def _init_engine(self):
        """Initialize pyttsx3 engine with configuration."""
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

    def say(self, text: str) -> bool:
        """Speak text using TTS.

        Args:
            text: Text to speak.

        Returns:
            True if successful, False otherwise.
        """
        if not self.engine:
            logger.error("TTS engine not initialized.")
            return False

        try:
            import time
            # Record first playback time if not streaming
            if not self._streaming_active and self._first_playback_time is None:
                self._first_playback_time = time.perf_counter()

            with self._engine_lock:
                self.engine.say(text)
                self.engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"Failed to speak text: {e}")
            return False

    def _stream_worker(self):
        """Background worker to consume queued text and speak it sequentially."""
        import time
        while True:
            text = self._stream_queue.get()
            if text is None:
                self._stream_queue.task_done()
                break
            try:
                # Record time of first playback (user-perceived latency)
                if self._first_playback_time is None:
                    self._first_playback_time = time.perf_counter()

                with self._engine_lock:
                    self.engine.say(text)
                    self.engine.runAndWait()
            except Exception as e:
                logger.error(f"Failed to stream TTS chunk: {e}")
            finally:
                self._stream_queue.task_done()

    def start_streaming(self):
        """Start background streaming playback if not already running."""
        if not self.engine:
            logger.error("TTS engine not initialized.")
            return

        if self._streaming_active and self._stream_thread and self._stream_thread.is_alive():
            return

        # Reset first playback time for new streaming session
        self._first_playback_time = None
        self._streaming_active = True
        self._stream_thread = threading.Thread(target=self._stream_worker, daemon=True)
        self._stream_thread.start()

    def stream_text(self, text: str):
        """Queue text for streaming playback (non-blocking)."""
        if not text or not self.engine:
            return
        if not self._streaming_active:
            self.start_streaming()
        self._stream_queue.put(text)

    def finish_streaming(self, wait: bool = True) -> Optional[float]:
        """Signal the streaming worker to finish and optionally wait.

        Args:
            wait: Whether to wait for playback to complete

        Returns:
            Time of first playback (perf_counter timestamp), or None if no audio played
        """
        if not self._streaming_active:
            return self._first_playback_time

        self._stream_queue.put(None)
        if wait and self._stream_thread:
            self._stream_thread.join()
        self._streaming_active = False

        return self._first_playback_time

    def cleanup(self):
        """Clean up TTS engine resources."""
        # Ensure streaming thread is stopped before tearing down engine
        self.finish_streaming(wait=True)
        if self.engine:
            try:
                self.engine.stop()
                if getattr(self.engine, "_inLoop", False):
                    self.engine.endLoop()
            except Exception as e:
                logger.error(f"Failed to clean up TTS engine: {e}")
            self.engine = None


class PiperTTSEngine:
    """GPU-accelerated TTS engine using PiperTTS.

    Drop-in replacement for TTSEngine with identical interface.
    Uses GPU-accelerated PiperTTS via ONNX Runtime for faster synthesis.
    Supports true streaming: tokens → sentence splitting → GPU synthesis → playback
    """

    def __init__(self):
        """Initialize Piper TTS engine."""
        self.engine: Optional['StreamingPiperTTS'] = None
        self._engine_lock = threading.Lock()
        self._token_queue: queue.Queue = queue.Queue()  # Queue for LLM tokens
        self._stream_thread: Optional[threading.Thread] = None
        self._streaming_active = False
        self._first_playback_time: Optional[float] = None  # Track first audio playback
        self._init_engine()

    def _init_engine(self):
        """Initialize PiperTTS engine with configuration."""
        try:
            # Import here to avoid dependency if not using Piper TTS
            from modules.audio.piper_tts import StreamingPiperTTS

            # Check if model files exist
            if not os.path.exists(PIPER_MODEL_PATH):
                logger.error(f"Piper model not found: {PIPER_MODEL_PATH}")
                logger.info("Falling back to pyttsx3")
                return

            if not os.path.exists(PIPER_CONFIG_PATH):
                logger.error(f"Piper config not found: {PIPER_CONFIG_PATH}")
                logger.info("Falling back to pyttsx3")
                return

            self.engine = StreamingPiperTTS(
                model_path=PIPER_MODEL_PATH,
                config_path=PIPER_CONFIG_PATH,
                use_gpu=PIPER_USE_GPU,
                sentence_min_words=PIPER_SENTENCE_MIN_WORDS
            )
            logger.info("✅ Piper TTS engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Piper TTS engine: {e}")
            logger.info("Falling back to pyttsx3")
            self.engine = None

    def say(self, text: str) -> bool:
        """Speak text using TTS (blocking).

        Args:
            text: Text to speak.

        Returns:
            True if successful, False otherwise.
        """
        if not self.engine:
            logger.error("Piper TTS engine not initialized.")
            return False

        try:
            import time
            # Record first playback time if not streaming
            if not self._streaming_active and self._first_playback_time is None:
                self._first_playback_time = time.perf_counter()

            with self._engine_lock:
                return self.engine.say(text)
        except Exception as e:
            logger.error(f"Failed to speak text: {e}")
            return False

    def _token_generator(self):
        """Generator that yields tokens from the queue."""
        while True:
            token = self._token_queue.get()
            if token is None:  # End of stream signal
                self._token_queue.task_done()
                break
            try:
                yield token
            finally:
                self._token_queue.task_done()

    def _stream_worker(self):
        """Background worker that runs PiperTTS streaming synthesis."""
        try:
            # Run true streaming TTS: tokens → sentence split → GPU synthesis → playback
            first_playback_time = self.engine.process_streaming_text(self._token_generator())
            self._first_playback_time = first_playback_time
            logger.debug(f"Streaming TTS completed, first playback at {first_playback_time}")
        except Exception as e:
            logger.error(f"Streaming TTS worker error: {e}", exc_info=True)

    def start_streaming(self):
        """Start background streaming playback thread."""
        if not self.engine:
            logger.error("Piper TTS engine not initialized.")
            return

        if self._streaming_active and self._stream_thread and self._stream_thread.is_alive():
            return

        # Reset first playback time for new streaming session
        self._first_playback_time = None
        self._streaming_active = True
        self._stream_thread = threading.Thread(target=self._stream_worker, daemon=True)
        self._stream_thread.start()
        logger.debug("Streaming TTS worker started")

    def stream_text(self, text: str):
        """Queue text token for streaming playback (non-blocking).

        Args:
            text: Text token/chunk from LLM to queue for streaming TTS
        """
        if not text or not self.engine:
            return
        if not self._streaming_active:
            self.start_streaming()
        self._token_queue.put(text)

    def finish_streaming(self, wait: bool = True) -> Optional[float]:
        """Signal streaming to finish and optionally wait for completion.

        Args:
            wait: Whether to wait for playback to complete

        Returns:
            Time of first playback (perf_counter timestamp), or None if no audio played
        """
        if not self._streaming_active:
            return self._first_playback_time

        # Signal end of stream
        self._token_queue.put(None)

        if wait and self._stream_thread:
            self._stream_thread.join()

        self._streaming_active = False
        logger.debug("Streaming TTS worker stopped")

        return self._first_playback_time

    def process_streaming_text(self, text_generator: Iterator[str]) -> Optional[float]:
        """Process streaming text from generator (e.g., LLM) - alternative interface.

        Args:
            text_generator: Iterator/generator yielding text chunks (tokens)

        Returns:
            Time of first playback (perf_counter timestamp), or None if no audio played

        Note:
            This is a direct pass-through to PiperTTS streaming.
            For the queue-based interface, use start_streaming() + stream_text() + finish_streaming().
        """
        if not self.engine:
            logger.error("Piper TTS engine not initialized.")
            return None

        try:
            with self._engine_lock:
                return self.engine.process_streaming_text(text_generator)
        except Exception as e:
            logger.error(f"Failed to process streaming text: {e}")
            return None

    def cleanup(self):
        """Clean up TTS engine resources."""
        # Stop streaming thread if active
        self.finish_streaming(wait=True)

        # Note: Skip explicit PiperTTS cleanup to avoid ONNX Runtime double-free errors
        # The streaming thread cleanup above is sufficient
        # Let Python garbage collector handle ONNX session cleanup naturally
        if self.engine:
            # Just stop threads and clear queues, don't call engine.cleanup()
            try:
                self.engine.stop_flag = True
                if hasattr(self.engine, '_player_thread') and self.engine._player_thread:
                    if self.engine._player_thread.is_alive():
                        self.engine._player_thread.join(timeout=1)
            except Exception as e:
                logger.debug(f"Error stopping Piper threads: {e}")
            self.engine = None


def _safe_stop_recording():
    """Safely stop sounddevice recording with error handling."""
    try:
        sd.stop()
        logger.info("Recording stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop recording: {e}")


def _is_usable_device(device_info) -> bool:
    """Check if a device is likely usable for recording.

    Args:
        device_info: Device info dict from sounddevice.

    Returns:
        True if device seems usable.
    """
    name = device_info['name'].lower()
    channels = device_info['max_input_channels']

    # Filter out virtual/unusable devices
    if channels == 0:
        return False
    if channels > 16:  # Likely virtual device
        return False
    if any(skip in name for skip in ['sysdefault', 'default', 'spdif', 'samplerate',
                                      'speexrate', 'upmix', 'vdownmix', 'pulse']):
        return False

    return True


def _find_best_device(input_devices) -> Optional[int]:
    """Automatically find the best input device.

    Prioritizes USB devices, then hw devices with reasonable channel counts.

    Args:
        input_devices: List of input device info dicts.

    Returns:
        Device index or None.
    """
    # First priority: USB devices
    usb_devices = [d for d in input_devices if 'usb' in d['name'].lower()]
    if usb_devices:
        logger.info(f"Auto-selecting USB device: {usb_devices[0]['name']}")
        return usb_devices[0]['index']

    # Second priority: hw devices with 1-2 channels (typical microphones)
    hw_devices = [d for d in input_devices
                  if 'hw:' in d['name'].lower() and d['max_input_channels'] <= 2]
    if hw_devices:
        logger.info(f"Auto-selecting hw device: {hw_devices[0]['name']}")
        return hw_devices[0]['index']

    # Fallback: first available device
    if input_devices:
        logger.info(f"Auto-selecting first device: {input_devices[0]['name']}")
        return input_devices[0]['index']

    return None


def select_input_device() -> Optional[int]:
    """Automatically select the best audio input device.

    If USB microphone is found, use it automatically.
    Otherwise, show filtered list of usable devices.

    Returns:
        Device index or None for default device.
    """
    all_devices = sd.query_devices()

    # Filter to usable input devices
    input_devices = [d for d in all_devices if _is_usable_device(d)]

    if not input_devices:
        logger.warning("No usable input devices found. Using system default.")
        return None

    # Try to auto-select best device
    best_device = _find_best_device(input_devices)

    # Show simplified device list (max 5 devices)
    print("\nUsable input devices:")
    for i, d in enumerate(input_devices[:5]):
        marker = " [SELECTED]" if d['index'] == best_device else ""
        print(f"{i}: {d['name']} (channels: {d['max_input_channels']}){marker}")

    if len(input_devices) > 5:
        print(f"... and {len(input_devices) - 5} more devices")

    # Ask if user wants to change
    try:
        response = input(f"\nPress Enter to use selected device, or enter device number to change: ").strip()
        if not response:
            return best_device
        idx = int(response)
        if 0 <= idx < len(input_devices):
            return input_devices[idx]['index']
        else:
            logger.warning("Invalid device index. Using auto-selected device.")
            return best_device
    except ValueError:
        logger.warning("Invalid input. Using auto-selected device.")
        return best_device


def record_audio(
    device_index: Optional[int] = None,
    duration: int = RECORD_DURATION,
    sample_rate: int = SAMPLE_RATE,
    output_file: str = AUDIO_FILE,
    timeout_margin: float = AUDIO_TIMEOUT_MARGIN,
) -> bool:
    """Record audio from microphone.

    Args:
        device_index: Audio device index (None for default).
        duration: Recording duration in seconds.
        sample_rate: Audio sample rate.
        output_file: Output WAV file path.
        timeout_margin: Extra seconds to wait beyond duration before timeout.

    Returns:
        True if recording successful, False otherwise.
    """
    try:
        # Log device information for debugging
        if device_index is not None:
            try:
                device_info = sd.query_devices(device_index)
                logger.info(f"Using device {device_index}: {device_info['name']}")
                logger.info(f"Device max input channels: {device_info['max_input_channels']}")
                logger.info(f"Device default samplerate: {device_info['default_samplerate']}")
            except Exception as e:
                logger.warning(f"Could not query device info: {e}")

        print(f"Recording for {duration} seconds...")

        # Start recording
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=device_index,
            blocking=False
        )

        # Wait with timeout to prevent infinite hanging
        timeout_seconds = duration + timeout_margin
        wait_completed = threading.Event()

        def wait_for_recording():
            try:
                sd.wait()
                wait_completed.set()
            except Exception as e:
                logger.error(f"Error during sd.wait(): {e}")
                wait_completed.set()

        wait_thread = threading.Thread(target=wait_for_recording, daemon=True)
        wait_thread.start()

        # Wait for completion or timeout
        if not wait_completed.wait(timeout=timeout_seconds):
            logger.error(f"Recording timeout after {timeout_seconds}s. Attempting to stop...")

            # Try to stop recording in a non-blocking way
            stop_thread = threading.Thread(target=lambda: _safe_stop_recording(), daemon=True)
            stop_thread.start()
            stop_thread.join(timeout=1.0)  # Wait max 1 second for stop

            if stop_thread.is_alive():
                logger.error("sd.stop() is also hanging. Giving up on this recording.")

            return False

        # Validate audio data
        if audio_data is None:
            logger.error("No audio data recorded (audio_data is None).")
            return False

        if not np.any(audio_data):
            logger.warning("Audio data is all zeros - microphone may not be working.")
            # Still save it, might be useful for debugging

        # Check for NaN or inf values
        if np.any(np.isnan(audio_data)) or np.any(np.isinf(audio_data)):
            logger.error("Audio data contains NaN or inf values.")
            return False

        # Save audio file
        wavfile.write(output_file, sample_rate, audio_data)
        print(f"Audio recording saved to {output_file}")

        # Log audio statistics for debugging
        logger.info(f"Audio stats - Shape: {audio_data.shape}, "
                   f"Min: {np.min(audio_data):.4f}, Max: {np.max(audio_data):.4f}, "
                   f"Mean: {np.mean(audio_data):.4f}")

        return True

    except Exception as e:
        logger.error(f"Audio recording failed: {e}", exc_info=True)
        # Try to stop in a non-blocking way
        stop_thread = threading.Thread(target=_safe_stop_recording, daemon=True)
        stop_thread.start()
        stop_thread.join(timeout=0.5)
        return False


def validate_device_capabilities(device_index: Optional[int], sample_rate: int = SAMPLE_RATE) -> bool:
    """Validate that the device supports required recording configuration.

    Args:
        device_index: Audio device index (None for default).
        sample_rate: Desired sample rate.

    Returns:
        True if device is compatible, False otherwise.
    """
    try:
        device_info = sd.query_devices(device_index, 'input')

        # Check if device has input channels
        if device_info['max_input_channels'] < 1:
            logger.error(f"Device has no input channels: {device_info['name']}")
            return False

        # Check if sample rate is supported (with some tolerance)
        default_sr = device_info['default_samplerate']
        if abs(default_sr - sample_rate) > 1000:
            logger.warning(f"Device default samplerate ({default_sr}) differs from requested ({sample_rate})")
            # Don't fail, just warn - sounddevice can resample

        logger.info(f"Device validation passed for: {device_info['name']}")
        return True

    except Exception as e:
        logger.error(f"Failed to validate device: {e}")
        return False


def toggle_recording(max_retries: int = AUDIO_MAX_RETRIES) -> bool:
    """Interactive audio recording with device selection and retry logic.

    Args:
        max_retries: Maximum number of retry attempts on failure.

    Returns:
        True if recording successful, False otherwise.
    """
    device_index = select_input_device()

    if device_index is None and not any(d['max_input_channels'] > 0 for d in sd.query_devices()):
        logger.error("No valid input device. Aborting recording.")
        return False

    # Validate device capabilities
    if device_index is not None:
        if not validate_device_capabilities(device_index):
            logger.warning("Device validation failed, but attempting to proceed anyway...")

    # Attempt recording with retries
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt}/{max_retries}...")
            print(f"Retrying recording (attempt {attempt}/{max_retries})...")

        success = record_audio(device_index)

        if success:
            return True

        if attempt < max_retries:
            logger.warning("Recording failed, will retry...")
            # Small delay before retry
            import time
            time.sleep(0.5)

    logger.error(f"Recording failed after {max_retries + 1} attempts.")
    return False


def cleanup_audio_file(audio_file: str = AUDIO_FILE):
    """Remove temporary audio file.

    Args:
        audio_file: Path to audio file to delete.
    """
    if os.path.exists(audio_file):
        try:
            os.remove(audio_file)
        except Exception as e:
            logger.error(f"Failed to remove audio file {audio_file}: {e}")
