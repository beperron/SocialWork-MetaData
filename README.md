# SocialWork-MetaData

A consolidated research metadata platform for social work scholarship, hosted on a single Supabase (PostgreSQL) project with two isolated schemas:

| Schema | Dataset | Scale |
|---|---|---|
| **`sswr`** | Society for Social Work and Research (SSWR) annual conference metadata, 2005–2026 | 23,793 papers · 21,209 canonical authors · 69,924 authorship records |
| **`swrd`** | Social Work Research Database — peer-reviewed journal articles, 1920–2025 | 110,618 papers · 164,549 authors · 91 journals · 241,766 authorship records · 113,646 author–organization affiliations |

Both datasets carry full-text search (Postgres `tsvector`), trigram author/institution matching (`pg_trgm`), and 768-dimensional semantic embeddings (`pgvector`, EmbeddingGemma-300m) for hybrid retrieval.

This repository contains the migration tooling, audit trail, verification reports, and operational documentation for the platform. **It contains no data and no credentials** — the data lives in Supabase; credentials live in a gitignored `.env`.

## Why this exists

The two datasets previously lived in separate Supabase projects, doubling hosting costs for closely related work. In July 2026 both were consolidated into one Pro project (`kcffctxedcscvvposypb`, AWS ca-central-1) with schema-level isolation — each dataset keeps its own tables, functions, row-level-security policies, and API surface, addressable independently through PostgREST schema profiles.

Two different migration philosophies were used deliberately:

- **SSWR — exact 1:1 copy.** The source database was in excellent shape (100% title/abstract/methodology coverage, fully resolved author entities, zero orphans). Every table, index, RLS policy, and RPC function was carried over verbatim, then rewritten to live in the `sswr` schema.
- **SWRD — clean rebuild.** The source had accreted 42 tables of backups, migration scaffolding, and staging debris around 9 essential tables. Only the essential core was migrated: `papers`, `journals`, `authors`, `organizations`, `paper_authors`, `author_affiliations`, embedding-tracking tables, and 6 analytics views. Everything else stayed behind in the retired project.

Embeddings were **not** migrated. Both schemas were re-embedded from scratch with a single consistent model (see below), replacing three incompatible legacy embedding sets (768/1536/3072-dim from different providers).

## Database architecture

### `sswr` schema
- `papers` — text PK (`YYYY-TYPE-NNNN`), title, abstract, format, methodology (+ LLM classification variants), `fts` tsvector
- `authors` — canonical author entities (name variants, institutions, active years as JSONB)
- `paper_authors` — authorship instances: position, degree, institution (raw + normalized), geo fields, FK to canonical author
- `paper_html_mappings` — provenance bridge to original conference HTML files
- `institution_mappings` / `country_mappings` / `author_canonical_mapping` / `author_linkage_audit` — entity-resolution infrastructure
- `paper_embeddings` — one 768-dim vector per paper (`embeddinggemma:300m`), HNSW-indexed
- `search_logs` / `page_views` — app telemetry
- RPCs: `match_papers` (semantic), `search_papers_bm25`, `search_papers_keyword`, `search_authors_by_name` (trigram), `search_papers_by_institution`, `autocomplete_institutions`, and more
- `paper_export` — flat denormalized view for analysis exports

### `swrd` schema
- `papers` — integer PK, DOI/WoS/Scopus identifiers, journal FK, citations, OA flag, volume/issue/pages, plus LLM-enrichment fields: `is_scientific`, `is_empirical`, `research_method`, stage confidences/justifications
- `journals`, `authors` (ORCID/WoS/Scopus ids), `organizations`, `paper_authors` (position, corresponding flag), `author_affiliations`
- `title_abstract_embeddings` — one 768-dim vector per paper, HNSW-indexed
- `embedding_models` / `embedding_runs` — embedding provenance tracking
- Views: `papers_with_journals`, `author_publication_stats`, `publication_trends`, `highly_cited_papers`, `database_summary`, `organization_collaborations`

