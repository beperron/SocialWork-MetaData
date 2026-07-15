---
name: swrd-database
description: Query the Social Work Research Database (SWRD) — 110,618 journal-article records from 88 social work journals (1920–2025) with study-type classifications and semantic search. Use when the user asks about social work journal literature, publication trends, methodology patterns, or wants to find studies on a topic.
---

# SWRD — Social Work Research Database: Agent Skill (Quickstart)

> This is the self-contained quickstart. A fuller skill with the complete data catalog, tested SQL recipes, and search guides lives in [`swrd-database/`](swrd-database/SKILL.md). End-to-end examples: [`../cookbook/`](../cookbook/).

You (the agent) can query a hosted database of social work journal-article records. Everything works over plain HTTPS with the public key below — **no password, no account, no database driver**. All access is read-only. Semantic search additionally uses a small local embedding model (§5).

## 1. What this database is

The SWRD contains records (title, abstract, authors, affiliations, journal, year, DOI) for articles in **88 disciplinary social work journals** (the `swrd.journals` table carries 91 rows: two contain no articles and one journal appears under two ids):

- **The SWRD proper:** 87,329 records, **1989–2025**, systematically compiled and validated. Within it, **62,602 research articles with abstracts**, each classified: `is_scientific` (research vs editorial/review/letter), `is_empirical`, and `research_method` (values: `Quantitative`, `Qualitative`, `Mixed-Methods`, `Review` — note the exact capitalization).
- **The SWRD Supplement:** 23,289 records, **1920–1988**, substantially incomplete (missing abstracts/details). Treat pre-1989 counts as lower bounds. **Default analyses to `publication_year >= 1989` unless the user asks for historical data.**

Citation to report when the user publishes with these data: *Perron, B. E., Victor, B. G., & Qi, Z. (2026). Evolution of social work knowledge production over 35 years. Research on Social Work Practice. https://doi.org/10.1177/10497315261416833*

**Critical caveat for author-level analysis:** author names are stored **exactly as published — no disambiguation**. "J. Garcia" and "Jennifer Garcia" may be the same person under two entries. Do not report unique-author counts as fact; caveat them.

## 2. Connection details

| What | Value |
|---|---|
| Base URL | `https://kcffctxedcscvvposypb.supabase.co/rest/v1` |
| API key (public, read-only) | `sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5` |
| Required headers | `apikey: <KEY>` and `Authorization: Bearer <KEY>` on every request, plus `Accept-Profile: swrd` on GET or `Content-Profile: swrd` on POST |

The key is intentionally public and grants read-only access. Writes are rejected at the database level.

## 3. Schema reference

| Table | Rows | Key columns |
|---|---|---|
| `swrd.papers` | 110,618 | `id` (int PK), `title`, `abstract`, `publication_year`, `journal_id` → journals, `doi`, `document_type`, `data_source`, `open_access`, `volume`, `issue`, `pages`, `is_scientific` (bool), `is_empirical` (bool), `research_method` (text: `Quantitative`/`Qualitative`/`Mixed-Methods`/`Review`) |
| `swrd.journals` | 91 | `id`, `name`, `publisher` |
| `swrd.authors` | 164,549 | `id`, `name` (as published), `orcid`, `wos_author_id`, `scopus_author_id` |
| `swrd.paper_authors` | 241,766 | `paper_id`, `author_id`, `position` (1 = first author), `is_corresponding` |
| `swrd.organizations` | 34,967 | `id`, `name` |
| `swrd.author_affiliations` | 113,646 | `author_id`, `organization_id`, `paper_id` |
| `swrd.title_abstract_embeddings` | 110,618 | `paper_id`, `embedding` (768-dim vector), `model` |

**Search API** (identical on both databases): `search_papers_semantic(query_embedding, match_count, min_year, max_year)` · `search_papers_keyword(query_text, match_count, min_year, max_year)` — ranked full-text · `search_papers_hybrid(query_text, query_embedding, match_count, rrf_k, min_year, max_year)` — reciprocal-rank fusion of both, **the recommended default for topic questions**.

