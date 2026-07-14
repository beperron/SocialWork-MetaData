# SSWR — Semantic Catalog (Data Dictionary)

*Generated from the live database on 2026-07-14 by `migration/07_generate_catalog.py`. All counts and coverage figures are measured, not estimated.*

## Tables

### `author_canonical_mapping` — 375 rows

Audit trail of author-identity merges.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `author_id` | integer | 100.0% |  |
| `canonical_author_id` | integer | 100.0% |  |
| `confidence` | double precision | 100.0% |  |
| `match_reasons` | ARRAY | 100.0% |  |
| `reviewed` | boolean | 100.0% |  |
| `created_at` | timestamp with time zone | 100.0% |  |

### `author_linkage_audit` — 153 rows

Audit log of author-linkage decisions.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `paper_author_id` | bigint | 100.0% |  |
| `original_name` | text | 100.0% |  |
| `original_name_normalized` | text | 100.0% |  |
| `matched_author_id` | integer | 100.0% |  |
| `matched_author_name` | text | 100.0% |  |
| `match_type` | text | 100.0% |  |
| `match_score` | integer | 100.0% |  |
| `created_at` | timestamp with time zone | 100.0% |  |
| `notes` | text | 26.8% |  |

### `authors` — 21,209 rows

CANONICAL author entities — disambiguated across years. name format: 'First Last', sometimes with credentials.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `name` | text | 100.0% |  |
| `variants` | jsonb | 100.0% | JSON list of name variants resolved to this identity. |
| `institutions` | jsonb | 100.0% | JSON list of institutions seen for this author. |
| `years` | jsonb | 100.0% |  |
| `total_papers` | integer | 100.0% | Presentations linked to this canonical identity. |
| `is_canonical` | boolean | 100.0% |  |

### `country_mappings` — 106 rows

Raw → normalized country names.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `raw_name` | text | 100.0% |  |
| `normalized_name` | text | 100.0% |  |
| `created_at` | timestamp with time zone | 100.0% |  |

### `institution_mappings` — 4,335 rows

Raw → canonical institution name mappings.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `raw_name` | text | 100.0% |  |
| `cleaned_name` | text | 100.0% |  |
| `canonical_name` | text | 100.0% |  |
| `institution_id` | text | 100.0% |  |
| `created_at` | timestamp with time zone | 100.0% |  |

### `page_views` — 0 rows

Telemetry from the original web app (not research data).

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | bigint | — |  |
| `visited_at` | timestamp with time zone | — |  |
| `page` | text | — |  |
| `referrer` | text | — |  |
| `user_agent` | text | — |  |
| `screen_width` | integer | — |  |
| `screen_height` | integer | — |  |

### `paper_authors` — 69,924 rows

Authorship instances: name as printed + link to canonical author (author_id).

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | bigint | 100.0% |  |
| `paper_id` | text | 100.0% |  |
| `author_order` | integer | 100.0% | Byline position; 1 = first author. |
| `name` | text | 100.0% |  |
| `name_normalized` | text | 100.0% |  |
| `degree` | text | 97.1% |  |
| `position` | text | 97.1% |  |
| `institution` | text | 100.0% |  |
| `institution_raw` | text | 100.0% |  |
| `institution_id` | text | 99.7% |  |
| `city` | text | 97.1% |  |
| `state_province` | text | 97.1% |  |
| `country` | text | 100.0% |  |
| `country_normalized` | text | 99.0% |  |
| `country_fixed` | boolean | 0.0% |  |
| `country_fix_from` | text | 0.0% |  |
| `parsing_error` | boolean | 0.0% |  |
| `author_id` | integer | 100.0% |  |
| `position_normalized` | text | 100.0% |  |
| `canonical_author_id` | integer | 100.0% |  |
| `institution_normalized` | text | 100.0% | Institution mapped to a canonical name. |

### `paper_embeddings` — 23,793 rows

One 768-dim meaning vector per presentation (embeddinggemma:300m).

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | bigint | 100.0% |  |
| `paper_id` | text | 100.0% |  |
| `embedding` | vector(768) | 100.0% |  |
| `created_at` | timestamp with time zone | 100.0% |  |
| `model` | text | 100.0% |  |

### `paper_html_mappings` — 24,610 rows

Provenance: link from each record to its source conference-program HTML file.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `html_path` | text | 100.0% |  |
| `paper_id` | text | 96.5% |  |
| `year` | integer | 100.0% |  |
| `match_method` | text | 96.5% |  |
| `created_at` | timestamp with time zone | 100.0% |  |

### `papers` — 23,793 rows

