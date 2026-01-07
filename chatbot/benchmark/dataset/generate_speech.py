"""Generate speech audio for benchmark samples.

Creates OpenAI TTS outputs (MP3 + WAV) for each sample query and saves them
into the corresponding sample folder.

Usage:
    python generate_speech.py --sample-id H001           # single sample
    python generate_speech.py                            # all samples
    python generate_speech.py --data dataset/data.json   # legacy combined file

Requirements:
- OPENAI_API_KEY must be set.
- pydub installed for MP3 → WAV conversion.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add repo root to path for logger/config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.config import logger  # noqa: E402

OPENAI_TTS_MODEL = "tts-1"
OPENAI_TTS_VOICE = "alloy"

DEFAULT_DATA_PATH = Path(__file__).parent / "samples"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "samples"
DEFAULT_ENV_PATH = Path(__file__).parent.parent / ".env"


# ============================================================================
# Helpers
# ============================================================================

def load_samples_with_destinations(
    data_path: Path,
    output_dir: Path,
) -> List[Tuple[Dict[str, Any], Path]]:
    """Load samples and map each to its destination directory."""
    samples_with_paths: List[Tuple[Dict[str, Any], Path]] = []

    if data_path.is_dir():
        for sample_dir in sorted([p for p in data_path.iterdir() if p.is_dir()]):
            sample_file = sample_dir / "sample.json"
            if not sample_file.exists():
                logger.warning(f"No sample.json in {sample_dir}, skipping")
                continue
            with open(sample_file, "r") as f:
                sample = json.load(f)
            samples_with_paths.append((sample, sample_dir))
        return samples_with_paths

    if data_path.is_file():
        with open(data_path, "r") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"Expected a list of samples in {data_path}")
        for sample in data:
            sample_id = sample.get("id")
            if not sample_id:
                logger.warning("Sample missing id, skipping")
                continue
            sample_dir = output_dir / sample_id
            samples_with_paths.append((sample, sample_dir))
        return samples_with_paths

    raise FileNotFoundError(f"Data path not found: {data_path}")


def load_env_vars(env_path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ if not already set."""
    if not env_path.exists():
        logger.debug(f"No .env found at {env_path}")
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def text_to_speech_openai(text: str, output_path: Path) -> bool:
    """Generate MP3 via OpenAI TTS."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.error("OPENAI_API_KEY not set; cannot generate TTS")
        return False

    try:
        from openai import OpenAI
    except Exception as exc:
        logger.error(f"OpenAI package not available: {exc}")
        return False

    try:
        client = OpenAI(api_key=api_key)
        logger.info(f"Generating speech ({len(text)} chars) -> {output_path.name}")
        response = client.audio.speech.create(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            input=text,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response.stream_to_file(str(output_path))
        logger.info(f"✓ Saved MP3: {output_path}")
        return True
    except Exception as exc:
        logger.error(f"OpenAI TTS failed: {exc}")
        return False


def convert_mp3_to_wav(mp3_path: Path, wav_path: Path) -> bool:
    """Convert MP3 to mono 16k WAV."""
    try:
        from pydub import AudioSegment
    except Exception as exc:
        logger.error(f"pydub not available for conversion: {exc}")
        return False

    try:
        audio = AudioSegment.from_mp3(str(mp3_path))
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(str(wav_path), format="wav")
        logger.info(f"✓ Saved WAV: {wav_path}")
        return True
    except Exception as exc:
        logger.error(f"MP3 → WAV conversion failed: {exc}")
        return False


def generate_for_sample(
    sample: Dict[str, Any],
    sample_dir: Path,
    force: bool = False,
) -> None:
    """Generate TTS audio for a single sample."""
    sample_id = sample.get("id", "UNKNOWN")
    # Prefer last user turn in dialogue/chat history; fallback to query
    dialogue = sample.get("dialogue") or sample.get("chat_history") or []
    last_user = None
    for msg in reversed(dialogue):
        if msg.get("role") == "user":
            last_user = msg.get("content", "")
            break

    text = last_user or sample.get("query", "")
    if not text:
        logger.warning(f"Sample {sample_id} missing user text; skipping")
        return

    mp3_path = sample_dir / "query.mp3"
    wav_path = sample_dir / "query.wav"

    sample_dir.mkdir(parents=True, exist_ok=True)

    if mp3_path.exists() and not force:
        logger.info(f"[{sample_id}] MP3 exists, skipping generation")
    else:
        if not text_to_speech_openai(text, mp3_path):
            logger.error(f"[{sample_id}] TTS failed; skipping conversion")
            return

    if wav_path.exists() and not force:
        logger.info(f"[{sample_id}] WAV exists, skipping conversion")
    else:
        if not mp3_path.exists():
            logger.error(f"[{sample_id}] MP3 missing, cannot convert to WAV")
            return
        if convert_mp3_to_wav(mp3_path, wav_path):
            mp3_path.unlink(missing_ok=True)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate speech audio for benchmark samples.")
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to dataset directory (samples/) or legacy data.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to store per-sample outputs (defaults to samples/)",
    )
    parser.add_argument(
        "--sample-id",
        type=str,
        default=None,
        help="Process only this sample id (e.g., H001)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate audio even if files already exist",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_PATH,
        help="Path to .env with API keys (default: benchmark/.env)",
    )

    args = parser.parse_args()

    load_env_vars(args.env_file)

    samples = load_samples_with_destinations(args.data, args.output_dir)
    logger.info(f"Loaded {len(samples)} samples from {args.data}")

    processed = 0
    for sample, sample_dir in samples:
        sample_id = sample.get("id")
        if args.sample_id and sample_id != args.sample_id:
            continue
        logger.info(f"Processing sample {sample_id} -> {sample_dir}")
        generate_for_sample(sample, sample_dir, force=args.force)
        processed += 1

    if processed == 0:
        logger.warning("No samples processed (check --sample-id or data path)")
    else:
        logger.info(f"Completed {processed} sample(s)")


if __name__ == "__main__":
    main()
