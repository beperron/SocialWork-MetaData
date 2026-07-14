---
name: sswr-database
description: Analyze the SSWR Conference Database — 23,793 presentations from every Society for Social Work and Research annual conference (2005–2026) with disambiguated authors, full abstracts, method labels, and semantic + keyword + hybrid search. Use for questions about conference research, scholar trajectories, or institutional activity.
---

# SSWR Conference Database: Analysis Skill

Everything works over HTTPS with the public key below — no password, no account, no database driver. All access is read-only.

## What this database is

**All 23,793 presentations (papers, posters, symposia) from every SSWR annual conference, 2005–2026**, from official programs. Every record has a full abstract and a `methodology` label (`quantitative`/`qualitative`/`mixed_methods`/`review`/`other` — lowercase).

Its distinguishing strength: **authors are disambiguated** — 21,209 canonical identities with name variants resolved across years, so scholar-level and longitudinal analyses are reliable here (unlike the companion SWRD). Disambiguation is thorough but not perfect: for any scholar central to an analysis, run `search_authors_by_name` first and check for residual near-duplicates.

Citation for published work: *Perron, B. E., Victor, B. G., & Qi, Z. (2026). arXiv. https://doi.org/10.48550/arXiv.2603.06814 (in press, Journal of the Society for Social Work and Research)*

## Connection

| What | Value |
|---|---|
| Base URL | `https://kcffctxedcscvvposypb.supabase.co/rest/v1` |
| API key (public, read-only) | `sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5` |
| Headers on every request | `apikey: <KEY>`, `Authorization: Bearer <KEY>`, plus `Accept-Profile: sswr` (GET) or `Content-Profile: sswr` (POST) |

## Choosing the right tool

| The user wants… | Use |
|---|---|
| Counts, trends, scholar histories, joins | **SQL** via `run_sql` → `references/queries.md` |
| Presentations about a concept (wording may vary) | **Hybrid search** (best) or semantic → `references/semantic-search.md` |
| Exact terms/phrases; or no Ollama available | **Keyword search**: `rpc/search_papers_keyword` (no setup needed) |
| Find a scholar | `rpc/search_authors_by_name` (fuzzy), then join by `author_id` |
| Understand a column/value | **The catalog** → `references/catalog.md` |

The search API is **identical to the SWRD's**: `search_papers_semantic`, `search_papers_keyword`, `search_papers_hybrid` — same names, parameters, semantics. Semantic/hybrid require the **`ollama-embeddings`** skill (one-time local setup).

## Minimal working example (SQL over HTTPS)

```bash
KEY="sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
curl -s "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/run_sql" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Content-Profile: sswr" -H "Content-Type: application/json" \
  -d '{"query": "select methodology, count(*) as n from sswr.papers group by 1 order by 2 desc"}'
```

`run_sql` rules: one SELECT, no trailing semicolon, 30-second timeout, 1,000 rows per call.

## Analysis rules an agent must follow

1. For scholar analyses, resolve the person via `search_authors_by_name` and use `author_id` — never match on raw name strings (canonical names are "First Last", sometimes with credentials).
2. Check for residual duplicate identities when a specific scholar matters; report both if ambiguous.
3. Coverage is complete (2005–2026, 100% abstracts) — no era caveats needed, unlike the SWRD.
4. Stay inside `sswr.*` — never join `swrd.*` tables (incompatible id types). `paper_authors` has no year column; join `papers`. Always `select … from` when calling functions; search results arrive pre-sorted best-first (`rank` is a score, not a position). Qualify all columns in joins.
5. When reporting results the user may publish, include the citation above.

## Reference files (read on demand)

- `references/catalog.md` — full data dictionary with measured coverage, value vocabularies, views, functions, join map
- `references/queries.md` — tested SQL recipes (scholar trajectories, institutional activity, trends)
- `references/semantic-search.md` — semantic + hybrid retrieval recipes (requires `ollama-embeddings`)
