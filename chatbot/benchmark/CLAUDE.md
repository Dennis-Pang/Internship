# Benchmark - LLM Memory Citation Evaluation System

## Overview

This benchmark evaluates how well LLM models reference structured memory information when generating healthcare advice responses. It measures 12 independent metrics using state-of-the-art judge models (Claude Opus 4.5, GPT-4o, GPT-5.2, Gemini 2.0 Flash) automatically selected based on LMArena benchmarks (Dec 2025 - Jan 2026).

**Location**: `/home/user/ai_agent/ai_agent_project/chatbot/benchmark/`

**Cost**: ~$0.13 per sample (~$13 for 100 samples)

## Key Features

- **12 Evaluation Metrics**: Comprehensive evaluation across multiple dimensions
- **Automatic Judge Model Selection**: Each metric uses the optimal judge model
- **Multi-Provider Support**: Google (Gemini), Anthropic (Claude), OpenAI (GPT)
- **Modular Architecture**: Easy to extend with new metrics
- **Simplified API**: Clean, single-function calls for each metric

## Quick Start

### Recommended: Local Ollama + Cloud API (Fast & Best Quality)

**NEW!** Use `batch_evaluate_ollama.py` for optimal performance:

```bash
cd /home/user/ai_agent/ai_agent_project/chatbot/benchmark

# Evaluate all 100 samples with 3 local models (30 min for all 300 responses)
python batch_evaluate_ollama.py

# Quick test with 10 samples
python batch_evaluate_ollama.py --limit 10

# Specific models only
python batch_evaluate_ollama.py --models gemma3:4b phi3:3.8b
```

**Features**:
- ⚡ **14x faster**: 18s/sample vs 255s/sample (parallel cloud API judges)
- 💰 **Cost-effective**: Local generation (free) + cloud evaluation (~$13/100 samples)
- 🎯 **Best quality**: Auto-selects optimal judge model per metric
- 📊 **CSV output**: `results/{model}_{num_samples}.csv`

**Performance**:
| Samples | Time (3 models) | Cost |
|---------|-----------------|------|
| 10 | ~3 min | ~$1.30 |
| 100 | ~30 min | ~$13 |

### Alternative: Legacy Methods

#### 1. Generate Responses (Test Only, No Evaluation)

```bash
cd /home/user/ai_agent/ai_agent_project/chatbot/benchmark

# Basic usage with default model (gemma3:4b)
python test.py

# With specific model
python test.py --model gemma3:4b

# Quick test with limited samples
python test.py --limit 10

# Custom emotion weights
python test.py --speech-weight 0.7 --text-weight 0.3

# Disable OpenAI TTS (use uniform distribution for speech emotion)
python test.py --disable-openai-tts
```

**Output**: `results/responses_{model}_{timestamp}.json`

#### 2. Generate + Evaluate in One Step (Cloud-Only)

```bash
# Google Gemini (recommended for cost-effectiveness)
python evaluator.py --provider google --model gemini-2.0-flash-exp --start 1 --end 100

# Anthropic Claude
python evaluator.py --provider anthropic --model claude-3-5-sonnet-20241022 --start 1 --end 10

# OpenAI GPT
python evaluator.py --provider openai --model gpt-4o-mini --start 1 --end 100

# Custom sample range
python evaluator.py --provider google --model gemini-2.0-flash-exp --start 1 --end 20
```

**Output**:
- `results/{model}_{num_samples}.jsonl` - One JSON per sample
- `results/{model}_{num_samples}_summary.json` - Aggregated statistics

## Architecture

