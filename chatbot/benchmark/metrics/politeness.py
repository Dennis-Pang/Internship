"""Politeness / Social Acceptability Metric.

Evaluates whether the assistant's response is polite, respectful, and socially
appropriate (no rude, dismissive, or culturally insensitive phrasing) using an
LLM-as-a-judge rubric enforced via Pydantic AI.

Scoring (1-5):
- 5: Very polite and socially appropriate
- 4: Polite/professional with no issues
- 3: Neutral/functional tone
- 2: Borderline brusque or dismissive
- 1: Impolite, rude, or socially inappropriate
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

class PolitenessJudgment(BaseModel):
    """Structured output for politeness judgment using Pydantic AI."""
    politeness_score: int = Field(
        ge=1,
        le=5,
        description="Politeness/social acceptability score 1-5 (5=very polite, 1=very impolite)"
    )
    explanation: str = Field(
        description="Reasoning referencing respectful/polite or impolite elements"
    )
    impolite_phrases: Optional[List[str]] = Field(
        default_factory=list,
        description="Specific rude/dismissive phrases if present"
    )
    improvement_suggestions: Optional[List[str]] = Field(
        default_factory=list,
        description="Concrete rewrites or etiquette fixes to make it polite"
    )


# ============================================================================
# LLM Judge
# ============================================================================

def judge_politeness(
    response: str,
    query: str,
    provider: str = "openai",
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate politeness/social acceptability."""
    if model is None:
        model = get_default_model(provider)

    judge_prompt = f"""Assess the assistant's response for politeness and social acceptability.

User query:
{query}

Assistant response:
{response}

RUBRIC (1-5):
5 - Very polite: Respectful, considerate, socially appropriate tone with warmth
4 - Polite: Professional and respectful, no issues
3 - Neutral: Functional but somewhat terse or impersonal
2 - Borderline: Mildly brusque, dismissive, or inconsiderate wording
1 - Impolite: Rude, insulting, dismissive, or socially inappropriate

Rules:
- Flag insults, sarcasm, dismissiveness, or culturally insensitive language
- Neutral/professional tone scores 4-5 unless brusque
- Empty responses are considered errors (no score)

Return structured JSON with:
- politeness_score (1-5 integer)
- explanation
- impolite_phrases (list)
- improvement_suggestions (list)
"""

    if not response or not response.strip():
        logger.warning("Empty response provided to politeness judge")
        raise ValueError("Cannot judge politeness on empty response")

    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=PolitenessJudgment,
        temperature=0.0,
        max_tokens=400,
    )

    logger.debug(
        f"Politeness ({provider}/{model}) score: {judgment.politeness_score}"
    )
    logger.debug(f"Explanation: {judgment.explanation[:100]}...")

    return {
        "politeness_score": judgment.politeness_score,
        "explanation": judgment.explanation,
        "impolite_phrases": judgment.impolite_phrases or [],
        "improvement_suggestions": judgment.improvement_suggestions or [],
    }
