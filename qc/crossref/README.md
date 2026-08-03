# Crossref quality control for SWRD — pilot

Verifies SWRD records (1989+) against Crossref and proposes corrections. **Read-only throughout**: the project API rejects writes, so this pipeline cannot change the database even in principle. Its output is a reviewed patch set that feeds step 1 of the maintainer procedure in [`docs/DATA_CHANGELOG.md`](../../docs/DATA_CHANGELOG.md).

This is a **pilot on 442 records**, not the full run. Its purpose was to find the false-positive rate before committing to ~70,000 lookups. It did, twice.

## Running it

```bash
python3 code/01_sample.py 100     # stratified adversarial sample
python3 code/02_verify.py         # Crossref lookups + comparison (cached)
python3 code/03_report.py         # proposed_corrections.csv + summary
```

Re-runs are free: every Crossref response is cached under `cache/`, so changing a matching rule and re-running costs nothing.

## The sample is deliberately adversarial

100 records from each of: valid DOI, `oai:` DOI, `dc/` DOI, null DOI, and thin-coverage journals (regional/small-publisher titles where Crossref registration is patchy). 442 unique after overlap. A representative sample would be mostly easy records and would have taught us nothing.

## Results

| Stratum | n | Confirmed / recovered | Rejected or unresolved |
|---|---:|---:|---:|
| Valid DOI | 100 | 87 confirmed | 13 field mismatch |
| `oai:` DOI | 100 | **100 recovered** | 0 |
| `dc/` DOI | 100 | 71 recovered | 29 |
| Null DOI | 89 | 27 recovered | 62 |
| Thin coverage | 42 | 13 | 29 |

**214 proposed corrections**: 100 tier A, 110 tier B, 4 tier C.

### What worked

**The OAI→DOI rule is 100/100.** `oai:scholarworks.wmich.edu:jssw-NNNN` → `10.15453/0191-5096.NNNN`, with Crossref confirming the title every time. This is deterministic and safe to apply in bulk — roughly 2,000 records database-wide.

**Journal-name checking finds the misattribution class.** 11 records with a *perfect* title match (similarity 1.0) sit under the wrong journal — including four more instances of the *Journal of Social Work Practice* / *Journal of Sociology & Social Welfare* swap that started this whole thread, plus *Social Work*→*Affilia* and *Journal of Social Work Education*→*Journal of Applied Social Science*. Nine survive review; two are the *Smith College Studies in Social Work* → *Studies in Clinical Social Work* rename and are handled by an explicit exception list.

### What the pilot caught before it did damage

**1. The year rule produced 5/5 false positives.** Every year "mismatch" was *Social Work-Maatskaplike Werk* with a perfect title match and Crossref reporting 2014 — the year the publisher bulk-registered its back catalogue, not the year of publication. SWRD was right and Crossref was wrong in all five. Year disagreements are therefore recorded but **never proposed as corrections**.

**2. Search-based recovery matched the wrong journal 35 times.** Before a journal check existed, bibliographic search happily returned a *book review of the same work in a different journal*, or a same-titled paper elsewhere. Hand-checking five null-DOI recoveries found two clearly wrong and two doubtful. Adding a journal-agreement requirement moved 61 null-DOI proposals from "recovered" to `rejected_wrong_journal` and cut recoveries from 44 to 27 — a large precision gain and exactly the kind of error a full run would have propagated 70,000 times.

### The blocker worth fixing first

**84 of 91 journals have no ISSN.** Only 4 carry `issn_print` and 7 `issn_online`. ISSN is the reliable way to verify journal attribution; without it the check falls back to comparing names, which is why 385 of 425 journal verdicts rest on string comparison rather than an identifier.

This is fixable *from this same data*: Crossref returns ISSNs on every article record, so the ISSN for each journal can be recovered by majority vote across its articles. Doing that first would make journal verification identifier-based rather than name-based, and is a database improvement in its own right.

## Recommended order for the full run

1. **Backfill journal ISSNs** from Crossref (91 journals, cheap, high value).
2. **Apply the OAI conversion** — tier A, ~2,000 records.
3. **Run the full valid-DOI verification** with ISSN-based journal checking; expect the misattribution class to surface at scale.
4. **Leave null-DOI recovery last** — it is the weakest cell (27/89 here) and benefits most from ISSN filtering.

Full run cost: ~66,000 DOI lookups at 40 per batched call plus ~21,000 searches ≈ 1.5–2 hours, well inside Crossref's polite-pool limits.

## Caveats

- **Crossref is evidence, not truth.** 5 well-formed DOIs in the sample have no Crossref record at all, all in thin-coverage journals — likely registered with another agency or never deposited. Absence is not proof the DOI is wrong.
- **`type` does not identify book reviews** in this publisher set; several are typed `journal-article` and only the `Book Review:` title prefix distinguishes them.
- Rates here are **per stratum, not prevalence-weighted** — the sample was built to stress the rules, not to estimate corpus-wide error.

## Files

```
code/swrdqc.py      shared API client, cache, and matching helpers
code/01_sample.py   stratified sample
code/02_verify.py   lookups, comparison, tiered verdicts
code/03_report.py   proposed_corrections.csv + summary
data/findings.json  one verdict per record, with full evidence
data/proposed_corrections.csv   the reviewable patch set
cache/              gzipped Crossref responses (gitignored; regenerable)
```
