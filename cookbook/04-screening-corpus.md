# 04 · Build a Screening Corpus for a Review

**Goal:** assemble a high-recall candidate set for a systematic/scoping review — every record plausibly about the topic, exported with identifiers for screening. Recall matters more than precision here.

**Skills used:** `ollama-embeddings`, `swrd-database` (add SSWR the same way for gray-literature breadth).

## Strategy

Union three retrieval passes, then dedupe by id: (1) hybrid search with the research question, (2) hybrid search with 2–3 *rephrasings* (vocabulary variants recall different neighborhoods), (3) a keyword OR-sweep of established synonyms. Cast wide; screening removes false positives later.

## Step 1 — Multiple hybrid passes

```python
import requests
KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
     "Content-Profile": "swrd", "Content-Type": "application/json"}

phrasings = [
    "housing instability among youth aging out of foster care",
    "homelessness after leaving the child welfare system",
    "housing outcomes for transition-age foster youth",
]
candidates = {}
for ph in phrasings:
    emb = requests.post("http://localhost:11434/api/embed", json={
        "model": "embeddinggemma:300m",
        "input": [f"task: search result | query: {ph}"]}).json()["embeddings"][0]
    hits = requests.post(f"{BASE}/rpc/search_papers_hybrid", headers=H,
        json={"query_text": ph, "query_embedding": emb, "match_count": 60}).json()
    for h in hits:
        candidates.setdefault(h["id"], h)
```

## Step 2 — Keyword OR-sweep for synonyms the embeddings might rank low

```python
def run_sql(q): return requests.post(f"{BASE}/rpc/run_sql", headers=H, json={"query": q}).json()

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

## Step 3 — Attach screening metadata and export

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

## Step 4 — Document the retrieval for the methods section

Record: the phrasings used, the keyword query, `match_count` per pass, retrieval date, and the database citation (Perron, Victor, & Qi, 2026, doi:10.1177/10497315261416833). Note that records lacking abstracts (~28% of 1989+ records) are under-retrieved by the semantic arm — the keyword sweep partially compensates, and a journal/year census (`references/queries.md`) can bound what the search could not see.
