# Memobase-MCP: Long-Term Memory for AI Agents

MCP server backed by MemoBase that exposes memory tools for agents.

## What it provides
- `save_memory` – store information with semantic indexing.
- `get_user_profiles` – fetch profiles for a MemoBase user.
- `search_memories` – semantic search for relevant context.

## Prereqs
- Python 3.11+
- MemoBase project URL + API key (local default: `http://localhost:8019`, `secret`).

## Setup
```bash
cd memobase/src/mcp
uv pip install -e .          # or pip/pdm/poetry equivalent
cp .env.example .env         # set TRANSPORT, HOST/PORT, MEMOBASE_BASE_URL, MEMOBASE_API_KEY
```

Docker:
```bash
docker build -t memobase-mcp --build-arg PORT=8050 .
docker run --env-file .env -p 8050:8050 memobase-mcp
```

## Run
```bash
# SSE transport (default)
TRANSPORT=sse uv run src/main.py

# stdio for local MCP clients
TRANSPORT=stdio uv run src/main.py
```

## Minimal Client Config (Cursor/Windsurf)
```json
{
  "mcpServers": {
    "memobase": {
      "transport": "sse",
      "url": "http://localhost:8050/sse"
    }
  }
}
```
