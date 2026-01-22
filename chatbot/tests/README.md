# Chatbot Test Suite

Benchmarks and regression packs for the chatbot stack.

## Suites
- **chat4test** — info extraction and evaluation against ground truth.
  - `cd chat4test`
  - Extract: `python extract.py --user <id> --project_url http://localhost:8019 --project_token secret [--rounds-per-chunk N --skip-profile]`
  - Evaluate: `python evaluate.py [--output-dir chats/output --ground-truth-dir chats/ground_truth]`
- **prompts4test** — automated prompt/chunk-size experiments (see `prompts4test/test/README.md` for details).
  - `cd prompts4test/test`
  - `python run_experiments.py --rounds 5 10 20 [--user-prefix bench --skip-eval]`
- **cache4test** — Ollama performance with/without Flash Attention and KV cache.
  - `cd cache4test`
  - `python benchmark_extract.py --config baseline|flash|kvcache|both --user mock_user`
- **whisper4test** — Whisper ASR accuracy and speed across models/configs.
  - `cd whisper4test`
  - `python whisper_test.py`  # writes JSONL results to `results.txt`

Each line format: `<audio_id> <transcription_text>`

### Evaluation Method

**Word Error Rate Calculation:**
Uses Levenshtein edit distance algorithm to calculate the difference between reference and recognized text:
- Deletion operations
- Insertion operations
- Substitution operations

**Text Normalization:**
For fair comparison, all text undergoes normalization:
1. Convert to uppercase
2. Remove punctuation
3. Normalize whitespace
4. Tokenize

**Variant Generation:**
Considers different word variations (singular/plural, tense, etc.) to improve matching accuracy.

---

## Common Testing Tools and Methods

### Data Chunking Strategy

All conversation tests use a unified chunking strategy:
```python
def chunk_messages(messages, rounds_per_chunk=5):
    """
    Chunk conversations by user turns
    - Each chunk contains specified number of complete user-assistant conversation rounds
    - Ensures each chunk ends with an assistant reply
    """
```

### Performance Measurement Metrics

1. **Time Metrics:**
   - Cost Time: Total processing time
   - TTFT: Time to first token
   - Prompt Eval Duration: Prompt evaluation time
   - Eval Duration: Generation evaluation time

2. **Accuracy Metrics:**
   - Precision: Precision rate
   - Recall: Recall rate
   - F1 Score: F1 score
   - Accuracy: Accuracy rate
   - WER: Word error rate

3. **Efficiency Metrics:**
   - Generation Speed: Generation speed (tokens/second)
   - Redundancy Rate: Redundancy rate
   - Token Count: Token count

### Results Output Formats

- **Text Format**: For manual review (.txt)
- **JSON Format**: For programmatic analysis (.json)
- **JSON Lines Format**: For streaming append (.txt with JSONL)

---

## Quick Start

### 1. Run Complete Conversation Quality Test
```bash
cd chat4test
python extract.py --user 54 --skip-profile
python evaluate.py
```

### 2. Run Automated Prompt Experiments
```bash
cd prompts4test/test
python3 run_experiments.py --rounds 5 10 20 --user-prefix exp
```

### 3. Run Cache Performance Tests
```bash
cd cache4test
for config in baseline flash kvcache both; do
    python benchmark_extract.py --config $config --user mock_user
done
```

### 4. Run Whisper Benchmark Tests
```bash
cd whisper4test
python whisper_test.py
```

---

## Dependencies

### Python Packages
```
- memobase
- ollama
- transformers
- torch
- httpx
- rich
- tiktoken (optional, for token counting)
```

### External Services
- **MemoBase Server**: For chat4test (default: http://localhost:8019)
- **Ollama**: For prompts4test and cache4test (default: http://localhost:11434)
- **CUDA**: For whisper4test (GPU inference, optional)

---

## Notes

1. **Resource Requirements:**
   - Whisper tests require significant GPU memory (recommended 16GB+ for large models)
   - Automated experiments will restart Ollama service multiple times, requiring root privileges

2. **Data Preparation:**
   - Ensure conversation data and ground truth data correspond one-to-one
   - Audio file and transcription text IDs must match

3. **Configuration Validation:**
   - Flash Attention requires hardware support
   - FP16 not available on CPU

4. **Results Analysis:**
   - All tests generate detailed logs and result files
   - JSON format facilitates subsequent data analysis and visualization

---

## Extension and Customization

### Adding New Test Models
Modify model list in respective test scripts:
```python
models_to_benchmark = [
    "your-model-name",
    # ...
]
```

### Adjusting Test Parameters
Modify constants in scripts or use command-line arguments:
```python
ROUNDS_PER_CHUNK = 5  # Conversation rounds per chunk
MAX_TOKENS = 100      # Maximum generation tokens
```

### Custom Evaluation Metrics
Extend evaluation logic in `evaluate.py` to add new metric calculations.

---

## Troubleshooting

### Common Issues

1. **Ollama Connection Failed**
   - Confirm Ollama service is running
   - Check port configuration (default 11434)

2. **Model Loading Failed**
   - Confirm model is downloaded: `ollama pull <model-name>`
   - Check available memory

3. **Abnormal Evaluation Results**
   - Verify ground truth format is correct
   - Check data file encoding (should be UTF-8)

4. **GPU Out of Memory**
   - Reduce batch size
   - Use smaller model variants
   - Lower precision (use FP16)

---

## Contributing Guidelines

When adding new tests, follow existing directory structure and naming conventions:
- Use descriptive directory names (e.g., `<feature>4test`)
- Provide complete data samples and ground truth
- Include clear usage instructions and parameter descriptions
- Output structured result files

---

## References

- MemoBase API Documentation
- Ollama API Documentation
- Whisper Model Documentation
- Transformers Library Documentation
