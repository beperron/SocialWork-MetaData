---
name: sswr-database
description: Query the SSWR Conference Database — 23,793 presentations from every Society for Social Work and Research annual conference (2005–2026), with disambiguated authors, method labels, full abstracts, and semantic search. Use when the user asks about social work conference research, scholar trajectories, institutional activity, or wants to find presentations on a topic.
---

# SSWR Conference Database: Agent Skill (Quickstart)

> This is the self-contained quickstart. A fuller skill with the complete data catalog, tested SQL recipes, and search guides lives in [`sswr-database/`](sswr-database/SKILL.md). End-to-end examples: [`../cookbook/`](../cookbook/).

You (the agent) can query a hosted database of SSWR conference-presentation records. Everything works over plain HTTPS with the public key below — **no password, no account, no database driver**. All access is read-only. Semantic search additionally uses a small local embedding model (§5).

## 1. What this database is

Records for **all 23,793 presentations (papers, posters, symposia) at the Society for Social Work and Research annual conference, 2005–2026**, compiled from official conference programs. Every record has a full abstract and a research-method label.

Its distinguishing feature: **authors are disambiguated**. The 21,209 presenting researchers have canonical identities with name variants resolved across all years — author-level and longitudinal analyses are reliable here (unlike the companion SWRD journal database). Disambiguation is thorough but not perfect: when a scholar matters to the analysis, run `search_authors_by_name` first and check for residual near-duplicate entries.

Citation to report when the user publishes with these data: *Perron, B. E., Victor, B. G., & Qi, Z. (2026). AI-assisted curation of conference scholarship. arXiv. https://doi.org/10.48550/arXiv.2603.06814 (in press, Journal of the Society for Social Work and Research)*

## 2. Connection details

| What | Value |
|---|---|
| Base URL | `https://kcffctxedcscvvposypb.supabase.co/rest/v1` |
| API key (public, read-only) | `sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5` |
| Required headers | `apikey: <KEY>` and `Authorization: Bearer <KEY>` on every request, plus `Accept-Profile: sswr` on GET or `Content-Profile: sswr` on POST |

The key is intentionally public and grants read-only access. Writes are rejected at the database level.

## 3. Schema reference

| Table | Rows | Key columns |
|---|---|---|
| `sswr.papers` | 23,793 | `id` (text PK, e.g. `2019-O-0142`), `title`, `abstract`, `year`, `format` (oral/poster/symposium…), `methodology` (values: `quantitative`, `qualitative`, `mixed_methods`, `review`, `other`), `author_count` |
| `sswr.authors` | 21,209 | `id` (int PK), `name` (canonical), `variants` (jsonb), `institutions` (jsonb), `years` (jsonb), `total_papers` |
| `sswr.paper_authors` | 69,924 | `paper_id`, `author_id` → canonical author, `name` (as printed), `author_order` (1 = first), `institution`, `institution_normalized`, `position_normalized`, `country_normalized` |
| `sswr.institution_mappings` | 4,335 | raw → canonical institution names |
| `sswr.paper_embeddings` | 23,793 | `paper_id`, `embedding` (768-dim vector), `model` |

Convenience views: `sswr.paper_export` (flat, one row per paper with author arrays — easiest for exports), `sswr.database_info` (citation + counts).

**Search API** (identical on both databases):
- `sswr.search_papers_semantic(query_embedding, match_count, min_year, max_year)`
- `sswr.search_papers_keyword(query_text, match_count, min_year, max_year)` — ranked full-text
- `sswr.search_papers_hybrid(query_text, query_embedding, match_count, rrf_k, min_year, max_year)` — reciprocal-rank fusion, **recommended default for topic questions**

Helper functions:
- `sswr.search_authors_by_name(query_text, match_count)` — fuzzy author lookup (start scholar analyses here)
- `sswr.search_papers_by_institution(query_text, match_count, min_year, max_year)`
- `sswr.autocomplete_institutions(prefix, limit_count)`
- `sswr.match_papers`, `sswr.search_papers_bm25` — legacy aliases; prefer the aligned API above

## 4. SQL queries (over HTTPS — no database client needed)

POST any read-only SQL to the `run_sql` endpoint. Results return as JSON. Limits: SELECT-only privileges, 30-second timeout, **1,000 rows max per call** (paginate with `offset`/`limit` or aggregate server-side).

```bash
KEY="sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
curl -s "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/run_sql" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Content-Profile: sswr" -H "Content-Type: application/json" \
  -d '{"query": "select methodology, count(*) as n from sswr.papers group by 1 order by 2 desc"}'
```

```python
# pip install requests
import requests

KEY = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
def run_sql(query: str):
    r = requests.post(
        "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/run_sql",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Profile": "sswr", "Content-Type": "application/json"},
        json={"query": query},
    )
    r.raise_for_status()
    return r.json()          # list of row dicts

rows = run_sql("select year, count(*) as n from sswr.papers group by 1 order by 1")
```

Example queries the user commonly wants:

```sql
-- Finding a scholar: ALWAYS start with fuzzy lookup (canonical names are stored
-- as "First Last", sometimes with credentials, e.g. "Brian Perron, PhD")
select author_id, author_name, total_papers from sswr.search_authors_by_name('michael vaughn', 5)

-- Then pull their full presentation history by the returned author_id
select p.year, p.title, pa.author_order
from sswr.paper_authors pa
join sswr.papers p on p.id = pa.paper_id
where pa.author_id = 108089    -- id from the lookup above
order by p.year

-- Ranked full-text topic search
select id, title, year, rank from sswr.search_papers_keyword('kinship care', 10)

-- Most active institutions in a period (first authors)
select institution_normalized, count(*)
from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id
where pa.author_order = 1 and p.year between 2020 and 2026
group by 1 order by 2 desc limit 10
```

