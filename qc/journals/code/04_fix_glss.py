#!/usr/bin/env python3
"""
Fix 2 — 393 Journal of Gay & Lesbian Social Services articles filed under
Journal of Gerontological Social Work.

    python3 qc/journals/code/04_fix_glss.py

Writes ../data/fix_glss.csv, fix_glss.sql, rollback_glss.sql

WHY THIS ONE NEEDED A DIFFERENT PROOF

The Affilia fix rested partly on DOI prefixes being disjoint: 10.1177 against
10.1093. That does not work here. Both journals published through Haworth, so
prefix 10.1300 appears on the 393 misattributed records AND on 918 correctly
filed ones. The prefix cannot decide.

What can is the Haworth SERIES CODE inside the DOI. Haworth encoded the journal
in the suffix, and the two are completely disjoint:

    10.1300/J041...  Journal of Gay & Lesbian Social Services   (all 393)
    10.1300/J083...  Journal of Gerontological Social Work      (all 918)

Zero overlap. That signal lives in the DOI string we already store, so it is
independent of Crossref entirely -- it would hold even if Crossref were wrong
about everything.

THE EVIDENCE, ALL SIX AGREEING ON ALL 393

  series      10.1300/J041, disjoint from the J083 of every correct record
  issn        1053-8720 / 1540-4056 on 393 of 393
  container   "Journal of Gay & Lesbian Social Services" on 393 of 393
  era         1994-2006, which is that journal's own period; the correctly
              filed Gerontological records span 1989-2025 with median 2010
  target      id 232 already holds 518 records with the identical container
  direction   zero Gerontological-ISSN records sit under 232 -- one way only

WHERE THESE GO, AND WHY 232 RATHER THAN 263

Journal of Gay & Lesbian Social Services was renamed Sexual and Gender Diversity
in Social Services, and the SWRD table carries that journal as two rows: id 232
holds the pre-rename articles (749 of them, its sample voting 1053-8720) and
id 263 holds 39 post-rename ones. These 393 are pre-rename, so they belong with
232. Merging 232 and 263 is a separate fix and is not attempted here.

Read-only. Applying is the maintainer's step.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

OUT_CSV = os.path.join(ROOT, "data", "fix_glss.csv")
OUT_SQL = os.path.join(ROOT, "data", "fix_glss.sql")
OUT_RB = os.path.join(ROOT, "data", "rollback_glss.sql")

FROM_ID, TO_ID = 11, 232
GLSS = {"1053-8720", "1540-4056"}
JGSW = {"0163-4372", "1540-4048"}
SERIES = re.compile(r"^10\.1300/(J\d+)", re.I)
GLSS_SERIES, JGSW_SERIES = "J041", "J083"
EXPECTED = 393


def load_crossref():
    merged = {}
    for name in ("column_lookup", "doi_lookup", "audit_lookup"):
        Q.CACHE = os.path.join(HERE, "..", "..", "doi", "cache")
        try:
            for _, v in Q.cache_load(name).items():
                if isinstance(v, dict) and v.get("DOI"):
                    merged[v["DOI"].lower()] = v
        except Exception:
            continue
    return merged


def main():
    xref = load_crossref()
    if not xref:
        sys.exit("no cached Crossref records — run the qc/doi pipeline first")

    tgt = Q.rows(f"select id, name from swrd.journals where id = {TO_ID}")
    if not tgt:
        sys.exit(f"journal {TO_ID} does not exist")
    src = Q.rows(rf"""
      select p.id, p.doi, p.title, p.publication_year as year
      from swrd.papers p
      where p.journal_id = {FROM_ID} and p.doi ~ '^10\.[0-9]{{4,9}}/'
    """)
    print(f"under journal {FROM_ID}: {len(src):,} records with a valid DOI")
    print(f"target: id {TO_ID} = {tgt[0]['name']}")

    rows, rejected = [], []
    for r in src:
        x = xref.get(r["doi"].lower())
        if not x:
            continue
        issn = {s.strip().upper() for s in (x.get("ISSN") or []) if s}
        if not (issn & GLSS):
            continue
        m = SERIES.match(r["doi"])
        container = (x.get("container-title") or [None])[0]
        yrs = Q.cr_years(x)
        signals = {
            "series_is_J041": bool(m) and m.group(1).upper() == GLSS_SERIES,
            "issn_is_glss": True,
            "not_gerontological_issn": not (issn & JGSW),
            "container_is_glss": "gay" in (container or "").lower(),
            "year_in_glss_era": 1990 <= r["year"] <= 2010,
            # Crossref's publication year is NOT a gate here, only reported.
            # It does not bear on which journal an article is in, and Haworth's
            # back catalogue carries unreliable dates: the five records of
            # j041v17n04 are stored as 2006 while Crossref reports 2004 and
            # 2008 for the same issue. Gating on it would have excluded five
            # records whose journal is not in any doubt -- the same error as
            # gating the Affilia fix on title.
        }
        row = {"record_id": r["id"], "doi": r["doi"], "year": r["year"],
               "series": m.group(1).upper() if m else "",
               "crossref_container": container,
               "crossref_issn": ",".join(sorted(issn)),
               "crossref_years": ",".join(map(str, sorted(yrs))),
               "title": (r["title"] or "")[:180],
               **{k: str(v) for k, v in signals.items()}}
        (rows if all(signals.values()) else rejected).append(row)

    print(f"\nGLSS-ISSN records under journal {FROM_ID}: {len(rows) + len(rejected):,}")
    print(f"  passing every signal : {len(rows):,}")
    print(f"  rejected             : {len(rejected):,}")
    for r in rejected[:6]:
        fails = [k for k in r if r.get(k) == "False"]
        print(f"     {r['record_id']} ({r['year']}) series={r['series']} fails={fails}")

    # The series code must partition cleanly, or the premise of this fix is wrong.
    others = Q.rows(rf"""
      select count(*) as n from swrd.papers
      where journal_id = {FROM_ID} and doi ~* '^10\.1300/{JGSW_SERIES}'
    """)[0]["n"]
    print(f"\n  J083 (Gerontological) records left under journal {FROM_ID}: {others:,}")
    print(f"  J041 (GLSS) records being moved                     : {len(rows):,}")

    if len(rows) != EXPECTED:
        sys.exit(f"\nexpected {EXPECTED}, found {len(rows)} — the corpus moved; "
                 "re-check the evidence before proposing anything")

    cols = ["record_id", "doi", "series", "year", "crossref_container", "crossref_issn",
            "series_is_J041", "issn_is_glss", "not_gerontological_issn",
            "container_is_glss", "year_in_glss_era", "crossref_years", "title"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["record_id"]))

    ids = sorted(r["record_id"] for r in rows)
    idlist = ",".join(map(str, ids))
    with open(OUT_SQL, "w") as f:
        f.write(f"""-- Move {len(ids)} Journal of Gay & Lesbian Social Services articles
