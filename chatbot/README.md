# AI Voice Chatbot

Voice chatbot with Whisper STT, NeuTTS/Piper TTS, fused emotion analysis, Big Five personality, and MemoBase-backed memory.

## Run
```bash
cd chatbot
python -m app.app           # Interactive voice CLI
python -m app.server        # REST/SSE backend for the dashboard
```
Key flags (CLI): `--history-window`, `--speech-emotion-weight`, `--text-emotion-weight`, `--debug`.  
Toggle TTS engines via env: `USE_NEUTTS=true` (default), `USE_PIPER_TTS=true` or both false to fall back to pyttsx3.

## Features
- Whisper transcription with configurable recording (hold-to-talk or timed).
- Emotion fusion (speech + text) and personality extraction; Ollama model configurable via `OLLAMA_MODEL`.
- Long-term memory through MemoBase; short-term cache in SQLite (`data/memories.sqlite`) and JSON (`data/memory_cache.json`).
- Backend exposes `/api/dashboard/<user_id>`, `/api/stream/<user_id>`, `/api/notify/<user_id>` plus memory CRUD endpoints consumed by the frontend.

## Layout
- `app/app.py` – interactive loop and audio pipeline setup.
- `app/server.py` – Flask API + SSE streaming.
- `audio/` – STT/TTS engines (Whisper, NeuTTS, Piper).
- `models/` – emotion and personality models.
- `core/` – configuration, DB, logging, and pipeline utilities.
