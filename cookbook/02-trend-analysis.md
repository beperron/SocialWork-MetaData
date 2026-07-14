# 02 · Trend Analysis with Proper Caveats

**Goal:** describe how social work scholarship has changed over time — volume, empiricism, methodology — with the caveats a reviewer would demand. SQL only; no Ollama needed.

**Skills used:** `swrd-database` (its `references/queries.md` has more variants).

## Step 1 — Establish the analyzable corpus

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

## Step 2 — Volume and empiricism over time

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

## Step 3 — Methodological composition by decade

```sql
select (publication_year/10)*10 as decade, research_method, count(*) as n
from swrd.papers
where publication_year between 1989 and 2023 and is_empirical
group by 1,2 order by 1,2
```

Compute within-decade percentages when presenting; raw counts conflate growth with composition.

## Step 4 — Collaboration trend (article-level, safe despite no author disambiguation)

```sql
select (p.publication_year/10)*10 as decade, round(avg(a.n),2) as mean_authors,
       round(100.0 * count(*) filter (where a.n = 1) / count(*), 1) as pct_solo
from (select paper_id, count(*) as n from swrd.paper_authors group by 1) a
join swrd.papers p on p.id = a.paper_id
where p.publication_year between 1989 and 2023
group by 1 order by 1
```

## Step 5 — Cross-validate against the conference record

Run the same questions against SSWR (`Content-Profile: sswr`; `methodology` values are lowercase there). Agreement between the two independent corpora strengthens any trend claim — the 2026 article does exactly this comparison.

## Reporting checklist

- ☐ Corpus definition stated (scientific + abstract-bearing, 1989–2023)
- ☐ 2024–25 excluded from trends, and why
- ☐ Percentages within-year/decade, not raw counts, for composition claims
- ☐ Pre-1989 data (if used at all) labeled as lower bounds
- ☐ Citation: Perron, Victor, & Qi (2026), doi:10.1177/10497315261416833
