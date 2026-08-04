#!/usr/bin/env python3
"""
Fix 10 — restore surnames the legacy WoS ingest truncated at 8 characters.

    python3 qc/authors/code/04_fix_truncated.py [--selftest]

Writes ../data/fix_truncated.csv       old -> new, with the evidence
       ../data/fix_truncated.sql       UPDATEs, archiving in-transaction
       ../data/rollback_truncated.sql
       ../data/truncated_queue.csv     rows that cannot be repaired yet

THE DEFECT

200 author rows match SURNAME8.XX — a surname cut at exactly eight characters,
a period, and glued initials: SCHUERMA.JR, HOKENSTA.MC, KINNERSL.SC. This is
not a published name form; it is a field-width limit in the legacy Web of
Science ingest chopping surnames mid-word. All 200 sit on 1971-1975 papers in
the pre-1989 Supplement.

Unlike the initials-only format (THYER, BA), which IS as-published and is
handled separately as enrichment, a truncated surname is corruption, so the
stored value is overwritten -- the same reasoning as the mojibake repair.

THE REPAIR

Each row's own papers carry DOIs, and Crossref holds the era. A row is
repaired only when, on one of ITS OWN papers:

  stem       a Crossref author's family name begins with the 8-char stem and
             is strictly longer
  initials   every initial after the period matches the Crossref given name,
             in order (SCHUERMA.JR needs given names starting J then R)
  unique     exactly one author on that paper matches the stem
  agreement  if several of the row's papers yield a form, all forms agree

The repaired value is Crossref's rendering verbatim ("Schuerman, John R.") --
inventing an ALL-CAPS version to match the ingest's sibling rows would be
fabricating a form nobody published.

Rows whose papers have no DOI, or where Crossref offers no matching surname,
go to the queue, not the patch.

Archived in swrd_archive.renamed_authors_v1_4 (kind 'wos_truncated'),
alongside the 44 string repairs already applied. Each UPDATE matches on the
current value, so the patch is idempotent.

Read-only. Applying is the maintainer's step.
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

OUT_CSV = os.path.join(ROOT, "data", "fix_truncated.csv")
OUT_SQL = os.path.join(ROOT, "data", "fix_truncated.sql")
OUT_RB = os.path.join(ROOT, "data", "rollback_truncated.sql")
OUT_Q = os.path.join(ROOT, "data", "truncated_queue.csv")

PAT = re.compile(r"^[A-Z]{8}\.[A-Z]{1,3}$")


def match_author(name, cr_authors):
    """Repair candidate for one truncated name against one paper's authors.

    -> ('ok', family, given) | ('ambiguous',) | ('no_match',)
    """
    stem, _, initials = name.partition(".")
    stem_l = stem.lower()
    cands = []
    for ca in cr_authors or []:
        fam = (ca.get("family") or "").strip()
        # Compare on letters only: the ingest stripped punctuation before
        # truncating, so KEITHLUC is Keith-Lucas and OFLAHERT is O'Flaherty.
        fam_alpha = re.sub(r"[^a-z]", "", fam.lower())
        if fam_alpha.startswith(stem_l) and len(fam_alpha) > len(stem):
            cands.append(ca)
    if not cands:
        return ("no_match",)
    if len(cands) > 1:
        return ("ambiguous",)
    ca = cands[0]
    giv_tokens = [t for t in re.split(r"[\s.\-]+", ca.get("given") or "") if t]
    ours = list(initials)
    if len(giv_tokens) < len(ours):
        return ("no_match",)
    for o, g in zip(ours, giv_tokens):
        if g[0].upper() != o:
            return ("no_match",)
    return ("ok", ca["family"].strip(), (ca.get("given") or "").strip())


def render(family, given):
    return f"{family}, {given}" if given else family


# ---------------------------------------------------------------- selftest

def selftest():
    paper = [{"family": "Schuerman", "given": "John R."},
             {"family": "Hokenstad", "given": "Merl C."},
             {"family": "Schuermann", "given": "Alice"}]
    hyph = [{"family": "Keith-Lucas", "given": "Alan"},
            {"family": "O'Flaherty", "given": "Kate"}]
    cases = [
        ("SCHUERMA.JR", paper, ("ambiguous",)),           # two stem matches
        ("HOKENSTA.MC", paper, ("ok", "Hokenstad", "Merl C.")),
        ("HOKENSTA.XY", paper, ("no_match",)),            # initials disagree
        ("ROSENFEL.HM", paper, ("no_match",)),            # surname absent
        ("HOKENSTA.M", paper, ("ok", "Hokenstad", "Merl C.")),  # partial initials ok
        ("HOKENSTA.MCX", paper, ("no_match",)),           # more initials than names
        ("KEITHLUC.A", hyph, ("ok", "Keith-Lucas", "Alan")),    # hyphen stripped
        ("OFLAHERT.K", hyph, ("ok", "O'Flaherty", "Kate")),     # apostrophe stripped
    ]
    bad = 0
    for name, aus, want in cases:
        got = match_author(name, aus)
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name:<14} -> {got}")
    print("\nselftest passed" if not bad else f"\n{bad} SELFTEST FAILURES")
    return 1 if bad else 0


# ---------------------------------------------------------------- main

def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    rows = Q.rows(r"""
      select a.id, a.name, p.doi, p.publication_year as year
      from swrd.authors a
      join swrd.paper_authors pa on pa.author_id = a.id
      join swrd.papers p on p.id = pa.paper_id
      where a.name ~ '^[A-Z]{8}\.[A-Z]{1,3}$'
      order by a.id""")
    unlinked = Q.rows(r"""
      select a.id, a.name from swrd.authors a
      where a.name ~ '^[A-Z]{8}\.[A-Z]{1,3}$'
        and not exists (select 1 from swrd.paper_authors pa where pa.author_id = a.id)""")
    per = defaultdict(list)
    for r in rows:
        per[(r["id"], r["name"])].append(r)
    print(f"truncated rows: {len(per)} linked, {len(unlinked)} orphaned")

    dois = sorted({r["doi"].lower() for r in rows if r["doi"] and r["doi"].startswith("10.")})
    Q.CACHE = os.path.join(ROOT, "cache")
    os.makedirs(Q.CACHE, exist_ok=True)
    cache = Q.cache_load("trunc_lookup")
    missing = [d for d in dois if d not in cache]
    if missing:
        got = Q.crossref_by_dois(missing)
        for d in missing:
            cache[d] = got.get(d)
        Q.cache_save("trunc_lookup", cache)
    print(f"papers with a DOI: {len(dois)}, in Crossref: {sum(1 for d in dois if cache.get(d))}")

    fixes, queued = [], []
    for (aid, name), links in sorted(per.items()):
        verdicts = []
        for l in links:
            d = (l["doi"] or "").lower()
            x = cache.get(d) if d.startswith("10.") else None
            if not x:
                continue
            v = match_author(name, x.get("author"))
            if v[0] == "ok":
                verdicts.append((v[1], v[2], l["doi"]))
            elif v[0] == "ambiguous":
                verdicts = [("AMBIGUOUS",)]
                break
        if verdicts and verdicts[0][0] == "AMBIGUOUS":
            queued.append({"author_id": aid, "name": name,
                           "reason": "two_same_stem_authors_on_paper"})
            continue
        if not verdicts:
            reason = ("paper_has_no_doi" if not any(
                (l["doi"] or "").startswith("10.") for l in links)
                else "no_matching_crossref_surname")
            queued.append({"author_id": aid, "name": name, "reason": reason})
            continue
        forms = {render(f, g) for f, g, _ in verdicts}
        if len(forms) > 1:
            queued.append({"author_id": aid, "name": name,
                           "reason": "papers_disagree: " + " | ".join(sorted(forms))})
            continue
        fam, giv, doi = verdicts[0]
        fixes.append({"author_id": aid, "old_name": name,
                      "new_name": render(fam, giv), "evidence_doi": doi,
                      "papers_checked": len(verdicts), "links": len(links)})
    for r in unlinked:
        queued.append({"author_id": r["id"], "name": r["name"],
                       "reason": "orphaned_row_no_links"})

    print(f"\nrepairable : {len(fixes)}")
    print(f"queued     : {len(queued)}")
    reasons = defaultdict(int)
    for q in queued:
        reasons[q["reason"].split(":")[0]] += 1
    for k, v in sorted(reasons.items()):
        print(f"   {k:<34} {v}")

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["author_id", "old_name", "new_name",
                                          "evidence_doi", "papers_checked", "links"])
        w.writeheader()
        w.writerows(fixes)
    with open(OUT_Q, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["author_id", "name", "reason"])
        w.writeheader()
        w.writerows(queued)

    def lit(s):
        return "'" + s.replace("'", "''") + "'"

    upd = "\n".join(
        f"update swrd.authors set name = {lit(f['new_name'])} "
        f"where id = {f['author_id']} and name = {lit(f['old_name'])};"
        for f in fixes)
    arch = ",\n".join(
        f"  ({f['author_id']}, {lit(f['old_name'])}, {lit(f['new_name'])}, "
        f"'wos_truncated')" for f in fixes)
    with open(OUT_SQL, "w") as f:
        f.write(f"""-- Restore {len(fixes)} surnames truncated at 8 characters by the legacy WoS
