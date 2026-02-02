# AI Voice-First Chatbot Stack

Voice-first chatbot with real-time dashboard, long-term memory, emotion/personality analysis, and benchmarking suite.

## Demo
<video controls src="demo.mov"></video>

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interface                              │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend (React + Vite)     │  CLI Voice Interface                 │
│  http://localhost:3000       │  python -m app.app                   │
└──────────────┬───────────────┴──────────────┬───────────────────────┘
               │ SSE + REST                    │
               ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Backend API (Flask)                              │
│                    http://localhost:5000                            │
├─────────────────────────────────────────────────────────────────────┤
│  • REST endpoints for dashboard data                                │
│  • SSE streaming for real-time updates                              │
│  • Webhook receivers for chatbot events                             │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Chatbot Pipeline                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Audio In → Whisper STT → LLM (Ollama) → Kokoro TTS → Audio Out    │
│                    │              │                                 │
│            Emotion Analysis   Memory Integration                    │
│           (Speech + Text)     (MemoBase)                           │
│                    │              │                                 │
│         Personality Detection    │                                  │
│            (Big Five)            │                                  │
└──────────────────────────────────┼──────────────────────────────────┘
                                   │
               ┌───────────────────┼───────────────────┐
               ▼                   ▼                   ▼
┌──────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   Ollama (LLM)       │ │   MemoBase      │ │  HuggingFace Models │
│   :11434             │ │   :8019         │ │  (Local Cache)      │
│   qwen2.5:3b-instruct│ │   PostgreSQL    │ │  • Whisper          │
│                      │ │   Redis         │ │  • DeBERTa          │
│                      │ │                 │ │  • BERT             │
└──────────────────────┘ └─────────────────┘ └─────────────────────┘
```

## Project Structure

```
ai_agent_project/
├── chatbot/                    # Python backend
│   ├── app/
│   │   ├── app.py              # Interactive voice CLI
│   │   ├── server.py           # Flask REST/SSE API
│   │   └── sync.py             # Memory cache sync
│   ├── audio/                  # Audio processing
│   │   ├── recorder.py         # Audio recording (sounddevice)
│   │   ├── stt.py              # Whisper speech-to-text
│   │   └── tts.py              # Kokoro text-to-speech
│   ├── models/                 # AI models
│   │   ├── llm.py              # Ollama LLM client
│   │   ├── personality.py      # Big Five detection
│   │   └── emotion/            # Emotion recognition
│   ├── core/                   # Core modules
│   │   ├── config.py           # Configuration
│   │   ├── memory.py           # MemoBase integration
│   │   └── pipeline.py         # Processing pipeline
│   ├── benchmark/              # Evaluation suite
│   └── requirements.txt
├── frontend/                   # React + Vite dashboard
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── api/client.ts       # API client
│   │   └── audio/              # Streaming audio player
│   └── package.json
├── memobase/                   # Long-term memory (Docker)
│   └── src/server/
│       ├── docker-compose.yml
│       └── .env
├── start_all.sh                # Start all services
└── stop_all.sh                 # Stop all services
```

---

## Deployment Guide

### Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Docker | Latest | `docker --version` |
| Docker Compose | v2+ | `docker compose version` |
| Ollama | Latest | `ollama --version` |
| CUDA (optional) | 11.8+ | `nvidia-smi` |

### Hardware Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 16GB
- Storage: 30GB SSD
- GPU: Optional (CPU inference supported)

**Recommended:**
- CPU: 8+ cores
- RAM: 32GB
- Storage: 50GB+ NVMe SSD
- GPU: NVIDIA RTX 4060+ (8GB+ VRAM)

---

### Step 1: Clone and Setup Environment

```bash
git clone <repository-url> ai_agent_project
cd ai_agent_project

# Create HuggingFace cache directory (adjust path as needed)
export HF_HOME=/path/to/huggingface/cache
mkdir -p $HF_HOME
```

### Step 2: Install Ollama and Pull Model

```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve &

# Pull default model (or choose another)
ollama pull qwen2.5:3b-instruct

# Optional: Pull additional models for benchmarking
ollama pull qwen2.5:7b-instruct
ollama pull gemma3:4b
ollama pull phi3:3.8b
```

### Step 3: Setup MemoBase (Long-term Memory)

MemoBase provides long-term memory storage using PostgreSQL + Redis.

> For detailed MemoBase configuration, refer to the [MemoBase repository](https://github.com/memodb-io/memobase).

```bash
cd memobase/src/server

# Configure environment (edit as needed)
cp .env.example .env  # if exists, or edit .env directly

# Default .env configuration:
# DATABASE_PASSWORD=helloworld
# REDIS_PASSWORD=helloworld
# API_EXPORT_PORT=8019
# ACCESS_TOKEN=secret

# Start MemoBase services
docker compose up -d

# Verify services are running
docker compose ps
# Should show: memobase-server-db, memobase-server-redis, memobase-server-api

# Check API health
curl http://localhost:8019/health
```

### Step 4: Install Python Dependencies

```bash
cd chatbot

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For GPU support, ensure PyTorch CUDA version matches your driver
# pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Step 5: Install Frontend Dependencies

```bash
cd frontend
npm install
```

### Step 6: Configure Environment

Edit `chatbot/core/config.py` or set environment variables:

```bash
# Required
export HF_HOME=/path/to/huggingface/cache
export OLLAMA_MODEL=qwen2.5:3b-instruct

# Optional overrides
export MEMOBASE_PROJECT_URL=http://localhost:8019
export MEMOBASE_API_KEY=secret
export USE_KOKORO=true  # Set to false for pyttsx3 fallback
export KOKORO_DEVICE=auto  # cpu|cuda|auto
```