Convenience views: `swrd.swrd_papers` (1989–2025 only), `swrd.swrd_supplement_papers` (pre-1989), `swrd.papers_with_journals` (papers joined to journal names), `swrd.publication_trends` (per-year aggregates), `swrd.author_publication_stats`, `swrd.organization_collaborations`, `swrd.database_summary`, `swrd.database_info` (citation + counts).

## 4. SQL queries (over HTTPS — no database client needed)

POST any read-only SQL to the `run_sql` endpoint. Results return as JSON. Limits: SELECT-only privileges, 30-second timeout, **1,000 rows max per call** (paginate with `offset`/`limit` or aggregate server-side).

```bash
KEY="sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
curl -s "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/run_sql" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Content-Profile: swrd" -H "Content-Type: application/json" \
  -d '{"query": "select research_method, count(*) as n from swrd.papers where is_empirical group by 1 order by 2 desc"}'
```

```python
# pip install requests
import requests

KEY = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
def run_sql(query: str):
    r = requests.post(
        "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/run_sql",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Profile": "swrd", "Content-Type": "application/json"},
        json={"query": query},
    )
    r.raise_for_status()
    return r.json()          # list of row dicts

rows = run_sql("select publication_year, count(*) as n from swrd.papers where publication_year >= 1989 and is_scientific group by 1 order by 1")
```

Example queries the user commonly wants:

```sql
-- Topic count by keyword (title/abstract), core years only
select count(*) as n from swrd.papers
where publication_year >= 1989
  and (title ilike '%kinship care%' or abstract ilike '%kinship care%')

-- Methodology trend by decade
select (publication_year/10)*10 as decade, research_method, count(*) as n
from swrd.papers where is_empirical group by 1,2 order by 1,2

-- Recent articles in one journal
select p.title, p.publication_year
from swrd.papers p join swrd.journals j on j.id = p.journal_id
where j.name = 'Social Service Review'
order by p.publication_year desc limit 10

-- Full author list for a paper (names as published!)
select a.name, pa.position, pa.is_corresponding
from swrd.paper_authors pa join swrd.authors a on a.id = pa.author_id
where pa.paper_id = 12345 order by pa.position   -- replace 12345 with a real paper id
```

Tips: single SELECT statements only (no semicolons, no writes — both are rejected). Stay fast with year filters, `limit`, and the indexed columns (`journal_id`, `publication_year`, `doi`, `is_scientific`, `research_method`).

## SQL rules that prevent the most common errors

1. **Stay inside one database's schema.** For SWRD questions use ONLY `swrd.*` tables; never join `sswr.*` tables (the id types are incompatible: SWRD ids are integers, SSWR ids are text like `2019-O-0142`).
2. **Where the year lives:** `swrd.papers.publication_year`. `swrd.paper_authors` has NO year column — join `swrd.papers` when filtering by year.
3. **Calling functions:** always `select <columns> from swrd.search_papers_keyword(...)` — a bare function call without SELECT…FROM is a syntax error.
4. **Search results arrive pre-sorted, best match first.** The `rank` column is a relevance *score* (a float), not a position — never `where rank = 1` and never re-sort ascending; take the top row(s) with the function's match_count or LIMIT.
5. **Qualify every column with a table alias in any join** (`p.id`, `pa.paper_id`) — unqualified ids are ambiguous.
6. **Corpus filters are conditional.** Apply `publication_year >= 1989 and is_scientific and abstract is not null` when the question concerns the research corpus; when a question says "in total", "all years", or asks for raw record counts, do NOT add these filters.
7. **Answer the quantity asked** — if the question says "how many", return a count, not a list of rows.
8. **Search functions already return the columns you usually need — use them directly, don't re-join.** Every SWRD search function (`search_papers_keyword`, `search_papers_semantic`, `search_papers_hybrid`) returns exactly: `id, title, abstract, publication_year, journal_name` plus its score column(s). There is NO `journal_id` or `paper_id` in the output — `select journal_name from swrd.search_papers_keyword('…', 1)` is correct; joining the output to `swrd.journals` on `journal_id` is an error. If you need a column the function doesn't return (e.g., `research_method`), join `swrd.papers p on p.id = s.id` using the returned `id`.

