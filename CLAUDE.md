# AI Agent Project

## ⚠️ CRITICAL: Package Management Rules

**IMPORTANT**: When working with Python packages:

1. **NEVER uninstall or modify existing packages without explicit user approval**
   - Do NOT use `pip uninstall` without asking first
   - Do NOT use `--force-reinstall` without asking first
   - Do NOT downgrade/upgrade critical packages without asking first

2. **Installing NEW packages is OK**
   - You can use `pip install <package>` for new packages
   - You can install additional dependencies as needed

3. **When package conflicts occur:**
   - Report the conflict to the user
   - Ask for permission before making any changes
   - Explain what needs to be changed and why

**Example Good Practice:**
```
"I need to install numpy<2.0 for compatibility, but this will downgrade your current numpy 2.2.6.
May I proceed with this change?"
```

**Example Bad Practice:**
```
pip install numpy<2.0 --force-reinstall  # ❌ Don't do this without asking!
```

## Repository Structure

This repository contains 6 main components:

### 1. chatbot/
**Core AI chatbot with voice interaction and memory**
- Voice input/output using Whisper STT and **GPU-accelerated Piper TTS** (pyttsx3 as fallback)
- **Streaming TTS:** Real-time synthesis with 0.5x RTF (synthesis 2x faster than playback)
- Dual-source emotion analysis (speech + text) with configurable fusion
- Big Five personality trait detection (BERT-based)
- Long-term memory via MemoBase integration
- SQLite for personality storage (`data/memories.sqlite`), JSON cache for conversations (`data/memory_cache.json`)
- **Port:** Runs in terminal (interactive)
- **Entry point:** `chatbot/chatbot_cli.py`
- **Details:** See `chatbot/CLAUDE.md` for internal workflow

### 2. api_server.py (in chatbot/)
**Flask REST API server - Data aggregation layer**
- Aggregates data from 3 sources: SQLite (personality), `data/memory_cache.json` (emotions/conversations), MemoBase API (profiles/events)
- Provides unified data to frontend via REST endpoints
- Server-Sent Events (SSE) for real-time push updates
- Memory management: Delete profiles/events from MemoBase
- **Port:** 5000
- **Entry point:** `chatbot/api_server.py`
- **API Endpoints:**
  - `GET /api/dashboard/{userId}` - Full dashboard data (emotion, personality, profiles, events, transcription)
  - `GET /api/memories/{userId}` - Profiles and events only
  - `GET /api/stream/{userId}` - SSE stream for real-time updates
  - `POST /api/notify/{userId}` - Trigger push update to connected clients (called by chatbot)
  - `DELETE /api/profile/{profileId}?user_id={userId}` - Delete profile from MemoBase
  - `DELETE /api/event/{eventId}?user_id={userId}` - Delete event from MemoBase
  - `GET /health` - Health check
- **Note:** Events API uses `topk=1000` to fetch up to 1000 events (default was 10)

### 3. frontend/
**React-based real-time visualization dashboard**
- Displays emotion radar charts (speech vs text), Big5 personality, user profiles, events, and conversation transcription
- Memory management UI: Hover-to-delete buttons with confirmation dialogs
- Real-time updates via SSE (Server-Sent Events) - no polling needed
- Responsive layout with expandable/collapsible sections
- **Port:** 3000
- **Entry point:** `npm run dev` in frontend/
- **Default user:** `test1` (hardcoded in Dashboard.tsx)

### 4. agentic-report-gen/
**High-performance PDF to Markdown converter**
- GPU-accelerated using MinerU (PyTorch 2.7.0 + CUDA 12.6)
- Optimized for ARM64 (Nvidia Jetson Orin)
- Multi-language OCR support (English, Chinese, Korean, Japanese, etc.)
- **Performance:** GPU ~1.3s/page vs CPU ~19s/page (10-15x faster)
- **Entry point:** `agentic-report-gen/tools/pdf_to_markdown.py`
- **Output:** Markdown files in `data/markdown/` with extracted images
- **Details:** See `agentic-report-gen/README.md`

