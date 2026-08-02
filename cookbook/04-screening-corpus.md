# 04 · Build a Screening Corpus for a Review

**Goal:** assemble a high-recall candidate set for a systematic/scoping review — every record plausibly about the topic, exported with identifiers for screening. Recall matters more than precision here.

**Reference:** [`llms.txt`](../llms.txt) (connection + schema). Works on SWRD; add SSWR the same way for conference gray literature. Nothing to install.


## Do this with Claude or Codex

For systematic or scoping reviews. Tell the assistant your research question and insist on recall over precision; screening comes later, in your review tool.

Copy, edit the bracketed parts, and paste:

> I'm using the Social Work Meta-Data Project's hosted databases (public read-only key, plain HTTPS, nothing to install). Fetch https://beperron.github.io/SocialWork-MetaData/llms.txt and connect exactly as it describes (the endpoint is a POST API queried from a shell or code tool, not a page-fetch tool) — that one file has the endpoint, key, schema, and search functions. Build a high-recall screening corpus from the swrd database (add sswr too for conference gray literature) for a review of [RESEARCH QUESTION]. Distill my question into 4-6 short keyword phrases of 2-4 content words each, covering different vocabulary (the search AND-matches terms, so full sentences return nothing); run the built-in keyword search with each phrase, plus a full-text SQL OR-sweep of the established synonyms; union everything, dedupe by ID, and export a CSV with title, year, journal, DOI, and abstract. Do not filter aggressively: recall matters more than precision here. Use the built-in search and SQL only; do not install anything beyond common Python libraries (requests, pandas, matplotlib).

*If your assistant cannot fetch URLs, download [llms.txt](../llms.txt) and paste its contents into the chat together with the prompt.*

> **Strongly recommended for reviews: add the semantic arm.** Everything above matches exact words, so the corpus can only contain papers that use vocabulary you (or your rephrasings) anticipated — a real recall risk for a systematic review. With the one-time embedding setup ([`ollama-embeddings`](../skills/ollama-embeddings/SKILL.md), ~5 minutes), add semantic retrieval passes ([recipe 08](08-semantic-search-beyond-keywords.md)) to the union, or at minimum run [recipe 09](09-semantic-recall-audit.md) afterward to audit what the keywords missed and document it in your methods section.

**What to check when it finishes.** Ask how many records each pass contributed and how many were unique to the rephrasings; if the rephrasings added nothing, they were too similar. Spot-check 10 random rows of the CSV against the databases.

## Under the hood — the steps the assistant runs

### Strategy

Union two retrieval families, then dedupe by id: (1) ranked keyword search with several *short phrases* distilled from the research question — different vocabulary recalls different neighborhoods; (2) a full-text OR-sweep of established synonyms. Cast wide; screening removes false positives later.

The one mechanical rule that matters: **the search AND-matches terms, so phrases must be short** (2–4 content words). The full question "housing instability among youth aging out of foster care" returns zero rows; "foster youth housing" returns dozens.

### Step 1 — Multiple ranked-search passes with short phrases

```python
import requests
KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
     "Content-Profile": "swrd", "Content-Type": "application/json"}
def run_sql(q): return requests.post(f"{BASE}/rpc/run_sql", headers=H, json={"query": q}).json()

# the research question, distilled into short phrases with varied vocabulary
phrasings = [
    "foster youth housing",
    "aging out foster care housing",
    "foster care homelessness",
    "transition age youth homeless",
]
candidates = {}
for ph in phrasings:
    hits = run_sql(f"select id, title, abstract, publication_year "
                   f"from swrd.search_papers_keyword('{ph}', 60)")
    for h in hits:
        candidates.setdefault(h["id"], h)
```

### Step 2 — OR-sweep for synonyms the ranked search might rank low

```python
kw = run_sql("""
  select id, title, abstract, publication_year from swrd.papers
  cross join websearch_to_tsquery('english',
    '(\"aging out\" or \"emancipated foster\" or \"former foster youth\") housing or homeless') q
  where (to_tsvector('english', title) @@ q
         or (abstract is not null and to_tsvector('english', abstract) @@ q))
    and publication_year >= 1989
  limit 1000""")
for r in kw:
    candidates.setdefault(r["id"], r)
print(len(candidates), "unique candidates")
```

### Step 3 — Attach screening metadata and export

```python
ids = ",".join(str(i) for i in candidates)
rows = run_sql(f"""
  select p.id, p.title, p.abstract, p.publication_year, j.name as journal,
         p.doi, p.is_empirical, p.research_method
  from swrd.papers p left join swrd.journals j on j.id = p.journal_id
  where p.id in ({ids}) order by p.publication_year""")

import csv
with open("screening_corpus.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
```

(If the id list exceeds ~1,000, chunk it across multiple `run_sql` calls.)

### Step 4 — Document the retrieval for the methods section

Record: the phrasings used, the keyword query, `match_count` per pass, retrieval date, and the database citation (Perron, Victor, & Qi, 2026, doi:10.1177/10497315261416833). Note that records lacking abstracts (~28% of 1989+ records) can match only on their titles — include terms likely to appear in titles when phrasing the sweeps, and a journal/year census (`references/queries.md`) can bound what the search could not see.
