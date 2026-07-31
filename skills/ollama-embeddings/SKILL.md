---
name: ollama-embeddings
description: Check for, and if missing install, the local embedding model (Ollama + EmbeddingGemma 300M) that powers semantic search on the Social Work Meta-Data Project databases. Load this when a recipe or user asks for semantic (meaning-based) or hybrid search and the machine may not have the model yet. Not needed for SQL, keyword, or filter queries.
---

# Ollama + EmbeddingGemma: check, install, verify

Semantic search turns a question into a 768-dimension vector that is compared
against vectors stored in the SWRD and SSWR databases. The vectors must come
from the exact model the databases were embedded with, **`embeddinggemma:300m`**,
served locally by Ollama. This file is written so that an AI assistant can run
the whole setup: every step is a single command with its expected output and
an explicit next action. It is a prerequisite only for semantic and hybrid
search; SQL, keyword search, and filters need none of it.

Two rules for assistants before anything else:

1. **Ask the user before installing anything.** Step 2 installs a program and
   Step 3 downloads a ~620 MB model. Get a yes first.
2. **Never run `ollama serve` in the foreground.** It blocks the shell forever
   and your session will hang. Use the background form given in Step 2b.

## Step 1 — Check what is already there

Run the three checks in order. Each check's table names the next action; when
a check fails, fix only from that point rather than reinstalling from the top.
Most machines that have used these databases before need nothing installed.

```bash
# Check 1 — is the Ollama server responding?
curl -s --max-time 4 http://localhost:11434/api/version
```
| Result | Meaning | Next action |
|---|---|---|
| `{"version":"..."}` | server is up | go to Check 2 |
| empty / connection refused / timeout | server not running | run `command -v ollama`; if a path prints, go to Step 2b (start it); if nothing prints, go to Step 2a (install) |

```bash
# Check 2 — is the model pulled?  (use the API, not `ollama list`, so it
# works even when the CLI binary is not on PATH)
curl -s http://localhost:11434/api/tags | grep -o 'embeddinggemma[^"]*'
```
| Result | Next action |
|---|---|
| one or more lines containing `embeddinggemma:300m` | go to Check 3 |
| lines with other tags only (`:latest`, `:300m-bf16`, …) | go to Check 3 (Check 3 names the exact tag and will settle it) |
| nothing | go to Step 3 (pull the model) |

Duplicate lines are normal: the grep matches two JSON fields per installed
model, and machines often hold several embeddinggemma variants.

```bash
# Check 3 — does an embedding come back with the right shape?
curl -s http://localhost:11434/api/embed \
  -d '{"model":"embeddinggemma:300m","input":["task: search result | query: test"]}' \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)['embeddings'][0]))"
```
| Result | Next action |
|---|---|
| `768` | **nothing to install** — go to Step 4 to verify the database path end to end |
| any other number | wrong model responded; re-run Step 3 with the exact tag `embeddinggemma:300m` |
| `KeyError` / JSON error | model not loaded; go to Step 3 |

## Step 2a — Install Ollama (one time; ask the user first)

```bash
# macOS (Homebrew)
brew install ollama
# macOS without Homebrew, or Windows: the user installs the app from
#   https://ollama.com/download  (an assistant should hand this to the user)
# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

Expected: the installer prints a success line and `command -v ollama` now
prints a path. The Linux script and the macOS/Windows apps usually start the
server themselves; re-run Check 1 before doing anything else.

## Step 2b — Start the server (only if Check 1 still fails)

```bash
# macOS with Homebrew — survives reboots, nothing blocks:
brew services start ollama
# any platform, one-off background start (NEVER run `ollama serve` bare):
nohup ollama serve >/tmp/ollama.log 2>&1 &
```

Then poll until Check 1 passes (the server takes a few seconds):

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  curl -s --max-time 2 http://localhost:11434/api/version && break
  sleep 2
done
```

