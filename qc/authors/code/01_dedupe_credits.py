#!/usr/bin/env python3
"""
Fix 3 — one person credited more than once on the same paper.

    python3 qc/authors/code/01_dedupe_credits.py [--selftest]

Writes ../data/dedupe_credits.csv    every group, with the evidence
       ../data/dedupe_credits.sql    the DELETEs
       ../data/rollback_credits.sql  the reverse (re-INSERTs)
       ../data/credits_review.csv    groups the gate refused

WHAT THIS IS NOT

Issue #6 was filed as "spurious authors" and that framing does not survive the
data. Four separate defects are tangled together in swrd.paper_authors:

  1. one person split into two rows, surname and given name each becoming an
     "author" -- paper 100275 alternates Paat / Yok-Fong / Morales / Jessica
  2. a reference list ingested as authors -- ids 109627-109636 are the same ten
     rows in the same order on paper 100273 and on paper 100275, two unrelated
     articles
  3. the same person inserted twice by two later ingests
  4. positions colliding, several rows claiming byline slot 1

Only #3 is repaired here. #1, #2 and #4 stay open and flagged.

WHY NOT USE CROSSREF'S AUTHOR LIST AS TRUTH

The obvious repair is to make each paper's authors match Crossref. It is wrong,
and paper 19724 shows why: Crossref lists T. Booth alone, while the article is by
Tim Booth, Wendy Booth and David McConnell. Crossref author lists are routinely
truncated to the first author on older deposits. Trusting them would have deleted
two real co-authors, and no count-based guard catches it -- a one-author list is
trivially "covered".

So Crossref is used for two things only: to confirm the DOI identifies this
article, and to VETO merges. It never supplies the author list.

THE RULE

Within one paper, two credits are the same person when the surname matches and
the given-name evidence does not positively conflict:

    Charity Chenga   vs  Chenga, C.    -> same     (C is Charity's initial)
    Roux, A. A.      vs  Adrie Roux    -> same
    Freek Cronje     vs  Cronje, F.    -> same
    Booth, Tim       vs  Booth, Wendy  -> DIFFERENT, Tim and Wendy conflict
    van Nijnatten, C vs  van den Ackerveken, M -> DIFFERENT surnames

A missing given name is not evidence of agreement, it is absence of evidence, so
a bare surname merges only when the paper offers exactly one candidate given
name. Two candidates and the group is refused, not guessed.

THREE GATES, EACH ABLE TO REFUSE ON ITS OWN

  doi        title similarity >= 0.90 against the DOI's Crossref record, so we
             know which article we are editing
  surname    Crossref must not list two authors sharing the group's surname.
             This is the Booth veto, and it uses a signal the merge rule does
             not: Crossref's names rather than ours.
  ambiguity  a bare surname compatible with two different given names on the
             same paper refuses the group

The audit afterwards uses a further independent quantity -- the post-merge credit
count against Crossref's author count -- which no gate consulted.

--selftest plants known-wrong merges and fails if any is accepted.

Read-only. Applying is the maintainer's step.
"""
import csv
import os
import re
import sys
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

OUT_CSV = os.path.join(ROOT, "data", "dedupe_credits.csv")
OUT_SQL = os.path.join(ROOT, "data", "dedupe_credits.sql")
OUT_RB = os.path.join(ROOT, "data", "rollback_credits.sql")
OUT_Q = os.path.join(ROOT, "data", "credits_review.csv")

DOI_CONFIRM = 0.90

PARTICLE = {"van", "von", "de", "del", "della", "der", "den", "di", "da", "dos",
            "du", "la", "le", "el", "al", "bin", "ibn", "st", "ter", "ten"}
NOT_A_PERSON = re.compile(r"^\s*(anonymous|anon|staff|editors?|unknown|n/?a|"
                          r"et\.?\s*al\.?)\s*$", re.I)


# ---------------------------------------------------------------- name model

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(c))


