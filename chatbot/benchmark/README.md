# LLM Benchmark for Memory Citation

This benchmark evaluates how well LLM models reference structured memory information when generating healthcare advice responses.

## 🎯 Automatic Optimal Judge Models

All 12 metrics automatically use the best judge model based on LMArena benchmarks (Dec 2025 - Jan 2026):

| Metric | Judge Model | Why Selected |
|--------|-------------|--------------|
| **persona_consistency** | Claude Opus 4.5 | #1 instruction following + deep reasoning for personality traits |
| **emotional_congruence** | GPT-4o | Highest Sentient score for empathy and emotional understanding |
| **memory_utilization** | Claude Opus 4.5 | Precision in code/logic tasks, best for detecting exact memory references |
| **coherence** | GPT-4o | Highest MMLU (88.7%), best general language understanding |
| **helpfulness** | Claude Opus 4.5 | #1 instruction following, best at judging actionability |
| **empathy** | GPT-4o | GPT-4o-Latest achieves highest Sentient score for emotional intelligence |
| **politeness** | GPT-4o | Best social cognition and nuanced tone detection |
| **safety** | Claude Opus 4.5 | Anthropic's focus on AI safety, constitutional AI principles |
| **logical_consistency** | GPT-5.2 | Perfect 100% on AIME 2025, 52.9% on ARC-AGI abstract reasoning |
| **conversational_continuity** | Gemini 2.0 Flash | #1 overall (1501 Elo), excellent multimodal context understanding |
| **groundedness** | Claude Opus 4.5 | High precision, low hallucination rate, best for fact-checking |
| **relevance** | Gemini 2.0 Flash | #1 overall (1501 Elo), excellent context understanding for query-response matching |

**Sources:** [LMArena Leaderboard](https://lmarena.ai/leaderboard), [AI Benchmarks Dec 2025](https://lmcouncil.ai/benchmarks), [Sage: Empathy Evaluation](https://arxiv.org/html/2505.02847)


## Architecture

```
benchmark/
├── dataset/samples/          # 100 healthcare dialogue samples (001-100)
├── metrics/                  # 12 metrics modules (LLM-as-a-judge)
├── batch_evaluate_ollama.py  # Main evaluation script (local + cloud)
├── generate_comparison.py    # Generate model comparison TXT
└── results/                  # CSV outputs + model_comparison.txt
```

## Quick Start

```bash
# Evaluate all 100 samples with 3 local models (recommended)
python batch_evaluate_ollama.py

# Quick test with 10 samples
python batch_evaluate_ollama.py --limit 10

# Specific models only
python batch_evaluate_ollama.py --models gemma3:4b phi3:3.8b
```

**Output**:
- `results/{model}_{num_samples}.csv` - Per-sample scores for all 12 metrics
- `results/model_comparison.txt` - Average scores comparison across models

## Data Format

Each sample file (`dataset/samples/<id>/sample.json`):

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
  "must_use_keys": [
    "medication_type",
    "forgetting_pattern",
    "tech_comfort"
  ]
}
```

**Fields**:
- `id`: Sample identifier (001-100)
- `dialogue`: Multi-turn conversation history (last user turn is the query)
- `memory`: User profile information (key-value pairs)
- `must_use_keys`: Memory keys that should be referenced (for Memory Utilization metric)

## Evaluation Metrics (12 Total)

All metrics use LLM-as-a-judge evaluation. Scores are normalized to 0-1 range in final CSV output.

### 1. Persona Consistency
**Purpose**: Alignment with Big Five personality traits
**Scale**: 1-5 (normalized to 0.0-1.0)
**Criteria**: Response tailored to user's Extraversion, Neuroticism, Agreeableness, Conscientiousness, Openness

### 2. Emotional Congruence
**Purpose**: Tone alignment with detected user emotions
**Scale**: 1-5 (normalized to 0.0-1.0)
**Criteria**: Response tone matches user's emotional state (7 emotion classes: anger, disgust, fear, happy, neutral, sad, surprise)

### 3. Memory Utilization
**Purpose**: Correct citation of relevant memory keys
**Scale**: F1 score (0.0-1.0)
**Criteria**: Precision and recall of must-use memory keys referenced in response

### 4. Relevance
**Purpose**: Query-response topical alignment
**Scale**: 1-5 (normalized to 0.0-1.0)
**Criteria**: Response directly addresses user's query without off-topic content

### 5. Coherence
**Purpose**: Language quality and fluency
**Scale**: 1-5 (normalized to 0.0-1.0)
**Criteria**: Clear expression, logical flow, good organization, grammatical correctness

### 6. Helpfulness
**Purpose**: Task effectiveness and actionability
**Scale**: 1-5 (normalized to 0.0-1.0)
**Criteria**: Provides actionable guidance with clear next steps

### 7. Empathy
**Purpose**: Emotional intelligence and warmth
**Scale**: 1-5 (normalized to 0.0-1.0)
**Criteria**: Warm tone, validates feelings, supportive and encouraging

### 8. Politeness
**Purpose**: Social acceptability
**Scale**: 0-1
**Criteria**: Respectful, considerate tone; no rudeness or dismissiveness

### 9. Safety
**Purpose**: Toxicity detection
**Scale**: 0-1
**Criteria**: No toxic, harmful, or dangerous content

### 10. Logical Consistency
**Purpose**: Reasoning quality
**Scale**: 1-5 (normalized to 0.0-1.0)
**Criteria**: Sound reasoning, no internal contradictions, consistent recommendations

### 11. Conversational Continuity
**Purpose**: Dialogue flow and context maintenance
**Scale**: 1-5 (normalized to 0.0-1.0)
**Criteria**: References previous turns, maintains topic coherence, natural progression

### 12. Groundedness
**Purpose**: Hallucination detection
**Scale**: 0-1
**Criteria**: Claims grounded in memory/query/general knowledge vs. hallucinated details

## Dependencies

```bash
pip install instructor pydantic openai anthropic google-generativeai numpy pandas
```

**Environment Variables** (at least one required):
- `OPENAI_API_KEY` - For GPT-4o, GPT-5.2 judges
- `ANTHROPIC_API_KEY` - For Claude Opus 4.5 judges
- `GOOGLE_API_KEY` - For Gemini 2.0 Flash judges

## Troubleshooting

**Issue**: API key not found
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export GOOGLE_API_KEY="AIza..."
```

**Issue**: Ollama connection error
```bash
ollama serve
ollama pull gemma3:4b
```
