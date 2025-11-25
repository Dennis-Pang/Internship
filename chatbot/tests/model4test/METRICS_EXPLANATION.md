# Benchmark Metrics Explanation

This document provides detailed explanations of all metrics used in the model evaluation benchmark.

## 📊 Overview

The benchmark evaluates LLM models on their ability to extract structured information (slots) from conversational data and store them in a memory system. Models are evaluated across 3 user profiles with 5 conversation sessions each.

---

## 🎯 Core Performance Metrics

### 1. **Precision**
**Formula**: `Precision = TP / (TP + FP)`

**What it measures**: Of all the slots the model predicted, what percentage were correct?

**Calculation in code** (`slot_eval.py:34-36`):
```python
def precision(self) -> float:
    denom = self.tp + self.fp
    return self.tp / denom if denom else 0.0
```

**Example**:
- Model predicts 10 slots
- 7 are correct (TP), 3 are wrong (FP)
- Precision = 7 / (7 + 3) = 0.70 (70%)

**Interpretation**:
- **High precision** = Low false positives, model is conservative and accurate
- **Low precision** = Many hallucinations, model adds incorrect information

### 2. **Recall**
**Formula**: `Recall = TP / (TP + FN)`

**What it measures**: Of all the slots that should have been found (ground truth), what percentage did the model actually find?

**Calculation in code** (`slot_eval.py:38-41`):
```python
def recall(self) -> float:
    denom = self.tp + self.fn
    return self.tp / denom if denom else 0.0
```

**Example**:
- Ground truth has 15 slots
- Model found 12 (TP), missed 3 (FN)
- Recall = 12 / (12 + 3) = 0.80 (80%)

**Interpretation**:
- **High recall** = Model finds most information, good coverage
- **Low recall** = Model misses important information

### 3. **F1 Score**
**Formula**: `F1 = 2 × (Precision × Recall) / (Precision + Recall)`

**What it measures**: Harmonic mean of precision and recall, balancing both metrics.

**Calculation in code** (`slot_eval.py:43-49`):
```python
def f1(self) -> float:
    p = self.precision
    r = self.recall
    if not p and not r:
        return 0.0
    return 2 * p * r / (p + r)
```

**Why harmonic mean?**: It penalizes extreme imbalances. If either precision or recall is very low, F1 will be low.

**Example**:
- Precision = 0.70, Recall = 0.80
- F1 = 2 × (0.70 × 0.80) / (0.70 + 0.80) = 0.747

**Interpretation**:
- **F1 = 1.0**: Perfect precision and recall
- **F1 = 0.0**: Complete failure
- **F1 > 0.7**: Generally considered good performance

### 4. **Exact Match Coverage**
**Formula**: `Exact Match = (Number of slots with exact match) / (Total slots)`

**What it measures**: Percentage of slots where the model's output exactly matches the ground truth (after normalization).

**Calculation in code** (`slot_eval.py:51-53`):
```python
def exact_rate(self) -> float:
    return self.exact_match / self.count if self.count else 0.0
```

**Normalization** (`slot_eval.py:246-251`):
```python
def canonicalize(value: str) -> str:
    text = NON_ASCII_RE.sub("", value)  # Remove non-ASCII
    text = text.replace("_", " ")        # Normalize underscores
    text = re.sub(r"\s+", " ", text)     # Collapse whitespace
    text = PUNCT_RE.sub(" ", text)       # Remove punctuation
    return text.lower().strip()          # Lowercase and trim
```

**Example**:
- Slot 1: "Software Engineer" vs "software engineer" → **Exact Match** ✓
- Slot 2: "reading, hiking" vs "reading, swimming" → **No Match** ✗
- Slot 3: "25 years old" vs "25" → **No Match** ✗

**Interpretation**:
- Stricter than F1, requires complete accuracy
- High exact match indicates model produces precise, well-formatted outputs

### 5. **LLM Judge Score**
**What it measures**: A secondary evaluation metric where an LLM evaluates the quality of extracted information (not shown in provided code, likely external evaluation).

**Typical approach**:
- Another LLM (e.g., GPT-4) rates the extracted slots on semantic accuracy
- Scores from 0.0 (completely wrong) to 1.0 (perfect)
- Provides human-like quality assessment

**Interpretation**:
- Captures nuanced correctness that strict matching might miss
- Lower scores may indicate semantic misunderstandings

---

## 📝 Token-Level Metrics

These metrics evaluate at the word/token level rather than slot level.

