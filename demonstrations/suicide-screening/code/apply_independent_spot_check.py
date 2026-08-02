#!/usr/bin/env python3
"""Record and apply an independent manual spot check of 20 classifications."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent / "data"
ALL_PATH = BASE / "suicide_abstract_screening_results.json"
RELEVANT_PATH = BASE / "suicide_relevant_articles.json"
SUMMARY_PATH = BASE / "screening_summary.json"
CANDIDATES_PATH = BASE / "independent_spot_check_candidates.json"
REPORT_PATH = BASE / "independent_manual_spot_check.json"


DECISIONS = {
    "SWRD:98221": (False, "Not applicable", "Not applicable", "Suicide is contextual motivation for a broad disaster mental-health intervention and is not distinctly analyzed."),
    "SSWR:2016-U-0447": (True, "Empirical", "Quantitative", "Suicidal ideation is included in regression as an analyzed mechanism and has a separately reported significant association."),
    "SWRD:100438": (False, "Not applicable", "Not applicable", "Suicidality appears only in background on eating-disorder mortality; the article argues for culturally responsive eating-disorder treatment."),
    "SSWR:2026-U-0041": (False, "Not applicable", "Not applicable", "The phrase race suicide is a historical demographic ideology, not suicide or suicidal behavior."),
    "SWRD:24841": (True, "Non-empirical", "Not applicable", "The title is centrally about HIV/AIDS and suicide; no abstract establishes an empirical design, so the conservative title-only rule applies."),
    "SWRD:46344": (True, "Non-empirical", "Not applicable", "The title is centrally about suicide and Foucauldian history; no abstract establishes an empirical design."),
    "SWRD:38211": (True, "Non-empirical", "Not applicable", "Suicide-prevention programs are central, but the abstract does not describe a systematic, scoping, or meta-analytic search and selection method."),
    "SWRD:38347": (True, "Non-empirical", "Not applicable", "The paper centrally develops a conceptual suicide-risk model without analyzing new observations or conducting a systematic review."),
    "SSWR:2018-P-0091": (True, "Empirical", "Quantitative", "The study uses death records, spatial statistics, principal components, and regression to analyze suicide clusters."),
    "SSWR:2024-P-0285": (True, "Empirical", "Quantitative", "Suicide ideation is the stated outcome in a multivariable logistic-regression study."),
    "SSWR:2024-P-0287": (True, "Empirical", "Quantitative", "Suicidal ideation and attempts are explicit dependent variables analyzed using weighted logistic regression."),
    "SSWR:2026-P-0414": (True, "Empirical", "Quantitative", "Provider suicide-assessment attitudes and practices are measured by survey and analyzed with regression."),
    "SWRD:81403": (True, "Empirical", "Qualitative", "The article reports case-study findings on an online community for parents bereaved by suicide."),
    "SWRD:42729": (True, "Empirical", "Qualitative", "The abstract explicitly reports qualitative interview data on providers' suicide experience and responses."),
    "SWRD:39284": (True, "Empirical", "Qualitative", "The study uses a phenomenological psychological autopsy to analyze a suicide case."),
    "SSWR:2019-P-0257": (False, "Not applicable", "Not applicable", "Suicide and self-harm are minor items within a broader needs assessment of domestic-violence services and are not distinctly analyzed."),
    "SSWR:2018-U-0164": (True, "Empirical", "Review", "This PRISMA-guided systematic review distinctly reports suicidality as one psychosocial outcome domain."),
    "SWRD:63268": (True, "Empirical", "Review", "The suicide-prevention review explicitly uses PICO, PRISMA, predefined selection, and GRADE assessment."),
    "SWRD:56221": (True, "Empirical", "Review", "The suicide-loss intervention review reports a registered systematic search, study selection, synthesis, and bias assessment."),
    "SWRD:71706": (True, "Empirical", "Review", "The suicide-screening paper uses a database search and predefined inclusion criteria to synthesize assessment tools."),
}


def label_tuple(screening: dict) -> tuple:
    return (
        screening["is_relevant"],
        screening["evidence_class"],
        screening["empirical_method"],
    )


def main() -> None:
    document = json.loads(ALL_PATH.read_text(encoding="utf-8"))
    candidates_doc = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    candidates = candidates_doc["candidates"]
    rows_by_key = {row["record_key"]: row for row in document["screening_results"]}
    audited = []
    corrected = 0

    for candidate in candidates:
        key = candidate["record_key"]
        row = rows_by_key[key]
        relevant, evidence, method, rationale = DECISIONS[key]
        manual = {
            "is_relevant": relevant,
            "evidence_class": evidence,
            "empirical_method": method,
        }
        initial = dict(row["screening"])
        agreement = label_tuple(initial) == label_tuple(manual)
        if not agreement:
            row["screening_pre_manual_spot_check"] = initial
            row["screening"] = manual
            row["screening_source"] = "Independent manual spot-check correction"
            corrected += 1
        row["independent_manual_spot_check"] = {
            "random_seed": candidates_doc["random_seed"],
            "agreement": agreement,
            "manual_screening": manual,
            "rationale": rationale,
        }
        audited.append({
            "record_key": key,
            "sample_group": candidate["sample_group"],
            "title": row["title"],
            "initial_screening": initial,
            "manual_screening": manual,
            "agreement": agreement,
            "rationale": rationale,
            "final_screening": row["screening"],
        })

    group_stats = {}
    for group in ["Irrelevant", "Relevant Non-empirical", "Quantitative", "Qualitative", "Review"]:
        items = [item for item in audited if item["sample_group"] == group]
        agreements = sum(item["agreement"] for item in items)
        group_stats[group] = {
            "sampled": len(items),
            "agreements": agreements,
            "agreement_rate": agreements / len(items),
        }
    summary = {
        "method": "Independent manual inspection of title and full abstract against the prespecified rubric",
        "random_seed": candidates_doc["random_seed"],
        "excluded_prior_model_audit_records": candidates_doc["excluded_prior_audit_records"],
        "sample_per_group": 4,
        "total_sampled": len(audited),
        "agreements": sum(item["agreement"] for item in audited),
        "agreement_rate": sum(item["agreement"] for item in audited) / len(audited),
        "records_corrected": corrected,
        "group_statistics": group_stats,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    REPORT_PATH.write_text(
        json.dumps({"summary": summary, "audited_records": audited}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    rows = document["screening_results"]
    relevant_rows = [row for row in rows if row["screening"]["is_relevant"]]
    evidence_counts = Counter(row["screening"]["evidence_class"] for row in relevant_rows)
    method_counts = Counter(
        row["screening"]["empirical_method"]
        for row in relevant_rows
        if row["screening"]["evidence_class"] == "Empirical"
    )
    document["metadata"].update({
        "relevant_records": len(relevant_rows),
        "irrelevant_records": len(rows) - len(relevant_rows),
        "evidence_class_counts_among_relevant": dict(evidence_counts),
        "empirical_method_counts": dict(method_counts),
        "independent_manual_spot_check": summary,
    })
    ALL_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    RELEVANT_PATH.write_text(
        json.dumps(
            {
                "metadata": document["metadata"],
                "taxonomy": document["taxonomy"],
                "relevant_articles": relevant_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(json.dumps(document["metadata"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
