# Reconnecting Apps & Scripts to the Consolidated Database

**Project:** `SocialWork-MetaData` (`kcffctxedcscvvposypb`, ca-central-1, org UM-DataLab)
**URL:** `https://kcffctxedcscvvposypb.supabase.co`
**Schemas:** `sswr` (SSWR conference metadata) · `swrd` (journal-article metadata). Nothing lives in `public`.
**Keys:** publishable + secret keys in Dashboard → Settings → API Keys (publishable key also in this repo's `.env`). Never hardcode keys in scripts — use env vars.

The one change every client needs: **name the schema explicitly.** Clients default to `public`, which is empty.

## supabase-js (Next.js / web)
```ts
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,        // https://kcffctxedcscvvposypb.supabase.co
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,   // sb_publishable_...
  { db: { schema: 'sswr' } }                    // or 'swrd'
)
// per-call override:
const { data } = await supabase.schema('swrd').from('papers_with_journals').select('*').limit(10)
// RPC:
const { data: hits } = await supabase.rpc('search_papers_keyword', { query_text: 'poverty', match_count: 10 })
```

## supabase-py (Python pipelines)
```python
import os
from supabase import create_client
from supabase.lib.client_options import ClientOptions

supabase = create_client(
    os.environ["SUPABASE_URL"],                # https://kcffctxedcscvvposypb.supabase.co
    os.environ["SUPABASE_KEY"],                # sb_secret_... for pipelines, sb_publishable_... for read-only
    options=ClientOptions(schema="swrd"),
)
# per-call override:
rows = supabase.schema("sswr").table("papers").select("id,title").limit(5).execute()
```

## psycopg2 / direct Postgres (DDL, bulk work)
```python
conn = psycopg2.connect(os.environ["SUPABASE_DB_CONNECTION"])  # session pooler, port 5432
cur = conn.cursor()
cur.execute("SET search_path = swrd, extensions;")   # or sswr, extensions
```
Connection string: `postgresql://postgres.kcffctxedcscvvposypb:<DB_PASSWORD>@aws-1-ca-central-1.pooler.supabase.com:5432/postgres` (check exact pooler host in Dashboard → Connect).

## Raw REST (curl, fetch)
```bash
# reads: Accept-Profile selects the schema
curl "https://kcffctxedcscvvposypb.supabase.co/rest/v1/papers?select=*&limit=5" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Accept-Profile: swrd"
# writes + RPC: Content-Profile
curl -X POST ".../rest/v1/rpc/search_papers_keyword" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Content-Profile: sswr" -H "Content-Type: application/json" \
  -d '{"query_text":"poverty","match_count":10}'
```

## Grants model (tighter than Supabase default)
- `service_role` (sb_secret key): full read/write on both schemas.
- `anon` / `authenticated` (sb_publishable key): SELECT on all tables/views + EXECUTE on functions; INSERT/UPDATE additionally granted on `sswr.paper_html_mappings` (RLS-gated, as in the old project).
- Widen per-table intentionally if a rebuilt app needs more anon writes:
  `GRANT INSERT ON sswr.search_logs TO anon;` etc. (RLS policies for anon inserts on search_logs/page_views carried over — the table GRANT is the gate.)

## Re-embedding targets
- `sswr.paper_embeddings` — empty; columns: embedding vector(1536), embedding_large vector(3072), embedding_small vector(1536); HNSW indexes ready. `match_papers` (uses embedding_large) and `match_papers_small` work as soon as rows exist.
- `swrd.openai_title_abstract_embeddings` — empty; openai_embedding vector(1536), ivfflat index. SWRD has no working search RPCs (the old ones referenced a dropped table and were not migrated) — write fresh ones against this table when re-embedding.
- `ALTER TABLE ... ALTER COLUMN ... TYPE extensions.vector(<dims>)` first if you switch to a different-dimension model (drop/recreate the vector index around it).

## Old projects (unchanged, still running)
- SSWR `jomsksqqcpkbuhwytovo` — still holds fence-sync app (table + storage + auth user) and the original embeddings.
- SWRD `obiwpnhrhjrgvmpzxzog` — still holds all 33 backup/migration/staging tables and original embeddings.
- Before deleting either: take a final full `pg_dump -Fc` to local/encrypted storage.
- Security: before making any of the older project repos public (or if they already are), audit their git history for committed credentials and rotate/retire anything found. Deleting the old Supabase projects invalidates their keys entirely. Never reuse old keys in the new project.
