#!/usr/bin/env python3
"""
Step 4 — turn confirmed recoveries into a reviewable patch set.

    python3 qc/doi/code/04_apply_sql.py

Reads  ../data/recovery.json, ../data/audit.json
Writes ../data/proposed_doi_corrections.csv   one row per correction, with evidence
       ../data/apply_doi_corrections.sql      the UPDATE statements
       ../data/review_queue.csv               everything not proposed, and why

This script does not touch the database and could not if it wanted to: the
project API is read-only. Applying is step 1 of the maintainer procedure in
docs/DATA_CHANGELOG.md, run against TGT by a person who has looked at the CSV.

The SQL is written defensively. Every UPDATE carries the old value in its WHERE
clause, so re-running is harmless and a row that has changed since the patch was
generated is skipped rather than overwritten. The transaction ends with a check
that the number of remaining malformed values fell by exactly the number of
statements applied — if it did not, the whole thing rolls back.
"""
import csv
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

REC = os.path.join(ROOT, "data", "recovery.json")
AUD = os.path.join(ROOT, "data", "audit.json")
CSV_OUT = os.path.join(ROOT, "data", "proposed_doi_corrections.csv")
SQL_OUT = os.path.join(ROOT, "data", "apply_doi_corrections.sql")
QUEUE_OUT = os.path.join(ROOT, "data", "review_queue.csv")


def sql_str(s):
    return "'" + str(s).replace("'", "''") + "'"


def main():
    with open(REC) as f:
        findings = json.load(f)
    with open(AUD) as f:
        audit = json.load(f)

    proposals = [r for r in findings if r["verdict"] == "recovered"]
    queue = [r for r in findings if r["verdict"] != "recovered"]

    # Refuse to emit a tier the audit did not actually clear.
    for key, s in audit["summary"].items():
        if s["precision"] < 1.0:
            print(f"  note: {key} audited at {100 * s['precision']:.1f}% "
                  f"({s['confirmed']}/{s['audited']})")
    audited_tiers = {k.split("/")[0] for k in audit["summary"]}
    emit = [r for r in proposals if r["tier"] in audited_tiers]
    skipped = len(proposals) - len(emit)
    if skipped:
        print(f"  {skipped} proposals held back: tier not covered by the audit")

    # Two different DOIs must never be proposed for the same record, and one DOI
    # must not be proposed for two records — either would mean a matching bug.
    by_id = Counter(r["id"] for r in emit)
    by_doi = Counter(r["proposed_doi"].lower() for r in emit)
    if any(v > 1 for v in by_id.values()):
        sys.exit("duplicate record ids in the patch set — aborting")
    collisions = {d: n for d, n in by_doi.items() if n > 1}
    if collisions:
        print(f"  WARNING: {len(collisions)} DOIs proposed for more than one record; "
              "these are held back for review")
        emit = [r for r in emit if by_doi[r["proposed_doi"].lower()] == 1]
        queue += [r for r in proposals if by_doi[r["proposed_doi"].lower()] > 1]

    cols = ["record_id", "journal_name", "year", "current_doi", "proposed_doi",
            "tier", "method", "title_similarity", "journal_verdict",
            "journal_basis", "author_overlap", "title"]
    with open(CSV_OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(emit, key=lambda r: (r["tier"], r["id"])):
            w.writerow({"record_id": r["id"], "journal_name": r["journal_name"],
                        "year": r["year"], "current_doi": r["doi"],
                        "proposed_doi": r["proposed_doi"], "tier": r["tier"],
                        "method": r["method"],
                        "title_similarity": r.get("title_similarity"),
                        "journal_verdict": r.get("journal_verdict"),
                        "journal_basis": r.get("journal_basis"),
                        "author_overlap": r.get("author_overlap"),
                        "title": (r["title"] or "")[:200]})

    qcols = ["record_id", "journal_name", "year", "current_doi", "pattern",
             "verdict", "best_candidate", "title_similarity", "journal_verdict", "title"]
    with open(QUEUE_OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=qcols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(queue, key=lambda r: (r["verdict"], r["id"])):
            w.writerow({"record_id": r["id"], "journal_name": r["journal_name"],
                        "year": r["year"], "current_doi": r["doi"],
                        "pattern": r["pattern"], "verdict": r["verdict"],
                        "best_candidate": r.get("proposed_doi"),
                        "title_similarity": r.get("title_similarity"),
                        "journal_verdict": r.get("journal_verdict"),
                        "title": (r["title"] or "")[:200]})

    n = len(emit)
    lines = [
        "-- Repair non-DOI values in swrd.papers.doi",
        "-- Generated by qc/doi/code/04_apply_sql.py. Review the accompanying",
        "-- proposed_doi_corrections.csv before running this.",
        "--",
        f"-- {n} corrections: "
        + ", ".join(f"tier {t} {c}" for t, c in sorted(Counter(r['tier'] for r in emit).items())),
        "-- Every statement matches on the current (broken) value, so this file is",
        "-- idempotent: a second run updates nothing.",
        "--",
        '--   psql "$TGT" -v ON_ERROR_STOP=1 -f apply_doi_corrections.sql',
        "",
        "begin;",
        "",
        "create temporary table _doi_before on commit drop as",
        "select count(*) as n from swrd.papers",
        r" where publication_year >= 1989 and doi is not null and doi !~ '^10\.[0-9]{4,9}/';",
        "",
    ]
    for r in sorted(emit, key=lambda r: (r["tier"], r["id"])):
        lines.append(
            f"update swrd.papers set doi = {sql_str(r['proposed_doi'])} "
            f"where id = {r['id']} and doi = {sql_str(r['doi'])};"
        )
    lines += [
        "",
        "-- The count of malformed values must fall by exactly the number of",
        "-- statements above. Anything else means a row moved underneath us.",
        "do $$",
        "declare before_n int; after_n int;",
        "begin",
        "  select n into before_n from _doi_before;",
        "  select count(*) into after_n from swrd.papers",
        r"   where publication_year >= 1989 and doi is not null and doi !~ '^10\.[0-9]{4,9}/';",
        f"  if before_n - after_n <> {n} then",
        f"    raise exception 'expected {n} repairs, saw %', before_n - after_n;",
        "  end if;",
        "  raise notice 'repaired % rows; % malformed values remain', before_n - after_n, after_n;",
        "end $$;",
        "",
        "commit;",
        "",
    ]
    with open(SQL_OUT, "w") as f:
        f.write("\n".join(lines))

    print(f"\nproposed corrections : {len(emit):,}  -> {CSV_OUT}")
    print(f"  by tier            : {dict(Counter(r['tier'] for r in emit))}")
    print(f"review queue         : {len(queue):,}  -> {QUEUE_OUT}")
    print(f"  by verdict         : {dict(Counter(r['verdict'] for r in queue))}")
    print(f"SQL                  : {SQL_OUT}")


if __name__ == "__main__":
    main()
