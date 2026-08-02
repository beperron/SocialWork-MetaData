#!/usr/bin/env python3
"""
Co-authorship networks for the suicide corpus, one per venue.

    python3 make_network.py

Reads  ../data/suicide_abstract_screening_results.json  (relevant records only)
Writes ../data/networks.json                            (the interactive figure's data)

Two thresholds keep the picture readable rather than a hairball. Both are
stated on the page, and both are constants here so a reader can redraw the
graph at their own cutoffs:

  MIN_ITEMS  an author must appear on at least this many relevant records
  MIN_LINKS  ...and hold at least this many co-author links after that

Author identity differs by venue, and the difference is not cosmetic:

  SSWR  carries canonical author ids with name variants already resolved.
        Those counts are solid.
  SWRD  stores names exactly as published with NO disambiguation, and not even
        in a consistent format — this corpus contains "GILLILAND, D",
        "Gilliland D." and "Fiona Gardner". Identity here is surname + first
        initial, recovered by the heuristic below. Same-initial namesakes merge
        and one person under two name forms may split. Treat as approximate.
"""
import json
import os
import re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "data", "suicide_abstract_screening_results.json")
OUT = os.path.join(HERE, "..", "data", "networks.json")

# The conference graph is far denser than the journal graph — the same cutoffs
# give 42 nodes in one and 306 in the other — so each venue gets its own,
# chosen to land both around 40 nodes. Both are printed in the figure caption.
MIN_ITEMS = {"journals": 2, "conference": 3}
MIN_LINKS = {"journals": 4, "conference": 4}

# Node colour runs from qualitative-leaning to quantitative-leaning, which is
# the corpus's most striking feature made visible at the author level.
RAMPS = {
    "journals":   ["#9FD3CB", "#7FC0B5", "#5CA99C", "#3D8F81", "#256E63", "#0F5257"],
    "conference": ["#F0C39A", "#E5A874", "#D98E52", "#C97B3E", "#A9612C", "#83481D"],
}
DARK_FROM = 3      # ramp index at which white label text becomes readable

INITIALS = re.compile(r"^[A-Za-z]\.?([A-Za-z]\.?)?$")

# Placeholders that are not people. SWRD carries 4 records credited to
# "Anonymous", which would otherwise become a node joining unrelated authors
# into a spurious collaboration.
NOT_A_PERSON = re.compile(r"^(anonymous|staff|editors?|unknown|n/?a)$", re.I)

# ---------------------------------------------------------------------------
# Disambiguation, for THIS corpus only.
#
# SWRD stores names as published with no disambiguation, so surname + first
# initial is wrong in both directions: it merges different people who share
# them, and it splits one person recorded under a misspelling. Both happen
# here. These tables fix the cases in this corpus and are deliberately
# explicit and hand-checked rather than fuzzy — the corpus is small enough to
# resolve properly, and a similarity threshold would quietly merge
# Cheng/Cheung and Collins/Collin, who are different people.
#
# NOTE: this corrects the figure on this page. It does not touch the database,
# where the same names remain undisambiguated.

# Misspelled surnames -> the form used by the same person elsewhere in the
# corpus. Each verified by inspecting the records: same co-authors, same
# journals, same research programme.
SURNAME_FIX = {
    "miriek": "mirick",     # 'Miriek, Rebecca G' — 4 records, incl. one paper
                            # listing both spellings as if two people
    "moffat": "moffatt",    # 'Moffat, Ken' / 'Moffatt, Ken'
    "muelle": "mueller",    # 'Muelle, Anna S' / 'Mueller, Anna S.'
}

# Given names that are the same person. Larry/Lawrence Berkowitz appears on
# seven records, always with the same Mirick postvention team.
NICKNAMES = [{"larry", "lawrence"}]


def swrd_key(raw: str):
    """Return (key, display) for a published SWRD author string.

    Handles the three formats present in this corpus:
        "GILLILAND, D"    surname first, comma
        "Gilliland D."    surname first, no comma, trailing initials
        "Fiona Gardner"   given name first
    """
    name = re.sub(r"\s+", " ", (raw or "").strip().strip(".,"))
    if not name or NOT_A_PERSON.match(name):
        return None, None, ""

    if "," in name:
        surname, _, rest = name.partition(",")
        given = rest.strip()
    else:
        parts = name.split()
        if len(parts) == 1:
            surname, given = parts[0], ""
        elif INITIALS.match(parts[-1]):
            # trailing token is an initial -> the name led with the surname
            surname, given = " ".join(parts[:-1]), parts[-1]
        else:
            surname, given = parts[-1], parts[0]

    surname = surname.strip().strip(".")
    if not surname:
        return None, None, ""
    slug = re.sub(r"[^a-z]", "", surname.lower())
    slug = SURNAME_FIX.get(slug, slug)
    initial = (given.strip().strip(".")[:1] or "").upper()
    first = re.sub(r"[^a-z]", "", given.split()[0].lower()) if given.split() else ""
    key = f"{slug}|{initial.lower()}"
    display = surname.title() + (f", {initial}." if initial else "")
    return key, display, (first if len(first) > 2 else "")


def outcome(rec):
    s = rec["screening"]
    return "Non-empirical" if s["evidence_class"] == "Non-empirical" else s["empirical_method"]


