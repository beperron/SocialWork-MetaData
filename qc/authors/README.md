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

| gate | refuses when | n |
|---|---|---:|
| doi | title similarity < 0.90 against the DOI's Crossref record | 7,042 |
| surname | Crossref lists two authors sharing the group's surname | 64 |
| ambiguity | a bare surname fits two different given names | 0 |
| repeat link | one author_id linked to the paper twice | 0 |

The surname veto is deliberately blunt. Paper 18821 has Wilfred **and** Trudie van
Delft, each genuinely triplicated; Crossref listing two van Delfts blocks both
merges. Those stay in `data/credits_review.csv` for a human.

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

**7,764 duplicate credits across 2,887 papers.** No person loses a credit; 2,887
papers stop crediting the same person twice. Author rows themselves are untouched
and `swrd.papers` is not modified, so the release row count cannot move.

## Run

```sh
python3 qc/authors/code/01_dedupe_credits.py --selftest   # 12 planted cases
python3 qc/authors/code/01_dedupe_credits.py              # proposes, applies nothing
psql "$TGT" -v ON_ERROR_STOP=1 -f qc/authors/data/dry_run_credits.sql
```

Dry run verified: `INSERT 0 7764`, `DELETE 7764`, no paper left authorless,
`ROLLBACK`.

`data/rollback_credits.sql` re-inserts every deleted link with the `position` and
`is_corresponding` read off the live table beforehand, so the restore is exact.

**Not applied.**
