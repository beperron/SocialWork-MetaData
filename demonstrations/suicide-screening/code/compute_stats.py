#!/usr/bin/env python3
"""
Recompute every number on the demonstration page from the released labels.

    python3 compute_stats.py

Reads  ../data/suicide_abstract_screening_results.json  (all 2,034 screened records)
       ../data/screening_summary.json                   (audit metadata)
Writes ../data/stats.json                               (every count on the page)
       ../data/suicide_corpus_labeled.csv               (compact record-level table)

Nothing to install; no network access; no model required. The point is that a
reader can regenerate the page's numbers from the released data and check them.
"""
import csv
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

RESULTS = os.path.join(DATA, "suicide_abstract_screening_results.json")
SUMMARY = os.path.join(DATA, "screening_summary.json")
STATS = os.path.join(DATA, "stats.json")
TABLE = os.path.join(DATA, "suicide_corpus_labeled.csv")

# The five terminal outcome groups. Every screened record lands in exactly one.
GROUPS = ["Irrelevant", "Non-empirical", "Quantitative", "Qualitative", "Review"]


def group(rec):
    """Collapse the three screening decisions into one terminal outcome label."""
    s = rec["screening"]
    if not s["is_relevant"]:
        return "Irrelevant"
    if s["evidence_class"] == "Non-empirical":
        return "Non-empirical"
    return s["empirical_method"]