### 6. **Token Precision**
**Formula**: `Token Precision = Matched Tokens / Total Predicted Tokens`

**What it measures**: Of all tokens in predicted values, what percentage match ground truth tokens?

**Calculation** (`slot_eval.py:316-318`):
```python
token_metrics.matched += sum((Counter(gt_tokens) & Counter(pred_tokens)).values())
token_metrics.pred_total += len(pred_tokens)
# Later: matched / pred_total
```

**Example**:
- Ground truth: "software engineer at Google"
- Prediction: "senior software engineer at Microsoft"
- Matched tokens: "software", "engineer", "at" (3 tokens)
- Predicted tokens: 5 total
- Token Precision = 3/5 = 0.60

### 7. **Token Recall**
**Formula**: `Token Recall = Matched Tokens / Total Ground Truth Tokens`

**What it measures**: Of all tokens in ground truth, what percentage appear in predictions?

**Example** (using same data):
- Ground truth tokens: 4 total
- Matched tokens: 3
- Token Recall = 3/4 = 0.75

### 8. **Token F1**
**Formula**: Same as regular F1, but using token-level precision and recall.

### 9. **BLEU-1 Score**
**Formula**: `BLEU-1 = Precision × Brevity Penalty`

**What it measures**: Machine translation metric adapted for slot extraction. Measures unigram (single word) overlap with brevity penalty.

**Calculation** (`slot_eval.py:264-278`):
```python
def bleu1_score(pred_tokens: Sequence[str], ref_tokens: Sequence[str]) -> float:
    if not pred_tokens:
        return 0.0

    # Count token overlaps
    pred_counts = Counter(pred_tokens)
    ref_counts = Counter(ref_tokens)
    overlap = sum((pred_counts & ref_counts).values())

    # Precision component
    precision = overlap / sum(pred_counts.values()) if pred_counts else 0.0

    # Brevity penalty (penalizes short predictions)
    if pred_len <= ref_len:
        bp = math.exp(1 - ref_len / pred_len) if pred_len else 0.0
    else:
        bp = 1.0

    return precision * bp
```

**Brevity Penalty (BP)**:
- If prediction is shorter than reference, apply exponential penalty
- Prevents gaming the metric with very short predictions
- BP = exp(1 - ref_length / pred_length) when pred < ref

**Example**:
- Reference: "software engineer" (2 tokens)
- Prediction: "engineer" (1 token)
- Precision: 1/1 = 1.0
- BP: exp(1 - 2/1) = exp(-1) ≈ 0.368
- BLEU-1: 1.0 × 0.368 = 0.368

---

## ⏱️ Latency Metrics

### 10. **Mean Latency**
**What it measures**: Average processing time per conversation session.

**Calculation**: `Sum of all durations / Number of sessions`

**Example** (from results):
- Llama: 460.4 seconds/session (≈7.7 minutes)
- Mistral: 258.4 seconds/session (≈4.3 minutes)
- Qwen: 349.9 seconds/session (≈5.8 minutes)

### 11. **Median Latency**
**What it measures**: Middle value of latency distribution (50th percentile).

**Why median?**: More robust to outliers than mean.

**Example**:
- Latencies: [200s, 250s, 400s, 600s, 800s]
- Median = 400s (middle value)
- Mean = 450s (affected by 800s outlier)

### 12. **P95 Latency**
**What it measures**: 95th percentile latency - 95% of requests complete faster than this.

**Calculation** (`slot_eval.py:374-375`):
```python
duration_values.sort()
p95_index = max(int(len(duration_values) * 0.95) - 1, 0)
p95 = duration_values[p95_index]
```

**Why P95?**: Standard SLA metric, captures tail latency without being skewed by extreme outliers.

### 13. **Total Latency**
**What it measures**: Sum of all processing times across all sessions.

**Use case**: Estimate total compute cost or processing time for batch jobs.

---

## 🎭 Per-Topic Breakdown

The benchmark evaluates performance separately for 3 conversation topics:

1. **basic_info**: Name, age, gender, location, etc.
2. **interests**: Hobbies, preferences, likes/dislikes
3. **mental_state**: Emotions, stress levels, mental health

**Calculation** (`slot_eval.py:289, 363-367`):
```python
per_topic: Dict[Topic, SlotMetrics] = defaultdict(SlotMetrics)

# Later, for each slot:
per_topic[topic].update(tp, fp, fn, exact_match)

# Output per-topic metrics
for topic, topic_metrics in sorted(per_topic.items()):
    print(f"  {topic:20s} P={topic_metrics.precision:.3f} "
          f"R={topic_metrics.recall:.3f} F1={topic_metrics.f1:.3f}")
```

