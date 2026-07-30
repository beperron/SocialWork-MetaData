# 01 · Map the Literature on a Topic

**Goal:** given a research topic in plain language, produce a topical corpus spanning journal articles (SWRD) and conference presentations (SSWR), with counts over time and top exemplars.

**Skills used:** `ollama-embeddings`, both database skills. Example topic: *grandparents raising grandchildren*.


## Do this with Claude or Codex

You do not need to write any code. Point your assistant (Claude, ChatGPT/Codex, or similar) at the project site, name the topic, and let it run the search on both databases.

Copy, edit the bracketed parts, and paste:

> I'm using the Social Work Meta-Data Project (https://beperron.github.io/SocialWork-MetaData/). Download the skill files from the site and connect to both databases (SWRD journals and SSWR conference). Map the literature on [YOUR TOPIC] using semantic search plus keywords: give me counts over time in both databases, the top 10 most relevant items from each with year and title, and tell me which results you actually verified as on-topic by reading the abstract.

**What to check when it finishes.** Ask it how many raw matches it screened out and why; a good run names its false positives. If counts look surprisingly high or low, ask it to show 5 borderline abstracts so you can judge the boundary yourself.

## Under the hood — the steps the assistant runs

### Step 1 — Embed the question once

```python
import requests
KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
def H(schema): return {"apikey": KEY, "Authorization": f"Bearer {KEY}",
                       "Content-Profile": schema, "Content-Type": "application/json"}

topic = "grandparents raising grandchildren"
emb = requests.post("http://localhost:11434/api/embed", json={
    "model": "embeddinggemma:300m",
    "input": [f"task: search result | query: {topic}"]}).json()["embeddings"][0]
```

### Step 2 — Hybrid search on both databases (identical API)

```python
swrd = requests.post(f"{BASE}/rpc/search_papers_hybrid", headers=H("swrd"),
    json={"query_text": topic, "query_embedding": emb, "match_count": 40}).json()
sswr = requests.post(f"{BASE}/rpc/search_papers_hybrid", headers=H("sswr"),
    json={"query_text": topic, "query_embedding": emb, "match_count": 40}).json()
```

### Step 3 — Inspect why each result surfaced

Every hit carries `semantic_rank` and `keyword_rank`. Results with both ranks are safest; results with only a `semantic_rank` are the vocabulary-variant finds keyword search would have missed (e.g., papers phrased as *custodial grandparents* or *kinship caregivers*) — these are often the most valuable additions, but skim their abstracts to confirm relevance.

### Step 4 — Size the topic over time (SQL keyword sweep for recall)

```python
def run_sql(schema, q):
    return requests.post(f"{BASE}/rpc/run_sql", headers=H(schema), json={"query": q}).json()

journal_trend = run_sql("swrd", """
  select publication_year as year, count(*) as n from swrd.papers
  cross join websearch_to_tsquery('english', 'grandparents grandchildren') q
  where (to_tsvector('english', title) @@ q
         or (abstract is not null and to_tsvector('english', abstract) @@ q))
    and publication_year >= 1989
  group by 1 order by 1""")
conference_trend = run_sql("sswr", """
  select p.year, count(*) as n from sswr.papers p
  cross join websearch_to_tsquery('english', 'grandparents grandchildren') q
  where p.fts @@ q group by 1 order by 1""")
```

### Step 5 — Report

Present: (a) total matching articles and presentations; (b) the two trend lines; (c) top 10 exemplars per database with year, venue, and DOI/id; (d) a note on which exemplars were semantic-only finds. Remember the standing caveats: SWRD counts before 1989 are lower bounds, and any author counting in SWRD needs the no-disambiguation caveat.
