#!/usr/bin/env python3
"""
Fix 1 — 801 Affilia articles filed under Social Work.

    python3 qc/journals/code/03_fix_affilia.py

Writes ../data/fix_affilia.csv       the records, with every signal
       ../data/fix_affilia.sql       the UPDATE statements
       ../data/rollback_affilia.sql  the reverse

One cluster, one cause, and the evidence is unusually complete. This is
deliberately NOT the 3,513-record sweep the identifier analysis suggests is
possible: the other clusters have weaker or mixed evidence and each deserves
its own look.

WHY THIS ONE IS SAFE TO APPLY

  identifier   Every one of the 801 carries ISSN 0886-1099 / 1552-3020. Affilia's
               own correctly-filed articles vote 120/120 for exactly that pair,
               so the identifier is not inferred, it is corroborated in-corpus.
  container    Crossref names the container "Affilia" on 801 of 801.
  prefix       All 801 are 10.1177 (SAGE). Every correctly-filed Social Work
               record is 10.1093 (Oxford). The two sets are disjoint, so the
               split is visible without consulting Crossref at all.
  year         801 of 801 agree within a year.
  direction    1,440 Affilia-ISSN records are already filed correctly under
               id 17, and ZERO Social Work records sit under Affilia. The error
               runs one way only, which is what a single bad ingest looks like.
  target       Affilia is id 17, already in the 91-journal set, so nothing
               leaves the corpus and no journal row is created.

TITLE IS NOT USED AS A GATE, on purpose. 11 of the 801 have a title that differs
from Crossref's: three are corrigenda where Crossref stores "Corrigendum" and we
store the descriptive title, three are editorials where Crossref stores
"Editorial", and the rest are multi-part titles truncated on one side. None of
that bears on which journal the article is in.

The distinction matters. In the v1.1 DOI repair we were *choosing* a DOI, so the
title had to confirm the choice. Here the DOI is already on the record and we
are reading which journal it belongs to. The title is not evidence for that
question; the ISSN is.

Read-only. Applying is the maintainer's step.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

OUT_CSV = os.path.join(ROOT, "data", "fix_affilia.csv")
OUT_SQL = os.path.join(ROOT, "data", "fix_affilia.sql")
OUT_RB = os.path.join(ROOT, "data", "rollback_affilia.sql")

FROM_ID, TO_ID = 1, 17
AFFILIA = {"0886-1099", "1552-3020"}
SOCIAL_WORK = {"0037-8046", "1545-6846"}
EXPECTED = 801


def load_crossref():
    merged = {}
    for base, name in (("qc/doi/cache", "column_lookup"),
                       ("qc/doi/cache", "doi_lookup"),
                       ("qc/doi/cache", "audit_lookup")):
        Q.CACHE = os.path.join(HERE, "..", "..", "..", base) \
            if not os.path.isdir(base) else base
        try:
            for k, v in Q.cache_load(name).items():
                if isinstance(v, dict) and v.get("DOI"):
                    merged[v["DOI"].lower()] = v
        except Exception:
            continue
    return merged


def main():
    xref = load_crossref()
    if not xref:
        sys.exit("no cached Crossref records found — run the qc/doi pipeline first")

    src = Q.rows(rf"""
      select p.id, p.doi, p.title, p.publication_year as year
      from swrd.papers p
      where p.journal_id = {FROM_ID} and p.doi ~ '^10\.[0-9]{{4,9}}/'
    """)
    tgt = Q.rows(f"select id, name from swrd.journals where id = {TO_ID}")
    if not tgt:
        sys.exit(f"journal id {TO_ID} does not exist")
    print(f"under journal {FROM_ID}: {len(src):,} records with a valid DOI")
    print(f"target: id {TO_ID} = {tgt[0]['name']}")

    rows, rejected = [], []
    for r in src:
        x = xref.get(r["doi"].lower())
        if not x:
            continue
        issn = {s.strip().upper() for s in (x.get("ISSN") or []) if s}
        if not (issn & AFFILIA):
            continue
        container = (x.get("container-title") or [None])[0]
        signals = {
            "issn_is_affilia": bool(issn & AFFILIA),
            "container_is_affilia": Q.norm_journal(container) == "affilia",
            "prefix_is_sage": r["doi"].split("/")[0] == "10.1177",
            "not_social_work_issn": not (issn & SOCIAL_WORK),
            "year_agrees": (lambda y: (not y) or any(abs(r["year"] - c) <= 1 for c in y))(
                Q.cr_years(x)),
        }
        row = {"record_id": r["id"], "doi": r["doi"], "year": r["year"],
               "title": (r["title"] or "")[:180],
               "crossref_container": container,
               "crossref_issn": ",".join(sorted(issn)),
               "title_similarity": round(Q.title_sim(r["title"] or "", Q.cr_title(x)), 3),
               **{k: str(v) for k, v in signals.items()}}
        (rows if all(signals.values()) else rejected).append(row)

    print(f"\nAffilia-ISSN records under journal {FROM_ID}: {len(rows) + len(rejected):,}")
    print(f"  passing every signal : {len(rows):,}")
    print(f"  rejected             : {len(rejected):,}")
    for r in rejected[:5]:
        print(f"     {r['record_id']} {r['crossref_container']}")
    if len(rows) != EXPECTED:
        sys.exit(f"\nexpected {EXPECTED} records, found {len(rows)} — the corpus moved; "
                 "re-check the evidence before proposing anything")

    cols = ["record_id", "doi", "year", "crossref_container", "crossref_issn",
            "title_similarity", "issn_is_affilia", "container_is_affilia",
            "prefix_is_sage", "not_social_work_issn", "year_agrees", "title"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["record_id"]))

    ids = sorted(r["record_id"] for r in rows)
    idlist = ",".join(map(str, ids))
    head = f"""-- Reassign {len(ids)} Affilia articles from journal {FROM_ID} to journal {TO_ID}.