## 5. Semantic search (find studies by meaning)

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
question = "burnout and turnover among child welfare workers"

emb = requests.post("http://localhost:11434/api/embed", json={
    "model": "embeddinggemma:300m",
    "input": [f"task: search result | query: {question}"],
}).json()["embeddings"][0]                      # 768 floats

hits = requests.post(
    "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/search_papers_semantic",
    headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
             "Content-Profile": "swrd", "Content-Type": "application/json"},
    json={"query_embedding": emb, "match_count": 10},
).json()
for h in hits:
    print(round(h["similarity"], 3), h["publication_year"], h["title"])
```

Same thing with curl:

```bash
QVEC=$(curl -s http://localhost:11434/api/embed \
  -d '{"model":"embeddinggemma:300m","input":["task: search result | query: burnout among child welfare workers"]}' \
  | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['embeddings'][0]))")

curl -s "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/search_papers_semantic" \
  -H "apikey: sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5" \
  -H "Authorization: Bearer sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5" \
  -H "Content-Profile: swrd" -H "Content-Type: application/json" \
  -d "{\"query_embedding\": $QVEC, \"match_count\": 10}"
```

Interpretation: `similarity` runs 0–1 (cosine); ≥ ~0.55 usually on-topic, ≥ ~0.65 strongly so.

### Hybrid search (recommended default for topic questions)

Fuses the semantic and keyword rankings (reciprocal-rank fusion), so results strong in *either* meaning or exact terms surface, and results strong in both rise to the top. Pass the plain question as `query_text` and its embedding as `query_embedding`:

```python
hits = requests.post(
    "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/search_papers_hybrid",
    headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
             "Content-Profile": "swrd", "Content-Type": "application/json"},
    json={"query_text": question, "query_embedding": emb, "match_count": 15},
).json()
# extra fields: rrf_score, semantic_rank, keyword_rank (NULL = not in that arm's top 60)
```

No Ollama available? `rpc/search_papers_keyword` (`{"query_text": "...", "match_count": 10}`) needs no embedding and no setup. Combine any search's returned `id`s with SQL (§4).

## 6. Simple filtered queries (REST shorthand)

For basic lookups, tables and views are directly addressable without SQL:

```bash
BASE="https://kcffctxedcscvvposypb.supabase.co/rest/v1"
KEY="sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
H1="apikey: $KEY"; H2="Authorization: Bearer $KEY"; H3="Accept-Profile: swrd"

# Recent highly cited articles about foster care
curl -s "$BASE/papers?select=title,publication_year&title=ilike.*foster%20care*&publication_year=gte.2015&order=publication_year.desc&limit=5" -H "$H1" -H "$H2" -H "$H3"

# Database overview (citation + counts)
curl -s "$BASE/database_info" -H "$H1" -H "$H2" -H "$H3"
```

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `Could not find the table 'public.papers'` | You forgot the `Accept-Profile: swrd` (GET) or `Content-Profile: swrd` (POST) header |
| `run_sql`: `syntax error` on a valid-looking statement | Remove trailing semicolons; only a single SELECT is accepted |
| `run_sql`: `permission denied` | You attempted a write — access is read-only |
| Exactly 1,000 rows returned | You hit the per-call cap; paginate with `offset`/`limit` or aggregate |
| Semantic results look random | You embedded the query without the `task: search result | query: ` prefix, or used a different model than `embeddinggemma:300m` |
| Ollama connection refused | Start it: `ollama serve` (or launch the Ollama app), then retry |
| `statement timeout` | Narrow the query (year filter, limit); queries are capped at 30 seconds |
