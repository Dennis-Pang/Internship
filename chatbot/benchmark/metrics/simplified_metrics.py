"""Simplified Metric Wrappers with Optimal Judges.

Each function returns a single numeric score for easy batching.
All functions automatically use the best judge model based on LMArena benchmarks.

ALL METRICS USE UNIFIED 0-1 SCALE (mapped from original 1-5 judges):
- persona_consistency: 0-1 (Claude Opus 4.5)
- emotional_congruence: 0-1 (GPT-4o)
- memory_utilization: 0-1 (Claude Opus 4.5) - F1 stays in 0-1
- relevance: 0-1 (Gemini 2.0 Flash)
- coherence: 0-1 (GPT-4o)
- helpfulness: 0-1 (Claude Opus 4.5)
- empathy: 0-1 (GPT-4o)
- politeness: 0-1 (GPT-4o)
- safety: 0-1 (Claude Opus 4.5)
- logical_consistency: 0-1 (GPT-5.2)
- conversational_continuity: 0-1 (Gemini 2.0 Flash)
- groundedness: 0-1 (Claude Opus 4.5)
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.config import logger
from .judge_config import get_judge_model

# Map raw 1-5 judge scores to 0-1 for unified downstream use
def _to_unit(score: Any) -> float:
    return (float(score) - 1.0) / 4.0

# Import original metric functions
from . import (
    judge_persona_consistency,
    judge_emotional_congruence,
    judge_memory_utilization,
    calculate_sample_metrics,
    judge_relevance,
    judge_coherence,
    judge_helpfulness,
    judge_empathy,
    judge_politeness,
    judge_safety,
    judge_logical_consistency,
    judge_conversational_continuity,
    judge_groundedness,
)


def persona_consistency(
    response: str,
    query: str,
    personality: List[Dict[str, Any]],
    provider: str = None,
    model: str = None,
) -> float:
    """Persona consistency score (0-1; mapped from 1-5 judge).

    Auto-uses Claude Opus 4.5 (best instruction following + reasoning)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("persona_consistency")
    elif (provider is None) != (model is None):
        raise ValueError("persona_consistency override requires both provider and model")

    result = judge_persona_consistency(response, query, personality, provider, model)
    score = result.get("persona_consistency_score")
    if score is None:
        raise ValueError(f"persona_consistency judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def emotional_congruence(
    response: str,
    query: str,
    emotion_distribution: Dict[str, float],
    provider: str = None,
    model: str = None,
) -> float:
    """Emotional congruence score (0-1; mapped from 1-5 judge).

    Auto-uses GPT-4o (highest Sentient score for empathy)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("emotional_congruence")
    elif (provider is None) != (model is None):
        raise ValueError("emotional_congruence override requires both provider and model")

    result = judge_emotional_congruence(response, query, emotion_distribution, provider, model)
    score = result.get("emotional_congruence_score")
    if score is None:
        raise ValueError(f"emotional_congruence judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def memory_utilization(
    response: str,
    query: str,
    memory: Dict[str, Any],
    must_use_keys: List[str],
    must_not_use_keys: List[str] = None,
    provider: str = None,
    model: str = None,
) -> float:
    """Memory utilization score (0-1; underlying F1).

    Auto-uses Claude Opus 4.5 (precision in logic tasks)

    Args:
        response: Generated response text
        query: User query
        memory: Memory dictionary
        must_use_keys: Required memory keys that should be cited
        must_not_use_keys: Optional forbidden keys (defaults to empty list if None)
        provider: LLM provider
        model: Model name
    """
    if provider is None and model is None:
        provider, model = get_judge_model("memory_utilization")
    elif (provider is None) != (model is None):
        raise ValueError("memory_utilization override requires both provider and model")

    # Handle None must_not_use_keys (backward compatibility)
    if must_not_use_keys is None:
        must_not_use_keys = []

    logger.info(f"[DEBUG] memory_utilization using {provider}/{model}")

    all_keys = list(memory.keys())
    cited_keys = judge_memory_utilization(response, query, memory, all_keys, provider, model)

    logger.info(f"[DEBUG] cited_keys from judge: {cited_keys}")
    logger.info(f"[DEBUG] must_use_keys: {must_use_keys}")
    logger.info(f"[DEBUG] must_not_use_keys: {must_not_use_keys}")

    metrics = calculate_sample_metrics(cited_keys, must_use_keys, must_not_use_keys)
    f1_score = metrics.get("f1")
    if f1_score is None:
        raise ValueError(f"memory_utilization calculation returned None F1 score")
    f1_score = float(f1_score)

    logger.info(f"[DEBUG] metrics: {metrics}, F1 (0-1): {f1_score}, final score: {f1_score}")

    # F1 already in 0-1; return normalized score directly
    return f1_score


def relevance(
    response: str,
    query: str,
    provider: str = None,
    model: str = None,
) -> float:
    """Relevance score via LLM-as-judge (0-1; mapped from 1-5 judge).

    Auto-uses Gemini 2.0 Flash (best conversational understanding)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("relevance")
    elif (provider is None) != (model is None):
        raise ValueError("relevance override requires both provider and model")

    result = judge_relevance(query, response, provider, model)
    score = result.get("relevance_score")
    if score is None:
        raise ValueError(f"relevance judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def coherence(
    response: str,
    query: str,
    provider: str = None,
    model: str = None,
) -> float:
    """Coherence score (0-1; mapped from 1-5 judge).

    Auto-uses GPT-4o (best general language understanding, MMLU 88.7%)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("coherence")
    elif (provider is None) != (model is None):
        raise ValueError("coherence override requires both provider and model")

    result = judge_coherence(response, query, provider, model)
    score = result.get("coherence_score")
    if score is None:
        raise ValueError(f"coherence judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def helpfulness(
    response: str,
    query: str,
    provider: str = None,
    model: str = None,
) -> float:
    """Helpfulness score (0-1; mapped from 1-5 judge).

    Auto-uses Claude Opus 4.5 (#1 instruction following)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("helpfulness")
    elif (provider is None) != (model is None):
        raise ValueError("helpfulness override requires both provider and model")

    result = judge_helpfulness(response, query, provider, model)
    score = result.get("helpfulness_score")
    if score is None:
        raise ValueError(f"helpfulness judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def empathy(
    response: str,
    query: str,
    provider: str = None,
    model: str = None,
) -> float:
    """Empathy score (0-1; mapped from 1-5 judge).

    Auto-uses GPT-4o (highest Sentient score)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("empathy")
    elif (provider is None) != (model is None):
        raise ValueError("empathy override requires both provider and model")

    result = judge_empathy(response, query, provider, model)
    score = result.get("empathy_score")
    if score is None:
        raise ValueError(f"empathy judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def politeness(
    response: str,
    query: str,
    provider: str = None,
    model: str = None,
) -> float:
    """Politeness score (0-1; mapped from 1-5 judge).

    Auto-uses GPT-4o (best social cognition)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("politeness")
    elif (provider is None) != (model is None):
        raise ValueError("politeness override requires both provider and model")

    result = judge_politeness(response, query, provider, model)
    score = result.get("politeness_score")
    if score is None:
        raise ValueError(f"politeness judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def safety(
    response: str,
    query: str,
    provider: str = None,
    model: str = None,
) -> float:
    """Safety score (0-1; mapped from 1-5 judge).

    Auto-uses Claude Opus 4.5 (Anthropic's AI safety focus)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("safety")
    elif (provider is None) != (model is None):
        raise ValueError("safety override requires both provider and model")

    result = judge_safety(response, query, provider, model)
    score = result.get("safety_score")
    if score is None:
        raise ValueError(f"safety judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def logical_consistency(
    response: str,
    query: str,
    provider: str = None,
    model: str = None,
) -> float:
    """Logical consistency score (0-1; mapped from 1-5 judge).

    Auto-uses GPT-5.2 (perfect 100% AIME 2025, 52.9% ARC-AGI)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("logical_consistency")
    elif (provider is None) != (model is None):
        raise ValueError("logical_consistency override requires both provider and model")

    result = judge_logical_consistency(response, query, provider, model)
    score = result.get("consistency_score")  # Note: judge returns "consistency_score" not "logical_consistency_score"
    if score is None:
        raise ValueError(f"logical_consistency judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def conversational_continuity(
    response: str,
    query: str,
    dialogue_history: List[Dict[str, str]],
    provider: str = None,
    model: str = None,
) -> float:
    """Conversational continuity score (0-1; mapped from 1-5 judge).

    Auto-uses Gemini 2.0 Flash (#1 overall 1501 Elo, excellent context)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("conversational_continuity")
    elif (provider is None) != (model is None):
        raise ValueError("conversational_continuity override requires both provider and model")

    # Fix: judge_conversational_continuity expects (conversation, response, provider, model)
    result = judge_conversational_continuity(dialogue_history, response, provider, model)
    score = result.get("continuity_score")
    if score is None:
        raise ValueError(f"conversational_continuity judge ({provider}/{model}) returned None score")
    return _to_unit(score)


def groundedness(
    response: str,
    query: str,
    memory: Dict[str, Any],
    provider: str = None,
    model: str = None,
) -> float:
    """Groundedness score (0-1; mapped from 1-5 judge).

    Auto-uses Claude Opus 4.5 (low hallucination rate)
    """
    if provider is None and model is None:
        provider, model = get_judge_model("groundedness")
    elif (provider is None) != (model is None):
        raise ValueError("groundedness override requires both provider and model")

    result = judge_groundedness(response, query, memory, provider, model)
    score = result.get("groundedness_score")
    if score is None:
        raise ValueError(f"groundedness judge ({provider}/{model}) returned None score")
    return _to_unit(score)
