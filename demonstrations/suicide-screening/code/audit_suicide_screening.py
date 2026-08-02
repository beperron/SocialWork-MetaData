#!/usr/bin/env python3
"""Blind stratified accuracy audit and adjudication for suicide screening."""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import screen_suicide_abstracts_ollama as primary


OUTPUT_DIR = primary.OUTPUT_DIR
ALL_RESULTS_PATH = primary.ALL_RESULTS_PATH
RELEVANT_PATH = primary.RELEVANT_PATH
SUMMARY_PATH = primary.SUMMARY_PATH
AUDIT_PATH = OUTPUT_DIR / "accuracy_audit.json"
BLIND_CHECKPOINT = OUTPUT_DIR / "accuracy_audit_blind_checkpoint.jsonl"
ADJUDICATION_CHECKPOINT = OUTPUT_DIR / "accuracy_audit_adjudication_checkpoint.jsonl"

RANDOM_SEED = 20260802
SAMPLE_PER_GROUP = 20
AUDIT_VERSION = "stratified-blind-audit-v1.0"


BASE_RUBRIC = primary.SYSTEM_PROMPT.split("OUTPUT CODES")[0].strip()
BLIND_PROMPT = BASE_RUBRIC + """

This is a blind accuracy audit. Re-evaluate the single record from scratch; no earlier decision is supplied. Return the required JSON only. Provide one concise sentence explaining relevance and one concise sentence explaining evidence design. For a relevant title-only record whose wording provides no defensible indication of empirical design, use the conservative fallback Non-empirical. If Empirical, you must choose Quantitative, Qualitative, or Review.
"""