def main():
    with open(RESULTS) as f:
        results = json.load(f)
    with open(SUMMARY) as f:
        summary = json.load(f)

    recs = results["screening_results"]
    rel = [r for r in recs if r["screening"]["is_relevant"]]

    overall = Counter(group(r) for r in recs)
    by_source = {
        src: Counter(group(r) for r in recs if r["source_database"] == src)
        for src in ("SWRD", "SSWR")
    }

    # Screening effort, straight off the per-request Ollama metrics. Every record
    # was one request, so these sum to the actual wall-clock model time.
    durations = sorted(r["model_metrics"].get("total_duration_ns", 0) for r in recs)
    attempts = Counter(r["model_metrics"].get("attempt") for r in recs)
    prompt_tokens = sum(r["model_metrics"].get("prompt_eval_count", 0) for r in recs)
    out_tokens = sum(r["model_metrics"].get("eval_count", 0) for r in recs)

    basis = Counter(r["screening_basis"] for r in recs)
    title_only_outcomes = Counter(
        group(r) for r in recs if r["screening_basis"] == "title_only"
    )

    # Each audit stage stamps the pre-adjudication decision on the record it
    # touched, so both the number reviewed and the number whose label actually
    # moved are countable. Adjudication can confirm the original label, so these
    # two counts differ: 8 disagreements went to adjudication, 6 changed.
    adjudicated = [r for r in recs if "screening_initial" in r]
    spot_checked = [r for r in recs if "screening_pre_manual_spot_check" in r]

    years = {
        src: dict(
            sorted(
                Counter(str(r["year"]) for r in rel if r["source_database"] == src).items()
            )
        )
        for src in ("SWRD", "SSWR")
    }

    journals = Counter(
        r["journal_or_venue"] for r in rel if r["source_database"] == "SWRD"
    )

    # Evidence synthesis against primary empirical work, by period. Averaging
    # reviews over the whole window is misleading — none appear before 2004 —
    # so the page reports the trend rather than a flat rate.
    empirical = [r for r in rel if group(r) in ("Quantitative", "Qualitative", "Review")]
    reviews = [r for r in empirical if group(r) == "Review"]
    periods = [(1989, 1999), (2000, 2009), (2010, 2014), (2015, 2019), (2020, 2026)]
    synthesis = []
    for lo, hi in periods:
        e = sum(1 for r in empirical if lo <= r["year"] <= hi)
        v = sum(1 for r in reviews if lo <= r["year"] <= hi)
        synthesis.append({
            "period": f"{lo}-{hi}",
            "empirical": e,
            "syntheses": v,
            "share": round(v / e, 5) if e else None,
            "per_year": round(v / (hi - lo + 1), 2),
        })

    stats = {
        "screened_records": len(recs),
        "relevant_records": len(rel),
        "irrelevant_records": len(recs) - len(rel),
        "relevance_rate": round(len(rel) / len(recs), 4),
        "outcome_groups": {g: overall[g] for g in GROUPS},
        "evidence_class": {
            "Empirical": sum(overall[g] for g in ("Quantitative", "Qualitative", "Review")),
            "Non-empirical": overall["Non-empirical"],
        },
        "by_source": {
            src: {
                "screened": sum(1 for r in recs if r["source_database"] == src),
                "relevant": sum(by_source[src][g] for g in GROUPS if g != "Irrelevant"),
                **{g: by_source[src][g] for g in GROUPS},
            }
            for src in ("SWRD", "SSWR")
        },
        "screening_basis": dict(basis),
        "title_only_outcomes": dict(title_only_outcomes),
        "model_effort": {
            "requests": len(recs),
            "total_model_hours": round(sum(durations) / 1e9 / 3600, 3),
            "median_seconds_per_record": round(durations[len(durations) // 2] / 1e9, 2),
            "slowest_seconds": round(durations[-1] / 1e9, 2),
            "attempts_needed": {str(k): v for k, v in sorted(attempts.items())},
            "prompt_tokens": prompt_tokens,
            "completion_tokens": out_tokens,
        },
        "corrections": {
            "blind_audit_disagreements_adjudicated": len(adjudicated),
            "blind_audit_labels_changed": sum(
                1 for r in adjudicated if r["screening_initial"] != r["screening"]
            ),
            "spot_check_records_reviewed": len(spot_checked),
            "spot_check_labels_changed": sum(
                1 for r in spot_checked
                if r["screening_pre_manual_spot_check"] != r["screening"]
            ),
        },
        "synthesis_by_period": synthesis,
        "first_synthesis_year": min(r["year"] for r in reviews),
        "syntheses_since_2020": sum(1 for r in reviews if r["year"] >= 2020),
        "syntheses_by_year": dict(sorted(Counter(str(r["year"]) for r in reviews).items())),
        "relevant_by_year": years,
        "relevant_swrd_journal_count": len(journals),
        "top_swrd_journals": journals.most_common(15),
        "year_range": [min(r["year"] for r in rel), max(r["year"] for r in rel)],
        "audit": {
            "blind_model_audit": summary["accuracy_audit"],
            "independent_manual_spot_check": summary["independent_manual_spot_check"],
        },
        "model": results["metadata"]["model"],
        "prompt_version": results["metadata"]["prompt_version"],
    }

    with open(STATS, "w") as f:
        json.dump(stats, f, indent=2)
        f.write("\n")

    # A compact table without abstracts: readable in a spreadsheet, small enough
    # to skim, and enough to locate any record and check its label.
    cols = [
        "record_key", "source_database", "year", "title", "authors",
        "journal_or_venue", "doi", "record_type", "screening_basis",
        "is_relevant", "evidence_class", "empirical_method", "outcome_group",
        "database_method", "corrected_by_audit", "corrected_by_spot_check",
    ]
    with open(TABLE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            s = r["screening"]
            w.writerow({
                **{c: r.get(c) for c in cols},
                "is_relevant": s["is_relevant"],
                "evidence_class": s["evidence_class"],
                "empirical_method": s["empirical_method"],
                "outcome_group": group(r),
                "corrected_by_audit": "screening_initial" in r,
                "corrected_by_spot_check": "screening_pre_manual_spot_check" in r,
            })

    print(json.dumps(stats, indent=2)[:1800])
    print(f"\nwrote {STATS}\nwrote {TABLE}")


if __name__ == "__main__":
    main()
