import json, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import Counter

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "DejaVu Sans"

recs = json.load(open("classify_records.json"))
new = json.load(open("mlabels_v2.json"))

# Three technology paradigms, named by the AI technology that dominated each.
ERAS = [
    ("Expert systems\n1989–1998",     1989, 1998),
    ("Machine learning\n1999–2022",   1999, 2022),
    ("Generative AI\n2023–2026",      2023, 2026),
]
CATS = [
    ("E", "Empirical AI work  —  build, apply, or test a model on data"),
    ("R", "Attitude & adoption studies  —  surveys of what people think of AI"),
    ("C", "Commentary & reviews  —  writing about AI"),
]

counts = []
for _, lo, hi in ERAS:
    c = Counter()
    for i, r in enumerate(recs):
        if new[str(i)] == "X":
            continue
        if lo <= r["y"] <= hi:
            c[new[str(i)]] += 1
    counts.append(c)
totals = [sum(c.values()) for c in counts]

def draw(color=True):
    cols = {"E": "#2a78d6", "R": "#8e6fb0", "C": "#eb6834"} if color else \
           {"E": "#3d3d3d", "R": "#9a9a9a", "C": "#d0d0d0"}
    fig, ax = plt.subplots(figsize=(7.25, 3.9), dpi=300)
    ypos = list(range(len(ERAS)))[::-1]     # earliest at top
    barh = 0.62
    for row, (era, e) in enumerate(zip(ERAS, range(len(ERAS)))):
        y = ypos[row]
        left = 0.0
        for ck, _ in CATS:
            pct = 100.0 * counts[e][ck] / totals[e] if totals[e] else 0
            if pct <= 0:
                continue
            ax.barh(y, pct, barh, left=left, color=cols[ck],
                    edgecolor="white", linewidth=1.0, zorder=3)
            if pct >= 6:
                txtcol = "white" if (color or ck == "E") else "#111111"
                ax.text(left + pct / 2, y, f"{pct:.0f}%\n(n={counts[e][ck]})",
                        ha="center", va="center", fontsize=8,
                        color=txtcol, linespacing=1.0, zorder=4)
            left += pct
    ax.set_yticks(ypos)
    ax.set_yticklabels([f"{era}\n(N={t})" for (era, _, _), t in zip(ERAS, totals)],
                       fontsize=8.5)
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 25))
    ax.set_xticklabels([f"{v}%" for v in range(0, 101, 25)], fontsize=8)
    ax.set_xlabel("Share of the era's articles", fontsize=9)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    # legend below
    handles = [plt.Rectangle((0, 0), 1, 1, color=cols[ck]) for ck, _ in CATS]
    ax.legend(handles, [nm for _, nm in CATS], loc="upper center",
              bbox_to_anchor=(0.5, -0.28), fontsize=7.6, frameon=False,
              handlelength=1.1, labelspacing=0.4)
    fig.tight_layout()
    suf = "color" if color else "gray"
    fig.savefig(f"figure_era_stacked_{suf}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"figure_era_stacked_{suf}.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote", suf)

for (era, _, _), c, t in zip(ERAS, counts, totals):
    print(era.replace(chr(10), " "), "N=", t, dict(c))
draw(True)
draw(False)
print("done")
