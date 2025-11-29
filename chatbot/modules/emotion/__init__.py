"""Emotion analysis: speech and text"""
from .speech_analyzer import load_emotion_model as load_speech_emotion_model
from .speech_analyzer import predict_emotion as predict_speech_emotion
from .text_analyzer import load_text_emotion_model, predict_text_emotion, TEXT_EMOTION_LABELS

__all__ = [
    'load_speech_emotion_model', 'predict_speech_emotion',
    'load_text_emotion_model', 'predict_text_emotion',
    'TEXT_EMOTION_LABELS'
]
