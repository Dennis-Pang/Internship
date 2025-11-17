# AI Agent Chatbot Project

An intelligent chatbot system with long-term memory capabilities, featuring voice interaction, personality modeling, and real-time dashboard visualization.

## Project Overview

This repository houses a complete AI chatbot solution with advanced memory management, designed to deliver personalized conversational experiences through context retention and learning from past interactions.

## Project Components

### [agentic-report-gen/](agentic-report-gen/)
High-performance PDF to Markdown conversion tool using MinerU, optimized for **Nvidia Jetson Orin** (ARM64 + CUDA).

**Key Features:**
- GPU acceleration (10-15x faster than CPU)
- Multi-language OCR support (English, Chinese, Korean, Japanese, etc.)
- ARM64 optimized (PyTorch 2.7.0 + CUDA 12.6)
- Default GPU mode for best performance

**Quick Start:**
```bash
cd agentic-report-gen
python pdf_to_markdown.py document.pdf  # GPU accelerated
python pdf_to_markdown.py document.pdf --lang ch  # Chinese PDF
```

**Performance:**
- GPU mode: ~1.3 seconds/page (30-40 seconds for 8-page PDF)
- CPU mode: ~19 seconds/page (5-7 minutes for 8-page PDF)

**See [agentic-report-gen/README.md](agentic-report-gen/README.md) for detailed documentation**

### [chatbot/](chatbot/)
A custom AI chatbot optimized for **Nvidia Orin 64GB** platform, featuring sophisticated memory integration and natural conversation capabilities.

**Core Capabilities:**
- Persistent long-term memory for personalized interactions
- Dual-source emotion analysis (speech + text)
- Big Five personality trait detection
- Real-time voice interaction support
- Flask REST API for dashboard integration
- Hardware-optimized performance for Nvidia Orin

**See [chatbot/README.md](chatbot/README.md) for detailed documentation**

### [frontend/](frontend/)
React-based dashboard for real-time visualization of chatbot data.

**Features:**
- Real-time emotion and personality visualization
- User profile and event memory display with management capabilities
- Delete profiles and events with confirmation dialogs
- Live conversation transcription
- Server-Sent Events (SSE) for automatic updates

### [memobase/](memobase/)
Backend memory management system providing robust infrastructure for conversational data storage, retrieval, and organization.

**Documentation:** https://github.com/memodb-io/memobase

### [memobase-inspector/](memobase-inspector/)
Web-based frontend for visualizing and managing the memory database, offering intuitive tools for inspection and interaction.

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
