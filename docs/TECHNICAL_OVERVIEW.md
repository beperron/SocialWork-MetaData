# Technical Overview

This document holds the technical detail that intentionally stays out of the README. Audience: collaborators working directly with the database.

**Platform:** one Supabase (PostgreSQL 17) project — `SocialWork-MetaData` (`kcffctxedcscvvposypb`, AWS ca-central-1) — with two isolated schemas. Nothing app-related lives in `public`. Connection recipes and the grants model: [`RECONNECTION_GUIDE.md`](RECONNECTION_GUIDE.md).

## Schema: `sswr`

- `papers` — text PK (`YYYY-TYPE-NNNN`), title, abstract, format, methodology (+ LLM classification variants), `fts` tsvector. 23,793 rows, 2005–2026, 100% abstract/methodology coverage.
- `authors` — canonical author entities (21,209; name variants, institutions, active years as JSONB). Entity resolution IS done for SSWR.
- `paper_authors` — authorship instances (69,924): position, degree, institution (raw + normalized), geo fields, FK to canonical author.
- `paper_html_mappings` — provenance bridge to original conference HTML files.
- `institution_mappings` / `country_mappings` / `author_canonical_mapping` / `author_linkage_audit` — entity-resolution infrastructure.
- `paper_embeddings` — one 768-dim vector per paper (`embeddinggemma:300m`, document prompt `title: {t} | text: {a}`), HNSW cosine index.
- RPCs: `match_papers` (semantic), `search_papers_bm25`, `search_papers_keyword`, `search_authors_by_name` (pg_trgm), `search_papers_by_institution`, `autocomplete_institutions`, others. All pinned `SET search_path = sswr, extensions, pg_temp`.
- Views: `paper_export` (flat denormalized), `database_info` (citation + counts).

## Schema: `swrd`

- `papers` — integer PK, DOI/WoS/Scopus identifiers, journal FK, OA flag, volume/issue/pages, `data_source`, plus SLM classification fields (`is_scientific`, `is_empirical`, `research_method`, stage confidences/justifications). 110,618 rows total.
- **Primary vs Supplement** (per Perron, Victor, & Qi, 2026): `swrd_papers` view = publication_year ≥ 1989 (87,329 rows — the SWRD proper; contains the paper's 62,602 scientific-with-abstract records exactly); `swrd_supplement_papers` view = pre-1989 back to 1920 (23,289 rows; much more incomplete — missing abstracts/details; retained for historical exploration).
- `journals` (91), `authors` (164,549 — **names preserved as provided by sources; NO entity resolution/disambiguation performed**, per the 2026 paper), `organizations` (34,967), `paper_authors` (241,766; position, corresponding flag), `author_affiliations` (113,646).
- `title_abstract_embeddings` — one 768-dim vector per paper, HNSW cosine index.
- `embedding_models` / `embedding_runs` — embedding provenance tracking.
- Views: `database_info` (both citations + counts), `papers_with_journals`, `author_publication_stats`, `publication_trends`, `highly_cited_papers`, `database_summary`, `organization_collaborations`.

## Semantic embeddings

Generated locally via Ollama with `embeddinggemma:300m` (Google EmbeddingGemma, 768 dims), document convention `title: {title} | text: {abstract or "none"}`; query convention `task: search result | query: {question}`. Model selection is based on extensive benchmarking on this corpus (Perron et al., manuscript in preparation): EmbeddingGemma matched or beat commercial embedding APIs on retrieval quality while being free and small enough for local, private inference. Pipeline: `migration/06_embed_pipeline.py` (resumable, batch=32).

## Migration provenance (July 2026)

Both datasets were consolidated from two separate Supabase projects into this one (cost + coherence). Method in brief: read-only audits of both sources (`migration/01_audit.sql`, snapshots in `audit/`); three-section `pg_dump` per source with embedding rows excluded; targeted DDL patching for extensions installed in `public` on the sources; restore into `public` → `ALTER SCHEMA public RENAME`; function bodies rewritten and `search_path`-pinned; tighter-than-default grants; exhaustive verification (exact row counts, column-level diffs, aggregate parity, byte-identical author-linkage samples, REST leakage checks) — all in [`VERIFICATION_REPORT.md`](VERIFICATION_REPORT.md). SSWR was migrated 1:1; SWRD was rebuilt clean (9 core tables from a 42-table source; backups/migration debris left behind). Embeddings were regenerated rather than migrated. Data-quality findings and the SWRD cleanup roadmap: [`HEALTH_CHECK_REPORT.md`](HEALTH_CHECK_REPORT.md).

Old source projects remain intact until formally retired: SSWR `jomsksqqcpkbuhwytovo`, SWRD `obiwpnhrhjrgvmpzxzog`.

## Repo layout

```
migration/   audit + rename/grants SQL, health checks, embedding pipeline
audit/       raw audit snapshots, captured view/function DDL
docs/        this file, verification + health reports, reconnection guide, Phase-1 audit
assets/      README graphics + the matplotlib script that renders them
```
