"""Helpfulness Metric.

Evaluates whether the assistant's response meaningfully addresses the user's
need and provides actionable, relevant guidance on a 1-5 rubric.

Scoring rubric (1-5):
- 5: Direct, accurate, actionable, covers key needs with clear next steps
- 4: Mostly helpful, minor gaps, generally actionable
- 3: Partially helpful/mixed; some relevant guidance but notable omissions
- 2: Limited usefulness; vague, generic, or misses key need
- 1: Not helpful or off-topic; fails to address the user's need

Outputs:
- helpfulness_score (1-5 integer)
- explanation (why the score was assigned)
- missing_info (optional list of gaps or clarifications needed)
- suggested_followups (optional list of next steps/questions)
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

class HelpfulnessJudgment(BaseModel):
    """Structured output for helpfulness judgment using Pydantic AI."""
    helpfulness_score: int = Field(
        ge=1,
        le=5,
        description="Helpfulness score on a 1-5 scale (1=not helpful, 5=highly helpful and actionable)"
    )
    explanation: str = Field(
        description="Reasoning referencing how well the response meets the user's need"
    )
    missing_info: Optional[List[str]] = Field(
        default_factory=list,
        description="Key gaps or clarifications that would improve the response"
    )
    suggested_followups: Optional[List[str]] = Field(
        default_factory=list,
        description="Concrete follow-up steps or questions to better assist the user"
    )


# ============================================================================
# LLM Judge
# ============================================================================

def judge_helpfulness(
    response: str,
    query: str,
    provider: str = "openai",
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate helpfulness of response.

    Uses Pydantic AI (instructor) for structured output enforcement.

    Args:
        response: Generated response text
        query: User input text
        provider: LLM provider for judging (anthropic/openai/google/ollama)
        model: Judge model name (if None, uses provider default)

    Returns:
        Dictionary with helpfulness metrics
    """
    if model is None:
        model = get_default_model(provider)

    judge_prompt = f"""Evaluate how helpful the assistant's response is for the user's need.

User query:
{query}

Assistant response:
{response}

Task: Assign a helpfulness score (1-5) using this rubric:
- 5: Addresses the user's need with relevant guidance; provides helpful direction or suggestions.
- 4: Generally helpful and on-topic; offers useful information even if not fully complete.
- 3: Shows attempt to help; provides some relevant information or asks clarifying questions.
- 2: Minimal usefulness; very generic or vague but not completely off-topic.
- 1: Not helpful or completely off-topic; fails to address the user's need at all.

Rules:
- Focus on whether the response attempts to help and is relevant to the query.
- Consider partial help or asking good clarifying questions as valuable.
- Acknowledge that brief responses can still be helpful if they're on-topic.
- Only score 1-2 for responses that are clearly unhelpful or completely miss the point.
- If the response is empty or non-responsive, score = 1.

Return structured JSON with:
- helpfulness_score (1-5 integer)
- explanation (why the score was chosen)
- missing_info (list of gaps/clarifications needed)
- suggested_followups (list of next steps/questions)
"""

    if not response or not response.strip():
        logger.warning("Empty response provided to helpfulness judge")
        raise ValueError("Cannot judge helpfulness on empty response")

    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=HelpfulnessJudgment,
        temperature=0.0,
        max_tokens=800,  # Increased for detailed helpfulness analysis
    )

    logger.debug(
        f"Helpfulness ({provider}/{model}) score: {judgment.helpfulness_score}/5"
    )
    logger.debug(f"Explanation: {judgment.explanation[:100]}...")

    return {
        "helpfulness_score": judgment.helpfulness_score,
        "explanation": judgment.explanation,
        "missing_info": judgment.missing_info or [],
        "suggested_followups": judgment.suggested_followups or [],
    }