--
-- Every one carries ISSN 0886-1099/1552-3020, DOI prefix 10.1177, and Crossref
-- container "Affilia". Social Work's own records are 10.1093 with ISSN
-- 0037-8046 -- the two sets are disjoint. Affilia (id {TO_ID}) already holds 1,440
-- correctly-filed records whose own sample votes 120/120 for this ISSN, and no
-- Social Work record sits under Affilia, so the error runs one way only.
--
-- Row counts do not change: both journals are in the 91-journal set, so the
-- export's inner join is unaffected and swrd_articles stays 62,602.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f fix_affilia.sql

begin;

update swrd.papers set journal_id = {TO_ID}
 where journal_id = {FROM_ID} and id in ({idlist});

do $$
declare moved int; left_behind int;
begin
  select count(*) into moved from swrd.papers
   where journal_id = {TO_ID} and id in ({idlist});
  select count(*) into left_behind from swrd.papers
   where journal_id = {FROM_ID} and id in ({idlist});
  if moved <> {len(ids)} or left_behind <> 0 then
    raise exception 'expected {len(ids)} moved and 0 left, saw % and %', moved, left_behind;
  end if;
  raise notice 'moved % records from journal {FROM_ID} to {TO_ID}', moved;
end $$;

commit;
"""
    with open(OUT_SQL, "w") as f:
        f.write(head)
    with open(OUT_RB, "w") as f:
        f.write(f"""-- Reverse of fix_affilia.sql. Written before applying, because a
-- {len(ids)}-row reassignment should never be one-way.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f rollback_affilia.sql

begin;
update swrd.papers set journal_id = {FROM_ID}
 where journal_id = {TO_ID} and id in ({idlist});
commit;
""")
    print(f"\n{len(ids):,} -> {OUT_CSV}\n{OUT_SQL}\n{OUT_RB}")


if __name__ == "__main__":
    main()
