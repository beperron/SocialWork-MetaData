# Skills for AI Assistants

Hand these files to an AI assistant (Claude, ChatGPT, or any comparable system) to work with the Social Work Meta-Data Project databases. Read-only, no password, no account.

## Which file to load

| You want to… | Load |
|---|---|
| **Get going in one file** (most users) | [`swrd-database-skill.md`](swrd-database-skill.md) or [`sswr-database-skill.md`](sswr-database-skill.md) — self-contained quickstarts |
| Analyze the **journal literature** in depth | [`swrd-database/SKILL.md`](swrd-database/SKILL.md) (+ its `references/`: catalog, SQL recipes, search recipes) |
| Analyze the **conference record** in depth | [`sswr-database/SKILL.md`](sswr-database/SKILL.md) (+ its `references/`) |
| Set up **semantic search** locally (one-time) | [`ollama-embeddings/SKILL.md`](ollama-embeddings/SKILL.md) |
| Follow **end-to-end worked examples** | [`../cookbook/`](../cookbook/) |

## How the pieces fit

- Both databases expose the **identical search API**: `search_papers_semantic`, `search_papers_keyword` (ranked full-text), and `search_papers_hybrid` (reciprocal-rank fusion of both — the recommended default for topic questions), plus `run_sql` for any read-only SQL.
- Keyword search and SQL need **nothing installed**. Semantic and hybrid search additionally need the `ollama-embeddings` skill (a free ~5-minute local setup).
- Each database skill's `references/catalog.md` is generated from the live database — measured coverage percentages, exact value vocabularies, and the join map.
