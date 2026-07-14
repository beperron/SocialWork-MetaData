# SWRD — Tested SQL Recipes

All queries run through the `run_sql` endpoint (see SKILL.md) or any SQL context. Rules: single SELECT, no trailing semicolon, 30s timeout, 1,000-row cap per call. Every recipe below has been executed against the live database.

## Corpus scoping (start most analyses this way)

```sql
-- The citable analytic core: scientific articles with abstracts, 1989+
select count(*) from swrd.papers
where publication_year >= 1989 and is_scientific
-- → 68,074 flagged scientific; 62,602 of these have abstracts (the paper's corpus)
```

## Trends

```sql
-- Publications per year (core corpus)
select publication_year, count(*) as n
from swrd.papers
where publication_year between 1989 and 2025 and is_scientific
group by 1 order by 1

-- Methodology composition by decade
select (publication_year/10)*10 as decade, research_method, count(*) as n
from swrd.papers where is_empirical
group by 1,2 order by 1,2

-- Share empirical over time
select publication_year,
       round(100.0 * count(*) filter (where is_empirical) / count(*), 1) as pct_empirical
from swrd.papers
where publication_year >= 1989 and is_scientific and abstract is not null
group by 1 order by 1
```

## Topic slices (keyword; for concept search use hybrid — see semantic-search.md)

```sql
-- Count and range for a topic
select count(*) as n, min(publication_year) as first_year, max(publication_year) as last_year
from swrd.papers
where publication_year >= 1989
  and (title ilike '%kinship care%' or abstract ilike '%kinship care%')

-- The actual records (paginate with offset)
select id, title, publication_year, times_cited, doi
from swrd.papers
where publication_year >= 1989
  and (title ilike '%kinship care%' or abstract ilike '%kinship care%')
order by publication_year desc
limit 100 offset 0
```

## Journals

```sql
-- Output by journal
select j.name, count(*) as n, round(avg(p.times_cited),1) as mean_cited
from swrd.papers p join swrd.journals j on j.id = p.journal_id
where p.publication_year >= 1989
group by 1 order by 2 desc

-- Most-cited articles in one journal
select p.title, p.publication_year, p.times_cited
from swrd.papers p join swrd.journals j on j.id = p.journal_id
where j.name = 'Social Service Review'
order by p.times_cited desc nulls last limit 10
```

## Citations

```sql
-- Uncited share by decade (cf. 17.5% overall in the 2026 article)
select (publication_year/10)*10 as decade,
       round(100.0 * count(*) filter (where times_cited = 0) / count(*), 1) as pct_uncited
from swrd.papers
where publication_year >= 1989 and is_scientific and times_cited is not null
group by 1 order by 1
```

## Authorship (remember: names NOT disambiguated)

```sql
-- Mean authors per article by decade (article-level: reliable)
select (p.publication_year/10)*10 as decade, round(avg(a.n),2) as mean_authors
from (select paper_id, count(*) as n from swrd.paper_authors group by 1) a
join swrd.papers p on p.id = a.paper_id
where p.publication_year >= 1989
group by 1 order by 1

-- Full author list for one paper (names as published)
select a.name, pa.position, pa.is_corresponding
from swrd.paper_authors pa join swrd.authors a on a.id = pa.author_id
where pa.paper_id = 12345 order by pa.position   -- replace with a real id

-- Author-name search (CAVEAT in any output: variants of one person count separately)
select a.name, count(*) as papers
from swrd.authors a join swrd.paper_authors pa on pa.author_id = a.id
where a.name ilike '%perron%'
group by 1 order by 2 desc
```

## Affiliations

```sql
-- Most frequent organizations (as-reported strings; not normalized)
select o.name, count(distinct aa.paper_id) as papers
from swrd.author_affiliations aa join swrd.organizations o on o.id = aa.organization_id
group by 1 order by 2 desc limit 20
```

## The Supplement (pre-1989 — always caveat as lower bounds)

```sql
select (publication_year/10)*10 as decade, count(*) as n,
       round(100.0 * count(abstract) / count(*), 1) as pct_with_abstract
from swrd.papers where publication_year < 1989
group by 1 order by 1
```

## Pagination past the 1,000-row cap

```sql
select id, title from swrd.papers where publication_year >= 1989 order by id limit 1000 offset 0
-- then offset 1000, 2000, … (stable because ordered by id)
```
