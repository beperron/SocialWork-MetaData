#!/usr/bin/env python3
"""
Regenerate the three figures on the demonstration page from the released labels.

    pip install matplotlib
    python3 make_figures.py

Reads  ../data/stats.json   (written by compute_stats.py — run that first)
Writes ../figures/growth.svg, composition.svg, audit.svg
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
STATS = os.path.join(HERE, "..", "data", "stats.json")
FIGS = os.path.join(HERE, "..", "figures")

# Palette: separable by hue and by lightness, so it survives greyscale printing
# and the common colour-vision deficiencies.
QT, QL, RV = "#0F5257", "#4C9F8A", "#D4A24C"      # quantitative / qualitative / review
NON, IRR = "#7A6A8F", "#C9C7C0"                    # non-empirical / screened out
SWRD, SSWR = "#0F5257", "#C97B3E"                  # journals / conference
INK, INK2, MUT, GRID, BASE, SURF = "#18181B", "#3F3F46", "#71717A", "#E7E5E0", "#C3C2B7", "#FFFFFF"

plt.rcParams.update({
    "svg.fonttype": "none",
    "font.family": "sans-serif",
    "font.sans-serif": ["IBM Plex Sans", "system-ui", "Helvetica Neue", "Arial"],
    "text.color": INK,
})


def frame(ax, yaxis=True):
    if yaxis:
        ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(BASE)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(colors=MUT, labelsize=9)


def growth(S):
    """Relevant records per year, the two venues stacked."""
    yrs = list(range(1989, 2027))
    a = [S["relevant_by_year"]["SWRD"].get(str(y), 0) for y in yrs]
    b = [S["relevant_by_year"]["SSWR"].get(str(y), 0) for y in yrs]

    fig, ax = plt.subplots(figsize=(10, 4.3))
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    ax.bar(yrs, a, color=SWRD, width=0.74, zorder=3, label="SWRD journal articles")
    ax.bar(yrs, b, bottom=a, color=SSWR, width=0.74, zorder=3,
           label="SSWR conference presentations")

    # The right-hand edge is not comparable across venues and must be marked.
    # SWRD 2024-25 lags publisher indexing; SSWR 2026 is a complete meeting.
    # The band is carried in the legend rather than annotated in place: the bars
    # it covers are the tallest on the chart, so there is no room beside them.
    band = ax.axvspan(2023.5, 2025.5, color="#F0E6D8", zorder=1,
                      label="SWRD indexing incomplete — lower bound")

    frame(ax)
    ax.set_xlim(1988.2, 2026.8)
    ax.set_ylim(0, 138)
    ax.set_ylabel("suicide-relevant records", fontsize=9.5, color=INK2)
    ax.legend(frameon=False, fontsize=9.5, loc="upper left", labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "growth.svg"), format="svg",
                facecolor=SURF, bbox_inches="tight")
    plt.close(fig)


def composition(S):
    """What the 2,034 screened candidates became, whole corpus and by venue."""
    rows = [
        ("Combined", S["outcome_groups"], S["screened_records"]),
        ("SSWR conference", S["by_source"]["SSWR"], S["by_source"]["SSWR"]["screened"]),
        ("SWRD journals", S["by_source"]["SWRD"], S["by_source"]["SWRD"]["screened"]),
    ]
    segs = [("Quantitative", QT), ("Qualitative", QL), ("Review", RV),
            ("Non-empirical", NON), ("Screened out as incidental", IRR)]

    fig, ax = plt.subplots(figsize=(10, 3.1))
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)

    for i, (label, counts, total) in enumerate(rows):
        left = 0
        for name, colour in segs:
            v = counts[name] if name != "Screened out as incidental" else counts["Irrelevant"]
            if not v:
                continue
            pct = 100 * v / total
            ax.barh(i, pct, left=left, color=colour, height=0.62, zorder=3)
            # Only label a slice wide enough to hold the text.
            if pct >= 6:
                ax.text(left + pct / 2, i, f"{v:,}", ha="center", va="center",
                        fontsize=9.5, color="#FFFFFF" if colour in (QT, NON) else INK,
                        fontweight="bold")
            left += pct

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{r[0]}\n{r[2]:,} screened" for r in rows],
                       fontsize=9.5, color=INK2, linespacing=1.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("percent of screened candidates", fontsize=9.5, color=INK2)
    frame(ax, yaxis=False)
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    ax.legend(handles=[Patch(facecolor=c, label=n) for n, c in segs],
              frameon=False, fontsize=9, ncol=5, loc="upper center",
              bbox_to_anchor=(0.5, -0.28), labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "composition.svg"), format="svg",
                facecolor=SURF, bbox_inches="tight")
    plt.close(fig)


def audit(S):
    """Agreement rates from the two checks, side by side, by outcome group."""
    groups = ["Irrelevant", "Relevant Non-empirical", "Quantitative", "Qualitative", "Review"]
    blind = S["audit"]["blind_model_audit"]["group_statistics"]
    spot = S["audit"]["independent_manual_spot_check"]["group_statistics"]
    b = [100 * blind[g]["full_label_agreement_rate"] for g in groups]
    s = [100 * spot[g]["agreement_rate"] for g in groups]
    bn = [blind[g]["sampled"] for g in groups]
    sn = [spot[g]["sampled"] for g in groups]

    x = range(len(groups))
    fig, ax = plt.subplots(figsize=(10, 3.6))
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    ax.bar([i - 0.2 for i in x], b, width=0.38, color=QT, zorder=3,
           label="Blind model re-screen (20 per group)")
    ax.bar([i + 0.2 for i in x], s, width=0.38, color=RV, zorder=3,
           label="Independent manual check (4 per group)")

    for i, (v, n) in enumerate(zip(b, bn)):
        ax.text(i - 0.2, v + 1.6, f"{v:.0f}%", ha="center", fontsize=9, color=INK2)
    for i, (v, n) in enumerate(zip(s, sn)):
        ax.text(i + 0.2, v + 1.6, f"{v:.0f}%", ha="center", fontsize=9, color=INK2)

    ax.set_xticks(list(x))
    ax.set_xticklabels([g.replace("Relevant ", "Relevant\n") for g in groups],
                       fontsize=9.5, color=INK2, linespacing=1.4)
    ax.set_ylim(0, 116)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("full-label agreement", fontsize=9.5, color=INK2)
    frame(ax)
    # Below the axes, not inside: every group is at 75% or higher, so an
    # in-plot legend lands on top of a bar wherever it is placed.
    ax.legend(frameon=False, fontsize=9.5, ncol=2, loc="upper center",
              bbox_to_anchor=(0.5, -0.20), labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "audit.svg"), format="svg",
                facecolor=SURF, bbox_inches="tight")
    plt.close(fig)


def main():
    with open(STATS) as f:
        S = json.load(f)
    os.makedirs(FIGS, exist_ok=True)
    growth(S)
    composition(S)
    audit(S)
    print("wrote growth.svg, composition.svg, audit.svg")


if __name__ == "__main__":
    main()
