# AI Agent Project - Models & Repositories Reference

> Complete Inventory of Models and Repositories

**Last Updated**: 2025-11-18
**Project**: AI Agent Chatbot with Emotion & Personality Analysis

---

## 📋 Table of Contents

1. [Speech-to-Text Models](#1-speech-to-text-models)
2. [Personality Analysis Models](#2-personality-analysis-models)
3. [Text Emotion Detection Models](#3-text-emotion-detection-models)
4. [Speech Emotion Detection Models](#4-speech-emotion-detection-models)
5. [PDF Parsing Models](#5-pdf-parsing-models)
6. [Large Language Models (LLMs)](#6-large-language-models-llms)
7. [Memory & Database Systems](#7-memory--database-systems)
8. [Frontend Frameworks](#8-frontend-frameworks--libraries)
9. [Backend API Framework](#9-backend-api-framework)
10. [Cloned/Modified Repositories](#10-clonedmodified-repositories)
11. [External Services](#11-external-services)
12. [Model Storage Locations](#12-model-storage-locations)
13. [Summary by Component](#13-summary-by-component)

---

## 1. Speech-to-Text Models

### Whisper Large-v3-Turbo
- **Model ID**: `openai/whisper-large-v3-turbo`
- **Source**: [HuggingFace](https://huggingface.co/openai/whisper-large-v3-turbo)
- **Purpose**: Automatic Speech Recognition (ASR) - converts audio to text
- **Location**: `chatbot/modules/speech2text.py`
- **Framework**: Hugging Face Transformers Pipeline
- **Model Path**: `/mnt/ssd/huggingface/hub/models--openai--whisper-large-v3-turbo/snapshots/41f01f3fe87f28c78e2fbf8b568835947dd65ed9`
- **Configuration**:
  - Batch size: 48
  - GPU-accelerated (float16) when CUDA available
  - Language: English
  - Device: Automatic (GPU/CPU fallback)

---

## 2. Personality Analysis Models

### BERT-Base-Personality
- **Model ID**: `Minej/bert-base-personality`
- **Source**: [HuggingFace](https://huggingface.co/Minej/bert-base-personality)
- **Purpose**: Big Five personality trait detection
- **Location**: `chatbot/modules/personality.py`
- **Framework**: Hugging Face Transformers (BertTokenizer + BertForSequenceClassification)
- **Output Traits**:
  - Extraversion
  - Neuroticism
  - Agreeableness
  - Conscientiousness
  - Openness
- **Output Range**: 0.0 - 1.0 (normalized)
- **Storage**: SQLite database (`memories.sqlite`)
- **Optimization**: CUDA with TF32 acceleration

---

## 3. Text Emotion Detection Models

### DeBERTa-v3-Large (Emotion Classification)
- **Model ID**: `Tanneru/Emotion-Classification-DeBERTa-v3-Large`
- **Source**: [HuggingFace](https://huggingface.co/Tanneru/Emotion-Classification-DeBERTa-v3-Large)
- **Purpose**: Text-based emotion classification
- **Location**: `chatbot/modules/text2emotion.py`
- **Framework**: Hugging Face Transformers (AutoTokenizer + AutoModelForSequenceClassification)
- **Output Classes** (7 emotions):
  - anger
  - disgust
  - fear
  - happy
  - neutral
  - sad
  - surprise
- **Features**:
  - Fast/slow tokenizer auto-detection
  - GPU-optimized with TF32 acceleration
  - Softmax normalization for probabilities
- **Weighting in Final Emotion**: 40% (configurable 0.0-1.0)

---

## 4. Speech Emotion Detection Models

### Model A: Wav2Vec2 English Speech Emotion Recognition
- **Model ID**: `r-f/wav2vec-english-speech-emotion-recognition`
- **Source**: [HuggingFace](https://huggingface.co/r-f/wav2vec-english-speech-emotion-recognition)
- **Purpose**: Audio-based emotion recognition
- **Location**: `chatbot/modules/emotion.py` (Deprecated/Alternative)
- **Framework**: Hugging Face Transformers (Wav2Vec2FeatureExtractor + Wav2Vec2ForSequenceClassification)
- **Output Classes**: 7 emotions
- **Features**:
  - fp16 precision for GPU inference
  - 16kHz audio resampling
  - Mono conversion for stereo audio
  - HF_HOME: `/mnt/ssd/huggingface`

### Model B: Parallel CNN + Transformer (Custom Model)
- **Model Architecture**: Parallel 2D CNN + Transformer Encoder
- **Source**: [GitHub - Speech-Emotion-Classification-with-PyTorch](https://github.com/Data-Science-kosta/Speech-Emotion-Classification-with-PyTorch)
- **Purpose**: Speech emotion recognition (Primary model)
- **Location**: `chatbot/modules/speech2emotion.py`
- **Model File**: `cnn_transf_parallel_model.pt` (symlink to `/mnt/ssd/speech2emo_model/cnn_transf_parallel_model.pt`)
- **Input Specifications**:
  - Sample rate: 48kHz
  - Clip duration: 3 seconds
  - Mel-spectrogram features (128 bins)
  - Mel-frequency range: 0-24kHz
- **Architecture Details**:
  - 4-layer Conv2D blocks with max pooling
  - Transformer encoder (4 layers, 4 attention heads)
  - Output: 8 emotion classes (normalized to 7 for consistency)
- **Output Classes**: anger, disgust, fear, happy, neutral, sad, surprise
- **Weighting in Final Emotion**: 60% (configurable 0.0-1.0)

---

## 5. PDF Parsing Models

### MinerU (Multi-Modal PDF Parser)
- **Package**: `magic-pdf` (MinerU CLI)
- **Source**: [OpenDataLab MinerU](https://opendatalab.github.io/MinerU/)
- **Purpose**: PDF to Markdown conversion with OCR and layout analysis
- **Location**: `agentic-report-gen/pdf_to_markdown.py`
- **Framework**: MinerU library (PyTorch-based)
- **Supported Languages**:
  - English, Chinese, Korean, Japanese, French, German, Arabic, Russian, etc.
- **Features**:
  - Multi-language OCR support
  - GPU acceleration (PyTorch 2.7.0 + CUDA 12.6)
  - ARM64 optimized (Nvidia Jetson Orin)
  - Optional formula and table parsing (disabled by default)
  - Multiple backends: pipeline, vlm-transformers, vlm-vllm-engine, vlm-http-client
- **Performance**:
  - GPU mode: ~1.3 seconds/page
  - CPU mode: ~19 seconds/page
- **Environment Variables**:
  - `MINERU_DEVICE_MODE`: cuda/cpu
  - `MINERU_MODEL_SOURCE`: huggingface
  - `OMP_NUM_THREADS`: 1 (ARM64 compatibility)
- **Documentation**: `agentic-report-gen/README.md`

---

## 6. Large Language Models (LLMs)

### Ollama-Served Models
- **Default Model**: `gemma3:1b`
- **Service**: Ollama (Local LLM service)
- **Endpoint**: http://localhost:11434
- **Client**: OpenAI Python library (OpenAI-compatible API)
- **Purpose**: Conversational AI responses with MemoBase context injection
- **Location**: `chatbot/modules/llm.py`
- **Configuration**:
  - Base URL: `http://localhost:11434/v1`
  - Temperature: 0.7
  - Max tokens: 256
  - Streaming: Enabled
- **Tested/Supported Models**:
  - `gemma3:1b` (default)
  - `mistral:7b-instruct`
  - `qwen2.5:7b-instruct`
  - `llama3.1:8b` (legacy tests)

---

## 7. Memory & Database Systems

### MemoBase (Vector Database)
- **Repository**: https://github.com/memodb-io/memobase
- **Purpose**: Long-term memory storage with semantic search
- **Location**: `memobase/`
- **Service Type**: Docker container
- **Port**: 8019
- **API Version**: api/v1
- **Key Dependencies**:
  - pydantic
  - httpx
  - openai
- **Features**:
  - Chat blob insertion
  - User profile management
  - Event storage and retrieval
  - Semantic search via embeddings
- **API Endpoints**:
  - `/users/profile/{uuid}`
  - `/users/event/{uuid}`
  - `/chat` (blob insertion)

### MemoBase Inspector
- **Repository**: https://github.com/memodb-io/memobase-inspector
- **Purpose**: Web-based UI for MemoBase visualization and management
- **Location**: `memobase-inspector/`
- **Technology Stack**:
  - React 18
  - TypeScript
  - Radix UI
  - Floating UI
  - AI SDK
- **Features**: Browse and manage profiles, events, and chat history

### SQLite Database
- **Purpose**: Store Big Five personality traits and user profiles
- **Location**: `chatbot/memories.sqlite`
- **Framework**: SQLAlchemy ORM
- **Tables**:
  - `users`
  - `personality_traits`
  - `memories` (legacy)

### Memory Cache (JSON)
- **Purpose**: Session-based conversation caching
- **Location**: `chatbot/memory_cache.json`
- **Structure**:
  ```json
  {
    "user_uuid": {
      "sessions": {
        "date": {
          "conversations": []
        }
      }
    }
  }
  ```
- **Sync**: Auto-sync every 2 seconds via SSE (Server-Sent Events)

---

## 8. Frontend Frameworks & Libraries

### React Dashboard
- **Framework**: React 18.2.0
- **Build Tool**: Vite 5.0.8
- **Language**: TypeScript 5.3.3
- **Location**: `frontend/`
- **Port**: 3000

**Key Dependencies**:
- **Styling**: Tailwind CSS 3.4.0, PostCSS 8.4.32
- **Charting**: Recharts 2.10.3
- **HTTP Client**: Axios 1.6.2
- **UI Components**: Radix UI (Dialog, Dropdown Menu)

**Main Components**:
- `Dashboard.tsx` - Main dashboard container
- `DualRadarChart.tsx` - Personality trait visualization
- `MemoryViewer.tsx` - Profile/Event management with delete functionality
- `TranscriptionDisplay.tsx` - Live transcription display

**Features**:
- Real-time SSE updates
- Delete profiles/events with confirmation dialogs
- Hover-to-reveal delete buttons
- Responsive design

---

## 9. Backend API Framework

### Flask REST API
- **Framework**: Flask 3.0.0
- **CORS**: flask-cors 4.0.0
- **Purpose**: Backend API server for frontend communication
- **Location**: `chatbot/backend_api.py`
- **Port**: 5000
- **HTTP Client**: requests 2.31.0

**API Endpoints**:
- `GET /api/dashboard/{userId}` - Full dashboard data
- `GET /api/memories/{userId}` - Profiles and events (topk=1000)
- `GET /api/stream/{userId}` - SSE real-time stream
- `DELETE /api/profile/{profileId}?user_id={userId}` - Delete profile
- `DELETE /api/event/{eventId}?user_id={userId}` - Delete event
- `GET /health` - Health check

**Features**:
- Aggregates data from MemoBase, SQLite, and memory cache
- SSE polling every 2 seconds
- UUID mapping via `uuid.uuid5`

---

## 10. Cloned/Modified Repositories

### Main Project Repository
- **Name**: ai_agent_chatbot
- **Owner**: SCAI-Lab
- **Repository**: https://github.com/SCAI-Lab/ai_agent_chatbot.git
- **Location**: `/home/user/ai_agent/ai_agent_project/`
- **Branch**: main
- **Contains**:
  - Chatbot module
  - Frontend React dashboard
  - Backend Flask API
  - MemoBase (cloned)
  - MemoBase Inspector (cloned)
  - PDF to Markdown tool (agentic-report-gen)

### MemoBase (Cloned Repository)
- **Upstream**: https://github.com/memodb-io/memobase
- **Origin**: https://github.com/SCAI-Lab/ai_agent_chatbot.git
- **Type**: Cloned and modified
- **Purpose**: Vector database for long-term memory
- **Location**: `memobase/`

### MemoBase Inspector (Cloned Repository)
- **Upstream**: https://github.com/memodb-io/memobase-inspector
- **Type**: Cloned and modified
- **Purpose**: Web UI for MemoBase management
- **Location**: `memobase-inspector/`

### Speech Emotion Model Source
- **Repository**: https://github.com/Data-Science-kosta/Speech-Emotion-Classification-with-PyTorch
- **Type**: Referenced (model architecture adopted)
- **Model File**: Custom-trained `cnn_transf_parallel_model.pt`

---

## 11. External Services

### Ollama
- **Type**: Local LLM inference service
- **Port**: 11434
- **API**: REST API on `/v1` (OpenAI-compatible)
- **Default Model**: `gemma3:1b`
- **Purpose**: LLM inference for conversational responses
- **Configuration**: Managed via environment variable `OLLAMA_MODEL`

### CUDA Toolkit
- **Version**: 12.6
- **Platform**: Nvidia Jetson Orin (ARM64)
- **Purpose**: GPU acceleration for PyTorch and MinerU
- **Optimizations**: TF32, fp16 mixed precision

---

## 12. Model Storage Locations

### HuggingFace Cache
**Base Path**: `/mnt/ssd/huggingface/`

- **Whisper**:
  `/mnt/ssd/huggingface/hub/models--openai--whisper-large-v3-turbo/snapshots/41f01f3fe87f28c78e2fbf8b568835947dd65ed9`
- **BERT Personality**: Auto-cached by transformers
- **Wav2Vec2**: Auto-cached by transformers
- **DeBERTa**: Auto-cached by transformers

### Custom Models
**Base Path**: `/mnt/ssd/speech2emo_model/`

- **Speech Emotion CNN+Transformer**:
  `/mnt/ssd/speech2emo_model/cnn_transf_parallel_model.pt`

### Project Local Models
**Base Path**: `chatbot/models/`

- Symlink to speech emotion model: `cnn_transf_parallel_model.pt` → `/mnt/ssd/speech2emo_model/cnn_transf_parallel_model.pt`

---

## 13. Summary by Component

### Chatbot Module (6 ML Models)
| Component | Model | Purpose |
|-----------|-------|---------|
| Speech-to-Text | Whisper Large-v3-Turbo | ASR transcription |
| Personality | BERT-Base-Personality | Big Five traits |
| Text Emotion | DeBERTa-v3-Large | Text emotion detection |
| Speech Emotion (Primary) | CNN+Transformer Parallel | Audio emotion detection |
| Speech Emotion (Alternative) | Wav2Vec2 | Audio emotion detection |
| LLM | Ollama (gemma3:1b) | Conversational responses |

### agentic-report-gen Module (1 Tool)
| Component | Tool | Purpose |
|-----------|------|---------|
| PDF Parser | MinerU | PDF to Markdown with OCR |

### Frontend Module (React Ecosystem)
| Component | Library | Purpose |
|-----------|---------|---------|
| Framework | React 18.2.0 | UI framework |
| Build Tool | Vite 5.0.8 | Development & build |
| Styling | Tailwind CSS 3.4.0 | Utility-first CSS |
| Charting | Recharts 2.10.3 | Data visualization |
| HTTP | Axios 1.6.2 | API requests |

### Backend Modules (3 Systems)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| REST API | Flask 3.0.0 | HTTP server |
| Database | SQLite + SQLAlchemy | Persistent storage |
| Vector DB | MemoBase (Docker) | Long-term memory |
| Cache | JSON file | Session cache |

### External Services (2)
| Service | Port | Purpose |
|---------|------|---------|
| Ollama | 11434 | LLM inference |
| MemoBase | 8019 | Vector database |

---

## 📊 Quick Reference Table

| Category | Count | Examples |
|----------|-------|----------|
| HuggingFace Models | 4 | Whisper, BERT, DeBERTa, Wav2Vec2 |
| Custom Models | 1 | CNN+Transformer Parallel |
| Cloned Repositories | 3 | MemoBase, MemoBase Inspector, Main Project |
| External Services | 2 | Ollama, CUDA |
| Frontend Frameworks | 1 | React + Vite |
| Backend Frameworks | 1 | Flask |
| Databases | 3 | SQLite, MemoBase, JSON Cache |
| PDF Tools | 1 | MinerU |
| **Total Components** | **16** | - |

---

## 🔧 Configuration Files

| Component | Configuration File | Key Settings |
|-----------|-------------------|--------------|
| Chatbot | `modules/config.py` | WHISPER_MODEL_PATH, OLLAMA_MODEL, MEMOBASE_PROJECT_URL, emotion weights |
| Frontend | `package.json` | React 18, Vite, Recharts, Tailwind CSS |
| Backend API | `backend_api.py` | Flask, CORS, memory_cache polling |
| MemoBase | Docker config | Port 8019, API v1 |
| PDF Parser | `pdf_to_markdown.py` | MinerU, PyTorch 2.7, CUDA 12.6 |

---

## 📦 Core Python Dependencies

**Deep Learning & ML**:
- PyTorch >=2.0.0 (2.7.0 on Jetson)
- Transformers >=4.30.0
- Sentencepiece >=0.1.99

**Audio Processing**:
- Librosa (speech processing)
- Sounddevice >=0.4.6 (audio I/O)
- Soundfile (WAV file handling)

**Data & Computing**:
- NumPy >=1.24.0
- Pandas >=2.0.0
- SciPy >=1.10.0

**Backend & API**:
- Flask 3.0.0
- SQLAlchemy >=2.0.0
- OpenAI >=1.0.0 (Ollama client)
- HTTPX >=0.24.0
- Requests 2.31.0

**Utilities**:
- Pyttsx3 >=2.90 (Text-to-Speech)
- Loguru (MinerU logging)
- Rich (console output)

---

## 🌐 External Resources

- **HuggingFace Hub**: https://huggingface.co/
- **Ollama Models**: https://ollama.com/library
- **MinerU Docs**: https://opendatalab.github.io/MinerU/
- **MemoBase GitHub**: https://github.com/memodb-io/memobase
- **Speech Emotion Model**: https://github.com/Data-Science-kosta/Speech-Emotion-Classification-with-PyTorch

---

## 📝 Notes

1. **Default User**: Frontend uses `test1` by default (see `frontend/src/components/Dashboard.tsx`)
2. **UUID Mapping**: Uses deterministic UUID generation via `uuid.uuid5`
3. **Emotion Weighting**: Speech emotion (60%) + Text emotion (40%) = Final emotion
4. **GPU Optimization**: TF32 enabled for Ampere+ GPUs, fp16 for older architectures
5. **ARM64 Compatibility**: OMP_NUM_THREADS=1 required for ONNX Runtime stability
6. **Model Caching**: All HuggingFace models cached to `/mnt/ssd/huggingface/` for faster loading

---

**End of Document** | 