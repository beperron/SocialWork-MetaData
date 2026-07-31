# 08 · Semantic Search: Find What Keywords Can't Name

**Goal:** map a topic by *meaning*, surfacing the papers that discuss it in vocabulary you didn't think to search — then show exactly what the semantic arm added over keywords, with evidence.

**Requires:** the one-time local embedding setup (~5 minutes, ~620 MB) — [`skills/ollama-embeddings/SKILL.md`](../skills/ollama-embeddings/SKILL.md) checks for it and installs it if missing. Connection reference: [`llms.txt`](../llms.txt). Example topic: *clients dropping out of treatment* — a topic the literature names five different ways (dropout, attrition, discontinuance, disengagement, premature termination).

## Do this with Claude or Codex

Copy, edit the bracketed parts, and paste:

> I'm using the Social Work Meta-Data Project's hosted databases (public read-only key, plain HTTPS). Fetch https://beperron.github.io/SocialWork-MetaData/llms.txt and connect exactly as it describes. This analysis uses semantic (meaning-based) search, which needs a small local embedding model: check whether Ollama is running with the embeddinggemma:300m model, and if anything is missing, fetch https://beperron.github.io/SocialWork-MetaData/skills/ollama-embeddings/SKILL.md and follow its check-install-verify steps — tell me before installing anything (it is a one-time ~620 MB download). Then map the literature on [YOUR TOPIC] by meaning across both databases (swrd journals and sswr conference): embed my topic with the required query prefix, run the semantic search and the keyword search side by side, and show me specifically which relevant items the semantic arm found that keyword search missed, with their similarity scores and the vocabulary they use instead of mine. Verify every semantic-only find by reading its abstract before calling it relevant, and use hybrid search for your final top-10 ranking. Use the built-in search and SQL plus the local embedding model only; do not install anything else beyond common Python libraries (requests, pandas, matplotlib).

*If your assistant cannot fetch URLs, download [llms.txt](../llms.txt) and the [setup skill](../skills/ollama-embeddings/SKILL.md) and paste both into the chat together with the prompt.*

**What to check when it finishes.** The deliverable that matters is the *semantic-only finds table*: each row should name the vocabulary the paper used instead of yours (that's the evidence semantic search earned its setup cost). If every semantic find was also a keyword find, the topic's vocabulary is uniform and keyword search alone (recipes 01/04) is enough — a legitimate finding worth stating.

## Under the hood — the steps the assistant runs

### Step 1 — Verify the embedding endpoint, then embed the topic once

The [setup skill](../skills/ollama-embeddings/SKILL.md) covers check/install/verify. Then:

```python
import requests
KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
def H(schema): return {"apikey": KEY, "Authorization": f"Bearer {KEY}",
                       "Content-Profile": schema, "Content-Type": "application/json"}

topic = "clients dropping out of treatment before completion"
emb = requests.post("http://localhost:11434/api/embed", json={
    "model": "embeddinggemma:300m",
    "input": [f"task: search result | query: {topic}"]}).json()["embeddings"][0]
```

The `task: search result | query: ` prefix is required — results degrade badly without it.

### Step 2 — Semantic and keyword, side by side

```python
sem = requests.post(f"{BASE}/rpc/search_papers_semantic", headers=H("swrd"),
    json={"query_embedding": emb, "match_count": 15}).json()
kw  = requests.post(f"{BASE}/rpc/search_papers_keyword", headers=H("swrd"),
    json={"query_text": "treatment dropout", "match_count": 15}).json()

kw_ids = {h["id"] for h in kw}
semantic_only = [h for h in sem if h["id"] not in kw_ids]
```

On the example topic this yields 10 semantic-only finds out of 15 — papers phrased as *attrition* ("Attrition in Psychotherapy: A Survival Analysis"), *discontinuance* ("Client Costs and Early Discontinuance from a Community-Based Treatment Program"), *termination* ("Revisiting unplanned termination"), none of which contain the word "dropout" prominently. Run the same pair on `sswr` (identical API; year column is `year`).

### Step 3 — Read before claiming

`similarity` is cosine, 0–1: ≥ ~0.55 is usually on-topic, ≥ ~0.65 strongly so. But a score is a hypothesis — read each semantic-only abstract and report the vocabulary it used instead of yours. That per-row vocabulary note is what makes the finding auditable.

### Step 4 — Hybrid for the final ranking

```python
hyb = requests.post(f"{BASE}/rpc/search_papers_hybrid", headers=H("swrd"),
    json={"query_text": topic, "query_embedding": emb, "match_count": 15}).json()
# extra fields: rrf_score, semantic_rank, keyword_rank (NULL = not in that arm's top 60)
```

Hybrid fuses both rankings (reciprocal-rank fusion), so items strong in *either* meaning or exact terms surface, and items strong in both rise to the top. Present the top 10 with each item's `semantic_rank`/`keyword_rank` so the reader sees which arm found it.

### Step 5 — Report

Present: (a) the side-by-side counts; (b) the semantic-only finds table with similarity and the substitute vocabulary; (c) the hybrid top 10 per database; (d) the standing caveats (pre-1989 lower bounds; 2024–25 indexing lag). If semantic added nothing, say so — that is a real result about the topic's vocabulary, not a failure.
