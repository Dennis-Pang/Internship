"""Audio processing: recording, STT, and TTS."""
from .recorder import (
    record_audio,
    record_audio_hold_to_talk,
    select_input_device,
    cleanup_audio_file,
    TTSEngine,
    PiperTTSEngine,
    NeuTTSEngine,
)
from .stt import load_whisper_pipeline
from .stt import transcribe_whisper as transcribe_audio

__all__ = [
    'record_audio',
    'record_audio_hold_to_talk',
    'select_input_device',
    'cleanup_audio_file',
    'TTSEngine',
    'PiperTTSEngine',
    'NeuTTSEngine',
    'load_whisper_pipeline',
    'transcribe_audio',
]
