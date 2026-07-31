#!/usr/bin/env python3
"""Conference figures: growth by venue, and the venue composition contrast."""
import json, os
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
D    = os.path.join(HERE, "..", "data")
FIGS = os.path.join(HERE, "..", "figures")
EMP, REC, COM = "#4a3aa7", "#eb6834", "#1baf7a"
JRN, CONF = "#4a3aa7", "#eb6834"
INK, INK2, MUT, GRID, BASE, SURF = "#18181B", "#3F3F46", "#71717A", "#E7E5E0", "#C3C2B7", "#FFFFFF"
plt.rcParams.update({"svg.fonttype": "none", "font.family": "sans-serif",
                     "font.sans-serif": ["IBM Plex Sans", "system-ui", "Arial"], "text.color": INK})

def main():
    J = json.load(open(f"{D}/ai_corpus_labeled.json"))
    C = json.load(open(f"{D}/conference_corpus_labeled.json"))
    jy = Counter(int(r["year"]) for r in J if r["year"])
    cy = Counter(int(r["year"]) for r in C if r["year"])

    # --- venue growth ---
    yrs = list(range(2005, 2027))
    fig, ax = plt.subplots(figsize=(10, 4.1)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    ax.plot(yrs, [jy.get(y, 0) for y in yrs], color=JRN, lw=2.4, marker="o", ms=4.6,
            markeredgecolor=SURF, markeredgewidth=1.2, label="Journal articles", zorder=3)
    ax.plot(yrs, [cy.get(y, 0) for y in yrs], color=CONF, lw=2.4, marker="o", ms=4.6,
            markeredgecolor=SURF, markeredgewidth=1.2, label="Conference presentations", zorder=3)
    # legend sits in the empty upper-left quadrant: it can neither clip nor collide
    ax.legend(frameon=False, fontsize=9.5, loc="upper left", labelcolor=INK2,
              handlelength=1.6, borderaxespad=0.6)
    ax.grid(axis="y", color=GRID, lw=.8, zorder=0)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(BASE); ax.spines["bottom"].set_color(BASE)
    ax.set_xticks(list(range(2005, 2027, 3)))
    ax.set_xticklabels([str(y) for y in range(2005, 2027, 3)])
    ax.tick_params(colors=MUT, labelsize=9); ax.set_xlim(2004.3, 2026.7); ax.set_ylim(0, 92)
    ax.set_ylabel("verified items", fontsize=9.5, color=INK2)
    ax.set_title("Two venues, 2005–2026", fontsize=13, fontweight="bold", loc="left", pad=12, color=INK)
    fig.savefig(f"{FIGS}/venue_growth.svg", bbox_inches="tight", pad_inches=0.28, facecolor=SURF); plt.close(fig)

    # --- venue composition ---
    fig, ax = plt.subplots(figsize=(9.6, 2.8)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    rows = [("Conference presentations", Counter(r["label"] for r in C), len(C)),
            ("Journal articles", Counter(r["label"] for r in J), len(J))]
    for i, (name, counts, n) in enumerate(rows):
        left = 0
        for lab, col in (("empirical", EMP), ("reception", REC), ("commentary", COM)):
            v = counts.get(lab, 0)
            if not v: continue
            w = 100 * v / n
            ax.barh(i, w, left=left, color=col, height=.55, zorder=3, edgecolor=SURF, linewidth=2)
            if w > 7:
                ax.text(left + w / 2, i, f"{lab}\n{v} ({w:.0f}%)", ha="center", va="center",
                        fontsize=8.6, color="#fff" if lab != "commentary" else "#06301e",
                        fontweight="bold", zorder=4)
            left += w
        ax.text(-1.5, i, f"{name}\nN = {n}", ha="right", va="center", fontsize=9.6, color=INK)
    ax.set_yticks([]); ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"])
    ax.set_ylim(-.55, 1.55); ax.set_xlim(0, 100); ax.invert_yaxis()
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE); ax.tick_params(colors=MUT, labelsize=9)
    ax.set_title("What each venue publishes", fontsize=13, fontweight="bold", loc="left", pad=12, color=INK)
    fig.savefig(f"{FIGS}/venues.svg", bbox_inches="tight", pad_inches=0.28, facecolor=SURF); plt.close(fig)
    print("wrote venue_growth.svg, venues.svg")

if __name__ == "__main__":
    main()
