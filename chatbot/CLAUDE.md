# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Voice Chatbot with personality analysis and long-term memory. Combines speech recognition (Whisper), Big Five personality detection (BERT), and conversational memory (MemoBase + SQLite) to provide personalized voice interactions.

## Essential Commands

### Running the Application
```bash
# Basic usage (default: 60% speech + 40% text emotion)
python main.py

# With custom conversation history window
python main.py --history-window 10

# Debug mode (prints full prompts sent to LLM)
python main.py --debug
```

### Emotion Analysis Control

The application supports dual-source emotion analysis with configurable weighting:

```bash
# Use only speech-based emotion (faster, audio-only)
python main.py --speech-emotion-weight 1.0 --text-emotion-weight 0.0

# Use only text-based emotion (text content only)
python main.py --speech-emotion-weight 0.0 --text-emotion-weight 1.0

# Custom weighted fusion (e.g., 70% speech, 30% text)
python main.py --speech-emotion-weight 0.7 --text-emotion-weight 0.3
```

**Weight Configuration:**
- `--speech-emotion-weight`: 0.0-1.0 (default: 0.6, set to 0 to disable loading)
- `--text-emotion-weight`: 0.0-1.0 (default: 0.4, set to 0 to disable loading)

**Fusion Method:**
- Simple probability averaging: `p = λ * p_speech + (1-λ) * p_text`
- Weights are automatically normalized
- Output probabilities sum to 1.0

**Emotion Classes (7 total):**
- anger, disgust, fear, happy, neutral, sad, surprise

### Syncing Memory Cache to MemoBase
```bash
# Sync cached conversations to MemoBase
python sync_memory_cache.py --batch-size 10
```

### Dependencies
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install torch transformers
pip install sounddevice scipy numpy
pip install pyttsx3 sqlalchemy pandas
pip install openai requests httpx sentencepiece
```

### External Services
Before running, ensure these services are running:
- **Ollama**: Must be running on `http://localhost:11434` with `gemma3:1b` model pulled
- **MemoBase**: Long-term memory service (default: `http://localhost:8019`)

```bash
# Start Ollama and pull model
ollama serve
ollama pull gemma3:1b
```

## Architecture Overview

### Processing Pipeline
The chatbot follows a carefully optimized pipeline that balances **serial and parallel execution** for optimal performance.

#### Key Design Principles:
- **Startup:** Conservative sequential + selective parallel loading (stability over speed)
- **Runtime:** Aggressive parallelization where safe (speed over simplicity)
- **GPU Safety:** Avoid concurrent large model loading (prevents CUDA OOM)

### Detailed Workflow: Startup vs Runtime

---

#### 🚀 **STARTUP SEQUENCE** (main.py lines 699-803)

The initialization sequence is carefully orchestrated to balance speed and stability:

**Phase 1: Sequential Fast Operations**
```
[1] Database init (SQLAlchemy)           ~0.02s
    ↓
[2] TTS engine init                      ~0.03s
    ↓
[3] Big5 Personality model load          ~2.5s
    (MUST be sequential - PyTorch 2.7 meta tensor issues with parallel loading)
```

**Phase 2: Parallel Emotion Models** ⚡
```
    ├─ [4a] Speech2Emotion model         ~3.3s ┐
    │                                          ├─→ Wall clock: ~3.3s (max, not sum)
    └─ [4b] Text2Emotion model           ~3.0s ┘

    ✓ Safe to parallelize: Both are small models (~500MB each)
    ✓ No GPU conflicts during concurrent loading
```

**Phase 3: Sequential Large Model**
```
[5] Whisper STT model                    ~1.6s
    (MUST be sequential - Large 3GB+ model, avoid GPU memory conflicts)
    ↓
[6] Ollama connection check              ~0.05s
```

**Total Startup Time: ~5.0 seconds**

**Why Not All Parallel?**
- **PyTorch 2.7 Issue:** Concurrent GPU model init causes "Cannot copy out of meta tensor" errors
- **GPU Memory:** Whisper (3GB+) + others would cause OOM
- **Trade-off:** Could be ~3-4s if all parallel, but unstable

---

#### ⚡ **RUNTIME PROCESSING** (process_audio function, lines 499-631)

Per-conversation processing is heavily parallelized for speed:

**Phase 1: Parallel Audio Analysis** (lines 532-542)
```
Audio File (WAV)
    ├─ [1a] Whisper transcription        ~1.7s  ← Critical path
    │       (CUDA accelerated)
    │
    └─ [1b] Speech emotion analysis      ~2.2s
            (Transformer+CNN, runs in parallel)

⚠️ Transcription MUST complete before Phase 2 (text needed)
```