def parse_name(name):
    """-> (surname, [given tokens]) or None.

    SWRD stores three orders, and getting the third wrong is not cosmetic.

      'Booth, Tim'    comma: surname first
      'Tim Booth'     given first, surname trails
      'Islam M.R.'    surname first, given collapsed to initials -- very common
                      in this corpus for Korean and Bangladeshi names

    Reading the third as given-first puts the INITIAL in the surname slot: 'Lee
    S.' becomes surname 's'. That silently disarms the Crossref surname veto,
    because it then looks up 's' rather than 'lee', and it merged Sunwoo Lee with
    Sangwoo Lee on paper 97213. So trailing single letters are treated as
    initials, never as the surname.

    Particles travel with the surname: 'van den Ackerveken' is one surname, not
    'Ackerveken' with two given names.
    """
    s = strip_accents(name or "").lower().strip().rstrip(".")
    s = re.sub(r"[^a-z,\s'-]", " ", s)
    if "," in s:
        surname, given = s.split(",", 1)
    else:
        toks = s.split()
        if not toks:
            return None
        lead = [t for t in toks if len(t) > 1]
        # There must BE a trailing initial: with none, all() over the empty tail
        # is vacuously true and 'Charity Chenga' becomes one long surname.
        if lead and len(lead) < len(toks) and toks[:len(lead)] == lead and \
                all(len(t) == 1 for t in toks[len(lead):]):
            # 'Islam M.R.' / 'Al Gharaibeh F.' -- surname first, then initials
            surname, given = " ".join(lead), " ".join(toks[len(lead):])
        else:
            i = len(toks) - 1
            while i > 0 and toks[i - 1] in PARTICLE:
                i -= 1
            surname, given = " ".join(toks[i:]), " ".join(toks[:i])
    surname = " ".join(surname.split())
    return (surname, given.split()) if surname else None


def compatible(a, b):
    """Same surname and no positive conflict in the given names.

    Only a DISAGREEMENT separates two credits. An initial against a full name
    agrees when the letter matches; a missing given name agrees with anything,
    which is why the ambiguity gate exists downstream.
    """
    if a[0] != b[0]:
        return False
    g1, g2 = a[1], b[1]
    if not g1 or not g2:
        return True
    for x, y in zip(g1, g2):
        if len(x) == 1 or len(y) == 1:
            if x[0] != y[0]:
                return False
        elif x != y:
            return False
    return True


def completeness(link):
    """Rank renderings of one name; the fullest wins, ties go to the older row."""
    p = link["parsed"]
    full = sum(1 for g in p[1] if len(g) > 1)
    return (-full, -len(p[1]), -len(link["name"]), link["author_id"])


def group_paper(links):
    """Partition one paper's credits into people. A credit joins a group only if
    it is compatible with EVERY member, so one conflict blocks the merge."""
    groups = []
    for l in links:
        for g in groups:
            if all(compatible(l["parsed"], m["parsed"]) for m in g):
                g.append(l)
                break
        else:
            groups.append([l])
    return groups


# ---------------------------------------------------------------- selftest

SELFTEST = [
    # (case, names, must_merge)
    ("two same-surname co-authors", ["Booth, Tim", "Booth, Wendy"], False),
    ("different surnames", ["van Nijnatten, C", "van den Ackerveken, M"], False),
    ("initial vs conflicting name", ["Smith, J.", "Smith, Robert"], False),
    ("particle surname split", ["de Jesus, Maria", "Jesus, Maria"], False),
    ("initial matches full name", ["Chenga, C.", "Charity Chenga"], True),
    ("two initials vs full names", ["Roux, A. A.", "Adrie Roux"], True),
    ("accent difference only", ["Freek Cronje", "Cronje, F."], True),
    ("reversed order", ["Booth, Tim", "Tim Booth"], True),
    # 'Surname Initials' format. Reading the initial as the surname merged two
    # different people on paper 72143 and disarmed the veto on 97213.
    ("surname-first, initials conflict", ["Park Y.", "Park S.Y."], False),
    ("surname-first, initials agree", ["Islam M.R.", "Islam M."], True),
    ("compound surname vs initial", ["Al Gharaibeh F.", "Fakir Al Gharaibeh"], True),
    ("initials-only, surname must not be the initial",
     ["Lee S.", "Kim S."], False),
]


