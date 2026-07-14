---
name: ollama-embeddings
description: Set up local text embeddings with Ollama and EmbeddingGemma 300M for the Social Work Meta-Data Project databases. Load this when the user wants semantic (meaning-based) search and the machine does not yet have Ollama running. Not needed for SQL, keyword, or filter queries.
---

# Local Embeddings with Ollama + EmbeddingGemma — Setup Skill

This skill does one thing: get a local embedding endpoint running so queries can be turned into 768-dimension meaning vectors that match the vectors stored in the SWRD and SSWR databases. It is a prerequisite **only** for semantic and hybrid search — SQL, keyword search, and filters work without it.

## Why this exact model

The databases' abstracts were embedded with **`embeddinggemma:300m`** (Google EmbeddingGemma, 768 dims), selected by benchmarking on this corpus: every embedding model beat keyword retrieval, open-weight models matched or exceeded commercial services, and EmbeddingGemma had the best quality-to-size ratio. **Query vectors must come from the same model** — vectors from any other model are not comparable and will return garbage.

## Install (one time, ~5 minutes, ~620 MB download)

```bash
# macOS
brew install ollama          # or the installer at https://ollama.com/download
# Linux
curl -fsSL https://ollama.com/install.sh | sh
# Windows: installer at https://ollama.com/download

ollama pull embeddinggemma:300m
```

If the server isn't already running (macOS app runs it automatically): `ollama serve`

## Verify

```bash
curl -s http://localhost:11434/api/version        # → {"version":"..."}
curl -s http://localhost:11434/api/embed \
  -d '{"model":"embeddinggemma:300m","input":["task: search result | query: test"]}' \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)['embeddings'][0]))"   # → 768
```

## The prompt conventions (critical — results degrade badly without them)

EmbeddingGemma was trained with task prefixes. Use them exactly:

| Purpose | Format |
|---|---|
| **Search queries** (what you'll do) | `task: search result | query: {the question}` |
| Documents (already done in the databases) | `title: {title} | text: {abstract}` |

## Embedding a query

```python
# pip install requests
import requests
def embed_query(question: str) -> list[float]:
    r = requests.post("http://localhost:11434/api/embed", json={
        "model": "embeddinggemma:300m",
        "input": [f"task: search result | query: {question}"],
    })
    r.raise_for_status()
    return r.json()["embeddings"][0]      # 768 floats
```

Batching: pass multiple strings in `input` to embed many at once (throughput on a laptop is roughly 30–50 texts/second).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `connection refused` on port 11434 | Start the server: `ollama serve` (or launch the Ollama app) |
| `model not found` | `ollama pull embeddinggemma:300m` |
| Search results look random | Missing `task: search result | query: ` prefix, or a different model was used |
| Wrong vector length (not 768) | Wrong model — the databases require `embeddinggemma:300m` |

## No local install possible?

If the environment can't run Ollama (e.g., a purely hosted assistant), skip semantic search and use each database's **keyword search** (`search_papers_keyword` / `search_papers_bm25`) and SQL filters instead — no setup required. Hybrid search needs both a query string and a vector, so it also requires this skill.
