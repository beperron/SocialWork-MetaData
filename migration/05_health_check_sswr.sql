-- SSWR data-quality health check. Run against the consolidated DB.
-- psql "$TGT" -f migration/05_health_check_sswr.sql

\echo '=== SSWR: PAPERS WITHOUT AUTHORS ==='
select count(*) as papers_without_authors from sswr.papers p
where not exists (select 1 from sswr.paper_authors pa where pa.paper_id = p.id);

\echo '=== SSWR: ORPHANED paper_authors ==='
select count(*) filter (where p.id is null) as missing_paper,
       count(*) filter (where pa.author_id is not null and a.id is null) as missing_author
from sswr.paper_authors pa
left join sswr.papers p on p.id = pa.paper_id
left join sswr.authors a on a.id = pa.author_id;

\echo '=== SSWR: paper_authors WITHOUT author_id LINK (unresolved entities) ==='
select count(*) as unlinked, round(100.0*count(*)/ (select count(*) from sswr.paper_authors),1) as pct
from sswr.paper_authors where author_id is null;

\echo '=== SSWR: ORPHANED html mappings ==='
select count(*) as orphaned_mappings from sswr.paper_html_mappings m
where m.paper_id is not null and not exists (select 1 from sswr.papers p where p.id = m.paper_id);

\echo '=== SSWR: PAPERS NOT COVERED BY html mapping ==='
select count(*) as papers_without_html_source from sswr.papers p
where not exists (select 1 from sswr.paper_html_mappings m where m.paper_id = p.id);

\echo '=== SSWR: DUPLICATE PAPER IDs BY (title, year) ==='
select count(*) as dup_title_year_groups from (
  select lower(title), year from sswr.papers group by 1,2 having count(*) > 1
) t;

\echo '=== SSWR: NULL-RATE PROFILE (papers) ==='
select count(*) as total,
  count(title) as has_title, round(100.0*count(title)/count(*),1) as pct_title,
  count(abstract) as has_abstract, round(100.0*count(abstract)/count(*),1) as pct_abstract,
  count(methodology) as has_methodology, round(100.0*count(methodology)/count(*),1) as pct_methodology,
  count(fts) as has_fts, round(100.0*count(fts)/count(*),1) as pct_fts
from sswr.papers;

\echo '=== SSWR: YEAR RANGE + DISTRIBUTION ==='
select min(year) as min_year, max(year) as max_year,
       count(*) filter (where year < 2005 or year > 2026) as out_of_expected_range
from sswr.papers;

\echo '=== SSWR: author_count FIELD CONSISTENCY vs ACTUAL LINKS ==='
select count(*) as mismatched_author_count from (
  select p.id, p.author_count, count(pa.id) as actual
  from sswr.papers p left join sswr.paper_authors pa on pa.paper_id = p.id
  group by p.id, p.author_count
  having p.author_count is distinct from count(pa.id)::int
) x;

\echo '=== SSWR: CANONICAL AUTHOR MAPPING INTEGRITY ==='
select count(*) filter (where a1.id is null) as bad_author_fk,
       count(*) filter (where a2.id is null) as bad_canonical_fk
from sswr.author_canonical_mapping m
left join sswr.authors a1 on a1.id = m.author_id
left join sswr.authors a2 on a2.id = m.canonical_author_id;

\echo '=== SSWR: EMBEDDING SHELL READY (0 rows, correct types) ==='
select count(*) as embedding_rows from sswr.paper_embeddings;
select a.attname, format_type(a.atttypid, a.atttypmod)
from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
where n.nspname='sswr' and c.relname='paper_embeddings' and a.attnum>0 and not a.attisdropped;

\echo '=== SSWR: SEQUENCE HEALTH ==='
select 'authors' t, (select last_value from sswr.authors_canonical_id_seq) seq, (select max(id) from sswr.authors) max_id
union all select 'paper_authors', (select last_value from sswr.paper_authors_id_seq1), (select max(id) from sswr.paper_authors)
union all select 'institution_mappings', (select last_value from sswr.institution_mappings_id_seq), (select max(id) from sswr.institution_mappings);
