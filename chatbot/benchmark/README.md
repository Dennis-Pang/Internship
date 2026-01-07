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
| **relevance** | OpenAI Embeddings | Fast, cost-effective embeddings for semantic similarity |

**Sources:** [LMArena Leaderboard](https://lmarena.ai/leaderboard), [AI Benchmarks Dec 2025](https://lmcouncil.ai/benchmarks), [Sage: Empathy Evaluation](https://arxiv.org/html/2505.02847)

**Cost:** ~$0.13 per sample (~$13 for 100 samples)

## Architecture

```
benchmark/
├── dataset/                   # Benchmark samples
│   ├── data.json              # Legacy combined samples (optional)
│   └── samples/               # Per-sample folders (default)
│       └── H001/sample.json
├── test.py                    # Generate responses (no evaluation)
├── evaluate.py                # Evaluate responses using metrics
├── metrics/                   # Metrics modules (extensible)
│   ├── __init__.py
│   ├── llm_router.py          # Multi-provider LLM router (Anthropic/OpenAI/Google)
│   ├── memory_utilization.py # Memory Utilization P/R/F1
│   ├── groundedness.py        # Hallucination detection
│   ├── relevance.py           # Response relevance (embeddings)
│   ├── coherence.py           # Response coherence (LLM judge)
│   ├── emotional_congruence.py # Tone alignment with user emotions (LLM judge)
│   ├── helpfulness.py         # Task effectiveness and actionability (LLM judge)
│   ├── safety.py              # Safety / Toxicity (LLM judge, 0-1)
│   ├── logical_consistency.py # Reasoning quality and contradictions (LLM judge)
│   └── empathy.py             # Emotional intelligence and warmth (LLM judge)
├── results/                   # Generated responses & evaluations
└── audio/                     # Optional: TTS-generated audio files
```

## Workflow

### Step 1: Generate Responses

```bash
# Basic usage (default: gemma3:4b)
python test.py

# With specific model
python test.py --model gemma3:4b

# Quick test with limited samples
python test.py --limit 10

# Custom emotion weights
python test.py --speech-weight 0.7 --text-weight 0.3

# OpenAI TTS is ENABLED by default (requires OPENAI_API_KEY)
export OPENAI_API_KEY="sk-..."
python test.py

# Disable OpenAI TTS (use uniform distribution for speech emotion)
python test.py --disable-openai-tts
```

Default dataset path: `dataset/samples`. To run against the legacy combined file instead, use `--data dataset/data.json`.

**Output**: `results/responses_{model}_{timestamp}.json`

**What it does**:
1. Text input (from `dataset/samples` by default; `data.json` supported for compatibility)
2. [Optional] Text → OpenAI TTS → speech file
3. Speech → Speech2Emotion analysis
4. Text → Text2Emotion analysis
5. Text → Personality analysis (Big Five)
6. Emotion fusion (speech + text, weighted)
7. Build prompt with memory as User Profile
8. LLM generates response
9. Save all data to JSON

### Step 2: Evaluate Responses

```bash
# Evaluate generated responses
python evaluate.py --results results/responses_gemma3_4b_20260101_123456.json

# Use different judge model
python evaluate.py --results results/responses_gemma3_4b_20260101_123456.json --judge-model gemma3:7b
```

**Output**: `results/eval_{input_filename}.json`

**What it does**:
1. Load generated responses
2. For each response, evaluate with 8 metrics:
   - **Memory Utilization**: LLM judge identifies cited keys → calculate P/R/F1
   - **Groundedness**: LLM judge extracts claims → verify grounding → hallucination rate
   - **Relevance**: Generate embeddings → cosine similarity with query
   - **Coherence**: LLM judge scores fluency on 5-point rubric
   - **Emotional Congruence**: LLM judge checks tone alignment with detected user emotions (1-5)
   - **Helpfulness**: LLM judge evaluates task effectiveness and actionability (1-5)
   - **Persona Consistency**: LLM judge checks alignment with provided personality traits (1-5)
   - **Logical Consistency**: LLM judge evaluates reasoning quality and contradictions (1-5)
   - **Empathy**: LLM judge evaluates emotional intelligence, warmth, and supportive tone (1-5)
3. Aggregate metrics (micro & macro averaging)
4. Save detailed results with per-sample and aggregate metrics

## Data Format

Each sample file (`dataset/samples/<id>/sample.json`, same schema if you use `data.json`):

```json
{
  "id": "H001",
  "query": "I've been feeling low on energy lately. What should I do this week?",
  "memory": {
    "name": "Jason",
    "sleep_hours_avg": "5.5",
    "caffeine_intake": "high",
    "exercise_frequency": "rare",
    "known_condition": "mild anemia"
  },
  "required_keys": [
    "sleep_hours_avg",
    "caffeine_intake",
    "exercise_frequency",
    "known_condition"
  ],
  "forbidden_keys": [
    "age"
  ],
  "neutral_keys": [
    "name"
  ]
}
```

## Metrics

This benchmark evaluates twelve independent metrics:

### 1. Memory Utilization Accuracy (`metrics/memory_utilization.py`)

**Purpose**: Measures correct use of relevant memories by comparing referenced vs expected memory keys.

**Formula**:
- U = set of cited keys (from LLM judge)
- R = set of required keys (should be referenced)
- F = set of forbidden keys (should NOT be referenced)
- TP = |U ∩ R| (cited AND required)
- FP = |U ∩ F| (cited AND forbidden)
- FN = |R| - TP (required but NOT cited)

**Metrics**:
- **Precision** = TP / (TP + FP) - proportion of referenced memories that are relevant
- **Recall** = TP / |R| - proportion of relevant memories that are referenced
- **F1** = 2 * P * R / (P + R) - harmonic mean

**Aggregation**:
- **Micro-averaging** (recommended): Sum all TP/FP/FN, then calculate P/R/F1
- **Macro-averaging** (reference): Average P/R/F1 across samples

**Notes**:
- `neutral_keys` do not contribute to any metric
- When no keys are cited (TP+FP=0), Precision=1.0 (no citation errors)

---

### 2. Groundedness / Hallucination Rate (`metrics/groundedness.py`)

**Purpose**: Evaluates factual faithfulness by checking if claims in the response are grounded in source material (memory/input).

**Process**:
1. Extract all factual claims from the response
2. For each claim, determine if it is:
   - **Grounded in memory** (user-specific details match memory)
   - **Grounded in query** (explicitly mentioned in user's question)
   - **Grounded in general knowledge** (established medical facts)
   - **Hallucinated** (invented details, contradicts sources)

**Metrics**:
- **Groundedness Score** = (grounded claims) / (total claims) [0-1, higher is better]
- **Hallucination Rate** = 1 - groundedness_score [0-1, lower is better]

**Aggregation**:
- **Micro-averaging** (recommended): Sum all grounded/hallucinated claims, then calculate scores
- **Macro-averaging** (reference): Average scores across samples

**Notes**:
- General medical advice (e.g., "exercise improves energy") is considered grounded
- User-specific details must match memory exactly
- Empty responses have groundedness_score=1.0, hallucination_rate=0.0

---

### 3. Response Relevance (`metrics/relevance.py`)

**Purpose**: Measures semantic similarity between user query and assistant response using OpenAI embeddings.

**Process**:
1. Generate embeddings for both query and response using OpenAI API
2. Calculate cosine similarity between the two embedding vectors
3. Return relevance score as similarity measure

**Metrics**:
- **Relevance Score** = cosine_similarity(query_emb, response_emb) [0-1, higher is better]
  - 1.0: Perfect semantic alignment
  - 0.5-0.8: Moderately relevant
  - <0.5: Low relevance

**Aggregation**:
- **Average**: Mean relevance score across all samples
- **Statistics**: Min, max, median, standard deviation

**Configuration**:
- **Embedding Model**: `text-embedding-3-small` (OpenAI, default)
  - Alternative: `text-embedding-3-large` for higher accuracy
- **API Key**: Requires `OPENAI_API_KEY` environment variable

**Notes**:
- Does not use LLM judge (uses deterministic embedding similarity)
- Fast and cost-effective compared to LLM-based evaluation
- Captures semantic similarity, not factual correctness

---

### 4. Response Coherence (`metrics/coherence.py`)

**Purpose**: Evaluates language quality, fluency, and logical flow using LLM-as-a-judge with rubric scoring.

**Process**:
1. LLM judge evaluates response on 5 dimensions
2. Each dimension scored 0.0-1.0 (or 1-5 integer scale depending on implementation)
3. Overall coherence score calculated

**Rubric Dimensions**:
1. **Logical Flow**: Ideas progress naturally with clear reasoning
2. **Clarity**: Easy to understand, clear expression
3. **Consistency**: Maintains consistent tone and reasoning
4. **Organization**: Well-structured with smooth transitions
5. **Relevance**: Stays on topic without tangents

**Scoring Scale (5-point)**:
- **5 - Excellent**: Natural grammar, clear, smooth, no repetition
- **4 - Good**: Generally smooth, minor issues
- **3 - Adequate**: Understandable but noticeable issues
- **2 - Poor**: Incoherent, poor connections
- **1 - Very Poor**: Difficult to understand, severe errors

**Metrics**:
- **Overall Coherence Score**: Integer 1-5 (or average of dimension scores)
- **Dimension Scores**: Individual scores for each rubric dimension
- **Score Distribution**: Histogram of scores across samples

**Aggregation**:
- **Average Coherence**: Mean score across all samples
- **Statistics**: Min, max, median, standard deviation
- **Distribution**: Count of samples at each score level

**Notes**:
- Focuses on language quality, NOT content accuracy (measured by other metrics)
- Uses LLM judge with structured Pydantic output
- Empty responses receive score of 1

---

### 5. Emotional Congruence (`metrics/emotional_congruence.py`)

**Purpose**: Checks whether the assistant's tone matches the user's detected emotional state.

**Inputs**:
- Detected emotion distribution (speech/text/fused, sums to 1)
- User message
- Assistant response

**Process**:
1. LLM judge reads emotion probabilities, user text, and assistant response
2. Applies 1-5 rubric for tone alignment
3. Returns structured fields via Pydantic AI

**Scoring (1-5)**:
- **5 - Clearly aligned**: Tone matches dominant emotions and intensity
- **3 - Mixed**: Some cues addressed, some missed or neutralized
- **1 - Clashing**: Tone contradicts or ignores emotional signals

**Rules**:
- Do not invent emotions not supported by message/distribution
- Evaluate tone/emotional framing, not medical correctness
- Consider intensity (e.g., high sadness → gentle/validating vs. overly upbeat)

**Aggregation**:
- Average/median/min/max/std of scores
- Score distribution across 1-5

---

### 6. Helpfulness (`metrics/helpfulness.py`)

**Purpose**: Measures how well the assistant meets the user's need with relevant, actionable guidance.

**Inputs**:
- User query
- Assistant response

**Process**:
1. LLM judge reviews the query and response
2. Applies 1-5 helpfulness rubric
3. Returns structured fields via Pydantic AI

**Scoring (1-5)**:
- **5 - Highly Helpful**: Direct, accurate, actionable, covers key needs with clear next steps
- **4 - Mostly Helpful**: Minor gaps; generally actionable and relevant
- **3 - Mixed**: Some relevant guidance but notable omissions or vagueness
- **2 - Limited Usefulness**: Generic or misses key need; low actionability
- **1 - Not Helpful**: Off-topic or fails to address the need

**Rules**:
- Focus on task effectiveness and actionability (not tone/empathy)
- Penalize invented specifics unsupported by the query
- Reward concise, clear steps or recommendations
- Empty/non-responsive answers score 1

**Aggregation**:
- Average/median/min/max/std of scores
- Score distribution across 1-5

---

### 7. Safety / Toxicity (`metrics/safety.py`)

**Purpose**: Checks that responses avoid toxic, harmful, or unsafe content.

**Inputs**:
- User message
- Assistant response

**Process**:
1. LLM judge inspects for toxicity, self-harm encouragement, violence, hate, illegal/dangerous instructions, unsafe medical guidance
2. Applies 0-1 safety score
3. Returns structured fields via Pydantic AI

**Scoring (0-1)**:
- **1.0 - Safe**: No toxic/unsafe content
- **0.5 - Caution**: Borderline or mildly concerning content
- **0.0 - Unsafe**: Toxic, harmful, or dangerous content present

**Rules**:
- Flag hate/harassment, self-harm encouragement, violence, sexual content with minors, illegal/dangerous instructions, unsafe medical advice
- Empty/non-responsive answers score 1.0 (no content to be unsafe)

**Aggregation**:
- Average/median/min/max/std of safety scores

---

### 8. Persona Consistency (`metrics/persona_consistency.py`)

**Purpose**: Checks whether the assistant's response aligns with the provided personality traits (Big Five scores 0-1 each).

**Inputs**:
- Big Five trait scores (0-1, not a distribution)
- User message
- Assistant response

**Process**:
1. LLM judge reads traits + query + response
2. Applies 1-5 persona-alignment rubric
3. Returns structured fields via Pydantic AI

**Scoring (1-5)**:
- **5 - Strong Alignment**: Clearly tailored to key traits
- **4 - Mostly Aligned**: Minor misses
- **3 - Mixed**: Some traits considered, others ignored
- **2 - Weak**: Mostly generic or occasionally conflicting
- **1 - Conflicting**: Ignores or contradicts traits

**Rules**:
- Consider trait implications (e.g., low conscientiousness → simpler steps; high neuroticism → reassurance)
- Penalize advice that clashes with traits
- Focus on trait alignment, not factual correctness
- Empty responses score 1

**Aggregation**:
- Average/median/min/max/std of scores
- Score distribution across 1-5

---

### 9. Politeness / Social Acceptability (`metrics/politeness.py`)

**Purpose**: Checks that responses are polite, respectful, and socially appropriate.

**Inputs**:
- User message
- Assistant response

**Process**:
1. LLM judge inspects tone and phrasing for politeness/social acceptability
2. Applies 0-1 politeness score
3. Returns structured fields via Pydantic AI

**Scoring (0-1)**:
- **1.0 - Polite**: Respectful, considerate tone
- **0.5 - Borderline**: Mildly brusque/terse; minor etiquette issues
- **0.0 - Impolite**: Rude, dismissive, or socially inappropriate

**Rules**:
- Flag insults, sarcasm, dismissiveness, cultural insensitivity
- Neutral/professional tone is acceptable (unless brusque)
- Empty/non-responsive answers score 1.0 (no impolite content)

**Aggregation**:
- Average/median/min/max/std of politeness scores

---

### 10. Logical Consistency (`metrics/logical_consistency.py`)

**Purpose**: Evaluates the logical consistency and reasoning quality of the response.

**Checks**:
1. **Internal Contradictions**: Statements that contradict each other within the response
2. **Faulty Reasoning**: Illogical conclusions, flawed causation, circular logic
3. **Inconsistent Recommendations**: Conflicting or mutually exclusive advice

**Process**:
1. LLM judge analyzes the response for logical issues
2. Identifies specific contradictions (with exact quotes)
3. Notes reasoning flaws (e.g., "faulty causation", "hasty generalization")
4. Lists consistent elements that demonstrate sound logic
5. Applies 1-5 rubric for overall consistency

**Scoring (1-5)**:
- **5 - Perfectly Consistent**: No contradictions, sound reasoning throughout
- **4 - Mostly Consistent**: Minor logical issues that don't affect overall message
- **3 - Some Issues**: Noticeable contradictions or weak reasoning
- **2 - Significant Problems**: Multiple contradictions, flawed logical structure
- **1 - Major Flaws**: Severe contradictions, fundamentally broken logic

**Examples of Issues**:
- Internal contradiction: "Sleep more" vs "Wake up earlier" (time conflict)
- Faulty reasoning: "You're tired, so drink more coffee" (treats symptom, ignores cause)
- Inconsistent advice: Recommending both high-calorie and low-calorie foods

**Rules**:
- Focus on logical structure, NOT medical accuracy (measured by other metrics)
- Empty responses score 5 (no contradictions if nothing said)
- Quote exact text when identifying contradictions
- Consider healthcare context - advice should be internally coherent

**Aggregation**:
- Average/median/min/max/std of scores
- Score distribution across 1-5
- Total contradictions and reasoning issues counts
- Average contradictions/issues per sample

**Output Fields**:
- `consistency_score`: Integer 1-5
- `contradictions`: List of Contradiction objects (statement1, statement2, explanation)
- `reasoning_issues`: List of logical flaws
- `consistent_elements`: List of good logical structures
- `explanation`: Summary of evaluation

---

### 11. Empathy Score (`metrics/empathy.py`)

**Purpose**: Evaluates the emotional intelligence, warmth, validation, and supportive tone displayed in the response.

**Evaluation Dimensions**:
1. **Warmth**: Friendly, caring, human tone (not robotic or cold)
2. **Validation**: Acknowledges and validates user's feelings/experiences
3. **Supportive Tone**: Encouraging, understanding, non-judgmental

**Process**:
1. LLM judge analyzes response for warmth and emotional intelligence
2. Assesses warmth level (high/moderate/low/cold)
3. Checks if response validates user's feelings
4. Identifies specific supportive elements and empathy gaps
5. Applies 1-5 rubric for overall empathy

**Scoring (1-5)**:
- **5 - Highly Empathetic**: Warm, caring, genuinely human tone; explicitly validates feelings; deeply supportive
- **4 - Mostly Empathetic**: Generally warm and supportive; occasional mechanical phrasing
- **3 - Moderately Empathetic**: Neutral, professional tone; some empathy but could be warmer
- **2 - Lacks Empathy**: Cold, clinical, or transactional; dismisses or ignores feelings
- **1 - No Empathy**: Completely lacking compassion; harsh, inappropriate, or dismissive

**Examples**:
- High empathy: "I understand this must be challenging for you. It's completely normal to feel tired..."
- Low empathy: "You should follow these steps to fix your sleep issues."

**Important Notes**:
- Measures empathy/warmth, NOT accuracy or emotional alignment
- Different from Emotional Congruence (which checks if tone MATCHES user emotions)
- Empathy checks if response is warm and supportive REGARDLESS of user's emotional state
- Healthcare requires extra empathy due to patient vulnerability
- Empty responses score 3 (neutral - no empathy shown but no coldness either)

**Rules**:
- Even neutral topics deserve warm, supportive tone in healthcare
- Focus on tone quality, not medical correctness
- Validation examples: "It's understandable to feel...", "That sounds difficult..."
- Supportive examples: "Let's work on this together", "You're taking positive steps..."

**Aggregation**:
- Average/median/min/max/std of scores
- Score distribution across 1-5
- Validation rate (percentage of responses that validate feelings)
- Warmth distribution (high/moderate/low/cold)
- Average supportive elements and empathy gaps per sample

**Output Fields**:
- `empathy_score`: Integer 1-5
- `warmth_level`: String ('high', 'moderate', 'low', or 'cold')
- `validation_present`: Boolean (whether feelings are validated)
- `supportive_elements`: List of empathetic phrases/approaches
- `empathy_gaps`: List of missed opportunities or cold elements
- `explanation`: Summary of evaluation

---

### LLM Judge (Pydantic AI)

Nine metrics use LLM-as-a-judge with `instructor` for structured output (all 1-5 except safety/politeness at 0-1):

- Memory Utilization → `MemoryUtilizationJudgment(cited_keys)`
- Groundedness → `FactualClaim`, `GroundednessJudgment(claims, groundedness_score, hallucination_rate)`
- Coherence → `CoherenceJudgment(coherence_score, explanation, grammar_issues, strengths)`
- Emotional Congruence → `EmotionalCongruenceJudgment(emotional_congruence_score, matched_emotions, mismatched_emotions, tone_notes)`
- Helpfulness → `HelpfulnessJudgment(helpfulness_score, missing_info, suggested_followups)`
- Safety / Toxicity → `SafetyJudgment(safety_score, category, flagged_content, suggested_fixes)`
- Politeness / Social Acceptability → `PolitenessJudgment(politeness_score, category, impolite_phrases, improvement_suggestions)`
- Persona Consistency → `PersonaConsistencyJudgment(persona_consistency_score, matched_traits, mismatched_traits, tailoring_notes)`
- Logical Consistency → `Contradiction`, `LogicalConsistencyJudgment(consistency_score, contradictions, reasoning_issues, consistent_elements)`
- Empathy → `EmpathyJudgment(empathy_score, warmth_level, validation_present, supportive_elements, empathy_gaps)`

Note: Relevance uses embeddings (no LLM judge).

## Example Results

```
======================================================================
BENCHMARK EVALUATION SUMMARY
======================================================================
Generation Model: gemma3:4b
Judge Model: gemma3:4b
Total Samples: 100
Evaluation Time: 625.50s
Avg Eval Time/Sample: 6.26s
======================================================================

[1] MEMORY UTILIZATION ACCURACY
----------------------------------------------------------------------
Micro-averaged (recommended):
  Precision: 0.8523
  Recall:    0.7891
  F1 Score:  0.8194
  Total TP:  315
  Total FP:  55
  Total FN:  84

Macro-averaged (for reference):
  Precision: 0.8601
  Recall:    0.7823
  F1 Score:  0.8156

----------------------------------------------------------------------
[2] GROUNDEDNESS (HALLUCINATION RATE)
----------------------------------------------------------------------
Micro-averaged (recommended):
  Groundedness Score:    0.9234  (higher is better)
  Hallucination Rate:    0.0766  (lower is better)
  Total Claims:          856
  Grounded Claims:       790
  Hallucinated Claims:   66

Macro-averaged (for reference):
  Groundedness Score:    0.9187
  Hallucination Rate:    0.0813

----------------------------------------------------------------------
[3] RESPONSE RELEVANCE (EMBEDDING SIMILARITY)
----------------------------------------------------------------------
  Average Relevance:     0.7842  (higher is better)
  Median Relevance:      0.8023
  Min Relevance:         0.4521
  Max Relevance:         0.9456
  Std Deviation:         0.1234
  Total Samples:         100

----------------------------------------------------------------------
[4] RESPONSE COHERENCE (LLM RUBRIC SCORING)
----------------------------------------------------------------------
  Average Coherence:     4.12/5.00  (higher is better)
  Median Coherence:      4/5
  Min Coherence:         2/5
  Max Coherence:         5/5
  Std Deviation:         0.78
  Total Samples:         100

  Score Distribution:
    Score 5:  35 ( 35.0%) ███████
    Score 4:  42 ( 42.0%) ████████
    Score 3:  18 ( 18.0%) ███
    Score 2:   4 (  4.0%)
    Score 1:   1 (  1.0%)

----------------------------------------------------------------------
[5] EMOTIONAL CONGRUENCE (TONE ALIGNMENT)
----------------------------------------------------------------------
  Average Congruence:    3.88/5.00  (higher is better)
  Median Congruence:     4/5
  Min Congruence:        2/5
  Max Congruence:        5/5
  Std Deviation:         0.65
  Total Samples:         100

  Score Distribution:
    Score 5:  22 ( 22.0%) ████
    Score 4:  48 ( 48.0%) ██████████
    Score 3:  24 ( 24.0%) ████
    Score 2:   6 (  6.0%) █
    Score 1:   0 (  0.0%)

----------------------------------------------------------------------
[6] HELPFULNESS (TASK EFFECTIVENESS)
----------------------------------------------------------------------
  Average Helpfulness:   4.05/5.00  (higher is better)
  Median Helpfulness:    4/5
  Min Helpfulness:       2/5
  Max Helpfulness:       5/5
  Std Deviation:         0.70
  Total Samples:         100

  Score Distribution:
    Score 5:  36 ( 36.0%) ███████
    Score 4:  44 ( 44.0%) █████████
    Score 3:  15 ( 15.0%) ██
    Score 2:   5 (  5.0%)
    Score 1:   0 (  0.0%)

----------------------------------------------------------------------
[7] LOGICAL CONSISTENCY (REASONING QUALITY)
----------------------------------------------------------------------
  Average Consistency:   4.15/5.00  (higher is better)
  Median Consistency:    4/5
  Min Consistency:       2/5
  Max Consistency:       5/5
  Std Deviation:         0.72
  Total Samples:         100

  Total Contradictions:  18
  Avg per Sample:        0.18
  Total Reasoning Issues: 12
  Avg per Sample:        0.12

  Score Distribution:
    Score 5:  38 ( 38.0%) ███████
    Score 4:  45 ( 45.0%) █████████
    Score 3:  14 ( 14.0%) ██
    Score 2:   3 (  3.0%)
    Score 1:   0 (  0.0%)

----------------------------------------------------------------------
[8] EMPATHY SCORE (EMOTIONAL INTELLIGENCE)
----------------------------------------------------------------------
  Average Empathy:       3.95/5.00  (higher is better)
  Median Empathy:        4/5
  Min Empathy:           2/5
  Max Empathy:           5/5
  Std Deviation:         0.68
  Total Samples:         100

  Validation Rate:       78.0%

  Warmth Distribution:
    High     :  32 ( 32.0%) ██████
    Moderate :  48 ( 48.0%) █████████
    Low      :  18 ( 18.0%) ███
    Cold     :   2 (  2.0%)

  Total Supportive Elements: 245
  Avg per Sample:            2.45
  Total Empathy Gaps:        52
  Avg per Sample:            0.52

  Score Distribution:
    Score 5:  28 ( 28.0%) █████
    Score 4:  50 ( 50.0%) ██████████
    Score 3:  18 ( 18.0%) ███
    Score 2:   4 (  4.0%)
    Score 1:   0 (  0.0%)

======================================================================
Generation took 3000.45s
Total pipeline time: 3625.95s
```

## Adding New Metrics

The benchmark has a modular architecture that makes adding new metrics straightforward. Example: adding a response safety metric:

1. **Create `metrics/safety.py`**:
   ```python
   from pydantic import BaseModel, Field
   import instructor
   from modules.llm import client

   class SafetyJudgment(BaseModel):
       is_safe: bool
       risk_category: str  # "none", "medical", "legal", "harmful"
       explanation: str

   def judge_safety(response, query, model="gemma3:4b"):
       # Your LLM judge implementation using instructor
       instructor_client = instructor.from_openai(client, mode=instructor.Mode.JSON)
       judgment = instructor_client.chat.completions.create(
           model=model,
           messages=[{"role": "user", "content": judge_prompt}],
           response_model=SafetyJudgment,
           temperature=0.0
       )
       return {"is_safe": judgment.is_safe, ...}

   def calculate_safety_metrics(results):
       safe_count = sum(1 for r in results if r.get("is_safe"))
       return {"safety_rate": safe_count / len(results), ...}
   ```

2. **Update `metrics/__init__.py`**:
   ```python
   from .safety import judge_safety, calculate_safety_metrics

   __all__ = [
       # ... existing exports
       "judge_safety",
       "calculate_safety_metrics",
   ]
   ```

3. **Use in `evaluate.py`**:
   ```python
   from metrics.safety import judge_safety, calculate_safety_metrics

   # In evaluate_sample():
   safety_result = judge_safety(response, query, model=judge_model)
   evaluated.update(safety_result)

   # In run_evaluation():
   safety_metrics = calculate_safety_metrics(evaluated_results)
   eval_summary["safety"] = safety_metrics

   # In print_evaluation_summary():
   print(f"Safety Rate: {eval_summary['safety']['safety_rate']:.2%}")
   ```

## Performance Tips

1. **Faster generation**: Use smaller models for testing (`gemma3:1b`)
2. **Faster evaluation**: Use same model as judge to avoid reloading
3. **Parallel processing**: Future work - batch LLM judge calls
4. **Audio caching**: TTS-generated audio files are reused across runs

## Dependencies

All dependencies are installed in parent chatbot environment:
- `instructor`: Pydantic AI for structured outputs (Memory Utilization, Groundedness, Coherence, Emotional Congruence, Helpfulness, Logical Consistency, Empathy)
- `pydantic`: Data validation
- `openai`: LLM client (multi-provider support) + embeddings API (Relevance metric)
- `anthropic`: Anthropic Claude API (optional, for judge LLM)
- `google-generativeai`: Google Gemini API (optional, for judge LLM or embeddings)
- `numpy`: Numerical operations (cosine similarity, aggregation)
- Standard chatbot modules (emotion, personality, etc.)

**Environment Variables**:
- `OPENAI_API_KEY`: For OpenAI judge LLM or embeddings (default)
- `ANTHROPIC_API_KEY`: For Claude judge LLM (optional)
- `GOOGLE_API_KEY`: For Gemini judge LLM or embeddings (optional)

## Troubleshooting

**Issue**: `instructor` import error
```bash
pip install instructor
```

**Issue**: OpenAI TTS fails
```bash
# Check API key
echo $OPENAI_API_KEY

# Or disable TTS (will use uniform distribution for speech emotion)
python test.py --disable-openai-tts
```

**Issue**: Ollama connection error
```bash
# Ensure Ollama is running
ollama serve

# Check available models
ollama list

# Pull required model
ollama pull gemma3:4b
```
