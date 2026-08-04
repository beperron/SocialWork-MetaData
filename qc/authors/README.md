# Authorship QC — one person credited twice on the same paper

Issue #6 was filed as "spurious authors". That framing did not survive the data.
`swrd.paper_authors` carries **four** separate defects, and only one of them has
evidence clear enough to repair.

| # | defect | papers | repaired here |
|---|---|---:|:---:|
| 1 | one person split into two rows, surname and given name each becoming an "author" | 316 | no |
| 2 | a reference list ingested as authors | ~300 | no |
| 3 | **the same person credited more than once** | 2,925 | **yes** |
| 4 | positions colliding, several rows claiming byline slot 1 | 4,755 | no |

Paper 100275 (`10.31265/jcsw.v15i1.316`) shows all four at once: a 6-author
article carrying **34** authorship links.

## Why Crossref does not supply the author list

The obvious repair is to make each paper's authors match Crossref. It is wrong.
Paper 19724 lists **T. Booth alone** in Crossref; the article is by Tim Booth,
Wendy Booth and David McConnell. Crossref author lists are routinely truncated to
the first author on older deposits, and no count-based guard catches it — a
one-author list is trivially "covered". Trusting Crossref there would have deleted
two real co-authors.

Crossref is used for exactly two things: confirming the DOI identifies the article
(title similarity ≥ 0.90), and **vetoing** merges. It never supplies names.

## The rule

Within one paper, two credits are the same person when the surname matches and the
given-name evidence does not positively conflict.

| pair | verdict |
|---|---|
| `Charity Chenga` / `Chenga, C.` | same |
| `Roux, A. A.` / `Adrie Roux` | same |
| `Freek Cronjé` / `Cronje, F.` | same |
| `Booth, Tim` / `Booth, Wendy` | **different** |
| `Lee S.` / `Kim S.` | **different** |

A missing given name is absence of evidence, not agreement, so a bare surname
merges only when the paper offers one candidate given name.

### The parser defect the audit caught

SWRD stores three name orders, and the third one broke the first version of this
fix. `Islam M.R.` is surname-first with collapsed initials. Read as given-first,
the **initial** lands in the surname slot: `Lee S.` becomes surname `s`. That
silently disarmed the Crossref veto — it looked up `s` instead of `lee` — and
merged Sunwoo Lee with Sangwoo Lee on paper 97213, and Sang Kyun Kim with Soo-Wan
Kim on 97424. The format is common for Korean and Bangladeshi names in this
corpus, so the blast radius was not small.

The count audit caught it because it uses a quantity no gate consulted.

## Gates

| gate | refuses when | n | |
|---|---|---:|---|
| doi | title similarity < 0.90 against the DOI's Crossref record | 7,042 | measured |
| surname | Crossref lists two authors sharing the group's surname | 64 | measured |
| given-name key | the group key is a Crossref *given* name, not a surname | 6 | measured |
| ambiguity | a bare surname fits two different given names | 0 | **structurally unreachable** |
| repeat link | one author_id linked to the paper twice | 0 | **structurally unreachable** |

The last two are tripwires, not filters, and their zeros are by construction
rather than by measurement. `compatible()` already forces every given-bearing
member of a group to share a first initial, so the ambiguity gate cannot fire;
and `(paper_id, author_id)` is unique in `swrd.paper_authors`, so the repeat-link
gate cannot either. They stay in place so the patch remains correct if either
assumption is ever loosened. **Three gates do work here, not five.**

The surname veto is deliberately blunt. Paper 18821 has Wilfred **and** Trudie van
Delft, each genuinely triplicated; Crossref listing two van Delfts blocks both
merges. Those stay in `data/credits_review.csv` for a human.

### The given-name gate, and why bug (b) had a second form

`parse_name('John')` returns `('john', [])` — the surname-first branch accepts a
leading token without ever checking that it *is* a surname. The Crossref veto then
looks up `cr_surnames['john']`, gets 0, and silently passes. On papers 100522 and
100548 that merged the fragment `John` into `John R.`: John Coates folded into
John R. Graham. Two people.

The fragments come from defect #1 — the split-name ingest — so this is one defect
feeding another. The gate withdraws 6 groups: those 4 plus two harmless
initial-merges on paper 100693.

**Gate order matters.** This runs *before* the corresponding-author promotion
below. On paper 100522 the dropped `John` row is flagged corresponding and the
keeper is a different person; promoting first would have converted a bad merge
into a false attribution.

## The corresponding-author flag is merged, not discarded

