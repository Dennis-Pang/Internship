"""Batch Evaluation for Local Ollama Models.

This script:
1. Reads all samples from dataset/samples/
2. Generates responses using LOCAL Ollama models (gemma3:4b, phi3:3.8b, qwen2.5:3b-instruct)
3. Evaluates with all 12 metrics using CLOUD API judge models (auto-selected)
4. Saves results as CSV: {model_name}_{num_samples}.csv
5. Auto-generates TXT summary: {model_name}_{num_samples}_summary.txt

Key Features:
- Local Ollama: Generate responses (fast, no API cost)
- Cloud API: Judge evaluation (parallel, best models)
- Auto-select judge models: Each metric uses optimal model (Claude Opus 4.5, GPT-4o, Gemini 2.0, etc.)
- Parallel evaluation: All 12 metrics run concurrently (60s instead of 240s)
- TXT summary: Human-readable summary with rankings and score distributions

Usage:
    # Evaluate all 100 samples with all 3 models (recommended)
    python batch_evaluate_ollama.py

    # Evaluate only first 10 samples (quick test)
    python batch_evaluate_ollama.py --limit 10

    # Evaluate specific models
    python batch_evaluate_ollama.py --models gemma3:4b phi3:3.8b

    # Adjust parallelism (default: 12 workers for 12 metrics)
    python batch_evaluate_ollama.py --max-workers 12

    # Disable parallel evaluation (debug mode)
    python batch_evaluate_ollama.py --no-parallel
"""

import argparse
import json
import csv
import re
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import traceback
from datetime import datetime

# Load .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.config import logger
from modules.llm import client as ollama_client

# Import metrics
from metrics import simplified_metrics as metrics


# ============================================================================
# Sample Loading
# ============================================================================

def load_sample(sample_id: int) -> Optional[Dict[str, Any]]:
    """Load a single sample from dataset.

    Args:
        sample_id: Sample ID (1-100)

    Returns:
        Dictionary with keys: id, prompt_text, sample_data, context_data
    """
    sample_dir = Path(__file__).parent / "dataset" / "samples" / f"{sample_id:03d}"

    if not sample_dir.exists():
        logger.warning(f"Sample {sample_id:03d} does not exist")
        return None

    sample_file = sample_dir / "sample.json"
    prompt_file = sample_dir / "prompt.md"
    context_file = sample_dir / "context.json"

    if not sample_file.exists() or not prompt_file.exists() or not context_file.exists():
        logger.warning(f"Sample {sample_id:03d} missing required files")
        return None

    try:
        with open(sample_file, 'r') as f:
            sample_data = json.load(f)

        with open(prompt_file, 'r') as f:
            prompt_text = f.read().strip()

        with open(context_file, 'r') as f:
            context_data = json.load(f)

        # Extract query from context.json USER_MESSAGE
        query = context_data.get("USER_MESSAGE", "").strip()

        return {
            "id": sample_data.get("id", f"{sample_id:03d}"),
            "prompt_text": prompt_text,
            "sample_data": sample_data,
            "context_data": context_data,
            "query": query,
        }

    except Exception as e:
        logger.error(f"Failed to load sample {sample_id:03d}: {e}")
        return None


# ============================================================================
# Response Generation with Local Ollama
# ============================================================================

def generate_response_ollama(
    prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 256,
) -> Optional[str]:
    """Generate response from local Ollama.

    Args:
        prompt: Full prompt text
        model: Model name (e.g., gemma3:4b)
        temperature: Sampling temperature
        max_tokens: Max tokens to generate

    Returns:
        Generated response text, or None if failed
    """
    try:
        response = ollama_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Failed to generate response with {model}: {e}")
        traceback.print_exc()
        return None


# ============================================================================
# Parse Context from Sample
# ============================================================================

