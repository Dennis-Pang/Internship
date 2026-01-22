# Automated Prompt Experiments

Runs extract + evaluation loops over fixed chat data to measure how chunk size (N rounds) affects quality and latency.

## Quick Start
```bash
# Requirements: Ollama running with qwen2.5:7b-instruct, MemoBase at http://localhost:8019
cd chatbot/tests/prompts4test/test
python3 run_experiments.py --rounds 5 10 20 [--user-prefix bench --skip-eval]
```
- Uses `chats/mock_user/*.json` with ground truth under `chats/ground_truth/`.
- Results land in `results/experiment_summary_<timestamp>.json`; Ollama logs in `logs/ollama_experiment.log`.
- Each run creates a fresh MemoBase user ID unless you pass `--user-prefix`/`--user-id`.

## Standalone Scripts
```bash
python3 extract.py --rounds-per-chunk 5 \
  --project_url http://localhost:8019 --project_token secret \
  [--user-id demo --skip-profile]

python3 evaluate.py --output-dir output --ground-truth-dir ground_truth
```

## Notes
- `run_experiments.py` warms the model and records TTFT/prompt/generation timing from Ollama.
- Defaults assume `qwen2.5:7b-instruct`, Flash Attention, KV cache; adjust inside the script if needed.
- Data + outputs stay local to `chats/`, `logs/`, and `results/` within this folder.
