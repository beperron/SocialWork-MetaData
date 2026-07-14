---
name: sswr-database
description: Query the SSWR Conference Database — 23,793 presentations from every Society for Social Work and Research annual conference (2005–2026), with disambiguated authors, method labels, full abstracts, and semantic search. Use when the user asks about social work conference research, scholar trajectories, institutional activity, or wants to find presentations on a topic.
---

# SSWR Conference Database: Agent Skill

You (the agent) can query a hosted PostgreSQL database of SSWR conference-presentation records. This file gives you everything needed: connection details, schema reference, plain SQL access, REST access, and a local semantic-search pipeline. All access is **read-only**.

## 1. What this database is

Records for **all 23,793 presentations (papers, posters, symposia) at the Society for Social Work and Research annual conference, 2005–2026**, compiled from official conference programs. Every record has a full abstract and a research-method label.

Its distinguishing feature: **authors are disambiguated**. The 21,209 presenting researchers have canonical identities with name variants resolved across all years — author-level and longitudinal analyses are reliable here (unlike the companion SWRD journal database). Disambiguation is thorough but not perfect: when a scholar matters to the analysis, run `search_authors_by_name` first and check for residual near-duplicate entries.

Citation to report when the user publishes with these data: *Perron, B. E., Victor, B. G., & Qi, Z. (2026). AI-assisted curation of conference scholarship. arXiv. https://doi.org/10.48550/arXiv.2603.06814 (in press, Journal of the Society for Social Work and Research)*

## 2. Connection details

| What | Value |
|---|---|
| REST base URL | `https://kcffctxedcscvvposypb.supabase.co/rest/v1` |
| REST API key (public, read-only) | `sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5` |
| REST schema header | `Accept-Profile: sswr` on GET; `Content-Profile: sswr` on POST |
| SQL (read-only login) | `postgresql://metadata_reader.kcffctxedcscvvposypb:SocialWorkData2026@aws-0-ca-central-1.pooler.supabase.com:5432/postgres` |
| SQL schema | Tables live in the `sswr` schema (qualify names: `sswr.papers`) |

The REST key and SQL login are intentionally public and read-only (30-second statement timeout, SELECT-only). Writes will be rejected.

## 3. Schema reference

| Table | Rows | Key columns |
|---|---|---|
| `sswr.papers` | 23,793 | `id` (text PK, e.g. `2019-O-0142`), `title`, `abstract`, `year`, `format` (oral/poster/symposium…), `methodology` (values: `quantitative`, `qualitative`, `mixed_methods`, `review`, `other`), `author_count` |
| `sswr.authors` | 21,209 | `id` (int PK), `name` (canonical), `variants` (jsonb), `institutions` (jsonb), `years` (jsonb), `total_papers` |
| `sswr.paper_authors` | 69,924 | `paper_id`, `author_id` → canonical author, `name` (as printed), `author_order` (1 = first), `institution`, `institution_normalized`, `position_normalized`, `country_normalized` |
| `sswr.institution_mappings` | 4,335 | raw → canonical institution names |
| `sswr.paper_embeddings` | 23,793 | `paper_id`, `embedding` (768-dim vector), `model` |

Convenience views: `sswr.paper_export` (flat, one row per paper with author arrays — easiest for exports), `sswr.database_info` (citation + counts).

Search functions (§5 for semantic):
- `sswr.match_papers(query_embedding, match_threshold, match_count, min_year, max_year)` — semantic
- `sswr.search_papers_bm25(query_text, match_count, min_year, max_year)` — ranked full-text
- `sswr.search_papers_keyword(query_text, match_count, min_year, max_year)` — substring match
- `sswr.search_authors_by_name(query_text, match_count)` — fuzzy author lookup
- `sswr.search_papers_by_institution(query_text, match_count, min_year, max_year)` — by institution
- `sswr.autocomplete_institutions(prefix, limit_count)`