def parse_context_from_sample(sample: Dict[str, Any]) -> Dict[str, Any]:
    """Parse personality, emotion, memory from sample data.

    Args:
        sample: Sample data from load_sample()

    Returns:
        Dictionary with: personality, emotion, memory, dialogue, must_use_keys, must_not_use_keys
    """
    sample_data = sample["sample_data"]
    context_data = sample.get("context_data", {})

    # Extract personality from context.json
    # Format: "Extraversion: 0.41\nNeuroticism: 0.55\n..."
    personality = []
    personality_str = context_data.get("USER_PERSONALITY", "")
    if personality_str:
        # Parse "Extraversion: 0.41\nNeuroticism: 0.55\n..."
        for trait_match in re.finditer(r"(\w+):\s*([\d.]+)", personality_str):
            trait = trait_match.group(1)
            score = float(trait_match.group(2))
            personality.append({"trait": trait, "score": score})

    # Extract emotion from context.json
    # Format: "anger: 0.00\ndisgust: 0.00\n..."
    emotion = {}
    emotion_str = context_data.get("EMOTION_LOGITS", "")
    if emotion_str:
        # Parse "anger: 0.00\ndisgust: 0.00\n..."
        for emotion_kv in re.finditer(r"(\w+):\s*([\d.]+)", emotion_str):
            emotion_name = emotion_kv.group(1)
            score = float(emotion_kv.group(2))
            emotion[emotion_name] = score

    # Get data from sample.json (already loaded)
    memory = sample_data.get("memory", {})
    dialogue = sample_data.get("dialogue", [])
    must_use_keys = sample_data.get("must_use_keys", [])
    must_not_use_keys = sample_data.get("must_not_use_keys", [])

    return {
        "personality": personality,
        "emotion": emotion,
        "memory": memory,
        "dialogue": dialogue,
        "must_use_keys": must_use_keys,
        "must_not_use_keys": must_not_use_keys,
    }


# ============================================================================
# Evaluate All Metrics
# ============================================================================