### 5. memobase/
**Long-term memory storage system (Docker service)**
- Vector database for semantic search and memory retrieval
- Stores user profiles and events with timestamps
- Cloned and modified from open-source repository
- **Port:** 8019
- **API Base URL:** `http://localhost:8019/api/v1`
- **Documentation:** https://github.com/memodb-io/memobase

### 6. memobase-inspector/
**Web-based memory database inspection tool**
- Frontend for visualizing and managing MemoBase data
- Query, filter, and explore stored memories
- Cloned and modified from open-source repository
- **Documentation:** https://github.com/memodb-io/memobase-inspector

## System Architecture

### Component Interaction Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                        │
│                     (Voice Input/Output)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CHATBOT (chatbot_cli.py)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Whisper STT (transcription)                           │   │
│  │ 2. Parallel: Speech emotion + Text emotion + Personality │   │
│  │ 3. MemoBase context fetch (long-term memory)             │   │
│  │ 4. LLM streaming response generation (Ollama)            │   │
│  │ 5. Streaming GPU TTS (Piper) or fallback (pyttsx3)      │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────┬─────────────────────────────────┬───────────────────────┘
        │                                 │
        │ Writes personality              │ Writes emotions/conversations
        ▼                                 ▼
 ┌───────────────────┐           ┌──────────────────────────┐
 │      SQLite       │           │ data/memory_cache.json   │
 │data/memories.db   │           │      (JSON file)         │
 └───────────────────┘           └──────────────────────────┘
        │                                 │
        │                                 │ sync_memory.py (manual)
        │                                 ▼
        │                          ┌─────────────────┐
        │                          │    MemoBase     │
        │                          │  (Port 8019)    │
        │                          │ Vector Database │
        │                          └─────────────────┘
        │                                 │
        ├─────────────────────────────────┤
        │                                 │
        │         READ                    │ READ
        ▼                                 ▼
┌────────────────────────────────────────────────────────────────┐
│              BACKEND API (api_server.py:5000)                  │
│  Aggregates: SQLite + data/memory_cache.json + MemoBase API   │
│  Provides: REST endpoints + SSE real-time stream              │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             │ HTTP + SSE
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND (React Dashboard:3000)                    │
│  Real-time display: Emotions, Personality, Profiles, Events    │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Summary
1. **User speaks** → Chatbot processes (Whisper + Emotion + Personality analysis)
2. **LLM generates** → Streaming response with real-time GPU TTS synthesis (Piper)
3. **Data saved** → SQLite (personality in `data/memories.sqlite`) + `data/memory_cache.json` (emotions/conversations)
4. **Data synced** → MemoBase (profiles/events) - manual sync via `sync_memory.py`
5. **Backend API** → Aggregates data from all 3 sources, pushes via SSE
6. **Frontend** → Displays via SSE real-time updates (push-based, not polling)

## Running the System

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Ollama running locally (port 11434) with `gemma3:1b` model
- MemoBase running (Docker, port 8019)
- Microphone for audio input (chatbot)
- CUDA-capable GPU (optional, for faster inference)

### Start All Services (Recommended)
```bash
./start_all.sh
```
This script automatically:
1. Checks dependencies (Python, Node.js, npm)
2. Installs missing packages if needed
3. Starts Backend API (port 5000) in background
4. Starts Frontend (port 3000) in background
5. Starts Chatbot (interactive mode) in foreground

**Logs:**
- Backend: `tail -f /tmp/api_server.log`
- Frontend: `tail -f /tmp/frontend.log`

**To stop:** Press `Ctrl+C` (will stop all services)

