#!/usr/bin/env python3
"""
Step 2 — every number on the demonstration page, recomputed from the released
labels. Run this to check the page rather than trust it.

    python3 compute_stats.py            # print the numbers
    python3 compute_stats.py --write    # also refresh data/stats.json
"""
import json, os, sys, re
from collections import Counter, defaultdict

HERE = os.path.dirname(__file__)
CORPUS = os.path.join(HERE, "..", "data", "ai_corpus_labeled.json")
STATS  = os.path.join(HERE, "..", "data", "stats.json")
ERAS = [("Expert systems", 1989, 1998),
        ("Machine learning", 1999, 2022),
        ("Generative AI", 2023, 2026)]

def load():
    with open(CORPUS) as f:
        return json.load(f)

def main():
    C = load()
    swrd = [r for r in C if r["source"] == "swrd"]
    wos  = [r for r in C if r["source"] == "wos"]
    print(f"corpus: {len(C)} records — SWRD database {len(swrd)}, WoS supplement {len(wos)}")
    print(f"labels: {dict(Counter(r['label'] for r in C))}")
    print(f"  hand-decided ties: {sum(1 for r in C if r.get('label_source') == 'human tie-break')}")

    print("\nper-year (database / supplement):")
    ys, yw = Counter(int(r['year']) for r in swrd if r['year']), Counter(int(r['year']) for r in wos if r['year'])
    for y in sorted(set(ys) | set(yw)):
        print(f"  {y}  {ys.get(y,0):3d} / {yw.get(y,0):3d}")

    print("\nera composition:")
    for name, lo, hi in ERAS:
        sub = [r for r in C if r["year"] and lo <= int(r["year"]) <= hi]
        c = Counter(r["label"] for r in sub); n = len(sub)
        pct = {k: f"{100*v/n:.0f}%" for k, v in c.items()}
        print(f"  {name:17} {lo}-{hi}  N={n:3d}  {dict(c)}  {pct}")

    print("\ntop 10 outlets:")
    jc = Counter(r["journal"] for r in C if r.get("journal"))
    src = defaultdict(Counter)
    for r in C:
        if r.get("journal"): src[r["journal"]][r["source"]] += 1
    top = jc.most_common(10)
    for i, (j, n) in enumerate(top, 1):
        print(f"  {i:2d}. {n:3d}  ({src[j]['swrd']} db / {src[j]['wos']} suppl)  {j}")
    print(f"  distinct outlets: {len(jc)} | single-article outlets: {sum(1 for _, n in jc.items() if n == 1)}"
          f" | top-10 share: {sum(n for _, n in top)}/{len(C)}")

    print("\nlabel agreement among the four independent runs:")
    unan = sum(1 for r in C if len(set(r["model_votes"].values())) == 1)
    print(f"  unanimous on label: {unan}/{len(C)} ({100*unan/len(C):.0f}%)")

    if "--write" in sys.argv:
        stats = {
            "total": len(C), "swrd": len(swrd), "wos": len(wos),
            "labels": dict(Counter(r["label"] for r in C)),
            "years_swrd": dict(sorted(ys.items())), "years_wos": dict(sorted(yw.items())),
            "top_outlets": [{"journal": j, "n": n, "swrd": src[j]["swrd"], "wos": src[j]["wos"]}
                            for j, n in top],
            "distinct_outlets": len(jc),
            "eras": [{"name": nm, "lo": lo, "hi": hi,
                      "counts": dict(Counter(r["label"] for r in C
                                             if r["year"] and lo <= int(r["year"]) <= hi))}
                     for nm, lo, hi in ERAS],
        }
        with open(STATS, "w") as f:
            json.dump(stats, f, indent=1)
        print(f"\nwrote {os.path.relpath(STATS)}")

if __name__ == "__main__":
    main()
