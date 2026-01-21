"""Emotion analysis: speech and text."""

from .base import EMOTION_LABELS
from .speech import load_emotion_model as load_speech_emotion_model
from .speech import predict_emotion as predict_speech_emotion
from .text import load_text_emotion_model, predict_text_emotion, TEXT_EMOTION_LABELS

__all__ = [
    "load_speech_emotion_model",
    "predict_speech_emotion",
    "load_text_emotion_model",
    "predict_text_emotion",
    "EMOTION_LABELS",
    "TEXT_EMOTION_LABELS",  # TEXT_EMOTION_LABELS for backward compatibility
]
