# LLM Benchmark for Memory Citation

Evaluates how well responses cite stored memories on a 100-sample healthcare dialogue set. Local generations come from Ollama; judging uses cloud APIs across 12 metrics (persona, emotion alignment, memory utilization, relevance/coherence/helpfulness/safety, etc.).

## Requirements
- Ollama running with the models you want to test (defaults include `gemma3:4b`, `phi3:3.8b`, `qwen2.5:3b-instruct`, `mistral:7b-instruct`, `qwen2.5:7b-instruct`, `llama3.1:8b`).
- API keys for judge models: set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`.
- Python deps: `pip install instructor pydantic openai anthropic google-generativeai numpy pandas`.

## Run
```bash
cd chatbot/benchmark
python batch_evaluate_ollama.py                 # all 100 samples, default models
python batch_evaluate_ollama.py --limit 10      # quick smoke test
python batch_evaluate_ollama.py --models gemma3:4b phi3:3.8b --max-workers 6
```

## Outputs
- `results/{model}_{num_samples}.csv` – per-sample scores for all 12 metrics.
- `results/model_comparison.txt` – averaged scores across models.

## MedQuAD medical QA benchmark (new)
- Script: `medquad_eval.py` (standalone; not reused from `batch_evaluate_ollama.py`).
- Downloads the MedQuAD CSV to a temp dir via Kaggle CLI, samples N=100 (default, seed=42), stores only the sampled subset at `dataset/MedQA/medquad_sampled.csv`.
- Prompts each local Ollama model on question-only; judges with OpenAI `o3-mini` (fallback `gpt-4.1`) using a 1–5 rubric normalized to 0–1; writes per-model CSVs and a summary TXT in `results/`.
- Usage:
  ```bash
  cd chatbot/benchmark
  # prerequisites: kaggle CLI configured; OPENAI_API_KEY set
  python medquad_eval.py --limit 100 --models gemma3:4b phi3:3.8b --seed 42
  ```

## Dataset
- Samples live in `dataset/samples/<id>/sample.json`; see `dataset/README.md` for full format.
- Each sample includes dialogue history, memory key/value pairs, and required memory keys for evaluation.