**Why per-topic?**: Identifies model strengths/weaknesses across different information types.

---

## 🔍 Extraneous Output (Hallucinations)

### 14. **Extra Slots**
**What it measures**: Number of slots predicted by the model that don't exist in ground truth.

**Example**:
- Ground truth has slots: [name, age, hobby]
- Model predicts: [name, age, hobby, career_goal, dream_job]
- Extra slots = 2 (career_goal, dream_job)

**Calculation** (`slot_eval.py:335-340`):
```python
for (topic, field), pred_entry in pred_slots.items():
    if (topic, field) not in gt_slots and pred_entry.values:
        extra_slot_counts[topic] += 1
        extra_value_counts[topic] += len(pred_entry.values)
        metrics.fp += 1  # Count as false positive
```

### 15. **Extra Values**
**What it measures**: Total number of individual values in extraneous slots.

**Example**:
- Extra slot 1 (career_goal): ["become a doctor", "help people"] → 2 values
- Extra slot 2 (dream_job): ["surgeon"] → 1 value
- Extra values = 3 total

**Interpretation**:
- **High extra output** = Model hallucinates information not present in conversation
- **Low extra output** = Model is conservative and accurate

---

## 📐 How Metrics Are Computed

### True Positives (TP), False Positives (FP), False Negatives (FN)

**Slot-level evaluation** (`slot_eval.py:297-340`):
```python
for session in session_ids:
    gt_slots = ground_truth.get(session, {})
    pred_slots = predictions.get(session, {})

    # Check each ground truth slot
    for (topic, field), gt_entry in gt_slots.items():
        pred_entry = pred_slots.get((topic, field))
        pred_has_values = bool(pred_entry and pred_entry.values)

        if pred_has_values:
            metrics.update(tp=1, fp=0, fn=0, exact=True)  # Found!
        else:
            metrics.update(tp=0, fp=0, fn=1, exact=False) # Missed!

    # Check for extra predictions
    for (topic, field), pred_entry in pred_slots.items():
        if (topic, field) not in gt_slots and pred_entry.values:
            metrics.fp += 1  # Hallucination!
```

**Key insight**: A slot is either found (TP) or missed (FN). Extra predictions count as FP.

---

## 📊 Results Summary

| Model | F1 | Latency | Strengths | Weaknesses |
|-------|----|---------|-----------| ------------|
| **Llama Flash** | 0.457 | 460.4s | High recall (0.58) | Low precision (0.38), slowest, many hallucinations (48 extra slots) |
| **Mistral Flash** | 0.466 | 258.4s | **Fastest**, fewest hallucinations (29 extra slots) | Lowest recall (0.48), lowest LLM judge score (0.10) |
| **Qwen Flash** | **0.714** | 349.9s | **Best overall**, highest precision (0.59) & recall (0.90), best per-topic performance | Moderate hallucinations (31 extra slots) |

### Key Findings

1. **Qwen Flash is the clear winner**:
   - 50% better F1 than competitors
   - Excellent performance across all topics (F1 > 0.89)
   - 90% exact match coverage

2. **Mistral Flash is the speed champion**:
   - 44% faster than Llama, 26% faster than Qwen
   - But sacrifices recall and accuracy

3. **Llama Flash struggles with hallucinations**:
   - 48 extra slots (60% more than Mistral)
   - Lowest precision at 0.377

4. **Topic difficulty ranking**:
   - **Easiest**: basic_info (models achieve F1 ≥ 0.42)
   - **Moderate**: mental_state (F1: 0.53-0.95)
   - **Hardest**: interests (F1: 0.27-0.89, high variance)

---

## 🎓 Metric Selection Guide

**For production deployment, prioritize:**
- **F1 Score**: Overall performance balance
- **Precision**: If false information is costly (e.g., medical, legal)
- **Recall**: If missing information is costly (e.g., customer support)
- **P95 Latency**: For real-time applications with SLA requirements

**For research/comparison:**
- **Per-topic F1**: Identify domain-specific strengths
- **Token metrics**: Fine-grained text quality
- **BLEU-1**: Semantic similarity to reference outputs
- **LLM Judge**: Human-like quality assessment

---

## 📚 References

- Code implementation: `slot_eval.py`
- Raw results: `slot_eval_output.txt`
- Summary: `evl_result.md`
- Visualization: `visualize_benchmark.py`
