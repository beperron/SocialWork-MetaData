# Cookbook — End-to-End Worked Examples

Where the [skills](../skills/) are reference material, these are complete walkthroughs an assistant (or a person) can follow start to finish. Each names the skills it uses and every step has been run against the live databases.

| Walkthrough | What it demonstrates | Needs Ollama? |
|---|---|---|
| [01 · Map the literature on a topic](01-map-a-topic.md) | Hybrid search on both databases, merged into one topical corpus with counts and exemplars | Yes |
| [02 · Trend analysis with proper caveats](02-trend-analysis.md) | SQL-only disciplinary trends, era caveats, methodology composition | No |
| [03 · A scholar's twenty-year arc](03-scholar-trajectory.md) | Author disambiguation workflow, presentation history, collaborators | No |
| [04 · Build a screening corpus](04-screening-corpus.md) | High-recall retrieval for a review: hybrid search + keyword sweep + export with DOIs | Yes |
| [05 · A verified topical corpus, extended past the release](05-verified-topic-corpus-with-wos-extension.md) | Keyword net → read-everything verification → semantic recall audit → separate Web of Science supplement | Yes (audit only) |
| [06 · Classify what a literature does](06-classify-what-a-literature-does.md) | Empirical / reception / commentary coding, era composition, journal-vs-conference comparison | No |
| [07 · Co-authorship networks with thresholds](07-coauthorship-networks-with-thresholds.md) | Disambiguation, stated inclusion thresholds, continuum coloring, overlap-free layout | No |

The fully worked artifact behind 05–07 (verified corpora, labels, figures, and scripts from the AI-in-social-work analysis) lives in [`analyses/ai-in-social-work/`](../analyses/ai-in-social-work/).

Setup common to all: the connection details in either database skill (public key, base URL, profile headers), plus the [`ollama-embeddings`](../skills/ollama-embeddings/SKILL.md) skill where marked.
