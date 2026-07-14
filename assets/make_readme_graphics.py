#!/usr/bin/env python3
"""Render README infographic cards in the house style (matplotlib, DejaVu Sans)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

NAVY = "#1a2744"; BLUE = "#2c6fad"; GREEN = "#1e8a4a"; ORANGE = "#d9880e"
GRAY = "#5c6b7a"; MUTED = "#8a97a5"; INK = "#2f3b4c"
PANEL_BLUE = "#eef3fa"; PANEL_GREEN = "#eaf6ee"; PANEL_AMBER = "#fdf3e3"; PANEL_GRAY = "#f4f6f8"
EDGE_BLUE = "#c9d9ec"; EDGE_GREEN = "#c4e2cf"; EDGE_AMBER = "#f0ddb8"; EDGE_GRAY = "#dde3e9"
OUT = "/Users/beperron/Documents/GitHub/SocialWork-MetaData/assets/"

def card():
    fig = plt.figure(figsize=(9.6, 9.6), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    fig.patch.set_facecolor("white")
    return fig, ax

def panel(ax, x, y, w, h, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.6",
                                fc=fc, ec=ec, lw=1.2, mutation_aspect=0.55))

def bar(ax, x, y, w, h, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.55",
                                fc=fc, ec="none", mutation_aspect=0.55))

def eyebrow(ax, text, y=95.5):
    ax.text(4, y, text, fontsize=15, fontweight="bold", color=BLUE, ha="left", va="center")

def title(ax, parts, y=89.5, size=31):
    x = 4
    for text, color in parts:
        t = ax.text(x, y, text, fontsize=size, fontweight="bold", color=color, ha="left", va="center")
        bbox = t.get_window_extent(ax.figure.canvas.get_renderer())
        x += bbox.width / ax.figure.get_window_extent().width * 100

# ============================ CARD A: what's inside ============================
fig, ax = card()
eyebrow(ax, "T W O   C O L L E C T I O N S   ·   O N E   H O M E   ·   F R E E   F O R   R E S E A R C H E R S")
title(ax, [("What's ", NAVY), ("inside", GREEN), (" the databases", NAVY)])
ax.text(4, 84, "Two large, carefully organized collections of information about social work research —\n"
               "each record holds a study's title, abstract, authors, and year, ready to explore.",
        fontsize=15.5, color=GRAY, ha="left", va="top", linespacing=1.45)

# left — SSWR
panel(ax, 4, 37, 44.5, 40, PANEL_BLUE, EDGE_BLUE)
ax.text(7, 73.2, "SSWR CONFERENCE DATABASE", fontsize=14.5, fontweight="bold", color=BLUE)
ax.text(7, 66.5, "23,793", fontsize=42, fontweight="bold", color=NAVY)
ax.text(7, 61.4, "conference presentations", fontsize=15.5, color=INK)
ax.text(7, 57.8, "from every SSWR annual conference", fontsize=12.5, color=MUTED)
for i, (n, lbl) in enumerate([("2005–2026", "22 years of meetings"),
                              ("21,209", "researchers, name-matched"),
                              ("100%", "abstracts + method labels")]):
    yy = 52 - i * 5.4
    ax.text(7, yy, n, fontsize=15, fontweight="bold", color=BLUE)
    ax.text(23, yy, lbl, fontsize=13, color=INK)

# right — SWRD
panel(ax, 51.5, 37, 44.5, 40, PANEL_GREEN, EDGE_GREEN)
ax.text(54.5, 73.2, "SWRD · JOURNAL ARTICLE DATABASE", fontsize=14.5, fontweight="bold", color=GREEN)
ax.text(54.5, 66.5, "62,602", fontsize=42, fontweight="bold", color=NAVY)
ax.text(54.5, 61.4, "research articles with abstracts", fontsize=15.5, color=INK)
ax.text(54.5, 57.8, "within 87,329 records overall, 1989–2025", fontsize=12.5, color=MUTED)
for i, (n, lbl) in enumerate([("91", "social work journals"),
                              ("100%", "labeled by study type"),
                              ("2026", "described in a new article")]):
    yy = 52 - i * 5.4
    ax.text(54.5, yy, n, fontsize=15, fontweight="bold", color=GREEN)
    ax.text(70.5, yy, lbl, fontsize=13, color=INK)

# supplement strip
panel(ax, 4, 18, 92, 15.5, PANEL_GRAY, EDGE_GRAY)
ax.text(7, 29.4, "AND A HISTORICAL SUPPLEMENT — KEPT SEPARATE, ON PURPOSE", fontsize=13.5,
        fontweight="bold", color=NAVY)
ax.text(7, 25.8, "The SWRD also preserves 23,289 much older journal records (1920–1988). They are far\n"
                 "less complete — many are missing abstracts or author details — but they are valuable\n"
                 "for historical questions. The timeline below shows how coverage changes over time.",
        fontsize=12.8, color=INK, va="top", linespacing=1.5)
ax.text(4, 12.5, "Both collections are described in peer-reviewed publications — see “How to cite these databases.”",
        fontsize=13, color=GRAY)
ax.text(4, 7.8, "SWRD: Perron, Victor, & Qi (2026), Research on Social Work Practice", fontsize=12, color=MUTED)
ax.text(4, 4.5, "SSWR: Perron, Victor, & Qi (2026), in press, J. of the Society for Social Work & Research",
        fontsize=12, color=MUTED)
fig.savefig(OUT + "whats_inside_the_databases.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ============================ CARD B: what's in a record ============================
fig, ax = card()
eyebrow(ax, "N O   F U L L   P A P E R S   ·   J U S T   T H E   E S S E N T I A L S ,   O R G A N I Z E D")
title(ax, [("Each record is like a ", NAVY), ("catalog card", GREEN)])
ax.text(4, 84, "A record isn't the paper itself — it's everything about the paper, in one tidy entry.\n"
               "Here's what one looks like (an invented example, shown the way the database stores it):",
        fontsize=15.5, color=GRAY, ha="left", va="top", linespacing=1.45)

panel(ax, 4, 21, 92, 56, "white", EDGE_GRAY)
ax.text(93, 73.5, "ILLUSTRATIVE EXAMPLE", fontsize=11.5, fontweight="bold", color=MUTED, ha="right")

rows = [
    ("TITLE", BLUE, "Kinship care and placement stability: A ten-year follow-up of\nchildren placed with relative caregivers", 71.5),
    ("AUTHORS", BLUE, "T. Rivera (Univ. of Michigan) · J. Chen (Wayne State) · M. Okafor\n(Univ. of Texas) — in the order they appeared on the paper", 62.5),
    ("PUBLISHED IN", BLUE, "Child & Family Social Work · 2019 · volume, issue, and pages", 53.8),
    ("ABSTRACT", BLUE, "“This study followed 412 children placed in kinship foster care to\nexamine placement stability over ten years. Results indicate…”\n(the full abstract is stored)", 47.3),
    ("STUDY TYPE", GREEN, "", 35.2),
    ("IMPACT", ORANGE, "Cited by 42 later articles · permanent web link (DOI) included", 28.6),
]
for label, color, content, y in rows:
    ax.text(7, y, label, fontsize=12.5, fontweight="bold", color=color)
    if content:
        ax.text(26, y, content, fontsize=13, color=INK, va="top", linespacing=1.45)
for j, chip in enumerate(["Research study", "Quantitative methods"]):
    ax.text(26 + j * 22, 35.2, chip, fontsize=12, fontweight="bold", color=GREEN, va="top",
            bbox=dict(boxstyle="round,pad=0.45", fc=PANEL_GREEN, ec=EDGE_GREEN, lw=1.1))

ax.text(4, 15.5, "Every one of the 134,411 records across both collections follows this same structure —",
        fontsize=13, color=GRAY)
ax.text(4, 11.8, "which is what makes them searchable, countable, and comparable across decades.",
        fontsize=13, color=GRAY)
fig.savefig(OUT + "whats_in_a_record.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ============================ CARD C: coverage over time ============================
fig, ax = card()
eyebrow(ax, "1 9 2 0   →   2 0 2 6   ·   H O W   F A R   B A C K   T H E   R E C O R D S   G O")
title(ax, [("What ", NAVY), ("years", GREEN), (" are covered", NAVY)])
ax.text(4, 84, "Each colored bar shows the years a collection covers. The further left, the older —\n"
               "and the thinner the surviving information gets.",
        fontsize=15.5, color=GRAY, ha="left", va="top", linespacing=1.45)

def yr(v):  # map year → x
    return 7 + 86 * (v - 1920) / 106.0

# SWRD row
ax.text(7, 68.5, "JOURNAL ARTICLES (SWRD)", fontsize=13.5, fontweight="bold", color=NAVY)
ax.text(7, 64.8, "SUPPLEMENT · 1920–1988 · 23,289 records", fontsize=12, fontweight="bold", color=GRAY)
ax.text(93, 54, "THE SWRD · 1989–2025 · 87,329 records", fontsize=12, fontweight="bold", color=GREEN, ha="right")
bar(ax, yr(1920), 57.5, yr(1988) - yr(1920) - 0.3, 5, MUTED)
bar(ax, yr(1989), 57.5, yr(2025) - yr(1989), 5, GREEN)
ax.text((yr(1920) + yr(1988)) / 2, 60, "older · less complete", fontsize=11.5, fontweight="bold",
        color="white", ha="center", va="center")
ax.text((yr(1989) + yr(2025)) / 2, 60, "carefully compiled", fontsize=11.5, fontweight="bold",
        color="white", ha="center", va="center")

# SSWR row
ax.text(7, 47.5, "CONFERENCE PRESENTATIONS (SSWR)", fontsize=13.5, fontweight="bold", color=NAVY)
ax.text(93, 43.8, "2005–2026 · 23,793 presentations · complete", fontsize=12, fontweight="bold", color=BLUE, ha="right")
bar(ax, yr(2005), 36.5, yr(2026) - yr(2005), 5, BLUE)
ax.text((yr(2005) + yr(2026)) / 2, 39, "complete", fontsize=11.5, fontweight="bold",
        color="white", ha="center", va="center")

# shared year ticks
for v in [1920, 1950, 1980, 1989, 2005, 2026]:
    ax.plot([yr(v), yr(v)], [30.5, 32], color=EDGE_GRAY, lw=1.4)
    ax.text(yr(v), 27.8, str(v), fontsize=12, color=GRAY, ha="center")

panel(ax, 4, 5.5, 92, 15, PANEL_GRAY, EDGE_GRAY)
ax.text(7, 16.4, "WHY THE SPLIT MATTERS", fontsize=13.5, fontweight="bold", color=NAVY)
ax.text(7, 12.9, "If your question is about research from 1989 onward, the SWRD gives you a thorough, well-\n"
                 "documented picture. For earlier decades, the Supplement is a helpful starting point — just\n"
                 "know that many older records are missing pieces, so counts from that era run low.",
        fontsize=12.8, color=INK, va="top", linespacing=1.5)
fig.savefig(OUT + "coverage_over_time.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("rendered 3 cards")
