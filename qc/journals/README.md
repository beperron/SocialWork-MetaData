# QC #2 — journal ISSNs and attribution

Stage 1 of v1.2. Recovers an ISSN for every SWRD journal ([issue #4](https://github.com/beperron/SocialWork-MetaData/issues/4)), then uses those identifiers to find journals holding another journal's articles ([issue #2](https://github.com/beperron/SocialWork-MetaData/issues/2)).

**Read-only.** Nothing here writes to the database.

## Why ISSNs first

84 of 91 journals carry no ISSN, so the journal check ran on **names** for 67,124 of 69,349 records. Name matching is unsafe here — it maps *Journal of Comparative Social **Welfare*** onto *Journal of Comparative Social **Work***, and *Journal of Social Work & Human Sexuality* onto *Journal of Social Work*. Different journals. An identifier removes the guesswork.

## Results

**66 of 91 journals** got an ISSN by majority vote over their own articles' Crossref records. **25 are queued**: 9 where the vote was too weak or split, 16 with no valid-DOI articles to vote on.

The method validates against the only ground truth available — the journals that already had an ISSN:

| Journal | Stored | Recovered | |
|---|---|---|---|
| Social Work Research | 1070-5309, 1545-6838 | same | ✓ |
| Columbia Social Work Review | 2164-1250 | + 2372-255X | ✓ |
| Global Social Work | 2013-6757 | same | ✓ |
| Journal of Forensic Social Work | 1936-928X, 1936-9298 | same | ✓ |
| ASEAN Social Work Journal | 2089-1075, 2963-2404 | same | ✓ |
| Sexual and Gender Diversity (id 263) | 1053-8720, 1540-4056 | 2993-3021, 2993-303X | *see below* |

Five of five exact. The sixth is not a failure: the stored pair is the ISSN of *Journal of Gay & Lesbian Social Services*, its **former** title.

## What the ISSN vote also detects

A journal whose articles carry more than one ISSN is saying something, and the year spans say which:

- **same journal** — the sets share an ISSN. One deposit listed print+online, another only online. *Social Work-Maatskaplike Werk* does this.
- **rename** — disjoint sets, sequential spans. **9 found**, including *Families in Society* running through three identities (*The Family* 1922–45 → *The Journal of Social Casework* 1947–48 → present) and *Computers in Human Services* → *Journal of Technology in Human Services* in 1999.
- **contamination** — disjoint sets, interleaved spans. **13 found.** This is issue #2, located by identifier rather than by string comparison.

The contamination list includes *Social Work* carrying Affilia articles (0886-1099) across 1990–2017 alongside its own 0037-8046 across 1959–2023, and *Administration in Social Work* carrying *Journal of Religion & Spirituality in Social Work*.

## The duplicated journal row, explained

ids 232 and 263 are both "Sexual and Gender Diversity in Social Services" — the v1.0 known imperfection. They are not an accidental duplicate: **232 holds the 749 pre-rename articles** (voting 1053-8720/1540-4056, container *Journal of Gay & Lesbian Social Services*, 91.6% agreement) and **263 holds 39 post-rename ones**. One journal, split across a title change.

## Caveats

- **The 16 title lookups must not be trusted blind.** Asked for *School Social Work Journal*, Crossref returns a Korean *Journal of School Social Work*; *Arete* returns *Arete Political Philosophy Journal*. Seven return nothing. All 16 are queued for a person.
- **One rename needs a human**: *Journal of Social Work in End-of-Life* ← *Journal of Social Work & Human Sexuality* (1993, 3 articles). Those look like different journals; the span was sequential only because the sample is thin.
- Crossref cannot distinguish print from online ISSN — it returns a flat array. Sorted order is a convention, not a fact.

## Running it

```bash
python3 qc/journals/code/01_backfill_issn.py   # ~8,300 Crossref lookups, cached
python3 qc/journals/code/02_classify_eras.py   # reads the cache, no network
```

## Files

```
code/01_backfill_issn.py   ISSN recovery by vote, with title lookup as fallback
code/02_classify_eras.py   same-journal vs rename vs contamination
data/proposed_issns.csv    66 journals, tier A
data/issn_review_queue.csv 25 needing a decision, with the reason
data/issn_evidence.json    every vote and every candidate
data/journal_eras.json     each journal's ISSN groups with year spans
data/rename_map.csv        9 title changes
data/contamination.csv     13 journals holding another journal's articles
```
