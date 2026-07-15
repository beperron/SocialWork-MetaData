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
