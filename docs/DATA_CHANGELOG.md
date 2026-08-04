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

- **New: `swrd.author_name_enrichment` — derived fuller names for 26,313
  initials-only authors** (ships in v1.4 as `swrd_author_name_enrichment.csv`).
  `THYER, BA` gains the annotation `Thyer, Bruce A.`, recovered from the
  author's **own papers'** Crossref records and admitted only when every
  checkable paper agrees on the identical rendering — unanimity is a CHECK
  constraint on the table, not a convention. `swrd.authors` is **not written**:
  the "names as published" guarantee is unchanged, this is an annotation, and
  it is not disambiguation — two ids sharing a `full_name` are not thereby one
  person, and the table must never be used to merge author ids.

  Census over all 164,549 author rows: 50,393 initials-only forms (the planning
  figure of 24,007 was scoped to 1989+/valid-DOI authors and missed two name
  orders); 26,313 enriched, 24,080 refused across 12 itemised classes in
  `qc/authors/data/enrich_initials_queue.csv` — largest: no DOI (9,929),
  orphaned rows (5,253), Crossref's own author list truncated (2,992),
  Crossref itself initials-only (2,390). Two rows were refused because
  **Crossref's own deposit carries U+FFFD encoding damage** (`Ren� C.` at the
  registry itself) — verbatim is the rule, but shipping a replacement
  character is shipping garbage.

  Verified: 18-case selftest including the three name orders and the historical
  parser traps; OpenAlex census of all 26,313 (97.4% confirmed outright, every
  apparent contradiction adjudicated — 53/54 reproduce exactly at live
  Crossref, the 54th is a non-breaking space our normalisation correctly
  collapses); 25 live-registry refetches bypassing the cache (25/25);
  a seeded 20-row sample from the weakest stratum (single-paper rows, 81% of
  the table) checked against Semantic Scholar (20/20 consistent, 0
  contradictions); and a mechanical all-rows check that every `full_name`
  reproduces its `name_as_published`'s surname and initials (26,313/26,313).

  Rollback is `drop table` — the first change in this project that destroys
  nothing observed, which is also why there is no `swrd_archive` entry for it.
  The export gains the CSV with `EXPECTED = 26,313`, a new guard on
  `swrd_authors` itself (164,549), and a freshness preflight that refuses to
  package if any `name_as_published` has drifted from the live name.
  Regenerated wholesale each release, never patched.

- **99 surnames truncated by the legacy WoS ingest restored** (will ship in
  v1.4): `SCHUERMA.JR` → `Schuerman, John R.`, `KEITHLUC.A` → `Keith-Lucas,
  Alan`. The ingest cut surnames at an 8-character field limit — not a
  published form, so the stored value is overwritten, the same reasoning as the
  mojibake repair. Each restoration comes from the author's **own paper's**
  Crossref record: family name extends the stem (compared letters-only, which
  is how hyphenated and apostrophe surnames were hiding), every initial agrees
  in order, exactly one candidate on the paper, and all of a row's papers
  agree. Verified 99/99 against live Crossref and 10/10 against OpenAlex by an
  independent review that re-implemented the matching rule from scratch.

  Three qualifications, stated rather than buried:
  - The name-quality census did not classify this form, so census totals are
    unchanged by this fix by design; it now carries a `format_wos_truncated`
    category. Before/after verification is the regex count
    (`name ~ '^[A-Z]{8}\.[A-Z]{1,3}$'`): **200 before, 101 after**, the
    residue itemised with reasons in `qc/authors/data/truncated_queue.csv`
    (89 papers with no DOI, 9 orphaned rows, 2 ambiguous, 1 where the row's
    papers name two different people — Edward vs Eliyahu Rosenheim).
  - For 2 of the 99 (`RABINOVI.H`, `ROSENFEL.HM`) the evidence DOI is a
    bundled "Book reviews" section record with no per-item title; identity
    rests on journal + year + unique stem/initials match, one notch weaker
    than the title-corroborated 97.
  - 18 of the repaired names now visibly duplicate names on other author rows
    (`Garfinkel, Irwin` appears on 5). Expected and corroborating under the
    no-merge policy — no linkage was changed, and the sibling *misspelled*
    truncation `GARFINKL.I` remains queued. Zero same-paper duplicate credits
    were created (verified before applying).

  Prior values in `swrd_archive.renamed_authors_v1_4` (kind `wos_truncated`);
  rollback in `qc/authors/data/rollback_truncated.sql`, round-trip proven.

