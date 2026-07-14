---
name: swrd-database
description: Analyze the Social Work Research Database (SWRD) — journal-article records from 91 social work journals (1920–2025) with study-type classifications and semantic + keyword + hybrid search. Use for questions about the social work journal literature, publication trends, methodology patterns, or finding studies on a topic.
---

# SWRD — Social Work Research Database: Analysis Skill

Everything works over HTTPS with the public key below — no password, no account, no database driver. All access is read-only.

## What this database is

Article records (title, abstract, authors, affiliations, journal, year, DOI) from **91 disciplinary social work journals**:

- **The SWRD proper:** 87,329 records, **1989–2025**. Analytic core: **62,602 research articles with abstracts**, each classified: `is_scientific`, `is_empirical`, `research_method` (`Quantitative` / `Qualitative` / `Mixed-Methods` / `Review` — exact capitalization).
- **The SWRD Supplement:** 23,289 records, **1920–1988**, substantially incomplete. Treat pre-1989 counts as lower bounds. **Default analyses to `publication_year >= 1989`.**

Citation for published work: *Perron, B. E., Victor, B. G., & Qi, Z. (2026). Research on Social Work Practice. https://doi.org/10.1177/10497315261416833*

**Critical caveat:** author names are stored **as published — no disambiguation**. Never report unique-author counts as fact.

## Connection

| What | Value |
|---|---|
| Base URL | `https://kcffctxedcscvvposypb.supabase.co/rest/v1` |
| API key (public, read-only) | `sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5` |
| Headers on every request | `apikey: <KEY>`, `Authorization: Bearer <KEY>`, plus `Accept-Profile: swrd` (GET) or `Content-Profile: swrd` (POST) |

## Choosing the right tool

| The user wants… | Use |
|---|---|
| Counts, trends, joins, aggregates | **SQL** via the `run_sql` endpoint → `references/queries.md` |
| Studies about a concept (wording may vary) | **Hybrid search** (best) or semantic search → `references/semantic-search.md` |
| Studies containing exact terms/phrases | **Keyword search**: `rpc/search_papers_keyword` (no setup needed) |
| To understand what a column/value means | **The catalog** → `references/catalog.md` (measured coverage, exact value vocabularies, join map) |

Semantic and hybrid search require a local query-embedding endpoint — load the **`ollama-embeddings`** skill first (one-time setup). Without it, keyword search still works.

## Minimal working example (SQL over HTTPS)

```bash
KEY="sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
curl -s "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/run_sql" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Content-Profile: swrd" -H "Content-Type: application/json" \
  -d '{"query": "select research_method, count(*) as n from swrd.papers where is_empirical group by 1 order by 2 desc"}'
```

`run_sql` rules: one SELECT statement, no trailing semicolon, 30-second timeout, 1,000 rows per call (paginate with `offset`/`limit`).

## Analysis rules an agent must follow

1. Filter `publication_year >= 1989` unless the question is explicitly historical; if using pre-1989 data, say counts are lower bounds.
2. Do not count "unique authors" — names aren't disambiguated. Count articles, or caveat heavily.
3. Classification labels exist only where abstracts exist (~72% of 1989+ records); condition on `is_scientific`/`is_empirical` explicitly rather than assuming NULL = no.
4. `data_source` is messy provenance, not a clean category — don't group by it for substantive claims.
5. Stay inside `swrd.*` — never join `sswr.*` tables (incompatible id types). `paper_authors` has no year column; join `papers`. Always `select … from` when calling functions; search results arrive pre-sorted best-first (`rank` is a score, not a position). Qualify all columns in joins.
6. Corpus filters (rule 1) apply to research-corpus questions only — never add them to "in total"/"all years" counts.
7. When reporting results to the user, include the article citation above if they intend to publish.

## Reference files (read on demand)

- `references/catalog.md` — full data dictionary: every table/column with measured coverage, exact value vocabularies, views, functions, join map
- `references/queries.md` — tested SQL recipes for common research questions
- `references/semantic-search.md` — semantic + hybrid retrieval recipes (requires `ollama-embeddings`)