**Phase 2: Wait for Text, Then Parallel Multi-Task** (lines 549-562)
```
Transcription Complete → "Q: [user text]"
    │
    ├─ [2a] Text emotion analysis        ~1.4s
    │       (DeBERTa-v3-Large)
    │
    ├─ [2b] Big5 personality analysis    ~0.2s
    │       (BERT)
    │
    └─ [2c] MemoBase context fetch       ~0.15s
            (Semantic search via API)

✓ All three run concurrently (ThreadPoolExecutor)
✓ Wall clock time = max(1.4s, 0.2s, 0.15s) = ~1.4s (not 1.75s sum)
```

**Phase 3: Sequential Final Steps**
```
[3] Log emotion scores                   ~0.001s
    ↓
[4] Build prompt context                 ~0.002s
    (Combine: emotions + personality + memory + history)
    ↓
[5] LLM generation (Ollama)              ~3.5s
    - Memory injection: ~0.15s (already done in parallel)
    - First token: ~2.8s
    - Full response: ~3.5s
    ↓
[6] Save to database & cache             ~0.01s
    - SQLite: Personality traits
    - JSON: Conversations + emotions
    ↓
[7] Notify dashboard backend             ~0.05s
    (POST to backend_api.py)
    ↓
[8] TTS voice output                     ~1.2s
    (pyttsx3 speech synthesis)
```

**Total Processing Time: ~6.8 seconds**
- Audio analysis (parallel): ~2.2s (not 3.9s)
- Text-based tasks (parallel): ~1.4s (not 1.75s)
- LLM + TTS (sequential): ~4.7s

---

#### 📊 **Parallelization Summary**

| Stage | Parallel Tasks | Wall Clock | Serial Would Be |
|-------|---------------|------------|-----------------|
| Startup: Emotion models | 2 models | ~3.3s | ~6.3s |
| Runtime: Audio analysis | Whisper + Speech emotion | ~2.2s | ~3.9s |
| Runtime: Text analysis | Text emotion + Personality + Memory | ~1.4s | ~1.75s |

**Total Time Saved: ~4.05 seconds per conversation** ⚡

---

### Module Responsibilities

Below are the individual modules and their roles:

1. **Audio Input** → `modules/audio.py`
   - Records 5-second audio clips via sounddevice
   - Supports multiple input devices with timeout protection
   - Saves to temporary WAV file

2. **Speech-to-Text** → `modules/speech2text.py`
   - Uses Whisper Large-v3-Turbo via transformers pipeline
   - GPU-accelerated (CUDA) if available
   - Batch size: 48

3. **Speech Emotion** → `modules/speech2emotion.py`
   - Transformer+CNN model for acoustic emotion analysis
   - 7 classes: anger, disgust, fear, happy, neutral, sad, surprise
   - Returns logits (for fusion) or probabilities

4. **Text Emotion** → `modules/text2emotion.py`
   - DeBERTa-v3-Large model for semantic emotion analysis
   - Same 7 emotion classes (aligned with speech emotion)
   - Returns logits (for fusion) or probabilities

5. **Personality Analysis** → `modules/personality.py`
   - BERT-based Big Five trait detection (`Minej/bert-base-personality`)
   - Returns: Extraversion, Neuroticism, Agreeableness, Conscientiousness, Openness
   - Cached globally, loaded once at startup

6. **Context Building** → `build_prompt_context()` in main.py
   - Combines: short-term history (sliding window), personality traits, user preferences
   - Formats into system prompt with delimited sections
   - Injects both speech and text emotion data

7. **LLM Chat** → `modules/llm.py`
   - Uses Ollama via OpenAI client interface
   - Fetches long-term memory from MemoBase API (parallel with other tasks)
   - Injects MemoBase context into system prompt
   - Streams response with TTFT (time-to-first-token) tracking

8. **Database Storage** → `modules/database.py`
   - SQLAlchemy models for users and personality traits
   - Raw SQL for memories table (legacy compatibility)
   - Stores personality updates per conversation

9. **Memory Caching** → `modules/memory.py`
   - Appends conversations to JSON cache (`memory_cache.json`)
   - Session-based structure: `{user_uuid: {sessions: {date: {conversations: []}}}}`
   - Tracks timings: speech_to_text, llm_generation, total
   - Provides MemoBase API wrappers

10. **Text-to-Speech** → `modules/audio.py`
    - pyttsx3 engine for voice responses
    - Rate: 200, Volume: 0.8

### Key Architectural Patterns

**Application State Management**
- Uses `ApplicationState` dataclass to encapsulate all application state (no global variables in main.py)
- Contains: `whisper_pipeline`, `current_speaker`, `preferences`, `history_window_size`, `selected_device_index`, `debug_mode`, `conversation_states`
- `_model`, `_tokenizer`, `_device`: Personality model globals in `modules/personality.py` (loaded once at startup)
- Each speaker has a `ConversationState` with conversation history and greeting status

**Memory Hierarchy**
- **Short-term**: File-based (`memory_cache.json`), sliding window (configurable via `--history-window`, default 5 rounds)
  - Messages written immediately after user input and assistant response
  - History loaded from file for each conversation
  - No in-memory history storage (persistent across restarts)
