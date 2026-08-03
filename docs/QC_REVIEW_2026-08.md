# Quality-control review — DOI column repair (v1.1)

**Date:** August 2026 · **Subject:** the patch set released as data v1.1 ·
**Outcome:** two disqualifying defects found and fixed before release

This records how the v1.1 patch was checked, what the check found, and what was
deliberately left alone. It exists because the first round of verification passed
everything and was wrong to.

## Why an adversarial review

The DOI repair produced 2,973 proposed corrections and a self-audit reporting
**120/120 precision**. That number was close to tautological: the audit confirmed a
proposal by recomputing `title_sim >= 0.90` and `journal_match` — the same two
predicates, from the same functions, that had caused the proposal to be accepted. For
the search-recovered tier those two tests *are* the acceptance rule, so the audit
could not return a failure. It was measuring its own reflection.

A gate that has never rejected anything has not been tested. So the patch was given
to seven independent reviewers, each with a different lens, and **every finding they
raised was then handed to a separate skeptic instructed to refute it**. Findings that
could not be independently reproduced were discarded rather than reported.

## Scale

| | |
|---|---:|
| Reviewers (lenses) | 7 |
| Total agents, including refutation and synthesis | 47 |
| Findings raised | 39 |
| Survived refutation | 23 |
| Refuted and discarded | 16 |

The seven lenses: independent re-sampling; attacking the deterministic rule; testing
the journal guard; hunting systematic bias; SQL apply-safety; duplicates and
collisions; and reading the pipeline code for further bugs of the kind already found.

## The two disqualifying findings

### 1. The patch could not have run at all

`swrd.papers` carries a partial unique index:

```
unique_papers_doi ON swrd.papers USING btree (doi) WHERE (doi IS NOT NULL)
```

**323 of the 2,973 proposed DOIs were already held by a different row.** The first
such `UPDATE` raises a unique violation, and inside `begin; … commit;` with
`ON_ERROR_STOP=1` that rolls back the entire transaction. The patch would have
applied nothing, and the failure would have looked like a database problem rather
than a patch problem.

The cause was a scoping error in the guard: it compared proposals against *each
other* and never against the live column. Five of the seven lenses found it
independently.

**Fixed** — `04_apply_sql.py` now runs a preflight against the live column before
emitting any SQL, and routes collisions to the review queue by kind.

**And it was a finding in its own right.** 212 of the collisions are the same article
present twice from two different ingests: the recovered DOI is correct and the *row*
is redundant. That is a duplicate-record defect, not a DOI defect, and it is now
logged as such with each sibling row id named.

### 2. Three wrong DOIs, and an audit that could not see them

| Record | Was assigned | Should be | Why it slipped through |
|---|---|---|---|
| 115909 | `10.15270/38-4-1430` | `10.15270/39-1-377` | A reply article was given the DOI of the article it replies to. Different author; author overlap was 0.0 and was not being used as a gate. |
| 115257 | `10.31265/jcsw.v14i2.245` | `10.31265/jcsw.v14i2.246` | The issue editorial and the real article are both prefixes of our stored title. A flat 0.97 prefix score made them indistinguishable, so Crossref's result order decided. |
| 117167 | `10.1080/…2014.909682` | `10.1080/…2013.853553` | "Letter from the Editors (5)" matched "Letter from the Editors (7)". One digit apart scores 0.96 on any string metric. |

117167 was **inside the 120/120 audit sample** and passed it.

**Fixed** — four changes to candidate selection: filter to journal-agreeing candidates
*before* ranking rather than after; reject any match whose title digit sequences
differ; break ties on author agreement instead of API result order; and scale the
prefix similarity by how much text is actually shared. All three records are now
correctly routed to the review queue, each for the right stated reason.

## The audit, rebuilt

The replacement deliberately avoids every signal the recovery step used to accept:

