-- Run AFTER a source's restore into public is verified.
-- Usage: psql "$TGT" -v schema_name=sswr -f migration/02_rename_and_grants.sql

ALTER SCHEMA public RENAME TO :schema_name;
CREATE SCHEMA public;
ALTER SCHEMA public OWNER TO postgres;
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON SCHEMA public TO postgres, service_role;
COMMENT ON SCHEMA public IS 'standard public schema';

GRANT USAGE ON SCHEMA :schema_name TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA :schema_name TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA :schema_name TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA :schema_name TO anon, authenticated, service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA :schema_name TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA :schema_name GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA :schema_name GRANT SELECT ON TABLES TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA :schema_name GRANT EXECUTE ON FUNCTIONS TO anon, authenticated, service_role;
