#!/usr/bin/env python3
"""Generate the semantic catalog (data dictionary) for each database schema,
directly from the live database, into skills/<db>/references/catalog.md.

Usage: python 07_generate_catalog.py sswr|swrd
Regenerate whenever the data changes — everything numeric is measured live.
"""
import os, sys, datetime
import psycopg2

SCHEMA = sys.argv[1]
assert SCHEMA in ("sswr", "swrd")
repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = {l.split("=", 1)[0]: l.split("=", 1)[1].strip()
       for l in open(os.path.join(repo, ".env")) if "=" in l and not l.startswith("#")}
conn = psycopg2.connect(cfg["TGT"]); conn.autocommit = True
cur = conn.cursor(); cur.execute("set statement_timeout = 0")

# Hand-written semantic descriptions (survive regeneration). schema.table.column → meaning.
DESC = {
  # ---------------- SWRD ----------------
  "swrd.papers": "One row per journal article. The primary table.",
  "swrd.papers.id": "Internal article identifier (stable within this database).",
  "swrd.papers.doi": "Digital Object Identifier — permanent link to the article (https://doi.org/<doi>).",
  "swrd.papers.title": "Article title as published.",
  "swrd.papers.abstract": "Full abstract where available; NULL when never digitized.",
  "swrd.papers.publication_year": "Year of publication. 1989+ = the SWRD proper; pre-1989 = Supplement (incomplete).",
  "swrd.papers.journal_id": "Foreign key to journals.id.",
  "swrd.papers.document_type": "Source-reported document type (article, review, etc.).",
  "swrd.papers.data_source": "Which harvest supplied the record (WoS, Scopus, RDS = original SWRD 1.0, etc.). Messy vocabulary — do not treat as clean categories.",
  "swrd.papers.open_access": "Whether the article is open access (source-reported).",
  "swrd.papers.is_scientific": "SLM classification: original research contribution vs editorial/book review/letter. Only set where an abstract exists.",
  "swrd.papers.is_empirical": "SLM classification: reports collection/analysis of original data. Subset of is_scientific.",
  "swrd.papers.research_method": "SLM classification of empirical articles. Exact values below — note capitalization.",
  "swrd.journals": "The 91 disciplinary social work journals (the population list).",
  "swrd.authors": "Author name strings AS PUBLISHED. NOT disambiguated — one person may have several rows.",
  "swrd.authors.orcid": "ORCID iD where the source supplied one.",
  "swrd.paper_authors": "Authorship: links papers to authors with byline order.",
  "swrd.paper_authors.position": "Byline position; 1 = first author.",
  "swrd.paper_authors.is_corresponding": "Corresponding-author flag where known.",
  "swrd.organizations": "Institutional affiliations as reported by sources (not normalized).",
  "swrd.author_affiliations": "Author–organization pairs per paper.",
  "swrd.title_abstract_embeddings": "One 768-dim meaning vector per paper (embeddinggemma:300m over 'title: {t} | text: {abstract}').",
  "swrd.embedding_models": "Registry of embedding models used, with dimensions.",
  "swrd.embedding_runs": "Provenance log of embedding runs.",
  # ---------------- SSWR ----------------
  "sswr.papers": "One row per SSWR conference presentation. The primary table.",
  "sswr.papers.id": "Presentation identifier: YYYY-TYPE-NNNN (e.g. 2019-O-0142).",
  "sswr.papers.year": "Conference year (2005–2026, complete).",
  "sswr.papers.title": "Presentation title.",
  "sswr.papers.abstract": "Full abstract (present for 100% of records).",
  "sswr.papers.format": "Presentation format code from the program.",
  "sswr.papers.methodology": "Research-method label. Exact values below (lowercase).",
  "sswr.papers.author_count": "Number of authorship rows (kept consistent with paper_authors).",
  "sswr.papers.fts": "Precomputed full-text search vector (used by keyword/BM25 search).",
  "sswr.authors": "CANONICAL author entities — disambiguated across years. name format: 'First Last', sometimes with credentials.",
  "sswr.authors.variants": "JSON list of name variants resolved to this identity.",
  "sswr.authors.institutions": "JSON list of institutions seen for this author.",
  "sswr.authors.total_papers": "Presentations linked to this canonical identity.",
  "sswr.paper_authors": "Authorship instances: name as printed + link to canonical author (author_id).",
  "sswr.paper_authors.author_order": "Byline position; 1 = first author.",
  "sswr.paper_authors.institution_normalized": "Institution mapped to a canonical name.",
  "sswr.institution_mappings": "Raw → canonical institution name mappings.",
  "sswr.paper_embeddings": "One 768-dim meaning vector per presentation (embeddinggemma:300m).",
  "sswr.paper_html_mappings": "Provenance: link from each record to its source conference-program HTML file.",
  "sswr.author_canonical_mapping": "Audit trail of author-identity merges.",
  "sswr.author_linkage_audit": "Audit log of author-linkage decisions.",
  "sswr.country_mappings": "Raw → normalized country names.",
  "sswr.search_logs": "Telemetry from the original search app (not research data).",
  "sswr.page_views": "Telemetry from the original web app (not research data).",
}
# Low-cardinality columns whose full value distribution belongs in the catalog.
VOCAB = {
  "swrd": [("papers", "research_method"), ("papers", "document_type"), ("papers", "data_source")],
  "sswr": [("papers", "methodology"), ("papers", "format")],
}
SKIP_TABLES = {"sswr": ["fence_sync"], "swrd": []}

