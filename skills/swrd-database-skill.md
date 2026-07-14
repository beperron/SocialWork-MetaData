---
name: swrd-database
description: Query the Social Work Research Database (SWRD) — 110,618 journal-article records from 91 social work journals (1920–2025) with study-type classifications and semantic search. Use when the user asks about social work journal literature, publication trends, methodology patterns, or wants to find studies on a topic.
---

# SWRD — Social Work Research Database: Agent Skill

You (the agent) can query a hosted PostgreSQL database of social work journal-article records. This file gives you everything needed: connection details, schema reference, plain SQL access, REST access, and a local semantic-search pipeline. All access is **read-only**.

## 1. What this database is

The SWRD contains records (title, abstract, authors, affiliations, journal, year, DOI, citation count) for articles in **91 disciplinary social work journals**:

- **The SWRD proper:** 87,329 records, **1989–2025**, systematically compiled and validated. Within it, **62,602 research articles with abstracts**, each classified: `is_scientific` (research vs editorial/review/letter), `is_empirical`, and `research_method` (values: `Quantitative`, `Qualitative`, `Mixed-Methods`, `Review` — note the exact capitalization).
- **The SWRD Supplement:** 23,289 records, **1920–1988**, substantially incomplete (missing abstracts/details). Treat pre-1989 counts as lower bounds. **Default analyses to `publication_year >= 1989` unless the user asks for historical data.**

Citation to report when the user publishes with these data: *Perron, B. E., Victor, B. G., & Qi, Z. (2026). Evolution of social work knowledge production over 35 years. Research on Social Work Practice. https://doi.org/10.1177/10497315261416833*

**Critical caveat for author-level analysis:** author names are stored **exactly as published — no disambiguation**. "J. Garcia" and "Jennifer Garcia" may be the same person under two entries. Do not report unique-author counts as fact; caveat them.

## 2. Connection details

| What | Value |
|---|---|
| REST base URL | `https://kcffctxedcscvvposypb.supabase.co/rest/v1` |
| REST API key (public, read-only) | `sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5` |
| REST schema header | `Accept-Profile: swrd` on GET; `Content-Profile: swrd` on POST |
| SQL (read-only login) | `postgresql://metadata_reader.kcffctxedcscvvposypb:SocialWorkData2026@aws-0-ca-central-1.pooler.supabase.com:5432/postgres` |
| SQL schema | Tables live in the `swrd` schema; the login's default `search_path` already includes it |

The REST key and SQL login are intentionally public and read-only (30-second statement timeout, SELECT-only). Writes will be rejected.

## 3. Schema reference

| Table | Rows | Key columns |
|---|---|---|
| `swrd.papers` | 110,618 | `id` (int PK), `title`, `abstract`, `publication_year`, `journal_id` → journals, `doi`, `times_cited`, `document_type`, `data_source`, `open_access`, `volume`, `issue`, `pages`, `is_scientific` (bool), `is_empirical` (bool), `research_method` (text: `Quantitative`/`Qualitative`/`Mixed-Methods`/`Review`) |
| `swrd.journals` | 91 | `id`, `name`, `publisher` |
| `swrd.authors` | 164,549 | `id`, `name` (as published), `orcid`, `wos_author_id`, `scopus_author_id` |
| `swrd.paper_authors` | 241,766 | `paper_id`, `author_id`, `position` (1 = first author), `is_corresponding` |
| `swrd.organizations` | 34,967 | `id`, `name`, `country` |
| `swrd.author_affiliations` | 113,646 | `author_id`, `organization_id`, `paper_id` |
| `swrd.title_abstract_embeddings` | 110,618 | `paper_id`, `embedding` (768-dim vector), `model` |

Convenience views: `swrd.swrd_papers` (1989–2025 only), `swrd.swrd_supplement_papers` (pre-1989), `swrd.papers_with_journals` (papers joined to journal names), `swrd.publication_trends` (per-year aggregates), `swrd.author_publication_stats`, `swrd.highly_cited_papers` (>50 citations), `swrd.database_summary`, `swrd.database_info` (citation + counts).

Search functions: `swrd.search_papers_semantic(query_embedding, match_count, min_year, max_year)` — see §5.

## 4. SQL queries

Works with `psql`, or any Postgres client library, using the connection string above.

```bash
psql "postgresql://metadata_reader.kcffctxedcscvvposypb:SocialWorkData2026@aws-0-ca-central-1.pooler.supabase.com:5432/postgres" \
  -c "select research_method, count(*) from swrd.papers where is_empirical group by 1 order by 2 desc;"
```

