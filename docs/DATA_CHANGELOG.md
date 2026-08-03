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

## Applied to the live database, not yet released

These corrections are **in the live database now** and will ship in v1.2. Anyone
working from the v1.1 download will not see them yet.

| # | fix | scope | issue |
|---|---|---|---|
| 1 | 801 *Affilia* articles reassigned off *Social Work* | `journal_id` | [#2](../../issues/2) |
| 2 | 393 *J. Gay & Lesbian Social Services* articles reassigned off *J. Gerontological Social Work* | `journal_id` | [#2](../../issues/2) |
| 3 | 7,756 duplicate authorship credits removed; 509 corresponding-author flags merged onto the surviving credit | `paper_authors` | [#6](../../issues/6) |

**No paper counts change.** `swrd.papers` is untouched by all three: fixes 1 and 2
move articles between journals that are both already in the set, and fix 3 touches
only `paper_authors`. The released figure of 62,602 articles is unaffected.

Verified after applying: `paper_authors` 241,766 → 234,010; distinct authors
credited 137,659 → 133,211; corresponding-author links 31,727 → 29,204 but papers
*with* a corresponding author unchanged at 25,621, which is the flag merge working.
Health check clean — 0 orphaned `paper_authors`, 0 null or dangling `journal_id`,
0 duplicate DOIs.

Two consequences to carry into the release:

- **Authors-without-papers rose from 26,890 to 31,338.** Deduping a credit usually
  orphans the redundant `swrd.authors` row. Harmless for counts, but it means a raw
  `count(*) from swrd.authors` overstates credited authors by more than it did.
  Cleaning those rows is a separate fix and is deliberately not bundled here.
- **Report 04 was regenerated and did not change.** Its co-authorship network and
  author statistics derive from `paper_authors`, so it was re-run against the
  corrected database: `stats.json` identical on all 174 values, `networks.json`
  byte-identical, same 37 and 38 nodes. Only **3** of the report's 705 DOIs are
  among the 2,885 deduped papers, and its conference half (1,238 of 2,034 records)
  has no `paper_authors` rows at all. The live page needs no republish.

Fix 3 covers roughly half the defect **by design**: 4,855 of the 9,895 corpus-wide
duplicate groups. The remainder fail the DOI-confirmation gate, and 107 in-scope
groups were explicitly refused by a gate rather than missed. The defect is reduced,
not eliminated. Non-Latin-script names (e.g. `炳光 甘`) are outside the fix entirely.

Rollbacks for all three are committed and were proven exact before applying:
`qc/journals/data/rollback_{affilia,glss}.sql` and
`qc/authors/data/rollback_credits.sql`.

Full reasoning, gate design and independent verification: `qc/authors/README.md`
and `qc/authors/VERIFICATION.md`.

## Versions

### v1.1 — August 2026 (current)

**Repairs the `doi` column. Nothing else changes** — no rows added, removed, or
merged, and no other field touched.

3,399 records held an identifier in `doi` that was not a DOI. A populated-but-wrong
identifier is worse than a null one: it satisfies "has a DOI" while breaking every
lookup, and it misleads any rule that prefers the row carrying an identifier.

| | Before | After |
|---|---:|---:|
| Malformed `doi` values, all years | 4,326 | **927** |
| — 1989+ corpus | 3,556 | 927 |
| — pre-1989 Supplement | 770 | 0 |
| Populated `doi` values that are valid DOIs | 94.9% | **99.0%** |

Corrections applied: **3,399** — 2,595 derived by rule and 804 recovered by
bibliographic search. 927 records remain malformed and are itemised with reasons in
[`qc/doi/data/review_queue.csv`](../qc/doi/data/review_queue.csv).

**Where the two populations came from.** Neither was scattered rot; each was one
ingest. 2,772 rows carried an OAI identifier from the Digital Commons ingest, all in
*The Journal of Sociology & Social Welfare*, and the identifier embeds the article
number that forms the DOI. 1,554 carried an internal `dc/` hash from the DOAJ ingest
across eight journals, where the hash encodes nothing and the DOI had to be recovered
by search.

#### Deliberately not changed

- **212 rows whose recovered DOI is already held by another row.** These are the same
  article ingested twice; the DOI is right and the *row* is redundant. Assigning it
  would violate the `unique_papers_doi` index. They belong to a duplicate-record job,
  and each is queued with the id of its sibling row.
- **4 rows where a different article already holds the recovered DOI**, including two
  where the *pre-existing* row appears to be the mis-assigned one. These need
  adjudication, not automation.
- **519 weak title matches, 174 with no Crossref candidate, 8 wrong-journal, 5
  ambiguous, 1 author disagreement, 1 digit conflict, 3 absent from Crossref.**
- **Coverage gap:** the recovery search filters on year ±1 and on the print ISSN,
  which suppresses candidates for publishers that bulk-registered a back catalogue or
  migrated platforms. Fixing this should recover a further slice of the 927 and is
  tracked separately; it was not changed here because doing so would have invalidated
  the review this release passed.

#### How it was verified

The patch was reviewed adversarially by seven independent lenses, with every finding
then given to a separate skeptic instructed to refute it: 39 findings raised, 23
survived. Two were disqualifying and both were fixed before this release:

1. **323 proposed DOIs collided with rows already in the column.** `swrd.papers`
   carries a partial unique index on `doi`, so the first collision would have rolled
   back the entire transaction and applied nothing. The generator now runs a
   preflight against the live column.
2. **The original audit was not independent.** It re-applied the same two predicates
   that caused acceptance, so it could not fail; its reported "120/120" was close to
   tautological and is **retracted**. Three wrong DOIs were found by external review,
   one of them inside that sample. The audit was rebuilt on signals the recovery step
   does not use — DOI prefix against the journal's registered prefixes, digit
   sequences, author-token overlap, year agreement — and now carries a self-test that
   feeds it those three known-wrong proposals and fails the run if it confirms any.

Every proposal — all 3,615, not a sample — was re-checked against Crossref on signals the recovery step does not use, and all 3,615 confirm: tier A 2,769/2,769, tier B/ISSN 375/375, tier B/name 471/471. This is verification, not sampling: the population is small
enough to check exhaustively, so it was. Full method and the complete finding list:
[`docs/QC_REVIEW_2026-08.md`](QC_REVIEW_2026-08.md) and
[`qc/doi/README.md`](../qc/doi/README.md).

#### Applying and checking

```bash
psql "$TGT" -v ON_ERROR_STOP=1 -f qc/doi/data/apply_doi_corrections.sql
psql "$TGT" -f migration/04_health_check_swrd.sql   # DOI SYNTAX VALIDITY -> malformed 927
```

Each `UPDATE` matches on the current broken value, so the file is idempotent and a row
that changed since generation is skipped rather than overwritten. The transaction
asserts the malformed count fell by exactly 3,399 and rolls back otherwise.

**Row-count invariants are unaffected.** `EXPECTED` in
`migration/10_export_release_csv.py` (`swrd_articles: 62602`,
`sswr_presentations: 23793`, `sswr_authors: 21209`) needs no update, because this
release changes field values and not the number of rows.

Closes [#1](https://github.com/beperron/SocialWork-MetaData/issues/1).

| Archive | Contents |
|---|---|
| `swrd-database-csv-v1.1.zip` | As v1.0, with the DOI column repaired |
| `sswr-database-csv-v1.1.zip` | Unchanged from v1.0 |

### v1.0 — July 2026

Initial public release.

| Archive | Contents |
|---|---|
| `swrd-database-csv-v1.0.zip` | The SWRD: 62,602-article research corpus (1989–2025) exactly as described in Perron, Victor, & Qi (2026); additional 1989–2025 records; the 1920–1988 historical Supplement; journals, authors, authorship links, organizations, affiliations |
| `sswr-database-csv-v1.0.zip` | The SSWR Conference Database: all 23,793 presentations (2005–2026) with abstracts and methodology labels; 21,209 disambiguated author identities; authorship links with normalized institutions and countries |

Known imperfections carried in v1.0, and their status:
- `swrd_journals.csv` holds 91 rows for the 88-journal population: two rows
  contain no articles, and one journal appears under two ids
  ("Sexual and Gender Diversity in Social Services", ids 232 and 263). *Open.*
- SWRD author names are as published (not disambiguated). *Open.*
- 3,556 `doi` values (5.1% of populated) are not DOIs. **Fixed in v1.1.**

Discovered during the v1.1 work and still open:
- **~3,571 records appear to be filed under the wrong journal.** Verifying the DOI
  column against Crossref found clusters with a consistent shape — 795 records under
  *Social Work* whose DOIs resolve to *Affilia*, 302 under *Journal of Social Work
  Education* resolving to *Journal of Applied Social Science*. Distinct from the 1,338
  cases explained by journal renames. Corrupts any per-journal count.
- **At least 212 duplicate rows**, where the same article is present twice from two
  ingests. Surfaced by the DOI collision preflight; the true total is likely higher.
- **84 of 91 journals carry no ISSN**, and ISSNs are not exported. This is why journal
  verification currently rests on name comparison for 67,124 of 69,349 records.
