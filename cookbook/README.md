# Cookbook — Worked Examples You Can Run by Prompting

Each walkthrough here is an analysis you can get done by prompting an AI assistant — Claude, ChatGPT/Codex, or any assistant that can fetch a URL and run code. You do not need to write SQL or Python yourself, and there is nothing to install: the databases are hosted, read-only, and open with a public key. Every recipe has two layers:

- **Do this with Claude or Codex** — a copy-paste prompt (edit the bracketed parts), plus what to check when the assistant finishes.
- **Under the hood** — the actual steps and queries the assistant runs, kept for transparency and for assistants reading this repo directly.

Every prompt starts the same way: it hands the assistant one URL — [`llms.txt`](../llms.txt) — a single plain-text file with the connection details, both database schemas, the search functions, and the rules that prevent common errors. One fetch and the assistant is connected; no web page to parse, no files to discover. If your assistant cannot fetch URLs, paste the contents of `llms.txt` into the chat along with the prompt — it works identically.

| Walkthrough | What you get |
|---|---|
| [01 · Map the literature on a topic](01-map-a-topic.md) | Counts over time and top items on any topic, across journals and conference |
| [02 · Trend analysis with proper caveats](02-trend-analysis.md) | How the discipline's scholarship changed 1989–2023, with honest caveats |
| [03 · A scholar's twenty-year arc](03-scholar-trajectory.md) | One researcher's conference history: topics, collaborators, moves |
| [04 · Build a screening corpus](04-screening-corpus.md) | A high-recall CSV of candidates for a systematic or scoping review |
| [05 · A verified topical corpus, extended past the release](05-verified-topic-corpus-with-wos-extension.md) | Every article on a topic, verified by reading, with a separate Web of Science extension |
| [06 · Classify what a literature does](06-classify-what-a-literature-does.md) | Empirical vs. reception vs. commentary composition, by era and venue |
| [07 · Co-authorship networks with thresholds](07-coauthorship-networks-with-thresholds.md) | A readable network of the frequent authors, with explicit inclusion rules |

The fully worked artifact behind 05–07 (verified corpora, labels, figures, and scripts from the AI-in-social-work analysis) lives in [`analyses/ai-in-social-work/`](../analyses/ai-in-social-work/).

## Writing prompts that work with these databases

A few habits make the difference between a plausible-looking answer and a checkable one:

1. **Hand the assistant `llms.txt`, not the website.** Start every prompt with "Fetch https://beperron.github.io/SocialWork-MetaData/llms.txt and connect exactly as it describes." That one file carries the endpoint, key, schemas, and query rules, so the assistant starts querying immediately instead of exploring.
2. **Say "nothing to install," and mean it.** The recipes use only the built-in full-text search and SQL over HTTPS. Adding "use the built-in search and SQL only; do not install anything beyond common Python libraries (requests, pandas, matplotlib)" to the prompt keeps assistants from wandering into local model tooling while still letting them chart and export. (The databases also support semantic search via a local embedding model — see the [skill files](../skills/) — but no recipe requires it.)
3. **Name the deliverable.** "Give me a chart and a five-sentence summary" gets you a chart and a summary; "analyze X" gets you whatever the assistant felt like.
4. **Ask for verification, not just results.** Add "read the abstracts of the matches and remove false positives, and tell me what you removed and why." The databases make this cheap; unverified keyword counts are the single biggest source of wrong answers.
5. **Ask for the caveats.** "State what your counts do not cover" surfaces the boundary decisions (journal set, incomplete recent years, abstract-only coding) that a reviewer would ask about.
6. **Keep arithmetic auditable.** Ask the assistant to report counts stepwise (raw, removed, kept) and to show its work when numbers disagree.
7. **Check a sample yourself.** Every recipe ends with a "what to check" note. Ten spot-checks catch most problems.

The prompts in the recipes bake these habits in; adapting them to a new question is usually just changing the bracketed topic.
