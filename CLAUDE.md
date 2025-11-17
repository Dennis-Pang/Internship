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

This repository contains 5 main components:

### 1. chatbot
- **Custom-developed chatbot implementation**
- Voice-powered AI with personality analysis and emotion detection
- Integrates with MemoBase for long-term memory
- See `chatbot/CLAUDE.md` for detailed documentation

### 2. frontend
- **React-based dashboard for real-time visualization**
- Displays emotion, personality, profiles, and events
- Memory management: Delete profiles and events with confirmation dialogs
- Hover-to-reveal delete buttons with smooth transitions
- Uses Server-Sent Events (SSE) for live updates
- Port: 3000

### 3. backend_api.py (in chatbot/)
- **Flask REST API server**
- Provides data to frontend dashboard
- Aggregates data from MemoBase, SQLite, and memory cache
- Port: 5000
- **API Endpoints:**
  - `GET /api/dashboard/{userId}` - Full dashboard data
  - `GET /api/memories/{userId}` - Profiles and events
  - `GET /api/stream/{userId}` - SSE real-time stream
  - `DELETE /api/profile/{profileId}?user_id={userId}` - Delete profile
  - `DELETE /api/event/{eventId}?user_id={userId}` - Delete event
  - `GET /health` - Health check
- **Important:** Events API uses `topk=1000` to fetch up to 1000 events instead of default 10

### 4. memobase
- Cloned and modified from open-source repository
- Used for long-term memory/data storage functionality
- Port: 8019

### 5. memobase-inspector
- Cloned and modified from open-source repository
- Used for inspecting and debugging memory data

## System Architecture

```
User speaks → Chatbot (voice processing)
              ↓
        [Emotion + Personality Analysis]
              ↓
        SQLite + memory_cache.json
              ↓
        MemoBase (sync via sync_memory_cache.py)
              ↓
        Backend API (Flask) ← Frontend Dashboard
              ↓
        Real-time display (SSE)
```

## Running the System

### Start All Services
```bash
./start_all.sh
```
This starts backend API (5000), frontend (3000), and chatbot.

### Start Individual Components
```bash
# Backend API only
cd chatbot && ./start_backend.sh

# Frontend only
cd frontend && npm run dev

# Chatbot only
cd chatbot && python main.py
```

## Data Storage Locations

- **Big5 Personality**: `chatbot/memories.sqlite` (persistent, cumulative averaging)
- **Emotions + Conversations**: `chatbot/memory_cache.json` (session cache)
- **Profiles + Events**: MemoBase (long-term, after sync)

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
- **SSE Update Interval**: Backend polls memory_cache.json every 2 seconds
- **Emotion Default Values**: Uniform distribution (1/7 ≈ 0.143 for each emotion)
- **Big5 Default Values**: Neutral values at 0.5 for each trait

## PDF to Markdown Tool (agentic-report-gen/)

### Overview
High-performance PDF to Markdown conversion tool using MinerU, optimized for ARM64 (Nvidia Jetson Orin).

### Location
`/home/user/ai_agent/ai_agent_project/agentic-report-gen/pdf_to_markdown.py`

### Quick Start
```bash
cd agentic-report-gen
python pdf_to_markdown.py document.pdf  # Default: GPU accelerated
python pdf_to_markdown.py document.pdf --device cpu  # Force CPU mode
python pdf_to_markdown.py document.pdf --lang ch  # Chinese PDF
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

