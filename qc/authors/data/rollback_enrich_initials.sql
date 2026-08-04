-- Reverse of enrich_initials.sql. Nothing else was written, so the rollback
-- destroys nothing observed — the first change in this project for which that
-- is true.
--   psql "$TGT" -v ON_ERROR_STOP=1 -f rollback_enrich_initials.sql
drop table if exists swrd.author_name_enrichment;
