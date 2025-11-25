# AI Agent Chatbot Project

An intelligent chatbot system with long-term memory capabilities, featuring voice interaction, personality modeling, and real-time dashboard visualization.

## Project Overview

This repository houses a complete AI chatbot solution with advanced memory management, designed to deliver personalized conversational experiences through context retention and learning from past interactions.

**Key Features:**
- Voice-powered AI with dual-source emotion analysis (speech + text)
- Big Five personality trait detection
- Long-term memory via MemoBase vector database
- Real-time visualization dashboard with SSE updates
- GPU-accelerated PDF to Markdown conversion
- Optimized for Nvidia Jetson Orin (ARM64 + CUDA)

## System Architecture Overview

```
User Voice Input → Chatbot (Whisper + Emotion + Personality)
                      ↓
              SQLite + memory_cache.json
                      ↓
                  MemoBase API
                      ↓
              Backend API (Flask)
                      ↓
              Frontend Dashboard (React)
```

## Project Components

### 1. [chatbot/](chatbot/) - Core AI Voice Chatbot
**Voice-powered AI with personality analysis and long-term memory**

**Core Capabilities:**
- **Voice I/O:** Whisper Large-v3-Turbo (STT) + pyttsx3 (TTS)
- **Dual-Source Emotion:** Speech-based (Transformer+CNN) + Text-based (DeBERTa-v3-Large) with configurable fusion (default: 60% speech + 40% text)
- **Personality Analysis:** Big Five traits using BERT-based model (Extraversion, Neuroticism, Agreeableness, Conscientiousness, Openness)
- **Long-term Memory:** MemoBase integration for semantic search and context retrieval
- **Data Storage:** SQLite (personality), JSON cache (conversations/emotions)
- **LLM:** Ollama local inference (default: gemma3:1b)

**Entry Point:** `chatbot/main.py`

**Quick Start:**
```bash
cd chatbot
python main.py  # Default: 60% speech + 40% text emotion
python main.py --speech-emotion-weight 1.0 --text-emotion-weight 0.0  # Speech-only (faster)
python main.py --history-window 10  # Custom conversation window
```

**See [chatbot/README.md](chatbot/README.md) for detailed documentation**

### 2. [chatbot/backend_api.py](chatbot/backend_api.py) - Backend API Server
**Flask REST API for dashboard data aggregation**

**Responsibilities:**
- Aggregates data from 3 sources: SQLite (personality), memory_cache.json (emotions/conversations), MemoBase API (profiles/events)
- Provides REST endpoints for frontend
- Server-Sent Events (SSE) for real-time push updates
- Memory management: Delete profiles/events from MemoBase

**Port:** 5000

**Key Endpoints:**
- `GET /api/dashboard/{userId}` - Full dashboard data
- `GET /api/stream/{userId}` - SSE real-time stream
- `DELETE /api/profile/{profileId}` - Delete profile
- `DELETE /api/event/{eventId}` - Delete event

### 3. [frontend/](frontend/) - Real-time Visualization Dashboard
**React-based dashboard for chatbot data visualization**

**Features:**
- **Real-time Updates:** SSE (Server-Sent Events) - push-based, no polling
- **Emotion Visualization:** Dual radar charts (speech vs text emotions)
- **Personality Display:** Big Five traits radar chart
- **Memory Management:** View and delete user profiles/events with confirmation dialogs
- **Conversation Transcription:** Live display of user/assistant dialogue
- **Responsive UI:** Expandable/collapsible sections with hover-to-delete buttons

**Port:** 3000
**Default User:** `test1` (configurable in Dashboard.tsx)

**Quick Start:**
```bash
cd frontend
npm install
npm run dev
```

### 4. [agentic-report-gen/](agentic-report-gen/) - PDF to Markdown Converter
**High-performance PDF conversion using MinerU, optimized for Nvidia Jetson Orin**

**Key Features:**
- **GPU Acceleration:** PyTorch 2.7.0 + CUDA 12.6 (10-15x faster than CPU)
- **ARM64 Optimized:** Fixes ONNX Runtime threading issues
- **Multi-language OCR:** English, Chinese, Korean, Japanese, etc.
- **Performance:** GPU ~1.3s/page vs CPU ~19s/page

**Entry Point:** `agentic-report-gen/tools/pdf_to_markdown.py`

**Quick Start:**
```bash
cd agentic-report-gen
python tools/pdf_to_markdown.py document.pdf  # GPU accelerated (default)
python tools/pdf_to_markdown.py document.pdf --device cpu  # Force CPU mode
python tools/pdf_to_markdown.py document.pdf --lang ch  # Chinese PDF
```

**Output:** `data/markdown/document_name/auto/document_name.md`

**See [agentic-report-gen/README.md](agentic-report-gen/README.md) for detailed documentation**

### 5. [memobase/](memobase/) - Long-term Memory System
**Vector database for semantic memory storage and retrieval**

**Responsibilities:**
- Stores user profiles and events with timestamps
- Semantic search for relevant past conversations
- User-specific memory isolation

**Port:** 8019
**API Base URL:** `http://localhost:8019/api/v1`