- **44 corrupted author-name strings repaired** (will ship in v1.4): 27 mojibake
  decodes (`Vesna LeskoÅ¡ek` → `Vesna Leskošek`), 4 footnote digits
  (`Eybalin1` → `Eybalin`), 6 trailing commas, 7 doubled spaces. No linkage
  changes — `paper_authors` joins on `author_id`. Prior values archived in
  `swrd_archive.renamed_authors_v1_4`; rollback in
  `qc/authors/data/rollback_strings.sql`. Four rows deliberately left: two `7`
  rows (spurious links, issue #6 class), one fax/email block on a no-DOI record,
  one broken entity — all need evidence, not string transforms. Verified false
  positives left untouched: `Coldon, Lawrence, 3rd` (generational suffix) and
  `Zuraini J.@.O.` (Malaysian alias convention, confirmed at Crossref).
  Census: `qc/authors/code/02_name_quality.py`.

## Versions

### v1.3 — August 2026 (current)

**Journal attribution: the five remaining ISSN-backed clusters.** 1,517 articles
moved to the journal their DOI's registry record names. No article is added,
removed, or merged — `swrd_articles` remains **62,602**.

| fix | records | from → to |
|---|---:|---|
| `fix_bjsw` | 216 | British J. Social Work → Asia Pacific J. of Social Work and Development |
| `fix_rswp` | 318 | Research on Social Work Practice → Child & Family Social Work |
| `fix_scsw` | 318 | Studies in Clinical Social Work → Asian Social Work and Policy Review |
| `fix_jswp` | 181 | J. of Social Work Practice → The J. of Sociology & Social Welfare |
| `fix_admin` | 484 | Administration in Social Work → J. of Religion & Spirituality in Social Work |

Per-record gates (each independently able to refuse): Crossref ISSN is the
target's and not the source's, container-title carries the target's tokens, and
the DOI's own publisher code agrees. Four clusters are fully prefix-separable
(e.g. moving `10.1080` vs staying `10.1093` on all 4,386 correctly-filed BJSW
records). The fifth is Taylor & Francis on both sides, so the Haworth series code
decides: `J377` is Religion & Spirituality, `J147` (Admin's own, 520 records) is
forbidden — the same proof shape as v1.2's GLSS fix.

**A circularity resolved.** Administration in Social Work was the one journal
whose ISSN failed its own majority vote (70%, below the 0.80 bar) — *because of
this contamination*: 484 of its 1,629 DOI'd records were another journal's.
Post-fix the vote is **0.989**, and the ISSN graduates from
`qc/journals/data/issn_review_queue.csv`.

#### How it was verified

Four independent routes, before applying:

- **Gates** over cached Crossref — all 1,517 pass all four; zero rejections
- **OpenAlex census** of all 1,517 (not a sample) — 1,512/1,512 resolvable
  confirm the target venue; the 2 apparent exceptions were OpenAlex's own venue
  errors, confirmed as the target at the DOI registry directly
- **Structural census** — every moving DOI embeds the target journal's publisher
  code in its own string (T&F 8-digit codes, Wiley `1365-2206`/`aswp`/`cfs`,
  WMU's literal `0191-5096`, Haworth `J377`); all 1,517 stems accounted for
- **Live Crossref sample** — 25 movers fetched fresh from api.crossref.org,
  bypassing the cache: 25/25 return the target's container and ISSN, closing the
  corrupt-DOI-field loophole

Premise checks: no ISSN-confirmed staying record carries a moving signal, and
zero source-ISSN records sit under any target — the error runs one way in every
cluster. An 18-agent adversarial review returned **apply as is**, the first wave
to pass with no required changes; its independent live-registry sample and
whole-DB DOI-pattern census both came back clean.

#### Deliberately not changed (the next queue)

- 5 Religion & Spirituality records under journal 232, and 10 more strays found
  by the completeness sweep
- 15 *Family Journal* records under Research on Social Work Practice; 1 stray
  under J. of Social Work Practice
- 14 GLSS records under J. Gerontological Social Work with `10.1080`-era DOIs,
  outside the v1.2 series-code fix — surfaced by the new health-check block
- *Social Work with Groups* → J. Ethnic & Cultural Diversity (120 records,
  shared-prefix, needs its own proof); journal rows 232/263 merge; out-of-set
  containers

The health check now carries a `SWRD: JOURNAL ATTRIBUTION` block flagging
journals whose records carry a rare DOI publisher-code — the check that would
have surfaced all of these clusters from the start.

#### Reversibility

Prior state archived in the unlinked `swrd_archive.reassigned_papers_v1_3`
(1,517 rows, populated in the same transaction as each fix). Rollback scripts in
`qc/journals/data/rollback_*.sql`; round-trip proven exact on the largest
cluster before applying. Report 04 was re-run and is unchanged (0 of 213 values).

| Archive | Contents |
|---|---|
| `swrd-database-csv-v1.3.zip` | As v1.2, with journal attribution corrected for a further 1,517 articles |
| `sswr-database-csv-v1.3.zip` | Unchanged from v1.0 |

### v1.2 — August 2026

**Journal attribution and duplicate authorship credits.** No article is added,
removed, or merged: `swrd.papers` is untouched, so `swrd_articles` remains
**62,602** and the figure cited in Perron, Victor & Qi (2026) is unaffected.

| # | correction | scope | issue |
|---|---|---|---|
| 1 | 801 *Affilia* articles reassigned off *Social Work* | `journal_id` | [#2](https://github.com/beperron/SocialWork-MetaData/issues/2) |
| 2 | 393 *J. Gay & Lesbian Social Services* articles reassigned off *J. Gerontological Social Work* | `journal_id` | [#2](https://github.com/beperron/SocialWork-MetaData/issues/2) |
| 3 | 7,756 duplicate authorship credits removed, 509 corresponding-author flags merged onto the surviving credit | `paper_authors` | [#6](https://github.com/beperron/SocialWork-MetaData/issues/6) |

| | before | after |
|---|---:|---:|
| `paper_authors` links | 241,766 | **234,010** |
| distinct authors credited | 137,659 | **133,211** |
| corresponding-author links | 31,727 | **29,204** |
| papers *with* a corresponding author | 25,621 | 25,621 |
| articles (`swrd_articles`) | 62,602 | 62,602 |

#### 1 — Affilia (801 records)

Articles filed under *Social Work* (id 1) moved to *Affilia-Feminist Inquiry in
Social Work* (id 17): Social Work 8,987 → 8,186, Affilia 1,932 → 2,733.

Six independent signals agreed on all 801: Crossref ISSN `0886-1099`/`1552-3020`
(corroborated 120/120 by Affilia's own correctly-filed articles), container-title
"Affilia", and DOI prefix `10.1177` — disjoint from *Social Work*'s `10.1093`.
1,440 Affilia-ISSN records were already filed correctly and no *Social Work*
record sat under Affilia, so the error ran one way only.

Title was deliberately **not** a gate. Eleven records differ from Crossref's title
(corrigenda, editorials, multi-part titles truncated on one side), and none of
that bears on which journal an article is in.

#### 2 — Journal of Gay & Lesbian Social Services (393 records)

Both journals published through Haworth, so the DOI *prefix* cannot separate them —
`10.1300` appears on both sides. The Haworth **series code** can, with no overlap:
`10.1300/J041` is J. Gay & Lesbian Social Services (all 393) and `10.1300/J083` is
J. Gerontological Social Work (1,264, all left in place). Corroborated by ISSN
`1053-8720`/`1540-4056` and a 1994–2006 span matching that journal's own era.

#### 3 — Duplicate authorship credits (7,756 removed)

One person credited more than once on the same paper — the same name at the same
byline position, from repeated ingests. Crossref did **not** supply the author
lists: it confirmed each DOI identifies its article and vetoed merges, nothing
more. Trusting it would have deleted real co-authors, because its author lists are
routinely truncated to the first author on older deposits (paper 19724 lists
"T. Booth" for an article by Tim Booth, Wendy Booth and David McConnell).

The corresponding-author flag is **merged, not discarded**: 3,032 deleted rows
carried it, and without the merge 502 papers would have gone from asserting a
corresponding author to asserting none.

**This reduces the defect, it does not eliminate it.** 4,855 of 9,895 corpus-wide
duplicate groups are corrected — the rest fail the DOI-confirmation gate. A
further 107 in-scope groups were explicitly refused by a gate rather than missed,
and non-Latin-script names are outside the fix entirely.

#### Deliberately not changed

- **Orphaned author rows.** Deduping a credit usually orphans the redundant
  `swrd.authors` row; authors-without-papers rose from 26,890 to 31,338. A raw
  `count(*) from swrd.authors` therefore overstates credited authors by more than
  before. Cleaning these is a separate job and was not bundled here.
- **The other misattribution clusters** in issue #2, and the three remaining
  authorship defects in issue #6 (split names, reference lists ingested as
  authors, colliding positions).

#### How it was verified

- **Census, not sample.** All 4,855 merge groups checked against **OpenAlex**,
  which runs its own author disambiguation: 98.3% confirmed as exactly one person,
  and every apparent contradiction resolved as an artifact of the check.
- **Publisher bylines.** 16 groups drawn at random from the 1,228 where the two
  renderings genuinely differ, read off each journal's own article page: 16/16
  correct. 74.7% of all groups merge strings identical modulo punctuation and need
  no external source at all.
- **Adversarial review.** 18 agents across five lenses with two refutation
  skeptics per finding; 19 findings, 5 survived, 2 had real data effect. Both were
  fixed before applying: the corresponding-author loss above, and four merges that
  conflated two people through a given-name fragment.
- **Round trip.** Apply → rollback → set difference in both directions: 0 rows
  lost, 0 altered, identical on all five columns including `created_at`.

Full method: [`qc/authors/README.md`](../qc/authors/README.md),
[`qc/authors/VERIFICATION.md`](../qc/authors/VERIFICATION.md),
[`qc/journals/`](../qc/journals/).

#### Reversibility

The prior state is preserved **inside the database** in the unlinked
`swrd_archive` schema — 7,756 removed credits with their original `created_at`,
509 promoted flags with their prior value, and 1,194 reassigned articles with
their original `journal_id`. No foreign keys, triggers, or views reference these
tables, and they are not exported.
[`qc/archive/restore_from_archive_v1_2.sql`](../qc/archive/restore_from_archive_v1_2.sql)
reverses the release reading only those tables — no file, no git object — and
asserts its way back to 241,766 links and 1,194 articles.

| Archive | Contents |
|---|---|
| `swrd-database-csv-v1.2.zip` | As v1.1, with journal attribution corrected for 1,194 articles and 7,756 duplicate authorship credits removed |
| `sswr-database-csv-v1.2.zip` | Unchanged from v1.0 |

### v1.1 — August 2026

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