### Semantic embeddings
All embeddings are generated locally via [Ollama](https://ollama.com) with **`embeddinggemma:300m`** (Google EmbeddingGemma, 768 dims), using the model's document prompt convention:

```
title: {title} | text: {abstract or "none"}
```

Queries should use the matching query convention: `task: search result | query: {question}`. Cosine distance, HNSW indexes.

## Repository layout

```
migration/
  01_audit.sql               read-only source-database audit (sizes, counts, DDL, RLS, vectors)
  02_rename_and_grants.sql   schema rename + role grants applied after each restore
  04_health_check_swrd.sql   data-quality checks for swrd
  05_health_check_sswr.sql   data-quality checks for sswr
  06_embed_pipeline.py       resumable Ollama → pgvector embedding pipeline
  dumps/                     local working dir for pg_dump output (gitignored — dumps are never committed)
audit/                       raw audit snapshots + captured view/function DDL
docs/
  PHASE1_AUDIT_SUMMARY.md    what the source databases actually contained
  VERIFICATION_REPORT.md     full parity verification (all checks passed)
  HEALTH_CHECK_REPORT.md     data-quality review + SWRD cleanup roadmap
  RECONNECTION_GUIDE.md      how to point apps/scripts at the new schemas
.env.example                 connection-string template (real .env is gitignored)
```

## Migration method (summary)

1. **Read-only audit** of both live sources: exact row counts, per-table sizes, extension placement, vector dimensions, full function DDL (several RPCs existed only in the live DBs), indexes, RLS policies, triggers, and non-`public` surfaces (auth/storage/cron).
2. **Three-section `pg_dump`** per source (`pre-data` / `data` / `post-data`, `--no-owner --no-privileges`), excluding embedding-table rows and out-of-scope tables. SWRD used a selective `-t` table list.
3. **Targeted DDL patching** — both sources had extensions installed in `public` (`vector` in SWRD, `pg_trgm` in SSWR); dumped references were rewritten to the `extensions` schema, where the target installs them.
4. **Restore into `public` → `ALTER SCHEMA public RENAME TO sswr/swrd`** — the rename is a catalog operation, so tables, indexes, sequences, defaults, and RLS policies follow automatically and data is never touched by text substitution. Repeated for the second source with a fresh `public` between.
5. **Function fixup** — bodies rewritten from `public.` references, and every function pinned with `SET search_path = <schema>, extensions, pg_temp`.
6. **PostgREST exposure + grants** — both schemas exposed through the Data API; deliberately tighter-than-default grants (`service_role` full; `anon`/`authenticated` read + execute only, with narrow write exceptions).
7. **Verification** — exact row-count parity, column-level `information_schema` diffs (99 + 110 columns identical), aggregate data parity (null-rates, citation sums, distinct linkage counts), byte-identical author-linkage chains for sampled papers, index/policy/sequence parity, per-schema REST tests with leakage checks.
8. **Health check** — referential integrity, duplicate detection, null-rate profiling, range sanity. Results and a prioritized SWRD cleanup roadmap are in `docs/HEALTH_CHECK_REPORT.md`.

## Connecting

Clients must name the schema explicitly (nothing lives in `public`):

```ts
// supabase-js
const supabase = createClient(url, key, { db: { schema: 'sswr' } })
const { data } = await supabase.schema('swrd').from('papers_with_journals').select('*')
```

```python
# supabase-py
supabase = create_client(url, key, options=ClientOptions(schema="swrd"))
```

```bash
# raw REST — Accept-Profile (reads) / Content-Profile (writes, RPC)
curl ".../rest/v1/papers?limit=5" -H "apikey: $KEY" -H "Accept-Profile: swrd"
```

Full recipes, the grants model, and re-embedding notes: [`docs/RECONNECTION_GUIDE.md`](docs/RECONNECTION_GUIDE.md).

## Data quality at a glance

- **sswr**: production-quality. 100% title/abstract/methodology coverage, fully linked author entities, zero orphans.
- **swrd**: structurally sound (zero duplicate DOIs/WoS/Scopus ids, perfect FK integrity) with known content debt inherited from its assembly history: ~2.4% of papers lack author records, 16% of author rows are unreferenced, author entity resolution is still to-do, and `data_source` needs normalization (26 messy values). See the [health check report](docs/HEALTH_CHECK_REPORT.md) for the full roadmap.

## Provenance

- SSWR data was scraped and entity-resolved from official SSWR conference programs (2005–2026); see the SSWR-History project.
- SWRD aggregates Web of Science, Scopus, DOAJ, Digital Commons, and journal-archive exports, deduplicated on DOI/WoS/Scopus identifiers, with LLM-based scientific/empirical/method classification on papers with abstracts (61.5% coverage).
- The original source Supabase projects remain intact (read-only reference) until formally retired.

---
*Maintained by Brian Perron (University of Michigan School of Social Work). Migration and verification performed July 2026.*