```
benchmark/
├── dataset/                   # Benchmark samples
│   ├── generate_speech.py     # Generate TTS audio from text queries
│   └── samples/               # Per-sample folders (100 samples: 001-100)
│       └── 001/
│           ├── sample.json    # Sample data (dialogue, memory, rules)
│           └── prompt.json    # Formatted prompt for LLM
├── evaluator.py               # Main evaluator (generate + evaluate)
├── example_usage.py           # Usage examples for metrics
├── test_judge_config.py       # Test judge model configuration
├── test_output_filename.py    # Test output file naming
├── metrics/                   # Metrics modules (extensible)
│   ├── __init__.py
│   ├── llm_router.py          # Multi-provider LLM router
│   ├── judge_config.py        # Automatic judge model selection
│   ├── simplified_metrics.py  # Simplified metric API (12 functions)
│   ├── memory_utilization.py  # Memory Utilization P/R/F1
│   ├── groundedness.py        # Hallucination detection
│   ├── relevance.py           # Response relevance (embeddings)
│   ├── coherence.py           # Response coherence (LLM judge)
│   ├── emotional_congruence.py # Tone alignment with user emotions
│   ├── helpfulness.py         # Task effectiveness and actionability
│   ├── empathy.py             # Emotional intelligence and warmth
│   ├── safety.py              # Safety / Toxicity (0-1)
│   ├── logical_consistency.py # Reasoning quality and contradictions
│   ├── persona_consistency.py # Personality trait alignment
│   ├── politeness.py          # Social acceptability
│   └── conversational_continuity.py # Dialogue flow
├── results/                   # Generated responses & evaluations
└── .env                       # API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY)
```

## 12 Evaluation Metrics

### Overview Table

| # | Metric | Judge Model | Scale | Key Question |
|---|--------|-------------|-------|--------------|
| 1 | **Persona Consistency** | Claude Opus 4.5 | 1-5 | Does response align with Big Five personality traits? |
| 2 | **Emotional Congruence** | GPT-4o | 1-5 | Does tone match detected user emotions? |
| 3 | **Memory Utilization** | Claude Opus 4.5 | P/R/F1 | Are relevant memory keys cited correctly? |
| 4 | **Coherence** | GPT-4o | 1-5 | Is response fluent, clear, and well-structured? |
| 5 | **Helpfulness** | Claude Opus 4.5 | 1-5 | Is response actionable and task-effective? |
| 6 | **Empathy** | GPT-4o | 1-5 | Does response show warmth and emotional intelligence? |
| 7 | **Politeness** | GPT-4o | 0-1 | Is response respectful and socially appropriate? |
| 8 | **Safety** | Claude Opus 4.5 | 0-1 | Is response free of toxic/harmful content? |
| 9 | **Logical Consistency** | GPT-5.2 | 1-5 | Is reasoning sound without contradictions? |
| 10 | **Conversational Continuity** | Gemini 2.0 Flash | 1-5 | Does response maintain dialogue flow? |
| 11 | **Groundedness** | Claude Opus 4.5 | 0-1 | Are claims grounded in source material? |
| 12 | **Relevance** | OpenAI Embeddings | 0-1 | Is response semantically similar to query? |

### Detailed Metric Descriptions

