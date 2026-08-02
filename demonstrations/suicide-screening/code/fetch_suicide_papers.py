#!/usr/bin/env python3
"""Export suicide-explicit records from the SWRD and SSWR databases.

The inclusion rule is deliberately reproducible: the title or abstract must
contain a word beginning with the stem ``suicid`` (suicide, suicidal,
suicidality, and related forms). SWRD is restricted to its recommended 1989+
corpus. The raw and title/year-deduplicated SWRD exports are both retained.
"""

from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


API_KEY = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
API_URL = "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/run_sql"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
PAGE_SIZE = 700


def run_sql(query: str, schema: str) -> list[dict]:
    request = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query}).encode("utf-8"),
        method="POST",
        headers={
            "apikey": API_KEY,
            "Authorization": f"Bearer {API_KEY}",
            "Content-Profile": schema,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{schema} query failed ({exc.code}): {detail}") from exc


def fetch_pages(query_template: str, schema: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page = run_sql(query_template.format(limit=PAGE_SIZE, offset=offset), schema)
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", title or "").lower()


def dedupe_swrd(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        key = f"{normalize_title(row.get('title', ''))}|{row.get('year')}"
        groups.setdefault(key, []).append(row)

    unique_rows: list[dict] = []
    for group in groups.values():
        selected = max(
            group,
            key=lambda r: (
                bool(r.get("doi")),
                len(r.get("abstract") or ""),
                len(r.get("authors") or ""),
            ),
        ).copy()
        selected["duplicate_record_ids"] = "; ".join(
            str(r["record_id"]) for r in group if r["record_id"] != selected["record_id"]
        )
        unique_rows.append(selected)
    return sorted(unique_rows, key=lambda r: (r["year"], r["title"].lower(), str(r["record_id"])))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


SWRD_QUERY = r"""
select
  'SWRD' as source_database,
  p.id as record_id,
  p.publication_year as year,
  p.title,
  p.abstract,
  coalesce((
    select string_agg(a.name, '; ' order by pa.position)
    from swrd.paper_authors pa
    join swrd.authors a on a.id = pa.author_id
    where pa.paper_id = p.id
  ), '') as authors,
  j.name as journal_or_venue,
  p.doi,
  p.document_type as record_type,
  p.research_method as method,
  p.is_scientific,
  p.is_empirical,
  (coalesce(p.title, '') ~* '\msuicid') as matched_in_title,
  (coalesce(p.abstract, '') ~* '\msuicid') as matched_in_abstract
from swrd.papers p
left join swrd.journals j on j.id = p.journal_id
where p.publication_year >= 1989
  and (coalesce(p.title, '') || ' ' || coalesce(p.abstract, '')) ~* '\msuicid'
order by p.publication_year, p.title, p.id
limit {limit} offset {offset}
""".strip()


SSWR_QUERY = r"""
select
  'SSWR' as source_database,
  p.id as record_id,
  p.year,
  p.title,
  p.abstract,
  coalesce((
    select string_agg(a.name, '; ' order by pa.author_order)
    from sswr.paper_authors pa
    join sswr.authors a on a.id = pa.author_id
    where pa.paper_id = p.id
  ), '') as authors,
  coalesce((
    select string_agg(a.id::text, '; ' order by pa.author_order)
    from sswr.paper_authors pa
    join sswr.authors a on a.id = pa.author_id
    where pa.paper_id = p.id
  ), '') as author_ids,
  'SSWR annual conference' as journal_or_venue,
  null::text as doi,
  p.format as record_type,
  p.methodology as method,
  null::boolean as is_scientific,
  null::boolean as is_empirical,
  (coalesce(p.title, '') ~* '\msuicid') as matched_in_title,
  (coalesce(p.abstract, '') ~* '\msuicid') as matched_in_abstract
from sswr.papers p
where (coalesce(p.title, '') || ' ' || coalesce(p.abstract, '')) ~* '\msuicid'
order by p.year, p.title, p.id
limit {limit} offset {offset}
""".strip()


BASE_FIELDS = [
    "source_database",
    "record_id",
    "year",
    "title",
    "abstract",
    "authors",
    "author_ids",
    "journal_or_venue",
    "doi",
    "record_type",
    "method",
    "is_scientific",
    "is_empirical",
    "matched_in_title",
    "matched_in_abstract",
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    swrd_raw = fetch_pages(SWRD_QUERY, "swrd")
    sswr = fetch_pages(SSWR_QUERY, "sswr")
    swrd_unique = dedupe_swrd(swrd_raw)

    for row in swrd_raw:
        row.setdefault("author_ids", "")
    for row in swrd_unique:
        row.setdefault("author_ids", "")

    combined = sorted(
        swrd_unique + sswr,
        key=lambda r: (r["year"], r["source_database"], r["title"].lower(), str(r["record_id"])),
    )
    title_specific = [row for row in combined if row["matched_in_title"]]

    write_csv(OUTPUT_DIR / "swrd_suicide_matches_raw.csv", swrd_raw, BASE_FIELDS)
    write_csv(
        OUTPUT_DIR / "swrd_suicide_matches_unique.csv",
        swrd_unique,
        BASE_FIELDS + ["duplicate_record_ids"],
    )
    write_csv(OUTPUT_DIR / "sswr_suicide_matches.csv", sswr, BASE_FIELDS)
    write_csv(OUTPUT_DIR / "all_suicide_papers.csv", combined, BASE_FIELDS + ["duplicate_record_ids"])
    write_json(OUTPUT_DIR / "all_suicide_papers.json", combined)
    write_csv(
        OUTPUT_DIR / "suicide_title_specific_papers.csv",
        title_specific,
        BASE_FIELDS + ["duplicate_record_ids"],
    )
    write_json(OUTPUT_DIR / "suicide_title_specific_papers.json", title_specific)

    summary = {
        "inclusion_rule": (
            "Title or abstract contains a word beginning with 'suicid' "
            "(case-insensitive); SWRD restricted to publication_year >= 1989."
        ),
        "swrd_raw_records": len(swrd_raw),
        "swrd_unique_title_year_papers": len(swrd_unique),
        "swrd_duplicate_records_removed": len(swrd_raw) - len(swrd_unique),
        "sswr_presentations": len(sswr),
        "combined_unique_records": len(combined),
        "title_specific_records": len(title_specific),
        "abstract_only_expansion_records": len(combined) - len(title_specific),
        "title_matches": {
            "SWRD_raw": sum(bool(r["matched_in_title"]) for r in swrd_raw),
            "SWRD_unique": sum(bool(r["matched_in_title"]) for r in swrd_unique),
            "SSWR": sum(bool(r["matched_in_title"]) for r in sswr),
        },
        "year_ranges": {
            "SWRD": [min(r["year"] for r in swrd_unique), max(r["year"] for r in swrd_unique)],
            "SSWR": [min(r["year"] for r in sswr), max(r["year"] for r in sswr)],
        },
        "top_swrd_journals": Counter(r["journal_or_venue"] for r in swrd_unique).most_common(15),
        "swrd_methods": Counter(r["method"] or "Unclassified" for r in swrd_unique).most_common(),
        "sswr_methods": Counter(r["method"] or "Unclassified" for r in sswr).most_common(),
        "swrd_scientific_records": sum(bool(r["is_scientific"]) for r in swrd_unique),
        "swrd_records_with_doi": sum(bool(r["doi"]) for r in swrd_unique),
        "records_by_year": {
            "SWRD": dict(sorted(Counter(str(r["year"]) for r in swrd_unique).items())),
            "SSWR": dict(sorted(Counter(str(r["year"]) for r in sswr).items())),
        },
    }
    write_json(OUTPUT_DIR / "summary.json", summary)
    readme = f"""# Suicide-topic records from SWRD and SSWR

Generated from the Social Work Meta-Data Project POST API.

## Recommended files

- `suicide_title_specific_papers.csv`: {len(title_specific):,} high-precision records whose title contains a word beginning with `suicid`.
- `all_suicide_papers.csv`: {len(combined):,} unique records whose title or abstract contains a word beginning with `suicid`.
- `swrd_suicide_matches_raw.csv`: all {len(swrd_raw):,} matching SWRD database rows before title/year deduplication.
- `swrd_suicide_matches_unique.csv`: {len(swrd_unique):,} deduplicated SWRD papers.
- `sswr_suicide_matches.csv`: all {len(sswr):,} matching SSWR presentations.
- JSON equivalents and `summary.json` are included for programmatic use.

## Scope

The reproducible inclusion rule is a case-insensitive `suicid*` word-start match in the title or abstract. This captures suicide, suicidal, suicidality, and related forms. It intentionally does not automatically treat every paper about nonsuicidal self-injury or self-harm as a suicide paper. The title-specific file is the higher-precision set; the title-or-abstract file is the higher-recall set.

SWRD is restricted to the recommended 1989+ corpus and deduplicated by normalized title plus publication year. SSWR covers 2005–2026. The databases provide bibliographic metadata and abstracts, not guaranteed full-text PDFs. SWRD author names are as published and are not identity-disambiguated; SSWR author IDs are canonical.

The most recent SWRD years, 2024–2025, are incomplete because publisher indexing lags, so they should not be used for trend conclusions.
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
