#!/usr/bin/env python3
"""Screen suicide-topic candidates one-by-one with local Ollama Qwen3.6-27B.

Every source record is sent in its own API request. Results are appended to a
JSONL checkpoint immediately and can be resumed without repeating completed
records. Final JSON artifacts include both the full audit trail and a filtered
set containing only records judged relevant.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "all_suicide_papers.json"
OUTPUT_DIR = ROOT / "data"
CHECKPOINT_PATH = OUTPUT_DIR / "screening_checkpoint.jsonl"
ALL_RESULTS_PATH = OUTPUT_DIR / "suicide_abstract_screening_results.json"
RELEVANT_PATH = OUTPUT_DIR / "suicide_relevant_articles.json"
SUMMARY_PATH = OUTPUT_DIR / "screening_summary.json"

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen3.6:27b"
PROMPT_VERSION = "suicide-screen-v1.4-one-record-labels"


SYSTEM_PROMPT = """You are an expert evidence-reviewer screening one bibliographic record for a suicide-focused evidence corpus. Analyze the title and abstract carefully, then return the required JSON object.

RELEVANCE
Set is_relevant=true only when suicide, suicidal ideation, suicide attempt, suicide death, suicidality, suicide risk/protective factors, suicide prevention/postvention, suicide bereavement/survivors, attitudes toward suicide, or suicide-specific assessment is a central substantive focus, primary outcome, exposure, population, intervention, or a distinctly analyzed and reported component.

Include research where suicide is one of multiple outcomes only when the abstract indicates it is actually analyzed or reported as a distinct outcome. Include suicide-loss, suicide-bereavement, clinician/gatekeeper knowledge or behavior about suicide, and suicide-specific policy or practice when central.

Set is_relevant=false when suicide is merely background context, an illustrative example, one unanalysed item in a broad list, or a passing sentence unrelated to the main aim/results. Nonsuicidal self-injury, self-harm, euthanasia, or general mental health alone is not relevant unless the abstract substantively analyzes suicide or suicidality.

EVIDENCE CLASS FOR RELEVANT RECORDS
- Empirical: analyzes primary or secondary observations/data, including surveys, experiments, trials, administrative or clinical data, statistical models, qualitative interviews/focus groups/observations/textual data, empirical case studies, or program evaluations. Systematic reviews, meta-analyses, and scoping reviews also count as Empirical for this task.
- Non-empirical: narrative/traditional literature reviews, conceptual or theoretical articles, commentaries, editorials, book reviews, introductions, practice overviews, policy arguments without analyzed data, illustrative clinical vignettes, and research/review protocols without results. A review is Non-empirical unless the title or abstract explicitly identifies systematic, meta-analytic, or scoping methods, or clearly describes a reproducible systematic search and selection process. Narrative reviews are always Non-empirical.

EMPIRICAL METHOD
For Empirical records choose exactly one:
- Quantitative: numerical/statistical analysis, experiments, trials, surveys, administrative data, psychometrics, or mixed-methods work with a central quantitative component.
- Qualitative: predominantly qualitative interviews, focus groups, ethnography, observations, qualitative case analysis, or qualitative textual/thematic analysis without a central quantitative component.
- Review: systematic review, meta-analysis, scoping review, or clearly methodologically systematic evidence synthesis.
For Non-empirical or irrelevant records, empirical_method must be "Not applicable".
This is a forced-choice taxonomy: if you select Empirical, you must select the single best-supported empirical method even when details are limited. If the supplied text provides no defensible evidence of an empirical design, select Non-empirical instead of returning an unknown empirical method.
For every relevant record, evidence_class is also a forced choice between Empirical and Non-empirical. Never use "Not applicable" for a relevant record. For a title-only relevant record whose wording provides no defensible indication of design, use the conservative fallback Non-empirical.

DECISION RULES
Use only the supplied title and abstract; do not infer methods merely from journal, year, or authors. If the abstract is unavailable, make the best binary decision from the title. For a title-only relevant record whose wording provides no defensible indication of design, use the conservative fallback Non-empirical.

LOGICAL OUTPUT
- If is_relevant=false: evidence_class="Not applicable" and empirical_method="Not applicable".
- If is_relevant=true and evidence_class="Non-empirical": empirical_method="Not applicable".
- If is_relevant=true and evidence_class="Empirical": empirical_method is Quantitative, Qualitative, or Review.