Tips: single SELECT statements only (no semicolons, no writes — both are rejected). Use `limit` and year filters for heavy joins.

## SQL rules that prevent the most common errors

1. **Stay inside one database's schema.** For SSWR questions use ONLY `sswr.*` tables; never join `swrd.*` tables (the id types are incompatible: SSWR ids are text like `2019-O-0142`, SWRD ids are integers).
2. **Where the year lives:** `sswr.papers.year`. `sswr.paper_authors` has NO year column — join `sswr.papers` when filtering by year.
3. **Calling functions:** always `select <columns> from sswr.search_papers_keyword(...)` — a bare function call without SELECT…FROM is a syntax error.
4. **Search results arrive pre-sorted, best match first.** The `rank` column is a relevance *score* (a float), not a position — never `where rank = 1` and never re-sort ascending; take the top row(s) with the function's match_count or LIMIT.
5. **Qualify every column with a table alias in any join** (`p.id`, `pa.paper_id`) — unqualified ids are ambiguous.
6. **Answer the quantity asked** — if the question says "how many", return a count, not a list of rows.

## 5. Semantic search (find presentations by meaning)

Semantic search needs a query "fingerprint" from the same model the abstracts were embedded with: **EmbeddingGemma 300M via Ollama, 768 dimensions**. This runs locally.

### One-time setup

```bash
# macOS:  brew install ollama   (or download from https://ollama.com/download)
# Linux:  curl -fsSL https://ollama.com/install.sh | sh
# Windows: installer at https://ollama.com/download
ollama pull embeddinggemma:300m       # ~620 MB, one time
curl -s http://localhost:11434/api/version   # verify the server is running
```

### The prompt convention (required — results degrade without it)

- Search queries MUST be embedded as: `task: search result | query: {user's question}`
- (Documents were embedded as `title: {title} | text: {abstract}` — already done; you never need to.)

### Recipe

```python
# pip install requests
import requests

KEY = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
question = "interventions for children in kinship foster care"

emb = requests.post("http://localhost:11434/api/embed", json={
    "model": "embeddinggemma:300m",
    "input": [f"task: search result | query: {question}"],
}).json()["embeddings"][0]                      # 768 floats

hits = requests.post(
    "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/search_papers_semantic",
    headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
             "Content-Profile": "sswr", "Content-Type": "application/json"},
    json={"query_embedding": emb, "match_count": 10},
).json()
for h in hits:
    print(round(h["similarity"], 3), h["year"], h["title"])
```

### Hybrid search (recommended default for topic questions)

Fuses semantic and keyword rankings (reciprocal-rank fusion). Pass the plain question and its embedding:

```python
hits = requests.post(
    "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/search_papers_hybrid",
    headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
             "Content-Profile": "sswr", "Content-Type": "application/json"},
    json={"query_text": question, "query_embedding": emb, "match_count": 15},
).json()
# extra fields: rrf_score, semantic_rank, keyword_rank (NULL = not in that arm's top 60)
```

Same thing with curl:

```bash
QVEC=$(curl -s http://localhost:11434/api/embed \
  -d '{"model":"embeddinggemma:300m","input":["task: search result | query: interventions for children in kinship foster care"]}' \
  | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['embeddings'][0]))")

curl -s "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/search_papers_semantic" \
  -H "apikey: sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5" \
  -H "Authorization: Bearer sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5" \
  -H "Content-Profile: sswr" -H "Content-Type: application/json" \
  -d "{\"query_embedding\": $QVEC, \"match_count\": 10}"
```

Interpretation: `similarity` runs 0–1 (cosine); ≥ ~0.55 usually on-topic. All search functions return the full author list as JSON. No Ollama available? `rpc/search_papers_keyword` needs no embedding and no setup.

## 6. REST queries (no SQL client required)

```bash
BASE="https://kcffctxedcscvvposypb.supabase.co/rest/v1"
KEY="sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
H1="apikey: $KEY"; H2="Authorization: Bearer $KEY"; H3="Accept-Profile: sswr"

# Posters about opioids since 2015
curl -s "$BASE/papers?select=id,title,year&abstract=ilike.*opioid*&year=gte.2015&limit=5" -H "$H1" -H "$H2" -H "$H3"

# Flat export view (papers with author arrays)
curl -s "$BASE/paper_export?select=id,title,year,canonical_authors&year=eq.2024&limit=3" -H "$H1" -H "$H2" -H "$H3"

# Full-text search via RPC
curl -s "$BASE/rpc/search_papers_bm25" -H "$H1" -H "$H2" -H "Content-Profile: sswr" -H "Content-Type: application/json" \
  -d '{"query_text":"homelessness", "match_count":5}'
```

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `Could not find the table 'public.papers'` | You forgot the `Accept-Profile: sswr` (GET) or `Content-Profile: sswr` (POST) header |
| `run_sql`: `relation "papers" does not exist` | Qualify with the schema: `sswr.papers` |
| `run_sql`: `syntax error` on a valid statement | Remove trailing semicolons; only a single SELECT is accepted |
| `run_sql`: `permission denied` | You attempted a write — access is read-only |
| Exactly 1,000 rows returned | You hit the per-call cap; paginate with `offset`/`limit` or aggregate |
| Semantic results look random | You embedded the query without the `task: search result | query: ` prefix, or used a different model than `embeddinggemma:300m` |
| Ollama connection refused | Start it: `ollama serve` (or launch the Ollama app), then retry |
| Query cancelled after 30s | Narrow the query (year filter, limit) |
