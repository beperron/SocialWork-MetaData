# 05 · A Verified Topical Corpus, Extended Past the Release Date

**Goal:** build a defensible corpus of every article on a topic (here: artificial intelligence), verify every record by reading, audit recall semantically, and extend the analysis window past SWRD's versioned release with a Web of Science supplement that stays separate from the database.

**Skills used:** `swrd-database`, `ollama-embeddings` (for the recall audit only).


## Do this with Claude or Codex

This is the full verified-corpus workflow behind the AI-in-social-work analysis in this repo. The Web of Science step needs your institutional access: you run the query there and hand the export to the assistant.

Copy, edit the bracketed parts, and paste:

> I'm using the Social Work Meta-Data Project (https://beperron.github.io/SocialWork-MetaData/). Download the skills from the site and connect to SWRD. Build a verified corpus of every article on [YOUR TOPIC]: cast a wide keyword net including historical vocabulary, then read every match and remove false positives, naming each false-positive class and reporting the arithmetic stepwise (raw, removed by class, kept). Then run a semantic recall audit with the embeddings to catch what the keywords missed. I will also give you a Web of Science export for recent years [attach it]: screen it the same way, deduplicate against SWRD by DOI, and keep it as a separate supplement file; do not merge it into the database records. Give me the labeled corpus as JSON plus a summary I can audit.

**What to check when it finishes.** The arithmetic must add up exactly (raw minus removed equals kept) and every 100 percent of removals should be itemized. Ask what the recall audit recovered; zero recoveries on a broad topic is suspicious.

## Under the hood — the steps the assistant runs

**Worked artifact:** [`analyses/ai-in-social-work/`](../analyses/ai-in-social-work/) contains the full output of this recipe: data, labels, figures, and scripts.

### Step 1 — Cast a wide keyword net, expecting garbage

Search titles and abstracts with every phrasing of the topic, historical vocabulary included. For AI that means 17 phrases from "expert system" to "large language model," plus standalone "AI," hyphenated compounds, and GPT/LLM tokens.

```sql
select id, publication_year, title, abstract
from swrd.papers
where (coalesce(title,'') || ' ' || coalesce(abstract,''))
      ~* '(artificial intelligence|machine learning|expert system|neural network|deep learning|chatgpt|large language model|\mai\M|...)'
```

Word-boundary anchors matter: an unanchored `ai` matches "AI/AN" (American Indian/Alaska Native) and "Appreciative Inquiry," and those false positives will dominate your raw set.

### Step 2 — Read everything; taxonomize the false positives

Every match gets read. Do not sample. Name each false-positive class as you remove it, because the classes are reusable: pedagogical "deep learning," qualitative "clinical data mining," neurobiological "neural network," sociological "expert systems," acronym collisions. Report the arithmetic stepwise (raw N, removed N by class, kept N) so a reader can audit it.

### Step 3 — Audit recall with embeddings, then distrust both directions

Keywords establish precision, not recall. Embed two or three natural-language statements of the corpus definition, pull the ~300 nearest abstracts per query, and read every high-similarity record the keywords missed. In our AI corpus this recovered seven in-scope articles, each from a nameable vocabulary gap ("decision support," tree studies that never say "machine learning"). Below the similarity band where precision collapses, stop: embeddings cannot replace keyword screening either.

### Step 4 — Extend past the release with a supplement that stays separate

SWRD's versioned release has an end date; the literature does not. Run the same keyword net in Web of Science restricted to the same journal list, overlapping the last released year so you can validate coverage:

- Export, then screen with the same false-positive discipline.
- Deduplicate against SWRD by DOI. If every record from the overlap year is a duplicate, the database's layer for that year is complete and the gap is confined to the corpus edge.
- Keep the supplement as its own file with its own labels. Do not merge it into the database records: the versioned release stays clean, and any analysis states "SWRD + supplement" explicitly.

### Step 5 — Report the corpus with its boundary

State the journal-set boundary as a design decision, report the corpus as a lower bound, and publish the labeled list so others can re-screen. The counts are only as credible as the reader's ability to check them.
