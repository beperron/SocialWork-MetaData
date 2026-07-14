# SWRD — Semantic Catalog (Data Dictionary)

*Generated from the live database on 2026-07-14 by `migration/07_generate_catalog.py`. All counts and coverage figures are measured, not estimated.*

## Tables

### `author_affiliations` — 113,646 rows

Author–organization pairs per paper.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `author_id` | integer | 100.0% |  |
| `organization_id` | integer | 100.0% |  |
| `paper_id` | integer | 100.0% |  |
| `created_at` | timestamp without time zone | 100.0% |  |

### `authors` — 164,549 rows

Author name strings AS PUBLISHED. NOT disambiguated — one person may have several rows.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `name` | text | 100.0% |  |
| `wos_author_id` | text | 0.0% |  |
| `scopus_author_id` | text | 14.5% |  |
| `orcid` | text | 1.2% | ORCID iD where the source supplied one. |
| `created_at` | timestamp without time zone | 100.0% |  |

### `embedding_models` — 3 rows

Registry of embedding models used, with dimensions.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `model_key` | character varying | 100.0% |  |
| `model_name` | character varying | 100.0% |  |
| `full_name` | character varying | 100.0% |  |
| `model_id` | character varying | 66.7% |  |
| `version` | character varying | 66.7% |  |
| `dimension` | integer | 100.0% |  |
| `huggingface_url` | text | 66.7% |  |
| `paper_url` | text | 0.0% |  |
| `repository_url` | text | 0.0% |  |
| `documentation_url` | text | 0.0% |  |
| `description` | text | 66.7% |  |
| `provider` | character varying | 66.7% |  |
| `architecture` | character varying | 66.7% |  |
| `license` | character varying | 0.0% |  |
| `model_type` | character varying | 0.0% |  |
| `language_support` | ARRAY | 0.0% |  |
| `batch_size` | integer | 66.7% |  |
| `gpu_memory_gb` | numeric | 66.7% |  |
| `speed_tokens_per_sec` | integer | 0.0% |  |
| `max_sequence_length` | integer | 66.7% |  |
| `special_features` | jsonb | 100.0% |  |
| `created_at` | timestamp with time zone | 100.0% |  |
| `updated_at` | timestamp with time zone | 100.0% |  |

### `embedding_runs` — 2 rows

Provenance log of embedding runs.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `run_id` | uuid | 100.0% |  |
| `model_key` | character varying | 100.0% |  |
| `started_at` | timestamp with time zone | 100.0% |  |
| `completed_at` | timestamp with time zone | 0.0% |  |
| `status` | character varying | 100.0% |  |
| `total_documents` | integer | 100.0% |  |
| `documents_processed` | integer | 100.0% |  |
| `documents_failed` | integer | 100.0% |  |
| `chunks_created` | integer | 100.0% |  |
| `embeddings_generated` | integer | 100.0% |  |
| `processing_time_seconds` | numeric | 0.0% |  |
| `tokens_processed` | bigint | 0.0% |  |
| `avg_processing_speed` | numeric | 0.0% |  |
| `peak_memory_usage_mb` | integer | 0.0% |  |
| `error_message` | text | 0.0% |  |
| `failed_document_ids` | ARRAY | 0.0% |  |
| `metadata` | jsonb | 100.0% |  |
| `configuration` | jsonb | 100.0% |  |
| `created_at` | timestamp with time zone | 100.0% |  |
| `updated_at` | timestamp with time zone | 100.0% |  |

### `journals` — 91 rows

The 91 disciplinary social work journals (the population list).

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `name` | text | 100.0% |  |
| `publisher` | text | 73.6% |  |
| `created_at` | timestamp without time zone | 100.0% |  |
| `issn_print` | character varying | 4.4% |  |
| `issn_online` | character varying | 7.7% |  |
| `url` | text | 7.7% |  |
| `status` | character varying | 12.1% |  |
| `notes` | text | 12.1% |  |

### `organizations` — 34,967 rows

