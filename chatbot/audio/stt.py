"""Speech-to-text module using Whisper."""
import logging
import os
from typing import Any, Dict

import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

from core.config import WHISPER_MODEL_PATH

logger = logging.getLogger(__name__)


def transcribe_whisper(audio_file: str, pipe) -> str:
    """Transcribe audio using Whisper pipeline.

    Args:
        audio_file: Path to audio file.
        pipe: Hugging Face transformers pipeline for ASR.

    Returns:
        Transcribed text.
    """
    try:
        with open(audio_file, "rb") as f:
            audio_data = f.read()

        if not audio_data:
            logger.error("Audio file is empty.")
            return ""

        # Run Whisper transcription
        outputs = pipe(audio_data, batch_size=48, return_timestamps=False)
        transcription = outputs["text"]

        return transcription

    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return ""


def load_whisper_pipeline(use_gpu: bool = None) -> Any:
    """Load Whisper ASR pipeline.

    Args:
        use_gpu: Whether to use GPU. If None, auto-detect CUDA availability.

    Returns:
        Transformers pipeline for automatic speech recognition.

    Raises:
        FileNotFoundError: If Whisper model path doesn't exist.
    """
    if use_gpu is None:
        use_gpu = torch.cuda.is_available()

    pipeline_device = 0 if use_gpu else "cpu"
    torch_dtype = torch.float16 if use_gpu else torch.float32

    if not os.path.isdir(WHISPER_MODEL_PATH):
        raise FileNotFoundError(f"Whisper model directory not found: {WHISPER_MODEL_PATH}")

    try:
        # Load model without device_map to avoid meta tensor issues on PyTorch 2.7+
        device = f"cuda:{pipeline_device}" if use_gpu else "cpu"
        processor = AutoProcessor.from_pretrained(WHISPER_MODEL_PATH)
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            WHISPER_MODEL_PATH,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=False,
            attn_implementation="sdpa",
        )
        model.to(device)
        model.eval()

        pipe = pipeline(
            task="automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            generate_kwargs={"task": "transcribe", "language": "en"},
        )
        return pipe

    except Exception as e:
        logger.error(f"Failed to load Whisper pipeline: {e}")
        raise
