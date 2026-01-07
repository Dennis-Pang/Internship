# Dataset Structure

This directory contains the benchmark dataset for evaluating LLM memory citation and personalization quality in healthcare conversational contexts.

## Overview

- **Total Samples**: 100 (IDs: 001-100)
- **Domain**: Healthcare advice and behavior change support
- **Context**: Multi-turn dialogues with user personality, emotions, and memory

## Directory Structure

```
dataset/
├── README.md                    # This file
├── generate_speech.py           # TTS generation script (OpenAI API)
├── build_prompts.py            # Prompt template and formatting utilities
├── sample_processing.py        # Full pipeline: TTS → emotion/personality → context/prompt
└── samples/                    # Sample data directory
    ├── 001/
    │   ├── sample.json         # Raw sample data
    │   ├── query.wav           # TTS-generated audio (last user message)
    │   ├── context.json        # Processed context (personality, emotion, preferences)
    │   └── prompt.md           # Complete prompt for LLM evaluation
    ├── 002/
    │   └── ...
    └── 100/
        └── ...
```

## Sample Structure

Each sample is stored in `samples/{id}/` (e.g., `samples/001/`) and contains 4 files:

### 1. `sample.json` - Raw Sample Data

Core sample information including dialogue history, memory, and evaluation constraints.

**Structure:**
```json
{
  "id": "001",
  "dialogue": [
    {
      "role": "user|assistant",
      "content": "Message text"
    }
  ],
  "memory": {
    "key1": "value1",
    "key2": "value2"
  },
  "must_use_keys": ["key1", "key2"],
  "must_not_use_keys": ["key3"]
}
```

**Fields:**
- `id` (string): Sample identifier (001-100)
- `dialogue` (array): Conversation history leading up to the user's final message
  - `role`: "user" or "assistant"
  - `content`: Message text
- `memory` (object): Key-value pairs of user profile information known to the system
  - Examples: medication type, behavioral patterns, preferences, context details
- `must_use_keys` (array): Memory keys that **must** be referenced in the response (for evaluation)
- `must_not_use_keys` (array): Memory keys that **must not** be mentioned (testing selective memory use)

**Purpose:**
- Provides conversation context and user profile information
- Defines constraints for memory utilization evaluation (Precision/Recall/F1)

**Example:**
```json
{
  "id": "001",
  "dialogue": [
    {"role": "user", "content": "I keep missing my medication sometimes."},
    {"role": "assistant", "content": "That's common. Do you notice it more on weekdays or weekends?"},
    {"role": "user", "content": "Mostly weekends. My mornings look different and I forget."}
  ],
  "memory": {
    "medication_type": "daily blood pressure pill",
    "forgetting_pattern": "mornings on weekends",
    "tech_comfort": "high",
    "wake_time_shift": "wakes ~2 hours later on weekends"
  },
  "must_use_keys": ["medication_type", "forgetting_pattern", "tech_comfort"],
  "must_not_use_keys": ["wake_time_shift"]
}
```

---

### 2. `query.wav` - TTS-Generated Audio

Audio file of the **last user message** in the dialogue, generated using OpenAI TTS API (voice: "shimmer").

**Specifications:**
- **Format**: WAV (uncompressed)
- **Sample Rate**: 24,000 Hz
- **Channels**: Mono
- **Encoding**: PCM 16-bit
- **Typical Size**: 100-200 KB
- **Duration**: 3-6 seconds (varies by message length)

**Purpose:**
- Enables speech emotion analysis using acoustic features
- Supports dual-source emotion analysis (speech + text)

**Generation:**
```bash
# Generate TTS for all samples
python generate_speech.py

# Regenerate TTS for specific sample
python generate_speech.py --sample-id 001 --force
```

---

### 3. `context.json` - Processed Context

Derived data containing analyzed personality traits, fused emotion probabilities, and formatted preferences. This file is **generated** by `sample_processing.py` from `sample.json` + audio analysis.

