import json, sys, numpy as np, networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from scipy.spatial import cKDTree

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "DejaVu Sans"

SRC, TAG, THRESH, ITEM = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
ITEMC = ITEM.capitalize()
d = json.load(open(SRC))
name = {int(k): v for k, v in d["name"].items()}
apc = {int(k): v for k, v in d["apc"].items()}
ascore = {int(k): v for k, v in d["ascore"].items()}
acat = {int(k): v for k, v in d["acat"].items()}
Efull = {}
for k, w in d["edges"].items():
    a, b = k.split("|"); Efull[(int(a), int(b))] = int(w)

# selection rule: authors with THRESH+ items, plus co-authorships among them
top = sorted([a for a in apc if apc[a] >= THRESH], key=lambda a: -apc[a])
tset = set(top); tnum = {a: i + 1 for i, a in enumerate(top)}
G = nx.Graph()
for a in top: G.add_node(a)
for (a, b), w in Efull.items():
    if a in tset and b in tset: G.add_edge(a, b, w=w)
print(f"{TAG}: threshold >= {THRESH} -> {len(top)} authors, {G.number_of_edges()} edges")

P0 = nx.spring_layout(G, k=1.3, iterations=500, seed=5, weight=None)
nodes = list(G.nodes())
P = np.array([P0[n] for n in nodes]); P -= P.mean(0); P /= (np.abs(P).max() + 1e-9)
MIN = 0.30
for _ in range(500):
    pairs = cKDTree(P).query_pairs(MIN)
    if not pairs: break
    disp = np.zeros_like(P)
    for i, j in pairs:
        v = P[i] - P[j]; dist = np.hypot(*v) or 1e-6
        push = (MIN - dist) * 0.5 * v / dist; disp[i] += push; disp[j] -= push
    P += disp
pos = {n: tuple(P[k]) for k, n in enumerate(nodes)}

def draw(color=True):
    cmap = plt.get_cmap("RdYlBu") if color else plt.get_cmap("Greys")
    norm = Normalize(0, 1)
    fig = plt.figure(figsize=(7.25, 5.3), dpi=300)
    axn = fig.add_axes([0.01, 0.20, 0.62, 0.78])
    for a, b, dd in G.edges(data=True):
        axn.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]],
                 color="#c2c6cc", lw=0.5 + 0.4 * (dd["w"] - 1), zorder=1, alpha=0.9)
    for nd in G.nodes():
        s = 130 + apc[nd] ** 1.05 * 18
        axn.scatter(*pos[nd], s=s, color=[cmap(norm(ascore[nd]))], edgecolors="#111111",
                    linewidths=0.9, zorder=3)
    for a in top:
        val = ascore[a]
        tc = "white" if (color and (val <= 0.14 or val >= 0.88)) else "#111111"
        axn.text(pos[a][0], pos[a][1], str(tnum[a]), fontsize=8.6, fontweight="bold",
                 ha="center", va="center", zorder=6, color=tc)
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    axn.set_xlim(min(xs) - .12, max(xs) + .12); axn.set_ylim(min(ys) - .12, max(ys) + .12)
    axn.axis("off"); axn.set_aspect("equal")

    axc = fig.add_axes([0.05, 0.10, 0.45, 0.03])
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=axc, orientation="horizontal")
    cb.set_ticks([]); axc.tick_params(length=0)
    axc.set_title("Orientation of the author's AI work", fontsize=8.5, pad=3)
    for xv, lab, ha in [(0.0, "Commentary", "left"), (0.5, "Study of AI", "center"), (1.0, "Empirical", "right")]:
        axc.text(xv, -1.4, lab, transform=axc.transAxes, ha=ha, va="top", fontsize=8.6, color="#111")

    axt = fig.add_axes([0.645, 0.02, 0.35, 0.96]); axt.axis("off")
    axt.text(0.0, 1.0, "Author", fontsize=8.5, fontweight="bold", color="#444", va="top")
    axt.text(1.0, 1.0, ITEMC, fontsize=8.5, fontweight="bold", color="#444", va="top", ha="right")
    per = len(top); dy = 0.955 / per
    for i, a in enumerate(top):
        yy = 0.95 - i * dy; c = acat[a]
        axt.text(0.0, yy, f"{tnum[a]}", fontsize=8.6, fontweight="bold", color="#333", va="top")
        axt.text(0.07, yy, name[a], fontsize=8.6, color="#111", va="top")
        axt.text(1.0, yy, f"{apc[a]} ({c['E']}/{c['S']}/{c['C']})", fontsize=8.6, color="#333", va="top", ha="right")

    suf = "color" if color else "gray"
    fig.savefig(f"figureN_{TAG}_network_{suf}.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(f"figureN_{TAG}_network_{suf}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", TAG, suf)

draw(True); draw(False); print("done", TAG)
