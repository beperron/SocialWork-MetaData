# Cookbook — Worked Examples You Can Run by Prompting

Each walkthrough here is an analysis you can get done by prompting an AI assistant — Claude, ChatGPT/Codex, or any assistant that can fetch a URL and run code. You do not need to write SQL or Python yourself. Every recipe has two layers:

- **Do this with Claude or Codex** — a copy-paste prompt (edit the bracketed parts), plus what to check when the assistant finishes.
- **Under the hood** — the actual steps and queries the assistant runs, kept for transparency and for assistants reading this repo directly.

| Walkthrough | What you get | Needs Ollama? |
|---|---|---|
| [01 · Map the literature on a topic](01-map-a-topic.md) | Counts over time and top items on any topic, across journals and conference | Yes |
| [02 · Trend analysis with proper caveats](02-trend-analysis.md) | How the discipline's scholarship changed 1989–2023, with honest caveats | No |
| [03 · A scholar's twenty-year arc](03-scholar-trajectory.md) | One researcher's conference history: topics, collaborators, moves | No |
| [04 · Build a screening corpus](04-screening-corpus.md) | A high-recall CSV of candidates for a systematic or scoping review | Yes |
| [05 · A verified topical corpus, extended past the release](05-verified-topic-corpus-with-wos-extension.md) | Every article on a topic, verified by reading, with a separate Web of Science extension | Yes (audit only) |
| [06 · Classify what a literature does](06-classify-what-a-literature-does.md) | Empirical vs. reception vs. commentary composition, by era and venue | No |
| [07 · Co-authorship networks with thresholds](07-coauthorship-networks-with-thresholds.md) | A readable network of the frequent authors, with explicit inclusion rules | No |

The fully worked artifact behind 05–07 (verified corpora, labels, figures, and scripts from the AI-in-social-work analysis) lives in [`analyses/ai-in-social-work/`](../analyses/ai-in-social-work/).

## Writing prompts that work with these databases

A few habits make the difference between a plausible-looking answer and a checkable one:

1. **Point the assistant at the site first.** Start every prompt with "I'm using the Social Work Meta-Data Project (https://beperron.github.io/SocialWork-MetaData/). Download the skill files from the site and connect." The skills carry the connection details, schema notes, and query examples, so the assistant does not have to guess.
2. **Name the deliverable.** "Give me a chart and a five-sentence summary" gets you a chart and a summary; "analyze X" gets you whatever the assistant felt like.
3. **Ask for verification, not just results.** Add "read the abstracts of the matches and remove false positives, and tell me what you removed and why." The databases make this cheap; unverified keyword counts are the single biggest source of wrong answers.
4. **Ask for the caveats.** "State what your counts do not cover" surfaces the boundary decisions (journal set, incomplete recent years, abstract-only coding) that a reviewer would ask about.
5. **Keep arithmetic auditable.** Ask the assistant to report counts stepwise (raw, removed, kept) and to show its work when numbers disagree.
6. **Check a sample yourself.** Every recipe ends with a "what to check" note. Ten spot-checks catch most problems.

The prompts in the recipes bake these habits in; adapting them to a new question is usually just changing the bracketed topic.

Setup common to all: nothing beyond the prompt for most recipes. Recipes marked "Yes" in the Ollama column use local embeddings for semantic search; the [`ollama-embeddings`](../skills/ollama-embeddings/SKILL.md) skill covers the one-time setup, or you can ask the assistant to fall back to keyword-plus-database search where Ollama is unavailable.
