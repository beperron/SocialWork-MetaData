#!/usr/bin/env python3
"""
Step 1 — pull every SWRD row whose `doi` is not a DOI.

    python3 qc/doi/code/01_extract.py

Writes ../data/malformed.json

The `doi` column holds 3,556 values in the 1989+ corpus that are not DOIs. They
are not scattered: each pattern comes from exactly one ingest, and the whole
problem sits in nine journals.

    oai:scholarworks.wmich.edu:jssw-NNNN   2,002   data_source = Digital Commons
    dc/<hash>                              1,554   data_source = DOAJ

This script only reads. It asserts the expected shape up front, because if the
counts have moved the database has changed underneath the plan and the recovery
rules need re-checking before anything is proposed.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402  (path is set immediately above)

OUT = os.path.join(ROOT, "data", "malformed.json")

# Measured 2026-08-02. A mismatch is not necessarily an error, but it means the
# corpus moved and the recovery rules below were validated against a different
# population — so stop and re-check rather than silently proposing corrections.
EXPECTED = {"total": 3556, "oai": 2002, "dc": 1554, "journals": 9}

QUERY = r"""
select
  p.id, p.title, p.publication_year as year, p.doi, p.data_source,
  p.document_type, p.is_scientific, p.abstract is not null as has_abstract,
  p.journal_id, j.name as journal_name, j.issn_print, j.issn_online,
  coalesce((
    select string_agg(a.name, '; ' order by pa.position)
    from swrd.paper_authors pa join swrd.authors a on a.id = pa.author_id
    where pa.paper_id = p.id), '') as authors,
  case when p.doi like 'oai:%' then 'oai' else 'dc' end as pattern
from swrd.papers p
left join swrd.journals j on j.id = p.journal_id
where p.publication_year >= 1989
  and p.doi is not null
  and p.doi !~ '^10\.[0-9]{4,9}/'
order by p.id
"""


def main():
    rows = Q.rows(QUERY)

    got = {
        "total": len(rows),
        "oai": sum(1 for r in rows if r["pattern"] == "oai"),
        "dc": sum(1 for r in rows if r["pattern"] == "dc"),
        "journals": len({r["journal_id"] for r in rows}),
    }
    print("shape:")
    for k, v in got.items():
        flag = "ok" if v == EXPECTED[k] else f"EXPECTED {EXPECTED[k]}"
        print(f"  {k:<9} {v:>6}   {flag}")
    if got != EXPECTED:
        sys.exit("\nCorpus shape differs from the planned population — stopping. "
                 "Re-check the recovery rules before proposing any correction.")

    # Journal breakdown: the dc/ recovery leans on journal agreement, and four of
    # these journals have an ISSN while four do not, so the split matters.
    print("\njournals holding malformed DOIs:")
    by_journal = {}
    for r in rows:
        k = (r["journal_name"], r["issn_print"] or r["issn_online"])
        by_journal.setdefault(k, {"oai": 0, "dc": 0})[r["pattern"]] += 1
    for (name, issn), c in sorted(by_journal.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  oai={c['oai']:>5}  dc={c['dc']:>5}  issn={issn or '—':<12} {name}")

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    print(f"\n{len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