### Step 7: Download Models (First Run)

Models are downloaded automatically on first use. To pre-download:

```bash
cd chatbot

# Pre-download Whisper model
python -c "from audio.stt import load_whisper_pipeline; load_whisper_pipeline()"

# Pre-download emotion models
python -c "from models.emotion import load_speech_emotion_model, load_text_emotion_model; load_speech_emotion_model(); load_text_emotion_model()"

# Pre-download personality model
python -c "from models.personality import load_personality_model; load_personality_model()"
```

---

## Running the Stack

### Quick Start (All Services)

```bash
./start_all.sh
```

This starts:
1. MemoBase (Docker) - Port 8019
2. Backend API (Flask) - Port 5000
3. Frontend (Vite) - Port 3000
4. Chatbot CLI (foreground)

### Manual Start (Individual Services)

```bash
# Terminal 1: MemoBase
cd memobase/src/server && docker compose up -d

# Terminal 2: Backend API
cd chatbot && python -m app.server

# Terminal 3: Frontend
cd frontend && npm run dev

# Terminal 4: Voice Chatbot CLI
cd chatbot && python -m app.app
```

### Stop All Services

```bash
./stop_all.sh
```

---

## Port Reference

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| Frontend | 3000 | http://localhost:3000 | React dashboard |
| Backend API | 5000 | http://localhost:5000 | Flask REST/SSE |
| MemoBase | 8019 | http://localhost:8019 | Memory API |
| PostgreSQL | 15432 | - | MemoBase database |
| Redis | 16379 | - | MemoBase cache |
| Ollama | 11434 | http://localhost:11434 | LLM inference |

---

## API Endpoints

### Dashboard Data
- `GET /api/dashboard/{user_id}` - Full dashboard data
- `GET /api/memories/{user_id}` - User memories (profiles + events)
- `GET /api/stream/{user_id}` - SSE real-time stream
- `GET /api/config` - System configuration
- `GET /health` - Health check

### Memory Management
- `DELETE /api/profile/{profile_id}?user_id={uid}` - Delete profile
- `DELETE /api/event/{event_id}?user_id={uid}` - Delete event

### Real-time Updates (Chatbot → Frontend)
- `POST /api/notify/{user_id}` - Trigger dashboard refresh
- `POST /api/user-input/{user_id}` - Push user transcription
- `POST /api/stream-chunk/{user_id}` - Push text stream chunk
- `POST /api/audio-chunk/{user_id}` - Push audio stream chunk
- `POST /api/status/{user_id}` - Push processing status

---

## Configuration Reference

### Key Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_HOME` | `~/.cache/huggingface` | HuggingFace model cache |
| `OLLAMA_MODEL` | `qwen2.5:3b-instruct` | LLM model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama API URL |
| `MEMOBASE_PROJECT_URL` | `http://localhost:8019` | MemoBase API URL |
| `MEMOBASE_API_KEY` | `secret` | MemoBase access token |
| `USE_KOKORO` | `true` | Use Kokoro TTS (vs pyttsx3) |
| `KOKORO_DEVICE` | `auto` | TTS device (cpu/cuda/auto) |
| `KOKORO_VOICE` | `af_heart` | TTS voice preset |
| `DEFAULT_SPEAKER` | `test_user` | Default user name |

### Model Paths

| Model | Purpose | Size |
|-------|---------|------|
| `openai/whisper-large-v3-turbo` | Speech-to-text | ~1.5GB |
| `Tanneru/Emotion-Classification-DeBERTa-v3-Large` | Text emotion | ~900MB |
| `Minej/bert-base-personality` | Big Five personality | ~440MB |
| `hexgrad/Kokoro-82M` | Text-to-speech | ~320MB |
| Custom CNN+Transformer | Speech emotion | ~100MB |

---

## Benchmarking

Run LLM evaluation with 12 metrics:

```bash
cd chatbot/benchmark

# Full benchmark (100 samples, ~30 min)
python batch_evaluate_ollama.py

# Quick test (10 samples)
python batch_evaluate_ollama.py --limit 10

# Compare multiple models
python batch_evaluate_ollama.py --models qwen2.5:3b-instruct gemma3:4b phi3:3.8b
```

Results are saved to `benchmark/results/`.

---

## Troubleshooting

### Ollama Connection Failed
```bash
# Check if Ollama is running
lsof -i :11434
curl http://localhost:11434/api/tags

# Restart Ollama
sudo systemctl restart ollama
# or: ollama serve
```

### MemoBase Not Starting
```bash
cd memobase/src/server

# Check Docker logs
docker compose logs -f memobase-server-api

# Rebuild containers
docker compose down && docker compose up -d --build
```

### Frontend Can't Connect to API
```bash
# Check backend is running
curl http://localhost:5000/health

# Check Vite proxy config in frontend/vite.config.ts
```

### Model Download Timeout
```bash
# Set HuggingFace mirror (if needed)
export HF_ENDPOINT=https://hf-mirror.com

# Pre-download with retry
huggingface-cli download openai/whisper-large-v3-turbo
```

### Audio Device Issues
```bash
# List audio devices
python -c "import sounddevice; print(sounddevice.query_devices())"

# Set specific input device in chatbot/core/config.py
# or use environment variable
export AUDIO_INPUT_DEVICE=0
```

---

## Bluetooth Audio (Optional)

Connect to Bluetooth speaker (e.g., Yamaha THR10II):

```bash
# Start PulseAudio
pulseaudio --start

# Connect to device
bluetoothctl connect <MAC_ADDRESS>

# Set as default output
pactl set-default-sink bluez_sink.<MAC_ADDRESS>.a2dp_sink

# Test
aplay /tmp/test.wav
```

---

## License

MIT License
