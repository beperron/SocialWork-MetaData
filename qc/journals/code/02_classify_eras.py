#!/usr/bin/env python3
"""
Stage 2 — read each journal's ISSN history and say what it means.

    python3 qc/journals/code/02_classify_eras.py

Reads  ../cache/issn_lookup.jsonl.gz  (written by 01_backfill_issn.py)
Writes ../data/journal_eras.json      every journal's ISSN groups with year spans
       ../data/rename_map.csv         former title -> current journal row
       ../data/contamination.csv      journals holding another journal's articles

A journal whose articles carry more than one ISSN is telling you something, and
which thing depends on how the ISSNs sit in time:

  same journal      The two sets share an ISSN. One deposit listed print+online
                    and another listed only online. Nothing is wrong.
                    Social Work-Maatskaplike Werk does this.

  rename            The sets are disjoint and their year spans are sequential.
                    The journal changed title or publisher and took a new ISSN.
                    Families in Society runs 0887-400X (1922-45) -> 0037-7678
                    as Social Casework (1950-89) -> 1044-3894 (1990-).

  contamination     The sets are disjoint and their year spans interleave. One
                    journal's row is holding another journal's articles, which
                    is issue #2. Social Work carries 27 sampled articles with
                    Affilia's 0886-1099 spread across 1990-2017, alongside its
                    own 0037-8046 across 1959-2023.

That last distinction is the useful one: it finds misattribution from the
identifier rather than from journal-name string comparison, which is what made
the earlier estimate unreliable.

Read-only. Produces evidence for the next stage; changes nothing.
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

CACHE = os.path.join(ROOT, "cache")
OUT_ERAS = os.path.join(ROOT, "data", "journal_eras.json")
OUT_RENAME = os.path.join(ROOT, "data", "rename_map.csv")
OUT_CONTAM = os.path.join(ROOT, "data", "contamination.csv")

MIN_GROUP = 3          # an ISSN set needs this many articles to count as an era
MAX_ERA_OVERLAP = 2    # years two eras may overlap and still read as sequential

SAMPLE_SQL = r"""
select journal_id, doi, publication_year as year from (
  select p.journal_id, p.doi, p.publication_year,
         row_number() over (partition by p.journal_id
                            order by (p.id * 2654435761) % 1000003) as rn
  from swrd.papers p
  where p.doi ~ '^10\.[0-9]{4,9}/' and p.journal_id is not null
) t where rn <= 120
"""


def classify(a, b):
    """Two ISSN groups from one journal: same, rename, or contamination.

    A rename is SEQUENTIAL: the second identifier begins at or after the first
    one ends. Measuring raw overlap instead is wrong, because a short
    contaminating era sitting inside a long one produces a small overlap and
    reads as a rename -- Social Work in Health Care spans 1975-2025 and carries
    a handful of Journal of Comparative Social Welfare articles from 2010-2012,
    which is three years of overlap and obviously not a title change.

    So containment is the test: if one era sits inside the other, it is
    contamination whatever the arithmetic says.
    """
    if set(a["issn"]) & set(b["issn"]):
        return "same_journal_variant_deposit"
    lo, hi = sorted([a, b], key=lambda g: g["first"])
    if hi["last"] <= lo["last"]:
        return "contamination"          # nested entirely within the other era
    return "rename" if hi["first"] >= lo["last"] - MAX_ERA_OVERLAP else "contamination"


def main():
    Q.CACHE = CACHE
    cache = Q.cache_load("issn_lookup")
    if not cache:
        sys.exit("no cached Crossref records — run 01_backfill_issn.py first")

    journals = {j["id"]: j for j in Q.rows("select id, name from swrd.journals")}
    by_journal = defaultdict(list)
    for r in Q.rows(SAMPLE_SQL):
        by_journal[r["journal_id"]].append((r["year"], r["doi"]))

    eras, renames, contam = {}, [], []
    for jid, items in sorted(by_journal.items()):
        groups = defaultdict(lambda: {"years": [], "containers": Counter()})
        for yr, doi in items:
            item = cache.get(doi.lower())
            if not item:
                continue
            key = tuple(sorted(Q.cr_issns(item)))
            if not key:
                continue
            g = groups[key]
            g["years"].append(yr)
            ct = (item.get("container-title") or [None])[0]
            if ct:
                g["containers"][ct] += 1

        gl = []
        for key, g in groups.items():
            if len(g["years"]) < MIN_GROUP:
                continue
            gl.append({"issn": list(key), "n": len(g["years"]),
                       "first": min(g["years"]), "last": max(g["years"]),
                       "container": g["containers"].most_common(1)[0][0]
                       if g["containers"] else None})
        gl.sort(key=lambda g: -g["n"])
        eras[str(jid)] = {"journal_id": jid, "name": journals[jid]["name"],
                          "sampled": len(items), "groups": gl}
        if len(gl) < 2:
            continue

        primary = gl[0]
        for other in gl[1:]:
            kind = classify(primary, other)
            row = {"journal_id": jid, "journal_name": journals[jid]["name"],
                   "primary_issn": ",".join(primary["issn"]),
                   "primary_container": primary["container"] or "",
                   "primary_years": f"{primary['first']}-{primary['last']}",
                   "other_issn": ",".join(other["issn"]),
                   "other_container": other["container"] or "",
                   "other_years": f"{other['first']}-{other['last']}",
                   "other_n": other["n"], "sampled": len(items), "kind": kind}
            if kind == "rename":
                renames.append(row)
            elif kind == "contamination":
                contam.append(row)

    cols = ["journal_id", "journal_name", "primary_issn", "primary_container",
            "primary_years", "other_issn", "other_container", "other_years",
            "other_n", "sampled", "kind"]
    for path, rowset in ((OUT_RENAME, renames), (OUT_CONTAM, contam)):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(rowset, key=lambda r: -r["other_n"]))
    with open(OUT_ERAS, "w") as f:
        json.dump(eras, f, indent=1, ensure_ascii=False)

    print(f"journals with a usable sample : {len(eras)}")
    print(f"  single ISSN throughout      : {sum(1 for e in eras.values() if len(e['groups']) < 2)}")
    print(f"  rename / publisher change   : {len(renames)}  -> {OUT_RENAME}")
    print(f"  contamination (issue #2)    : {len(contam)}  -> {OUT_CONTAM}")

    if contam:
        print("\ncontamination — a journal row holding another journal's articles:")
        for r in contam:
            print(f"  {r['journal_name'][:38]:<38} {r['other_n']:>3}/{r['sampled']:<3} sampled")
            print(f"     carry {r['other_issn']:<22} = {(r['other_container'] or '?')[:40]}")
            print(f"     ours  {r['primary_issn']:<22} = {(r['primary_container'] or '?')[:40]}")
    if renames:
        print("\nrename / publisher change — no data error, needed for the map:")
        for r in renames:
            print(f"  {r['journal_name'][:34]:<34} {r['other_years']:<11} "
                  f"{(r['other_container'] or '?')[:34]}")


if __name__ == "__main__":
    main()