Institutional affiliations as reported by sources (not normalized).

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% |  |
| `name` | text | 100.0% |  |
| `wos_org_id` | text | 0.0% |  |
| `scopus_affil_id` | text | 50.0% |  |
| `created_at` | timestamp without time zone | 100.0% |  |

### `paper_authors` — 241,766 rows

Authorship: links papers to authors with byline order.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `paper_id` | integer | 100.0% |  |
| `author_id` | integer | 100.0% |  |
| `position` | integer | 100.0% | Byline position; 1 = first author. |
| `is_corresponding` | boolean | 100.0% | Corresponding-author flag where known. |
| `created_at` | timestamp without time zone | 100.0% |  |

### `papers` — 110,618 rows

One row per journal article. The primary table.

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `id` | integer | 100.0% | Internal article identifier (stable within this database). |
| `doi` | text | 76.1% | Digital Object Identifier — permanent link to the article (https://doi.org/<doi>). |
| `title` | text | 100.0% | Article title as published. |
| `abstract` | text | 61.5% | Full abstract where available; NULL when never digitized. |
| `publication_year` | integer | 100.0% | Year of publication. 1989+ = the SWRD proper; pre-1989 = Supplement (incomplete). |
| `journal_id` | integer | 100.0% | Foreign key to journals.id. |
| `document_type` | text | 97.2% | Source-reported document type (article, review, etc.). |
| `data_source` | text | 100.0% | Which harvest supplied the record (WoS, Scopus, RDS = original SWRD 1.0, etc.). Messy vocabulary — do not treat as clean categories. |
| `wos_uid` | text | 68.2% |  |
| `scopus_eid` | text | 16.5% |  |
| `open_access` | boolean | 98.8% | Whether the article is open access (source-reported). |
| `volume` | text | 10.8% |  |
| `issue` | text | 10.8% |  |
| `pages` | text | 10.3% |  |
| `created_at` | timestamp without time zone | 100.0% |  |
| `updated_at` | timestamp without time zone | 100.0% |  |
| `publisher` | text | 28.1% |  |
| `crossref_updated_at` | timestamp with time zone | 46.9% |  |
| `author_count` | integer | 28.1% |  |
| `is_scientific` | boolean | 61.5% | SLM classification: original research contribution vs editorial/book review/letter. Only set where an abstract exists. |
| `is_empirical` | boolean | 59.0% | SLM classification: reports collection/analysis of original data. Subset of is_scientific. |
| `research_method` | text | 33.8% | SLM classification of empirical articles. Exact values below — note capitalization. |
| `stage_01_confidence` | text | 61.5% |  |
| `stage_02_confidence` | text | 59.0% |  |
| `stage_05_confidence` | text | 33.8% |  |
| `stage_01_justification` | text | 61.5% |  |
| `stage_02_justification` | text | 59.0% |  |
| `stage_05_justification` | text | 33.8% |  |
| `classification_timestamp` | timestamp with time zone | 61.5% |  |
| `classification_version` | text | 61.5% |  |
| `fts` | tsvector | 100.0% |  |

### `title_abstract_embeddings` — 110,618 rows

One 768-dim meaning vector per paper (embeddinggemma:300m over 'title: {t} | text: {abstract}').

| Column | Type | Filled | Meaning |
|---|---|---|---|
| `paper_id` | integer | 100.0% |  |
| `embedding` | vector(768) | 100.0% |  |
| `created_at` | timestamp without time zone | 100.0% |  |
| `model` | text | 100.0% |  |

## Value vocabularies (exact values — match capitalization)

### `papers.research_method`

| Value | Count |
|---|---|
| `Quantitative` | 19,530 |
| `Qualitative` | 15,164 |
| `Mixed-Methods` | 1,970 |
| `Review` | 706 |

### `papers.document_type`

*58 distinct values — top 25 shown; treat this field as messy free text, not clean categories.*

| Value | Count |
|---|---|
| `Article` | 33,105 |
| `journal-article` | 31,166 |
| `Book Review` | 15,036 |
| `Journal Article` | 14,429 |
| `fetch_failed` | 3,600 |
| `Editorial Material` | 2,641 |
| `Letter` | 1,390 |
| `Article; Early Access` | 1,239 |
| `Review` | 1,077 |
| `Note` | 905 |
| `Article; Proceedings Paper` | 822 |
| `Editorial` | 491 |
| `Meeting Abstract` | 227 |
| `Book Review; Early Access` | 194 |
| `Abstract of Published Item` | 171 |
| `Correction` | 137 |
| `Feature` | 119 |
| `Article , Report` | 98 |
| `General Information` | 77 |
| `PERIODICAL` | 67 |
| `Conference Paper` | 62 |
| `Poetry` | 58 |
| `Biographical-Item` | 48 |
| `Correction, Addition` | 32 |
| `Discussion` | 29 |

### `papers.data_source`

*26 distinct values — top 25 shown; treat this field as messy free text, not clean categories.*

| Value | Count |
|---|---|
| `WoS` | 75,418 |
| `Scopus` | 17,496 |
| `RDS` | 4,500 |
| `Digital Commons` | 2,772 |
| `MISC.csv` | 2,330 |
| `DOAJ` | 1,625 |
| `REFL.csv` | 1,343 |
| `Affilia.csv` | 1,284 |
| `DOAJ_OAI_PMH` | 1,211 |
| `Manual Impor` | 708 |
| `Sociological Abstracts` | 496 |
| `JSWVE.csv` | 428 |
| `Sociological Abstracts, Sociology Database` | 363 |
| `Education Research Index, Sociological Abstracts, Sociology Database` | 147 |
| `Sociological Abstracts, Sociological Abstracts, Sociology Database` | 140 |
| `CSW` | 103 |
| `Education Research Index, ERIC, Sociological Abstracts` | 67 |
| `Education Research Index, ERIC, Education Research Index, Sociological Abstracts, Sociology Database` | 59 |
| `misc_import` | 46 |
| `ASW.csv` | 37 |
| `Education Research Index, Sociological Abstracts, Sociology Database, Sociological Abstracts` | 16 |
| `APSW-OJS` | 13 |
| `Education Research Index, ERIC` | 9 |
| `Education Research Index, ERIC, Education Research Index, Sociological Abstracts, Sociology Database, Sociological Abstracts` | 5 |
| `Education Research Index, ERIC, PTSDpubs` | 1 |

## Views (precomputed answers)

| View | What it answers |
|---|---|
| `author_publication_stats` |  |
| `database_info` |  |
| `database_summary` |  |
| `organization_collaborations` |  |
| `papers_with_journals` |  |
| `publication_trends` |  |
| `swrd_papers` | The SWRD (primary database): article records 1989-2025, per Perron, Victor, & Qi (2026), doi:10.1177/10497315261416833. |
| `swrd_supplement_papers` | SWRD Supplement: historical records 1920-1988; much less complete; retained for historical exploration. |

## Functions (callable via SQL or the REST rpc endpoint)

| Function | Signature |
|---|---|
| `run_sql` | (query text) |
| `search_papers_hybrid` | (query_text text, query_embedding vector, match_count integer DEFAULT 10, rrf_k integer DEFAULT 60, min_year integer DEFAULT 1920, max_year integer DEFAULT 2026) |
| `search_papers_keyword` | (query_text text, match_count integer DEFAULT 10, min_year integer DEFAULT 1920, max_year integer DEFAULT 2026) |
| `search_papers_semantic` | (query_embedding vector, match_count integer DEFAULT 10, min_year integer DEFAULT 1920, max_year integer DEFAULT 2026) |
| `update_updated_at_column` | () |

## Join map

- `author_affiliations.author_id` → `authors.id`
- `author_affiliations.organization_id` → `organizations.id`
- `author_affiliations.paper_id` → `papers.id`
- `embedding_runs.model_key` → `embedding_models.model_key`
- `paper_authors.author_id` → `authors.id`
- `paper_authors.paper_id` → `papers.id`
- `papers.journal_id` → `journals.id`
- `title_abstract_embeddings.paper_id` → `papers.id`

