#!/usr/bin/env python3
"""
Fix 9 — repair 44 corrupted author-name strings.

    python3 qc/authors/code/03_fix_strings.py

Writes ../data/fix_strings.csv       old -> new for every row
       ../data/fix_strings.sql       the UPDATEs, archiving in-transaction
       ../data/rollback_strings.sql

The smallest fix in the series, held to the same bar as the largest. Only
strings whose repair is DETERMINISTIC are touched:

  mojibake (27)      'Vesna LeskoÅ¡ek' -> 'Vesna Leskošek'. UTF-8 text was read
                     as Latin-1 and re-encoded; the reverse round trip either
                     reproduces the original text or fails, so the repair
                     cannot guess.
  footnote digits(4) 'Eybalin1, Dominique' -> 'Eybalin, Dominique'. A trailing
                     superscript marker on the surname.
  trailing comma (6) 'Chan, Wing-tai,' -> 'Chan, Wing-tai'
  doubled spaces (7) 'Darlene  Chalmers' -> 'Darlene Chalmers'

DELIBERATELY NOT TOUCHED, each verified by hand:

  'Coldon, Lawrence, 3rd'   generational suffix, a real name form
  'Zuraini J.@.O.'          Crossref gives 'Jamil @ Osman Zuraini' -- the @ is
                            the Malaysian alias convention, part of the name
  '7' (x2)                  not a name at all; the LINK is spurious. That is a
                            paper_authors deletion (issue #6 class), not a
                            string repair, and it is queued there.
  '570-662-43 (fax nsidell@mansfield.edu'
                            a contact block ingested as an author on a no-DOI
                            record; the true author list needs bibliographic
                            search, not a guess. Queued.
  '&;#xd;rvig, Kjersti'     probably Ørvig, but that repair would come from
                            web knowledge, not from the string. Orphaned row
                            (0 links). Queued.

Renaming an author row changes no linkage: paper_authors joins on author_id,
so counts, positions, and credits are all untouched. The only observable
change is the spelling of 44 names, 42 of them backed by links.

Prior values are archived in swrd_archive.renamed_authors_v1_4 in the SAME
transaction; the rollback restores from its own literals and each UPDATE
matches on the CURRENT value, so a row that changed since generation is
skipped, not clobbered.

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

OUT_CSV = os.path.join(ROOT, "data", "fix_strings.csv")
OUT_SQL = os.path.join(ROOT, "data", "fix_strings.sql")
OUT_RB = os.path.join(ROOT, "data", "rollback_strings.sql")

MOJI_SIG = re.compile(r"Ã[a-z©¡³¤¶¼«±«]|â€|Å[¡¾¸†™]|Ã˜|Ã…")
EXPECTED = 44


def repair(name):
    """-> (new_name, kind) or None. Deterministic transforms only."""
    n = name or ""
    if MOJI_SIG.search(n):
        try:
            fixed = n.encode("latin-1").decode("utf-8")
            if fixed != n:
                return fixed, "mojibake"
        except Exception:
            pass
    # a digit glued to a name token is a footnote marker; a free-standing
    # digit ('7') or a generational suffix ('3rd') is not ours to touch
    if re.search(r"[A-Za-z]\d", n) and not re.search(r"\d(st|nd|rd|th)\b", n):
        return re.sub(r"(?<=[A-Za-z])\d+", "", n), "footnote_digit"
    if re.search(r",\s*$", n):
        return re.sub(r"[\s,]+$", "", n), "trailing_comma"
    if re.search(r"\s{2,}", n):
        return re.sub(r"\s{2,}", " ", n).strip(), "doubled_space"
    return None


def selftest():
    cases = [
        ("Vesna LeskoÅ¡ek", "Vesna Leskošek", "mojibake"),
        ("Filip CoussÃ©e", "Filip Coussée", "mojibake"),
        ("Eybalin1, Dominique", "Eybalin, Dominique", "footnote_digit"),
        ("Chan, Wing-tai,", "Chan, Wing-tai", "trailing_comma"),
        ("Darlene  Chalmers", "Darlene Chalmers", "doubled_space"),
        ("Coldon, Lawrence, 3rd", None, None),      # suffix, untouched
        ("Zuraini J.@.O.", None, None),             # Malaysian alias, untouched
        ("7", None, None),                          # not a string repair
        ("Bergmark Å.", None, None),                # real Swedish initial
        ("Smith, John", None, None),                # nothing to do
    ]
    bad = 0
    for name, want, wkind in cases:
        got = repair(name)
        ok = (got is None and want is None) or (got and got[0] == want and got[1] == wkind)
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name!r:<28} -> {got}")
    print("\nselftest passed" if not bad else f"\n{bad} SELFTEST FAILURES")
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    rows = Q.rows("""
      select a.id, a.name, count(pa.paper_id) as links
      from swrd.authors a
      left join swrd.paper_authors pa on pa.author_id = a.id
      group by a.id, a.name""")
    fixes = []
    for r in rows:
        rep = repair(r["name"])
        if rep:
            fixes.append({"author_id": r["id"], "old_name": r["name"],
                          "new_name": rep[0], "kind": rep[1], "links": r["links"]})
    fixes.sort(key=lambda f: (f["kind"], f["author_id"]))
    kinds = {}
    for f in fixes:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    print(f"repairs: {len(fixes)}   {kinds}")
    if len(fixes) != EXPECTED:
        sys.exit(f"expected {EXPECTED}, found {len(fixes)} — the corpus moved; "
                 "re-check before proposing")

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["author_id", "old_name", "new_name",
                                          "kind", "links"])
        w.writeheader()
        w.writerows(fixes)

    def lit(s):
        return "'" + s.replace("'", "''") + "'"

    upd = "\n".join(
        f"update swrd.authors set name = {lit(f['new_name'])} "
        f"where id = {f['author_id']} and name = {lit(f['old_name'])};"
        for f in fixes)
    arch = ",\n".join(
        f"  ({f['author_id']}, {lit(f['old_name'])}, {lit(f['new_name'])}, "
        f"'{f['kind']}')" for f in fixes)
    with open(OUT_SQL, "w") as f:
        f.write(f"""-- Repair {len(fixes)} corrupted author-name strings.
-- Mojibake decode, footnote digits, trailing commas, doubled spaces.
-- No linkage changes: paper_authors joins on author_id.
-- Each UPDATE matches on the CURRENT name, so the patch is idempotent and a
-- row that moved since generation is skipped rather than clobbered.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f fix_strings.sql

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
      on r.author_id = a.id and r.old_name = a.name;
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
      on r.author_id = a.id and r.new_name = a.name;
  if done <> {len(fixes)} then
    raise exception 'expected {len(fixes)} rows renamed, found %', done;
  end if;
  raise notice 'repaired {len(fixes)} author-name strings';
end $$;

commit;
""")
    rb = "\n".join(
        f"update swrd.authors set name = {lit(f['old_name'])} "
        f"where id = {f['author_id']} and name = {lit(f['new_name'])};"
        for f in fixes)
    with open(OUT_RB, "w") as f:
        f.write(f"""-- Reverse of fix_strings.sql, written before applying.
--   psql "$TGT" -v ON_ERROR_STOP=1 -f rollback_strings.sql
begin;
{rb}
delete from swrd_archive.renamed_authors_v1_4
 where author_id in ({",".join(str(f['author_id']) for f in fixes)});
commit;
""")
    print(f"-> {OUT_CSV}\n-> {OUT_SQL}\n-> {OUT_RB}")


if __name__ == "__main__":
    main()
