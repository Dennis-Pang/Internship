"""Build per-sample prompt.md files using real signals (speech/text emotion + personality).

For each sample directory:
- Load sample.json (expects fields: id, dialogue, memory, etc.)
- Use the last user turn for emotion/personality analysis
- Run speech2emotion on query.wav and text2emotion on the last user text
- Fuse emotions using chatbot_cli weights
- Run personality analysis on the last user text
- Render a Markdown prompt in the latest format (matching samples/001) and save to prompt.md

Usage:
    python build_prompts.py                      # process all samples in dataset/samples
    python build_prompts.py --sample-ids 001 002 # process specific samples
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Ensure imports work like chatbot_cli
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.config import logger, SPEECH_EMOTION_WEIGHT, TEXT_EMOTION_WEIGHT  # noqa: E402
from models.emotion import TEXT_EMOTION_LABELS  # noqa: E402
from core.pipeline import (  # noqa: E402
    analyze_speech_emotion,
    analyze_text_emotion,
    analyze_personality,
    fuse_emotions,
)

SAMPLES_DIR = Path(__file__).parent / "samples"


PROMPT_TEMPLATE = """You are Hackcelerate — a health companion who chats naturally with users. You adapt your responses to the moment: sometimes you ask questions, sometimes you share thoughts, sometimes you just listen. When something connects to what you know about the user, you reference it naturally to make the conversation personal.

INSTRUCTIONS:
- Use EMOTION_LOGITS to adjust emotional tone and USER_PERSONALITY to adjust interaction style
- Reference KNOWN_PREFERENCES directly when relevant (e.g., "your blood pressure pill," "your weekend mornings")
- 2–5 sentences, conversational tone, no meta-talk about context/memory/prompts
- User wants help → offer 1–2 small steps | User is sharing → respond supportively
- Write ONLY your reply as Assistant, no analysis or commentary

---

EXAMPLES:

Example 1:
KNOWN_PREFERENCES: medication=insulin, struggle=lunch_dose_at_work
User: "Forgot my insulin again at work"
Assistant: "That lunch dose is tricky. Does your work routine vary a lot day to day?"

Example 2:
KNOWN_PREFERENCES: goal=walking_habit, milestone=walked_3_days
User: "Hit 3 days of walking!"
Assistant: "Nice! How's your energy feeling? Notice any difference yet?"

---

CONTEXT:

USER_PERSONALITY: {personality_block}

EMOTION_LOGITS: {emotion_block}

KNOWN_PREFERENCES: {preferences_block}

CONVERSATION:
{conversation_history}
"""


def load_sample(sample_dir: Path) -> Dict[str, Any]:
    sample_file = sample_dir / "sample.json"
    if not sample_file.exists():
        raise FileNotFoundError(f"sample.json not found in {sample_dir}")
    return json.loads(sample_file.read_text())


def split_dialogue(dialogue: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str]:
    """Return (history_without_last_user, last_user_text)."""
    last_user_idx = None
    for idx in range(len(dialogue) - 1, -1, -1):
        if dialogue[idx].get("role") == "user":
            last_user_idx = idx
            break

    if last_user_idx is None:
        raise ValueError("No user turn found in dialogue")

    last_user_text = dialogue[last_user_idx].get("content", "") or ""
    history = dialogue[:last_user_idx]
    return history, last_user_text


def format_conversation_history(history: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for msg in history:
        content = msg.get("content", "")
        if not content:
            continue
        role = msg.get("role", "")
        speaker = "User" if role == "user" else "Assistant"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines) if lines else "No prior conversation history."


def format_personality(personality_df) -> str:
    entries = [f"{row['theta']}={row['r']:.2f}" for _, row in personality_df.iterrows()]
    return ", ".join(entries)


def format_emotion_block(fused_emotion: Dict[str, float]) -> str:
    return ", ".join(
        f"{label}={fused_emotion.get(label, 0.0):.2f}"
        for label in TEXT_EMOTION_LABELS
    )


def format_preferences(memory: Dict[str, Any]) -> str:
    if not memory:
        return "No known user preferences."
    return ", ".join(f"{k}={v}" for k, v in memory.items())


def build_prompt_markdown(sample: Dict[str, Any], sample_dir: Path) -> str:
    dialogue = sample.get("dialogue", [])
    memory = sample.get("memory", {})

    history, last_user = split_dialogue(dialogue)
    if not last_user:
        raise ValueError(f"Last user turn is empty for {sample_dir.name}")
    full_history = dialogue

    wav_path = sample_dir / "query.wav"
    if not wav_path.exists():
        raise FileNotFoundError(f"query.wav not found for {sample_dir.name}")

    # Emotions
    speech_emotion = analyze_speech_emotion(str(wav_path))
    text_emotion = analyze_text_emotion(last_user)
    fused_emotion = fuse_emotions(
        speech_emotion=speech_emotion,
        text_emotion=text_emotion,
        speech_weight=SPEECH_EMOTION_WEIGHT,
        text_weight=TEXT_EMOTION_WEIGHT,
    )

    # Personality
    personality_df = analyze_personality(last_user)

    prompt_text = PROMPT_TEMPLATE.format(
        conversation_history=format_conversation_history(full_history),
        personality_block=format_personality(personality_df),
        emotion_block=format_emotion_block(fused_emotion),
        preferences_block=format_preferences(memory),
    ).strip() + "\n"

    return prompt_text


def process_samples(sample_ids: List[str]) -> None:
    for sid in sample_ids:
        sample_dir = SAMPLES_DIR / sid
        try:
            sample = load_sample(sample_dir)
            prompt_md = build_prompt_markdown(sample, sample_dir)
            out_path = sample_dir / "prompt.md"
            out_path.write_text(prompt_md, encoding="utf-8")
            logger.info(f"[{sid}] prompt.md regenerated")
        except Exception as exc:
            logger.error(f"[{sid}] failed: {exc}")
            continue


def main():
    parser = argparse.ArgumentParser(description="Build prompt.md for samples using real signals.")
    parser.add_argument(
        "--sample-ids",
        nargs="*",
        default=None,
        help="Sample IDs to process (e.g., 001 002). Default: all in samples/.",
    )
    args = parser.parse_args()

    if args.sample_ids:
        sample_ids = args.sample_ids
    else:
        sample_ids = sorted([p.name for p in SAMPLES_DIR.iterdir() if p.is_dir()])

    process_samples(sample_ids)


if __name__ == "__main__":
    main()
