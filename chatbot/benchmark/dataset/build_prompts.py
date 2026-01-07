"""Build per-sample prompt.md files using real signals (speech/text emotion + personality).

For each sample directory:
- Load sample.json (expects fields: id, dialogue, memory, etc.)
- Use the last user turn as USER_MESSAGE
- Run speech2emotion on query.wav and text2emotion on the last user text
- Fuse emotions using chatbot_cli weights
- Run personality analysis on the last user text
- Render a Markdown prompt in the latest format and save to prompt.md

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

from modules.config import logger, SPEECH_EMOTION_WEIGHT, TEXT_EMOTION_WEIGHT  # noqa: E402
from modules.emotion import TEXT_EMOTION_LABELS  # noqa: E402
from chatbot_cli import (  # noqa: E402
    analyze_speech_emotion,
    analyze_text_emotion,
    analyze_personality,
    fuse_emotions,
)

SAMPLES_DIR = Path(__file__).parent / "samples"


PROMPT_TEMPLATE = """You are Hackcelerate — a warm, practical health companion. You talk like a real person: brief, clear, natural.

GOAL
Reply to USER_MESSAGE using the provided context. Use EMOTION_LOGITS and USER_PERSONALITY to adjust tone naturally.
Write only the reply text — no preambles, no meta commentary.

USING KNOWN_PREFERENCES
- These are facts you already know about this user
- Reference them directly when relevant to USER_MESSAGE (e.g., "your insulin," "that lunch dose")
- Use them to make your reply specific and personalized
- Don't mention preferences that don't connect to the current message
- If unsure about a detail, ask one quick question instead of guessing

STYLE
- 2–5 sentences, conversational
- If user wants improvement → offer 1–2 small steps
- If user is sharing → respond supportively, don't push
- No meta talk about context or memory

---

EXAMPLES

Ex1:
EMOTION: frustrated=0.8, sad=0.2
KNOWN_PREFERENCES: medication=insulin, struggle=remembering_lunch_dose
USER: "Forgot my insulin again at work"
REPLY: "That lunch dose is tricky. Does your work routine vary a lot day to day?"

Ex2:
EMOTION: happy=0.7, excited=0.2
KNOWN_PREFERENCES: goal=walking_habit, milestone=walked_3_days_straight
USER: "Hit 3 days of walking!"
REPLY: "Nice! How's your energy feeling? Notice any difference yet?"

Ex3:
EMOTION: neutral=0.75, fear=0.15
KNOWN_PREFERENCES: concern=blood_pressure, last_reading=145/92
USER: "My BP was high again this morning"
REPLY: "145/92. Was it right after waking up, or later in the morning?"

---

### CONVERSATION_HISTORY
{conversation_history}

### USER_PERSONALITY
{personality_block}

### EMOTION_LOGITS
{emotion_block}

### KNOWN_PREFERENCES
{preferences_block}

### USER_MESSAGE
{user_message}

Write only the reply.
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
    return "\n".join(
        f"{row['theta']}: {row['r']:.2f}"
        for _, row in personality_df.iterrows()
    )


def format_emotion_block(fused_emotion: Dict[str, float]) -> str:
    return "\n".join(
        f"{label}: {fused_emotion.get(label, 0.0):.2f}"
        for label in TEXT_EMOTION_LABELS
    )


def format_preferences(memory: Dict[str, Any]) -> str:
    if not memory:
        return "No known user preferences."
    return "\n".join(f"{k}: {v}" for k, v in memory.items())


def build_prompt_markdown(sample: Dict[str, Any], sample_dir: Path) -> str:
    dialogue = sample.get("dialogue", [])
    memory = sample.get("memory", {})

    history, last_user = split_dialogue(dialogue)
    if not last_user:
        raise ValueError(f"Last user turn is empty for {sample_dir.name}")

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
        conversation_history=format_conversation_history(history),
        personality_block=format_personality(personality_df),
        emotion_block=format_emotion_block(fused_emotion),
        preferences_block=format_preferences(memory),
        user_message=last_user,
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
