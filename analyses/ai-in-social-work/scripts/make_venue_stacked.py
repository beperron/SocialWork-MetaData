import json, os, numpy as np
import matplotlib
APA = os.environ.get("APA") == "1"   # APA mode: no title/note baked into the image
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "DejaVu Sans"

d = json.load(open("journal_venues.json"))
jc = d["jc"]; tot = d["tot"]; disp = d["disp"]
order = sorted(tot, key=lambda k: -tot[k])
TOPN = 14
top = order[:TOPN]; rest = order[TOPN:]
rest_c = {"E": sum(jc[k].get("E", 0) for k in rest),
          "S": sum(jc[k].get("S", 0) for k in rest),
          "C": sum(jc[k].get("C", 0) for k in rest)}
rows = [(disp[k], jc[k].get("E", 0), jc[k].get("S", 0), jc[k].get("C", 0)) for k in top]
rows.append((f"Other ({len(rest)} journals)", rest_c["E"], rest_c["S"], rest_c["C"]))

CATS = [("E", "Empirical AI work", "#2a78d6"), ("S", "Study of AI (reception)", "#8e6fb0"),
        ("C", "Commentary & review", "#eb6834")]
GRY = {"E": "#3d3d3d", "S": "#9a9a9a", "C": "#d0d0d0"}

def draw(color=True):
    cmap = {k: c for k, _, c in CATS} if color else GRY
    fig, ax = plt.subplots(figsize=(7.5, 5.6), dpi=300)
    labels = [r[0] for r in rows][::-1]
    E = np.array([r[1] for r in rows])[::-1]
    S = np.array([r[2] for r in rows])[::-1]
    C = np.array([r[3] for r in rows])[::-1]
    y = np.arange(len(rows))
    ax.barh(y, E, color=cmap["E"], edgecolor="white", linewidth=0.6, zorder=3, label="E")
    ax.barh(y, S, left=E, color=cmap["S"], edgecolor="white", linewidth=0.6, zorder=3, label="S")
    ax.barh(y, C, left=E + S, color=cmap["C"], edgecolor="white", linewidth=0.6, zorder=3, label="C")
    tot_row = E + S + C
    for i in range(len(rows)):
        ax.text(tot_row[i] + 0.6, y[i], str(tot_row[i]), va="center", ha="left",
                fontsize=7.5, color="#333")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Number of verified AI articles", fontsize=9)
    ax.set_xlim(0, max(tot_row) + 22)   # right margin for the legend
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0); ax.tick_params(axis="x", labelsize=8)
    ax.grid(axis="x", color="#ececec", linewidth=0.7, zorder=0)
    handles = [Rectangle((0, 0), 1, 1, color=cmap[k]) for k, _, _ in CATS]
    ax.legend(handles, [f"{k} — {nm}" for k, nm, _ in CATS], loc="center right",
              bbox_to_anchor=(1.0, 0.5), fontsize=8, frameon=True, framealpha=0.95,
              edgecolor="#cccccc")
    if not APA:
        ax.set_title("Where AI Is Published in Disciplinary Social Work Journals, by Article Type",
                     fontsize=10.5, pad=8)
        fig.text(0.5, -0.02,
                 f"Verified AI articles (N = 289 substantively AI-focused; 7 off-topic excluded) across 50 journals, 1989–2026. "
                 f"Top {TOPN} venues shown; the rest are pooled. Bars split by article type.",
                 ha="center", va="top", fontsize=7.0, color="#555555")
    fig.tight_layout()
    suf = ("apa_" if APA else "") + ("color" if color else "gray")
    fig.savefig(f"figure_venues_{suf}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"figure_venues_{suf}.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote", suf)

draw(True); draw(False); print("done")