**Structure:**
```json
{
  "USER_PERSONALITY": "Extraversion: 0.41\nNeuroticism: 0.55\nAgreeableness: 0.47\nConscientiousness: 0.36\nOpenness: 0.44",
  "EMOTION_LOGITS": "anger: 0.00\ndisgust: 0.00\nfear: 0.00\nhappy: 0.06\nneutral: 0.79\nsad: 0.15\nsurprise: 0.00",
  "KNOWN_PREFERENCES": "medication_type: daily blood pressure pill\nforgetting_pattern: mornings on weekends\ntech_comfort: high\n...",
  "USER_MESSAGE": "If it worked for weekend mornings, I'd finally be consistent."
}
```

**Fields:**
- `USER_PERSONALITY` (string): Big Five personality trait scores (0-1 scale)
  - Model: `Minej/bert-base-personality` (BERT-based)
  - Traits: Extraversion, Neuroticism, Agreeableness, Conscientiousness, Openness
  - Analyzed from the last user message text

- `EMOTION_LOGITS` (string): Fused emotion probability distribution (7 classes)
  - Classes: anger, disgust, fear, happy, neutral, sad, surprise
  - Fusion: 60% speech emotion (from `query.wav`) + 40% text emotion (default weights)
  - Speech model: CNN+Transformer acoustic model
  - Text model: DeBERTa-v3-Large

- `KNOWN_PREFERENCES` (string): Formatted memory key-value pairs from `sample.json`
  - Direct mapping from `memory` field

- `USER_MESSAGE` (string): The last user message (extracted from dialogue)

**Purpose:**
- Provides evaluation context for judge models
- Used in metrics: persona_consistency, emotional_congruence, memory_utilization

**Generation:**
```bash
# Process all samples (generates context.json)
python sample_processing.py

# Process single sample
python sample_processing.py --sample-id 001
```

---

### 4. `prompt.md` - Complete LLM Prompt

Final prompt text combining template instructions, conversation history, personality, emotions, and preferences. Ready to send directly to LLM for response generation.

**Structure:**
```markdown
You are Hackcelerate — a warm, practical health companion...

GOAL
Reply to USER_MESSAGE using the provided context...

USING KNOWN_PREFERENCES
- These are facts you already know about this user...

STYLE
- 2–5 sentences, conversational...

---

EXAMPLES
[3 few-shot examples with emotion/personality context]

---

### CONVERSATION_HISTORY
User: [message 1]
Assistant: [response 1]
...

---

### USER_PERSONALITY
Extraversion: 0.41
Neuroticism: 0.55
...

---

### EMOTION_LOGITS
anger: 0.00
disgust: 0.00
...

---

### KNOWN_PREFERENCES
medication_type: daily blood pressure pill
forgetting_pattern: mornings on weekends
...

---

### USER_MESSAGE
[Last user message to respond to]
```

**Sections:**
1. **System Instructions**: Role, goal, guidelines for using context
2. **Examples**: Few-shot examples demonstrating personalized responses
3. **Conversation History**: Dialogue turns leading to current message
4. **User Personality**: Big Five trait scores
5. **Emotion Logits**: Fused emotion probabilities
6. **Known Preferences**: User memory key-value pairs
7. **User Message**: Current message requiring response

**Purpose:**
- Direct input to LLM for generating responses
- Ensures consistent prompt structure across all samples
- Used by `batch_evaluate_ollama.py` and `evaluator.py`

**Template Source:**
- Defined in `build_prompts.py` as `PROMPT_TEMPLATE`
- Formatting functions: `format_personality()`, `format_emotion_block()`, `format_preferences()`, etc.

---

## Data Processing Pipeline

### Full Pipeline

```bash
# 1. Generate TTS audio (if not already present)
python generate_speech.py

# 2. Run full processing: TTS → emotion/personality → context.json + prompt.md
python sample_processing.py

# 3. Verify all files generated
ls samples/*/
```

### Pipeline Steps (executed by `sample_processing.py`)

For each sample:

1. **TTS Generation** (optional)
   - If `query.wav` exists → skip
   - If missing → generate from last user message via OpenAI TTS API

2. **Speech Emotion Analysis**
   - Input: `query.wav`
   - Model: CNN+Transformer acoustic emotion recognition
   - Output: 7-class probability distribution