## 4. SQL queries

```bash
psql "postgresql://metadata_reader.kcffctxedcscvvposypb:SocialWorkData2026@aws-0-ca-central-1.pooler.supabase.com:5432/postgres" \
  -c "select methodology, count(*) from sswr.papers group by 1 order by 2 desc limit 10;"
```

```python
# pip install psycopg2-binary
import psycopg2
conn = psycopg2.connect("postgresql://metadata_reader.kcffctxedcscvvposypb:SocialWorkData2026@aws-0-ca-central-1.pooler.supabase.com:5432/postgres")
cur = conn.cursor()
cur.execute("select year, count(*) from sswr.papers group by 1 order by 1")
rows = cur.fetchall()
```

Example queries the user commonly wants:

```sql
-- Finding a scholar: ALWAYS start with fuzzy lookup (canonical names are stored
-- as "First Last", sometimes with credentials, e.g. "Brian Perron, PhD")
select author_id, author_name, total_papers from sswr.search_authors_by_name('michael vaughn', 5);

-- Then pull their full presentation history by the returned author_id
select p.year, p.title, pa.author_order
from sswr.paper_authors pa
join sswr.papers p on p.id = pa.paper_id
where pa.author_id = 108089    -- id from the lookup above
order by p.year;

-- Ranked full-text topic search
select id, title, year from sswr.search_papers_bm25('kinship care', 10);

-- Most active institutions in a period (first authors)
select institution_normalized, count(*)
from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id
where pa.author_order = 1 and p.year between 2020 and 2026
group by 1 order by 2 desc limit 10;
```

Note: queries have a 30s timeout; use `limit` and year filters for heavy joins.

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
# pip install requests psycopg2-binary
import requests, psycopg2, json

question = "interventions for children in kinship foster care"
emb = requests.post("http://localhost:11434/api/embed", json={
    "model": "embeddinggemma:300m",
    "input": [f"task: search result | query: {question}"],
}).json()["embeddings"][0]                      # 768 floats

conn = psycopg2.connect("postgresql://metadata_reader.kcffctxedcscvvposypb:SocialWorkData2026@aws-0-ca-central-1.pooler.supabase.com:5432/postgres")
cur = conn.cursor()
cur.execute(
    "select id, title, year, similarity "
    "from sswr.match_papers(%s::extensions.vector, 0.3, %s)",
    (json.dumps(emb), 10),
)
for row in cur.fetchall():
    print(row)
```

Or over REST (no Postgres client needed):

```bash
QVEC=$(curl -s http://localhost:11434/api/embed \
  -d '{"model":"embeddinggemma:300m","input":["task: search result | query: interventions for children in kinship foster care"]}' \
  | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['embeddings'][0]))")

curl -s "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/match_papers" \
  -H "apikey: sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5" \
  -H "Authorization: Bearer sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5" \
  -H "Content-Profile: sswr" -H "Content-Type: application/json" \
  -d "{\"query_embedding\": $QVEC, \"match_count\": 10}"
```

Interpretation: `similarity` runs 0–1 (cosine); results above ~0.55 are usually on-topic. `match_papers` returns each paper's full author list as JSON, so one call gives you a complete answer. For hybrid search, also run `search_papers_bm25` with the same question and merge.

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
| REST: `Could not find the table 'public.papers'` | You forgot the `Accept-Profile: sswr` header |
| SQL: `relation "papers" does not exist` | Qualify with the schema: `sswr.papers` |
| SQL: `permission denied` | You attempted a write — the login is SELECT-only |
| SQL: `type "vector" does not exist` | Cast as `::extensions.vector` |
| Semantic results look random | You embedded the query without the `task: search result | query: ` prefix, or used a different model than `embeddinggemma:300m` |
| Ollama connection refused | Start it: `ollama serve` (or launch the Ollama app), then retry |
| Query cancelled after 30s | Narrow the query (year filter, limit) |
