# Artificial Intelligence in Social Work, 1989–2026

A worked demonstration: every article on AI in the disciplinary social work journals, verified by reading and classified by what each study does.

**Read it:** https://beperron.github.io/SocialWork-MetaData/demonstrations/ai-in-social-work/

## What is here

```
index.html                          the demonstration write-up
data/ai_corpus_labeled.json         278 verified records with labels and per-model votes
data/candidates_raw.json            373 raw keyword matches, before screening
data/stats.json                     every count on the page, machine-readable
code/fetch_candidates.py            keyword net over the database  → candidates_raw.json
code/semantic_audit.py              embedding-based recall audit (finds what keywords missed)
code/compute_stats.py               recompute every number from the labels
code/make_figures.py                regenerate the three figures
figures/*.svg                       growth, era composition, publication outlets
```

## Reproducing it

```bash
python3 code/fetch_candidates.py     # nothing to install; public read-only key
python3 code/compute_stats.py        # check the page's numbers against the data
pip install matplotlib && python3 code/make_figures.py
```

The screening and labeling steps are deliberately not scripted: they require reading each abstract. The machine retrieves and proposes; a person decides.

## Semantic search

`code/semantic_audit.py` finds articles the keyword net missed because they use different vocabulary. It needs a local embedding model:

| | |
|---|---|
| Model | **EmbeddingGemma 300M** (`embeddinggemma:300m`) |
| Dimensions | 768 |
| Served by | [Ollama](https://ollama.com), locally, port 11434 |
| Download | ~620 MB, once |
| Query prefix | `task: search result \| query: {question}` — **required** |

Both databases were embedded with this exact model. Vectors from any other model are not comparable and return noise. Setup is covered by the [`ollama-embeddings` skill](../../skills/ollama-embeddings/SKILL.md); the script checks your setup before it runs.

```bash
ollama pull embeddinggemma:300m
python3 code/semantic_audit.py
```

## Data notes

- **The Web of Science supplement is kept separate** from the database records and is never merged. Every count reports the two sources distinctly.
- WoS indexes a curated journal set, so recent open-access titles, newer journals, and regional or non-English outlets may be missing from the 2025–2026 figures. Treat recent years as a lower bound.
- SWRD 2024–25 counts are also lower bounds — publisher indexing lags.
- Labels come from four independent AI runs working only from the public documentation; the recorded label is the majority, and the 8 records that split evenly were decided by a human reader and flagged in the data.

## Citation

Perron, B. E., Victor, B. G., & Qi, Z. (2026). Evolution of social work knowledge production over 35 years. *Research on Social Work Practice.* https://doi.org/10.1177/10497315261416833