3. **Text Emotion Analysis**
   - Input: Last user message text
   - Model: DeBERTa-v3-Large
   - Output: 7-class probability distribution

4. **Emotion Fusion**
   - Method: Weighted average (default: 60% speech, 40% text)
   - Weights configurable via `SPEECH_EMOTION_WEIGHT`, `TEXT_EMOTION_WEIGHT` in config

5. **Personality Analysis**
   - Input: Last user message text
   - Model: BERT-based Big Five classifier
   - Output: 5 trait scores (0-1 scale)

6. **Context Generation**
   - Combine: personality + fused emotion + memory + last message
   - Save to: `context.json`

7. **Prompt Rendering**
   - Apply template with all context sections
   - Save to: `prompt.md`

### Command-Line Options

```bash
# Process all samples (default behavior)
python sample_processing.py

# Process specific sample
python sample_processing.py --sample-id 001

# Force regenerate TTS even if audio exists
python sample_processing.py --force-tts

# Custom data path
python sample_processing.py --data ./samples --output-dir ./output
```

---

## Usage in Evaluation

### 1. Response Generation

```python
# Load sample
sample_dir = Path("samples/001")
with open(sample_dir / "sample.json") as f:
    sample = json.load(f)

# Option A: Use prompt.md directly
with open(sample_dir / "prompt.md") as f:
    prompt = f.read()

response = llm.generate(prompt)

# Option B: Use context.json programmatically
with open(sample_dir / "context.json") as f:
    context = json.load(f)

# Build custom prompt with context
messages = [
    {"role": "system", "content": build_system_prompt(context)},
    {"role": "user", "content": context["USER_MESSAGE"]}
]
response = llm.chat(messages)
```

### 2. Metric Evaluation

```python
from metrics import simplified_metrics as metrics

# Load sample + context
sample = load_sample(sample_dir)
context = parse_context_from_sample(sample)

# Evaluate response
scores = {
    "memory_utilization": metrics.memory_utilization(
        response, query, context["memory"],
        sample["must_use_keys"], sample["must_not_use_keys"]
    ),
    "persona_consistency": metrics.persona_consistency(
        response, query, context["personality"]
    ),
    "emotional_congruence": metrics.emotional_congruence(
        response, query, context["emotion"]
    ),
    # ... 9 more metrics
}
```

### 3. Batch Evaluation

```bash
# Evaluate all samples with local Ollama models
python batch_evaluate_ollama.py

# Evaluate first 10 samples (quick test)
python batch_evaluate_ollama.py --limit 10

# Evaluate with specific models
python batch_evaluate_ollama.py --models gemma3:4b phi3:3.8b

# Cloud API evaluation (legacy method)
python evaluator.py --provider google --model gemini-2.0-flash-exp --start 1 --end 100
```

**Output:**
- CSV files: `results/{model}_{num_samples}.csv`
- Columns: sample_id, query, response, [12 metric scores]

---

## Data Statistics

### Sample Characteristics

- **Dialogue Turns**: 7-12 turns per sample (average: 9)
- **User Messages**: 30-120 characters (last message)
- **Memory Keys**: 4-8 key-value pairs per sample
- **Must-Use Keys**: 2-4 keys (required for memory_utilization metric)
- **Must-Not-Use Keys**: 0-2 keys (testing selective memory)

### Audio Files

- **Total Size**: ~13 MB (100 WAV files)
- **Average Duration**: 4.2 seconds
- **Compression**: None (uncompressed PCM)

### Generated Data

- **context.json**: ~500-700 bytes per file
- **prompt.md**: ~2.5-3.0 KB per file
- **Total Dataset Size**: ~30 MB (including audio)

---

## Quality Assurance

### Validation Checks

Run validation to ensure all samples are properly formatted:

