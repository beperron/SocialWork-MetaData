#!/usr/bin/env python3
"""
Co-authorship network for the AI corpus.

Two explicit thresholds keep the picture readable rather than a hairball, and
both are stated in the figure caption:

  MIN_ITEMS  an author must appear on at least this many corpus items
  MIN_LINKS  ...and must have at least this many co-author links after that

Authors are identified by surname + first initial. The journal database stores
names as published with NO disambiguation, so two people who share a surname
and an initial are merged here; treat author-level counts as approximate.

    pip install matplotlib networkx
    python3 make_network.py
"""
import json, math, os
from collections import Counter, defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

HERE = os.path.dirname(__file__)
NET  = os.path.join(HERE, "..", "data", "coauthorship.json")
FIGS = os.path.join(HERE, "..", "figures")

MIN_ITEMS = 2      # author must appear on >= this many corpus items
MIN_LINKS = 3      # ...and have >= this many co-author links

EMP, REC, COM = "#4a3aa7", "#eb6834", "#1baf7a"
INK, INK2, MUT, EDGE, SURF = "#18181B", "#3F3F46", "#71717A", "#C9C7C0", "#FFFFFF"
plt.rcParams.update({"svg.fonttype": "none", "font.family": "sans-serif",
                     "font.sans-serif": ["IBM Plex Sans", "system-ui", "Arial"], "text.color": INK})

def main():
    D = json.load(open(NET))
    pc, counts, labels = D["pc"], Counter(D["counts"]), D["labels"]

    keep = {a for a, c in counts.items() if c >= MIN_ITEMS}
    w = Counter()
    for pid, ns in pc.items():
        ks = sorted(a for a in ns if a in keep)
        for i, x in enumerate(ks):
            for y in ks[i + 1:]:
                w[(x, y)] += 1
    # prune iteratively: dropping a node removes its links, which can push a
    # neighbour below the threshold. Repeat until every surviving node really
    # has MIN_LINKS links *within the displayed graph* (a k-core).
    nodes = set(keep)
    while True:
        edges = {k: v for k, v in w.items() if k[0] in nodes and k[1] in nodes}
        deg = Counter()
        for (x, y) in edges:
            deg[x] += 1; deg[y] += 1
        drop = {a for a in nodes if deg[a] < MIN_LINKS}
        if not drop:
            break
        nodes -= drop

    # each author's dominant category, for node colour
    mix = defaultdict(Counter)
    for pid, ns in pc.items():
        lab = labels.get(pid)
        for a in ns:
            if a in nodes and lab: mix[a][lab] += 1
    colour = {a: {"empirical": EMP, "reception": REC, "commentary": COM}[mix[a].most_common(1)[0][0]]
              for a in nodes}

    G = nx.Graph(); G.add_nodes_from(nodes)
    for (x, y), n in edges.items(): G.add_edge(x, y, weight=n)

    order = sorted(nodes, key=lambda a: (-counts[a], a))
    num = {a: i + 1 for i, a in enumerate(order)}

    pos = nx.spring_layout(G, seed=9, k=3.4 / math.sqrt(len(nodes)), iterations=900)
    P = {n: [pos[n][0], pos[n][1]] for n in G}
    MIN_SEP = 0.17
    for _ in range(1200):                      # push overlapping nodes apart
        moved = False
        ns = list(P)
        for i, a in enumerate(ns):
            for b in ns[i + 1:]:
                dx, dy = P[a][0] - P[b][0], P[a][1] - P[b][1]
                d = math.hypot(dx, dy)
                if d < MIN_SEP:
                    push = (MIN_SEP - d) / 2 / (d + 1e-9)
                    P[a][0] += dx * push; P[a][1] += dy * push
                    P[b][0] -= dx * push; P[b][1] -= dy * push
                    moved = True
        if not moved: break

    fig = plt.figure(figsize=(13.4, 7.8)); fig.patch.set_facecolor(SURF)
    ax = fig.add_axes([0.0, 0.085, 0.615, 0.85]); ax.set_facecolor(SURF); ax.axis("off")
    for (a, b), n in edges.items():
        ax.plot([P[a][0], P[b][0]], [P[a][1], P[b][1]], color=EDGE,
                lw=0.7 + 0.8 * n, zorder=1, solid_capstyle="round")
    for a in G:
        c = counts[a]
        ax.scatter([P[a][0]], [P[a][1]], s=190 + 62 * c, color=colour[a],
                   edgecolors="#111", linewidths=1.1, zorder=3)
        ax.text(P[a][0], P[a][1], str(num[a]), ha="center", va="center",
                fontsize=8.6, color="#fff" if colour[a] != COM else "#06301e",
                fontweight="bold", zorder=4)
    ax.margins(0.09)

    lg = fig.add_axes([0.625, 0.085, 0.375, 0.85]); lg.axis("off")
    lg.set_xlim(0, 1); lg.set_ylim(0, 1)
    lg.text(0, 0.995, "Node colour — the author's most common category",
            fontsize=9.2, fontweight="bold", va="top", color=INK)
    for i, (lab, col) in enumerate((("empirical", EMP), ("reception", REC), ("commentary", COM))):
        lg.scatter([0.022], [0.952 - i * 0.038], s=95, color=col, edgecolors="#111", linewidths=1)
        lg.text(0.065, 0.952 - i * 0.038, lab, fontsize=8.8, color=INK2, va="center")
    top_y = 0.952 - 3 * 0.038 - 0.032
    lg.text(0, top_y, "Authors, by number of corpus items",
            fontsize=9.2, fontweight="bold", va="top", color=INK)
    half = math.ceil(len(order) / 2)
    step = min(0.042, (top_y - 0.05) / max(half, 1))
    for col, chunk in enumerate((order[:half], order[half:])):
        for row, a in enumerate(chunk):
            y = top_y - 0.042 - row * step
            lg.text(col * 0.5, y, f"{num[a]}.", fontsize=8.5, color=MUT, va="center", ha="left")
            lg.text(col * 0.5 + 0.055, y, f"{a} ({counts[a]})", fontsize=8.5,
                    color=INK2, va="center", ha="left")

    fig.text(0.008, 0.988, f"Who works with whom — {len(nodes)} authors, {len(edges)} collaborations",
             fontsize=13, fontweight="bold", color=INK, va="top")
    fig.text(0.008, 0.012,
             f"Inclusion: authors on {MIN_ITEMS}+ corpus items with {MIN_LINKS}+ co-author links "
             f"({len(nodes)} of {len(counts)} authors in the corpus). Node size and the number in the legend "
             f"are that author's item count;\nedge width is joint items. Position carries no meaning beyond "
             f"connectivity. Names are surname + first initial: the journal database does not disambiguate "
             f"authors, so same-initial namesakes merge.",
             fontsize=7.9, color=MUT, va="bottom")
    fig.savefig(f"{FIGS}/network.svg", bbox_inches="tight", facecolor=SURF)
    fig.savefig("/tmp/_network_check.png", dpi=155, bbox_inches="tight", facecolor=SURF)
    print(f"wrote network.svg — {len(nodes)} nodes, {len(edges)} edges "
          f"(every node has >= {MIN_LINKS} links within the graph)")
    comps = [c for c in nx.connected_components(G) if len(c) > 1]
    print(f"components: {len(comps)}, largest {max((len(c) for c in comps), default=0)}")

if __name__ == "__main__":
    main()
