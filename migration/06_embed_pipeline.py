#!/usr/bin/env python3
"""Embed papers with embeddinggemma:300m (Ollama, 768-dim) into the consolidated DB.

Usage: python 06_embed_pipeline.py sswr|swrd
Reads TGT connection string from the repo .env. Resumable: skips papers that
already have an embedding. Documents are formatted per EmbeddingGemma's
document prompt convention: "title: {title} | text: {text}".
"""
import os, sys, time, json
import requests
import psycopg2
from psycopg2.extras import execute_values

SCHEMA = sys.argv[1]
assert SCHEMA in ("sswr", "swrd")
BATCH = 32
OLLAMA = "http://localhost:11434/api/embed"
MODEL = "embeddinggemma:300m"

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = {l.split("=", 1)[0]: l.split("=", 1)[1].strip()
       for l in open(os.path.join(repo, ".env")) if "=" in l and not l.startswith("#")}

conn = psycopg2.connect(cfg["TGT"])
conn.autocommit = False
cur = conn.cursor()
cur.execute("set statement_timeout = 0")

if SCHEMA == "sswr":
    FETCH = """select p.id::text, p.title, p.abstract from sswr.papers p
               where not exists (select 1 from sswr.paper_embeddings e where e.paper_id = p.id)
               order by p.id"""
    INSERT = """insert into sswr.paper_embeddings (paper_id, embedding, model) values %s
                on conflict (paper_id) do nothing"""
else:
    FETCH = """select p.id::text, p.title, p.abstract from swrd.papers p
               where not exists (select 1 from swrd.title_abstract_embeddings e where e.paper_id = p.id)
               order by p.id"""
    INSERT = """insert into swrd.title_abstract_embeddings (paper_id, embedding, model) values %s
                on conflict (paper_id) do nothing"""

cur.execute(FETCH)
rows = cur.fetchall()
total = len(rows)
print(f"[{SCHEMA}] {total} papers to embed", flush=True)

session = requests.Session()
done, t0 = 0, time.time()
for i in range(0, total, BATCH):
    chunk = rows[i:i + BATCH]
    docs = []
    for pid, title, abstract in chunk:
        title = (title or "").strip()
        text = (abstract or "").strip()
        docs.append(f"title: {title} | text: {text}" if text else f"title: {title} | text: none")
    for attempt in range(5):
        try:
            r = session.post(OLLAMA, json={"model": MODEL, "input": docs}, timeout=300)
            r.raise_for_status()
            embs = r.json()["embeddings"]
            break
        except Exception as e:
            print(f"[{SCHEMA}] ollama retry {attempt+1}: {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    else:
        raise SystemExit(f"[{SCHEMA}] FAILED: ollama unreachable at row {i}")
    assert len(embs) == len(chunk) and len(embs[0]) == 768
    values = [(pid if SCHEMA == "sswr" else int(pid), json.dumps(emb), MODEL)
              for (pid, _, _), emb in zip(chunk, embs)]
    for attempt in range(5):
        try:
            execute_values(cur, INSERT, values, template="(%s, %s::vector, %s)")
            conn.commit()
            break
        except Exception as e:
            conn.rollback()
            print(f"[{SCHEMA}] db retry {attempt+1}: {e}", flush=True)
            time.sleep(5 * (attempt + 1))
            try:
                conn.close()
            except Exception:
                pass
            conn = psycopg2.connect(cfg["TGT"])
            cur = conn.cursor()
            cur.execute("set statement_timeout = 0")
    else:
        raise SystemExit(f"[{SCHEMA}] FAILED: db unreachable at row {i}")
    done += len(chunk)
    if done % 1024 < BATCH:
        rate = done / (time.time() - t0)
        eta = (total - done) / rate / 60 if rate else 0
        print(f"[{SCHEMA}] {done}/{total} ({100*done/total:.1f}%) {rate:.0f}/s eta {eta:.0f}m", flush=True)

print(f"[{SCHEMA}] COMPLETE: {done} embedded in {(time.time()-t0)/60:.1f}m", flush=True)