| Signal | Why it is independent |
|---|---|
| **DOI prefix** against the journal's registered prefixes | Derived from the live column; recovery never looked at prefixes |
| **Digit sequences** in the title | Exact test, unrelated to similarity scoring |
| **Author-token overlap** as a magnitude | Recovery only tested `!= 0`, and only for some rows |
| **Year agreement** | Recovery used year as a *retrieval* filter, never as an acceptance test |

It now reports Wilson 95% intervals rather than a bare fraction, is stratified by
`(tier, journal-agreement basis)` rather than tier alone, and ships a **self-test**:
`03_audit.py --selftest` feeds it the three known-wrong DOIs above and exits non-zero
if it confirms any of them.

```
selftest — the audit must REJECT all of these:
  115909: rejected (good)  reasons=['authors_do_not_overlap']
  115257: rejected (good)  reasons=['authors_do_not_overlap']
  117167: rejected (good)  reasons=['digit_sequence_differs']
```

Precision, run **exhaustively over every proposal** rather than on a sample:

| Stratum | Confirmed | Population |
|---|---|---:|
| A / rule | 2,769/2,769 | 2,769 |
| B / ISSN | 375/375 | 375 |
| B / name | 471/471 | 471 |

Sampling was the wrong tool here: 3,615 records with cached Crossref responses can
be checked in full, so estimating a rate would have been a choice to know less.

## A false positive worth recording

The rebuilt audit initially flagged two *Journal of Forensic Social Work* records
whose DOI prefix `10.15763` was "not in the journal's set". It was wrong: that journal
has only three valid DOIs in the column, all `10.1080`, and has since moved to a
self-hosted prefix. A baseline of three had "proved" that the journal's own current
prefix was foreign.

The check now requires 20 valid DOIs before it applies, and a Crossref
container-title match overrides a prefix objection. **A check with no baseline does
not abstain — it invents an answer.**

## Also fixed along the way

- **`swrd_surnames()` handled one name format.** It split on the comma, so
  given-name-first strings returned whole names and never matched Crossref's `family`
  field — author overlap read 0.0 for entire journals. Now compares name *token sets*
  on both sides, which also handles compound and non-Western surnames (`de Jesús`,
  `Van Wormer`, `Ríos Campos`). Median overlap on confirmed matches went 0.0 → 1.0.
- **Journal comparison was order-sensitive**, scoring the bilingual title *Global
  Social Work / Trabajo Social Global* against *Trabajo Social Global-Global Social
  Work* as a disagreement. Journal matching now lives in one shared function used by
  both recovery and audit, ISSN preferred, with a token-set fallback.

## Accepted, not fixed

- **The ±1 year and print-ISSN search filters** suppress candidates for publishers who
  bulk-registered a back catalogue or migrated platforms, which is why per-journal
  recovery is uneven. Not changed for v1.1: re-running recovery would have invalidated
  this review. Tracked separately.
- **Year disagreements are never proposed as corrections.** An earlier pilot found all
  five sampled year mismatches were Crossref bulk-registration artifacts where SWRD
  was right. Year is reported as evidence only.

## What this review did not examine

- The **journal misattribution** the column verification surfaced (~3,571 records) —
  found by this work but out of scope for a DOI patch, and now logged separately.
- The **SSWR database**, untouched by v1.1.
- Whether Crossref's own metadata is correct. It is treated as evidence, not truth:
  976 well-formed DOIs are absent from Crossref entirely, mostly in thin-coverage
  regional journals, and absence is not proof a DOI is wrong.

## Reproducing

```bash
python3 qc/doi/code/01_extract.py               # asserts the population shape
python3 qc/doi/code/02_recover.py               # cached; re-runs are free
python3 qc/doi/code/03_audit.py --selftest      # the gate, with its own test
python3 qc/doi/code/04_apply_sql.py             # patch set + queue + SQL
```

Full per-record evidence: `qc/doi/data/recovery.json`, `audit.json`,
`review_queue.csv`. Method: [`qc/doi/README.md`](../qc/doi/README.md).
