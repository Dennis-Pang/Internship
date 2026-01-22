# Locomo Benchmark for Various Memory Backends

Compares memory systems (Memobase, mem0, zep, langmem, RAG, naive LLM) on the Locomo long-conversation dataset.

## Headline Results (LLM Judge Score)
| Method              | Single-Hop | Multi-Hop | Open Domain | Temporal | Overall |
| ------------------- | ---------- | --------- | ----------- | -------- | ------- |
| Mem0                | 67.13      | 51.15     | 72.93       | 55.51    | 66.88   |
| Mem0-Graph          | 65.71      | 47.19     | 75.71       | 58.13    | 68.44   |
| LangMem             | 62.23      | 47.92     | 71.12       | 23.43    | 58.10   |
| Zep                 | 61.70      | 41.35     | 76.60       | 49.31    | 65.99   |
| OpenAI              | 63.79      | 42.92     | 62.29       | 21.71    | 52.90   |
| Memobase v0.0.32    | 63.83      | 52.08     | 71.82       | 80.37    | 70.91   |
| Memobase v0.0.37    | 70.92      | 46.88     | 77.17       | 85.05    | 75.78   |

Artifacts for Memobase runs live under `fixture/memobase/`. Re-score any run with:
```bash
python generate_scores.py --input_path fixture/memobase/memobase_eval_0710_3000.json
```

## Setup
- Download `locomo10.json` into `dataset/`.
- `.env` needs `OPENAI_API_KEY`; add MemoBase creds for local runs:
  - `MEMOBASE_API_KEY=...`
  - `MEMOBASE_PROJECT_URL=http://localhost:8019` (optional override)
- Install deps as needed: `pip install memobase mem0 zep_cloud langgraph langmem`.

## Run (Memobase flow)
```bash
make run-memobase-add       # ingest data
make run-memobase-search    # answer benchmark questions
python evals.py --input_file results.json --output_file evals.json
python generate_scores.py --input_path evals.json
```
Other backends share the same make targets (`run-mem0-*`, `run-zep-*`, `run-langmem`, `run-rag`, `run-openai`).

## Project Structure
```
.
├── src/          # memory implementations (memobase, mem0, zep, rag, langmem, openai)
├── metrics/      # evaluation metrics
├── dataset/      # Locomo data
├── results/      # saved answers and evals
├── evals.py      # scoring
├── run_experiments.py
└── generate_scores.py
```