If it still fails after ~20 seconds, read `/tmp/ollama.log` and match the
error against Troubleshooting below.

## Step 3 — Pull the model (one time, ~620 MB; ask the user first)

```bash
ollama pull embeddinggemma:300m 2>&1 | tail -2
```

Expected final line: `success`. The download takes a few minutes on a typical
connection. The `tail -2` trims the progress output, though some Ollama
versions render progress with carriage returns, so one long line may still
come through; only the final `success` matters. If the
CLI is unavailable, the API form works too:
`curl -s http://localhost:11434/api/pull -d '{"model":"embeddinggemma:300m"}' | tail -c 200`

Then re-run Check 3. It must print `768`.

Why this exact model: the databases' 134,411 abstracts were embedded with
EmbeddingGemma 300M (768 dimensions), selected by benchmarking on this corpus.
Query vectors from any other model, provider, or build are not comparable and
return noise. There is no substitute tag.

## Step 4 — End-to-end verification against the live database

This confirms the whole path: local embedding, then a semantic query.

```bash
python3 - <<'EOF'
import json, urllib.request
def post(url, payload, headers={}):
    req = urllib.request.Request(url, json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers})
    return json.loads(urllib.request.urlopen(req).read())
vec = post("http://localhost:11434/api/embed",
    {"model": "embeddinggemma:300m",
     "input": ["task: search result | query: burnout among child welfare workers"]})["embeddings"][0]
assert len(vec) == 768, f"expected 768 dims, got {len(vec)}"
# Intentionally public read-only key, the same one the project publishes in llms.txt
KEY = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
hits = post("https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/search_papers_semantic",
    {"query_embedding": vec, "match_count": 3},
    {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Profile": "swrd"})
assert hits and hits[0]["similarity"] > 0.5, "semantic search returned no confident match"
print("OK:", round(hits[0]["similarity"], 3), hits[0]["title"][:70])
EOF
```

Expected: a line beginning `OK:` with similarity above 0.5 and a title about
burnout or child welfare workers. If this prints, everything works.

## Prompt conventions (results degrade badly without them)

EmbeddingGemma is trained with task prefixes. Use them exactly:

| Purpose | Format |
|---|---|
| Search queries (what you will do) | `task: search result \| query: {the question}` |
| Documents (already done in the databases) | `title: {title} \| text: {abstract}` |

Reusable query helper:

```python
import json, urllib.request
def embed_query(question):
    req = urllib.request.Request("http://localhost:11434/api/embed",
        json.dumps({"model": "embeddinggemma:300m",
                    "input": [f"task: search result | query: {question}"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req).read())["embeddings"][0]  # 768 floats
```

Batching: pass several strings in `input` at once (roughly 30–50 texts/second
on a laptop). Similarity is cosine, 0–1: about 0.55 and above is usually on
topic, 0.65 and above strongly so. The database's semantic function returns at
most ~40 rows per call regardless of the requested count; union several
differently worded queries for deeper coverage.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `connection refused` on port 11434 | Server not running: Step 2b |
| `model "embeddinggemma:300m" not found` | Model not pulled: Step 3 |
| Check 3 prints a number other than 768 | A different model answered; pull and name the exact tag `embeddinggemma:300m` |
| Search results look random | The `task: search result \| query: ` prefix was omitted, or a different model embedded the query |
| `ollama: command not found` after install | Open a new shell, or use the full path Homebrew printed; the API forms of Steps 1–3 work without the CLI |
| Step 2b log shows `address already in use` | A server is already running; re-run Check 1 |
| Shell hangs after starting the server | `ollama serve` was run in the foreground; kill it and use the `nohup … &` form |

## No local install possible?

Hosted environments that cannot run Ollama should skip semantic search and use
the databases' keyword search (`search_papers_keyword`) and SQL, which need no
setup; cookbook recipes 01–07 are built entirely on them. Hybrid search needs
a query vector, so it also requires this setup.
