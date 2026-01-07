"""Empathy Score Metric.

This module evaluates the empathy and emotional intelligence displayed in
LLM responses using LLM-as-a-judge with a rubric-based scoring system.

Evaluates:
1. Warmth - Friendly, caring, human tone
2. Validation - Acknowledges and validates user's feelings/experiences
3. Supportive Tone - Encouraging, understanding, non-judgmental

Note: This differs from Emotional Congruence, which checks if tone *matches*
user emotions. Empathy checks if the response is *warm, validating, and supportive*
regardless of the user's emotional state.

Uses Pydantic AI for structured output with a 5-point scale:
- 5: Highly empathetic, warm, validating, deeply supportive
- 4: Mostly empathetic with occasional mechanical phrasing
- 3: Neutral, some empathy but could be warmer
- 2: Lacks empathy, cold or dismissive
- 1: Completely lacking empathy, inappropriate or harsh

Metric:
- Empathy Score: Integer score from 1-5 (higher is better)
- Average Empathy: Mean score across all samples
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

class EmpathyJudgment(BaseModel):
    """Structured output for empathy judgment using Pydantic AI."""
    empathy_score: int = Field(
        ge=1,
        le=5,
        description="Empathy score on a 5-point scale (1=lacking empathy, 5=highly empathetic)"
    )
    warmth_level: str = Field(
        description="Assessment of warmth: 'high', 'moderate', 'low', or 'cold'"
    )
    validation_present: bool = Field(
        description="Whether the response validates user's feelings/experiences"
    )
    supportive_elements: List[str] = Field(
        default_factory=list,
        description="Specific supportive/empathetic phrases or approaches"
    )
    empathy_gaps: List[str] = Field(
        default_factory=list,
        description="Missed opportunities for empathy or cold/dismissive elements"
    )
    explanation: str = Field(
        description="Summary of the empathy evaluation"
    )


# ============================================================================
# LLM Judge
# ============================================================================

def judge_empathy(
    response: str,
    query: str,
    provider: str = "openai",
    model: str = None,
) -> Dict[str, Any]:
    """Use LLM as judge to evaluate empathy in response.

    Uses Pydantic AI (instructor) for structured output enforcement.

    Args:
        response: Generated response text
        query: User input query (for context)
        provider: LLM provider for judging (anthropic/openai/google)
        model: Judge model name (if None, uses provider default)

    Returns:
        Dictionary with empathy metrics
    """
    # Use default model if not specified
    if model is None:
        model = get_default_model(provider)

    judge_prompt = f"""Evaluate the empathy and emotional intelligence displayed in a healthcare assistant's response using the following rubric.

User Query:
{query}

Assistant Response:
{response}

EMPATHY RUBRIC:

Score 5 - Highly Empathetic:
• Warm and supportive tone
• Shows understanding of user's situation
• Generally caring and encouraging
• Acknowledges user's feelings or experiences

Score 4 - Mostly Empathetic:
• Friendly and approachable tone
• Some validation or support present
• Professional but warm
• Overall positive and helpful

Score 3 - Moderately Empathetic:
• Neutral but not cold tone
• Basic professionalism maintained
• Some attempt at being helpful
• Not dismissive or harsh

Score 2 - Lacks Empathy:
• Somewhat cold or overly clinical
• Minimal warmth or validation
• Very transactional or robotic
• Feels detached or indifferent

Score 1 - No Empathy:
• Harsh, inappropriate, or very dismissive
• Actively invalidating or judgmental
• Cold and uncaring throughout
• Clearly lacks any compassion

EVALUATION DIMENSIONS:

1. WARMTH
   Assess the human warmth in the tone:
   - Uses caring, friendly language
   - Shows genuine concern
   - Feels personal rather than robotic
   - Example: "I understand this must be challenging" vs "You should follow these steps"

2. VALIDATION
   Does the response validate the user's feelings/experiences?
   - Acknowledges user's concerns
   - Normalizes their feelings
   - Shows understanding of their situation
   - Example: "It's completely understandable to feel tired" vs skipping validation entirely

3. SUPPORTIVE TONE
   Is the response encouraging and non-judgmental?
   - Offers reassurance
   - Encourages positive steps
   - Avoids blame or criticism
   - Maintains hopeful, helpful tone
   - Example: "Let's work on this together" vs "You need to fix this"

IMPORTANT NOTES:
- This evaluates empathy/warmth, NOT accuracy or emotional alignment
- Even neutral topics deserve warm, supportive tone
- Healthcare requires extra empathy due to vulnerability
- Empathy ≠ emotional matching (that's measured elsewhere)
- Empty responses are considered errors (no score)

TASK:
1. Read the response carefully
2. Assess warmth level (high/moderate/low/cold)
3. Check if feelings/experiences are validated
4. Identify supportive elements (specific phrases)
5. Note empathy gaps or cold elements
6. Assign score 1-5 based on rubric
7. Provide clear explanation

Return:
- empathy_score: integer 1-5
- warmth_level: string ('high', 'moderate', 'low', or 'cold')
- validation_present: boolean
- supportive_elements: list of empathetic phrases/approaches
- empathy_gaps: list of missed opportunities or cold elements
- explanation: detailed reasoning for the score
"""

    # Handle empty response
    if not response or not response.strip():
        logger.warning("Empty response provided to empathy judge")
        raise ValueError("Cannot judge empathy on empty response")

    # Get structured response via LLM router
    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=EmpathyJudgment,
        temperature=0.0,  # Use temperature=0 for more deterministic judging
        max_tokens=500,
    )

    logger.debug(f"Empathy ({provider}/{model}) score: {judgment.empathy_score}/5")
    logger.debug(f"Warmth: {judgment.warmth_level}, Validation: {judgment.validation_present}")

    return {
        "empathy_score": judgment.empathy_score,
        "warmth_level": judgment.warmth_level,
        "validation_present": judgment.validation_present,
        "supportive_elements": judgment.supportive_elements,
        "empathy_gaps": judgment.empathy_gaps,
        "explanation": judgment.explanation,
        "num_supportive_elements": len(judgment.supportive_elements),
        "num_empathy_gaps": len(judgment.empathy_gaps),
    }