ADJUDICATION_PROMPT = BASE_RUBRIC + """

You are adjudicating a disagreement between two prior screens of one record. Neither prior decision is presumed correct. Re-read the title and abstract, evaluate both stated rationales against the rubric, and return the final classification as JSON. For a relevant title-only record whose wording provides no defensible indication of empirical design, use the conservative fallback Non-empirical. If Empirical, you must choose Quantitative, Qualitative, or Review. Provide concise final rationales.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "is_relevant": {"type": "boolean"},
        "relevance_rationale": {"type": "string"},
        "evidence_class": {
            "type": "string",
            "enum": ["Empirical", "Non-empirical", "Not applicable"],
        },
        "empirical_method": {
            "type": "string",
            "enum": ["Quantitative", "Qualitative", "Review", "Not applicable"],
        },
        "classification_rationale": {"type": "string"},
        "confidence": {"type": "string", "enum": ["High", "Moderate", "Low"]},
    },
    "required": [
        "is_relevant",
        "relevance_rationale",
        "evidence_class",
        "empirical_method",
        "classification_rationale",
        "confidence",
    ],
}


def logical(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    required = set(SCHEMA["required"])
    if not required.issubset(value):
        return False
    rel = value["is_relevant"]
    ec = value["evidence_class"]
    method = value["empirical_method"]
    if not isinstance(rel, bool):
        return False
    if not rel:
        return ec == "Not applicable" and method == "Not applicable"
    if ec == "Non-empirical":
        return method == "Not applicable"
    if ec == "Empirical":
        return method in {"Quantitative", "Qualitative", "Review"}
    return False


def model_call(messages: list[dict], think: bool = False) -> tuple[dict, dict]:
    payload = {
        "model": primary.MODEL,
        "stream": False,
        "think": think,
        "format": SCHEMA,
        "options": {"temperature": 0, "seed": 8675309, "num_ctx": 4096},
        "messages": messages,
    }
    last_error: Exception | None = None
    for attempt in range(1, 5):
        request = urllib.request.Request(
            primary.OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=900) as response:
                result = json.load(response)
            screening = json.loads(result["message"]["content"])
            if logical(screening):
                return screening, {
                    "attempt": attempt,
                    "total_duration_ns": result.get("total_duration"),
                    "prompt_eval_count": result.get("prompt_eval_count"),
                    "eval_count": result.get("eval_count"),
                    "thinking_tokens": result.get("thinking_count"),
                }
            last_error = ValueError(f"Logically invalid output: {screening}")
            payload["messages"] = messages + [{
                "role": "user",
                "content": "The output violated the forced logical rules. Re-evaluate and return corrected JSON only.",
            }]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
            last_error = exc
            time.sleep(min(2**attempt, 8))
    raise RuntimeError("Audit model call failed after four attempts") from last_error


def record_text(row: dict) -> dict:
    return {
        "title": row.get("title") or "",
        "abstract": (row.get("abstract") or "").strip()
        or "[NO ABSTRACT AVAILABLE — SCREEN FROM TITLE ONLY]",
    }


def group_name(row: dict) -> str:
    s = row["screening"]
    if not s["is_relevant"]:
        return "Irrelevant"
    if s["evidence_class"] == "Non-empirical":
        return "Relevant Non-empirical"
    return s["empirical_method"]


def label_tuple(screening: dict) -> tuple:
    return (
        screening["is_relevant"],
        screening["evidence_class"],
        screening["empirical_method"],
    )


def load_jsonl(path: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("audit_version") != AUDIT_VERSION:
            raise RuntimeError(f"Wrong audit version in {path} line {line_number}")
        result[item["record_key"]] = item
    return result


def append_jsonl(handle, item: dict) -> None:
    handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


def recalculate_documents(document: dict) -> tuple[dict, dict, dict]:
    rows = document["screening_results"]
    relevant = [r for r in rows if r["screening"]["is_relevant"]]
    evidence = Counter(r["screening"]["evidence_class"] for r in relevant)
    methods = Counter(
        r["screening"]["empirical_method"]
        for r in relevant
        if r["screening"]["evidence_class"] == "Empirical"
    )
    summary = dict(document["metadata"])
    summary.update({
        "relevant_records": len(relevant),
        "irrelevant_records": len(rows) - len(relevant),
        "evidence_class_counts_among_relevant": dict(evidence),
        "empirical_method_counts": dict(methods),
        "accuracy_audit_version": AUDIT_VERSION,
        "accuracy_audit_random_seed": RANDOM_SEED,
        "accuracy_audit_sample_size": SAMPLE_PER_GROUP,
        "accuracy_audit_completed_at": datetime.now(timezone.utc).isoformat(),
    })
    document["metadata"] = summary
    relevant_document = {
        "metadata": summary,
        "taxonomy": document["taxonomy"],
        "relevant_articles": relevant,
    }
    return document, relevant_document, summary


def main() -> None:
    document = json.loads(ALL_RESULTS_PATH.read_text(encoding="utf-8"))
    rows = document["screening_results"]
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[group_name(row)].append(row)
    group_order = ["Irrelevant", "Relevant Non-empirical", "Quantitative", "Qualitative", "Review"]
    rng = random.Random(RANDOM_SEED)
    sampled: list[tuple[str, dict]] = []
    for group in group_order:
        pool = sorted(groups[group], key=lambda r: r["input_index"])
        selection = rng.sample(pool, min(SAMPLE_PER_GROUP, len(pool)))
        sampled.extend((group, row) for row in sorted(selection, key=lambda r: r["input_index"]))

    blind = load_jsonl(BLIND_CHECKPOINT)
    pending = [(group, row) for group, row in sampled if row["record_key"] not in blind]
    print(f"Blind audit sample={len(sampled)} resumed={len(sampled)-len(pending)} pending={len(pending)}", flush=True)
    started = time.monotonic()
    with BLIND_CHECKPOINT.open("a", encoding="utf-8") as handle:
        for number, (group, row) in enumerate(pending, 1):
            screening, metrics = model_call([
                {"role": "system", "content": BLIND_PROMPT},
                {"role": "user", "content": json.dumps(record_text(row), ensure_ascii=False)},
            ])
            item = {
                "audit_version": AUDIT_VERSION,
                "record_key": row["record_key"],
                "input_index": row["input_index"],
                "sample_group": group,
                "blind_screening": screening,
                "model_metrics": metrics,
            }
            append_jsonl(handle, item)
            blind[row["record_key"]] = item
            if number == 1 or number % 5 == 0:
                seconds = (time.monotonic() - started) / number
                print(
                    f"blind_progress={len(sampled)-len(pending)+number}/{len(sampled)} "
                    f"seconds_per_record={seconds:.2f} eta_minutes={(len(pending)-number)*seconds/60:.1f}",
                    flush=True,
                )

    disagreements: list[tuple[str, dict, dict]] = []
    for group, row in sampled:
        audit_item = blind[row["record_key"]]
        if label_tuple(row["screening"]) != label_tuple(audit_item["blind_screening"]):
            disagreements.append((group, row, audit_item))
    print(f"Blind full-label disagreements={len(disagreements)}/{len(sampled)}", flush=True)

    adjudicated = load_jsonl(ADJUDICATION_CHECKPOINT)
    pending_adj = [item for item in disagreements if item[1]["record_key"] not in adjudicated]
    print(f"Adjudication resumed={len(disagreements)-len(pending_adj)} pending={len(pending_adj)}", flush=True)
    started = time.monotonic()
    with ADJUDICATION_CHECKPOINT.open("a", encoding="utf-8") as handle:
        for number, (group, row, audit_item) in enumerate(pending_adj, 1):
            payload = {
                **record_text(row),
                "primary_screening": row["screening"],
                "blind_audit_screening": audit_item["blind_screening"],
            }
            screening, metrics = model_call([
                {"role": "system", "content": ADJUDICATION_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ], think=True)
            item = {
                "audit_version": AUDIT_VERSION,
                "record_key": row["record_key"],
                "input_index": row["input_index"],
                "sample_group": group,
                "adjudicated_screening": screening,
                "model_metrics": metrics,
            }
            append_jsonl(handle, item)
            adjudicated[row["record_key"]] = item
            seconds = (time.monotonic() - started) / number
            print(
                f"adjudication_progress={len(disagreements)-len(pending_adj)+number}/{len(disagreements)} "
                f"seconds_per_record={seconds:.2f}",
                flush=True,
            )

    audit_records = []
    corrected = 0
    for group, row in sampled:
        blind_item = blind[row["record_key"]]
        agreement = label_tuple(row["screening"]) == label_tuple(blind_item["blind_screening"])
        audit_info = {
            "sample_group": group,
            "random_seed": RANDOM_SEED,
            "blind_screening": blind_item["blind_screening"],
            "full_label_agreement": agreement,
        }
        initial = dict(row["screening"])
        if not agreement:
            final = adjudicated[row["record_key"]]["adjudicated_screening"]
            audit_info["adjudicated_screening"] = final
            row["screening_initial"] = initial
            row["screening"] = {
                "is_relevant": final["is_relevant"],
                "evidence_class": final["evidence_class"],
                "empirical_method": final["empirical_method"],
            }
            row["screening_source"] = "Accuracy-audit adjudication"
            if label_tuple(row["screening"]) != label_tuple(initial):
                corrected += 1
        else:
            row["screening_source"] = "Primary screen; blind audit agreement"
        row["accuracy_audit"] = audit_info
        audit_records.append({
            "record_key": row["record_key"],
            "input_index": row["input_index"],
            "sample_group": group,
            "title": row["title"],
            "abstract": row["abstract"],
            "primary_screening": initial,
            "blind_screening": blind_item["blind_screening"],
            "full_label_agreement": agreement,
            "adjudicated_screening": audit_info.get("adjudicated_screening"),
            "final_screening": row["screening"],
        })

    group_stats = {}
    for group in group_order:
        items = [r for r in audit_records if r["sample_group"] == group]
        group_stats[group] = {
            "sampled": len(items),
            "full_label_agreements": sum(r["full_label_agreement"] for r in items),
            "full_label_agreement_rate": (
                sum(r["full_label_agreement"] for r in items) / len(items) if items else None
            ),
        }
    audit_summary = {
        "audit_version": AUDIT_VERSION,
        "model": primary.MODEL,
        "method": "Reproducible stratified random sample; blind one-record rescreen; thinking-mode adjudication of every disagreement",
        "random_seed": RANDOM_SEED,
        "sample_per_group": SAMPLE_PER_GROUP,
        "total_sampled": len(sampled),
        "group_statistics": group_stats,
        "full_label_agreements": sum(r["full_label_agreement"] for r in audit_records),
        "full_label_agreement_rate": sum(r["full_label_agreement"] for r in audit_records) / len(audit_records),
        "disagreements_adjudicated": len(disagreements),
        "sampled_records_corrected_after_adjudication": corrected,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    audit_document = {"summary": audit_summary, "audited_records": audit_records}
    AUDIT_PATH.write_text(json.dumps(audit_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    document["metadata"]["accuracy_audit"] = audit_summary
    document, relevant_document, final_summary = recalculate_documents(document)
    ALL_RESULTS_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    RELEVANT_PATH.write_text(json.dumps(relevant_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(final_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit_summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
