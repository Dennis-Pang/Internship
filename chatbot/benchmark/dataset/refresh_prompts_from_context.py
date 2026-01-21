"""Refresh prompt.md for samples using existing context.json and the latest prompt template.

This avoids re-running emotion/personality models. It:
- Loads sample.json for dialogue.
- Loads context.json for USER_PERSONALITY, EMOTION_LOGITS, KNOWN_PREFERENCES.
- Normalizes these blocks to the current template format (matching samples/001).
- Writes prompt.md with PROMPT_TEMPLATE from build_prompts.

Usage:
    python refresh_prompts_from_context.py          # refresh all samples
    python refresh_prompts_from_context.py --ids 001 010
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from build_prompts import PROMPT_TEMPLATE, format_conversation_history, load_sample  # noqa: E402

SAMPLES_DIR = Path(__file__).parent / "samples"
REQUIRED_CONTEXT_KEYS = ["USER_PERSONALITY", "EMOTION_LOGITS", "KNOWN_PREFERENCES"]


def normalize_key_values(raw: str) -> str:
    """Convert newline- or comma-delimited `key: value` entries to `key=value` comma string."""
    text = raw.strip()
    if not text:
        raise ValueError("Empty context block")

    # Split by lines first; fall back to comma splits if only one line
    parts = [p.strip() for p in text.splitlines() if p.strip()]
    if len(parts) <= 1 and "," in text:
        parts = [p.strip() for p in text.split(",") if p.strip()]

    normalized = []
    for part in parts:
        if ":" in part:
            k, v = part.split(":", 1)
        elif "=" in part:
            k, v = part.split("=", 1)
        else:
            # Unable to split; keep as-is
            normalized.append(part)
            continue
        normalized.append(f"{k.strip()}={v.strip()}")

    return ", ".join(normalized)


def load_context(sample_dir: Path) -> Dict[str, str]:
    ctx_path = sample_dir / "context.json"
    if not ctx_path.exists():
        raise FileNotFoundError(f"context.json not found in {sample_dir}")

    data = json.loads(ctx_path.read_text())
    context: Dict[str, str] = {}
    for key in REQUIRED_CONTEXT_KEYS:
        value = str(data.get(key, "")).strip()
        if not value:
            raise ValueError(f"{key} missing or empty in {ctx_path}")
        context[key] = normalize_key_values(value)
    return context


def build_prompt(sample_dir: Path) -> str:
    sample = load_sample(sample_dir)
    dialogue = sample.get("dialogue", [])
    if not dialogue:
        raise ValueError(f"Dialogue is empty for {sample_dir.name}")

    context = load_context(sample_dir)

    prompt_text = PROMPT_TEMPLATE.format(
        conversation_history=format_conversation_history(dialogue),
        personality_block=context["USER_PERSONALITY"],
        emotion_block=context["EMOTION_LOGITS"],
        preferences_block=context["KNOWN_PREFERENCES"],
    ).strip() + "\n"

    return prompt_text


def list_sample_ids(selected_ids: List[str] | None) -> List[str]:
    if selected_ids:
        return selected_ids
    return sorted(
        [p.name for p in SAMPLES_DIR.iterdir() if p.is_dir() and p.name.isdigit() and len(p.name) == 3]
    )


def main():
    parser = argparse.ArgumentParser(description="Refresh prompt.md using context.json for samples.")
    parser.add_argument("--ids", nargs="*", help="Sample IDs to process (e.g., 001 010). Default: all.")
    args = parser.parse_args()

    sample_ids = list_sample_ids(args.ids)
    if not sample_ids:
        raise RuntimeError("No sample directories found.")

    for sid in sample_ids:
        sample_dir = SAMPLES_DIR / sid
        prompt_path = sample_dir / "prompt.md"
        prompt_text = build_prompt(sample_dir)
        prompt_path.write_text(prompt_text, encoding="utf-8")
        print(f"[{sid}] prompt.md refreshed")


if __name__ == "__main__":
    main()