**Documentation:** https://github.com/memodb-io/memobase

### 6. [memobase-inspector/](memobase-inspector/) - Memory Database Inspector
**Web-based tool for visualizing and managing MemoBase data**

**Features:**
- Query and filter stored memories
- Explore user profiles and events
- Debug and inspect memory data

**Documentation:** https://github.com/memodb-io/memobase-inspector

## Quick Start

### Option 1: Start Everything (Recommended)

```bash
./start_all.sh
```

This launches:
- Backend API (port 5000)
- Frontend Dashboard (port 3000)
- Chatbot (interactive mode)

Access the dashboard at: **http://localhost:3000**

### Option 2: Start Components Separately

**Backend API only:**
```bash
cd chatbot
./start_backend.sh
```

**Frontend only:**
```bash
cd frontend
npm run dev
```

**Chatbot only:**
```bash
cd chatbot
python main.py
```

## Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Frontend   │ ◄─────► │  Backend    │ ◄─────► │  MemoBase   │
│  (React)    │         │  Flask API  │         │  Service    │
│  Port 3000  │         │  Port 5000  │         │  Port 8019  │
└─────────────┘         └─────────────┘         └─────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │ SQLite DB   │
                        │ + Cache     │
                        └─────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  Chatbot    │
                        │  (Voice I/O)│
                        └─────────────┘
```

## Data Flow

1. **User speaks** → Chatbot processes (Whisper + Emotion + Personality)
2. **Data saved** → SQLite (Big5) + memory_cache.json (emotions + conversations)
3. **Data synced** → MemoBase (profiles + events)
4. **Backend API** → Fetches data from all sources
5. **Frontend** → Displays via SSE real-time updates

## Prerequisites

- Python 3.10
- Node.js 18+ and npm
- CUDA-capable GPU (optional, for faster inference)
- Microphone for audio input
- Ollama running locally (port 11434)
- Docker (for MemoBase)

## Installation

### 1. Set up MemoBase (Memory System)

Follow the official installation guide:
```bash
# See: https://github.com/memodb-io/memobase
docker compose up -d
```

### 2. Set up Python Environment

```bash
cd chatbot
pip install -r requirements.txt
```

### 3. Set up Frontend

```bash
cd frontend
npm install
```

### 4. Configure Services

**Chatbot configuration** (`chatbot/modules/config.py`):
```python
MEMOBASE_PROJECT_URL = "http://localhost:8019"
MEMOBASE_API_KEY = "secret"
DEFAULT_SPEAKER = "test1"
```

**Frontend configuration** (`frontend/.env`):
```bash
VITE_API_URL=http://localhost:5000/api
```

## API Endpoints

Backend API provides:
- `GET /api/dashboard/{userId}` - Complete dashboard data
- `GET /api/memories/{userId}` - Profiles and events only
- `GET /api/stream/{userId}` - SSE real-time updates
- `DELETE /api/profile/{profileId}?user_id={userId}` - Delete a specific profile
- `DELETE /api/event/{eventId}?user_id={userId}` - Delete a specific event
- `GET /health` - Health check

**Note:** Event API uses `topk=1000` parameter to retrieve up to 1000 events (default was 10).

## Port Usage

- **3000**: Frontend (React + Vite)
- **5000**: Backend API (Flask)
- **8019**: MemoBase server
- **11434**: Ollama LLM service

## Frontend Features

### Memory Management
The frontend dashboard includes memory management capabilities:

**Viewing Memories:**
- Switch between "Profiles" and "Events" tabs
- Expand/collapse profile topics
- View full conversation history and event details

**Deleting Memories:**
1. Hover over any profile or event card
2. Click the red trash icon that appears in the top-right corner
3. Confirm deletion in the popup dialog
4. The item will be permanently deleted from MemoBase
5. Dashboard automatically refreshes to show updated data

**Important Notes:**
- Deletions are permanent and cannot be undone
- The system displays up to 1000 most recent events
- Profiles are not limited by count

### Real-time Updates
- Dashboard polls `memory_cache.json` every 2 seconds
- Automatic updates via Server-Sent Events (SSE)
- No manual refresh needed

## Troubleshooting

**Frontend shows no data:**
1. Check if backend API is running: `curl http://localhost:5000/health`
2. Verify MemoBase is running: `docker logs -f memobase-server-api`
3. Check user ID matches: Frontend uses `test1` by default

**Emotions not updating:**
1. Run a conversation with the chatbot
2. Data will auto-save to `memory_cache.json`
3. Frontend will update via SSE within 2 seconds

**Profiles/Events empty:**
1. Sync cache to MemoBase: `python sync_memory_cache.py`
2. Check MemoBase API: `curl http://localhost:8019/api/v1/users/profile/{uuid}`

**Only 10 events showing (before fix):**
- Old behavior: MemoBase API defaulted to `topk=10`
- Current behavior: Backend now uses `topk=1000` to fetch up to 1000 events
- If using old backend, restart the backend API service

**Delete button not showing:**
1. Make sure you're hovering over the profile/event card
2. Check browser console for errors
3. Ensure backend API endpoints are accessible

## License

Each component maintains its own license. Please check individual directories for details.
