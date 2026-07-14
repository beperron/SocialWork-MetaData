# Database Health Check Report (2026-07-14)

Data-quality review of the consolidated database (`kcffctxedcscvvposypb`). Raw output: `audit/health_sswr.txt`, `audit/health_swrd.txt`. Every issue below **also exists in the source databases** (aggregates matched exactly) — these are pre-existing data characteristics, not migration artifacts.

## sswr schema — healthy

| Check | Result | Assessment |
|---|---|---|
| Papers without authors | 2 of 23,793 | ✅ negligible |
| Orphaned paper_authors | 0 | ✅ |
| Unlinked author entities | 0 (100% linked to canonical authors) | ✅ |
| Orphaned html mappings | 13 (point at deleted paper ids) | ⚠ trivial cleanup candidate |
| Papers without an HTML source | 54 | ✅ known + documented in source repo |
| Duplicate (title, year) groups | 5 | ✅ negligible |
| Null rates | title/abstract/methodology/fts all 100% | ✅ excellent |
| Year range | 2005–2026, 0 out of range | ✅ |
| papers.author_count vs actual links | 0 mismatches | ✅ |
| Canonical-mapping FKs | 0 bad | ✅ |

**Verdict: production-quality.** The SSWR entity-resolution work holds up completely.

## swrd schema — clean structurally; known data-quality debt

| Check | Result | Assessment |
|---|---|---|
| Orphaned paper_authors / author_affiliations | 0 / 0 | ✅ perfect referential integrity |
| Duplicate DOIs / wos_uid / scopus_eid | 0 / 0 / 0 | ✅ hard-identifier dedup complete |
| Journal FKs | 0 null, 0 dangling | ✅ |
| Year range | 1920–2025, 0 out of range | ✅ |
| Citations | 0–1,675, none negative | ✅ |
| Papers without authors | 2,709 (2.4%) | ⚠ mostly imports without author metadata |
| Authors without any paper | 26,890 (16.3%) | ⚠ dead author rows left from dedup deletions |
| Papers with authors but no position-1 author | 482 | ⚠ ordering data lost/absent for these |
| Same (title, year) duplicate candidates | 1,375 groups | ⚠ fuzzy dupes beyond hard-ID dedup |
| Exact duplicate author name rows | 14,955 groups | ⚠ no entity resolution done on SWRD authors |
| DOI coverage | 76.1% | ℹ typical for this corpus mix |
| Abstract coverage | 61.5% | ℹ matches classification coverage |
| LLM classification coverage | 61.5% (68,074) | ℹ classified ⊆ has-abstract |
| `data_source` values | **26 distinct, messy** — 'Manual Impor' (truncated), '*.csv' filenames, comma-joined index lists | ⚠ top normalization candidate |

**Verdict: structurally sound, ready to use; carries known content-level debt from its assembly history.**

## Recommended SWRD cleanup roadmap (post-migration, at your pace)

1. **Normalize `data_source`** into a small controlled vocabulary (WoS, Scopus, RDS, DOAJ, Digital Commons, Journal Archive, Manual) — 26 → ~7 values; keep the raw value in a new `data_source_raw` column if provenance matters.
2. **Delete or flag the 26,890 authorless author rows** (they inflate author counts and slow joins; they're recoverable from the old project if ever needed).
3. **Author entity resolution** — 14,955 exact-name duplicate groups (plus near-misses). The SSWR project's canonical-mapping approach (authors.is_canonical + author_canonical_mapping) is a proven template to port.
4. **Review the 1,375 title+year duplicate groups** — likely genuine fuzzy duplicates surviving hard-ID dedup.
5. **Investigate the 482 papers with no first author** — ordering may be recoverable from source records in the old project.
6. Optional: backfill abstracts for the 38.5% without (Crossref/OpenAlex), which also unlocks classification and embedding for those papers.

None of these block re-embedding or app rebuilding.
