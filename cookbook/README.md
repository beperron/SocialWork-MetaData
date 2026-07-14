# Cookbook — End-to-End Worked Examples

Where the [skills](../skills/) are reference material, these are complete walkthroughs an assistant (or a person) can follow start to finish. Each names the skills it uses and every step has been run against the live databases.

| Walkthrough | What it demonstrates | Needs Ollama? |
|---|---|---|
| [01 · Map the literature on a topic](01-map-a-topic.md) | Hybrid search on both databases, merged into one topical corpus with counts and exemplars | Yes |
| [02 · Trend analysis with proper caveats](02-trend-analysis.md) | SQL-only disciplinary trends, era caveats, methodology composition | No |
| [03 · A scholar's twenty-year arc](03-scholar-trajectory.md) | Author disambiguation workflow, presentation history, collaborators | No |
| [04 · Build a screening corpus](04-screening-corpus.md) | High-recall retrieval for a review: hybrid search + keyword sweep + export with DOIs | Yes |

Setup common to all: the connection details in either database skill (public key, base URL, profile headers), plus the [`ollama-embeddings`](../skills/ollama-embeddings/SKILL.md) skill where marked.
