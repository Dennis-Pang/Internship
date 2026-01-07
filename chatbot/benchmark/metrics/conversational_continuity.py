"""Conversational Continuity Metric.

Evaluates whether the assistant's reply maintains context, resolves references,
and stays coherent with the preceding dialogue using an LLM-as-a-judge rubric.

Scoring (1-5):
- 5: Excellent continuity; correctly references prior turns and resolves entities/topics
- 4: Good continuity with minor gaps
- 3: Adequate/on-topic but some missed references or vagueness
- 2: Weak continuity with inconsistencies or missed context
- 1: Broken continuity; ignores or contradicts prior turns

Inputs:
- conversation history (list of messages with role/content), last turn is the user message to respond to
- assistant response to evaluate
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

class ContinuityJudgment(BaseModel):
    """Structured output for conversational continuity judgment."""
    continuity_score: int = Field(
        ge=1,
        le=5,
        description="Conversational continuity score 1-5 (5=excellent continuity, 1=broken)"
    )
    explanation: str = Field(
        description="Reasoning referencing how the reply used (or missed) prior context"
    )
    continuity_strengths: Optional[List[str]] = Field(
        default_factory=list,
        description="Examples of good continuity (resolved references, kept topic)"
    )
    continuity_breaks: Optional[List[str]] = Field(
        default_factory=list,
        description="Breaks or errors (ignored context, wrong entity, contradiction)"
    )


# ============================================================================
# Helpers
# ============================================================================

def _format_conversation(conversation: List[Dict[str, str]]) -> str:
    """Format conversation messages into a readable block."""
    lines = []
    for msg in conversation:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "Unavailable"


# ============================================================================
# LLM Judge
# ============================================================================

def judge_conversational_continuity(
    conversation: List[Dict[str, str]],
    response: str,
    provider: str = "openai",
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate conversational continuity of a response."""
    if model is None:
        model = get_default_model(provider)

    # Ensure conversation is present
    if not conversation:
        logger.warning("No conversation provided; treating as single-turn query")
        conversation = []

    conversation_str = _format_conversation(conversation)

    judge_prompt = f"""Assess conversational continuity for the assistant's reply.

Conversation history (last user turn is the one being answered):
{conversation_str}

Assistant response:
{response}

RUBRIC (1-5):
5 - Excellent: Perfectly references prior turns, resolves pronouns/entities, maintains topic and commitments
4 - Good: Strong continuity with minor gaps in callbacks or context
3 - Adequate: On-topic but some missing references or vague callbacks
2 - Weak: Partial continuity with inconsistencies or missed context
1 - Broken: Ignores context, contradicts prior turns, answers unrelatedly, or mis-attributes speakers/entities

Rules:
- Check if references (people, symptoms, plans) align with prior turns
- Penalize introducing new, irrelevant topics or contradicting earlier info
- Empty/non-responsive answers score 1 (no continuity demonstrated)

Return structured JSON with:
- continuity_score (1-5 integer)
- explanation
- continuity_strengths (list)
- continuity_breaks (list)
"""

    if not response or not response.strip():
        logger.warning("Empty response provided to conversational continuity judge")
        raise ValueError("Cannot judge conversational continuity on empty response")

    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=ContinuityJudgment,
        temperature=0.0,
        max_tokens=400,
    )

    logger.debug(
        f"Conversational Continuity ({provider}/{model}) score: {judgment.continuity_score}"
    )
    logger.debug(f"Explanation: {judgment.explanation[:100]}...")

    return {
        "continuity_score": judgment.continuity_score,
        "explanation": judgment.explanation,
        "continuity_strengths": judgment.continuity_strengths or [],
        "continuity_breaks": judgment.continuity_breaks or [],
    }
