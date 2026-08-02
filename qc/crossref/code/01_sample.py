#!/usr/bin/env python3
"""
Step 1 — draw the stratified pilot sample from SWRD (1989+).

    python3 01_sample.py [n_per_stratum]

Writes ../data/pilot_sample.json

The sample is deliberately adversarial, not representative. It over-samples
the states most likely to break the matching rules — malformed identifiers,
missing DOIs, and journals where Crossref coverage is thin — because the point
of a pilot is to find the false-positive rate before committing to a full run.
A representative sample would be mostly easy records and would tell us little.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swrdqc as Q

SEED = 20260802
OUT = os.path.join(Q.DATA, "pilot_sample.json")

COLS = """
  p.id, p.title, p.abstract is not null as has_abstract, p.publication_year as year,
  p.doi, p.document_type, p.is_scientific, p.journal_id,
  j.name as journal_name, j.issn_print, j.issn_online,
  coalesce((select string_agg(a.name, '; ' order by pa.position)
            from swrd.paper_authors pa join swrd.authors a on a.id = pa.author_id
            where pa.paper_id = p.id), '') as authors
"""

# Thin-coverage journals: regional, non-English, or small-publisher titles where
# Crossref registration is patchy. If the rules survive here they will survive
# on Taylor & Francis and Sage.
THIN = (
    "'Social Work-Maatskaplike Werk','Indian Journal of Social Work',"
    "'The Journal of Sociology & Social Welfare','Journal of Social Work Practice'"
)

STRATA = {
    # syntactically valid DOI — the bulk of the corpus, the easy case
    "valid_doi": f"p.doi ~ '^10\\.[0-9]{{4,9}}/'",
    # the two malformed families, sampled separately: one is deterministically
    # convertible, the other is not
    "malformed_oai": "p.doi like 'oai:%'",
    "malformed_dc": "p.doi like 'dc/%'",
    # no identifier at all — recovery has to go through bibliographic search
    "null_doi": "p.doi is null",
    # adversarial: thin Crossref coverage
    "thin_coverage": f"j.name in ({THIN})",
}


def draw(where: str, n: int):
    return Q.rows(f"""
      select {COLS}
      from swrd.papers p
      left join swrd.journals j on j.id = p.journal_id
      where p.publication_year >= 1989 and ({where})
      order by md5(p.id::text || '{SEED}')
      limit {n}
    """)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    os.makedirs(Q.DATA, exist_ok=True)

    sample, seen = [], set()
    for name, where in STRATA.items():
        got = draw(where, n)
        fresh = 0
        for r in got:
            if r["id"] in seen:      # strata overlap (a thin-coverage record
                continue             # may also be a malformed-DOI record)
            seen.add(r["id"])
            r["stratum"] = name
            sample.append(r)
            fresh += 1
        print(f"  {name:<16} drew {len(got):>4}, {fresh:>4} new")

    with open(OUT, "w") as f:
        json.dump(sample, f, indent=1, ensure_ascii=False)
    print(f"\n{len(sample)} unique records -> {OUT}")


if __name__ == "__main__":
    main()
