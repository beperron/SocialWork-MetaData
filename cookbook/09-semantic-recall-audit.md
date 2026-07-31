# 09 · Semantic Recall Audit of a Keyword-Built Corpus

**Goal:** take a corpus built with keywords (recipe 04's screening corpus, recipe 05's verified corpus) and answer the reviewer's hardest question — *what did your keywords miss?* — with embeddings. Every recovered record comes with the vocabulary gap that explains the miss.

**Requires:** the one-time local embedding setup (~5 minutes, ~620 MB) — [`skills/ollama-embeddings/SKILL.md`](../skills/ollama-embeddings/SKILL.md) checks for it and installs it if missing. Connection reference: [`llms.txt`](../llms.txt). This is the embedding-powered upgrade of recipe 05's vocabulary-expansion audit; run whichever your setup allows — both are legitimate, this one sees further.

## Do this with Claude or Codex

Copy, edit the bracketed parts, and paste:

> I'm using the Social Work Meta-Data Project's hosted databases (public read-only key, plain HTTPS). Fetch https://beperron.github.io/SocialWork-MetaData/llms.txt and connect exactly as it describes. I have a keyword-built corpus of [TOPIC] items [attach it, reference it, or paste the keyword net so you can rebuild it]. This audit uses semantic search, which needs a small local embedding model: check whether Ollama is running with the embeddinggemma:300m model, and if anything is missing, fetch https://beperron.github.io/SocialWork-MetaData/skills/ollama-embeddings/SKILL.md and follow its check-install-verify steps — tell me before installing anything (one-time ~620 MB download). Then audit my corpus's recall: write 2-3 natural-language statements of what the corpus is about, embed each with the required query prefix, pull the ~200 nearest abstracts per statement with the semantic search, and read every record above about 0.50 similarity that is not already in my corpus. Report each recovered record with the vocabulary gap that explains why my keywords missed it, note where precision collapses so we know the audit's floor, and give me an updated corpus file that keeps original and recovered records distinguishable. Use the built-in search and SQL plus the local embedding model only; do not install anything else beyond common Python libraries (requests, pandas, matplotlib).

*If your assistant cannot fetch URLs, download [llms.txt](../llms.txt) and the [setup skill](../skills/ollama-embeddings/SKILL.md) and paste both into the chat together with the prompt.*

**What to check when it finishes.** Every recovered record must name its vocabulary gap — "found because the paper says X where my net said Y." Zero recoveries on a broad topic is suspicious (wrong prefix, wrong model, or statements too narrow); dozens of recoveries usually means the similarity floor was set too low and precision collapsed. The audit should also state what it *cannot* see: records without abstracts are invisible to the semantic arm.

## Under the hood — the steps the assistant runs

### Step 1 — Assemble the corpus ids being audited

From the attached file, or rebuilt from the stated keyword net:

```python
import requests
KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
def H(s): return {"apikey": KEY, "Authorization": f"Bearer {KEY}",
                  "Content-Profile": s, "Content-Type": "application/json"}
def run_sql(s, q):
    return requests.post(f"{BASE}/rpc/run_sql", headers=H(s), json={"query": q}).json()

corpus = run_sql("swrd", """
  select id from swrd.papers
  cross join websearch_to_tsquery('english',
    '"treatment dropout" or "premature termination" or "treatment attrition"') q
  where fts @@ q and publication_year >= 1989""")
corpus_ids = {r["id"] for r in corpus}          # example net → 31 records
```

### Step 2 — Embed 2–3 statements of the corpus definition

Different phrasings probe different semantic neighborhoods — that is the point:

```python
statements = [
    "clients dropping out of treatment before completion",
    "why people stop attending therapy or services early",
]
def embed(q):
    return requests.post("http://localhost:11434/api/embed", json={
        "model": "embeddinggemma:300m",
        "input": [f"task: search result | query: {q}"]}).json()["embeddings"][0]
```

### Step 3 — Pull neighbors, keep the high-similarity strangers

```python
recovered = {}
for st in statements:
    emb = embed(st)
    hits = requests.post(f"{BASE}/rpc/search_papers_semantic", headers=H("swrd"),
        json={"query_embedding": emb, "match_count": 200}).json()
    for h in hits:
        if h["id"] not in corpus_ids and h["similarity"] >= 0.50:
            recovered.setdefault(h["id"], h)
```

On the example corpus (31 keyword records) this surfaces 10 candidates — led by "Deciding to Leave Care Is Not Dropout" (0.60), "Client Costs and Early Discontinuance" (0.59), and "Attrition in Psychotherapy: A Survival Analysis" (0.59), each missed for a nameable reason: the paper's vocabulary (*discontinuance*, *leaving care*, *aftercare attendance*) never intersects the net's terms.

### Step 4 — Read everything recovered; name each gap

A similarity score nominates; reading decides. For each candidate read the abstract and either (a) admit it with a one-line vocabulary-gap note, or (b) reject it as a semantic near-neighbor that is genuinely out of scope (adjacent constructs like *service disengagement by providers* score high but may not belong). Track where in the similarity ranking the rejects start to dominate — that band is the audit's floor, and going below it trades reading time for noise.

### Step 5 — Report and update the corpus honestly

Deliver: (a) recovered records with similarity + gap notes; (b) the rejection log; (c) the audit floor; (d) an updated corpus file where recovered records carry a `source: "semantic_audit"` flag so the keyword core stays reconstructable; (e) the blind spot statement — abstract-less records (~28% of 1989+ SWRD) are invisible to this audit. If the recovered vocabulary suggests new keyword terms, say so: the best audit result is a better keyword net for the next run.
