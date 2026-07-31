---
name: ollama-embeddings
description: Check for, and if missing install, the local embedding model (Ollama + EmbeddingGemma 300M) that powers semantic search on the Social Work Meta-Data Project databases. Load this when a recipe or user asks for semantic (meaning-based) or hybrid search and the machine may not have the model yet. Not needed for SQL, keyword, or filter queries.
---

# Ollama + EmbeddingGemma — Check, Install, Verify

Semantic search turns a question into a 768-dimension meaning vector that is
compared against vectors stored in the SWRD and SSWR databases. The vectors
must come from the exact model the databases were embedded with —
**`embeddinggemma:300m`** — running locally via Ollama. This skill gets that
working. It is a prerequisite **only** for semantic and hybrid search; SQL,
keyword search, and filters need none of it.

## Step 0 — Check what is already there (do this first, in order)

Most machines that have used these databases before need nothing installed.
Run the three checks; stop at the first one that fails and fix only from there.

```bash
# Check 1 — is the Ollama server running?
curl -s --max-time 3 http://localhost:11434/api/version
#   → {"version":"..."}          server is up: go to Check 2
#   → connection refused/timeout: is the binary installed?  `which ollama`
#       installed but not running → `ollama serve` (or open the Ollama app), recheck
#       not installed            → Step 1

# Check 2 — is the model pulled?
ollama list | grep embeddinggemma
#   → embeddinggemma:300m ...    model present: go to Check 3
#   → (nothing)                  → Step 2

# Check 3 — does an embedding come back with the right shape?
curl -s http://localhost:11434/api/embed \
  -d '{"model":"embeddinggemma:300m","input":["task: search result | query: test"]}' \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)['embeddings'][0]))"
#   → 768                        everything works: skip to "Prompt conventions"
```

If all three checks pass, there is nothing to install — do not reinstall.

## Step 1 — Install Ollama (one time)

**If you are an AI assistant: tell the user before installing** — this is a
local install plus a ~620 MB model download, and they may prefer to run it
themselves.

```bash
# macOS
brew install ollama            # or the installer at https://ollama.com/download
# Linux
curl -fsSL https://ollama.com/install.sh | sh
# Windows
# installer at https://ollama.com/download
```

Start the server if it doesn't start itself (the macOS/Windows apps do):

```bash
ollama serve
```

## Step 2 — Pull the model (one time, ~620 MB)

```bash
ollama pull embeddinggemma:300m
```

Why this exact model: the databases' 134,411 abstracts were embedded with
EmbeddingGemma 300M (768 dims), selected by benchmarking on this corpus —
every embedding model beat keyword retrieval, open-weight models matched or
exceeded commercial services, and EmbeddingGemma had the best
quality-to-size ratio. **Vectors from any other model are not comparable and
will return garbage.**

## Step 3 — Verify end to end

Re-run Check 3 above; it must print `768`. Then confirm against the live
database with one semantic call (see the database skill files or
`llms.txt` for connection details) — the top results for a test query like
*burnout among child welfare workers* should be plainly on-topic.

## Prompt conventions (critical — results degrade badly without them)

EmbeddingGemma was trained with task prefixes. Use them exactly:

| Purpose | Format |
|---|---|
| **Search queries** (what you'll do) | `task: search result \| query: {the question}` |
| Documents (already done in the databases) | `title: {title} \| text: {abstract}` |

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

Batching: pass multiple strings in `input` to embed many at once (throughput
on a laptop is roughly 30–50 texts/second).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `connection refused` on port 11434 | Start the server: `ollama serve` (or launch the Ollama app) |
| `model not found` | `ollama pull embeddinggemma:300m` |
| Search results look random | Missing `task: search result \| query: ` prefix, or a different model was used |
| Wrong vector length (not 768) | Wrong model — the databases require `embeddinggemma:300m` |
| `brew: command not found` (macOS) | Use the installer at https://ollama.com/download instead |

## No local install possible?

If the environment can't run Ollama (e.g., a purely hosted assistant), skip
semantic search and use each database's **keyword search**
(`search_papers_keyword`) and SQL filters instead — no setup required, and
cookbook recipes 01–07 are built entirely on them. Hybrid search needs both
a query string and a vector, so it also requires this skill.
