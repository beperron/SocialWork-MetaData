# 05 · A Verified Topical Corpus, Extended Past the Release Date

**Goal:** build a defensible corpus of every article on a topic (here: artificial intelligence), verify every record by reading, audit recall semantically, and extend the analysis window past SWRD's versioned release with a Web of Science supplement that stays separate from the database.

**Skills used:** `swrd-database`, `ollama-embeddings` (for the recall audit only).

**Worked artifact:** [`analyses/ai-in-social-work/`](../analyses/ai-in-social-work/) contains the full output of this recipe: data, labels, figures, and scripts.

## Step 1 — Cast a wide keyword net, expecting garbage

Search titles and abstracts with every phrasing of the topic, historical vocabulary included. For AI that means 17 phrases from "expert system" to "large language model," plus standalone "AI," hyphenated compounds, and GPT/LLM tokens.

```sql
select id, publication_year, title, abstract
from swrd.papers
where (coalesce(title,'') || ' ' || coalesce(abstract,''))
      ~* '(artificial intelligence|machine learning|expert system|neural network|deep learning|chatgpt|large language model|\mai\M|...)'
```

Word-boundary anchors matter: an unanchored `ai` matches "AI/AN" (American Indian/Alaska Native) and "Appreciative Inquiry," and those false positives will dominate your raw set.

## Step 2 — Read everything; taxonomize the false positives

Every match gets read. Do not sample. Name each false-positive class as you remove it, because the classes are reusable: pedagogical "deep learning," qualitative "clinical data mining," neurobiological "neural network," sociological "expert systems," acronym collisions. Report the arithmetic stepwise (raw N, removed N by class, kept N) so a reader can audit it.

## Step 3 — Audit recall with embeddings, then distrust both directions

Keywords establish precision, not recall. Embed two or three natural-language statements of the corpus definition, pull the ~300 nearest abstracts per query, and read every high-similarity record the keywords missed. In our AI corpus this recovered seven in-scope articles, each from a nameable vocabulary gap ("decision support," tree studies that never say "machine learning"). Below the similarity band where precision collapses, stop: embeddings cannot replace keyword screening either.

## Step 4 — Extend past the release with a supplement that stays separate

SWRD's versioned release has an end date; the literature does not. Run the same keyword net in Web of Science restricted to the same journal list, overlapping the last released year so you can validate coverage:

- Export, then screen with the same false-positive discipline.
- Deduplicate against SWRD by DOI. If every record from the overlap year is a duplicate, the database's layer for that year is complete and the gap is confined to the corpus edge.
- Keep the supplement as its own file with its own labels. Do not merge it into the database records: the versioned release stays clean, and any analysis states "SWRD + supplement" explicitly.

## Step 5 — Report the corpus with its boundary

State the journal-set boundary as a design decision, report the corpus as a lower bound, and publish the labeled list so others can re-screen. The counts are only as credible as the reader's ability to check them.