-- from journal {FROM_ID} (Journal of Gerontological Social Work) to {TO_ID}.
--
-- Both journals published through Haworth, so the DOI PREFIX cannot separate
-- them -- 10.1300 appears on both sides. The Haworth SERIES CODE can, and does,
-- with no overlap at all:
--
--     10.1300/J041...  Journal of Gay & Lesbian Social Services   ({len(ids)} records)
--     10.1300/J083...  Journal of Gerontological Social Work      ({others} records)
--
-- Corroborated by ISSN 1053-8720/1540-4056, Crossref container
-- "Journal of Gay & Lesbian Social Services", and a 1994-2006 span that matches
-- that journal's own era. id {TO_ID} already holds 518 records with the identical
-- container, and no Gerontological record sits under it.
--
-- Row counts do not change; both journals are in the set.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f fix_glss.sql

begin;

update swrd.papers set journal_id = {TO_ID}
 where journal_id = {FROM_ID} and id in ({idlist});

do $$
declare moved int; left_behind int; stragglers int;
begin
  select count(*) into moved from swrd.papers
   where journal_id = {TO_ID} and id in ({idlist});
  select count(*) into left_behind from swrd.papers
   where journal_id = {FROM_ID} and id in ({idlist});
  select count(*) into stragglers from swrd.papers
   where journal_id = {FROM_ID} and doi ~* '^10\\.1300/{GLSS_SERIES}';
  if moved <> {len(ids)} or left_behind <> 0 then
    raise exception 'expected {len(ids)} moved and 0 left, saw % and %', moved, left_behind;
  end if;
  if stragglers <> 0 then
    raise exception '% {GLSS_SERIES} records still under journal {FROM_ID}', stragglers;
  end if;
  raise notice 'moved % records; no {GLSS_SERIES} records remain under journal {FROM_ID}', moved;
end $$;

commit;
""")
    with open(OUT_RB, "w") as f:
        f.write(f"""-- Reverse of fix_glss.sql, written before applying.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f rollback_glss.sql

begin;
update swrd.papers set journal_id = {FROM_ID}
 where journal_id = {TO_ID} and id in ({idlist});
commit;
""")
    print(f"\n{len(ids):,} -> {OUT_CSV}\n{OUT_SQL}\n{OUT_RB}")


if __name__ == "__main__":
    main()