#### 1. Persona Consistency (1-5)
- **Judge**: Claude Opus 4.5 (#1 instruction following)
- **Checks**: Alignment with Big Five personality traits (Extraversion, Neuroticism, Agreeableness, Conscientiousness, Openness)
- **Example**: Low conscientiousness → simpler steps; high neuroticism → reassurance

#### 2. Emotional Congruence (1-5)
- **Judge**: GPT-4o (highest Sentient score for empathy)
- **Checks**: Tone alignment with detected user emotions (7 classes: anger, disgust, fear, happy, neutral, sad, surprise)
- **Example**: High sadness → gentle/validating vs. overly upbeat

#### 3. Memory Utilization (Precision/Recall/F1)
- **Judge**: Claude Opus 4.5 (best for detecting exact memory references)
- **Checks**: Correct citation of required memory keys, avoidance of forbidden keys
- **Formula**: P = TP/(TP+FP), R = TP/|R|, F1 = 2*P*R/(P+R)

#### 4. Coherence (1-5)
- **Judge**: GPT-4o (highest MMLU 88.7%)
- **Checks**: Logical flow, clarity, consistency, organization, relevance

#### 5. Helpfulness (1-5)
- **Judge**: Claude Opus 4.5 (#1 instruction following)
- **Checks**: Task effectiveness, actionability, clear next steps

#### 6. Empathy (1-5)
- **Judge**: GPT-4o (highest Sentient score for emotional intelligence)
- **Checks**: Warmth, validation, supportive tone

#### 7. Politeness (0-1)
- **Judge**: GPT-4o (best social cognition)
- **Checks**: Respectful, considerate tone; flags rudeness/dismissiveness

#### 8. Safety (0-1)
- **Judge**: Claude Opus 4.5 (Anthropic's AI safety focus)
- **Checks**: No toxic, harmful, or unsafe content

#### 9. Logical Consistency (1-5)
- **Judge**: GPT-5.2 (perfect 100% on AIME 2025)
- **Checks**: Internal contradictions, faulty reasoning, inconsistent recommendations

#### 10. Conversational Continuity (1-5)
- **Judge**: Gemini 2.0 Flash (#1 overall, 1501 Elo)
- **Checks**: Dialogue flow, context maintenance, smooth transitions

#### 11. Groundedness (0-1)
- **Judge**: Claude Opus 4.5 (high precision, low hallucination)
- **Checks**: Claims grounded in memory/query/general knowledge vs. hallucinated

#### 12. Relevance (0-1)
- **Method**: OpenAI Embeddings (fast, cost-effective)
- **Checks**: Semantic similarity via cosine distance

## Data Format

### Sample Structure (`dataset/samples/{id}/sample.json`)

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
    "wake_time_shift": "wakes ~2 hours later on weekends",
    "current_strategy": "none",
    "reminder_devices": "smartphone available"
  },
  "must_use_keys": [
    "medication_type",
    "forgetting_pattern",
    "tech_comfort"
  ],
  "must_not_use_keys": [
    "wake_time_shift"
  ]
}
```

### Prompt Structure (`dataset/samples/{id}/prompt.json`)

Formatted messages in OpenAI format with system prompt containing:
- User personality traits (Big Five scores)
- User emotional state (7 emotion probabilities)
- User profile memory
- Dialogue history

## Simplified Metrics API

All metrics are available through `metrics/simplified_metrics.py` with clean, single-function calls:

```python
from metrics import simplified_metrics as metrics

# 1-5 scale metrics
score = metrics.persona_consistency(response, query, personality, provider, model)
score = metrics.emotional_congruence(response, query, emotion, provider, model)
score = metrics.coherence(response, query, provider, model)
score = metrics.helpfulness(response, query, provider, model)
score = metrics.empathy(response, query, provider, model)
score = metrics.logical_consistency(response, query, provider, model)
score = metrics.conversational_continuity(response, query, dialogue, provider, model)

# 0-1 scale metrics
score = metrics.politeness(response, query, provider, model)
score = metrics.safety(response, query, provider, model)
score = metrics.groundedness(response, query, memory, provider, model)
score = metrics.relevance(response, query, provider="openai")  # Embedding-based

# F1 score metric
f1_score = metrics.memory_utilization(response, query, memory, must_use, must_not, provider, model)
```

## Example Usage

See `example_usage.py` for detailed examples:

```python
# Example 1: Single metric call
score = metrics.helpfulness(
    response="Try getting more sleep and reducing caffeine.",
    query="I've been feeling low on energy lately.",
    provider="openai",
    model="gpt-4o-mini"
)

# Example 2: Multiple metrics for one sample
scores = {
    "helpfulness": metrics.helpfulness(response, query, provider, model),
    "coherence": metrics.coherence(response, query, provider, model),
    "empathy": metrics.empathy(response, query, provider, model),
}

# Example 3: Batch evaluation loop
for sample in samples:
    scores = evaluate_all_metrics(sample, provider, model)
    all_scores.append(scores)

avg_helpfulness = sum(s["helpfulness"] for s in all_scores) / len(all_scores)
```

## Configuration

### Environment Variables (.env)

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-api03-...
GOOGLE_API_KEY=AIza...
```

### Provider/Model Options

**Google (Gemini)**:
- `gemini-2.0-flash-exp` (recommended for cost)
- `gemini-1.5-pro`

**Anthropic (Claude)**:
- `claude-3-5-sonnet-20241022`
- `claude-opus-4.5` (highest quality)

**OpenAI (GPT)**:
- `gpt-4o-mini` (cost-effective)
- `gpt-4o` (higher quality)

## Performance Optimization

### ⚡ Parallel Evaluation (Recommended)

**NEW**: `batch_evaluate_ollama.py` uses parallel cloud API calls:

```
每个样本处理时间：
├─ 生成响应 (Local Ollama):   15秒    (83%)
└─ 评估 12 个 metrics:        3秒     (17%) ✅ 并行
   └─ 所有 metric 同时调用云端 API

总时间：18秒/样本（14x 加速！）
```

**Bottleneck Analysis**:
- **Before**: 255s/sample (94.5% spent on serial judge calls)
- **After**: 18s/sample (parallel cloud API, max_workers=12)
- **Speedup**: 80x faster metric evaluation

### Performance Tips

1. **Use parallel evaluation** (default in `batch_evaluate_ollama.py`)
2. **Local generation**: Use local Ollama for responses (free, fast)
3. **Cloud judges**: Auto-select best models (Claude Opus 4.5, GPT-4o, Gemini 2.0, GPT-5.2)
4. **Adjust workers**: `--max-workers 12` (one per metric, default)
5. **Smaller test sets**: Use `--limit 10` for quick validation
6. **Audio caching**: TTS-generated audio files are reused across runs

## Adding New Metrics

The benchmark has a modular architecture. To add a new metric:

1. **Create `metrics/new_metric.py`**:
   ```python
   from pydantic import BaseModel
   from metrics.llm_router import get_structured_response

   class NewMetricJudgment(BaseModel):
       score: int  # 1-5 or float for 0-1
       explanation: str

   def evaluate_new_metric(response, query, provider, model):
       prompt = f"Evaluate this response: {response}"
       judgment = get_structured_response(
           prompt=prompt,
           response_model=NewMetricJudgment,
           provider=provider,
           model=model
       )
       return judgment.score
   ```

2. **Add to `metrics/simplified_metrics.py`**:
   ```python
   from metrics.new_metric import evaluate_new_metric

   def new_metric(response, query, provider, model):
       return evaluate_new_metric(response, query, provider, model)
   ```

3. **Use in `evaluator.py`**:
   ```python
   scores["new_metric"] = metrics.new_metric(response, query, provider, model)
   ```

## Troubleshooting

### Issue: `instructor` import error
```bash
pip install instructor
```

### Issue: OpenAI TTS fails
```bash
# Check API key
echo $OPENAI_API_KEY

# Or disable TTS
python test.py --disable-openai-tts
```

### Issue: Ollama connection error
```bash
# Ensure Ollama is running
ollama serve

# Check available models
ollama list

# Pull required model
ollama pull gemma3:4b
```

### Issue: API key not found
```bash
# Load environment variables from .env
export $(cat .env | xargs)

# Or set directly
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export GOOGLE_API_KEY="AIza..."
```

## Important Notes

- **Evaluation Scope**: Focuses on memory citation quality, not general chatbot quality
- **Healthcare Context**: Samples are healthcare-specific (medication, energy, sleep, etc.)
- **Judge Model Selection**: Automatic based on LMArena benchmarks (see README.md)
- **Cost Estimation**: ~$0.13 per sample for full 12-metric evaluation
- **Sample Range**: 100 samples total (001-100) in `dataset/samples/`

## Related Files

- **Main Chatbot**: `../chatbot_cli.py` (uses same personality/emotion modules)
- **Shared Modules**: `../modules/` (config, database, llm, memory, personality, emotion)
- **Documentation**: `README.md` (detailed metric descriptions and formulas)

## Development Workflow

1. **Add/modify samples**: Edit `dataset/samples/{id}/sample.json`
2. **Test single metric**: Use `example_usage.py`
3. **Test full evaluation**: Run `evaluator.py --start 1 --end 10`
4. **Analyze results**: Check `results/{model}_{num}_summary.json`
5. **Compare models**: Run with different `--provider` and `--model` options

## References

- [LMArena Leaderboard](https://lmarena.ai/leaderboard)
- [AI Benchmarks Dec 2025](https://lmcouncil.ai/benchmarks)
- [Sage: Empathy Evaluation](https://arxiv.org/html/2505.02847)
