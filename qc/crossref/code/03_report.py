#!/usr/bin/env python3
"""
Step 3 — turn findings into a reviewable patch set and a summary.

    python3 03_report.py

Reads  ../data/findings.json
Writes ../data/proposed_corrections.csv   one row per proposed change
       ../data/pilot_summary.json         counts behind the write-up

Every row carries the evidence that produced it. Nothing is applied here; the
CSV is the input to step 1 of the maintainer procedure in docs/DATA_CHANGELOG.md.
"""
import collections
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swrdqc as Q

FIND = os.path.join(Q.DATA, "findings.json")
CSV_OUT = os.path.join(Q.DATA, "proposed_corrections.csv")
SUM_OUT = os.path.join(Q.DATA, "pilot_summary.json")

# Journals that changed name. Crossref keeps the historical container-title, so
# a name-based journal check flags these as mismatches when nothing is wrong.
# Enumerated rather than fuzzy-matched: the list is short and the alternative
# is silently suppressing real misattributions.
RENAMES = [
    {"smith college studies in social work",
     "studies in clinical social work transforming practice education and research"},
]


def rename_pair(a, b):
    na, nb = Q.norm_journal(a), Q.norm_journal(b)
    return any(na in grp and nb in grp for grp in RENAMES)


def main():
    with open(FIND) as f:
        findings = json.load(f)

    corrections = []
    for r in findings:
        ev = (f"crossref={r.get('crossref_doi')} sim={r.get('title_similarity')} "
              f"year={r.get('year_verdict')} journal={r.get('journal_verdict')}"
              f"/{r.get('journal_basis')}")

        if r["verdict"] == "recovered" and r.get("proposed_doi"):
            corrections.append({
                "record_id": r["id"], "field": "doi", "current": r.get("doi") or "",
                "proposed": r["proposed_doi"], "tier": r["tier"],
                "basis": r["check"], "evidence": ev, "title": (r["title"] or "")[:120],
            })

        if r["verdict"] == "field_mismatch":
            for fld in r.get("mismatched_fields", []):
                if fld == "journal":
                    if rename_pair(r.get("journal_name"), r.get("crossref_journal")):
                        continue                      # historical name, not an error
                    corrections.append({
                        "record_id": r["id"], "field": "journal",
                        "current": r.get("journal_name") or "",
                        "proposed": r.get("crossref_journal") or "",
                        "tier": "B", "basis": "doi_lookup", "evidence": ev,
                        "title": (r["title"] or "")[:120],
                    })
                elif fld == "title":
                    corrections.append({
                        "record_id": r["id"], "field": "title(review)",
                        "current": (r["title"] or "")[:120],
                        "proposed": (r.get("crossref_title") or "")[:120],
                        "tier": "C", "basis": "doi_lookup", "evidence": ev,
                        "title": (r["title"] or "")[:120],
                    })
                # 'year' deliberately omitted: see pilot findings — every year
                # flag in the sample was a Crossref bulk-registration artifact,
                # not a SWRD error.

    with open(CSV_OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["record_id", "field", "current", "proposed",
                                          "tier", "basis", "evidence", "title"])
        w.writeheader()
        w.writerows(corrections)

    summary = {
        "sample_size": len(findings),
        "by_stratum": dict(collections.Counter(r["stratum"] for r in findings)),
        "by_verdict": dict(collections.Counter(r["verdict"] for r in findings)),
        "by_tier": dict(collections.Counter(r["tier"] for r in findings)),
        "verdict_by_stratum": {
            s: dict(collections.Counter(r["verdict"] for r in findings if r["stratum"] == s))
            for s in sorted({r["stratum"] for r in findings})
        },
        "journal_check_basis": dict(collections.Counter(
            r.get("journal_basis") for r in findings if r.get("journal_basis"))),
        "proposed_corrections": {
            "total": len(corrections),
            "by_field": dict(collections.Counter(c["field"] for c in corrections)),
            "by_tier": dict(collections.Counter(c["tier"] for c in corrections)),
        },
    }
    with open(SUM_OUT, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary["proposed_corrections"], indent=2))
    print(f"\n{len(corrections)} proposed corrections -> {CSV_OUT}")
    print(f"summary -> {SUM_OUT}")


if __name__ == "__main__":
    main()
