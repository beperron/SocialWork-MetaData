#!/usr/bin/env python3
"""
Fixes 4-8 — the five remaining ISSN-backed misattribution clusters (v1.3).

    python3 qc/journals/code/05_fix_clusters.py --selftest
    python3 qc/journals/code/05_fix_clusters.py            # all five
    python3 qc/journals/code/05_fix_clusters.py bjsw       # one

Writes, per cluster:  ../data/fix_<key>.csv   every record, with every signal
                      ../data/fix_<key>.sql   the UPDATE + archive insert
                      ../data/rollback_<key>.sql

One engine, five specs, because the five proofs are the same shape and five
near-identical scripts would drift apart. Everything cluster-specific is data
in CLUSTERS, not code.

WHY ONE CLUSTER STILL DIFFERS

Four clusters are fully separable by DOI prefix: every moving record carries a
prefix no staying record carries (10.1093 vs 10.1080, 10.1177 vs 10.1111, ...).
The fifth -- Administration in Social Work -> J. Religion & Spirituality -- is
Taylor & Francis on BOTH sides, so 10.1080 appears on moving and staying records
alike and the prefix cannot decide. There the Haworth SERIES CODE (10.1300/J377
is Religion & Spirituality; Admin's own is J147) plus the per-record ISSN carry
the proof, exactly as in the GLSS fix.

THE ADMIN CIRCULARITY, RESOLVED

Admin in Social Work is the one journal whose own ISSN sits in the review queue
rather than the proposed map: its majority vote reached only 70% (84/120)
*because of this contamination* -- 484 of its records are another journal's.
That is why the cluster analysis showed 0 "staying" records for it. The fix
breaks the loop; post-apply the vote is expected to clear the 0.80 bar, and
that re-vote is a named verification step, not an assumption.

GATES (each independently able to refuse a record)

  issn       Crossref ISSN intersects the TARGET journal's pair
  not_src    ...and does not intersect the SOURCE journal's pair
  container  Crossref container-title carries the target's distinctive tokens
  signal     DOI prefix in the cluster's moving set, or its Haworth series code
  era        REPORTED ONLY, never gated -- the GLSS lesson: Haworth back-catalogue
             dates are unreliable and bear nothing on journal identity

PREMISE CHECKS (whole-cluster, run before anything is emitted)

  disjoint   no ISSN-confirmed staying record carries a moving prefix
  direction  zero records under the TARGET carry the SOURCE's ISSN
  expected   the count matches the pinned EXPECTED; otherwise stop

Each patch also inserts its rows into swrd_archive.reassigned_papers_v1_3 in the
SAME transaction, so the unlinked in-database archive is never behind the data.

Read-only. Applying is the maintainer's step.
"""
import csv
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

SERIES = re.compile(r"^10\.1300/(J\d+)", re.I)

