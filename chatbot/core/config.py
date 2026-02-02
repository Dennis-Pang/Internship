"""Configuration constants and environment variables."""
import os
import logging
import warnings

# Ensure HF cache dir is writable and consistent across modules (avoids meta tensor issues)
HF_CACHE_DIR = os.getenv("HF_HOME", "/mnt/ssd/huggingface")
os.environ.setdefault("HF_HOME", HF_CACHE_DIR)
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(HF_CACHE_DIR, "hub"))
os.environ.setdefault("HF_DATASETS_CACHE", os.path.join(HF_CACHE_DIR, "datasets"))
os.makedirs(HF_CACHE_DIR, exist_ok=True)

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "memories.sqlite")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Audio configuration
SAMPLE_RATE = 16000
AUDIO_FILE = "temp_audio.wav"
RECORD_DURATION = 5  # Seconds
WHISPER_WARMUP_SAMPLES = 1600  # 0.1s @16k for initial graph compilation

# User configuration
DEFAULT_SPEAKER = "test user"

# Whisper model configuration
# Default to local path if available, otherwise use HuggingFace model ID
WHISPER_MODEL_PATH = os.getenv(
    "WHISPER_MODEL_PATH",
    "/mnt/ssd/huggingface/hub/"
    "models--openai--whisper-large-v3-turbo/"
    "snapshots/41f01f3fe87f28c78e2fbf8b568835947dd65ed9"
)

# Conversation memory configuration
DEFAULT_HISTORY_WINDOW = 5  # short-term window size

# MemoBase configuration
MEMOBASE_PROJECT_URL = os.getenv("MEMOBASE_PROJECT_URL", "http://localhost:8019")
MEMOBASE_API_KEY = os.getenv("MEMOBASE_API_KEY", "secret")
MEMOBASE_API_VERSION = os.getenv("MEMOBASE_API_VERSION", "api/v1")
MEMOBASE_TIMEOUT = int(os.getenv("MEMOBASE_TIMEOUT", "5"))  # Reduced from 600s to 5s to prevent hangs
MEMOBASE_SYNC_TIMEOUT = int(
    os.getenv("MEMOBASE_SYNC_TIMEOUT", str(60 * 60))
)  # Allow up to 1 hour for synchronous flushes
MEMOBASE_BASE_URL = f"{MEMOBASE_PROJECT_URL.rstrip('/')}/{MEMOBASE_API_VERSION.strip('/')}"

DEFAULT_MEMORY_PROMPT = "Only refer to the memory if it's relevant to user's input."
DEFAULT_MAX_CONTEXT_SIZE = 1000

# Memory cache configuration
MEMORY_CACHE_FILE = os.getenv("MEMORY_CACHE_FILE", os.path.join(DATA_DIR, "memory_cache.json"))
MEMORY_CACHE_BATCH_SIZE = int(os.getenv("MEMORY_CACHE_BATCH_SIZE", "2")) # each round

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "qwen2.5:3b-instruct"
OLLAMA_STREAM = True
OLLAMA_TEMPERATURE = 0.7
OLLAMA_MAX_TOKENS = 256

# Personality model paths
PERSONALITY_MODELS_DIR = os.path.join(BASE_DIR, "data", "models")

# TTS (Text-to-Speech) configuration
TTS_RATE = 200  # Speech rate (words per minute)
TTS_VOLUME = 0.8  # Volume level (0.0 to 1.0)

# Kokoro TTS configuration
USE_KOKORO = os.getenv("USE_KOKORO", "true").lower() == "true"
KOKORO_REPO_ID = os.getenv("KOKORO_REPO_ID", "hexgrad/Kokoro-82M")
KOKORO_LANG = "en-us"  # Force English only
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_heart")
KOKORO_SPEED = float(os.getenv("KOKORO_SPEED", "1.0"))
KOKORO_DEVICE = os.getenv("KOKORO_DEVICE", "auto")  # auto|cpu|cuda
KOKORO_OUTPUT_DEVICE_INDEX = os.getenv("KOKORO_OUTPUT_DEVICE_INDEX", "")
KOKORO_OUTPUT_SAMPLE_RATE = os.getenv("KOKORO_OUTPUT_SAMPLE_RATE", "")

# Audio recording configuration
AUDIO_TIMEOUT_MARGIN = 2.0  # Extra seconds to wait beyond duration before timeout
AUDIO_MAX_RETRIES = 2  # Maximum number of retry attempts on recording failure
AUDIO_MIN_RMS = float(os.getenv("AUDIO_MIN_RMS", "0.01"))  # Minimum RMS energy threshold for valid audio

# Emotion fusion configuration
SPEECH_EMOTION_WEIGHT = float(os.getenv("SPEECH_EMOTION_WEIGHT", "0.5"))  # Weight for speech-based emotion (0.0-1.0, 0=disabled)
TEXT_EMOTION_WEIGHT = float(os.getenv("TEXT_EMOTION_WEIGHT", "0.5"))  # Weight for text-based emotion (0.0-1.0, 0=disabled)

# Parallel processing configuration
MAX_PARALLEL_WORKERS = int(os.getenv("MAX_PARALLEL_WORKERS", "4"))  # Maximum parallel workers for audio processing

# Processing status constants
STATUS_IDLE = "idle"
STATUS_RECORDING = "recording"
STATUS_TRANSCRIBING = "transcribing"
STATUS_GENERATING = "generating"

# Greeting messages
GREETING_MESSAGES = [
    "Give me a sec to think about that.",
    "Let me process that real quick.",
    "Just a moment, I'm working on it.",
    "Let me figure this out for you.",
    "Hold on, I'll get right back to you.",
    "One moment while I put this together.",
]

# Disable greeting TTS by default (set PLAY_GREETING=true to enable)
PLAY_GREETING = os.getenv("PLAY_GREETING", "false").lower() == "true"

# Logging configuration
# Set to INFO to see audio debugging information, ERROR to suppress
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress noisy third-party future warnings (Python version + deprecated google.generativeai)
warnings.filterwarnings(
    "ignore",
    message=".*google.api_core.*Python version.*",
    category=FutureWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*google\\.generativeai.*has ended.*",
    category=FutureWarning,
)
