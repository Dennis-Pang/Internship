"""Groundedness (Hallucination Rate) Metric.

This module evaluates how well LLM responses avoid inventing information not
present in the input or memory. Measures factual faithfulness by extracting
factual claims and checking if they are grounded in source material.

Uses LLM-as-a-judge with Pydantic AI for structured output.

Metrics:
- Groundedness Score: 1-5 scale (5=all claims grounded, 1=mostly hallucinated)

A claim is "grounded" if it can be verified from:
- User memory profile
- User input query
- General medical knowledge (not penalized)

A claim is "hallucinated" if it:
- Contradicts memory/input
- Invents specific details not present in sources
"""

import json
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

class FactualClaim(BaseModel):
    """A single factual claim extracted from the response."""
    claim: str = Field(
        description="The factual claim or statement"
    )
    is_grounded: bool = Field(
        description="Whether this claim is grounded in memory/input (True) or hallucinated (False)"
    )
    source: str = Field(
        description="Source of grounding: 'memory', 'query', 'general_knowledge', or 'hallucination'"
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Brief explanation of the judgment"
    )


class GroundednessJudgment(BaseModel):
    """Structured output for groundedness judgment using Pydantic AI."""
    claims: List[FactualClaim] = Field(
        default_factory=list,
        description="List of factual claims extracted from the response"
    )
    groundedness_score: int = Field(
        ge=1,
        le=5,
        description="Groundedness score 1-5 (5=all claims grounded, 1=mostly hallucinated)"
    )
    explanation: str = Field(
        description="Brief explanation of the overall groundedness assessment"
    )


# ============================================================================
# LLM Judge
# ============================================================================

def judge_groundedness(
    response: str,
    query: str,
    memory: Dict[str, Any],
    provider: str = "openai",
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate groundedness of response.

    Uses Pydantic AI (instructor) for structured output enforcement.

    Args:
        response: Generated response text
        query: User input query
        memory: User memory profile
        provider: LLM provider for judging (anthropic/openai/google)
        model: Judge model name (if None, uses provider default)

    Returns:
        Dictionary with groundedness metrics
    """
    # Use default model if not specified
    if model is None:
        model = get_default_model(provider)

    if not response or not response.strip():
        logger.warning("Empty response provided to groundedness judge")
        raise ValueError("Cannot judge groundedness on empty response")

    memory_json = json.dumps(memory, indent=2)

    judge_prompt = f"""Evaluate the groundedness of a healthcare assistant's response by checking if factual claims are supported by the provided sources.

User Memory Profile:
{memory_json}

User Query:
{query}

Assistant Response:
{response}

TASK:
1. Extract all factual claims from the response (e.g., "you sleep 5.5 hours", "you have anemia", "exercise helps energy")
2. For each claim, determine if it is:
   - GROUNDED in memory (specific to this user's profile)
   - GROUNDED in query (explicitly mentioned in user's question)
   - GROUNDED in general knowledge (established medical facts, not user-specific)
   - HALLUCINATED (invented details not in sources, contradicts sources)

3. Score overall groundedness using this rubric:

RUBRIC (1-5):
5 - Fully grounded: All claims are grounded in memory/query/general knowledge, no hallucinations
4 - Mostly grounded: >80% of claims grounded, minor unsupported details
3 - Partially grounded: 50-80% of claims grounded, some invented details
2 - Mostly hallucinated: <50% of claims grounded, significant fabricated information
1 - Fully hallucinated: Most/all claims are invented or contradict sources

IMPORTANT RULES:
- General medical advice (e.g., "exercise improves energy") is GROUNDED (general_knowledge)
- User-specific details (e.g., "you sleep 5.5 hours") MUST match memory exactly to be grounded
- If response invents details not in memory (e.g., claims user exercises daily when memory says "rare"), mark as HALLUCINATED
- Empty responses are considered errors (no score)

Return:
- claims: List of FactualClaim objects with claim, is_grounded, source, explanation
- groundedness_score: int (1-5)
- explanation: Brief explanation of the overall groundedness assessment
"""

    # Get structured response via LLM router
    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=GroundednessJudgment,
        temperature=0.0,  # Use temperature=0 for more deterministic judging
        max_tokens=2000,  # More tokens needed for detailed claim analysis
    )

    logger.debug(f"Groundedness ({provider}/{model}): {judgment.groundedness_score}/5")
    logger.debug(f"Total claims: {len(judgment.claims)}")
    logger.debug(f"Explanation: {judgment.explanation}")

    return {
        "claims": [claim.model_dump() for claim in judgment.claims],
        "groundedness_score": judgment.groundedness_score,
        "explanation": judgment.explanation,
        "total_claims": len(judgment.claims),
        "grounded_claims": sum(1 for c in judgment.claims if c.is_grounded),
        "hallucinated_claims": sum(1 for c in judgment.claims if not c.is_grounded),
    }