```bash
# Check all samples have required files
for i in {001..100}; do
    dir="samples/$i"
    [ -f "$dir/sample.json" ] || echo "Missing: $dir/sample.json"
    [ -f "$dir/query.wav" ] || echo "Missing: $dir/query.wav"
    [ -f "$dir/context.json" ] || echo "Missing: $dir/context.json"
    [ -f "$dir/prompt.md" ] || echo "Missing: $dir/prompt.md"
done

# Count files
echo "sample.json: $(find samples -name sample.json | wc -l)"
echo "query.wav: $(find samples -name query.wav | wc -l)"
echo "context.json: $(find samples -name context.json | wc -l)"
echo "prompt.md: $(find samples -name prompt.md | wc -l)"
```

### Expected Output
```
sample.json: 100
query.wav: 100
context.json: 100
prompt.md: 100
```

---

## Regenerating Data

### Regenerate TTS Only

```bash
# Regenerate all audio files (overwrites existing)
python generate_speech.py --force

# Regenerate specific sample
python generate_speech.py --sample-id 001 --force
```

### Regenerate Context and Prompts

```bash
# Regenerate context.json + prompt.md (preserves audio)
python sample_processing.py

# Force regenerate everything including audio
python sample_processing.py --force-tts
```

### Clean Generated Files

```bash
# Remove all generated files (keeps sample.json only)
find samples -name "query.wav" -delete
find samples -name "context.json" -delete
find samples -name "prompt.md" -delete

# Regenerate all
python sample_processing.py --force-tts
```

---

## Dependencies

### Required Packages

```bash
pip install torch transformers
pip install openai requests httpx
pip install sounddevice scipy numpy
pip install pandas sqlalchemy
```

### External Services

- **OpenAI API**: TTS generation (requires `OPENAI_API_KEY` in `.env`)
  - Endpoint: `https://api.openai.com/v1/audio/speech`
  - Voice: "shimmer"
  - Model: "tts-1"

### Models (Auto-downloaded on first run)

1. **Speech Emotion** (~500 MB)
   - CNN+Transformer acoustic model
   - 7 emotion classes
   - Loaded from HuggingFace cache

2. **Text Emotion** (~1.3 GB)
   - DeBERTa-v3-Large
   - 7 emotion classes (aligned with speech)
   - Model: Pre-trained on emotion classification task

3. **Personality** (~440 MB)
   - `Minej/bert-base-personality`
   - Big Five trait prediction
   - BERT-base architecture

---

## Notes

### Emotion Weight Configuration

Default fusion weights (defined in `modules/config.py`):
- `SPEECH_EMOTION_WEIGHT = 0.6` (60% from audio)
- `TEXT_EMOTION_WEIGHT = 0.4` (40% from text)

To change weights during processing:
```bash
# Use only speech emotion
python sample_processing.py --speech-weight 1.0 --text-weight 0.0

# Use only text emotion
python sample_processing.py --speech-weight 0.0 --text-weight 1.0

# Custom balance (70% speech, 30% text)
python sample_processing.py --speech-weight 0.7 --text-weight 0.3
```

### Reproducibility

- **TTS**: Audio files are deterministic for the same input text (OpenAI API caching)
- **Emotion/Personality**: Models use deterministic inference (no dropout, fixed random seed)
- **Context/Prompts**: Generated deterministically from sample data + model outputs

### File Modification Times

Sample processing updates timestamps:
- `sample.json`: Original creation (unchanged during processing)
- `query.wav`: Only modified if regenerated with `--force-tts`
- `context.json`: Updated every time `sample_processing.py` runs
- `prompt.md`: Updated every time `sample_processing.py` runs

---

## Related Documentation

- **Main Benchmark README**: `../README.md` - Full benchmark system documentation
- **Metrics Documentation**: `../CLAUDE.md` - Detailed metric descriptions and formulas
- **Evaluation Scripts**: `../batch_evaluate_ollama.py`, `../evaluator.py`
- **Metric Implementations**: `../metrics/*.py` - Individual metric modules

---

## Questions or Issues?

- Check the main benchmark README: `../README.md`
- Review the processing scripts: `generate_speech.py`, `build_prompts.py`, `sample_processing.py`
- Validate your setup by running on a single sample first: `python sample_processing.py --sample-id 001`

---

**Last Updated**: 2026-01-06
**Dataset Version**: 1.0
**Total Samples**: 100
