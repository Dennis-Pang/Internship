"""Logical Consistency Metric.

This module evaluates the logical consistency of LLM responses using
LLM-as-a-judge with a rubric-based scoring system.

Evaluates:
1. Internal contradictions - statements that contradict each other
2. Faulty reasoning - illogical conclusions or flawed causation
3. Inconsistent recommendations - conflicting advice

Uses Pydantic AI for structured output with a 5-point scale:
- 5: Perfectly consistent, sound reasoning throughout
- 4: Mostly consistent with minor logical issues
- 3: Some contradictions or weak reasoning
- 2: Noticeable logical problems or contradictions
- 1: Major contradictions or severely flawed logic

Metric:
- Logical Consistency Score: Integer score from 1-5 (higher is better)
- Average Consistency: Mean score across all samples
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

class Contradiction(BaseModel):
    """A single contradiction found in the response."""
    statement1: str = Field(
        description="First contradicting statement (exact quote)"
    )
    statement2: str = Field(
        description="Second contradicting statement (exact quote)"
    )
    explanation: str = Field(
        description="Brief explanation of why these statements contradict"
    )


class LogicalConsistencyJudgment(BaseModel):
    """Structured output for logical consistency judgment using Pydantic AI."""
    consistency_score: int = Field(
        ge=1,
        le=5,
        description="Logical consistency score on a 5-point scale (1=major issues, 5=perfect)"
    )
    contradictions: List[Contradiction] = Field(
        default_factory=list,
        description="List of internal contradictions found"
    )
    reasoning_issues: List[str] = Field(
        default_factory=list,
        description="Logical reasoning flaws (e.g., 'faulty causation', 'circular logic')"
    )
    consistent_elements: List[str] = Field(
        default_factory=list,
        description="Elements that demonstrate good logical consistency"
    )
    explanation: str = Field(
        description="Summary of the logical consistency evaluation"
    )


# ============================================================================
# LLM Judge
# ============================================================================

def judge_logical_consistency(
    response: str,
    query: str,
    provider: str = "openai",
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate logical consistency of response.

    Uses Pydantic AI (instructor) for structured output enforcement.

    Args:
        response: Generated response text
        query: User input query (for context)
        provider: LLM provider for judging (anthropic/openai/google)
        model: Judge model name (if None, uses provider default)

    Returns:
        Dictionary with logical consistency metrics
    """
    # Use default model if not specified
    if model is None:
        model = get_default_model(provider)

    judge_prompt = f"""Evaluate the logical consistency of a healthcare assistant's response using the following rubric.

User Query:
{query}

Assistant Response:
{response}

LOGICAL CONSISTENCY RUBRIC:

Score 5 - Perfectly Consistent:
• No internal contradictions
• All reasoning is sound and well-supported
• Recommendations are coherent and compatible
• Logical flow from premises to conclusions
• No faulty causation or circular logic

Score 4 - Mostly Consistent:
• Minor logical inconsistencies that don't affect overall message
• Reasoning is generally sound with occasional weak points
• Recommendations mostly compatible
• Overall logical structure is intact

Score 3 - Some Issues:
• Noticeable contradictions or inconsistent advice
• Some faulty reasoning or weak logical connections
• Recommendations partially conflict
• Requires effort to reconcile different parts

Score 2 - Significant Problems:
• Multiple contradictions in the response
• Flawed reasoning or poor logical structure
• Recommendations clearly conflict with each other
• Difficult to follow the logic

Score 1 - Major Logical Flaws:
• Severe contradictions throughout
• Fundamentally flawed reasoning
• Incompatible or contradictory recommendations
• Logic breaks down entirely

EVALUATION CRITERIA:

1. INTERNAL CONTRADICTIONS
   Look for statements that directly contradict each other:
   - "You should exercise more" vs "Avoid physical activity"
   - "Sleep 8 hours" vs "Wake up earlier" (when time budget doesn't allow)
   - "Reduce caffeine" vs "Coffee is fine" in the same response

2. FAULTY REASONING
   Identify logical flaws:
   - Treating symptoms without addressing causes
   - Circular reasoning (A causes B because B causes A)
   - False causation (correlation ≠ causation)
   - Hasty generalization from limited information
   - Post hoc ergo propter hoc fallacies

3. INCONSISTENT RECOMMENDATIONS
   Check if advice conflicts:
   - Mutually exclusive suggestions
   - Recommendations that work against each other
   - Advice that creates impossible constraints

TASK:
1. Read the response carefully
2. Identify specific contradictions (with exact quotes)
3. Note reasoning flaws (label them: "faulty causation", "circular logic", etc.)
4. Identify consistent elements that show good logic
5. Assign a score from 1-5 based on the rubric
6. Provide a clear explanation

IMPORTANT RULES:
- Focus on logical structure, NOT medical accuracy (that's measured elsewhere)
- Empty responses are considered errors (no score)
- Quote exact text when citing contradictions
- Be objective and consistent in applying the rubric
- Consider healthcare context - medical advice should be internally coherent

Return:
- consistency_score: integer 1-5
- contradictions: list of Contradiction objects with statement1, statement2, explanation
- reasoning_issues: list of strings describing logical flaws
- consistent_elements: list of strings noting good logical structure
- explanation: detailed reasoning for the score
"""

    # Handle empty response
    if not response or not response.strip():
        logger.warning("Empty response provided to logical consistency judge")
        raise ValueError("Cannot judge logical consistency on empty response")

    # Get structured response via LLM router
    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=LogicalConsistencyJudgment,
        temperature=0.0,  # Use temperature=0 for more deterministic judging
        max_tokens=600,  # More tokens for detailed analysis
    )

    logger.debug(f"Logical Consistency ({provider}/{model}) score: {judgment.consistency_score}/5")
    logger.debug(f"Found {len(judgment.contradictions)} contradictions, {len(judgment.reasoning_issues)} reasoning issues")

    return {
        "consistency_score": judgment.consistency_score,
        "contradictions": [c.model_dump() for c in judgment.contradictions],
        "reasoning_issues": judgment.reasoning_issues,
        "consistent_elements": judgment.consistent_elements,
        "explanation": judgment.explanation,
        "num_contradictions": len(judgment.contradictions),
        "num_reasoning_issues": len(judgment.reasoning_issues),
    }