One row per SSWR conference presentation. The primary table.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | text | 100.0% | Presentation identifier: YYYY-TYPE-NNNN (e.g. 2019-O-0142). |
| `year` | integer | 100.0% | Conference year (2005–2026, complete). |
| `title` | text | 100.0% | Presentation title. |
| `abstract` | text | 100.0% | Full abstract (present for 100% of records). |
| `format` | text | 100.0% | Presentation format code from the program. |
| `author_parse_llm` | text | 0.0% |  |
| `original_paper_id` | text | 96.3% |  |
| `methodology_qwen3-32b` | text | 87.4% |  |
| `methodology_confidence_qwen3-32b` | text | 87.4% |  |
| `status` | text | 0.0% |  |
| `author_count` | integer | 100.0% | Number of authorship rows (kept consistent with paper_authors). |
| `fts` | tsvector | 100.0% | Precomputed full-text search vector (used by keyword/BM25 search). |
| `methodology_evidence_qwen3-32b` | text | 0.0% |  |
| `methodology_gpt-oss-20b` | text | 100.0% |  |
| `methodology_evidence_gpt-oss-20b` | text | 100.0% |  |
| `methodology` | text | 100.0% | Research-method label. Exact values below (lowercase). |

### `search_logs` — 146 rows

Telemetry from the original search app (not research data).

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | bigint | 100.0% |  |
| `created_at` | timestamp with time zone | 100.0% |  |
| `search_type` | text | 100.0% |  |
| `query_text` | text | 100.0% |  |
| `filters` | jsonb | 100.0% |  |
| `results_count` | integer | 100.0% |  |
| `session_hash` | text | 100.0% |  |
| `duration_ms` | integer | 100.0% |  |

## Value vocabularies (exact values — match capitalization)

### `papers.methodology`

| Value | Count |
|---|---|
| `quantitative` | 14,542 |
| `qualitative` | 5,565 |
| `mixed_methods` | 2,172 |
| `review` | 1,274 |
| `other` | 240 |

### `papers.format`

| Value | Count |
|---|---|
| `Oral` | 12,346 |
| `Poster` | 8,868 |
| `Unknown` | 2,046 |
| `Sig` | 246 |
| `Flash` | 183 |
| `Other` | 93 |
| `Workshop` | 11 |

## Views (precomputed answers)

| View | What it answers |
|---|---|
| `database_info` |  |
| `paper_export` |  |

## Functions (callable via SQL or the REST rpc endpoint)

| Function | Signature |
|---|---|
| `autocomplete_institutions` | (prefix text, limit_count integer DEFAULT 10) |
| `export_paper_embeddings` | () |
| `jsonb_to_vector` | (embedding jsonb) |
| `match_papers` | (query_embedding vector, match_threshold double precision DEFAULT 0.3, match_count integer DEFAULT 10, min_year integer DEFAULT 2005, max_year integer DEFAULT 2026) |
| `prepare_papers_for_embedding` | (max_papers integer DEFAULT 100) |
| `run_sql` | (query text) |
| `search_authors_by_name` | (query_text text, match_count integer DEFAULT 20) |
| `search_papers_bm25` | (query_text text, match_count integer, min_year integer DEFAULT 0, max_year integer DEFAULT 9999) |
| `search_papers_by_embedding` | (query_embedding vector, similarity_threshold double precision, match_count integer, filter_year integer DEFAULT NULL::integer) |
| `search_papers_by_institution` | (query_text text, match_count integer DEFAULT 20, min_year integer DEFAULT 2005, max_year integer DEFAULT 2026) |
| `search_papers_fulltext` | (search_query text, max_results integer DEFAULT 1000, min_rank real DEFAULT 0.01) |
| `search_papers_hybrid` | (query_text text, query_embedding vector, match_count integer DEFAULT 10, rrf_k integer DEFAULT 60, min_year integer DEFAULT 2005, max_year integer DEFAULT 2026) |
| `search_papers_keyword` | (query_text text, match_count integer DEFAULT 10, min_year integer DEFAULT 2005, max_year integer DEFAULT 2026) |
| `search_papers_semantic` | (query_embedding vector, match_count integer DEFAULT 10, min_year integer DEFAULT 2005, max_year integer DEFAULT 2026) |
| `update_embedding_vector` | () |

## Join map

- `author_canonical_mapping.author_id` → `authors.id`
- `author_canonical_mapping.canonical_author_id` → `authors.id`
- `paper_authors.author_id` → `authors.id`
- `paper_authors.canonical_author_id` → `authors.id`
- `paper_authors.paper_id` → `papers.id`
- `paper_embeddings.paper_id` → `papers.id`