def nickname_group(first):
    """Collapse known nickname pairs so they do not read as two people."""
    for grp in NICKNAMES:
        if first in grp:
            return "/".join(sorted(grp))
    return first


def resolve_swrd(records):
    """Map every SWRD author mention to a disambiguated identity.

    Surname + first initial is the only key the source supports, but it is
    wrong in both directions. This pass repairs both:

      merge   misspelled surnames are folded in by SURNAME_FIX before keying,
              and nickname pairs are treated as one person
      split   where one key covers two genuinely different first names, the
              key gains the first name, so 'Lee, Edward Ou Jin' and
              'Lee, Eunjung' become separate identities

    Entries that give only an initial attach to the majority full name under
    that key when there is exactly one; when a key is genuinely contested they
    cannot be assigned and are left on the bare key.
    """
    seen = defaultdict(Counter)          # key -> first names seen, weighted
    for rec in records:
        for raw in (rec.get("authors") or "").split(";"):
            k, _, first = swrd_key(raw)
            if k and first:
                seen[k][nickname_group(first)] += 1

    contested = {k for k, c in seen.items() if len(c) > 1}
    majority = {k: c.most_common(1)[0][0] for k, c in seen.items() if len(c) == 1}

    def resolve(raw):
        k, disp, first = swrd_key(raw)
        if not k:
            return None, None
        g = nickname_group(first) if first else ""
        if k not in contested:
            return k, disp
        if not g:
            # initial only under a contested key: it cannot be assigned to
            # either person, so the mention is dropped rather than guessed
            return None, None
        surname = disp.split(",")[0]
        return f"{k}|{g}", f"{surname}, {g.split('/')[0].title()}"

    return resolve


def build(records, venue, resolve=None):
    """One venue -> nodes, links, and the colour/threshold metadata."""
    per_paper, counts, display, mix = {}, Counter(), {}, defaultdict(Counter)

    for rec in records:
        keys = []
        if venue == "conference":
            ids = [i.strip() for i in (rec.get("author_ids") or "").split(";") if i.strip()]
            names = [n.strip() for n in (rec.get("authors") or "").split(";") if n.strip()]
            for i, aid in enumerate(ids):
                keys.append(aid)
                display.setdefault(aid, names[i] if i < len(names) else aid)
        else:
            for raw in (rec.get("authors") or "").split(";"):
                k, d = resolve(raw)
                if k:
                    keys.append(k)
                    display.setdefault(k, d)
        # A number of SWRD records list the same author twice; dedupe within
        # the paper so that does not become a self-collaboration.
        keys = sorted(set(keys))
        if not keys:
            continue
        per_paper[rec["record_key"]] = keys
        o = outcome(rec)
        for k in keys:
            counts[k] += 1
            mix[k][o] += 1

    keep = {a for a, c in counts.items() if c >= MIN_ITEMS[venue]}
    weights = Counter()
    for keys in per_paper.values():
        ks = [a for a in keys if a in keep]
        for i, x in enumerate(ks):
            for y in ks[i + 1:]:
                weights[tuple(sorted((x, y)))] += 1

    # Prune iteratively: removing a node deletes its links, which can push a
    # neighbour below the threshold. Repeat until every surviving node really
    # holds MIN_LINKS links *within the drawn graph*.
    while True:
        deg = Counter()
        for (x, y), w in weights.items():
            if x in keep and y in keep:
                deg[x] += 1
                deg[y] += 1
        drop = {a for a in keep if deg[a] < MIN_LINKS[venue]}
        if not drop:
            break
        keep -= drop

    ordered = sorted(keep, key=lambda a: (-counts[a], display.get(a, a)))
    index = {a: i for i, a in enumerate(ordered)}
    ramp = RAMPS[venue]

    nodes = []
    for a in ordered:
        m = mix[a]
        qt, ql, rv, ne = (m["Quantitative"], m["Qualitative"], m["Review"], m["Non-empirical"])
        total = qt + ql + rv + ne
        score = qt / total if total else 0.0
        band = min(int(score * len(ramp)), len(ramp) - 1)
        nodes.append({
            "i": index[a], "num": index[a] + 1,
            "name": display.get(a, a), "n": counts[a],
            "split": [qt, ql, rv, ne], "score": round(score, 3),
            "color": ramp[band], "dark": band >= DARK_FROM,
        })

    links = [{"s": index[x], "t": index[y], "w": w}
             for (x, y), w in weights.items() if x in keep and y in keep]

    return {
        "venue": venue, "ramp": ramp,
        "min_items": MIN_ITEMS[venue], "min_links": MIN_LINKS[venue],
        "total_authors": len(counts),
        "nodes": nodes, "links": links,
    }


def main():
    with open(SRC) as f:
        recs = [r for r in json.load(f)["screening_results"] if r["screening"]["is_relevant"]]

    swrd = [r for r in recs if r["source_database"] == "SWRD"]
    out = {
        "journals": build(swrd, "journals", resolve_swrd(swrd)),
        "conference": build([r for r in recs if r["source_database"] == "SSWR"], "conference"),
    }
    with open(OUT, "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    for v, g in out.items():
        print(f"{v:<11} {len(g['nodes']):>4} of {g['total_authors']:>4} authors shown, "
              f"{len(g['links']):>4} links  (>={g['min_items']} items, >={g['min_links']} links)")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
