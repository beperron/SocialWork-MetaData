# 02 · Trend Analysis with Proper Caveats

**Goal:** describe how social work scholarship has changed over time — volume, empiricism, methodology — with the caveats a reviewer would demand. SQL only; nothing to install.

**Reference:** [`llms.txt`](../llms.txt) (connection + schema); `skills/swrd-database/references/queries.md` has more query variants.


## Do this with Claude or Codex

This one is SQL-only, so any assistant with web access can run it; no local install of anything.

Copy and paste:

> I'm using the Social Work Meta-Data Project's hosted databases (public read-only key, plain HTTPS, nothing to install). Fetch https://beperron.github.io/SocialWork-MetaData/llms.txt and connect exactly as it describes (the endpoint is a POST API queried from a shell or code tool, not a page-fetch tool) — that one file has the endpoint, key, and schema. Using the swrd database, describe how social work scholarship changed from 1989 to 2023: articles per year, percent empirical over time, methodology mix by decade, and team size trends. Exclude 2024-2025 from trend claims because publisher indexing is incomplete, and state that caveat in your summary. Give me a short written summary plus one chart. Use SQL only; do not install anything beyond common Python libraries (requests, pandas, matplotlib).

*If your assistant cannot fetch URLs, download [llms.txt](../llms.txt) and paste its contents into the chat together with the prompt.*

**What to check when it finishes.** The assistant should volunteer the incomplete-recent-years caveat without being reminded twice, and its percentages should be within-decade shares, not raw counts. Ask it to re-run one number a second way if anything looks off.

## Under the hood — the steps the assistant runs

### Step 1 — Establish the analyzable corpus

```python
import requests
KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
     "Content-Profile": "swrd", "Content-Type": "application/json"}
def run_sql(q): return requests.post(f"{BASE}/rpc/run_sql", headers=H, json={"query": q}).json()

run_sql("select count(*) as total, count(*) filter (where abstract is not null) as with_abstract "
        "from swrd.papers where publication_year >= 1989 and is_scientific")
```

State in the report: classifications exist only where abstracts exist; analysis of methodology is therefore of the abstract-bearing scientific corpus (62,602 records), per Perron, Victor, & Qi (2026).

### Step 2 — Volume and empiricism over time

```sql
select publication_year as year,
       count(*) as scientific_articles,
       round(100.0 * count(*) filter (where is_empirical) / count(*), 1) as pct_empirical
from swrd.papers
where publication_year between 1989 and 2023   -- exclude 2024–25: publisher schedules incomplete
  and is_scientific and abstract is not null
group by 1 order by 1
```

(The 2026 article excludes 2024–2025 from trend analysis for exactly this reason — mirror that choice.)

### Step 3 — Methodological composition by decade

```sql
select (publication_year/10)*10 as decade, research_method, count(*) as n
from swrd.papers
where publication_year between 1989 and 2023 and is_empirical
group by 1,2 order by 1,2
```

Compute within-decade percentages when presenting; raw counts conflate growth with composition.

### Step 4 — Collaboration trend (article-level, safe despite no author disambiguation)

```sql
select (p.publication_year/10)*10 as decade, round(avg(a.n),2) as mean_authors,
       round(100.0 * count(*) filter (where a.n = 1) / count(*), 1) as pct_solo
from (select paper_id, count(*) as n from swrd.paper_authors group by 1) a
join swrd.papers p on p.id = a.paper_id
where p.publication_year between 1989 and 2023
group by 1 order by 1
```

### Step 5 — Cross-validate against the conference record

Run the same questions against SSWR (`Content-Profile: sswr`; `methodology` values are lowercase there). Agreement between the two independent corpora strengthens any trend claim — the 2026 article does exactly this comparison.

## Reporting checklist

- ☐ Corpus definition stated (scientific + abstract-bearing, 1989–2023)
- ☐ 2024–25 excluded from trends, and why
- ☐ Percentages within-year/decade, not raw counts, for composition claims
- ☐ Pre-1989 data (if used at all) labeled as lower bounds
- ☐ Citation: Perron, Victor, & Qi (2026), doi:10.1177/10497315261416833
