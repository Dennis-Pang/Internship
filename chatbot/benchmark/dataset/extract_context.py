"""
Extract key sections from the first 10 sample prompts into a consolidated JSON.
"""

import json
import re
from pathlib import Path
from typing import Dict, List


SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
TARGET_IDS = [f"{i:03d}" for i in range(1, 11)]
FIELDS = ["USER_PERSONALITY", "EMOTION_LOGITS", "KNOWN_PREFERENCES", "USER_MESSAGE"]


def extract_sections(text: str) -> Dict[str, str]:
    """Pull section bodies for target headings from a prompt file."""
    sections: Dict[str, List[str]] = {}
    current: str | None = None
    buffer: List[str] = []

    for line in text.splitlines():
        heading = re.match(r"^###\s+([A-Z_]+)", line.strip())
        if heading:
            if current in FIELDS:
                sections[current] = buffer.copy()
            current = heading.group(1)
            buffer = []
        elif current:
            buffer.append(line)

    if current in FIELDS:
        sections[current] = buffer.copy()

    # Join buffered lines back into text blocks
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def main() -> None:
    for sample_id in TARGET_IDS:
        prompt_path = SAMPLES_DIR / sample_id / "prompt.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing prompt file: {prompt_path}")

        text = prompt_path.read_text(encoding="utf-8")
        sections = extract_sections(text)

        missing = [f for f in FIELDS if f not in sections]
        if missing:
            raise ValueError(f"Missing sections {missing} in {prompt_path}")

        data = {field: sections[field] for field in FIELDS}

        output_path = prompt_path.parent / "context.json"
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
