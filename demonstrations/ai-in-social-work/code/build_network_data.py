#!/usr/bin/env python3
"""
Build the node/link data behind the interactive co-authorship graph, for both
venues. Thresholds are applied as an iterative k-core so every node shown
really has MIN_LINKS links within the displayed graph.

    python3 build_network_data.py
"""
import json, os
from collections import Counter, defaultdict

HERE = os.path.dirname(__file__)
D    = os.path.join(HERE, "..", "data")
# Sequential ramp: light = commentary, dark = empirical. Node colour places an
# author on a continuum of work orientation (commentary -> study of AI ->
# empirical) from the mix of their own items, exactly as the published figures
# do, rather than flattening them to one dominant category.
RAMP = ["#EDE8FB", "#CFC2F2", "#A896E4", "#7C67CE", "#5A48B4", "#3E3191"]

def ramp_colour(score):
    """score 0 = wholly commentary, 0.5 = wholly study of AI, 1 = wholly empirical"""
    i = min(len(RAMP) - 1, max(0, int(round(score * (len(RAMP) - 1)))))
    return RAMP[i]

def kcore(pc, counts, min_items, min_links):
    keep = {a for a, c in counts.items() if c >= min_items}
    w = Counter()
    for ns in pc.values():
        ks = sorted(a for a in ns if a in keep)
        for i, x in enumerate(ks):
            for y in ks[i + 1:]:
                w[(x, y)] += 1
    nodes = set(keep)
    while True:
        edges = {k: v for k, v in w.items() if k[0] in nodes and k[1] in nodes}
        deg = Counter()
        for (x, y) in edges:
            deg[x] += 1; deg[y] += 1
        drop = {a for a in nodes if deg[a] < min_links}
        if not drop:
            return nodes, edges
        nodes -= drop

def build(pc, counts, labels, names, min_items, min_links, venue):
    nodes, edges = kcore(pc, counts, min_items, min_links)
    mix = defaultdict(Counter)
    for pid, ns in pc.items():
        lab = labels.get(pid)
        for a in ns:
            if a in nodes and lab:
                mix[a][lab] += 1
    order = sorted(nodes, key=lambda a: (-counts[a], names.get(str(a), str(a))))
    idx = {a: i for i, a in enumerate(order)}
    out_nodes = []
    for a in order:
        m = mix[a]
        e, r_, c = m.get("empirical", 0), m.get("reception", 0), m.get("commentary", 0)
        tot = e + r_ + c
        score = (e + 0.5 * r_) / tot if tot else 0.5
        out_nodes.append({"i": idx[a], "num": idx[a] + 1, "name": names.get(str(a), str(a)),
                          "n": counts[a], "split": [e, r_, c], "score": round(score, 3),
                          "color": ramp_colour(score),
                          "dark": score >= 0.55})
    out_links = [{"s": idx[x], "t": idx[y], "w": n} for (x, y), n in edges.items()]
    return {"venue": venue, "min_items": min_items, "min_links": min_links,
            "total_authors": len(counts), "nodes": out_nodes, "links": out_links}

def main():
    # journals: names are surname + first initial (database has no disambiguation)
    J = json.load(open(f"{D}/coauthorship.json"))
    jpc = {k: set(v) for k, v in J["pc"].items()}
    jnames = {a: a for a in J["counts"]}
    journals = build(jpc, Counter(J["counts"]), J["labels"], jnames, 2, 3, "journals")

    # conference: canonical author ids, so identity is reliable
    C = json.load(open(f"{D}/conference_coauthorship.json"))
    cpc = {k: set(v) for k, v in C["pc"].items()}
    conference = build(cpc, Counter({int(k): v for k, v in C["counts"].items()}),
                       C["labels"], C["names"], 3, 2, "conference")

    json.dump({"journals": journals, "conference": conference},
              open(f"{D}/networks.json", "w"), indent=1)
    for k, g in (("journals", journals), ("conference", conference)):
        print(f"{k:11} {len(g['nodes']):3d} nodes, {len(g['links']):3d} links "
              f"(>= {g['min_items']} items, >= {g['min_links']} links; of {g['total_authors']} authors)")

if __name__ == "__main__":
    main()
