"""Persona Consistency Metric.

Evaluates how well the assistant's response aligns with the provided Big Five
personality profile (scores 0-1 per trait; not a probability distribution).

Scoring rubric (1-5):
- 5: Strong alignment; advice/tone clearly tailored to key traits
- 4: Generally aligned with minor misses
- 3: Mixed; some trait alignment, some ignored
- 2: Weak alignment; mostly generic or occasionally conflicting
- 1: Conflicts with or ignores the provided persona

Outputs:
- persona_consistency_score (1-5 integer)
- explanation (why the score was assigned)
- matched_traits: traits well-respected/leveraged
- mismatched_traits: traits that were ignored or contradicted
- tailoring_notes: observations about how the response used personality context
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

class PersonaConsistencyJudgment(BaseModel):
    """Structured output for persona consistency judgment using Pydantic AI."""
    persona_consistency_score: int = Field(
        ge=1,
        le=5,
        description="Persona consistency score on a 1-5 scale (1=conflicts/ignores, 5=well-tailored)"
    )
    explanation: str = Field(
        description="Reasoning referencing the provided personality traits and how the response aligned or conflicted"
    )
    matched_traits: Optional[List[str]] = Field(
        default_factory=list,
        description="Traits that were respected, leveraged, or aligned with"
    )
    mismatched_traits: Optional[List[str]] = Field(
        default_factory=list,
        description="Traits that were ignored or contradicted"
    )
    tailoring_notes: Optional[List[str]] = Field(
        default_factory=list,
        description="Notable tailoring choices (e.g., structured advice for conscientiousness, reassuring tone for neuroticism)"
    )


# ============================================================================
# Helpers
# ============================================================================

def _format_personality(personality: List[Dict[str, Any]]) -> str:
    """Format personality list into readable lines."""
    lines = []
    for item in personality:
        trait = item.get("trait")
        score = item.get("score")
        if trait is None or score is None:
            continue
        try:
            score_val = float(score)
        except Exception:
            score_val = score
        lines.append(f"{trait}: {score_val}")
    return "\n".join(lines) if lines else "Unavailable"


# ============================================================================
# LLM Judge
# ============================================================================

def judge_persona_consistency(
    response: str,
    query: str,
    personality: List[Dict[str, Any]],
    provider: str = "openai",
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate persona consistency of response.

    Uses Pydantic AI (instructor) for structured output enforcement.

    Args:
        response: Generated response text
        query: User input text
        personality: List of {trait, score} with scores in [0, 1]
        provider: LLM provider for judging (anthropic/openai/google/ollama)
        model: Judge model name (if None, uses provider default)

    Returns:
        Dictionary with persona consistency metrics
    """
    if model is None:
        model = get_default_model(provider)

    if not personality:
        logger.warning("No personality provided; using empty profile")

    personality_str = _format_personality(personality)

    judge_prompt = f"""Evaluate how well the assistant's response aligns with the provided Big Five personality profile.

Personality (scores 0-1, not a probability distribution):
{personality_str}

User message:
{query}

Assistant response:
{response}

Task: Assign a persona consistency score (1-5) using this rubric:
- 5: Response shows some consideration of personality traits or adapts tone appropriately.
- 4: Response is generally appropriate and doesn't conflict with major traits.
- 3: Neutral response that doesn't strongly align or conflict with the profile.
- 2: Response seems to ignore personality or has minor conflicts with traits.
- 1: Response clearly conflicts with multiple key traits or is completely inappropriate.

Rules:
- Give credit for any reasonable personalization attempt or appropriate tone.
- Consider generic but helpful responses as acceptable (score 3-4).
- Only penalize responses that actively conflict with personality traits.
- Acknowledge that brief responses may not show personalization but can still be appropriate.
- Empty/non-responsive answers score 1.

Return structured JSON with:
- persona_consistency_score (1-5 integer)
- explanation
- matched_traits (list)
- mismatched_traits (list)
- tailoring_notes (list)
"""

    if not response or not response.strip():
        logger.warning("Empty response provided to persona consistency judge")
        raise ValueError("Cannot judge persona consistency on empty response")

    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=PersonaConsistencyJudgment,
        temperature=0.0,
        max_tokens=1000,  # Increased for detailed personality analysis
    )

    logger.debug(
        f"Persona Consistency ({provider}/{model}) score: {judgment.persona_consistency_score}/5"
    )
    logger.debug(f"Explanation: {judgment.explanation[:100]}...")

    return {
        "persona_consistency_score": judgment.persona_consistency_score,
        "explanation": judgment.explanation,
        "matched_traits": judgment.matched_traits or [],
        "mismatched_traits": judgment.mismatched_traits or [],
        "tailoring_notes": judgment.tailoring_notes or [],
    }
