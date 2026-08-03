#!/usr/bin/env python3
"""
Step 5 — verify the whole DOI column against Crossref.

    python3 qc/doi/code/05_verify_column.py [--limit N]

Reads  the live database (all 1989+ rows whose doi is already valid syntax)
       ../data/recovery.json  (so repaired rows are checked on their new value)
Writes ../data/column_verification.json
       ../data/column_summary.json

Stage 1 fixed the values that were obviously not DOIs. This asks the next
question of the ones that look fine: does the DOI actually point at this article?

For each record: fetch the DOI, then compare title, journal, and year.

  title    similarity against what we hold
  journal  ISSN where both sides have one, journal name otherwise
  year     REPORTED ONLY, NEVER PROPOSED AS A CORRECTION

The year rule is a scar. In the earlier pilot every single year disagreement was
a false positive: publishers who bulk-register a back catalogue give Crossref the
registration year, so a 2006 article reads as 2014 with a perfect title match.
Crossref is wrong there and SWRD is right, so year disagreements are counted and
displayed but never turned into corrections.

This stage is diagnostic. It produces a queue to look at, not a patch set.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

REC = os.path.join(ROOT, "data", "recovery.json")
OUT = os.path.join(ROOT, "data", "column_verification.json")
SUM = os.path.join(ROOT, "data", "column_summary.json")
CACHE = os.path.join(ROOT, "cache")

CONFIRM, REVIEW = 0.90, 0.75

QUERY = r"""
select p.id, p.title, p.publication_year as year, p.doi, p.data_source,
       p.document_type, p.is_scientific,
       j.name as journal_name, j.issn_print, j.issn_online,
       coalesce((
         select string_agg(a.name, '; ' order by pa.position)
         from swrd.paper_authors pa join swrd.authors a on a.id = pa.author_id
         where pa.paper_id = p.id), '') as authors
from swrd.papers p
left join swrd.journals j on j.id = p.journal_id
where p.publication_year >= 1989
  and p.doi ~ '^10\.[0-9]{4,9}/'
order by p.id
limit {limit} offset {offset}
"""


def fetch_population():
    """Page through the already-valid DOIs (the API caps a call at 1,000 rows)."""
    out, offset, page = [], 0, 900
    while True:
        got = Q.rows(QUERY.replace("{limit}", str(page)).replace("{offset}", str(offset)))
        out.extend(got)
        print(f"  pulled {len(out):,}", flush=True)
        if len(got) < page:
            return out
        offset += page


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    Q.CACHE = CACHE
    os.makedirs(CACHE, exist_ok=True)

    print("population:")
    records = fetch_population()

    # Rows repaired in stage 1 are verified on the DOI they would be given, so
    # this stage covers the column as it will look after the patch is applied.
    with open(REC) as f:
        repaired = {r["id"]: r for r in json.load(f)
                    if r["verdict"] == "recovered" and r.get("proposed_doi")}
    for r in repaired.values():
        records.append({**{k: r.get(k) for k in
                           ("id", "title", "year", "data_source", "document_type",
                            "is_scientific", "journal_name", "issn_print",
                            "issn_online", "authors")},
                        "doi": r["proposed_doi"], "repaired_in_stage_1": True})
    print(f"  + {len(repaired):,} repaired rows = {len(records):,} total")

    if limit:
        records = records[:limit]
        print(f"(limited to {limit})")

    cache = Q.cache_load("column_lookup")
    wanted = sorted({r["doi"].strip().lower() for r in records})
    missing = [d for d in wanted if d not in cache]
    print(f"\nlookups: {len(wanted):,} distinct, {len(missing):,} to fetch")
    for i in range(0, len(missing), 400):
        got = Q.crossref_by_dois(missing[i:i + 400])
        for k in missing[i:i + 400]:
            cache[k] = got.get(k)
        done = min(i + 400, len(missing))
        print(f"  {done:,}/{len(missing):,} ({100 * done / len(missing):.0f}%)", flush=True)
        if done % 4000 == 0:
            Q.cache_save("column_lookup", cache)   # checkpoint a long run
    Q.cache_save("column_lookup", cache)

    findings = []
    for rec in records:
        item = cache.get(rec["doi"].strip().lower())
        base = {"id": rec["id"], "doi": rec["doi"], "year": rec["year"],
                "journal_name": rec["journal_name"],
                "data_source": rec.get("data_source"),
                "title": (rec["title"] or "")[:200],
                "repaired_in_stage_1": rec.get("repaired_in_stage_1", False)}
        if not item:
            findings.append({**base, "verdict": "not_in_crossref"})
            continue

        sim = Q.title_sim(rec["title"] or "", Q.cr_title(item))
        jv, jb = Q.journal_match([rec.get("issn_print"), rec.get("issn_online")],
                                 Q.cr_issns(item), rec.get("journal_name"),
                                 (item.get("container-title") or [None])[0])
        yrs = Q.cr_years(item)
        y = rec.get("year")
        year_v = ("unknown" if not yrs or y is None else
                  "match" if y in yrs else
                  "match_offset_1" if any(abs(y - c) <= 1 for c in yrs) else "mismatch")

        row = {**base, "title_similarity": round(sim, 3),
               "journal_verdict": jv, "journal_basis": jb,
               "year_verdict": year_v, "crossref_years": sorted(yrs),
               "crossref_title": Q.cr_title(item)[:200],
               "crossref_journal": (item.get("container-title") or [None])[0],
               "crossref_type": item.get("type"),
               "author_overlap": round(
                   Q.jaccard(Q.swrd_surnames(rec.get("authors")),
                             Q.cr_surnames(item)), 3)}

        if sim < REVIEW:
            row["verdict"] = "title_mismatch"
        elif jv == "mismatch":
            row["verdict"] = "journal_mismatch"
        elif sim < CONFIRM:
            row["verdict"] = "title_weak"
        else:
            row["verdict"] = "confirmed"
        findings.append(row)

    with open(OUT, "w") as f:
        json.dump(findings, f, ensure_ascii=False, separators=(",", ":"))

    verdicts = Counter(r["verdict"] for r in findings)
    summary = {
        "records_checked": len(findings),
        "verdicts": dict(verdicts),
        "confirmed_rate": round(verdicts["confirmed"] / len(findings), 4),
        "journal_basis": dict(Counter(r.get("journal_basis") for r in findings
                                      if r.get("journal_basis"))),
        # Counted for visibility, never proposed. See the module docstring.
        "year_verdicts_informational": dict(Counter(r.get("year_verdict")
                                                    for r in findings if r.get("year_verdict"))),
        "by_journal_mismatch": dict(Counter(
            r["journal_name"] for r in findings if r["verdict"] == "journal_mismatch").most_common(15)),
        "not_in_crossref_by_journal": dict(Counter(
            r["journal_name"] for r in findings if r["verdict"] == "not_in_crossref").most_common(15)),
    }
    with open(SUM, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\nverdicts:")
    for v, n in verdicts.most_common():
        print(f"  {v:<20} {n:>7,}  {100 * n / len(findings):5.1f}%")
    print(f"\n-> {OUT}\n-> {SUM}")


if __name__ == "__main__":
    main()
