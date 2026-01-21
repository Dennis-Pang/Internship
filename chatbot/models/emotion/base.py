"""Base utilities for emotion analysis across speech and text models."""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Standard emotion labels for all models
EMOTION_LABELS = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]


def get_default_emotion_scores(return_logits: bool = False) -> Dict[str, float]:
    """Get default emotion scores when analysis fails.

    Args:
        return_logits: If True, return zero logits; otherwise return uniform probabilities

    Returns:
        Dictionary with emotion labels as keys
    """
    if return_logits:
        return {label: 0.0 for label in EMOTION_LABELS}
    else:
        uniform = 1.0 / len(EMOTION_LABELS)
        return {label: uniform for label in EMOTION_LABELS}


def handle_emotion_prediction_error(
    error: Exception, model_name: str, return_logits: bool = False
) -> Dict[str, float]:
    """Handle emotion prediction errors consistently.

    Args:
        error: The exception that occurred
        model_name: Name of the model for logging
        return_logits: If True, return zero logits; otherwise return uniform probabilities

    Returns:
        Default emotion scores
    """
    logger.error(f"{model_name} emotion analysis failed: {error}")
    return get_default_emotion_scores(return_logits)


def validate_emotion_scores(scores: Dict[str, float]) -> Dict[str, float]:
    """Validate and normalize emotion scores.

    Args:
        scores: Raw emotion scores

    Returns:
        Validated emotion scores with all required labels
    """
    validated = {}
    for label in EMOTION_LABELS:
        validated[label] = float(scores.get(label, 0.0))
    return validated
