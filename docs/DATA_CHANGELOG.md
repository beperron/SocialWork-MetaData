# Data Changelog

Each data release is a numbered, immutable snapshot published on the
[releases page](https://github.com/beperron/SocialWork-MetaData/releases).
Filenames carry the version (`swrd-database-csv-v1.0.zip`), so a downloaded
file always identifies its release. Corrections accepted through
[data-quality issues](https://github.com/beperron/SocialWork-MetaData/issues?q=label%3Adata-quality)
are applied to the live database and shipped in the next numbered release;
prior releases are never modified or removed.

## Releasing a new version (maintainer procedure)

1. Apply accepted corrections to the live database (each linked to its
   data-quality issue).
2. Export: `python migration/10_export_release_csv.py v1.x` — the script
   validates row-count invariants and writes `dist/*-v1.x.zip` with a
   versioned README inside each archive.
3. Publish: `gh release create data-v1.x dist/*-v1.x.zip --title "Data Release v1.x — <Month Year>"`
   with notes listing the changes and closing the underlying issues.
4. Update the version badge in `index.html` (Download section), the
   "Current data release" line in `README.md`, and add an entry below.

## Versions

### v1.0 — July 2026 (current)

Initial public release.

| Archive | Contents |
|---|---|
| `swrd-database-csv-v1.0.zip` | The SWRD: 62,602-article research corpus (1989–2025) exactly as described in Perron, Victor, & Qi (2026); additional 1989–2025 records; the 1920–1988 historical Supplement; journals, authors, authorship links, organizations, affiliations |
| `sswr-database-csv-v1.0.zip` | The SSWR Conference Database: all 23,793 presentations (2005–2026) with abstracts and methodology labels; 21,209 disambiguated author identities; authorship links with normalized institutions and countries |

Known imperfections carried in v1.0 (candidates for v1.1):
- `swrd_journals.csv` holds 91 rows for the 88-journal population: two rows
  contain no articles, and one journal appears under two ids
  ("Sexual and Gender Diversity in Social Services", ids 232 and 263).
- SWRD author names are as published (not disambiguated).
- **3,556 `doi` values (5.1% of populated) are not DOIs** — OAI identifiers from
  the Digital Commons ingest and internal `dc/` hashes from DOAJ, across nine
  journals. Repair prepared in [`qc/doi/`](../qc/doi/README.md); see
  [issue #1](https://github.com/beperron/SocialWork-MetaData/issues/1).
- 84 of 91 journals carry no ISSN, and ISSNs are not currently exported.

## Prepared for v1.1 (not yet applied)

### DOI column repair — 2,973 corrections

Recovers the real DOI for records whose `doi` field held a non-DOI identifier.
Method, precision, and the review queue are documented in
[`qc/doi/README.md`](../qc/doi/README.md); the patch set is
`qc/doi/data/proposed_doi_corrections.csv` and the statements are
`qc/doi/data/apply_doi_corrections.sql`.

| | |
|---|---|
| Affected before | 3,556 (2,002 `oai:`, 1,554 `dc/`) |
| Corrections proposed | 2,973 (1,999 rule-derived, 974 search-recovered) |
| Remaining after | 583, itemised in `qc/doi/data/review_queue.csv` |
| Precision | 120/120 sampled, seed `20260802` |

Applying:

```bash
psql "$TGT" -v ON_ERROR_STOP=1 -f qc/doi/data/apply_doi_corrections.sql
```

The file is idempotent — each `UPDATE` matches on the current broken value — and
the transaction asserts the malformed count fell by exactly 2,973 before
committing. Afterwards, re-run `migration/04_health_check_swrd.sql` and confirm
the new `SWRD: DOI SYNTAX VALIDITY` block reports `malformed = 583`.

This changes field values only, so the `EXPECTED` row-count invariants in
`migration/10_export_release_csv.py` are unaffected and need no update.

Twenty records are deliberately excluded: ten DOIs were each proposed for two
records because those are the same article ingested twice under different `dc/`
hashes. Assigning one DOI to both would create duplicate DOIs. They belong to a
separate duplicate-consolidation job.
