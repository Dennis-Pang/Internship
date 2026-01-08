# Dataset Structure

This directory contains 100 healthcare dialogue samples for evaluating LLM memory citation and personalization quality.

## Overview

- **Total Samples**: 100 (IDs: 001-100)
- **Domain**: Healthcare advice and behavior change support
- **Format**: Multi-turn dialogues with user personality, emotions, and memory

## Directory Structure

```
dataset/
├── generate_speech.py        # Generate TTS audio from text
├── sample_processing.py       # Full pipeline: TTS → emotion/personality → context/prompt
└── samples/                   # Sample data (001-100)
    └── 001/
        ├── sample.json        # Raw sample data (dialogue + memory + constraints)
        ├── query.wav          # TTS audio of last user message
        ├── context.json       # Processed context (personality + emotion + preferences)
        └── prompt.md          # Complete LLM prompt (ready to use)
```

## Sample Files

Each sample folder (`samples/{id}/`) contains 4 files:

### 1. `sample.json` - Raw Sample Data

Core sample information including dialogue history and memory.

```json
{
  "id": "001",
  "dialogue": [
    {"role": "user", "content": "I keep missing my medication sometimes."},
    {"role": "assistant", "content": "That's common. Do you notice it more on weekdays or weekends?"},
    {"role": "user", "content": "If it worked for weekend mornings, I'd finally be consistent."}
  ],
  "memory": {
    "medication_type": "daily blood pressure pill",
    "forgetting_pattern": "mornings on weekends",
    "tech_comfort": "high",
    "wake_time_shift": "wakes ~2 hours later on weekends"
  },
  "must_use_keys": ["medication_type", "forgetting_pattern", "tech_comfort"]
}
```

**Fields**:
- `id`: Sample identifier (001-100)
- `dialogue`: Conversation history (last message is the query)
- `memory`: User profile key-value pairs
- `must_use_keys`: Memory keys that should be referenced (for Memory Utilization metric)

### 2. `query.wav` - TTS Audio

Audio of the last user message, generated using OpenAI TTS API.

- **Format**: WAV (PCM 16-bit, 24kHz, mono)
- **Size**: ~100-200 KB
- **Duration**: 3-6 seconds

### 3. `context.json` - Processed Context

Derived data with analyzed personality, emotions, and formatted preferences.

```json
{
  "USER_PERSONALITY": "Extraversion: 0.41\nNeuroticism: 0.55\n...",
  "EMOTION_LOGITS": "anger: 0.00\ndisgust: 0.00\nneutral: 0.79\n...",
  "KNOWN_PREFERENCES": "medication_type: daily blood pressure pill\n...",
  "USER_MESSAGE": "If it worked for weekend mornings, I'd finally be consistent."
}
```

**Fields**:
- `USER_PERSONALITY`: Big Five trait scores (0-1 scale)
- `EMOTION_LOGITS`: Fused emotion probabilities (60% speech + 40% text, 7 classes)
- `KNOWN_PREFERENCES`: Formatted memory from `sample.json`
- `USER_MESSAGE`: Last user message

### 4. `prompt.md` - Complete LLM Prompt

Final prompt combining template, history, personality, emotions, and preferences. Ready for LLM input.

## Data Processing Pipeline

### Quick Start

```bash
# Generate all TTS audio files
python generate_speech.py

# Process all samples (emotion/personality analysis → context.json + prompt.md)
python sample_processing.py

# Verify files generated
ls samples/*/
```

### Pipeline Steps

For each sample, `sample_processing.py`:

1. **TTS Generation** - Generate `query.wav` from last user message (if missing)
2. **Speech Emotion** - Analyze audio → 7-class emotion probabilities
3. **Text Emotion** - Analyze text → 7-class emotion probabilities
4. **Emotion Fusion** - Weighted average (60% speech + 40% text)
5. **Personality Analysis** - Extract Big Five traits from text
6. **Context Generation** - Save to `context.json`
7. **Prompt Rendering** - Save to `prompt.md`

### Command Options

```bash
# Process all samples
python sample_processing.py

# Process specific sample
python sample_processing.py --sample-id 001

# Force regenerate TTS
python sample_processing.py --force-tts

# Custom emotion weights
python sample_processing.py --speech-weight 0.7 --text-weight 0.3
```

## Usage in Evaluation

### Load Sample and Generate Response

```python
# Load prompt
with open("samples/001/prompt.md") as f:
    prompt = f.read()

# Generate response
response = llm.generate(prompt)
```

### Batch Evaluation

```bash
# Evaluate all 100 samples with local models
python batch_evaluate_ollama.py

# Quick test with 10 samples
python batch_evaluate_ollama.py --limit 10
```

**Output**: `results/{model}_{num_samples}.csv` with 12 metric scores per sample

## Data Statistics

- **Dialogue Turns**: 7-12 turns per sample (average: 9)
- **User Message Length**: 30-120 characters
- **Memory Keys**: 4-8 key-value pairs per sample
- **Must-Use Keys**: 2-4 keys per sample
- **Total Dataset Size**: ~30 MB (including audio)

## Validation

Check all files exist:

```bash
# Count files
echo "sample.json: $(find samples -name sample.json | wc -l)"
echo "query.wav: $(find samples -name query.wav | wc -l)"
echo "context.json: $(find samples -name context.json | wc -l)"
echo "prompt.md: $(find samples -name prompt.md | wc -l)"
```

Expected: 100 files each

## Regenerate Data

```bash
# Regenerate all audio (overwrites existing)
python generate_speech.py --force

# Regenerate context + prompts (preserves audio)
python sample_processing.py

# Clean and regenerate everything
find samples -name "query.wav" -delete
find samples -name "context.json" -delete
find samples -name "prompt.md" -delete
python sample_processing.py --force-tts
```

## Dependencies

```bash
pip install torch transformers openai requests numpy pandas
```

**Environment Variables**:
- `OPENAI_API_KEY` - For TTS generation

**Models** (auto-downloaded on first run):
- Speech Emotion: ~500 MB (CNN+Transformer)
- Text Emotion: ~1.3 GB (DeBERTa-v3-Large)
- Personality: ~440 MB (BERT-base)

## Notes

- **Default Emotion Weights**: 60% speech + 40% text (configurable)
- **TTS Voice**: OpenAI "shimmer"
- **Reproducibility**: Models use deterministic inference