CLUSTERS = {
    "bjsw": dict(
        FROM_ID=3, TO_ID=63, EXPECTED=216,
        src_issn={"0045-3102", "1468-263X"},
        tgt_issn={"2165-0993", "2994-9769"},
        tgt_tokens={"asia", "pacific"},
        moving_prefixes={"10.1080"}, moving_series=set(),
        title="216 Asia Pacific J. of Social Work and Development articles under British J. of Social Work",
    ),
    "rswp": dict(
        FROM_ID=5, TO_ID=22, EXPECTED=318,
        src_issn={"1049-7315", "1552-7581"},
        tgt_issn={"1356-7500", "1365-2206"},
        tgt_tokens={"child", "family"},
        moving_prefixes={"10.1046", "10.1111"}, moving_series=set(),
        title="318 Child & Family Social Work articles under Research on Social Work Practice",
    ),
    "scsw": dict(
        FROM_ID=2, TO_ID=52, EXPECTED=318,
        src_issn={"0037-7317", "1553-0426"},
        tgt_issn={"1753-1403", "1753-1411"},
        tgt_tokens={"asian", "policy"},
        moving_prefixes={"10.1111"}, moving_series=set(),
        title="318 Asian Social Work and Policy Review articles under Studies in Clinical Social Work",
    ),
    "jswp": dict(
        FROM_ID=14, TO_ID=236, EXPECTED=181,
        src_issn={"0265-0533", "1465-3885"},
        tgt_issn={"0191-5096"},
        tgt_tokens={"sociology", "welfare"},
        moving_prefixes={"10.15453"}, moving_series=set(),
        title="181 J. of Sociology & Social Welfare articles under J. of Social Work Practice",
    ),
    "admin": dict(
        FROM_ID=12, TO_ID=224, EXPECTED=484,
        # Admin's ISSN comes from the REVIEW QUEUE (84/120 votes, diluted by
        # this very contamination), not the proposed map. Using it as the
        # not-source gate is exactly what it is good for.
        src_issn={"0364-3107", "1544-4376"},
        tgt_issn={"1542-6432", "1542-6440"},
        tgt_tokens={"religion"},
        # T&F on both sides, so 10.1080 alone cannot decide -- the ISSN and
        # container gates do the deciding; the J377 series corroborates the
        # Haworth-era slice. Admin's own Haworth code J147 must never appear.
        moving_prefixes={"10.1080"}, moving_series={"J377"},
        forbidden_series={"J147"},
        title="484 J. of Religion & Spirituality in Social Work articles under Administration in Social Work",
    ),
}


def norm_tokens(name):
    return set(re.findall(r"[a-z]+", (name or "").lower()))


def signal(doi):
    m = SERIES.match(doi)
    return ("series", m.group(1).upper()) if m else ("prefix", doi.split("/")[0])


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


def gates(rec, item, spec):
    issn = {s.strip().upper() for s in (item.get("ISSN") or []) if s}
    container = (item.get("container-title") or [None])[0]
    kind, val = signal(rec["doi"])
    sig_ok = (val in spec["moving_prefixes"] if kind == "prefix"
              else val in spec["moving_series"])
    if val in spec.get("forbidden_series", set()):
        sig_ok = False
    return {
        "issn_is_target": bool(issn & {s.upper() for s in spec["tgt_issn"]}),
        "not_source_issn": not (issn & {s.upper() for s in spec["src_issn"]}),
        "container_is_target": spec["tgt_tokens"] <= norm_tokens(container),
        "signal_ok": sig_ok,
    }, issn, container, f"{kind}:{val}"


# ---------------------------------------------------------------- selftest

def selftest():
    """Planted records that MUST be refused, one per gate, plus one that passes."""
    spec = CLUSTERS["bjsw"]
    cases = [
        ("wrong ISSN entirely", {"ISSN": ["1234-5678"], "container-title":
         ["Asia Pacific Journal of Social Work and Development"]},
         "10.1080/x", False),
        ("SOURCE's own ISSN", {"ISSN": ["0045-3102"], "container-title":
         ["Asia Pacific Journal of Social Work and Development"]},
         "10.1080/x", False),
        ("right ISSN, wrong container", {"ISSN": ["2165-0993"],
         "container-title": ["British Journal of Social Work"]},
         "10.1080/x", False),
        ("right everything, wrong prefix", {"ISSN": ["2165-0993"],
         "container-title": ["Asia Pacific Journal of Social Work and Development"]},
         "10.1093/x", False),
        ("genuine mover", {"ISSN": ["2165-0993"], "container-title":
         ["Asia Pacific Journal of Social Work and Development"]},
         "10.1080/02185385.2012.9756092", True),
    ]
    # the admin cluster's forbidden series must also refuse
    aspec = CLUSTERS["admin"]
    cases.append(("admin: J147 is Admin's own series",
                  {"ISSN": ["1542-6432"], "container-title":
                   ["Journal of Religion & Spirituality in Social Work"]},
                  "10.1300/J147v01n01_01", False))
    cases.append(("admin: J377 corroborates",
                  {"ISSN": ["1542-6432"], "container-title":
                   ["Journal of Religion & Spirituality in Social Work: Social Thought"]},
                  "10.1300/J377v01n01_01", True))
    bad = 0
    for name, item, doi, want in cases:
        sp = aspec if name.startswith("admin") else spec
        g, *_ = gates({"doi": doi}, item, sp)
        got = all(g.values())
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name:<38} "
              f"{'moves' if got else 'refused':<8} (want {'moves' if want else 'refused'})"
              + ("" if ok else f"  gates={g}"))
    print("\nselftest passed" if not bad else f"\n{bad} SELFTEST FAILURES")
    return 1 if bad else 0


