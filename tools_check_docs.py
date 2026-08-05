#!/usr/bin/env python3
"""
Verify every number llms.txt asserts against the live database.

    python3 tools_check_docs.py        # exit 0 = every claim verified

Release procedure step 5. Exists because prose rots exactly like data and
nothing was checking it: the DOI-defect paragraph described 3,556 malformed
rows for three releases after v1.1 repaired them to 926, and the
paper_authors count survived two releases stale. llms.txt is the file AI
agents treat as ground truth, so a stale number there propagates into other
people's analyses with this project's authority behind it.

Each claim is ENUMERATED, not extracted by pattern — the house style
(RENAMES, SURNAME_FIX): explicit and hand-checked, because a regex loose
enough to find every number would also "verify" numbers that mean something
else. Two checks per claim:

  1. the exact claim string still appears in llms.txt — if it was reworded,
     this checker must be updated in the same commit, which is the point;
  2. the number in it equals what the live database says right now.

Also verifies llms.html embeds the current llms.txt verbatim, so the mirror
cannot drift the way it did before tools_make_llms_html.py was rerun.

Prose claims with no mechanical counterpart ("names are as published", "the
error runs one way") remain human-verified; this covers only what a query
can settle.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "qc", "crossref", "code"))
import swrdqc as Q  # noqa: E402

# (claim snippet that must appear verbatim in llms.txt, SQL whose single value
#  must equal the number embedded in the snippet, that expected number)
CLAIMS = [
    ("87,329 systematically compiled records from 1989 onward",
     "select count(*) from swrd.papers where publication_year >= 1989", 87329),
    ("62,602 research articles with abstracts",
     "select count(*) from swrd.papers where publication_year >= 1989 "
     "and is_scientific and abstract is not null and abstract <> ''", 62602),
    ("physically holds 110,618 rows",
     "select count(*) from swrd.papers", 110618),
    ("a pre-1989 Supplement (23,288 records, 1920–1988)",
     "select count(*) from swrd.papers where publication_year < 1989", 23288),
    ("164,549 `swrd.authors` rows",
     "select count(*) from swrd.authors", 164549),
    ("234,010 `swrd.paper_authors`",
     "select count(*) from swrd.paper_authors", 234010),
    ("204,493 of them on 1989+ papers",
     "select count(*) from swrd.paper_authors pa join swrd.papers p "
     "on p.id = pa.paper_id where p.publication_year >= 1989", 204493),
    ("DERIVED fuller name for 26,313",
     "select count(*) from swrd.author_name_enrichment", 26313),
    ("926 rows in the 1989+ corpus",
     "select count(*) from swrd.papers where publication_year >= 1989 "
     "and doi is not null and doi <> '' "
     "and not doi ~ '^10\\.[0-9]{4,9}/'", 926),
    ("69,911 populated values",
     "select count(*) from swrd.papers where publication_year >= 1989 "
     "and doi is not null and doi <> ''", 69911),
    ("62,628\n`is_scientific` records",
     "select count(*) from swrd.papers where publication_year >= 1989 "
     "and is_scientific", 62628),
    ("All 23,793 presentations",
     "select count(*) from sswr.papers", 23793),
    ("21,209 canonical identities",
     "select count(*) from sswr.authors", 21209),
    # schema-table rows
    ("| `swrd.journals` | 91 |",
     "select count(*) from swrd.journals", 91),
    ("| `swrd.organizations` | 34,967 |",
     "select count(*) from swrd.organizations", 34967),
    ("| `swrd.author_affiliations` | 113,646 |",
     "select count(*) from swrd.author_affiliations", 113646),
    ("| `swrd.author_name_enrichment` | 26,313 |",
     "select count(*) from swrd.author_name_enrichment", 26313),
]


def main():
    txt = open(os.path.join(HERE, "llms.txt"), encoding="utf-8").read()
    html = open(os.path.join(HERE, "llms.html"), encoding="utf-8").read()
    failures = 0

    for snippet, sql, expected in CLAIMS:
        label = " ".join(snippet.split())[:52]
        if snippet not in txt:
            print(f"  FAIL  claim text missing/reworded : {label!r}")
            print("        (update CLAIMS in this checker in the same commit)")
            failures += 1
            continue
        try:
            live = list(Q.rows(sql)[0].values())[0]
        except Exception as exc:
            print(f"  FAIL  query error for {label!r}: {exc}")
            failures += 1
            continue
        if live != expected:
            print(f"  FAIL  {label!r}: llms.txt says {expected:,}, live is {live:,}")
            failures += 1
        else:
            print(f"  ok    {label:<52} = {live:,}")

    # the mirror must embed the current text, HTML-escaped exactly the way
    # tools_make_llms_html.py writes it
    import html as html_mod
    if html_mod.escape(txt) not in html:
        print("  FAIL  llms.html does not embed the current llms.txt — "
              "run python3 tools_make_llms_html.py")
        failures += 1
    else:
        print("  ok    llms.html embeds the current llms.txt")

    print(f"\n{len(CLAIMS) + 1 - failures}/{len(CLAIMS) + 1} checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
