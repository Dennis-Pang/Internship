# AI Agent Project

Voice-first chatbot stack with real-time dashboard, long-term memory, benchmarks, and PDF tooling.

## What's Inside
- `chatbot/` – voice chatbot pipeline (Whisper STT, NeuTTS/Piper TTS, emotion/personality analysis, MemoBase memory) plus Flask REST/SSE backend.
- `frontend/` – React + Vite dashboard that streams live metrics from the backend.
- `memobase/` – embedded MemoBase server plus MCP server and Go/TS clients.
- `chatbot/tests/` – regression and benchmark suites (conversation extraction, prompt sweeps, Ollama cache tests, Whisper accuracy).
- `chatbot/benchmark/` – LLM-as-judge benchmark and 100-sample dataset for memory citation.
- `agentic-report-gen/` – MinerU-based PDF → Markdown converter (GPU-first, ARM64 friendly).
- `neutts/` – on-device TTS models and runnable examples.

## Run the Stack
Prereqs: Python 3.10+, Node 18+, Docker, Ollama (for local LLMs).

```bash
./start_all.sh  # starts MemoBase (docker), chatbot API, and frontend
# Dashboard: http://localhost:3000  (API on :5000, MemoBase on :8019)
```

Manual entry points:
```bash
cd chatbot && python -m app.server   # REST/SSE backend
cd chatbot && python -m app.app      # interactive voice chatbot
cd frontend && npm install && npm run dev
```

## Ports
- 3000: Frontend dashboard
- 5000: Chatbot API
- 8019: MemoBase
- 11434: Ollama (LLM runtime)