OUTPUT CODES
Return only the three compact JSON fields below; do not add prose.
- rel: boolean relevance decision.
- ec: E=Empirical, N=Non-empirical, NA=Not applicable.
- method: QT=Quantitative, QL=Qualitative, R=Review, NA=Not applicable.
"""


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "rel": {"type": "boolean"},
        "ec": {"type": "string", "enum": ["E", "N", "NA"]},
        "method": {"type": "string", "enum": ["QT", "QL", "R", "NA"]},
    },
    "required": ["rel", "ec", "method"],
}


EVIDENCE_MAP = {"E": "Empirical", "N": "Non-empirical", "NA": "Not applicable"}
METHOD_MAP = {"QT": "Quantitative", "QL": "Qualitative", "R": "Review", "NA": "Not applicable"}
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Process at most this many total input records")
    parser.add_argument("--start", type=int, default=0, help="Start at this zero-based input index")
    parser.add_argument("--no-finalize", action="store_true", help="Do not write final aggregate JSON files")
    return parser.parse_args()


def load_checkpoint() -> dict[int, dict]:
    completed: dict[int, dict] = {}
    if not CHECKPOINT_PATH.exists():
        return completed
    with CHECKPOINT_PATH.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid checkpoint JSON on line {line_number}") from exc
            if item.get("prompt_version") != PROMPT_VERSION:
                raise RuntimeError(
                    "Checkpoint was produced by a different prompt version; move it aside before restarting"
                )
            completed[int(item["input_index"])] = item
    return completed


def valid_screening(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    required = {"rel", "ec", "method"}
    if not required.issubset(value):
        return False
    relevant = value["rel"]
    evidence = value["ec"]
    method = value["method"]
    if not isinstance(relevant, bool):
        return False
    if not relevant:
        return evidence == "NA" and method == "NA"
    if evidence == "N":
        return method == "NA"
    if evidence == "E":
        return method in {"QT", "QL", "R"}
    return False


def expand_screening(value: dict) -> dict:
    return {
        "is_relevant": value["rel"],
        "evidence_class": EVIDENCE_MAP[value["ec"]],
        "empirical_method": METHOD_MAP[value["method"]],
    }


def request_screening(record: dict, input_index: int) -> tuple[dict, dict]:
    abstract = (record.get("abstract") or "").strip()
    user_content = {
        "record_number": input_index,
        "title": record.get("title") or "",
        "abstract": abstract if abstract else "[NO ABSTRACT AVAILABLE — SCREEN FROM TITLE ONLY]",
    }
    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "format": OUTPUT_SCHEMA,
        "options": {
            "temperature": 0,
            "seed": 42,
            "num_ctx": 4096,
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
        ],
    }

    last_error: Exception | None = None
    correction = ""
    for attempt in range(1, 5):
        if correction:
            payload["messages"] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
                {"role": "user", "content": correction},
            ]
        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                api_result = json.load(response)
            raw_screening = json.loads(api_result["message"]["content"])
            if not valid_screening(raw_screening):
                if isinstance(raw_screening, dict) and raw_screening.get("rel") is True and raw_screening.get(
                    "ec"
                ) == "NA":
                    correction = (
                        "Your previous output marked the record relevant but did not make the mandatory "
                        "Empirical versus Non-empirical choice. Never use Not applicable for a relevant record. "
                        "Choose Empirical only if the supplied title/abstract supports an empirical design; "
                        "otherwise use the conservative fallback Non-empirical. Return corrected JSON only."
                    )
                elif (
                    isinstance(raw_screening, dict)
                    and raw_screening.get("ec") == "E"
                    and raw_screening.get("method") == "NA"
                ):
                    correction = (
                        "Your previous output selected Empirical but omitted its required method. This is a "
                        "forced choice: select Quantitative, Qualitative, or Review using the best available "
                        "evidence. If no empirical design is defensible from "
                        "the supplied text, select Non-empirical and Not applicable instead. Return corrected JSON only."
                    )
                else:
                    correction = (
                        "Your previous JSON violated the logical output rules. Re-evaluate the same record and "
                        "return a logically consistent JSON object only."
                    )
                last_error = ValueError(f"Logically invalid model output: {raw_screening}")
                continue
            screening = expand_screening(raw_screening)
            metrics = {
                "attempt": attempt,
                "total_duration_ns": api_result.get("total_duration"),
                "prompt_eval_count": api_result.get("prompt_eval_count"),
                "eval_count": api_result.get("eval_count"),
            }
            return screening, metrics
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
            last_error = exc
            if attempt < 4:
                time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"Screening failed after four attempts for input index {input_index}") from last_error


def checkpoint_item(index: int, record: dict, screening: dict, metrics: dict) -> dict:
    return {
        "input_index": index,
        "record_key": f"{record.get('source_database')}:{record.get('record_id')}",
        "source_database": record.get("source_database"),
        "record_id": record.get("record_id"),
        "year": record.get("year"),
        "title": record.get("title"),
        "abstract": record.get("abstract"),
        "authors": record.get("authors"),
        "author_ids": record.get("author_ids"),
        "journal_or_venue": record.get("journal_or_venue"),
        "doi": record.get("doi"),
        "record_type": record.get("record_type"),
        "database_method": record.get("method"),
        "database_is_scientific": record.get("is_scientific"),
        "database_is_empirical": record.get("is_empirical"),
        "screening_basis": "title_and_abstract" if (record.get("abstract") or "").strip() else "title_only",
        "screening": screening,
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "model_metrics": metrics,
        "screened_at": datetime.now(timezone.utc).isoformat(),
    }


def write_final(results: list[dict], input_count: int) -> None:
    evidence_counts = Counter(
        row["screening"]["evidence_class"]
        for row in results
        if row["screening"]["is_relevant"]
    )
    method_counts = Counter(
        row["screening"]["empirical_method"]
        for row in results
        if row["screening"]["evidence_class"] == "Empirical"
    )
    relevant = [row for row in results if row["screening"]["is_relevant"]]
    summary = {
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "screening_mode": "Sequential: exactly one bibliographic record per Ollama request",
        "input_file": str(INPUT_PATH),
        "input_records": input_count,
        "screened_records": len(results),
        "relevant_records": len(relevant),
        "irrelevant_records": len(results) - len(relevant),
        "title_only_records": sum(row["screening_basis"] == "title_only" for row in results),
        "evidence_class_counts_among_relevant": dict(evidence_counts),
        "empirical_method_counts": dict(method_counts),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    taxonomy = {
        "relevance": "Suicide must be a central focus or distinctly analyzed component, not an incidental mention.",
        "evidence_class": ["Empirical", "Non-empirical"],
        "empirical_methods": ["Qualitative", "Quantitative", "Review"],
        "review_rule": "Review is limited to systematic reviews, meta-analyses, scoping reviews, or explicitly systematic evidence syntheses; narrative reviews are Non-empirical.",
    }
    all_document = {"metadata": summary, "taxonomy": taxonomy, "screening_results": results}
    relevant_document = {"metadata": summary, "taxonomy": taxonomy, "relevant_articles": relevant}
    ALL_RESULTS_PATH.write_text(
        json.dumps(all_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    RELEVANT_PATH.write_text(
        json.dumps(relevant_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    records = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    completed = load_checkpoint()
    stop = min(len(records), args.limit) if args.limit is not None else len(records)
    indices = list(range(max(0, args.start), stop))
    pending = [index for index in indices if index not in completed]
    started = time.monotonic()
    processed_now = 0

    print(
        f"Starting sequential Ollama screening: model={MODEL} input={len(records)} "
        f"target={len(indices)} resumed={len(indices) - len(pending)} pending={len(pending)}",
        flush=True,
    )
    with CHECKPOINT_PATH.open("a", encoding="utf-8") as checkpoint:
        for index in pending:
            record = records[index]
            screening, metrics = request_screening(record, index)
            item = checkpoint_item(index, record, screening, metrics)
            checkpoint.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
            checkpoint.flush()
            os.fsync(checkpoint.fileno())
            completed[index] = item
            processed_now += 1
            if processed_now == 1 or processed_now % 5 == 0:
                elapsed = time.monotonic() - started
                rate = elapsed / processed_now
                remaining = len(pending) - processed_now
                relevant_so_far = sum(
                    bool(completed[i]["screening"]["is_relevant"])
                    for i in indices
                    if i in completed
                )
                print(
                    f"progress={len(indices) - len(pending) + processed_now}/{len(indices)} "
                    f"new={processed_now} relevant={relevant_so_far} "
                    f"seconds_per_record={rate:.2f} eta_minutes={remaining * rate / 60:.1f}",
                    flush=True,
                )

    selected_results = [completed[i] for i in indices if i in completed]
    if not args.no_finalize:
        write_final(selected_results, len(indices))
        print(f"Wrote {ALL_RESULTS_PATH}", flush=True)
        print(f"Wrote {RELEVANT_PATH}", flush=True)


if __name__ == "__main__":
    main()
