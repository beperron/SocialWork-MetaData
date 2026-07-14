-- SWRD data-quality health check. Run against the consolidated DB.
-- psql "$TGT" -f migration/04_health_check_swrd.sql

\echo '=== SWRD: PAPERS WITHOUT AUTHORS ==='
select count(*) as papers_without_authors from swrd.papers p
where not exists (select 1 from swrd.paper_authors pa where pa.paper_id = p.id);

\echo '=== SWRD: AUTHORS WITHOUT PAPERS ==='
select count(*) as authors_without_papers from swrd.authors a
where not exists (select 1 from swrd.paper_authors pa where pa.author_id = a.id);

\echo '=== SWRD: ORPHANED paper_authors ==='
select count(*) filter (where p.id is null) as missing_paper,
       count(*) filter (where a.id is null) as missing_author
from swrd.paper_authors pa
left join swrd.papers p on p.id = pa.paper_id
left join swrd.authors a on a.id = pa.author_id;

\echo '=== SWRD: ORPHANED author_affiliations ==='
select count(*) filter (where a.id is null) as missing_author,
       count(*) filter (where o.id is null) as missing_org,
       count(*) filter (where p.id is null) as missing_paper
from swrd.author_affiliations aa
left join swrd.authors a on a.id = aa.author_id
left join swrd.organizations o on o.id = aa.organization_id
left join swrd.papers p on p.id = aa.paper_id;

\echo '=== SWRD: PAPERS WITH NULL JOURNAL ==='
select count(*) as papers_null_journal from swrd.papers where journal_id is null;
select count(*) as papers_bad_journal_fk from swrd.papers p
where journal_id is not null and not exists (select 1 from swrd.journals j where j.id = p.journal_id);

\echo '=== SWRD: DUPLICATE DOIs ==='
select count(*) as duplicate_doi_groups from (
  select doi from swrd.papers where doi is not null group by doi having count(*) > 1
) d;

\echo '=== SWRD: DUPLICATE wos_uid / scopus_eid ==='
select (select count(*) from (select wos_uid from swrd.papers where wos_uid is not null group by wos_uid having count(*) > 1) x) as dup_wos,
       (select count(*) from (select scopus_eid from swrd.papers where scopus_eid is not null group by scopus_eid having count(*) > 1) y) as dup_scopus;

\echo '=== SWRD: EXACT-TITLE DUPLICATE CANDIDATES (same title+year) ==='
select count(*) as dup_title_year_groups from (
  select lower(title), publication_year from swrd.papers
  group by 1, 2 having count(*) > 1
) t;

\echo '=== SWRD: NULL-RATE PROFILE (papers) ==='
select count(*) as total,
  count(doi) as has_doi, round(100.0*count(doi)/count(*),1) as pct_doi,
  count(abstract) as has_abstract, round(100.0*count(abstract)/count(*),1) as pct_abstract,
  count(publication_year) as has_year, round(100.0*count(publication_year)/count(*),1) as pct_year,
  count(journal_id) as has_journal, round(100.0*count(journal_id)/count(*),1) as pct_journal,
  count(is_scientific) as has_is_scientific, round(100.0*count(is_scientific)/count(*),1) as pct_classified
from swrd.papers;

\echo '=== SWRD: YEAR RANGE SANITY ==='
select min(publication_year) as min_year, max(publication_year) as max_year,
       count(*) filter (where publication_year < 1900 or publication_year > 2027) as out_of_range
from swrd.papers;

\echo '=== SWRD: CITATION SANITY ==='
select min(times_cited) as min_cited, max(times_cited) as max_cited,
       count(*) filter (where times_cited < 0) as negative
from swrd.papers;

\echo '=== SWRD: DATA SOURCE DISTRIBUTION ==='
select data_source, count(*) from swrd.papers group by 1 order by 2 desc;

\echo '=== SWRD: AUTHOR POSITION SANITY (papers with no position-1 author) ==='
select count(*) as papers_missing_first_author from swrd.papers p
where exists (select 1 from swrd.paper_authors pa where pa.paper_id = p.id)
  and not exists (select 1 from swrd.paper_authors pa where pa.paper_id = p.id and pa."position" = 1);

\echo '=== SWRD: DUPLICATE AUTHOR NAMES (entity-resolution signal, informational) ==='
select count(*) as exact_name_dup_groups from (
  select name from swrd.authors group by name having count(*) > 1
) a;

\echo '=== SWRD: SEQUENCE HEALTH (last_value must be >= max id) ==='
select 'papers' t, (select last_value from swrd.papers_id_seq) seq, (select max(id) from swrd.papers) max_id
union all select 'authors', (select last_value from swrd.authors_id_seq), (select max(id) from swrd.authors)
union all select 'organizations', (select last_value from swrd.organizations_id_seq), (select max(id) from swrd.organizations)
union all select 'journals', (select last_value from swrd.journals_id_seq), (select max(id) from swrd.journals)
union all select 'author_affiliations', (select last_value from swrd.author_affiliations_id_seq), (select max(id) from swrd.author_affiliations);
