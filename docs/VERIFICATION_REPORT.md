# Migration Verification Report (2026-07-14)

Target: Supabase project `kcffctxedcscvvposypb` (ca-central-1, PG 17.6), schemas `sswr` + `swrd`.
Sources: SSWR `jomsksqqcpkbuhwytovo` (us-east-1), SWRD `obiwpnhrhjrgvmpzxzog` (us-east-2) — both untouched, read-only throughout.

## Result: ALL CHECKS PASSED

### 1. Row counts — exact match
**sswr** (11 tables): papers 23,793 · paper_authors 69,924 · authors 21,209 · paper_html_mappings 24,610 · institution_mappings 4,335 · author_canonical_mapping 375 · author_linkage_audit 153 · country_mappings 106 · search_logs 146 · page_views 0 · paper_embeddings 0 (shell by design; source had 23,793). `fence_sync` intentionally excluded (unrelated app).
**swrd** (9 tables): papers 110,618 · authors 164,549 · paper_authors 241,766 · author_affiliations 113,646 · organizations 34,967 · journals 91 · embedding_models 2 · embedding_runs 2 · openai_title_abstract_embeddings 0 (shell by design; source had 51,751). 33 backup/migration/staging tables intentionally left behind (clean-rebuild directive).

### 2. Column-level parity — identical
`information_schema.columns` diff (name, type, nullability, position): **99/99 SSWR columns, 110/110 SWRD columns identical**. All SWRD LLM-enrichment fields verified present (is_scientific, is_empirical, research_method, stage_01/02/05_confidence + justification, classification_timestamp, classification_version).

### 3. Data-level parity — identical aggregates
- swrd.papers: total | abstracts | DOIs | classified | research_method | sum(times_cited) = 110618|68043|84213|68074|37370|832958 — matches source exactly.
- swrd.paper_authors: 241766 rows | 107909 distinct papers | 137659 distinct authors | 31727 corresponding — exact match.
- swrd.author_affiliations: 113646 | 61224 | 21604 | 51230 — exact match.
- sswr.papers and sswr.paper_authors aggregates — exact match (100% titles/abstracts/methodology/fts populated).

### 4. Author linkage (user-required check)
- 10 random DOIs: full paper→author→position→corresponding→affiliation chains **byte-identical** source vs target (27 author rows).
- Zero orphaned paper_authors (both schemas), zero orphaned author_affiliations, zero unlinked sswr.paper_authors.author_id.

### 5. Structural parity
- Indexes: sswr 33/33, swrd 51/51 (incl. HNSW ×2, ivfflat ×1, GIN fts/trgm).
- RLS policies: sswr 36/36 (excl. fence_sync), swrd 6/6. RLS enabled flags carried over.
- Triggers: swrd updated_at ×3 fire correctly; migration-logging triggers intentionally dropped.
- Views: sswr paper_export + swrd 6 analytics views all queryable with correct results.

### 6. Functions
- All 13 sswr functions restored, bodies rewritten (`public.` → `sswr.`), `search_path` pinned to `sswr, extensions, pg_temp`. Smoke tests pass: search_papers_keyword ✓, search_papers_bm25 ✓, search_authors_by_name (pg_trgm) ✓, autocomplete_institutions ✓, match_papers executes ✓ (returns empty until re-embedding).
- swrd: update_updated_at_column migrated + pinned. The two source semantic-search functions were **already broken in the live source** (they reference a dropped `title_abstract_embeddings` table) and were deliberately not migrated — write fresh ones during re-embedding.

### 7. Embedding shells ready for re-embedding
- sswr.paper_embeddings: 0 rows; embedding vector(1536), embedding_large vector(3072), embedding_small vector(1536); FK + HNSW indexes in place.
- swrd.openai_title_abstract_embeddings: 0 rows; openai_embedding vector(1536); ivfflat index in place.
- Dimensions can be ALTERed if new embedding models differ.

### 8. Sequences
All serial sequences at source values, ≥ max(id): swrd papers 128503, authors 166941, organizations 43650, journals 263, author_affiliations 121102; sswr authors 129750, paper_authors 583350, institution_mappings 4605.

### 9. PostgREST per-schema API — PASSED
Exposed schemas set to include `sswr` and `swrd` (Data API settings; all 15 swrd tables/views + 12 sswr entries + 14 functions exposed; extra search path = public, extensions). Curl tests with the new publishable key:
- `GET /rest/v1/papers` with `Accept-Profile: sswr` → returns SSWR paper ✓
- `GET /rest/v1/papers` with `Accept-Profile: swrd` → returns SWRD paper with DOI ✓
- `GET /rest/v1/papers_with_journals` (swrd view) → joined journal name ✓
- `POST /rest/v1/rpc/search_papers_keyword` with `Content-Profile: sswr` → full-text result ✓
- No profile header → PGRST205 "table not found in public" — **no cross-schema leakage** ✓