-- ingest (SCHUERMA.JR -> Schuerman, John R.). Each repair comes from the
-- author's OWN paper's Crossref record: family name extends the stem, every
-- initial agrees, exactly one candidate on the paper, and all of the row's
-- papers agree on the form. No linkage changes.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f fix_truncated.sql

begin;

create schema if not exists swrd_archive;
create table if not exists swrd_archive.renamed_authors_v1_4 (
  author_id int not null, old_name text not null, new_name text not null,
  kind text not null, archived_at timestamptz not null default now());

insert into swrd_archive.renamed_authors_v1_4 (author_id, old_name, new_name, kind)
values
{arch};

do $$
declare live int;
begin
  select count(*) into live from swrd.authors a
    join swrd_archive.renamed_authors_v1_4 r
      on r.author_id = a.id and r.old_name = a.name
   where r.kind = 'wos_truncated';
  if live <> {len(fixes)} then
    raise exception 'preflight: expected {len(fixes)} rows carrying the old name, found %', live;
  end if;
end $$;

{upd}

do $$
declare done int;
begin
  select count(*) into done from swrd.authors a
    join swrd_archive.renamed_authors_v1_4 r
      on r.author_id = a.id and r.new_name = a.name
   where r.kind = 'wos_truncated';
  if done <> {len(fixes)} then
    raise exception 'expected {len(fixes)} rows renamed, found %', done;
  end if;
  raise notice 'restored {len(fixes)} truncated surnames';
end $$;

commit;
""")
    rb = "\n".join(
        f"update swrd.authors set name = {lit(f['old_name'])} "
        f"where id = {f['author_id']} and name = {lit(f['new_name'])};"
        for f in fixes)
    with open(OUT_RB, "w") as f:
        f.write(f"""-- Reverse of fix_truncated.sql, written before applying.
--   psql "$TGT" -v ON_ERROR_STOP=1 -f rollback_truncated.sql
begin;
{rb}
delete from swrd_archive.renamed_authors_v1_4
 where kind = 'wos_truncated'
   and author_id in ({",".join(str(f['author_id']) for f in fixes)});
commit;
""")
    print(f"\n-> {OUT_CSV}\n-> {OUT_SQL}\n-> {OUT_RB}\n-> {OUT_Q}")


if __name__ == "__main__":
    main()
