"""Response Relevance Metric.

This module evaluates how relevant the LLM response is to the user query
using LLM-as-judge with rubric-based scoring.

Metric:
- Relevance Score: 1-5 scale evaluating how well the response addresses the query
  - 5: Perfectly addresses the query, all key points covered
  - 4: Mostly relevant, minor tangents or omissions
  - 3: Partially relevant, some key points missing
  - 2: Tangentially related, mostly off-topic
  - 1: Completely irrelevant or unrelated
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pydantic import BaseModel, Field
from modules.config import logger
from .llm_router import get_structured_response


# ============================================================================
# Pydantic Models
# ============================================================================

class RelevanceJudgment(BaseModel):
    """Structured output for relevance evaluation."""

    relevance_score: int = Field(
        ge=1,
        le=5,
        description="Relevance score from 1 (completely irrelevant) to 5 (perfectly relevant)"
    )
    explanation: str = Field(
        description="Brief explanation of the score, highlighting addressed/missing points"
    )


# ============================================================================
# Relevance Evaluation
# ============================================================================

def judge_relevance(
    query: str,
    response: str,
    provider: str = "google",
    model: str = "gemini-2.0-flash-exp",
) -> Dict[str, Any]:
    """Evaluate relevance of response to query using LLM-as-judge.

    Args:
        query: User input query
        response: Model-generated response
        provider: LLM provider (default: google for Gemini 2.0 Flash)
        model: LLM model name (default: gemini-2.0-flash-exp)

    Returns:
        Dictionary with relevance_score (1-5) and explanation
    """
    if not response or not response.strip() or not query or not str(query).strip():
        logger.warning("Empty query or response provided to relevance judge")
        raise ValueError("Cannot judge relevance with empty query or response")

    # Construct judge prompt with rubric
    judge_prompt = f"""TASK: Evaluate how relevant the response is to the user's query.

QUERY:
{query}

RESPONSE:
{response}

RUBRIC (1-5):
5 - Highly relevant: Addresses the main topic or concern from the query appropriately
4 - Mostly relevant: Responds to the query with reasonable connection to the topic
3 - Moderately relevant: Related to the general topic area, even if not addressing all details
2 - Somewhat related: Touches on related concepts but may miss the specific point
1 - Completely irrelevant: Unrelated to the query or addresses entirely different topic

EVALUATION CRITERIA:
1. Is the response generally on-topic and related to the query subject?
2. Does it show understanding of the user's general concern or question?
3. Even if brief, does it attempt to address the query in a reasonable way?
4. Give credit for responses that are in the right topic area, even if not comprehensive.

Provide:
1. relevance_score: Integer from 1-5 based on rubric
2. explanation: Brief justification highlighting what was addressed/missing
"""

    # Get structured response via LLM router
    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=RelevanceJudgment,
        temperature=0.0,
        max_tokens=300,
    )

    logger.debug(
        f"Relevance judge ({provider}/{model}) score: {judgment.relevance_score}/5 - {judgment.explanation[:100]}"
    )

    return {
        "relevance_score": judgment.relevance_score,
        "explanation": judgment.explanation,
    }

