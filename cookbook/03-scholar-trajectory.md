# 03 · A Scholar's Twenty-Year Arc

**Goal:** trace one researcher's conference activity across two decades — topics, collaborators, institutional moves. Uses the SSWR database's disambiguated authors. SQL only; no Ollama needed.

**Skills used:** `sswr-database`.

## Step 1 — Resolve the person (never skip this)

Canonical names are "First Last," sometimes with credentials, and a few residual duplicates exist. Always start with fuzzy lookup:

```python
import requests
KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
     "Content-Profile": "sswr", "Content-Type": "application/json"}
def run_sql(q): return requests.post(f"{BASE}/rpc/run_sql", headers=H, json={"query": q}).json()

run_sql("select author_id, author_name, total_papers from sswr.search_authors_by_name('michael vaughn', 5)")
# → e.g. 108089 "Michael G. Vaughn" (89 papers) and a residual 123182 "Vaughn Michael" (5)
```

If near-duplicates appear, either include both ids or report the ambiguity. Everything below uses `author_id`, never name strings.

## Step 2 — The presentation record

```sql
select p.year, p.title, p.methodology, pa.author_order,
       case when pa.author_order = 1 then 'first author' else '' end as role
from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id
where pa.author_id = 108089
order by p.year, p.id
```

## Step 3 — Activity shape

```sql
select p.year, count(*) as presentations,
       count(*) filter (where pa.author_order = 1) as first_authored
from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id
where pa.author_id = 108089 group by 1 order by 1
```

## Step 4 — Collaboration network

```sql
select a2.name, count(*) as joint, min(p.year) as first_together, max(p.year) as last_together
from sswr.paper_authors pa1
join sswr.paper_authors pa2 on pa2.paper_id = pa1.paper_id and pa2.author_id <> pa1.author_id
join sswr.authors a2 on a2.id = pa2.author_id
join sswr.papers p on p.id = pa1.paper_id
where pa1.author_id = 108089
group by 1 order by 2 desc limit 15
```

## Step 5 — Institutional history

```sql
select p.year, pa.institution_normalized, count(*) as n
from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id
where pa.author_id = 108089 and pa.institution_normalized is not null
group by 1,2 order by 1
```

Affiliation changes across years show institutional moves as reflected in conference bylines.

## Step 6 — Topical evolution (optional; needs Ollama)

Pull the scholar's titles by era and compare, or run `search_papers_semantic` seeded with an abstract of theirs from each era to find their nearest intellectual neighbors over time.

## Reporting notes

Conference presentations are a *complement* to a publication record, not a substitute — presentations include work in progress. If the scholar also publishes in social work journals, the SWRD can add the journal side, **but only with the no-disambiguation caveat there**.