def q(sql, args=()):
    cur.execute(sql, args); return cur.fetchall()

out = []
out.append(f"# {SCHEMA.upper()} — Semantic Catalog (Data Dictionary)")
out.append(f"\n*Generated from the live database on {datetime.date.today().isoformat()} by `migration/07_generate_catalog.py`. All counts and coverage figures are measured, not estimated.*\n")

tables = [t for (t,) in q("""select tablename from pg_tables where schemaname=%s order by tablename""", (SCHEMA,))
          if t not in SKIP_TABLES[SCHEMA]]

out.append("## Tables\n")
for t in tables:
    (n,) = q(f'select count(*) from {SCHEMA}."{t}"')[0]
    desc = DESC.get(f"{SCHEMA}.{t}", "")
    out.append(f"### `{t}` — {n:,} rows\n")
    if desc: out.append(desc + "\n")
    out.append("| Column | Type | Filled | Meaning |")
    out.append("|---|---|---|---|")
    cols = q("""select column_name, data_type, udt_name from information_schema.columns
                where table_schema=%s and table_name=%s order by ordinal_position""", (SCHEMA, t))
    for cname, dtype, udt in cols:
        typ = "vector(768)" if udt == "vector" else dtype
        if n > 0:
            (nn,) = q(f'select count("{cname}") from {SCHEMA}."{t}"')[0]
            filled = f"{100.0*nn/n:.1f}%"
        else:
            filled = "—"
        meaning = DESC.get(f"{SCHEMA}.{t}.{cname}", "")
        out.append(f"| `{cname}` | {typ} | {filled} | {meaning} |")
    out.append("")

out.append("## Value vocabularies (exact values — match capitalization)\n")
for t, c in VOCAB[SCHEMA]:
    rows = q(f'select "{c}", count(*) from {SCHEMA}."{t}" where "{c}" is not null group by 1 order by 2 desc')
    out.append(f"### `{t}.{c}`\n")
    if len(rows) > 25:
        out.append(f"*{len(rows)} distinct values — top 25 shown; treat this field as messy free text, not clean categories.*\n")
        rows = rows[:25]
    out.append("| Value | Count |")
    out.append("|---|---|")
    for v, n in rows:
        out.append(f"| `{v}` | {n:,} |")
    out.append("")

out.append("## Views (precomputed answers)\n")
out.append("| View | What it answers |")
out.append("|---|---|")
for (v,) in q("select viewname from pg_views where schemaname=%s order by viewname", (SCHEMA,)):
    cur.execute("select obj_description(%s::regclass)", (f"{SCHEMA}.{v}",))
    comment = cur.fetchone()[0] or ""
    out.append(f"| `{v}` | {comment} |")
out.append("")

out.append("## Functions (callable via SQL or the REST rpc endpoint)\n")
out.append("| Function | Signature |")
out.append("|---|---|")
for name, args in q("""select p.proname, pg_get_function_arguments(p.oid)
                        from pg_proc p join pg_namespace ns on ns.oid=p.pronamespace
                        where ns.nspname=%s and p.prokind='f' order by p.proname""", (SCHEMA,)):
    out.append(f"| `{name}` | ({args}) |")
out.append("")

out.append("## Join map\n")
fks = q("""select tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name
           from information_schema.table_constraints tc
           join information_schema.key_column_usage kcu on tc.constraint_name = kcu.constraint_name and tc.table_schema = kcu.table_schema
           join information_schema.constraint_column_usage ccu on tc.constraint_name = ccu.constraint_name and tc.table_schema = ccu.table_schema
           where tc.constraint_type='FOREIGN KEY' and tc.table_schema=%s order by 1,2""", (SCHEMA,))
if fks:
    for a, ac, b, bc in fks:
        out.append(f"- `{a}.{ac}` → `{b}.{bc}`")
else:
    out.append("*No declared foreign keys — join on the id columns described above.*")
out.append("")

dest = os.path.join(repo, "skills", f"{SCHEMA}-database", "references", "catalog.md")
os.makedirs(os.path.dirname(dest), exist_ok=True)
open(dest, "w").write("\n".join(out) + "\n")
print(f"wrote {dest} ({len(out)} lines)")
