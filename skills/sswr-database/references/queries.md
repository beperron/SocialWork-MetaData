# SSWR — Tested SQL Recipes

All queries run through the `run_sql` endpoint (see SKILL.md). Rules: single SELECT, no trailing semicolon, 30s timeout, 1,000-row cap. Every recipe below has been executed against the live database.

## Overview & trends

```sql
-- Presentations per conference year (coverage is complete)
select year, count(*) as n from sswr.papers group by 1 order by 1

-- Methodology composition over time
select year, methodology, count(*) as n
from sswr.papers group by 1,2 order by 1,2

-- Format mix (posters vs orals vs symposia)
select format, count(*) as n from sswr.papers group by 1 order by 2 desc
```

## Scholar analyses (the flagship use — authors are disambiguated)

```sql
-- STEP 1: always resolve the person first (canonical names are "First Last",
-- sometimes with credentials, e.g. "Brian Perron, PhD")
select author_id, author_name, total_papers
from sswr.search_authors_by_name('michael vaughn', 5)

-- STEP 2: full presentation history by the returned author_id
select p.year, p.title, pa.author_order
from sswr.paper_authors pa
join sswr.papers p on p.id = pa.paper_id
where pa.author_id = 108089        -- id from step 1
order by p.year

-- A scholar's collaborators (co-presenters across all years)
select a2.name, count(*) as joint_presentations
from sswr.paper_authors pa1
join sswr.paper_authors pa2 on pa2.paper_id = pa1.paper_id and pa2.author_id <> pa1.author_id
join sswr.authors a2 on a2.id = pa2.author_id
where pa1.author_id = 108089
group by 1 order by 2 desc limit 15

-- Most prolific presenters overall
select a.name, a.total_papers from sswr.authors a
order by a.total_papers desc limit 20
```

## Institutions

```sql
-- Most active institutions in a period (first authors)
select pa.institution_normalized, count(*) as n
from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id
where pa.author_order = 1 and p.year between 2020 and 2026
group by 1 order by 2 desc limit 15

-- One institution's presence over time
select p.year, count(distinct p.id) as presentations
from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id
where pa.institution_normalized = 'University of Michigan'
group by 1 order by 1

-- Fuzzy institution lookup / autocomplete
select * from sswr.autocomplete_institutions('Mich', 10)
```

## Topic slices (keyword; for concept search use hybrid — see semantic-search.md)

```sql
-- Ranked full-text search (identical semantics to the SWRD's keyword search)
select id, title, year, rank from sswr.search_papers_keyword('opioid overdose', 20)

-- Topic trajectory over conference years
select p.year, count(*) as n
from sswr.papers p
cross join websearch_to_tsquery('english', 'artificial intelligence') q
where p.fts @@ q
group by 1 order by 1
```

## International participation

```sql
select pa.country_normalized, count(distinct pa.paper_id) as presentations
from sswr.paper_authors pa
where pa.country_normalized is not null and pa.country_normalized not in ('USA', 'United States')
group by 1 order by 2 desc limit 20
```

## Flat export (easiest shape for spreadsheets)

```sql
-- One row per presentation with author arrays, via the paper_export view
select id, title, year, canonical_authors, canonical_institutions, methodology
from sswr.paper_export where year = 2024 limit 1000
```

## Pagination past the 1,000-row cap

```sql
select id, title from sswr.papers order by id limit 1000 offset 0
-- then offset 1000, 2000, … (stable because ordered by id)
```