```python
# pip install psycopg2-binary
import psycopg2
conn = psycopg2.connect("postgresql://metadata_reader.kcffctxedcscvvposypb:SocialWorkData2026@aws-0-ca-central-1.pooler.supabase.com:5432/postgres")
cur = conn.cursor()
cur.execute("""
    select publication_year, count(*)
    from swrd.papers
    where publication_year >= 1989 and is_scientific
    group by 1 order by 1
""")
rows = cur.fetchall()
```

Example queries the user commonly wants:

```sql
-- Topic count by keyword (title/abstract), core years only
select count(*) from swrd.papers
where publication_year >= 1989
  and (title ilike '%kinship care%' or abstract ilike '%kinship care%');

-- Methodology trend by decade
select (publication_year/10)*10 as decade, research_method, count(*)
from swrd.papers where is_empirical group by 1,2 order by 1,2;

-- Most-cited articles in a journal
select p.title, p.publication_year, p.times_cited
from swrd.papers p join swrd.journals j on j.id = p.journal_id
where j.name = 'Social Service Review'
order by p.times_cited desc limit 10;

-- Full author list for a paper (names as published!)
select a.name, pa.position, pa.is_corresponding
from swrd.paper_authors pa join swrd.authors a on a.id = pa.author_id
where pa.paper_id = 12345 order by pa.position;   -- replace 12345 with a real paper id
```

Notes: queries have a 30s timeout — add `where publication_year >= 1989`, `limit`, and indexed filters (`journal_id`, `publication_year`, `doi`, `is_scientific`, `research_method`) to stay fast. If the connection fails from an IPv6-less network, this pooler host is IPv4-compatible; check firewall on port 5432.

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
- (Documents were embedded as `title: {title} | text: {abstract}` — you never need to do this; it's already done.)

### Recipe

```python
# pip install requests psycopg2-binary
import requests, psycopg2, json

question = "burnout and turnover among child welfare workers"
emb = requests.post("http://localhost:11434/api/embed", json={
    "model": "embeddinggemma:300m",
    "input": [f"task: search result | query: {question}"],
}).json()["embeddings"][0]                      # 768 floats

conn = psycopg2.connect("postgresql://metadata_reader.kcffctxedcscvvposypb:SocialWorkData2026@aws-0-ca-central-1.pooler.supabase.com:5432/postgres")
cur = conn.cursor()
cur.execute(
    "select id, title, publication_year, journal_name, times_cited, similarity "
    "from swrd.search_papers_semantic(%s::extensions.vector, %s)",
    (json.dumps(emb), 10),
)
for row in cur.fetchall():
    print(row)
```

Or over REST (no Postgres client needed):

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

Interpretation: `similarity` runs 0–1 (cosine); on this corpus, results above ~0.55 are usually on-topic and above ~0.65 strongly so. Combine semantic results with SQL filters by using the returned `id`s.

## 6. REST queries (no SQL client required)

PostgREST syntax; always send the three headers shown.

```bash
BASE="https://kcffctxedcscvvposypb.supabase.co/rest/v1"
KEY="sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
H1="apikey: $KEY"; H2="Authorization: Bearer $KEY"; H3="Accept-Profile: swrd"

# Recent highly cited articles about foster care
curl -s "$BASE/papers?select=title,publication_year,times_cited&title=ilike.*foster%20care*&publication_year=gte.2015&order=times_cited.desc&limit=5" -H "$H1" -H "$H2" -H "$H3"

# Papers joined with journal names (via the view)
curl -s "$BASE/papers_with_journals?select=title,journal_name,publication_year&journal_name=eq.Social%20Work&limit=5" -H "$H1" -H "$H2" -H "$H3"

# Database overview
curl -s "$BASE/database_info" -H "$H1" -H "$H2" -H "$H3"
```

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| REST: `Could not find the table 'public.papers'` | You forgot the `Accept-Profile: swrd` header |
| SQL: `permission denied` | You attempted a write, or connected as the wrong user — the login is SELECT-only |
| SQL: `type "vector" does not exist` | Cast as `::extensions.vector` (the type lives in the `extensions` schema) |
| Semantic results look random | You embedded the query without the `task: search result | query: ` prefix, or used a different model than `embeddinggemma:300m` |
| Ollama connection refused | Start it: `ollama serve` (or launch the Ollama app), then retry |
| Query cancelled after 30s | Narrow the query (year filter, limit); the read-only role enforces a 30s timeout |
