# QC #1 — repairing the DOI column

Recovers the real DOI for every SWRD record whose `doi` field holds something that
is not a DOI. Addresses the largest part of
[issue #1](https://github.com/beperron/SocialWork-MetaData/issues/1).

**Read-only.** The project API rejects writes, so nothing here can modify the
database. The output is a reviewed patch set plus the SQL to apply it, for step 1 of
the maintainer procedure in [`docs/DATA_CHANGELOG.md`](../../docs/DATA_CHANGELOG.md).

## The problem

3,556 of 69,912 populated `doi` values in the 1989+ corpus (5.1%) are not DOIs. A
populated-but-wrong identifier is worse than a null one: it satisfies "has a DOI"
while breaking every lookup, and it misleads any dedup rule that prefers the row
carrying an identifier.

It is not scattered rot. Each pattern comes from exactly one ingest, and the whole
problem sits in nine journals:

| Pattern | Rows | `data_source` | Journals |
|---|---:|---|---|
| `oai:scholarworks.wmich.edu:jssw-NNNN` | 2,002 | Digital Commons | 1 |
| `dc/<hash>` | 1,554 | DOAJ | 8 |

## Results

| | Recovered | Held for review |
|---|---:|---:|
| `oai:` (deterministic rule, all years) | **2,769** of 2,772 | 3 |
| `dc/` (Crossref search, 1989+) | **846** of 1,554 | 708 |
| Less collisions with rows already in the column | −216 | +216 |
| **Proposed** | **3,399** | **927** |

Applying takes malformed values from **4,326 to 927** (all years), and from 3,556 to
927 in the 1989+ corpus — every pre-1989 Supplement row is repaired.

Sampled precision, 60 per stratum, seed `20260802`, 95% Wilson intervals: tier A
60/60 [94.0–100], tier B/ISSN 60/60 [94.0–100], tier B/name 60/60 [94.0–100].

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
required** — ISSN where the journal has one, journal name otherwise. That guard
rejected 27 records outright. The earlier pilot proved it is load-bearing: without it,
searches match book reviews of the same work in other journals.

## What the review queue contains

| Verdict | n | Meaning |
|---|---:|---|
| `weak_title` | 358 | Best candidate below 0.90 similarity |
| `no_candidate` | 174 | Crossref returned nothing usable |
| `rejected_wrong_journal` | 27 | Title matched, journal did not — the guard working |
| `recovered` (collision) | 20 | See below |
| `candidate_not_in_crossref` | 3 | Rule produced a DOI Crossref does not hold |
| `journal_unverified` | 1 | Crossref record carries no journal |

**The 20 collisions are a separate defect.** Ten DOIs were each proposed for two
records — because those really are the same article ingested twice under different
`dc/` hashes, sometimes with a subtitle on one copy and a different year on the other
(online vs print). Assigning one DOI to both would create duplicate DOIs. They are
held back and belong to the duplicate-consolidation job, not this one.

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
python3 qc/doi/code/01_extract.py     # asserts the population is still 3,556 / 2,002 / 1,554 / 9 journals
python3 qc/doi/code/02_recover.py     # ~25 min uncached; every response cached, so re-runs are free
python3 qc/doi/code/03_audit.py       # the gate — per-tier precision
python3 qc/doi/code/04_apply_sql.py   # patch set + SQL
```

Stdlib only, no install. `01_extract.py` refuses to continue if the population has
moved, because the recovery rules were validated against this one.

## Applying

```bash
psql "$TGT" -v ON_ERROR_STOP=1 -f qc/doi/data/apply_doi_corrections.sql
```

Every `UPDATE` matches on the current broken value, so the file is idempotent and a row
that changed since generation is skipped rather than overwritten. The transaction ends
by asserting that malformed values fell by exactly 2,973, and rolls back otherwise.

Afterwards, re-run the new `SWRD: DOI SYNTAX VALIDITY` block in
[`migration/04_health_check_swrd.sql`](../../migration/04_health_check_swrd.sql) —
`malformed` should read 583.

## Files

```
code/01_extract.py    pull the malformed rows, assert the expected shape
code/02_recover.py    rule + search recovery, tiered verdicts with evidence
code/03_audit.py      stratified precision check, fixed seed
code/04_apply_sql.py  patch set, review queue, and idempotent SQL
data/malformed.json               the 3,556 affected rows
data/recovery.json                one verdict per row, with full evidence
data/audit.json                   the precision check and its sample
data/proposed_doi_corrections.csv the patch set
data/apply_doi_corrections.sql    the UPDATE statements
data/review_queue.csv             the 583 not proposed, and why
cache/                            gzipped Crossref responses (gitignored)
```

Shared Crossref client is [`qc/crossref/code/swrdqc.py`](../crossref/code/swrdqc.py).

## Out of scope

Journal ISSN backfill, journal misattribution, duplicate consolidation, author
disambiguation, `data_source` normalization. Each is its own job.
