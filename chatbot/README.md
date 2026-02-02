# AI Voice Chatbot

Voice chatbot with Whisper STT, Kokoro TTS, fused emotion analysis (speech + text), Big Five personality detection, and MemoBase-backed long-term memory.

## Run

```bash
cd chatbot
python -m app.app           # Interactive voice CLI
python -m app.server        # REST/SSE backend for the dashboard
python -m app.sync          # Sync memory cache to MemoBase
```

## CLI Flags

```bash
python -m app.app \
  --history-window 5         # Conversation rounds for short-term memory (default: 5)
  --speech-emotion-weight 0.5 # Weight for speech-based emotion (0.0-1.0, 0=disabled)
  --text-emotion-weight 0.5   # Weight for text-based emotion (0.0-1.0, 0=disabled)
  --debug                     # Print full prompts sent to LLM
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_KOKORO` | `true` | Use Kokoro TTS engine (`false` to fallback to pyttsx3) |
| `OLLAMA_MODEL` | `qwen2.5:3b-infect` | LLM model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama API endpoint |
| `MEMOBASE_PROJECT_URL` | `http://localhost:8019` | MemoBase API base URL |
| `MEMOBASE_API_KEY` | `secret` | MemoBase authentication token |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `PLAY_GREETING` | `false` | Enable greeting TTS on startup |
| `KOKORO_VOICE` | `af_heart` | Kokoro TTS voice |
| `KOKORO_SPEED` | `1.0` | Kokoro TTS speed multiplier |
| `KOKORO_DEVICE` | `auto` | Kokoro device (`auto`, `cpu`, `cuda`) |

## Features

- **Whisper STT**: GPU-accelerated speech-to-text with configurable recording (hold-to-talk or timed)
- **Emotion Fusion**: Dual-source emotion analysis combining speech acoustics (CNN+Transformer) and text semantics (DeBERTa-v3-Large), with configurable weighting
- **Big Five Personality**: BERT-based personality detection (Extraversion, Neuroticism, Agreeableness, Conscientiousness, Openness)
- **Memory System**:
  - Short-term: SQLite database + JSON cache with sliding window history
  - Long-term: MemoBase API with semantic search for context retrieval
- **Kokoro TTS**: High-quality neural TTS with real-time audio streaming to frontend
- **Real-time Dashboard**: Flask backend with Server-Sent Events (SSE) for live updates

## Layout

```
chatbot/
├── app/
│   ├── app.py          # Interactive voice CLI entrypoint
│   ├── server.py       # Flask API + SSE streaming backend
│   └── sync.py         # Memory cache sync utility
├── audio/
│   ├── recorder.py     # Audio recording (sounddevice)
│   ├── stt.py          # Whisper STT pipeline
│   └── tts.py          # Kokoro TTS engine
├── models/
│   ├── emotion/        # Speech + Text emotion models
│   ├── llm.py          # Ollama chat client
│   └── personality.py  # BERT Big Five model
├── core/
│   ├── config.py       # Configuration constants
│   ├── database.py     # SQLAlchemy models
│   ├── memory.py       # MemoBase API + cache management
│   ├── notifications.py # HTTP notification service
│   ├── pipeline.py     # Core processing pipeline
│   └── logger.py       # Structured logging
├── data/               # Runtime data (SQLite, models cache)
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## External Services

Before running, ensure these services are running:

- **Ollama**: `http://localhost:11434` with model specified in `OLLAMA_MODEL`
- **MemoBase**: `http://localhost:8019` (default) for long-term memory storage

```bash
# Start Ollama
ollama serve
ollama pull qwen2.5:3b-instruct

# Optional: start MemoBase
# docker run -p 8019:8019 memobase:latest
```