### Start Individual Components
```bash
# Backend API only
cd chatbot && ./start_backend.sh
# OR manually: python api_server.py

# Frontend only
cd frontend && npm run dev

# Chatbot only
cd chatbot && python chatbot_cli.py
# With custom emotion weights: python chatbot_cli.py --speech-emotion-weight 0.6 --text-emotion-weight 0.4
# Disable GPU TTS (use pyttsx3): USE_PIPER_TTS=false python chatbot_cli.py

# PDF to Markdown tool
cd agentic-report-gen
python tools/pdf_to_markdown.py document.pdf  # GPU mode (default)
python tools/pdf_to_markdown.py document.pdf --device cpu  # CPU mode
```

## Data Storage Locations

- **Big5 Personality**: `chatbot/data/memories.sqlite` (persistent, cumulative averaging)
- **Emotions + Conversations**: `chatbot/data/memory_cache.json` (session cache)
- **Profiles + Events**: MemoBase (long-term, after sync via `sync_memory.py`)

## Git Workflow Instructions

When performing git operations (add, commit, push), follow these important guidelines:

### Before Any Git Operations:
1. **Verify Repository Context**
   - Check that you're working in the user's repository, NOT the original upstream repositories
   - Confirm the status of `memobase` and `memobase-inspector` submodules/components

2. **Check for Upstream Updates**
   - Check if there are any updates from the original repositories
   - Inform the user about any available updates
   - Ask the user whether they want to pull and merge upstream changes before proceeding

### Git Operations:
- Use the GitHub MCP tool for all git operations
- Ensure changes are staged and committed to the correct repository
- Follow proper commit message conventions

## Important Notes

- **Default User**: Frontend uses `test1` by default (see `frontend/src/components/Dashboard.tsx`)
- **User UUID Mapping**: Uses deterministic UUID generation via `uuid.uuid5`
- **MemoBase API Paths**:
  - Profiles: `/users/profile/{uuid}` (NOT `/users/{uuid}/profiles`)
  - Events: `/users/event/{uuid}` (NOT `/users/{uuid}/events`)
- **SSE Update Interval**: Backend polls `data/memory_cache.json` every 2 seconds
- **Emotion Default Values**: Uniform distribution (1/7 ≈ 0.143 for each emotion)
- **Big5 Default Values**: Neutral values at 0.5 for each trait

## PDF to Markdown Tool (agentic-report-gen/)

### Overview
High-performance PDF to Markdown conversion tool using MinerU, optimized for ARM64 (Nvidia Jetson Orin).

### Location
`/home/user/ai_agent/ai_agent_project/agentic-report-gen/tools/pdf_to_markdown.py`

### Quick Start
```bash
cd agentic-report-gen
python tools/pdf_to_markdown.py document.pdf  # Default: GPU accelerated
python tools/pdf_to_markdown.py document.pdf --device cpu  # Force CPU mode
python tools/pdf_to_markdown.py document.pdf --lang ch  # Chinese PDF
```

### Key Features
- ✅ GPU acceleration (PyTorch 2.7.0 + CUDA 12.6) - **10-15x faster than CPU**
- ✅ ARM64 optimized (fixes ONNX Runtime threading issues)
- ✅ Multi-language OCR support (English, Chinese, Korean, Japanese, etc.)
- ✅ Default GPU mode for best performance
- ⚠️ Formula and table parsing disabled by default for stability

### Performance
- **GPU mode**: ~1.3 seconds/page (30-40 seconds for 8-page PDF)
- **CPU mode**: ~19 seconds/page (5-7 minutes for 8-page PDF)

### Output
- Default: `./data/markdown/document_name/auto/document_name.md`
- Includes extracted images in `images/` subdirectory
- JSON metadata files for debugging

### Documentation
- `agentic-report-gen/README.md` - Detailed documentation
- `agentic-report-gen/USAGE.txt` - Quick reference guide

### Important Notes
- Default device is CUDA (GPU) for optimal performance
- Formula/table parsing can be enabled with `--enable-formula` and `--enable-table` flags
- ARM64 threading issues resolved via environment variables (OMP_NUM_THREADS=1)
- Automatic CUDA fallback to CPU if GPU not available