- **Long-term**: MemoBase API with semantic search for relevant past conversations
- **Personality**: SQLite database, updated after each interaction
- **Preferences**: Stored in database (placeholder, not actively used yet)

**Timing System** (`modules/timing.py`)
- Decorator: `@timing("operation_name")`
- Context manager: `with timing_context("operation_name"):`
- Direct recording: `_record_timing(name, duration)`
- Preserves execution order for performance analysis

## Configuration

All configuration in `modules/config.py`:

### Critical Paths
- `WHISPER_MODEL_PATH`: Local path to Whisper model snapshot (default: `/mnt/ssd/huggingface/hub/models--openai--whisper-large-v3-turbo/...`)
- `DB_PATH`: SQLite database location (`memories.sqlite` in project root)
- `MEMORY_CACHE_FILE`: JSON cache for conversations (`memory_cache.json` in project root)

### Tunable Parameters
- `DEFAULT_HISTORY_WINDOW`: Short-term conversation rounds (default: 5)
- `RECORD_DURATION`: Audio recording length in seconds (default: 5)
- `OLLAMA_MODEL`: LLM model name (default: `gemma3:1b`)
- `OLLAMA_TEMPERATURE`: Response randomness (default: 0.7)
- `OLLAMA_MAX_TOKENS`: Max response length (default: 256)
- `DEFAULT_MAX_CONTEXT_SIZE`: MemoBase context token limit (default: 1000)

### Environment Variables
- `MEMOBASE_PROJECT_URL`: MemoBase API base URL
- `MEMOBASE_API_KEY`: Auth token for MemoBase
- `LOG_LEVEL`: Logging verbosity (default: INFO)

## Development Notes

### Working with Memory Systems
When modifying memory/context logic:
- **Short-term memory** is stored in `memory_cache.json` with immediate file writes
  - `append_message_to_cache()`: Writes individual messages immediately
  - `get_recent_history()`: Reads recent conversation history from file
  - `format_short_term_memory()`: Formats history for prompt inclusion
- **Long-term memory** injection happens in `modules/llm.py:chat()` via `inject_memobase_context()`
- Both are combined in `build_prompt_context()` in main app
- Context sections use delimited markers: `--# SECTION NAME #--` ... `--# END OF SECTION NAME #--`

**Important**: History is now file-based, not in-memory. Each conversation:
1. Writes user message to file immediately after transcription
2. Reads recent history from file before generating response
3. Writes assistant response to file immediately after generation

### MemoBase Integration
- User UUIDs are deterministic (generated via `uuid.uuid5` from speaker name)
- Must call `ensure_memobase_user()` before first context fetch
- Context retrieval uses recent chat history for semantic search
- API wrapper in `modules/memory.py` with `memobase_request()` helper

### Adding New Personality Traits
The personality analysis returns 5 values in fixed order:
```python
[extraversion, neuroticism, agreeableness, conscientiousness, openness]
```
Database schema in `modules/database.py:User` model must be updated if adding traits.

### Audio Device Handling
- Device selection happens once per session (stored in `selected_device_index`)
- Timeout protection: `duration + 2s` margin to prevent hanging
- Non-blocking stop mechanism using threading for robustness
- Validation includes channel count and sample rate checks

### Timing Best Practices
- Use `@timing()` decorator for functions
- Use `timing_context()` for code blocks
- Use `_record_timing()` for manual measurements within functions
- Call `clear_timings()` at start of each processing cycle
- Call `print_timings()` to display ordered performance summary

## Current Limitations & TODOs

From README.md:
- Personality analysis needs updates (consider more recent models)
- Multi-agent architecture not yet implemented
- Optional RAG for semantic context enhancement
- Long-term memory terms need refinement
- Test coverage is minimal

## File Organization

```
main.py                        # Main entry point, orchestrates pipeline
sync_memory_cache.py           # Utility to sync cache to MemoBase
memories.sqlite                # SQLite database (users, memories)
memory_cache.json              # Conversation history cache (session-based)

modules/
├── config.py                  # All configuration constants
├── audio.py                   # Recording (sounddevice) + TTS (pyttsx3)
├── speech.py                  # Whisper pipeline loading + transcription
├── personality.py             # BERT Big Five model + prediction
├── llm.py                     # Ollama chat + MemoBase integration
├── memory.py                  # MemoBase API + short/long-term formatting
├── database.py                # SQLAlchemy models + personality storage
└── timing.py                  # Performance measurement utilities

legacy/                        # Legacy/backup files
├── app_new_legacy.py          # Old monolithic version
└── personality_old.py         # Old personality module

tests/                         # Various test scripts (not automated suite)
data/models/                   # Personality model cache directory
```
## 注意

代码不要过度封装,保持良好的可读性和可维护性
除非用户要求，不要随便添加新的文件，包括.py和.md文件