def selftest():
    bad = 0
    for case, names, must in SELFTEST:
        links = [{"name": n, "parsed": parse_name(n), "author_id": i}
                 for i, n in enumerate(names)]
        merged = len(group_paper(links)) == 1
        ok = merged == must
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {case:<30} "
              f"{'merged' if merged else 'separate':<9} (want {'merged' if must else 'separate'})")
    print("\nselftest passed" if not bad else f"\n{bad} SELFTEST FAILURES")
    return 1 if bad else 0


# ---------------------------------------------------------------- main

def load_crossref():
    merged = {}
    Q.CACHE = os.path.join(HERE, "..", "..", "doi", "cache")
    for name in ("column_lookup", "doi_lookup", "audit_lookup"):
        try:
            for _, v in Q.cache_load(name).items():
                if isinstance(v, dict) and v.get("DOI"):
                    merged[v["DOI"].lower()] = v
        except Exception:
            continue
    return merged


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    xref = load_crossref()
    if not xref:
        sys.exit("no cached Crossref records — run the qc/doi pipeline first")

    papers = {r["id"]: r for r in Q.rows(
        r"""select id, doi, title, publication_year as year
            from swrd.papers
            where publication_year >= 1989 and doi ~ '^10\.[0-9]{4,9}/'""")}
    print(f"papers in scope (1989+, valid DOI): {len(papers):,}")

    links = defaultdict(list)
    for r in Q.rows(
        r"""select pa.paper_id, pa.author_id, pa."position", a.name
            from swrd.paper_authors pa
            join swrd.authors a on a.id = pa.author_id
            join swrd.papers p on p.id = pa.paper_id
            where p.publication_year >= 1989 and p.doi ~ '^10\.[0-9]{4,9}/'"""):
        links[r["paper_id"]].append(r)
    print(f"authorship links                  : {sum(len(v) for v in links.values()):,}")

    rows, queued = [], []
    stats = defaultdict(int)
    for pid, ls in links.items():
        paper = papers.get(pid)
        if not paper:
            continue
        item = xref.get(paper["doi"].lower())
        if not item:
            stats["doi_not_in_crossref"] += 1
            continue
        if Q.title_sim(paper["title"] or "", Q.cr_title(item)) < DOI_CONFIRM:
            stats["doi_not_confirmed_by_title"] += 1
            continue

        # Crossref surnames, for the veto only. Never used as the author list.
        cr_surnames = defaultdict(int)
        cr_given = set()
        for a in (item.get("author") or []):
            p = parse_name((a.get("family") or "") or (a.get("name") or ""))
            if p:
                cr_surnames[p[0]] += 1
            for t in strip_accents(a.get("given") or "").lower().replace(".", " ").split():
                if len(t) > 1:
                    cr_given.add(t)

        parsed = []
        for l in ls:
            if NOT_A_PERSON.match(l["name"] or ""):
                stats["skipped_non_person_name"] += 1
                continue
            p = parse_name(l["name"])
            if p:
                parsed.append({**l, "parsed": p})
        if len(parsed) < 2:
            continue

        for g in group_paper(parsed):
            if len(g) < 2:
                continue
            surname = g[0]["parsed"][0]
            keep, *drop = sorted(g, key=completeness)

            base = {"paper_id": pid, "doi": paper["doi"], "year": paper["year"],
                    "surname": surname,
                    "keep_author_id": keep["author_id"], "keep_name": keep["name"],
                    "drop_author_ids": ";".join(str(d["author_id"]) for d in drop),
                    "drop_names": " | ".join(d["name"] for d in drop),
                    "positions": ";".join(str(d["position"]) for d in [keep] + drop),
                    "crossref_same_surname": cr_surnames.get(surname, 0),
                    "crossref_authors": len(item.get("author") or []),
                    "title": (paper["title"] or "")[:120]}

            # GATE 1 — Crossref lists two people with this surname. Booth veto.
            if cr_surnames.get(surname, 0) > 1:
                queued.append({**base, "refused": "crossref_has_two_of_this_surname"})
                stats["refused_surname_veto"] += 1
                continue
            # GATE 1b — the key is not a surname at all, it is somebody's GIVEN
            # name. This is bug (b) in a new input class: the surname-first
            # branch accepts a leading token without ever checking it IS a
            # surname, so a bare fragment left by the split-name defect (#1)
            # becomes a group key. parse_name('John') -> ('john', []), GATE 1
            # then looks up cr_surnames['john'] = 0 and silently passes.
            #
            # On papers 100522/100548 that merged the fragment 'John' into
            # 'John R.' -- John Coates folded into John R. Graham. Two people.
            if cr_surnames.get(surname, 0) == 0 and surname in cr_given:
                queued.append({**base, "refused": "key_is_a_crossref_given_name"})
                stats["refused_given_name_key"] += 1
                continue
            # GATE 2 — a bare surname that fits two different given names.
            #
            # STRUCTURALLY UNREACHABLE, kept as a tripwire. compatible() already
            # forces every given-bearing member of a group to share a first
            # initial, so len(initials) > 1 cannot hold here. It fires only if
            # someone loosens compatible(); the count below is therefore 0 by
            # construction, not by measurement.
            bare = [m for m in g if not m["parsed"][1]]
            initials = {m["parsed"][1][0][0] for m in g if m["parsed"][1]}
            if bare and len(initials) > 1:
                queued.append({**base, "refused": "bare_surname_fits_two_people"})
                stats["refused_ambiguous"] += 1
                continue
            # GATE 3 — a row linked to the paper twice cannot be addressed by
            # (paper_id, author_id) alone. Also structurally 0: that pair is
            # unique in swrd.paper_authors (verified against the live table).
            # Kept so the patch stays correct if that ever stops being true.
            if len({d["author_id"] for d in drop}) != len(drop) or \
                    keep["author_id"] in {d["author_id"] for d in drop}:
                queued.append({**base, "refused": "author_id_repeats_on_this_paper"})
                stats["refused_repeat_link"] += 1
                continue

            rows.append(base)
            stats["merged_groups"] += 1
            stats["links_dropped"] += len(drop)
            stats["papers"] = stats["papers"]

    affected = sorted({r["paper_id"] for r in rows})
    print("\nscreening:")
    for k in ("doi_not_in_crossref", "doi_not_confirmed_by_title",
              "skipped_non_person_name", "refused_surname_veto",
              "refused_given_name_key", "refused_ambiguous", "refused_repeat_link"):
        print(f"  {k:<30} {stats[k]:>7,}")
    print(f"\n  merged groups                  {stats['merged_groups']:>7,}")
    print(f"  duplicate links to delete      {stats['links_dropped']:>7,}")
    print(f"  papers affected                {len(affected):>7,}")

    # ---- audit on a quantity no gate used: post-merge count vs Crossref count
    agree = under = over = 0
    per_paper = defaultdict(int)
    for r in rows:
        per_paper[r["paper_id"]] += len(r["drop_author_ids"].split(";"))
    for pid in affected:
        after = len(links[pid]) - per_paper[pid]
        n_cr = len(xref[papers[pid]["doi"].lower()].get("author") or [])
        if after == n_cr:
            agree += 1
        elif after < n_cr:
            under += 1
        else:
            over += 1
    print("\naudit — credits remaining after the merge vs Crossref's author count")
    print("        (Crossref truncation makes 'more than Crossref' expected;")
    print("         FEWER than Crossref would mean we deleted a real author)")
    print(f"  exactly equal          {agree:>7,}")
    print(f"  more than Crossref     {over:>7,}")
    print(f"  FEWER than Crossref    {under:>7,}   <- must be 0")
    if under:
        sys.exit("\naudit failed: some papers would end with fewer credits than "
                 "Crossref lists. Do not apply.")

    cols = ["paper_id", "doi", "year", "surname", "keep_author_id", "keep_name",
            "drop_author_ids", "drop_names", "positions", "crossref_same_surname",
            "crossref_authors", "title"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["paper_id"], r["surname"])))
    with open(OUT_Q, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["refused"], extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(queued, key=lambda r: (r["refused"], r["paper_id"])))

    pairs = sorted({(r["paper_id"], int(a))
                    for r in rows for a in r["drop_author_ids"].split(";")})
    vals = ",".join(f"({p},{a})" for p, a in pairs)

    # Read every live link on every affected paper. Needed twice: to restore the
    # deleted rows exactly, and to decide which surviving credits inherit the
    # corresponding-author flag. Batched -- a single IN of ~7,500 tuples returns
    # HTTP 500 from the endpoint.
    want, live, live_rows = set(pairs), {}, []
    ids = sorted({p for p, _ in pairs})
    for i in range(0, len(ids), 500):
        chunk = ",".join(map(str, ids[i:i + 500]))
        for r in Q.rows('select paper_id, author_id, "position", is_corresponding, '
                        "created_at from swrd.paper_authors "
                        f"where paper_id in ({chunk})"):
            live_rows.append(r)
            if (r["paper_id"], r["author_id"]) in want:
                live[(r["paper_id"], r["author_id"])] = r
    if len(live) != len(pairs):
        sys.exit(f"read back {len(live):,} of {len(pairs):,} targeted links — "
                 "the table moved under us; re-run before applying")

    # ---- is_corresponding must MERGE, not be discarded with the row.
    #
    # A deleted duplicate can be the row carrying is_corresponding. Deleting it
    # does not just lose a row, it silently turns a true statement false: there
    # are ZERO nulls in this column corpus-wide, so false is an assertion, not
    # "unknown". It cannot be recovered from position either -- 1,236 flagged
    # rows sit at position <> 1 and 94,566 position-1 rows are false. The value
    # ships, in migration/10_export_release_csv.py and in the
    # author_publication_stats.corresponding_author_count view.
    #
    # So before deleting, the surviving credit inherits the flag. Ordering
    # matters: this runs AFTER gate 1b, because on paper 100522 the dropped
    # 'John' row is flagged and the keeper is 'John R.' -- a different person.
    # Promoting first would have turned a bad merge into a false attribution.
    corr = {(r["paper_id"], r["author_id"]): r["is_corresponding"]
            for r in live_rows}
    promote = sorted({
        (r["paper_id"], r["keep_author_id"])
        for r in rows
        if not corr.get((r["paper_id"], r["keep_author_id"]))
        and any(corr.get((r["paper_id"], int(a)))
                for a in r["drop_author_ids"].split(";"))})
    dropped_flags = sum(1 for p in pairs if corr.get(p))
    print(f"\ncorresponding-author flags on deleted rows : {dropped_flags:,}")
    print(f"  promoted onto the surviving credit       : {len(promote):,}")
    pvals = ",\n".join(f"  ({p},{a})" for p, a in promote) or "  (null, null)"
    with open(OUT_SQL, "w") as f:
        f.write(f"""-- Remove {len(pairs)} duplicate authorship credits: one person credited
-- more than once on the same paper.
--
-- Each deleted row has a surviving row on the same paper carrying the same
-- surname and a compatible -- usually fuller -- given name. Nobody loses a
-- credit; {len(affected)} papers stop crediting the same person twice.
--
-- Crossref did NOT supply the author lists. It confirmed the DOI identifies the
-- article (title similarity >= {DOI_CONFIRM}) and it vetoed any group whose surname it
-- lists twice, which is what protects papers like 19724, where Crossref names
-- only T. Booth but the article is by Tim Booth, Wendy Booth and David McConnell.
--
-- Author rows themselves are untouched; only the paper_authors links go, and
-- swrd.papers is not modified, so the release row count cannot move.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f dedupe_credits.sql

begin;

create temporary table _dupes (paper_id int, author_id int) on commit drop;
insert into _dupes (paper_id, author_id) values
{vals};

create temporary table _promote (paper_id int, author_id int) on commit drop;
insert into _promote (paper_id, author_id) values
{pvals};

-- Papers that assert a corresponding author right now. Snapshotted BEFORE any
-- change so the post-delete assertion has something honest to compare against.
create temporary table _corr_before on commit drop as
  select distinct paper_id from swrd.paper_authors
   where is_corresponding
     and paper_id in (select paper_id from _dupes);

-- Preflight against the LIVE table, not against this patch. Every targeted link
-- must exist, and every paper must keep at least one credit.
do $$
declare present int; orphaned int;
begin
  select count(*) into present
    from swrd.paper_authors pa join _dupes d
      on d.paper_id = pa.paper_id and d.author_id = pa.author_id;
  if present <> {len(pairs)} then
    raise exception 'expected {len(pairs)} live links, found %', present;
  end if;
  select count(*) into orphaned from (
    select pa.paper_id from swrd.paper_authors pa
     group by pa.paper_id
    having count(*) = count(*) filter (
      where (pa.paper_id, pa.author_id) in (select paper_id, author_id from _dupes))
  ) t;
  if orphaned <> 0 then
    raise exception '% papers would be left with no author at all', orphaned;
  end if;
end $$;

-- Inherit the corresponding-author flag BEFORE the row carrying it is deleted.
update swrd.paper_authors pa
   set is_corresponding = true
  from _promote m
 where pa.paper_id = m.paper_id and pa.author_id = m.author_id;

delete from swrd.paper_authors pa
 using _dupes d
 where d.paper_id = pa.paper_id and d.author_id = pa.author_id;

do $$
declare gone int; lost int;
begin
  select count(*) into gone
    from swrd.paper_authors pa join _dupes d
      on d.paper_id = pa.paper_id and d.author_id = pa.author_id;
  if gone <> 0 then
    raise exception '% targeted links survived the delete', gone;
  end if;
  -- No paper may go from asserting a corresponding author to asserting none.
  select count(*) into lost from _corr_before b
   where not exists (select 1 from swrd.paper_authors pa
                      where pa.paper_id = b.paper_id and pa.is_corresponding);
  if lost <> 0 then
    raise exception '% papers lost their corresponding author', lost;
  end if;
  raise notice 'removed {len(pairs)} duplicate credits across {len(affected)} papers; '
               'promoted {len(promote)} corresponding-author flags';
end $$;

commit;
""")

    def lit(v):
        if v is None:
            return "null"
        if isinstance(v, bool):
            return str(v).lower()
        if isinstance(v, (int, float)):
            return str(v)
        return "'" + str(v).replace("'", "''") + "'"

    restore = ",\n".join(
        "  (%d, %d, %s, %s, %s)" % (
            p, a, lit(live[(p, a)]["position"]),
            lit(live[(p, a)]["is_corresponding"]),
            lit(live[(p, a)]["created_at"]))
        for p, a in pairs if (p, a) in live)
    with open(OUT_RB, "w") as f:
        f.write(f"""-- Reverse of dedupe_credits.sql, written before applying and holding EVERY
-- column of swrd.paper_authors read off the live table beforehand, so the
-- restore is byte-exact rather than approximate. created_at is included on
-- purpose: letting it default would silently rewrite the ingest history of
-- {len(pairs)} rows, which is not what "rollback" should mean.
--
-- The delete removes {len(pairs)} rows; this puts back {len(restore.splitlines())}.
--
-- The rows go through a temp table rather than a literal IN list. A
-- {len(pairs)}-tuple IN exceeds max_stack_depth and the statement dies with
-- 'stack depth limit exceeded' -- found by the round-trip test, not by reading.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f rollback_credits.sql

begin;

create temporary table _restore (
  paper_id int, author_id int, "position" int,
  is_corresponding boolean, created_at timestamp) on commit drop;

insert into _restore (paper_id, author_id, "position", is_corresponding, created_at)
values
{restore};

insert into swrd.paper_authors
  (paper_id, author_id, "position", is_corresponding, created_at)
select paper_id, author_id, "position", is_corresponding, created_at from _restore
on conflict do nothing;

-- Undo the corresponding-author promotion. Restoring only the deleted rows
-- would leave {len(promote)} surviving credits flagged true that were false
-- before, so the "rollback" would quietly change data of its own.
create temporary table _unpromote (paper_id int, author_id int) on commit drop;
insert into _unpromote (paper_id, author_id) values
{pvals};

update swrd.paper_authors pa
   set is_corresponding = false
  from _unpromote m
 where pa.paper_id = m.paper_id and pa.author_id = m.author_id;

do $$
declare back int;
begin
  select count(*) into back
    from swrd.paper_authors pa join _restore r
      on r.paper_id = pa.paper_id and r.author_id = pa.author_id;
  if back <> {len(pairs)} then
    raise exception 'expected {len(pairs)} links restored, found %', back;
  end if;
  raise notice 'restored {len(pairs)} authorship credits';
end $$;

commit;
""")
    print(f"\n{len(pairs):,} deletions -> {OUT_CSV}\n{OUT_SQL}\n{OUT_RB}\n"
          f"{len(queued):,} refused -> {OUT_Q}")


if __name__ == "__main__":
    main()
