# 01 · Map the Literature on a Topic

**Goal:** given a research topic in plain language, produce a topical corpus spanning journal articles (SWRD) and conference presentations (SSWR), with counts over time and top exemplars. Nothing to install — the built-in full-text search and SQL do all the work.

**Reference:** [`llms.txt`](../llms.txt) carries the connection details and schema; the [database skill files](../skills/) go deeper. Example topic: *grandparents raising grandchildren*.


## Do this with Claude or Codex

You do not need to write any code. The prompt hands your assistant one plain-text file with everything it needs — connection, schema, search functions — so it can start querying immediately.

Copy, edit the bracketed parts, and paste:

> I'm using the Social Work Meta-Data Project's hosted databases (public read-only key, plain HTTPS, nothing to install). Fetch https://beperron.github.io/SocialWork-MetaData/llms.txt and connect exactly as it describes (the endpoint is a POST API queried from a shell or code tool, not a page-fetch tool) — that one file has the endpoint, key, schema, and search functions. Map the literature on [YOUR TOPIC] across both databases (swrd journals and sswr conference): run the built-in keyword search with my topic and with 2-3 rephrasings in different vocabulary, plus a full-text SQL sweep of the topic terms for per-year counts of matching items (not whole-database counts). Give me the topic's counts over time in both databases, the top 10 most relevant items from each with year and title, and tell me which results you actually verified as on-topic by reading the abstract. Use the built-in search and SQL only; do not install anything beyond common Python libraries (requests, pandas, matplotlib).

*If your assistant cannot fetch URLs, download [llms.txt](../llms.txt) and paste its contents into the chat together with the prompt.*

> **Strongly recommended: add the semantic arm.** Keyword search finds only exact matches — papers that use your words. The literature rarely agrees on vocabulary (*grandparents raising grandchildren* is also *custodial grandparents*, *kinship caregivers*, and *grandfamilies*), and rephrasings only catch the variants you thought of. With the one-time embedding setup ([`ollama-embeddings`](../skills/ollama-embeddings/SKILL.md), ~5 minutes), [recipe 08](08-semantic-search-beyond-keywords.md) finds papers by *meaning* regardless of wording — run it alongside this recipe whenever completeness matters.

**What to check when it finishes.** Ask it how many raw matches it screened out and why; a good run names its false positives. If counts look surprisingly high or low, ask it to show 5 borderline abstracts so you can judge the boundary yourself.

## Under the hood — the steps the assistant runs

### Step 1 — Ranked full-text search on both databases (identical API)

```python
import requests
KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
def run_sql(schema, q):
    return requests.post(f"{BASE}/rpc/run_sql",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Profile": schema, "Content-Type": "application/json"},
        json={"query": q}).json()

topic = "grandparents raising grandchildren"
swrd = run_sql("swrd", f"select id, title, publication_year, rank from swrd.search_papers_keyword('{topic}', 40)")
sswr = run_sql("sswr", f"select id, title, year, rank from sswr.search_papers_keyword('{topic}', 40)")
```

### Step 2 — Rephrase to catch vocabulary variants

One phrasing misses the papers that say it differently. Re-run the search with 2–3 rephrasings that use different vocabulary — for this topic, *custodial grandparents*, *kinship caregivers*, *grandfamilies* — and union the results by `id`. These variant finds are often the most valuable additions; skim their abstracts to confirm relevance.

```python
candidates = {h["id"]: h for h in swrd}
for ph in ["custodial grandparents", "kinship caregiver grandchild", "grandfamilies"]:
    for h in run_sql("swrd", f"select id, title, publication_year, rank from swrd.search_papers_keyword('{ph}', 40)"):
        candidates.setdefault(h["id"], h)
```

### Step 3 — Size the topic over time (SQL keyword sweep for recall)

```python
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

### Step 4 — Verify before reporting

Read the abstracts of the top candidates and drop the off-topic matches (a keyword hit is a hypothesis, not a finding). Name what was removed and why.

### Step 5 — Report

Present: (a) total matching articles and presentations; (b) the two trend lines; (c) top 10 exemplars per database with year, venue, and DOI/id; (d) a note on which exemplars came from the rephrasings rather than the original wording. Remember the standing caveats: SWRD counts before 1989 are lower bounds, and any author counting in SWRD needs the no-disambiguation caveat.
