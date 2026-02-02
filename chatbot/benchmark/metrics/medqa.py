"""MedQA Factual Consistency Metric.

Evaluates whether the assistant's response is factually consistent with
the ground truth answer for medical QA tasks on a 1-5 rubric.

Scoring rubric (1-5):
- 5: Fully consistent; response aligns with ground truth in all key facts
- 4: Mostly consistent; minor discrepancies that don't affect core accuracy
- 3: Partially consistent; some correct facts but notable errors or omissions
- 2: Mostly inconsistent; significant factual errors or misalignment
- 1: Not consistent; response contradicts or ignores ground truth
"""

import sys
from pathlib import Path
from typing import Dict, Any

from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import logger
from .llm_router import get_structured_response
from .judge_config import get_judge_model


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class MedQAJudgment(BaseModel):
    """Structured output for MedQA factual consistency judgment."""
    medqa_score: int = Field(
        ge=1,
        le=5,
        description="Factual consistency score on a 1-5 scale (1=not consistent, 5=fully consistent)"
    )


# ============================================================================
# LLM Judge
# ============================================================================

def judge_medqa(
    response: str,
    gold_answer: str,
    question: str,
    provider: str = None,
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate factual consistency of response against ground truth.

    Args:
        response: Generated response text (model answer)
        gold_answer: Ground truth answer
        question: Original question/query
        provider: LLM provider for judging (anthropic/openai/google/ollama)
        model: Judge model name (if None, uses config default for medqa)

    Returns:
        Dictionary with MedQA metrics:
        - medqa_score_raw: raw score 1-5
        - medqa_score_norm: normalized score 0-1
    """
    if provider is None and model is None:
        provider, model = get_judge_model("medqa")
    elif (provider is None) != (model is None):
        raise ValueError("medqa override requires both provider and model")

    judge_prompt = f"""Evaluate the factual consistency of the model's answer against the ground truth answer for a medical QA task.

Question:
{question}

Model Answer:
{response}

Ground Truth Answer:
{gold_answer}

Task: Assign a factual consistency score (1-5) using this rubric:
- 5: Fully consistent; the response accurately reflects all key facts from the ground truth answer.
- 4: Mostly consistent; minor discrepancies or omissions that don't affect the core medical accuracy.
- 3: Partially consistent; some correct facts but notable errors, omissions, or misleading information.
- 2: Mostly inconsistent; significant factual errors or substantial misalignment with ground truth.
- 1: Not consistent; response contradicts the ground truth or provides completely wrong information.

Rules:
- Focus on factual accuracy, not writing style or phrasing differences.
- Medical terminology variations are acceptable if the meaning is preserved.
- Partial answers that are correct but incomplete should score 3-4.
- Completely wrong or dangerous medical information should score 1-2.
- If the response is empty or non-responsive, score = 1.

Return with medqa_score (1-5 integer).
"""

    if not response or not response.strip():
        logger.warning("Empty response provided to MedQA judge")
        return {"medqa_score_raw": 1.0, "medqa_score_norm": 0.0}

    try:
        judgment = get_structured_response(
            provider=provider,
            model=model,
            messages=[{"role": "user", "content": judge_prompt}],
            response_model=MedQAJudgment,
            temperature=0.0,
            max_tokens=4096,
        )

        score = float(judgment.medqa_score)
        logger.debug(f"MedQA ({provider}/{model}) score: {score}/5")

        return {
            "medqa_score_raw": score,
            "medqa_score_norm": (score - 1.0) / 4.0,
        }

    except Exception as exc:
        logger.error(f"MedQA judge error ({provider}/{model}): {exc}")
        return {"medqa_score_raw": 1.0, "medqa_score_norm": 0.0}
