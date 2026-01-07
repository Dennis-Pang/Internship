"""Emotional Congruence Metric.

Evaluates whether the assistant's tone aligns with the user's detected emotional
state using a rubric-based 1-5 scale enforced via Pydantic AI.

Inputs:
- Detected emotion distribution (probabilities sum to 1)
- User message text
- Assistant response text

Scoring rubric (1-5):
- 5: Tone clearly aligns with user emotions and intensity
- 4: Mostly aligned with minor mismatches
- 3: Mixed alignment; some cues addressed, some missed
- 2: Noticeable mismatch or dismissive tone
- 1: Tone clashes with user emotion or ignores signals

Metric:
- Emotional Congruence Score: Integer 1-5 (higher = better alignment)
- Aggregates: average/median/min/max/std + score distribution
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.config import logger
from .llm_router import get_structured_response, get_default_model


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class EmotionalCongruenceJudgment(BaseModel):
    """Structured output for emotional congruence judgment using Pydantic AI."""
    emotional_congruence_score: int = Field(
        ge=1,
        le=5,
        description="Emotional congruence score on a 1-5 scale (1=clashing tone, 5=clear alignment)"
    )
    explanation: str = Field(
        description="Reasoning referencing the user's emotions and how the assistant's tone matched or missed them"
    )
    matched_emotions: Optional[List[str]] = Field(
        default_factory=list,
        description="User emotions that were appropriately acknowledged or mirrored"
    )
    mismatched_emotions: Optional[List[str]] = Field(
        default_factory=list,
        description="User emotions that the assistant mishandled, ignored, or contradicted"
    )
    tone_notes: Optional[List[str]] = Field(
        default_factory=list,
        description="Notable tone choices (e.g., empathetic, dismissive, overly cheerful, calming)"
    )


# ============================================================================
# LLM Judge
# ============================================================================

def judge_emotional_congruence(
    response: str,
    query: str,
    emotion_distribution: Dict[str, float],
    provider: str = "openai",
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate emotional congruence of response.

    Uses Pydantic AI (instructor) for structured output enforcement.

    Args:
        response: Generated response text
        query: User input text
        emotion_distribution: Detected user emotion probabilities (sum to 1)
        provider: LLM provider for judging (anthropic/openai/google/ollama)
        model: Judge model name (if None, uses provider default)

    Returns:
        Dictionary with emotional congruence metrics
    """
    # Use default model if not specified
    if model is None:
        model = get_default_model(provider)

    # Handle missing distribution gracefully
    if not emotion_distribution:
        logger.warning("No emotion distribution provided; defaulting to neutral=1.0")
        emotion_distribution = {"neutral": 1.0}

    # Format emotion distribution for the prompt
    emotion_lines = "\n".join(
        f"{label}: {prob:.2f}"
        for label, prob in sorted(emotion_distribution.items(), key=lambda x: x[0])
    )

    judge_prompt = f"""You are an evaluator for emotional congruence.

Given:
Detected user emotion distribution (probabilities sum to 1):
{emotion_lines}

User message:
{query}

Assistant response:
{response}

Task:
A) Congruence score (1-5): Does the assistant's tone appropriately match the user's emotional state?
- 5: clearly aligned
- 3: somewhat aligned / mixed
- 1: tone clashes with user emotion

Rules:
- Do not infer emotions not supported by the user message or provided distribution.
- Judge the assistant's tone and emotional framing, not medical correctness.
- Consider emotional intensity (e.g., high sadness should be met with gentle, validating tone).
- Note when the assistant is overly cheerful/neutral while user signals distress, or overly negative when user is upbeat.

Return structured JSON with:
- emotional_congruence_score (int 1-5)
- explanation (why the tone matches or misses)
- matched_emotions (list)
- mismatched_emotions (list)
- tone_notes (list of brief observations)
"""

    # Handle empty response
    if not response or not response.strip():
        logger.warning("Empty response provided to emotional congruence judge")
        raise ValueError("Cannot judge emotional congruence on empty response")

    # Get structured response via LLM router
    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=EmotionalCongruenceJudgment,
        temperature=0.0,  # Deterministic judging
        max_tokens=400,
    )

    logger.debug(
        f"Emotional Congruence ({provider}/{model}) score: {judgment.emotional_congruence_score}/5"
    )
    logger.debug(f"Explanation: {judgment.explanation[:100]}...")

    return {
        "emotional_congruence_score": judgment.emotional_congruence_score,
        "explanation": judgment.explanation,
        "matched_emotions": judgment.matched_emotions or [],
        "mismatched_emotions": judgment.mismatched_emotions or [],
        "tone_notes": judgment.tone_notes or [],
    }
