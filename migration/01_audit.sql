-- Read-only audit of a source Supabase project's public schema.
-- Run: psql "$SRC" -v ON_ERROR_STOP=0 -f migration/01_audit.sql > audit/<name>.txt 2>&1

\echo '=== DATABASE SIZE ==='
select current_database(), pg_size_pretty(pg_database_size(current_database())) as db_size;

\echo '=== SERVER VERSION ==='
select version();

\echo '=== PER-TABLE SIZES (public) ==='
select c.relname as table_name,
       pg_size_pretty(pg_total_relation_size(c.oid)) as total_size,
       pg_size_pretty(pg_relation_size(c.oid)) as table_size
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind in ('r','m','p')
order by pg_total_relation_size(c.oid) desc;

\echo '=== EXACT ROW COUNTS ==='
select tbl as table_name, cnt as row_count from (
  select tablename as tbl,
         (xpath('/row/cnt/text()',
            query_to_xml(format('select count(*) as cnt from public.%I', tablename), false, true, '')))[1]::text::bigint as cnt
  from pg_tables where schemaname = 'public'
) t order by tbl;

\echo '=== EXTENSIONS AND THEIR SCHEMAS ==='
select e.extname, e.extversion, n.nspname as schema
from pg_extension e join pg_namespace n on n.oid = e.extnamespace
order by e.extname;

\echo '=== VECTOR COLUMNS (declared types) ==='
select c.relname as table_name, a.attname as column_name,
       format_type(a.atttypid, a.atttypmod) as declared_type
from pg_attribute a
join pg_class c on c.oid = a.attrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and a.attnum > 0 and not a.attisdropped
  and format_type(a.atttypid, a.atttypmod) like '%vector%';

\echo '=== ALL COLUMNS (parity baseline) ==='
select table_name, column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
order by table_name, ordinal_position;

\echo '=== FUNCTION DDL (live-only RPCs) ==='
select p.proname, pg_get_functiondef(p.oid) as definition
from pg_proc p join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public' and p.prokind = 'f'
order by p.proname;

\echo '=== INDEX DEFINITIONS ==='
select tablename, indexname, indexdef from pg_indexes
where schemaname = 'public' order by tablename, indexname;

\echo '=== RLS POLICIES ==='
select schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
from pg_policies where schemaname = 'public' order by tablename, policyname;

\echo '=== RLS-ENABLED TABLES ==='
select relname, relrowsecurity, relforcerowsecurity
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r' and c.relrowsecurity;

\echo '=== TRIGGERS ==='
select event_object_table, trigger_name, action_timing, event_manipulation
from information_schema.triggers where trigger_schema = 'public'
order by event_object_table, trigger_name;

\echo '=== VIEWS / MATVIEWS ==='
select table_name, table_type from information_schema.tables
where table_schema = 'public' and table_type <> 'BASE TABLE';
select matviewname from pg_matviews where schemaname = 'public';

\echo '=== SEQUENCES ==='
select sequencename, last_value from pg_sequences where schemaname = 'public';

\echo '=== NON-PUBLIC SURFACE: auth.users ==='
select count(*) as auth_users from auth.users;

\echo '=== NON-PUBLIC SURFACE: storage.buckets ==='
select id, name, public from storage.buckets;

\echo '=== NON-PUBLIC SURFACE: storage object counts ==='
select bucket_id, count(*) from storage.objects group by bucket_id;

\echo '=== NON-PUBLIC SURFACE: pg_cron jobs (errors harmlessly if absent) ==='
select * from cron.job;