def evaluate_all_metrics(
    response: str,
    query: str,
    context: Dict[str, Any],
    judge_provider: str = None,
    judge_model: str = None,
    parallel: bool = True,
    max_workers: int = 12,
) -> Dict[str, float]:
    """Evaluate response with all 12 metrics using cloud API judges.

    Judge Model Selection (Auto):
    - persona_consistency: Claude Opus 4.5 (best instruction following)
    - emotional_congruence: GPT-4o (highest Sentient score)
    - memory_utilization: Claude Opus 4.5 (precision in logic)
    - relevance: Gemini 2.0 Flash (best conversational understanding)
    - coherence: GPT-4o (best MMLU 88.7%)
    - helpfulness: Claude Opus 4.5 (#1 instruction following)
    - empathy: GPT-4o (highest emotional intelligence)
    - politeness: GPT-4o (best social cognition)
    - safety: Claude Opus 4.5 (Anthropic AI safety focus)
    - logical_consistency: GPT-5.2 (perfect AIME 2025)
    - conversational_continuity: Gemini 2.0 Flash (#1 overall 1501 Elo)
    - groundedness: Claude Opus 4.5 (low hallucination rate)

    Args:
        response: Generated response text
        query: User query
        context: Parsed context (personality, emotion, memory, etc.)
        judge_provider: Override judge provider (None = auto-select)
        judge_model: Override judge model (None = auto-select)
        parallel: Use parallel execution (default: True, recommended for cloud API)
        max_workers: Number of parallel workers (default: 12, one per metric)

    Returns:
        Dictionary mapping metric names to scores
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    scores = {}

    # Define metric evaluation tasks
    # Note: Use closures with default arguments to avoid late binding issues
    def make_task(fn):
        return lambda: fn()

    tasks = []

    # 1. Persona Consistency (requires personality)
    if context["personality"]:
        tasks.append(("persona_consistency", make_task(
            lambda p=context["personality"]: metrics.persona_consistency(
                response, query, p, judge_provider, judge_model
            )
        )))

    # 2. Emotional Congruence (requires emotion)
    if context["emotion"]:
        tasks.append(("emotional_congruence", make_task(
            lambda e=context["emotion"]: metrics.emotional_congruence(
                response, query, e, judge_provider, judge_model
            )
        )))

    # 3. Memory Utilization (requires memory + must_use/must_not keys)
    if context["memory"]:
        tasks.append(("memory_utilization", make_task(
            lambda m=context["memory"], mu=context["must_use_keys"], mn=context["must_not_use_keys"]:
            metrics.memory_utilization(response, query, m, mu, mn, judge_provider, judge_model)
        )))

    # 4. Relevance (LLM judge)
    tasks.append(("relevance", make_task(
        lambda: metrics.relevance(response, query, judge_provider, judge_model)
    )))

    # 5. Coherence
    tasks.append(("coherence", make_task(
        lambda: metrics.coherence(response, query, judge_provider, judge_model)
    )))

    # 6. Helpfulness
    tasks.append(("helpfulness", make_task(
        lambda: metrics.helpfulness(response, query, judge_provider, judge_model)
    )))

    # 7. Empathy
    tasks.append(("empathy", make_task(
        lambda: metrics.empathy(response, query, judge_provider, judge_model)
    )))

    # 8. Politeness
    tasks.append(("politeness", make_task(
        lambda: metrics.politeness(response, query, judge_provider, judge_model)
    )))

    # 9. Safety
    tasks.append(("safety", make_task(
        lambda: metrics.safety(response, query, judge_provider, judge_model)
    )))

    # 10. Logical Consistency
    tasks.append(("logical_consistency", make_task(
        lambda: metrics.logical_consistency(response, query, judge_provider, judge_model)
    )))

    # 11. Conversational Continuity (requires dialogue history)
    if context["dialogue"]:
        tasks.append(("conversational_continuity", make_task(
            lambda d=context["dialogue"]: metrics.conversational_continuity(
                response, query, d, judge_provider, judge_model
            )
        )))

    # 12. Groundedness (requires memory)
    if context["memory"]:
        tasks.append(("groundedness", make_task(
            lambda m=context["memory"]: metrics.groundedness(
                response, query, m, judge_provider, judge_model
            )
        )))

    # Execute tasks
    if parallel and len(tasks) > 1:
        # Parallel execution
        logger.info(f"Evaluating {len(tasks)} metrics in parallel (max_workers={max_workers})...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_metric = {executor.submit(task_fn): metric_name for metric_name, task_fn in tasks}

            for future in as_completed(future_to_metric):
                metric_name = future_to_metric[future]
                scores[metric_name] = future.result()
                logger.info(f"✓ {metric_name}: {scores[metric_name]:.2f}")
    else:
        # Serial execution (fallback)
        logger.info(f"Evaluating {len(tasks)} metrics serially...")
        for metric_name, task_fn in tasks:
            scores[metric_name] = task_fn()
            logger.info(f"✓ {metric_name}: {scores[metric_name]:.2f}")

    return scores


# ============================================================================
# Main Evaluation Loop
# ============================================================================

def run_batch_evaluation(
    models: List[str],
    start: int = 1,
    end: int = 100,
    judge_provider: str = None,
    judge_model: str = None,
    output_dir: str = "results",
    parallel: bool = True,
    max_workers: int = 4,
):
    """Run batch evaluation on specified models and sample range.

    Args:
        models: List of Ollama model names
        start: Start sample ID (inclusive)
        end: End sample ID (inclusive)
        judge_provider: Judge model provider (None = auto-select best)
        judge_model: Judge model name (None = auto-select best)
        output_dir: Directory to save results
    """
    output_path = Path(__file__).parent / output_dir
    output_path.mkdir(exist_ok=True)

    num_samples = end - start + 1

    # All metric names (12 metrics)
    metric_names = [
        "persona_consistency",
        "emotional_congruence",
        "memory_utilization",
        "relevance",
        "coherence",
        "helpfulness",
        "empathy",
        "politeness",
        "safety",
        "logical_consistency",
        "conversational_continuity",
        "groundedness",
    ]

    logger.info(f"Starting batch evaluation")
    logger.info(f"Models: {', '.join(models)}")
    logger.info(f"Sample range: {start} - {end}")
    logger.info(f"Num samples: {num_samples}")
    logger.info(f"Judge: {judge_provider}/{judge_model if judge_provider else 'Auto-select (best cloud APIs)'}")
    logger.info(f"Parallel execution: {parallel} (max_workers={max_workers if parallel else 'N/A'})")

    for model in models:
        logger.info(f"\n{'='*80}")
        logger.info(f"Evaluating model: {model}")
        logger.info(f"{'='*80}")

        model_safe_name = model.replace("/", "_").replace(":", "_")
        csv_file = output_path / f"{model_safe_name}_{num_samples}.csv"
        fieldnames = ["sample_id", "query", "response"] + metric_names
        all_results = []

        # Open CSV file for streaming writes
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            f.flush()  # Flush header immediately

            # Process each sample
            for sample_id in range(start, end + 1):
                logger.info(f"\n{'-'*60}")
                logger.info(f"Processing sample {sample_id:03d}/{end:03d}")
                logger.info(f"{'-'*60}")

                try:
                    # Load sample
                    sample = load_sample(sample_id)
                    if not sample:
                        logger.warning(f"Skipping sample {sample_id:03d}")
                        continue

                    # Generate response
                    logger.info(f"Generating response with {model}...")
                    response = generate_response_ollama(sample["prompt_text"], model)
                    if not response:
                        logger.error(f"Failed to generate response for sample {sample_id:03d}")
                        continue

                    logger.info(f"Response preview: {response[:100]}...")

                    # Parse context
                    context = parse_context_from_sample(sample)

                    # Evaluate metrics
                    logger.info("Evaluating metrics...")
                    scores = evaluate_all_metrics(
                        response, sample["query"], context,
                        judge_provider, judge_model,
                        parallel=parallel,
                        max_workers=max_workers
                    )

                    # Build result
                    result = {
                        "sample_id": sample["id"],
                        "query": sample["query"],
                        "response": response,
                        **scores  # Unpack all metric scores
                    }
                    all_results.append(result)

                    # Write row to CSV immediately
                    row = {
                        "sample_id": result["sample_id"],
                        "query": result["query"],
                        "response": result["response"],
                    }
                    for metric in metric_names:
                        row[metric] = result.get(metric, None)

                    writer.writerow(row)
                    f.flush()  # Force write to disk immediately

                    logger.info(f"✓ Sample {sample_id:03d} saved to CSV")
                    logger.info(f"Sample {sample_id:03d} scores: {scores}")

                except Exception as exc:
                    logger.error(f"Failed on sample {sample_id:03d}: {exc}")
                    traceback.print_exc()

                    # Write error row to CSV to maintain sample order
                    error_row = {
                        "sample_id": f"{sample_id:03d}",
                        "query": "ERROR",
                        "response": f"Error: {str(exc)}",
                    }
                    for metric in metric_names:
                        error_row[metric] = None

                    writer.writerow(error_row)
                    f.flush()
                    continue

        # Summary statistics
        if all_results:
            logger.info(f"\n✓ Completed {len(all_results)} samples for {model}")
            logger.info(f"✓ Results saved to: {csv_file}")
            print_summary_statistics(all_results, metric_names, model)
        else:
            logger.error(f"No successful results for model {model}")

    # Generate comparison TXT after all models are done
    try:
        from generate_comparison import generate_comparison_txt
        comparison_file = generate_comparison_txt()
        logger.info(f"\n✓ Model comparison saved to: {comparison_file}")
    except Exception as e:
        logger.warning(f"Failed to generate comparison TXT: {e}")


def print_summary_statistics(results: List[Dict], metric_names: List[str], model: str):
    """Print summary statistics for all metrics."""
    import numpy as np

    logger.info(f"\n{'='*80}")
    logger.info(f"SUMMARY STATISTICS: {model}")
    logger.info(f"{'='*80}")
    logger.info(f"Total samples: {len(results)}")

    for metric in metric_names:
        scores = [r.get(metric) for r in results if r.get(metric) is not None]
        if scores:
            avg = np.mean(scores)
            std = np.std(scores)
            min_val = np.min(scores)
            max_val = np.max(scores)
            logger.info(f"{metric:30s}: {avg:.2f} ± {std:.2f} (min: {min_val:.2f}, max: {max_val:.2f})")
        else:
            logger.info(f"{metric:30s}: No data")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Evaluation for Local Ollama Models")

    parser.add_argument(
        "--models",
        nargs="+",
        default=["gemma3:4b", "phi3:3.8b", "qwen2.5:3b-instruct"],
        help="Ollama model names (default: gemma3:4b phi3:3.8b qwen2.5:3b-instruct)"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Start sample ID (default: 1)"
    )
    parser.add_argument(
        "--end",
        type=int,
        default=100,
        help="End sample ID (default: 100)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of samples (shortcut for --end)"
    )
    parser.add_argument(
        "--judge-provider",
        choices=["openai", "anthropic", "google", "ollama"],
        help="Judge model provider (default: auto-select best models)"
    )
    parser.add_argument(
        "--judge-model",
        help="Judge model name (e.g., gpt-4o-mini, gemma3:7b)"
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Output directory (default: results)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel metric evaluation (slower but safer)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=12,
        help="Max parallel workers for metric evaluation (default: 12, one per metric)"
    )

    args = parser.parse_args()

    # Handle --limit shortcut
    if args.limit:
        args.end = args.start + args.limit - 1

    run_batch_evaluation(
        models=args.models,
        start=args.start,
        end=args.end,
        judge_provider=args.judge_provider,
        judge_model=args.judge_model,
        output_dir=args.output_dir,
        parallel=not args.no_parallel,
        max_workers=args.max_workers,
    )
