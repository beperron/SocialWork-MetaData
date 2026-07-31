#!/usr/bin/env python3
"""
Conference co-authorship network, drawn at a deliberately high threshold so the
collaborating core is legible rather than a hairball.

    MIN_PRESENTATIONS  an author must appear on at least this many verified
                       presentations in the corpus
    MIN_LINKS          ...and must still hold at least this many co-author
                       links after everyone below the bar is removed

Both are applied repeatedly (a k-core): dropping an author removes their links,
which can push a collaborator below the bar, so the pass is run until every
author still shown genuinely meets both rules.

The conference database carries canonical author identifiers, so these counts
are reliable — unlike the journal side, where names are stored as published.

    pip install matplotlib networkx
    python3 make_sswr_network.py
"""
import json, math, os
from collections import Counter, defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

HERE = os.path.dirname(__file__)
NET  = os.path.join(HERE, "..", "data", "conference_coauthorship.json")
FIGS = os.path.join(HERE, "..", "figures")

MIN_PRESENTATIONS = 3
MIN_LINKS         = 3

RAMP = ["#EDE8FB", "#CFC2F2", "#A896E4", "#7C67CE", "#5A48B4", "#3E3191"]
INK, INK2, MUT, EDGE, SURF = "#18181B", "#3F3F46", "#71717A", "#C9C7C0", "#FFFFFF"
plt.rcParams.update({"svg.fonttype": "none", "font.family": "sans-serif",
                     "font.sans-serif": ["IBM Plex Sans", "system-ui", "Arial"], "text.color": INK})

def main():
    D = json.load(open(NET))
    pc = {k: set(v) for k, v in D["pc"].items()}
    counts = Counter({int(k): v for k, v in D["counts"].items()})
    names, labels = D["names"], D["labels"]

    keep = {a for a, c in counts.items() if c >= MIN_PRESENTATIONS}
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
        drop = {a for a in nodes if deg[a] < MIN_LINKS}
        if not drop:
            break
        nodes -= drop

    mix = defaultdict(Counter)
    for pid, ns in pc.items():
        lab = labels.get(pid)
        for a in ns:
            if a in nodes and lab:
                mix[a][lab] += 1
    def orient(a):
        m = mix[a]; e, r_, c = m.get("empirical", 0), m.get("reception", 0), m.get("commentary", 0)
        t = e + r_ + c
        return (e + 0.5 * r_) / t if t else 0.5
    score = {a: orient(a) for a in nodes}
    colour = {a: RAMP[min(len(RAMP) - 1, max(0, round(score[a] * (len(RAMP) - 1))))] for a in nodes}
    split = {a: (mix[a].get("empirical", 0), mix[a].get("reception", 0), mix[a].get("commentary", 0))
             for a in nodes}

    G = nx.Graph(); G.add_nodes_from(nodes)
    for (x, y), n in edges.items():
        G.add_edge(x, y, weight=n)
    order = sorted(nodes, key=lambda a: (-counts[a], names[str(a)]))
    num = {a: i + 1 for i, a in enumerate(order)}

    pos = nx.spring_layout(G, seed=4, k=3.0 / math.sqrt(len(nodes)), iterations=900)
    P = {n: [pos[n][0], pos[n][1]] for n in G}
    for _ in range(1200):
        moved = False
        ns = list(P)
        for i, a in enumerate(ns):
            for b in ns[i + 1:]:
                dx, dy = P[a][0] - P[b][0], P[a][1] - P[b][1]
                d = math.hypot(dx, dy)
                if d < 0.30:
                    push = (0.30 - d) / 2 / (d + 1e-9)
                    P[a][0] += dx * push; P[a][1] += dy * push
                    P[b][0] -= dx * push; P[b][1] -= dy * push
                    moved = True
        if not moved:
            break

    fig = plt.figure(figsize=(12.6, 6.6)); fig.patch.set_facecolor(SURF)
    ax = fig.add_axes([0.0, 0.02, 0.60, 0.86]); ax.set_facecolor(SURF); ax.axis("off")
    for (a, b), n in edges.items():
        ax.plot([P[a][0], P[b][0]], [P[a][1], P[b][1]], color=EDGE,
                lw=0.9 + 1.1 * n, zorder=1, solid_capstyle="round")
    for a in G:
        ax.scatter([P[a][0]], [P[a][1]], s=330 + 74 * counts[a], color=colour[a],
                   edgecolors="#111", linewidths=1.2, zorder=3)
        ax.text(P[a][0], P[a][1], str(num[a]), ha="center", va="center", fontsize=10,
                color="#fff" if score[a] >= 0.55 else "#241E38", fontweight="bold", zorder=4)
    ax.margins(0.12)

    lg = fig.add_axes([0.605, 0.02, 0.395, 0.86]); lg.axis("off")
    lg.set_xlim(0, 1); lg.set_ylim(0, 1)
    lg.text(0, 1.0, "Node colour — the orientation of that author's work",
            fontsize=9.2, fontweight="bold", va="top", color=INK)
    for i, c in enumerate(RAMP):
        lg.add_patch(plt.Rectangle((0.02 + i * 0.083, 0.925), 0.083, 0.036,
                                   facecolor=c, edgecolor="none", clip_on=False))
    lg.add_patch(plt.Rectangle((0.02, 0.925), 0.083 * len(RAMP), 0.036,
                               facecolor="none", edgecolor="#C9C7C0", lw=0.8, clip_on=False))
    lg.text(0.02, 0.905, "commentary", fontsize=8, color=MUT, va="top", ha="left")
    lg.text(0.02 + 0.083 * len(RAMP) / 2, 0.905, "study of AI", fontsize=8, color=MUT, va="top", ha="center")
    lg.text(0.02 + 0.083 * len(RAMP), 0.905, "empirical", fontsize=8, color=MUT, va="top", ha="right")
    lg.text(0, 0.775, "Authors, by verified presentations", fontsize=9.2,
            fontweight="bold", va="top", color=INK)
    for row, a in enumerate(order):
        y = 0.725 - row * 0.052
        lg.text(0, y, f"{num[a]}.", fontsize=9, color=MUT, va="center")
        e, r_, c = split[a]
        lg.text(0.055, y, f"{names[str(a)]} — {counts[a]} ({e}/{r_}/{c})",
                fontsize=8.8, color=INK2, va="center")

    fig.text(0.008, 0.985, "The conference collaborating core",
             fontsize=13.5, fontweight="bold", color=INK, va="top")
    fig.text(0.008, 0.935,
             f"THRESHOLD:  {MIN_PRESENTATIONS}+ verified presentations   AND   {MIN_LINKS}+ co-author links",
             fontsize=10, fontweight="bold", color="#4a3aa7", va="top")
    fig.savefig(f"{FIGS}/network_conference.svg", bbox_inches="tight", pad_inches=0.28, facecolor=SURF)
    fig.savefig("/tmp/_sswr_net.png", dpi=150, bbox_inches="tight", pad_inches=0.28, facecolor=SURF)
    comps = [c for c in nx.connected_components(G) if len(c) > 1]
    print(f"wrote network_conference.svg — {len(nodes)} authors, {len(edges)} links, "
          f"{len(comps)} groups (largest {max((len(c) for c in comps), default=0)})")

if __name__ == "__main__":
    main()
