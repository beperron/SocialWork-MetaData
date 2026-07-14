# Phase 1 Audit Summary (2026-07-14)

Read-only inspection of both live source databases. Raw output: `audit/sswr_audit.txt`, `audit/swrd_audit.txt`.

## SSWR — jomsksqqcpkbuhwytovo (us-east-1, PG 15.8)

- **DB size: 1,242 MB** — of which `paper_embeddings` is 881 MB (excluded from migration → ~360 MB moves).
- **12 tables** (row counts): papers 23,793 · paper_authors 69,924 · authors 21,209 · paper_html_mappings 24,610 · institution_mappings 4,335 · author_canonical_mapping 375 · author_linkage_audit 153 · country_mappings 106 · search_logs 146 · page_views 0 · fence_sync 2 · paper_embeddings 23,793 (shell only).
- **1 view**: `paper_export`.
- **Embeddings** (`paper_embeddings`): `embedding vector(1536)`, `embedding_large vector(3072)` (used by `match_papers`), `embedding_small vector(1536)` (models: text-embedding-3-large/small). Two HNSW indexes. All rows excluded; shells + indexes migrate.
- **Extensions**: `vector 0.8.0` in `extensions` (good); **`pg_trgm 1.6` in `public`** → dump will emit `public.gin_trgm_ops` etc.; patch to `extensions.` and install pg_trgm WITH SCHEMA extensions on target.
- **User RPCs** (live-only, must survive): match_papers, match_papers_small, search_papers_bm25, search_papers_keyword, search_papers_fulltext, search_authors_by_name, search_papers_by_institution, autocomplete_institutions, prepare_papers_for_embedding, search_papers_by_embedding, export_paper_embeddings, jsonb_to_vector, update_embedding_vector. (pg_trgm C functions are extension members — recreated by CREATE EXTENSION, not dumped.)
- **RLS**: enabled on all 12 tables, 38 permissive policies (public read on core tables, authenticated write, anon insert on search_logs/page_views).
- **⚠ Unrelated app found**: `fence_sync` table (2 rows, anon read/update policies) + storage buckets `fence-sync`/`fence-sync-app` (1 object) + 1 auth user. This is a separate application living in the SSWR project.
- No triggers, no matviews, no pg_cron.

## SWRD — obiwpnhrhjrgvmpzxzog (us-east-2, PG 15.8)

- **DB size: 1,453 MB** — of which `openai_title_abstract_embeddings` is 822 MB (excluded → ~630 MB moves).
- **42 tables** — far more than repo docs describe. Core: papers **110,618** (docs said 112,282 — that count matches `papers_backup_20251115_095843`; further dedup happened since) · authors 164,549 · paper_authors 241,766 · author_affiliations 113,646 · organizations 34,967 · journals **91** (docs said 262; journal consolidation happened — see journal_mapping + journals_backup) · journal_mapping 17.
- Plus: 8 `backup_*` tables, 12 `migration_*` tables, `integration_rollback_log` 49,452, `staging_crossref` 52,813, `staging_journal`, `eval_*` (empty), `embedding_models`/`embedding_runs` (metadata, kept), `processing_log`, logs.
- **Embeddings**: real table is `openai_title_abstract_embeddings` (51,751 rows, `openai_embedding vector(1536)`, ivfflat index) — NOT the `title_embeddings`/`title_abstract_embeddings` named in repo docs. Also `oss_paper_embeddings` (0 rows, dimensionless `vector`). Data excluded; shells migrate.
- **Extensions**: **`vector 0.8.0` installed in `public`** → dump will emit `public.vector` types and `public.vector_cosine_ops`; patch to `extensions.` on restore. No pg_trgm.
- **User RPCs**: search_papers_by_embedding, search_papers_semantic, import_new_journals_from_staging, match_staging_journals, paper_exists_check, rollback_migration_batch, log_migration_change, update_updated_at_column.
- **Triggers** (6): migration-logging AFTER INSERT on authors/organizations/papers; updated_at BEFORE UPDATE on papers/embedding_models/embedding_runs.
- **7 views**: papers_with_journals, author_publication_stats, publication_trends, highly_cited_papers, v_todays_migration, database_summary, organization_collaborations.
- **RLS**: all 42 tables enabled, several with FORCE RLS; public read on core tables, `no_public_access` (deny-all) on internal logs/mappings.
- No auth users, no storage, no pg_cron. Clean.

## Sizing checkpoint

- Data actually moving: ~360 MB (SSWR) + ~630 MB (SWRD) ≈ **~1.0 GB** → exceeds free tier (500 MB); **Pro plan (8 GB disk) confirmed as target**.
- After re-embedding both datasets the DB will grow by roughly 1–2 GB depending on models chosen — still comfortably within Pro disk.

## Adjustments to migration commands (vs original plan)

- SWRD exclude-data flag targets `public.openai_title_abstract_embeddings` (real name), not the doc names. `oss_paper_embeddings` has 0 rows (nothing to exclude).
- Both dumps need the DDL patch pass for `public.`-qualified extension objects: `vector`/`halfvec`/`sparsevec` types + `vector_*_ops` opclasses (SWRD), `gin_trgm_ops`/`gist_trgm_ops` + pg_trgm function refs (SSWR).
- Target project needs `pg_trgm` installed WITH SCHEMA extensions in addition to `vector`.
- SSWR region us-east-1, SWRD us-east-2 → new project region: user's choice between them.
