# QC #1 — repairing the DOI column

Recovers the real DOI for every SWRD record whose `doi` field holds something that
is not a DOI. Addresses the largest part of
[issue #1](https://github.com/beperron/SocialWork-MetaData/issues/1).

**Read-only.** The project API rejects writes, so nothing here can modify the
database. The output is a reviewed patch set plus the SQL to apply it, for step 1 of
the maintainer procedure in [`docs/DATA_CHANGELOG.md`](../../docs/DATA_CHANGELOG.md).

## The problem

4,326 `doi` values are not DOIs — 3,556 in the 1989+ corpus (5.1% of populated
values) and 770 more in the pre-1989 Supplement. A
populated-but-wrong identifier is worse than a null one: it satisfies "has a DOI"
while breaking every lookup, and it misleads any dedup rule that prefers the row
carrying an identifier.

It is not scattered rot. Each pattern comes from exactly one ingest, and the whole
problem sits in nine journals:

| Pattern | Rows | `data_source` | Journals |
|---|---:|---|---|
| `oai:scholarworks.wmich.edu:jssw-NNNN` | 2,772 (2,002 in 1989+, 770 older) | Digital Commons | 1 |
| `dc/<hash>` | 1,554 | DOAJ | 8 |

The OAI half is taken across **all years** because its rule is validated against the
publisher's own OAI-PMH feed (3,056 records, zero exceptions). The `dc/` half stays
1989+ because search recovery is weaker and the Supplement is documented as
substantially incomplete.

## Results

| | Recovered | Held for review |
|---|---:|---:|
| `oai:` (deterministic rule, all years) | **2,769** of 2,772 | 3 |
| `dc/` (Crossref search, 1989+) | **846** of 1,554 | 708 |
| Less collisions with rows already in the column | −216 | +216 |
| **Proposed** | **3,399** | **927** |

Applying takes malformed values from **4,326 to 927** (all years), and from 3,556 to
927 in the 1989+ corpus — every pre-1989 Supplement row is repaired.

Every proposal — all 3,615, not a sample — was re-checked against Crossref on signals the recovery step does not use, and all 3,615 confirm: tier A 2,769/2,769, tier B/ISSN 375/375, tier B/name 471/471.

The audit is run exhaustively rather than on a sample because the population is
small and the Crossref responses are cached, so there is no reason to estimate
something that can be measured.

> **An earlier version of this file reported "120/120 precision". That figure is
> retracted.** The audit that produced it re-applied the same two predicates that
> caused acceptance, so it could not fail. An adversarial review then found three
> wrong DOIs, one of them inside that very sample. See
> [`docs/QC_REVIEW_2026-08.md`](../../docs/QC_REVIEW_2026-08.md); the audit has been
> rebuilt on independent signals and now ships a self-test that fails the run if it
> confirms any of the three.

## How each half works

**`oai:` — deterministic.** The identifier embeds the article number that forms the
real DOI: `oai:scholarworks.wmich.edu:jssw-NNNN` → `10.15453/0191-5096.NNNN`. Still
confirmed against Crossref by title before being proposed, because a rule that is
right 100 times can be wrong the 101st. Three candidates are absent from Crossref and
went to the queue rather than being applied unverified.

**`dc/` — searched.** The hash is an internal ingest key and encodes nothing. Recovery
is a Crossref bibliographic search on title, year ±1, and **journal agreement is
required** — ISSN where the journal has one, journal name otherwise. Candidates are
filtered to journal-agreeing ones *before* ranking, ties break on author agreement
rather than API result order, and any pair of titles whose digit sequences differ is
rejected outright. The earlier pilot proved the journal guard is load-bearing: without
it, searches match book reviews of the same work in other journals.

## What the review queue contains

927 records are not proposed, each with a stated reason:

| Verdict | n | Meaning |
|---|---:|---|
| `weak_title` | 519 | Best candidate below 0.90 similarity |
| `duplicate_of_existing_row` | 212 | The DOI is right, but this row duplicates one SWRD already holds |
| `no_candidate` | 174 | Crossref returned nothing usable |
| `rejected_wrong_journal` | 8 | Title matched, journal did not — the guard working |
| `ambiguous_candidates` | 5 | Two journal-passing candidates within 0.02; refused rather than guessed |
| `collision_needs_review` | 4 | A *different* article already holds this DOI |
| `candidate_not_in_crossref` | 3 | Rule produced a DOI Crossref does not hold |
| `authors_disagree` | 1 | Both sides name authors and share none |
| `digits_conflict` | 1 | "Letter from the Editors (5)" vs "(7)" |

**The 212 duplicates are a separate defect.** The recovered DOI is correct; the *row*
is a redundant second ingest of an article SWRD already has. Each is queued with the
id of its sibling row so it can be merged rather than re-searched.

## Two bugs this work found and fixed

Both were in the shared helper library, and both would have quietly degraded evidence
rather than failing loudly:

1. **`swrd_surnames` assumed one name format.** It split on the comma only, so
   given-name-first strings came back as whole names (`richfurman`) and never matched
   a Crossref `family` field. Author overlap read as 0.0 for entire journals. Fixed to
   handle all three orderings present in SWRD; median overlap on confirmed matches went
   from 0.0 to 1.0.
2. **Journal comparison was order-sensitive.** *Global Social Work / Trabajo Social
   Global* and *Trabajo Social Global-Global Social Work* are the same bilingual title
   with the halves swapped, and 16 correct recoveries were being scored as journal
   disagreements. Journal matching now lives in one shared function
   (`swrdqc.journal_match`) used by both recovery and audit, with ISSN preferred and a
   token-set fallback.

The second bug is why the audit exists: it caught a systematic error that the recovery
step was confident about.

## Running it

```bash
python3 qc/doi/code/01_extract.py            # asserts 4,326 / 2,772 / 1,554 / 9 journals
python3 qc/doi/code/02_recover.py            # ~30 min uncached; responses cached, re-runs free
python3 qc/doi/code/03_audit.py --selftest   # the gate, plus its own test
python3 qc/doi/code/04_apply_sql.py          # preflight, patch set, queue, SQL
```

Stdlib only, no install. `01_extract.py` refuses to continue if the population has
moved, because the recovery rules were validated against this one.

## Applying

```bash
psql "$TGT" -v ON_ERROR_STOP=1 -f qc/doi/data/apply_doi_corrections.sql
```

Every `UPDATE` matches on the current broken value, so the file is idempotent and a row
that changed since generation is skipped rather than overwritten. The transaction ends
by asserting that malformed values fell by exactly 3,399, and rolls back otherwise.

Afterwards, re-run the `SWRD: DOI SYNTAX VALIDITY` block in
[`migration/04_health_check_swrd.sql`](../../migration/04_health_check_swrd.sql) —
`malformed` should read 927, and `duplicate_doi_groups` should still be 0.

## Files

```
code/01_extract.py    pull the malformed rows, assert the expected shape
code/02_recover.py    rule + search recovery, tiered verdicts with evidence
code/03_audit.py      independent precision check with a self-test
code/04_apply_sql.py  patch set, review queue, and idempotent SQL
data/malformed.json               the 4,326 affected rows
data/recovery.json                one verdict per row, with full evidence
data/audit.json                   the precision check and its sample
data/proposed_doi_corrections.csv the patch set
data/apply_doi_corrections.sql    the UPDATE statements
data/review_queue.csv             the 927 not proposed, and why
cache/                            gzipped Crossref responses (gitignored)
```

Shared Crossref client is [`qc/crossref/code/swrdqc.py`](../crossref/code/swrdqc.py).

## Out of scope

Journal ISSN backfill, journal misattribution, duplicate consolidation, author
disambiguation, `data_source` normalization. Each is its own job.
