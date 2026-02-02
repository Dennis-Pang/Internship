"""Generate answers on MedQuAD for local Ollama models (no judging).

- Downloads MedQuAD CSV to a temp dir (Kaggle CLI).
- Samples N QA pairs (default 100, seed=42) and saves to dataset/MedQA/medquad_sampled.csv.
- For each model, generates answers on question-only, records latency.
- Outputs per-model CSV under results/: medquad_gen_<model>_<n>.csv

This script is separate from medquad_eval.py (which includes judging).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import pandas as pd

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import logger  # type: ignore
from models.llm import client as ollama_client  # type: ignore

DEFAULT_MODELS = [
    "gemma3:4b",
    "phi3:3.8b",
    "qwen2.5:3b-instruct",
    "mistral:7b-instruct",
    "qwen2.5:7b-instruct",
    "llama3.1:8b",
]
DEFAULT_MAX_TOKENS = 256
DEFAULT_TEMPERATURE = 0.7
SAMPLED_CSV_NAME = "medquad_sampled.csv"

KAGGLE_DATASET = "pythonafroz/medquad-medical-question-answer-for-ai-research"
KAGGLE_FILE = "medquad.csv"

@dataclass
class QAItem:
    question: str
    answer: str
    meta: Dict[str, str]


def download_medquad(temp_dir: Path) -> Path:
    zip_path = temp_dir / KAGGLE_FILE
    csv_path = temp_dir / "medquad_extracted.csv"
    if csv_path.exists():
        return csv_path
    logger.info("Downloading MedQuAD via Kaggle CLI (this may take a bit)...")
    cmd = [
        "kaggle", "datasets", "download", "-d", KAGGLE_DATASET, "-f", KAGGLE_FILE, "-p", str(temp_dir)
    ]
    subprocess.run(cmd, check=True)
    if not zip_path.exists():
        raise FileNotFoundError(f"Expected {zip_path} after download")
    import zipfile
    if zipfile.is_zipfile(zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            inner = zf.namelist()[0]
            with zf.open(inner) as src, csv_path.open("wb") as dst:
                dst.write(src.read())
    else:
        zip_path.rename(csv_path)
    return csv_path


def sample_medquad(csv_path: Path, limit: int, seed: int) -> List[QAItem]:
    df = pd.read_csv(csv_path, encoding="latin1")
    cols = {c.lower(): c for c in df.columns}
    q_col = cols.get("question")
    a_col = cols.get("answer")
    if not q_col or not a_col:
        raise ValueError("CSV missing Question/Answer columns")
    rng = random.Random(seed)
    indices = list(range(len(df)))
    rng.shuffle(indices)
    indices = indices[:limit]
    items: List[QAItem] = []
    for idx in indices:
        row = df.iloc[idx]
        q = str(row[q_col]).strip()
        a = str(row[a_col]).strip()
        meta = {}
        for key in ("Source", "Topic", "URL", "Uri", "Synonyms"):
            if key in df.columns:
                meta[key.lower()] = str(row[key]) if not pd.isna(row[key]) else ""
        items.append(QAItem(question=q, answer=a, meta=meta))
    return items


def save_sampled(items: List[QAItem], out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["question", "answer", "meta_json"])
        for it in items:
            writer.writerow([it.question, it.answer, json.dumps(it.meta)])
    logger.info(f"Saved sampled set to {out_path}")


def generate_answer(model: str, question: str, temperature: float, max_tokens: int) -> Tuple[Optional[str], float]:
    try:
        resp = ollama_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text, 0.0
    except Exception as exc:
        logger.error(f"Generation failed for {model}: {exc}")
        return None, float("inf")


def generate_all(models: List[str], items: List[QAItem], temperature: float, max_tokens: int):
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    for model in models:
        logger.info(f"==== Generating with {model} on {len(items)} samples ====")
        out_csv = results_dir / f"medquad_gen_{model.replace(':','_')}_{len(items)}.csv"
        if out_csv.exists():
            out_csv.unlink()
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            fieldnames = ["question", "gold_answer", "model_answer"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in items:
                pred, _ = generate_answer(model, item.question, temperature, max_tokens)
                row = {
                    "question": item.question,
                    "gold_answer": item.answer,
                    "model_answer": pred or "",
                }
                writer.writerow(row)
                f.flush()
                os.fsync(f.fileno())
        logger.info(f"Saved generations to {out_csv}")


def main():
    parser = argparse.ArgumentParser(description="Generate MedQuAD answers (no judge)")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "dataset" / "MedQA")
    args = parser.parse_args()

    # Download and sample (temp download to avoid disk bloat)
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = download_medquad(Path(tmp))
        items = sample_medquad(csv_path, args.limit, args.seed)
        out_csv = args.data_dir / SAMPLED_CSV_NAME
        save_sampled(items, out_csv)

    generate_all(args.models, items, args.temperature, args.max_tokens)


if __name__ == "__main__":
    main()
