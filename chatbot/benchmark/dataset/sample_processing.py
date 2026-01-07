"""
Full sample processing pipeline: TTS → emotion/personality → context.json → prompt.md.

Steps per sample:
- Generate TTS for the last user turn (skips if query.wav already exists, unless --force-tts).
- Run speech2emotion, text2emotion, and personality analysis.
- Save results plus memory into context.json inside the sample folder.
- Render prompt.md using the fused emotion probs/personality and existing template.

Usage:
    python sample_processing.py                         # process all samples under samples/
    python sample_processing.py --sample-id 001         # process a single sample
    python sample_processing.py --force-tts             # regenerate audio even if present
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Ensure repo root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.config import logger, SPEECH_EMOTION_WEIGHT, TEXT_EMOTION_WEIGHT  # noqa: E402
from modules.emotion.text_analyzer import TEXT_EMOTION_LABELS  # noqa: E402
from chatbot_cli import (  # noqa: E402
    analyze_speech_emotion,
    analyze_text_emotion,
    analyze_personality,
    fuse_emotions,
)

from generate_speech import (  # noqa: E402
    DEFAULT_DATA_PATH,
    DEFAULT_ENV_PATH,
    DEFAULT_OUTPUT_DIR,
    generate_for_sample,
    load_env_vars,
    load_samples_with_destinations,
)
from build_prompts import (  # noqa: E402
    PROMPT_TEMPLATE,
    format_conversation_history,
    format_emotion_block,
    format_personality,
    format_preferences,
    split_dialogue,
    load_sample,
)


def logits_to_probs(logits: Dict[str, float]) -> Dict[str, float]:
    """Convert logits dict into softmax probabilities using TEXT_EMOTION_LABELS order."""
    if not logits:
        uniform = 1.0 / len(TEXT_EMOTION_LABELS)
        return {label: uniform for label in TEXT_EMOTION_LABELS}

    values = np.array([logits.get(label, 0.0) for label in TEXT_EMOTION_LABELS], dtype=float)
    values = values - values.max()
    exp = np.exp(values)
    denom = float(exp.sum())
    if denom <= 0:
        uniform = 1.0 / len(TEXT_EMOTION_LABELS)
        return {label: uniform for label in TEXT_EMOTION_LABELS}
    probs = exp / denom
    return {label: float(probs[i]) for i, label in enumerate(TEXT_EMOTION_LABELS)}


def build_prompt(
    conversation_history: List[Dict[str, str]],
    memory: Dict[str, Any],
    user_message: str,
    personality_df,
    fused_emotion: Dict[str, float],
) -> str:
    """Render prompt.md text using existing template and formatting helpers."""
    return PROMPT_TEMPLATE.format(
        conversation_history=format_conversation_history(conversation_history),
        personality_block=format_personality(personality_df),
        emotion_block=format_emotion_block(fused_emotion),
        preferences_block=format_preferences(memory),
        user_message=user_message,
    ).strip() + "\n"


def save_context(
    sample_dir: Path,
    user_message: str,
    memory: Dict[str, Any],
    fused_emotion: Dict[str, float],
    personality_df,
) -> Path:
    """Persist context.json matching historical format (string blocks)."""
    context = {
        "USER_PERSONALITY": format_personality(personality_df),
        "EMOTION_LOGITS": format_emotion_block(fused_emotion),
        "KNOWN_PREFERENCES": format_preferences(memory),
        "USER_MESSAGE": user_message,
    }

    out_path = sample_dir / "context.json"
    out_path.write_text(json.dumps(context, indent=2), encoding="utf-8")
    return out_path


def process_sample(sample: Dict[str, Any], sample_dir: Path, force_tts: bool) -> None:
    sample_id = sample.get("id", sample_dir.name)
    logger.info("=== Processing sample %s ===", sample_id)

    wav_path = sample_dir / "query.wav"

    # Generate TTS (skip if WAV already exists unless forced)
    if wav_path.exists() and not force_tts:
        logger.info("[%s] query.wav exists, skipping TTS", sample_id)
    else:
        generate_for_sample(sample, sample_dir, force=force_tts)

    if not wav_path.exists():
        logger.error("[%s] query.wav missing; TTS step may have failed", sample_id)
        return

    # Dialogue split
    dialogue = sample.get("dialogue", [])
    history, last_user = split_dialogue(dialogue)
    if not last_user:
        logger.error("[%s] last user message empty", sample_id)
        return

    memory = sample.get("memory", {})

    # Analyses
    speech_logits = analyze_speech_emotion(str(wav_path), return_logits=True)
    text_logits = analyze_text_emotion(last_user, return_logits=True)
    speech_probs = logits_to_probs(speech_logits)
    text_probs = logits_to_probs(text_logits)
    fused_emotion = fuse_emotions(
        speech_emotion=speech_probs,
        text_emotion=text_probs,
        speech_weight=SPEECH_EMOTION_WEIGHT,
        text_weight=TEXT_EMOTION_WEIGHT,
    )
    personality_df = analyze_personality(last_user)

    # Save context and prompt
    context_path = save_context(
        sample_dir=sample_dir,
        user_message=last_user,
        memory=memory,
        fused_emotion=fused_emotion,
        personality_df=personality_df,
    )
    prompt_text = build_prompt(history, memory, last_user, personality_df, fused_emotion)
    prompt_path = sample_dir / "prompt.md"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    logger.info("[%s] context.json -> %s", sample_id, context_path)
    logger.info("[%s] prompt.md -> %s", sample_id, prompt_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full sample processing pipeline.")
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
        help="Destination root for per-sample outputs (defaults to samples/)",
    )
    parser.add_argument(
        "--sample-id",
        type=str,
        default=None,
        help="Process only this sample id (e.g., 001)",
    )
    parser.add_argument(
        "--force-tts",
        action="store_true",
        help="Regenerate TTS audio even if query.wav already exists",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_PATH,
        help="Path to .env with API keys (default: benchmark/.env)",
    )
    args = parser.parse_args()

    load_env_vars(args.env_file)

    samples_with_paths = load_samples_with_destinations(args.data, args.output_dir)
    logger.info("Loaded %d sample(s) from %s", len(samples_with_paths), args.data)

    processed = 0
    for sample, sample_dir in samples_with_paths:
        sample_id = sample.get("id")
        if args.sample_id and sample_id != args.sample_id:
            continue
        try:
            # Ensure sample.json is available if data path came from legacy JSON
            if not (sample_dir / "sample.json").exists():
                sample_dir.mkdir(parents=True, exist_ok=True)
                (sample_dir / "sample.json").write_text(json.dumps(sample, indent=2), encoding="utf-8")
            else:
                # sync on-disk sample with loaded one (keeps existing file if present)
                sample = load_sample(sample_dir)
            process_sample(sample, sample_dir, force_tts=args.force_tts)
            processed += 1
        except Exception as exc:
            logger.error("[%s] pipeline failed: %s", sample_id or sample_dir.name, exc)
            continue

    if processed == 0:
        logger.warning("No samples processed (check --sample-id or data path)")
    else:
        logger.info("Completed %d sample(s)", processed)


if __name__ == "__main__":
    main()
