#!/usr/bin/env python3
"""
Census — malformed author names in swrd.authors.

    python3 qc/authors/code/02_name_quality.py

Writes ../data/name_quality.csv     every flagged row, with category and links
       prints the census

A CHECK, NOT A FIX. Nothing here proposes a change; the census separates three
very different things that "malformed name" conflates:

1. STRING CORRUPTION (~50 rows) -- text that is wrong in any convention:
     mojibake      'Vesna LeskoÅ¡ek' is 'Vesna Leskošek' read as Latin-1 and
                   re-encoded; 27 rows decode cleanly and are provably fixable
     footnote digits  'Eybalin1, Dominique' carried a superscript marker in
     doubled spaces, trailing commas, one broken XML entity, one stray '7'
   Small, deterministic, safe to repair as a tier-A fix.

2. CONVENTIONS (not corruption; policy calls):
     '[Anonymous]' (942 links) and its variants are deliberate markers for
       unsigned editorials, not bad data
     13,238 ALL-CAPS rows ('THYER, BA') are the legacy Web of Science format,
       ingested as published. 5,714 of them have a title-case twin with the
       same surname+initial -- that is the ENTITY RESOLUTION problem, already
       documented as out of scope ("author names are as published"), and no
       string cleanup should touch it.

3. STRUCTURAL DEFECTS (issue #6, already known):
     6,199 bare single-token rows ('Gottlieb', 'Price') and 256 short
     fragments ('Meg', 'Van') from the split-name ingest. Not fixable by
     looking at the string; needs per-paper evidence.

FALSE POSITIVES THE FIRST PASS MADE, kept here as a warning:
  - 'Bergmark Å.' is not mojibake; Å is Åke. A mojibake test must require the
    latin-1 -> utf-8 round trip to SUCCEED, not just spot suspicious bytes.
  - 'Park, Sunggeun (Ethan)' and tribal names in parentheses are real names.

Read-only.
"""
import csv
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

OUT = os.path.join(ROOT, "data", "name_quality.csv")

NOT_PERSON = re.compile(
    r"^\s*\[?(anonymous|anon\.?|staff|editors?|the editors?|editorial(\s+board)?|"
    r"unknown|n/?a|et\.?\s*al\.?|author unknown|no author|various)\]?\s*$", re.I)
MOJI_SIG = re.compile(r"Ã[a-z©¡³¤¶¼«±«]|â€|Å[¡¾¸†™]|Ã˜|Ã…")


def demojibake(s):
    try:
        fixed = s.encode("latin-1").decode("utf-8")
        return fixed if fixed != s else None
    except Exception:
        return None


def classify(name):
    """First matching category wins; ordered most-specific first."""
    n = name or ""
    if not n.strip():
        return "empty"
    if NOT_PERSON.match(n):
        return "placeholder_convention"
    if MOJI_SIG.search(n) and demojibake(n):
        return "corruption_mojibake"
    if re.search(r"&[a-z]+;|&#x?\d+|<[^>]+>|&;#", n, re.I):
        return "corruption_entity"
    if re.search(r"@|https?://|www\.", n):
        return "corruption_email_url"
    if re.search(r"\d", n):
        return "corruption_digits"
    if re.search(r"\s{2,}|[\x00-\x1f]", n):
        return "corruption_whitespace"
    if re.search(r"[,;:(\[{/-]\s*$", n):
        return "corruption_trailing_punct"
    if len(n.split()) == 1 and 0 < len(n.strip()) < 4:
        return "structural_fragment_short"
    if len(n.split()) == 1 and re.match(r"^[A-Za-zÀ-ÿ'-]+$", n.strip()):
        return "structural_bare_token"
    if len(n.split()) > 1 and n == n.upper() and re.search(r"[A-Z]{2}", n):
        return "format_all_caps_legacy"
    return None


def main():
    rows = Q.rows("""
      select a.id, a.name, count(pa.paper_id) as links
      from swrd.authors a
      left join swrd.paper_authors pa on pa.author_id = a.id
      group by a.id, a.name""")
    print(f"author rows: {len(rows):,}")

    flagged = []
    for r in rows:
        c = classify(r["name"])
        if c:
            row = {"author_id": r["id"], "name": r["name"], "links": r["links"],
                   "category": c}
            if c == "corruption_mojibake":
                row["suggested"] = demojibake(r["name"])
            flagged.append(row)

    counts = OrderedDict()
    for f in flagged:
        c = counts.setdefault(f["category"], {"rows": 0, "links": 0})
        c["rows"] += 1
        c["links"] += f["links"]
    print(f"\n{'category':<32} {'rows':>7} {'links':>8}")
    for k, c in sorted(counts.items()):
        print(f"{k:<32} {c['rows']:>7,} {c['links']:>8,}")
    print(f"\nflagged {len(flagged):,} of {len(rows):,} "
          f"({100 * len(flagged) / len(rows):.1f}%)")

    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["author_id", "name", "links",
                                          "category", "suggested"])
        w.writeheader()
        w.writerows(sorted(flagged, key=lambda r: (r["category"], -r["links"])))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