A deleted duplicate is often the row carrying `is_corresponding`. Dropping it does
not merely lose a row — it turns a true statement false. There are **zero NULLs**
in that column corpus-wide, so `false` is an assertion, not "unknown", and it
cannot be reconstructed from `position`: 1,236 flagged rows sit at position ≠ 1 and
94,566 position-1 rows are `false`.

3,032 of the deleted rows carry the flag. Without a merge, **502 papers** would go
from asserting a corresponding author to asserting none — 182 of them ending with a
single credit, where the sole author is necessarily the corresponding one. The
value ships, via `migration/10_export_release_csv.py` and the
`author_publication_stats.corresponding_author_count` view.

So the patch promotes the flag onto the surviving credit **before** the delete
(509 rows), and then asserts that no paper lost it. The assertion is proven able to
fail: strip the `UPDATE` and re-run, and it aborts with
`ERROR: 502 papers lost their corresponding author`.

## Audit

Post-merge credit count against Crossref's author count — a quantity no gate used.
"More than Crossref" is expected, because of the truncation above. **Fewer** would
mean a real author was deleted.

```
exactly equal          2,389
more than Crossref       498
FEWER than Crossref        0   <- must be 0, or the script refuses to emit SQL
```

## Result

**7,756 duplicate credits removed across 2,885 papers, and 509
corresponding-author flags promoted onto the surviving credit.** No person loses a
credit. Author rows themselves are untouched and `swrd.papers` is not modified, so
the release row count cannot move.

## Run

```sh
python3 qc/authors/code/01_dedupe_credits.py --selftest   # 12 planted name cases
python3 qc/authors/code/01_dedupe_credits.py              # proposes, applies nothing
psql "$TGT" -v ON_ERROR_STOP=1 -f qc/authors/data/dry_run_credits.sql
psql "$TGT" -v ON_ERROR_STOP=1 -f qc/authors/data/roundtrip_credits.sql
```

Dry run: `UPDATE 509`, `DELETE 7756`, no paper left authorless, none losing its
corresponding author, `ROLLBACK`.

Round trip: snapshot → apply → rollback → `except` in both directions →
**0 rows lost, 0 altered**, identical on all five columns.

`data/rollback_credits.sql` restores every deleted link with `position`,
`is_corresponding` **and `created_at`** read off the live table beforehand, and
un-promotes the 509 flags. Letting `created_at` default would have rewritten the
ingest history of 7,756 rows; restoring rows without un-promoting would have left
the "rollback" changing data of its own.

## Review record

An adversarial swarm (5 independent lenses, 2 refutation skeptics per finding,
18 agents) reviewed this before it was applied. 19 raw findings, 5 survived
refutation, 2 had real data effect — the corresponding-author loss and the 4
given-name-keyed merges. Both are fixed above. Refuted claims included
"the patch is not reproducible run to run" (group ordering changes a CSV label,
never the deletion set) and "Vibeke Krane loses her credit" (she does not).

Defects found on this fix, in order, each by a different mechanism:

| found by | defect |
|---|---|
| the count audit | name parser read the initial in `Lee S.` as the surname, merging two people and disarming the veto |
| a column diff | rollback restored 4 of 5 columns, silently rewriting `created_at` |
| the round-trip test | rollback's own assertion used a 7,756-tuple `IN` and died on `stack depth limit exceeded` |
| the swarm | `is_corresponding` discarded rather than merged — 502 papers |
| the swarm | `parse_name` accepts a given-name fragment as a surname key — 4 cross-person merges |

**Not applied.**


## The enrichment template contract

`swrd.author_name_enrichment` is the first *derived* table in the database, and
its shape is the contract every future enrichment (ORCID, affiliations) must
follow:

1. a **verbatim copy of the observed value** at generation time
   (`name_as_published`) — staleness is then a checkable predicate, enforced at
   load, in the health check, and at export packaging, each able to stop a
   release on its own;
2. **full evidence pointers** (`evidence_dois`), never a summary of them;
3. checked/agreeing counts with **unanimity as a CHECK constraint**, so a row
   that is not backed by every one of its papers cannot physically exist;
4. `generator` (script @ git sha) and `batch` (release), so any consumer can
   date and reproduce what they hold;
5. an `EXPECTED` row count in the export, forcing a conscious update;
6. **regenerate wholesale, never increment** — eligibility is a property of the
   row's whole link set, and appends cannot retract.

The enrichment never writes the observed table. Its rollback is `drop table` —
the only change in this project that destroys nothing observed.
