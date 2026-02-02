"""Audio recording module."""
import logging
import os
import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile

from core.config import (
    SAMPLE_RATE,
    RECORD_DURATION,
    AUDIO_FILE,
    AUDIO_TIMEOUT_MARGIN,
    AUDIO_MAX_RETRIES,
    AUDIO_MIN_RMS,
)

logger = logging.getLogger(__name__)


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

        # Calculate RMS energy to detect valid speech
        rms = np.sqrt(np.mean(audio_data ** 2))

        # Log audio statistics for debugging
        logger.info(f"Audio stats - Shape: {audio_data.shape}, "
                   f"Min: {np.min(audio_data):.4f}, Max: {np.max(audio_data):.4f}, "
                   f"RMS: {rms:.4f}")

        # Check if audio has sufficient energy
        if rms < AUDIO_MIN_RMS:
            logger.warning(f"Audio RMS ({rms:.4f}) below threshold ({AUDIO_MIN_RMS}). "
                          "No valid speech detected, please try again.")
            print(f"⚠ No speech detected (RMS: {rms:.4f}). Please speak louder or check your microphone.")
            return False

        # Save audio file
        wavfile.write(output_file, sample_rate, audio_data)
        print(f"Audio recording saved to {output_file}")

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


def record_audio_hold_to_talk(
    is_holding_key: Callable[[], bool],
    *,
    device_index: Optional[int] = None,
    sample_rate: int = SAMPLE_RATE,
    output_file: str = AUDIO_FILE,
    max_duration: float = 30.0,
    block_size: int = 1024,
) -> bool:
    """Record while a key is held down, stopping when released or after max_duration.

    Args:
        is_holding_key: Callable returning True while the key is still pressed.
        device_index: Optional device index.
        sample_rate: Recording sample rate.
        output_file: Path to save WAV.
        max_duration: Safety cap in seconds.
        block_size: Frames per read from sounddevice.

    Returns:
        True if recording succeeded and file saved, False otherwise.
    """
    chunks = []
    start = time.perf_counter()

    try:
        if device_index is not None:
            try:
                device_info = sd.query_devices(device_index)
                logger.info(f"Using device {device_index}: {device_info['name']}")
            except Exception as exc:
                logger.warning(f"Could not query device info: {exc}")

        print("Hold 'r' to record (release to stop, max 30s)...")
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            device=device_index,
            blocksize=block_size,
        ) as stream:
            while (time.perf_counter() - start) < max_duration and is_holding_key():
                data, overflowed = stream.read(block_size)
                if overflowed:
                    logger.warning("Input buffer overflowed during recording.")
                chunks.append(np.copy(data))

        if not chunks:
            logger.warning("No audio captured (possibly released too quickly).")
            return False

        audio_data = np.concatenate(chunks, axis=0)
        rms = np.sqrt(np.mean(audio_data ** 2))
        logger.info(
            "Hold-to-talk audio stats - Shape: %s, Min: %.4f, Max: %.4f, RMS: %.4f",
            audio_data.shape,
            float(np.min(audio_data)),
            float(np.max(audio_data)),
            float(rms),
        )

        if rms < AUDIO_MIN_RMS:
            logger.warning(
                "Audio RMS (%.4f) below threshold (%.4f). No valid speech detected.",
                rms,
                AUDIO_MIN_RMS,
            )
            print(f"⚠ No speech detected (RMS: {rms:.4f}). Please speak louder or check your microphone.")
            return False

        wavfile.write(output_file, sample_rate, audio_data)
        print(f"Audio recording saved to {output_file}")
        return True

    except Exception as exc:
        logger.error("Hold-to-talk recording failed: %s", exc, exc_info=True)
        return False
