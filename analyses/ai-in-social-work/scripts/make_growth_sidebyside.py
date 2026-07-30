import json, os, numpy as np
from collections import Counter
import matplotlib
APA = os.environ.get("APA") == "1"   # APA mode: no title/note baked into the image
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "DejaVu Sans"

recs = json.load(open("classify_records.json")); labs = json.load(open("mlabels.json"))
jy = Counter(recs[i]["y"] for i in range(len(recs)) if labs[str(i)] != "X")
# conference: use the reader-verified 180-set (non-X)
ver2 = {r["id"]: r for r in json.load(open("sswr_verified2.json"))}
flab = json.load(open("sswr_labels_final.json"))
cy = Counter(ver2[i]["year"] for i, l in flab.items() if l != "X")

years = list(range(2005, 2027))
J = [jy.get(y, 0) for y in years]
C = [cy.get(y, 0) for y in years]

JCOL = "#2a78d6"   # journal
CCOL = "#e07b39"   # conference

def draw(color=True):
    jc = JCOL if color else "#3d3d3d"
    cc = CCOL if color else "#9a9a9a"
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 3.7), dpi=300, sharey=True)
    ymax = max(max(J), max(C)) + 6
    for ax, vals, col, title, hatch26 in [
        (axes[0], J, jc, "Disciplinary journals (SWRD)", True),
        (axes[1], C, cc, "SSWR conference (presentations)", False),
    ]:
        bars = ax.bar(years, vals, color=col, edgecolor="white", linewidth=0.4, zorder=3)
        if hatch26:   # journal 2026 provisional (indexing lag); conference 2026 is complete
            bars[-1].set_alpha(0.55); bars[-1].set_hatch("///")
        # ChatGPT public release marker (Nov 30, 2022) — between the 2022 and 2023 bars
        ax.axvline(2022.5, color="#555555", linestyle="--", linewidth=0.9, zorder=2)
        ax.annotate("ChatGPT released\n(Nov 2022)", xy=(2022.5, ymax * 0.97),
                    xytext=(-4, 0), textcoords="offset points",
                    ha="right", va="top", fontsize=6.8, color="#444444", linespacing=1.1)
        ax.set_title(title, fontsize=9.5, pad=6)
        ax.set_ylim(0, ymax)
        ax.set_xticks(range(2006, 2027, 4))
        ax.tick_params(labelsize=8)
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
        ax.grid(axis="y", color="#ececec", linewidth=0.7, zorder=0)
        ax.set_xlabel("Year", fontsize=8.5)
        # annotate last bar
        ax.annotate(f"{vals[-1]}", (years[-1], vals[-1]), textcoords="offset points",
                    xytext=(0, 3), ha="center", fontsize=7.5, color=col)
    axes[0].set_ylabel("AI items per year", fontsize=9)
    if not APA:
        fig.suptitle("Artificial Intelligence in Social Work: Journal Articles vs. Conference Presentations, 2005–2026",
                     fontsize=10, y=1.02)
        fig.text(0.5, -0.04,
                 "Journal 2026 (hatched) is provisional pending indexing; the SSWR 2026 program is complete. "
                 "Both panels use the identical AI keyword net, false-positive screen, and reader verification.",
                 ha="center", va="top", fontsize=7.0, color="#555555")
    fig.tight_layout()
    suf = ("apa_" if APA else "") + ("color" if color else "gray")
    fig.savefig(f"figure_growth_sidebyside_{suf}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"figure_growth_sidebyside_{suf}.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote", suf)

print("journal total (2005+):", sum(J), "| conference total:", sum(C))
draw(True); draw(False)
print("done")
