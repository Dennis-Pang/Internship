"""Memory Utilization Accuracy Metric.

This module evaluates how well LLM responses utilize relevant memory information.
Measures correct use of relevant memories by comparing referenced vs expected memory keys.

Uses LLM-as-a-judge with Pydantic AI for structured output.

Metrics:
- Precision: TP / (TP + FP) - proportion of referenced memories that are relevant
- Recall: TP / (TP + FN) - proportion of relevant memories that are referenced
- F1: 2 * P * R / (P + R) - harmonic mean

Where:
- TP = cited required_keys (relevant memories used)
- FP = cited forbidden_keys (irrelevant memories used)
- FN = missed required_keys (relevant memories not used)
- neutral_keys do not contribute to any metric
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.config import logger
from .llm_router import get_structured_response, get_default_model


# ============================================================================
# Pydantic Model for Structured Output
# ============================================================================

class MemoryUtilizationJudgment(BaseModel):
    """Structured output for memory utilization judgment using Pydantic AI."""
    cited_keys: List[str] = Field(
        default_factory=list,
        description="List of memory keys that were explicitly referenced/utilized in the response"
    )


# ============================================================================
# LLM Judge
# ============================================================================

def judge_memory_utilization(
    response: str,
    query: str,
    memory: Dict[str, Any],
    all_keys: List[str],
    provider: str = "openai",
    model: str = None,
) -> List[str]:
    """Use LLM as judge to identify which memory keys were utilized in response.

    Uses Pydantic AI (instructor) for structured output enforcement.

    Args:
        response: Generated response text
        query: User query for the current turn (helps disambiguate required keys)
        memory: Original memory dictionary
        all_keys: All available memory keys (required + forbidden + neutral)
        provider: LLM provider for judging (anthropic/openai/google)
        model: Judge model name (if None, uses provider default)

    Returns:
        List of utilized memory keys
    """
    # Use default model if not specified
    if model is None:
        model = get_default_model(provider)

    if not response or not response.strip():
        logger.warning("Empty response provided to memory utilization judge")
        raise ValueError("Cannot judge memory utilization on empty response")

    memory_json = json.dumps(memory, indent=2)
    keys_list = ", ".join(all_keys)

    judge_prompt = f"""Given a healthcare assistant's response and the user's memory profile, identify which memory keys were referenced or utilized in the response.

User Memory Profile (key-value pairs):
{memory_json}

User Query (current turn):
{query}

Assistant Response:
{response}

Available memory keys: {keys_list}

TASK: Identify which memory keys were referenced by checking if the response mentions information that semantically matches the memory VALUE associated with each key.

IMPORTANT RULES:
1. A key is "cited" if the response mentions concepts/information that match the memory VALUE for that key
2. The response does NOT need to mention the key name itself - focus on whether the VALUE's information appears
3. Look for paraphrases, synonyms, or semantically equivalent mentions
4. Be lenient: if the concept is reasonably implied or partially described, include the key (favor recall over precision)
5. If unsure between include vs exclude, include the key

EXAMPLES:

Example 1:
Memory: {{"medication_type": "daily blood pressure pill"}}
Response: "We'll set a reminder for your blood pressure medication"
Cited keys: ["medication_type"] ✓ 

Example 2:
Memory: {{"forgetting_pattern": "evenings","medication_type": "blood pressure pills"}}
Response: "don't forget to take your pills in the evening"
Cited keys: ["forgetting_pattern", "medication_type"] ✓ 

Example 3:
Memory: {{"tech_comfort": "high"}}
Response: "Since you're comfortable using your phone"
Cited keys: ["tech_comfort"] ✓ 


Return the list of cited memory keys in the cited_keys field.
If no keys were clearly referenced, return an empty list.
"""

    # Get structured response via LLM router
    judgment = get_structured_response(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        response_model=MemoryUtilizationJudgment,
        temperature=0.0,  # Use temperature=0 for more deterministic judging
        max_tokens=500,  # Increased for memory key detection
    )

    # Validate that all cited keys are in all_keys
    cited_keys = [k for k in judgment.cited_keys if k in all_keys]

    logger.debug(f"Judge ({provider}/{model}) utilized memory keys: {cited_keys}")
    return cited_keys


# ============================================================================
# Metrics Calculation
# ============================================================================

def calculate_sample_metrics(
    cited_keys: List[str],
    required_keys: List[str],
    forbidden_keys: List[str],
) -> Dict[str, float]:
    """Calculate TP/FP/FN/Precision/Recall/F1 for a single sample.

    Formula:
    - U = set of cited keys (from judge)
    - R = set of required keys
    - F = set of forbidden keys
    - TP = |U ∩ R| (cited AND required)
    - FP = |U ∩ F| (cited AND forbidden)
    - FN = |R| - TP (required but NOT cited)
    - Precision = TP / (TP + FP), or 1.0 if TP+FP=0
    - Recall = TP / |R|, or 1.0 if |R|=0
    - F1 = 2*P*R / (P+R), or 0.0 if P+R=0

    Args:
        cited_keys: Keys identified as cited by judge
        required_keys: Keys that should be referenced
        forbidden_keys: Keys that should NOT be referenced

    Returns:
        Dictionary with metrics
    """
    U = set(cited_keys)
    R = set(required_keys)
    F = set(forbidden_keys)

    TP = len(U & R)
    FP = len(U & F)
    FN = len(R) - TP

    # Precision: when TP+FP=0 (no keys cited), set to 1.0 (no citation errors)
    if TP + FP == 0:
        precision = 1.0
    else:
        precision = TP / (TP + FP)

    # Recall
    if len(R) == 0:
        recall = 1.0
    else:
        recall = TP / len(R)

    # F1
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "TP": TP,
        "FP": FP,
        "FN": FN,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }
