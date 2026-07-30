# AI in Social Work: A Verified Two-Corpus Analysis (1989–2026)

This folder contains the data, figures, and scripts behind an open reanalysis of artificial intelligence scholarship in social work, built on the two databases of the Social Work Meta-Data Project and extended with a Web of Science supplement through July 2026.

## What this is

Every AI-related item was identified and verified in two open corpora:

- **Journals (SWRD).** 296 verified articles across the 88 disciplinary journals of the Social Work Research Database, 1989–2026; 289 are substantively AI-focused. Because the versioned SWRD release ends in 2025, the corpus was backfilled and extended with a Web of Science Core Collection query on the same journal list (2024–2026), adding 24 late-indexed 2025 articles and 89 provisional 2026 articles.
- **Conference (SSWR).** 180 verified presentations from the complete SSWR annual programs, 2005–2026.

Titles and abstracts were searched with 17 AI and computational phrases (from "expert system" and "neural network" to "machine learning," "ChatGPT," and "large language model"), plus standalone "AI," hyphenated AI compounds, and GPT/LLM tokens. Every match was read; recurring false-positive classes (for example, "AI" as American Indian, pedagogical "deep learning," qualitative "clinical data mining") were removed. A semantic recall audit using SWRD's embedding layer recovered seven additional journal articles the keywords missed.

Each verified item was assigned one of three categories:

- **Empirical AI work** — builds, applies, or tests a model on data (benchmarking included). Traditional statistics (e.g., logistic regression) do not qualify on their own; in this corpus they appear only as comparison baselines.
- **Study of AI (reception)** — original data on attitudes, adoption, or perceptions of AI; no model is run.
- **Commentary and review** — conceptual, ethical, educational, and critical writing.

## Headline findings

- Disciplinary engagement begins in 1989 (expert systems), not 2016, and has moved through three technological waves: expert systems, machine learning, and generative AI.
- Journals: only about a third of AI-focused articles are empirical (100 of 289; 34.6%); roughly half are commentary (148; 51.2%).
- Conference: the balance inverts — 135 of 180 presentations (75%) are empirical.
- 2026 is the largest year on record in both venues (journals: 88 provisional; conference: 53, complete program).

## Files

**data/**

The Web of Science supplement is kept strictly separate from the SWRD database records: nothing here modifies or merges into the versioned SWRD release. The supplement is an analysis-level layer that sits alongside it.

- `journal_corpus_swrd_verified.json` — the 183 verified AI articles drawn from SWRD v1.0, with year, title, abstract, and label.
- `wos_supplement_2024_2026.json` — the raw Web of Science export records (2024–2026) used to extend the analysis window.
- `wos_supplement_verified_labels.json` — the 113 verified, labeled supplement articles (24 late-indexed 2025; 89 provisional 2026). Combined with the SWRD file at analysis time, these form the 296-article corpus.
- `conference_corpus_verified.json` — all reader-verified SSWR records with labels (off-topic retained and marked).
- `journal_venues.json` — verified AI articles per journal with per-label counts.
- `journal_author_network.json`, `conference_author_network.json` — disambiguated author counts, orientation mixes, and co-authorship edges.
- `facts_groundtruth.md` — the computed ground-truth numbers used for internal consistency checks.

**figures/** — publication-quality figures (color and grayscale): growth by year in both venues (with the ChatGPT release marker), co-authorship networks (frequency-thresholded), composition by technological wave, and publication venues.

**scripts/** — the Python scripts that generate every figure from the data files.

## Citation

If you use these data or analyses, please cite the Social Work Meta-Data Project (https://beperron.github.io/SocialWork-MetaData/) and the accompanying comment manuscript (Perron et al., in preparation).
