# Screening a Suicide Literature with a Local Model

A worked demonstration of the project's AI integration: two prompts retrieve every suicide-related record in both databases and screen all 2,034 of them, one at a time, with a 27B open-weight model running on a laptop.

**Read it:** https://beperron.github.io/SocialWork-MetaData/demonstrations/suicide-screening/

## Why this exists

Jonathan Singer tested the [`llms.txt`](../../llms.txt) connection file on a suicide-literature question and hit two errors, both of which returned messages that read like a broken database and neither of which was. `llms.txt` was revised to cover them — the GET-vs-POST failure, the sandbox host approval, and a third gap where "dedupe on normalized title" was prescribed without a definition. This is the same analysis run again after the fix.

## Result

| | |
|---|---|
| Candidates screened | 2,034 (796 SWRD journal articles, 1,238 SSWR presentations) |
| Suicide-relevant | 1,331 (65.4%) |
| Empirical / Non-empirical | 1,160 / 171 |
| Quantitative / Qualitative / Review | 915 / 180 / 65 |
| Screening model | `qwen3.6:27b` via Ollama, local, one record per request |
| Model time | 1.7 hours, median 3.3 s per record, all 2,034 first-attempt |
| Blind re-screen agreement | 92% on the full label tuple (100 records) |
| Independent spot check | 90% (20 records) |

## What is here

```
index.html                                 the demonstration write-up
METHODS.md                                 long-form methods and results, written during the run

data/suicide_abstract_screening_results.json   all 2,034 records, decisions, model metrics, audit trail
data/suicide_relevant_articles.json            the 1,331 relevant records only
data/suicide_corpus_labeled.csv                flat table without abstracts, for spreadsheets
data/accuracy_audit.json                       100-record blind re-screen + adjudications
data/independent_manual_spot_check.json        20-record independent check + 2 corrections
data/screening_summary.json                    final counts and audit metadata
data/stats.json                                every number on the page, machine-readable

code/fetch_suicide_papers.py                   API retrieval, pagination, SWRD dedup  → data/
code/screen_suicide_abstracts_ollama.py        one-record-at-a-time screening, JSONL checkpointing
code/audit_suicide_screening.py                stratified blind audit + thinking-mode adjudication
code/apply_independent_spot_check.py           records and applies the manual spot-check decisions
code/compute_stats.py                          recompute every page number from the labels
code/make_figures.py                           regenerate the three figures

figures/*.svg                                  composition, growth, audit agreement
```

## Reproducing it

```bash
python3 code/fetch_suicide_papers.py     # public read-only key; nothing to install
python3 code/compute_stats.py            # verify the page's numbers against the released data

ollama pull qwen3.6:27b                  # ~17 GB, once
python3 code/screen_suicide_abstracts_ollama.py    # ~1.7 h on an M-series laptop
python3 code/audit_suicide_screening.py

pip install matplotlib && python3 code/make_figures.py
```

`compute_stats.py` needs no model and no network — run it first if you only want to check the page against the data. The screening scripts require Ollama serving `qwen3.6:27b` on port 11434.

## The two prompts

**Retrieval**, issued to a coding assistant:

> Ok, do this. I want to access all papers specific to the topic of suicide:
>
> Fetch https://beperron.github.io/SocialWork-MetaData/llms.txt (or its HTML mirror at .../llms.html), run its reachability check, and connect exactly as it describes, then answer my question using those databases. The database endpoint is a POST API, not a web page, so query it from a shell or code tool rather than a page-fetch tool, and approve the host if you are asked. If you cannot fetch either URL, tell me and I will paste the file.

**Screening and classification**, executed by the local model:

> Now, use my local Ollama model -- Qwen3.6-27b to carefully screen each abstract for its relevance to suicide. For all relevant articles, classify as Empirical (includes systematic, meta-analysis, scoping) vs. Non-empirical. If the article is empirical, classify as qualitative, quantitative, or review (systematic, meta-analysis, scoping). Narrative reviews should all considered non-empirical. If empirical, classify as qualitative, quantitative, or review (systematic, meta-analysis, scoping). Narrative reviews should be classified as Non-empirical. Return your results as a JSON file. Just do one-by-one for most accuracy

"One-by-one" is the substantive instruction. Batching abstracts into a shared context lets decisions bleed across records and drift toward whatever label the model has been emitting; one request per record costs wall-clock time and buys independence.

## Data notes

- **The inclusion rule is a word-start match on the stem `suicid`** in title or abstract (`~* '\msuicid'`), SWRD restricted to 1989+. Reproducible, but blind to studies that use no suicide-root term. Self-harm and NSSI are not swept in by default.
- **Labels come from abstracts, not full texts.** Distinguishing systematic from narrative reviews, and qualitative from mixed-methods, is sometimes impossible at abstract level — and those are the cells where both audits found the most movement.
- **62 records have no abstract** and were screened from title under a conservative rule that sends them all to Non-empirical. Flagged as `screening_basis: title_only` so they can be dropped.
- **No mixed-methods category** existed in the requested taxonomy; mixed-methods work was absorbed into Quantitative or Qualitative by predominance.
- **The 92% audit figure is internal consistency**, not accuracy — the same model produced the primary labels and the blind re-screen. The 20-record manual check was done by an AI assistant against the rubric, not by trained suicide researchers. This is a documented draft corpus, not a validated one.
- **SWRD 2024–2025 are lower bounds** (publisher indexing lag). SSWR 2026 is complete — that meeting has already occurred.
- **Every corrected record keeps its pre-correction decision** under `screening_initial` or `screening_pre_manual_spot_check`, with the audit that changed it.

## Citations

**SWRD** — Perron, B. E., Victor, B. G., & Qi, Z. (2026). Evolution of social work knowledge production over 35 years. *Research on Social Work Practice.* https://doi.org/10.1177/10497315261416833

**SSWR** — Perron, B. E., Victor, B. G., & Qi, Z. (2026). AI-assisted curation of conference scholarship. *arXiv.* https://doi.org/10.48550/arXiv.2603.06814
