#!/usr/bin/env python3
"""
Step 3 — regenerate the three figures on the demonstration page from the
released labels.

    pip install matplotlib
    python3 make_figures.py

Writes figures/growth.svg, figures/eras.svg, figures/outlets.svg.
"""
import json, os
from collections import Counter, defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
CORPUS = os.path.join(HERE, "..", "data", "ai_corpus_labeled.json")
FIGS   = os.path.join(HERE, "..", "figures")

# palette validated for colour-vision deficiency (all pairs, light surface)
EMP, REC, COM = "#4a3aa7", "#eb6834", "#1baf7a"   # empirical / reception / commentary
CORE, SUPP    = "#4a3aa7", "#e87ba4"              # database core / WoS supplement
INK, INK2, MUT, GRID, BASE, SURF = "#18181B", "#3F3F46", "#71717A", "#E7E5E0", "#C3C2B7", "#FFFFFF"
ERAS = [("Expert systems", 1989, 1998), ("Machine learning", 1999, 2022), ("Generative AI", 2023, 2026)]

plt.rcParams.update({"svg.fonttype": "none", "font.family": "sans-serif",
                     "font.sans-serif": ["IBM Plex Sans", "system-ui", "Helvetica Neue", "Arial"],
                     "text.color": INK})

def main():
    with open(CORPUS) as f:
        C = json.load(f)
    os.makedirs(FIGS, exist_ok=True)
    sw = Counter(int(r["year"]) for r in C if r["source"] == "swrd" and r["year"])
    wo = Counter(int(r["year"]) for r in C if r["source"] == "wos" and r["year"])

    # ---- growth ----
    yrs = list(range(1989, 2027))
    fig, ax = plt.subplots(figsize=(10, 4.3)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    b1 = [sw.get(y, 0) for y in yrs]; b2 = [wo.get(y, 0) for y in yrs]
    ax.bar(yrs, b1, color=CORE, label="SWRD database (verified)", width=.74, zorder=3)
    ax.bar(yrs, b2, bottom=b1, color=SUPP, linewidth=0,
           label="Web of Science supplement (kept separate)", width=.74, zorder=3)

    # 2026 is a partial year: the supplement was collected in July, so it covers
    # about seven months. Hatch that bar rather than drawing a projected one —
    # a forecast bar would dominate the y-scale and flatten the actual counts.
    obs26 = sw.get(2026, 0) + wo.get(2026, 0)
    MONTHS_COVERED = 7
    projected = round(obs26 * 12 / MONTHS_COVERED)
    ax.bar([2026], [obs26], width=.74, zorder=4, facecolor="none",
           edgecolor="#8C3B63", linewidth=1.1, hatch="////")
    ax.text(2026, obs26 + 2.5, "Jan–Jul\nonly", fontsize=7.8, color=MUT,
            ha="center", va="bottom", linespacing=1.3)
    ax.grid(axis="y", color=GRID, lw=.8, zorder=0)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(BASE); ax.spines["bottom"].set_color(BASE)
    ax.tick_params(colors=MUT, labelsize=9); ax.set_xlim(1988.2, 2027.2); ax.set_ylim(0, 104)
    ax.set_ylabel("verified items", fontsize=9.5, color=INK2)
    ax.legend(frameon=False, fontsize=9.2, loc="upper center", bbox_to_anchor=(0.44, 1.0),
              labelcolor=INK2, handlelength=1.5, borderaxespad=0.2)
    ax.set_title("Growth of the AI literature in social work, 1989–2026",
                 fontsize=13, fontweight="bold", loc="left", pad=38, color=INK)
    ax.text(0, 1.04, f"2024–25 database indexing is incomplete · 2026 is supplement-only, covering "
                     f"January–July only\n"
                     f"That partial year holds {obs26} articles in seven months — a pace of roughly "
                     f"{projected} across a full year",
            transform=ax.transAxes, fontsize=8.8, color=MUT, va="bottom", ha="left", linespacing=1.5)
    fig.savefig(f"{FIGS}/growth.svg", bbox_inches="tight", pad_inches=0.28, facecolor=SURF); plt.close(fig)

    # ---- eras ----
    fig, ax = plt.subplots(figsize=(9.6, 3.4)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    for i, (name, lo, hi) in enumerate(ERAS):
        sub = [r for r in C if r["year"] and lo <= int(r["year"]) <= hi]
        counts = Counter(r["label"] for r in sub); n = len(sub); left = 0
        for lab, col in (("empirical", EMP), ("reception", REC), ("commentary", COM)):
            v = counts.get(lab, 0)
            if not v: continue
            w = 100 * v / n
            ax.barh(i, w, left=left, color=col, height=.6, zorder=3, edgecolor=SURF, linewidth=2)
            if w > 8:
                ax.text(left + w / 2, i, f"{lab}\n{v} ({w:.0f}%)", ha="center", va="center",
                        fontsize=8.4, color="#fff" if lab != "commentary" else "#06301e",
                        fontweight="bold", zorder=4)
            left += w
        ax.text(-1.5, i, f"{name}\n{lo}–{hi}  ·  N={n}", ha="right", va="center", fontsize=9.4, color=INK)
    ax.set_yticks([]); ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"])
    ax.set_ylim(-.6, 2.5); ax.set_xlim(0, 100); ax.invert_yaxis()
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE); ax.tick_params(colors=MUT, labelsize=9)
    ax.set_title("What the literature does, by technological era",
                 fontsize=13, fontweight="bold", loc="left", pad=12, color=INK)
    fig.savefig(f"{FIGS}/eras.svg", bbox_inches="tight", pad_inches=0.28, facecolor=SURF); plt.close(fig)

    # ---- outlets ----
    jc = Counter(r["journal"] for r in C if r.get("journal"))
    src = defaultdict(Counter)
    for r in C:
        if r.get("journal"): src[r["journal"]][r["source"]] += 1
    top = jc.most_common(10)
    fig, ax = plt.subplots(figsize=(9.4, 4.6)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    names = [t[0] for t in top][::-1]
    a = [src[j]["swrd"] for j, _ in top][::-1]; b = [src[j]["wos"] for j, _ in top][::-1]
    yy = list(range(len(names)))
    ax.barh(yy, a, color=CORE, height=.66, zorder=3, label="SWRD database")
    ax.barh(yy, b, left=a, color=SUPP, linewidth=0, height=.66, zorder=3, label="WoS supplement")
    for i, (x1, x2) in enumerate(zip(a, b)):
        ax.text(x1 + x2 + .8, i, str(x1 + x2), va="center", fontsize=9, color=INK2, fontweight="bold")
    ax.set_yticks(yy); ax.set_yticklabels(names, fontsize=9.2, color=INK)
    ax.grid(axis="x", color=GRID, lw=.8, zorder=0)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE); ax.tick_params(colors=MUT, labelsize=9)
    ax.set_xlim(0, 66); ax.legend(frameon=False, fontsize=9, loc="lower right", labelcolor=INK2)
    ax.set_title(f"Where this work appears — top 10 outlets of {len(jc)}",
                 fontsize=13, fontweight="bold", loc="left", pad=12, color=INK)
    fig.savefig(f"{FIGS}/outlets.svg", bbox_inches="tight", pad_inches=0.28, facecolor=SURF); plt.close(fig)
    print("wrote growth.svg, eras.svg, outlets.svg")

if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# Co-authorship network (run separately: python3 make_network.py)
# ---------------------------------------------------------------------------
