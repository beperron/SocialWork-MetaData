# 05 · A Verified Topical Corpus, Extended Past the Release Date

**Goal:** build a defensible corpus of every article on a topic (here: artificial intelligence), verify every record by reading, audit recall with expanded vocabulary, and extend the analysis window past SWRD's versioned release with a Web of Science supplement that stays separate from the database.

**Reference:** [`llms.txt`](../llms.txt) (connection + schema). Nothing to install.


## Do this with Claude or Codex

This is the full verified-corpus workflow behind the AI-in-social-work analysis in this repo. The Web of Science step needs your institutional access: you run the query there and hand the export to the assistant.

Copy, edit the bracketed parts, and paste:

> I'm using the Social Work Meta-Data Project's hosted databases (public read-only key, plain HTTPS, nothing to install). Fetch https://beperron.github.io/SocialWork-MetaData/llms.txt and connect exactly as it describes — that one file has the endpoint, key, and schema. Build a verified corpus from the swrd database of every article on [YOUR TOPIC], restricted to publication_year >= 1989 — that is the SWRD's systematically compiled corpus and the window of the database's published article; pre-1989 records come from an incomplete supplement and stay out. Cast a wide keyword net including historical vocabulary, then read every match and remove false positives, naming each false-positive class and reporting the arithmetic stepwise (raw, removed by class, kept). Then run a recall audit: harvest recurring vocabulary from the abstracts you kept, run additional keyword sweeps with those terms and with 2-3 rephrasings of the topic, and read any new matches. I will also give you a Web of Science export for recent years [attach it]: screen it the same way, deduplicate against SWRD by DOI, and keep it as a separate supplement file; do not merge it into the database records. Give me the labeled corpus as JSON plus a summary I can audit. Use the built-in search and SQL only; do not install anything beyond common Python libraries (requests, pandas, matplotlib).

*If your assistant cannot fetch URLs, download [llms.txt](../llms.txt) and paste its contents into the chat together with the prompt.*

> **Strongly recommended: audit recall with embeddings.** The keyword net and the Step 3 vocabulary expansion both match exact words, so they can only find phrasings someone thought of. With the one-time embedding setup ([`ollama-embeddings`](../skills/ollama-embeddings/SKILL.md), ~5 minutes), [recipe 09](09-semantic-recall-audit.md) audits the finished corpus by *meaning* — in the original AI-in-social-work analysis, exactly this kind of embedding audit recovered in-scope articles the keywords missed (decision-support papers that never say "AI").

**What to check when it finishes.** The arithmetic must add up exactly (raw minus removed equals kept) and every 100 percent of removals should be itemized. Ask what the recall audit recovered; zero recoveries on a broad topic is suspicious.

## Under the hood — the steps the assistant runs

**Worked artifact:** [`analyses/ai-in-social-work/`](../analyses/ai-in-social-work/) contains the full output of this recipe: data, labels, figures, and scripts.

### Step 1 — Cast a wide keyword net, expecting garbage

Search titles and abstracts with every phrasing of the topic, historical vocabulary included. For AI that means 17 phrases from "expert system" to "large language model," plus standalone "AI," hyphenated compounds, and GPT/LLM tokens.

```sql
select id, publication_year, title, abstract
from swrd.papers
where publication_year >= 1989   -- the systematically compiled corpus; matches the SWRD paper's window
  and (coalesce(title,'') || ' ' || coalesce(abstract,''))
      ~* '(artificial intelligence|machine learning|expert system|neural network|deep learning|chatgpt|large language model|\mai\M|...)'
```

Word-boundary anchors matter: an unanchored `ai` matches "AI/AN" (American Indian/Alaska Native) and "Appreciative Inquiry," and those false positives will dominate your raw set. The `>= 1989` filter is a design decision, not a convenience: the pre-1989 Supplement is substantially incomplete (many records lack abstracts), so including it would mix a censused corpus with a partial one. State the window in your report.

### Step 2 — Read everything; taxonomize the false positives

Every match gets read. Do not sample. Name each false-positive class as you remove it, because the classes are reusable: pedagogical "deep learning," qualitative "clinical data mining," neurobiological "neural network," sociological "expert systems," acronym collisions. Report the arithmetic stepwise (raw N, removed N by class, kept N) so a reader can audit it.

### Step 3 — Audit recall with expanded vocabulary

Keywords establish precision, not recall: the net misses papers that describe the topic in words you did not think to search. Audit for them three ways, then read every new match with the same discipline as Step 2:

1. **Harvest the corpus's own vocabulary.** Skim the kept abstracts for recurring terms that were not in the net (in our AI corpus: "decision support," "predictive analytics," specific algorithm names) and sweep each one.
2. **Rephrase the topic** two or three ways in different registers — practitioner language, older terminology, adjacent-field terms — and run the ranked keyword search (`search_papers_keyword`) with each phrasing.
3. **Follow the false-positive classes backward.** A class you removed (pedagogical "deep learning") often names a nearby literature whose genuine members use vocabulary worth one sweep.

In our AI corpus, an audit of this kind recovered a handful of in-scope articles, each traceable to a nameable vocabulary gap — tree-model studies that never say "machine learning," decision-support papers that never say "AI." When a sweep stops yielding anything new, stop: recall auditing has diminishing returns, and the honest report states the vocabulary actually searched.

### Step 4 — Extend past the release with a supplement that stays separate

SWRD's versioned release has an end date; the literature does not. Run the same keyword net in Web of Science restricted to the same journal list, overlapping the last released year so you can validate coverage:

- Export, then screen with the same false-positive discipline.
- Deduplicate against SWRD by DOI. If every record from the overlap year is a duplicate, the database's layer for that year is complete and the gap is confined to the corpus edge.
- Keep the supplement as its own file with its own labels. Do not merge it into the database records: the versioned release stays clean, and any analysis states "SWRD + supplement" explicitly.

### Step 5 — Report the corpus with its boundary

State the journal-set boundary as a design decision, report the corpus as a lower bound, and publish the labeled list so others can re-screen. The counts are only as credible as the reader's ability to check them.