# ---------------------------------------------------------------- per cluster

def run_cluster(key, spec, xref):
    frm, to = spec["FROM_ID"], spec["TO_ID"]
    jn = {j["id"]: j["name"] for j in Q.rows(
        f"select id, name from swrd.journals where id in ({frm},{to})")}
    if len(jn) != 2:
        sys.exit(f"{key}: journal rows {frm}/{to} not both present")
    src = Q.rows(rf"""
      select p.id, p.doi, p.title, p.publication_year as year
      from swrd.papers p
      where p.journal_id = {frm} and p.doi ~ '^10\.[0-9]{{4,9}}/'""")
    print(f"\n=== {key}: {jn[frm]}  ->  {jn[to]} ===")
    print(f"  under journal {frm}: {len(src):,} records with a valid DOI")

    rows, rejected, stay_sigs = [], [], Counter()
    for r in src:
        x = xref.get(r["doi"].lower())
        if not x:
            continue
        g, issn, container, sig = gates(r, x, spec)
        if issn & {s.upper() for s in spec["src_issn"]}:
            stay_sigs[sig] += 1          # ISSN-confirmed staying record
            continue
        if not g["issn_is_target"]:
            continue                     # some third journal; not this cluster
        row = {"record_id": r["id"], "doi": r["doi"], "year": r["year"],
               "signal": sig, "crossref_container": container,
               "crossref_issn": ",".join(sorted(issn)),
               "title": (r["title"] or "")[:160],
               **{k: str(v) for k, v in g.items()}}
        (rows if all(g.values()) else rejected).append(row)

    print(f"  target-ISSN records under {frm}: {len(rows) + len(rejected):,}"
          f"  (passing {len(rows):,}, rejected {len(rejected):,})")
    for r in rejected[:5]:
        fails = [k for k in ("issn_is_target", "not_source_issn",
                             "container_is_target", "signal_ok") if r[k] == "False"]
        print(f"     refused {r['record_id']} ({r['year']}) {r['signal']} fails={fails}")

    # PREMISE 1 — disjointness: no ISSN-confirmed staying record may carry a
    # moving signal. For admin this is vacuous (0 confirmed stayers) BY DESIGN;
    # its premise is carried by the direction check and the forbidden series.
    clash = {s for s in stay_sigs
             if s.split(":")[1] in spec["moving_prefixes"] | spec["moving_series"]}
    print(f"  staying records (ISSN-confirmed): {sum(stay_sigs.values()):,}  "
          f"sigs {dict(stay_sigs.most_common(4))}")
    if clash and key != "admin":
        sys.exit(f"{key}: staying records carry moving signal {clash} — "
                 "the premise is wrong, do not emit")

    # PREMISE 2 — direction: the target row must hold no SOURCE-ISSN record.
    got = 0
    tgt_rows = Q.rows(rf"""select p.doi from swrd.papers p
      where p.journal_id = {to} and p.doi ~ '^10\.[0-9]{{4,9}}/'""")
    for t in tgt_rows:
        xi = xref.get(t["doi"].lower())
        if xi and ({s.strip().upper() for s in (xi.get("ISSN") or [])}
                   & {s.upper() for s in spec["src_issn"]}):
            got += 1
    print(f"  direction check: {got} source-ISSN records under target {to} (must be 0)")
    if got:
        sys.exit(f"{key}: contamination runs both ways — this is not one bad ingest")

    if len(rows) != spec["EXPECTED"]:
        sys.exit(f"{key}: expected {spec['EXPECTED']}, found {len(rows)} — "
                 "the corpus moved; re-check before proposing")

    years = sorted(r["year"] for r in rows if r["year"])
    print(f"  moving era {years[0]}-{years[-1]}  (reported, not gated)")

    cols = ["record_id", "doi", "year", "signal", "crossref_container",
            "crossref_issn", "issn_is_target", "not_source_issn",
            "container_is_target", "signal_ok", "title"]
    with open(os.path.join(ROOT, "data", f"fix_{key}.csv"), "w",
              newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["record_id"]))

    ids = sorted(r["record_id"] for r in rows)
    idlist = ",".join(map(str, ids))
    n = len(ids)
    with open(os.path.join(ROOT, "data", f"fix_{key}.sql"), "w") as f:
        f.write(f"""-- {spec['title']}.
-- Move journal {frm} ({jn[frm]}) -> {to} ({jn[to]}).
--
-- Every record's Crossref ISSN is the target's, none carries the source's, the
-- container names the target, and the DOI signal agrees. Direction verified:
-- zero source-ISSN records sit under the target, so the error runs one way.
-- Row counts do not change; both journals are in the exported set.
--
-- The same transaction archives the prior state into the unlinked
-- swrd_archive.reassigned_papers_v1_3, so the in-database archive can never
-- lag the data.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f fix_{key}.sql

begin;

create schema if not exists swrd_archive;
create table if not exists swrd_archive.reassigned_papers_v1_3 (
  paper_id int not null, from_journal_id int not null, to_journal_id int not null,
  fix text not null, issue text not null,
  archived_at timestamptz not null default now());

do $$
declare live int;
begin
  select count(*) into live from swrd.papers
   where journal_id = {frm} and id in ({idlist});
  if live <> {n} then
    raise exception 'preflight: expected {n} records under journal {frm}, found %', live;
  end if;
end $$;

insert into swrd_archive.reassigned_papers_v1_3
  (paper_id, from_journal_id, to_journal_id, fix, issue)
select id, {frm}, {to}, 'fix_{key}', '#2'
  from swrd.papers where journal_id = {frm} and id in ({idlist});

update swrd.papers set journal_id = {to}
 where journal_id = {frm} and id in ({idlist});

do $$
declare moved int; left_behind int;
begin
  select count(*) into moved from swrd.papers
   where journal_id = {to} and id in ({idlist});
  select count(*) into left_behind from swrd.papers
   where journal_id = {frm} and id in ({idlist});
  if moved <> {n} or left_behind <> 0 then
    raise exception 'expected {n} moved and 0 left, saw % and %', moved, left_behind;
  end if;
  raise notice 'fix_{key}: moved % records from journal {frm} to {to}', moved;
end $$;

commit;
""")
    with open(os.path.join(ROOT, "data", f"rollback_{key}.sql"), "w") as f:
        f.write(f"""-- Reverse of fix_{key}.sql, written before applying.
--   psql "$TGT" -v ON_ERROR_STOP=1 -f rollback_{key}.sql
begin;
update swrd.papers set journal_id = {frm}
 where journal_id = {to} and id in ({idlist});
delete from swrd_archive.reassigned_papers_v1_3
 where fix = 'fix_{key}' and paper_id in ({idlist});
commit;
""")
    print(f"  {n:,} -> data/fix_{key}.csv / .sql / rollback")
    return ids


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    keys = [a for a in sys.argv[1:] if a in CLUSTERS] or list(CLUSTERS)
    xref = load_crossref()
    if not xref:
        sys.exit("no cached Crossref records — run the qc/doi pipeline first")
    total = 0
    for key in keys:
        total += len(run_cluster(key, CLUSTERS[key], xref))
    print(f"\n{total:,} records across {len(keys)} clusters. Nothing applied.")


if __name__ == "__main__":
    main()
