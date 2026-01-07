"""Coherence/Fluency Metric.

This module evaluates the coherence and fluency of LLM responses using
LLM-as-a-judge with a rubric-based scoring system.

Uses Pydantic AI for structured output with a 5-point scale:
- 5: Natural grammar, clear expression, smooth structure, no obvious repetition/breaks
- 4: Generally smooth, occasional minor grammatical issues or slight jumps
- 3: Understandable, but multiple instances of unnaturalness/jumps/repetition
- 2: Obviously incoherent, poor logical connections
- 1: Very difficult to understand, severe grammar/breaks

Metric:
- Coherence Score: Integer score from 1-5 (higher is better)
- Average Coherence: Mean score across all samples
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.config import logger
from .llm_router import get_structured_response


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class CoherenceJudgment(BaseModel):
    """Structured output for coherence judgment using Pydantic AI."""
    coherence_score: int = Field(
        ge=1,
        le=5,
        description="Coherence score on a 5-point scale (1=poor, 5=excellent)"
    )
    explanation: str = Field(
        description="Detailed explanation of the coherence score based on the rubric"
    )
    grammar_issues: Optional[List[str]] = Field(
        default_factory=list,
        description="List of specific grammar or fluency issues identified"
    )
    strengths: Optional[List[str]] = Field(
        default_factory=list,
        description="List of coherence strengths in the response"
    )


# ============================================================================
# LLM Judge
# ============================================================================

def judge_coherence(
    response: str,
    query: str,
    provider: str = "openai",
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate coherence and fluency of response.

    Uses Pydantic AI (instructor) for structured output enforcement.

    Args:
        response: Generated response text
        query: User input query (for context)
        model: Judge model name

    Returns:
        Dictionary with coherence metrics
    """
    judge_prompt = f"""Evaluate the coherence and fluency of a healthcare assistant's response using the following rubric.

User Query:
{query}

Assistant Response:
{response}

COHERENCE/FLUENCY RUBRIC:

Score 5 - Excellent:
• Natural and grammatically correct language
• Clear and precise expression
• Smooth logical flow and structure
• No obvious repetition or breaks in thought
• Easy to read and understand

Score 4 - Good:
• Generally smooth and coherent
• Occasional minor grammatical issues (e.g., articles, prepositions)
• Slight logical jumps but still followable
• Overall clear communication

Score 3 - Adequate:
• Understandable but with noticeable issues
• Multiple instances of unnatural phrasing
• Some logical jumps or repetition
• Requires effort to follow in places

Score 2 - Poor:
• Obviously incoherent in multiple places
• Poor logical connections between sentences
• Significant grammatical errors affecting clarity
• Difficult to follow the main points

Score 1 - Very Poor:
• Very difficult to understand
• Severe grammatical errors or sentence fragments
• Major breaks in logical flow
• Lacks coherent structure

TASK:
1. Read the response carefully
2. Identify specific grammar issues, logical jumps, repetition, or breaks
3. Identify strengths in coherence and fluency
4. Assign a score from 1-5 based on the rubric
5. Provide a detailed explanation for your score

IMPORTANT RULES:
- Focus on language quality, NOT content accuracy (accuracy is measured by other metrics)
- Consider the healthcare context - medical terminology should be used appropriately
- Empty responses are considered errors (no score)
- Be objective and consistent in applying the rubric

Return:
- coherence_score: integer 1-5
- explanation: detailed reasoning for the score
- grammar_issues: list of specific problems found (if any)
- strengths: list of coherence strengths (if any)
"""

    # Handle empty response
    if not response or not response.strip():
        logger.warning("Empty response provided to coherence judge")
        raise ValueError("Cannot judge coherence on empty response")

    # Get structured response via LLM router
    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=CoherenceJudgment,
        temperature=0.0,
        max_tokens=400,
    )

    logger.debug(f"Coherence score: {judgment.coherence_score}/5")
    logger.debug(f"Explanation: {judgment.explanation[:100]}...")

    return {
        "coherence_score": judgment.coherence_score,
        "explanation": judgment.explanation,
        "grammar_issues": judgment.grammar_issues or [],
        "strengths": judgment.strengths or [],
    }
