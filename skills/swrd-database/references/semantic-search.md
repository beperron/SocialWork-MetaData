# SWRD — Semantic & Hybrid Search Recipes

Prerequisite: a local query-embedding endpoint (see the `ollama-embeddings` skill). Queries MUST be embedded as `task: search result | query: {question}` with `embeddinggemma:300m`.

Both databases expose the **identical search API**: `search_papers_semantic`, `search_papers_keyword`, `search_papers_hybrid` — same names, parameters, and semantics.

## Which search to use

| Situation | Function |
|---|---|
| Concept search; wording may vary (default for topic questions) | `search_papers_hybrid` — best overall: fuses meaning + exact terms |
| Pure meaning, vocabulary-independent | `search_papers_semantic` |
| Exact terms/phrases; or no Ollama available | `search_papers_keyword` (no embedding needed) |

## Hybrid search (recommended default)

Reciprocal Rank Fusion of the top-60 semantic and top-60 keyword results: `score = Σ 1/(rrf_k + rank)`. Returns `semantic_rank` and `keyword_rank` so you can see *why* each paper surfaced (NULL rank = not in that top-60 list).

```python
# pip install requests
import requests
KEY = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
     "Content-Profile": "swrd", "Content-Type": "application/json"}

question = "burnout and turnover among child welfare workers"
emb = requests.post("http://localhost:11434/api/embed", json={
    "model": "embeddinggemma:300m",
    "input": [f"task: search result | query: {question}"]}).json()["embeddings"][0]

hits = requests.post(f"{BASE}/rpc/search_papers_hybrid", headers=H, json={
    "query_text": question,          # feeds the keyword arm
    "query_embedding": emb,          # feeds the semantic arm
    "match_count": 15,
    # optional: "rrf_k": 60, "min_year": 1989, "max_year": 2026
}).json()
for h in hits:
    print(round(h["rrf_score"], 4), h["semantic_rank"], h["keyword_rank"],
          h["publication_year"], h["title"])
```

Keyword-arm tip: `query_text` goes through `websearch_to_tsquery`, which ANDs terms — long natural-language questions can match few keyword results (hybrid then gracefully leans semantic). For a stronger keyword arm, pass the 2–4 core terms as `query_text` while embedding the full question.

## Semantic-only

```python
hits = requests.post(f"{BASE}/rpc/search_papers_semantic", headers=H,
    json={"query_embedding": emb, "match_count": 10}).json()
# fields: id, title, abstract, publication_year, journal_name, times_cited, similarity
```

Interpretation: cosine `similarity` 0–1; on this corpus ≥ ~0.55 usually on-topic, ≥ ~0.65 strongly so.

## Keyword-only (no setup required)

```python
hits = requests.post(f"{BASE}/rpc/search_papers_keyword", headers=H,
    json={"query_text": "kinship care", "match_count": 10}).json()
# ranked full-text over title+abstract (websearch syntax: quotes for phrases, OR, -exclusions)
```

## Combining with SQL

All three return the paper `id`. Feed ids into `run_sql` for follow-up analysis:

```sql
select research_method, count(*) from swrd.papers
where id in (101, 202, 303) group by 1
```

## SQL-side equivalents (for use inside run_sql)

The same functions are callable in SQL — useful to join search results with anything else in one query:

```sql
select h.title, h.rrf_score, p.doi
from swrd.search_papers_hybrid('kinship care', '[...768 floats...]'::extensions.vector, 20) h
join swrd.papers p on p.id = h.id
where p.times_cited > 10
```
