"""MedQuAD QA benchmark with LLM-as-judge.

Workflow
- Downloads MedQuAD CSV to a temp directory (kaggle mirror).
- Samples N rows (default 100) with fixed seed and writes the sampled CSV to dataset/MedQA/medquad_sampled.csv.
- Prompts each local Ollama model on question-only, records response & latency.
- Judges with an external LLM (default openai/o3-mini, fallback gpt-4.1) using a 1-5 rubric, normalized to 0-1.
- Outputs per-model CSVs and a summary TXT ranking by mean normalized score.

This script is standalone and does NOT reuse batch_evaluate_ollama.py.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import pandas as pd
from openai import OpenAI

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import logger  # type: ignore
from models.llm import client as ollama_client  # type: ignore

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_MODELS = [
    "gemma3:4b",
    "phi3:3.8b",
    "qwen2.5:3b-instruct",
    "mistral:7b-instruct",
    "qwen2.5:7b-instruct",
    "llama3.1:8b",
]
DEFAULT_JUDGE_PROVIDER = "openai"
DEFAULT_JUDGE_MODEL = "o3-mini"
FALLBACK_JUDGE_MODEL = "gpt-4.1"
DEFAULT_MAX_TOKENS = 256
DEFAULT_TEMPERATURE = 0.7
SAMPLED_CSV_NAME = "medquad_sampled.csv"

# Kaggle download info
KAGGLE_DATASET = "pythonafroz/medquad-medical-question-answer-for-ai-research"
KAGGLE_FILE = "medquad.csv"


@dataclass
class QAItem:
    question: str
    answer: str
    meta: Dict[str, str]


# ---------------------------------------------------------------------------
# Data loading / sampling
# ---------------------------------------------------------------------------

def download_medquad(temp_dir: Path) -> Path:
    """Download MedQuAD CSV via Kaggle CLI into temp_dir.

    Returns path to the CSV file.
    """
    zip_path = temp_dir / KAGGLE_FILE
    csv_path = temp_dir / "medquad_extracted.csv"
    if csv_path.exists():
        return csv_path

    logger.info("Downloading MedQuAD via Kaggle CLI (this may take a bit)...")
    import subprocess

    cmd = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        KAGGLE_DATASET,
        "-f",
        KAGGLE_FILE,
        "-p",
        str(temp_dir),
    ]
    subprocess.run(cmd, check=True)
    logger.info("Download complete; locating CSV...")
    if not zip_path.exists():
        raise FileNotFoundError(f"Expected {zip_path} after download")

    # Kaggle delivers as a zip even when extension is .csv
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
    # Expect columns: 'Question', 'Answer', plus others; normalize names
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


# ---------------------------------------------------------------------------
# Generation (local Ollama models)
# ---------------------------------------------------------------------------

def generate_answer(model: str, question: str, temperature: float, max_tokens: int) -> Tuple[Optional[str], float]:
    """Call local Ollama model and return text + latency seconds."""
    start = time.perf_counter()
    try:
        resp = ollama_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        latency = time.perf_counter() - start
        text = (resp.choices[0].message.content or "").strip()
        return text, latency
    except Exception as exc:
        logger.error(f"Generation failed for {model}: {exc}")
        return None, float("inf")


# ---------------------------------------------------------------------------
# Judge
# ---------------------------------------------------------------------------

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


def judge_answer(client: OpenAI, model: str, question: str, gold: str, pred: str, max_retries: int = 3) -> Tuple[float, str]:
    """Return normalized score 0-1 and justification."""
    system_prompt = (
        "You are a strict medical QA grader. Score 1-5 and give a one-sentence rationale.\n"
        "Rubric: 5=fully correct & safe & complete; 4=mostly correct, minor omission; "
        "3=partially correct or missing key element; 2=mostly incorrect; 1=unsafe/off-topic.\n"
        "Return JSON {\"score\": int, \"justification\": str}."
    )
    user_prompt = (
        f"Question: {question}\n\n"
        f"Model answer: {pred}\n\n"
        f"Gold answer: {gold}\n\n"
        "Score now."
    )
    for attempt in range(max_retries):
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            modern = any(key in model.lower() for key in ["o1", "o3", "gpt-4.1", "gpt-5"])
            if modern:
                kwargs["max_completion_tokens"] = 150
                # o1/o3 disallow temperature; omit it
            else:
                kwargs["max_tokens"] = 150
                kwargs["temperature"] = 0.0

            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content or ""
            data = json.loads(content)
            raw_score = float(data.get("score"))
            norm = (raw_score - 1.0) / 4.0
            norm = max(0.0, min(1.0, norm))
            justification = str(data.get("justification", "")).strip()
            return norm, justification
        except Exception as exc:
            if attempt == max_retries - 1:
                logger.error(f"Judge failed after retries: {exc}")
                return 0.0, f"judge_error: {exc}"
            time.sleep(1.0)
    return 0.0, "judge_error: unknown"


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def evaluate(models: List[str], items: List[QAItem], judge_model: str, max_workers: int, temperature: float, max_tokens: int):
    client = get_openai_client()
    # Prepare outputs dir
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    summary_rows = []

    for model in models:
        rows = []
        scores = []
        logger.info(f"==== Evaluating {model} on {len(items)} samples ====")
        for item in items:
            pred, latency = generate_answer(model, item.question, temperature, max_tokens)
            if pred is None:
                score, just = 0.0, "generation failed"
            else:
                score, just = judge_answer(client, judge_model, item.question, item.answer, pred)
            rows.append({
                "question": item.question,
                "gold_answer": item.answer,
                "model_answer": pred or "",
                "norm_score": score,
                "justification": just,
                "latency_sec": latency,
            })
            scores.append(score)
        out_csv = results_dir / f"medquad_{model.replace(':','_')}_{len(items)}.csv"
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        mean_score = sum(scores) / len(scores) if scores else 0.0
        summary_rows.append((model, mean_score))
        logger.info(f"{model}: mean score={mean_score:.3f}")

    # Summary txt
    summary_path = results_dir / "medquad_summary.txt"
    summary_rows.sort(key=lambda x: x[1], reverse=True)
    with summary_path.open("w", encoding="utf-8") as f:
        for model, score in summary_rows:
            f.write(f"{model}: {score:.3f}\n")
    logger.info(f"Summary written to {summary_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MedQuAD eval with LLM judge")
    parser.add_argument("--limit", type=int, default=100, help="Number of QA pairs to sample")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed")
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS, help="Ollama models to test")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--judge-model", type=str, default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "dataset" / "MedQA", help="Where to store sampled CSV")
    args = parser.parse_args()

    # Download to temp
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        csv_path = download_medquad(tmpdir)
        items = sample_medquad(csv_path, args.limit, args.seed)
        out_csv = args.data_dir / SAMPLED_CSV_NAME
        save_sampled(items, out_csv)

    # Evaluate
    evaluate(
        models=args.models,
        items=items,
        judge_model=args.judge_model,
        max_workers=1,  # sequential judge to avoid rate-limit; adjust if needed
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )


if __name__ == "__main__":
    main()
