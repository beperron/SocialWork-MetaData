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

def card(w, h):
    fig = plt.figure(figsize=(w, h), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    fig.patch.set_facecolor("white")
    return fig, ax

def panel(ax, x, y, w, h, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.6",
                                fc=fc, ec=ec, lw=1.2, mutation_aspect=0.55))

def eyebrow(ax, text, y=95.5):
    ax.text(4, y, text, fontsize=15, fontweight="bold", color=BLUE,
            ha="left", va="center", fontfamily="DejaVu Sans")

def title(ax, parts, y=89.5, size=31):
    x = 4
    for text, color in parts:
        t = ax.text(x, y, text, fontsize=size, fontweight="bold", color=color,
                    ha="left", va="center", fontfamily="DejaVu Sans")
        bbox = t.get_window_extent(ax.figure.canvas.get_renderer())
        x += bbox.width / ax.figure.get_window_extent().width * 100

# ============================== CARD 1: what's inside ==============================
fig, ax = card(9.6, 9.6)
eyebrow(ax, "T W O   D A T A B A S E S   ·   O N E   H O M E   ·   B U I L T   F O R   R E S E A R C H E R S")
title(ax, [("What's ", NAVY), ("inside", GREEN), (" the databases", NAVY)])
ax.text(4, 84, "Two curated collections covering social work scholarship — every record has its title,\n"
               "abstract (when available), authors, and the links between them, ready to search.",
        fontsize=15.5, color=GRAY, ha="left", va="top", linespacing=1.45)

# left panel — SSWR
panel(ax, 4, 37, 44.5, 40, PANEL_BLUE, EDGE_BLUE)
ax.text(7, 73.2, "SSWR CONFERENCE DATABASE", fontsize=14.5, fontweight="bold", color=BLUE)
ax.text(7, 66.5, "23,793", fontsize=42, fontweight="bold", color=NAVY)
ax.text(7, 61.2, "conference presentations", fontsize=15.5, color=INK)
for i, (n, lbl) in enumerate([("2005–2026", "every annual conference"),
                              ("21,209", "researchers, name-matched"),
                              ("100%", "abstracts + method labels")]):
    yy = 54.5 - i * 5.6
    ax.text(7, yy, n, fontsize=15, fontweight="bold", color=BLUE)
    ax.text(23, yy, lbl, fontsize=13, color=INK)

# right panel — SWRD
panel(ax, 51.5, 37, 44.5, 40, PANEL_GREEN, EDGE_GREEN)
ax.text(54.5, 73.2, "SWRD · JOURNAL ARTICLE DATABASE", fontsize=14.5, fontweight="bold", color=GREEN)
ax.text(54.5, 66.5, "87,329", fontsize=42, fontweight="bold", color=NAVY)
ax.text(54.5, 61.2, "journal article records, 1989–2025", fontsize=15.5, color=INK)
for i, (n, lbl) in enumerate([("91", "social work journals"),
                              ("62,602", "research articles w/ abstracts"),
                              ("1989–2025", "described in a 2026 article")]):
    yy = 54.5 - i * 5.6
    ax.text(54.5, yy, n, fontsize=15, fontweight="bold", color=GREEN)
    ax.text(70.5, yy, lbl, fontsize=13, color=INK)

# SWRD vs Supplement strip
panel(ax, 4, 16.2, 92, 17.8, PANEL_GRAY, EDGE_GRAY)
ax.text(7, 30.4, "PLUS A HISTORICAL SUPPLEMENT — OLDER, FAR LESS COMPLETE, BUT PRESERVED",
        fontsize=13.5, fontweight="bold", color=NAVY)
bar_x, bar_w, bar_y, bar_h = 7, 86, 24.6, 3.4
prim_w = bar_w * 87329 / 110618
ax.add_patch(FancyBboxPatch((bar_x, bar_y), prim_w, bar_h, boxstyle="round,pad=0,rounding_size=0.55",
                            fc=GREEN, ec="none", mutation_aspect=0.55))
ax.add_patch(FancyBboxPatch((bar_x + prim_w + 0.4, bar_y), bar_w - prim_w - 0.4, bar_h,
                            boxstyle="round,pad=0,rounding_size=0.55", fc=MUTED, ec="none", mutation_aspect=0.55))
ax.text(bar_x + 1.5, bar_y + bar_h / 2, "THE SWRD  ·  87,329 records (1989–2025)",
        fontsize=12.5, fontweight="bold", color="white", va="center")
ax.text(bar_x + prim_w + 0.4 + (bar_w - prim_w - 0.4) / 2, bar_y + bar_h / 2, "23,289",
        fontsize=12, fontweight="bold", color="white", va="center", ha="center")
ax.text(7, 20.6, "Gray = the SWRD Supplement: journal records from 1920–1988. Many are missing abstracts or details,\n"
                 "so treat them as a starting point for historical questions rather than a complete record.",
        fontsize=12.2, color=INK, va="top", linespacing=1.45)

# footer
ax.text(4, 11.6, "Both databases are described in peer-reviewed publications — see “How to cite” in the README.",
        fontsize=13, color=GRAY)
ax.text(4, 7.2, "SWRD: Perron, Victor, & Qi (2026), Research on Social Work Practice", fontsize=12, color=MUTED)
ax.text(4, 4.0, "SSWR: Perron, Victor, & Qi (2026), in press, J. of the Society for Social Work & Research",
        fontsize=12, color=MUTED)
fig.savefig("/Users/beperron/Documents/GitHub/SocialWork-MetaData/assets/whats_inside_the_databases.png",
            bbox_inches="tight", facecolor="white")
plt.close(fig)

# ============================== CARD 2: how to use ==============================
fig, ax = card(9.6, 9.6)
eyebrow(ax, "G E T T I N G   S T A R T E D   ·   F R E E   ·   N O   S P E C I A L   S O F T W A R E   T O   B R O W S E")
title(ax, [("Three ways to ", NAVY), ("use", GREEN), (" the data", NAVY)])
ax.text(4, 84, "Pick the path that matches your comfort level — they all reach the same two databases.",
        fontsize=15.5, color=GRAY, ha="left", va="top")

ways = [
    (PANEL_BLUE, EDGE_BLUE, BLUE, "1 · ASK & BROWSE", "No coding",
     "Ask for a slice of the data —\n“all SWRD articles on kinship\ncare since 2015” — and get a\nspreadsheet you can open in\nExcel. Any collaborator with\naccess can pull this for you\nin minutes."),
    (PANEL_GREEN, EDGE_GREEN, GREEN, "2 · SEARCH BY MEANING", "Plain questions",
     "Type a question in everyday\nlanguage. The built-in AI search\nfinds studies about your idea\neven when the authors used\ncompletely different words —\nno more guessing keywords."),
    (PANEL_AMBER, EDGE_AMBER, ORANGE, "3 · ANALYZE & BUILD", "For data-savvy folks",
     "Connect R, Python, SPSS, or a\nweb app directly to the live\ndatabase. Ready-made views\n(publication trends, author\nstats, collaborations) mean\nthe common questions are\none query away."),
]
for i, (fc, ec, accent, head, tag, body) in enumerate(ways):
    x = 4 + i * 31.4
    panel(ax, x, 33, 29.2, 44, fc, ec)
    ax.text(x + 2.5, 73, head, fontsize=14, fontweight="bold", color=accent)
    ax.text(x + 2.5, 69, tag, fontsize=12.5, fontweight="bold", color=NAVY,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=ec, lw=1))
    ax.text(x + 2.5, 64.5, body, fontsize=12.8, color=INK, va="top", linespacing=1.5)

panel(ax, 4, 14.5, 92, 14, PANEL_GRAY, EDGE_GRAY)
ax.text(7, 24.7, "EVERYTHING STAYS SIMPLE ON PURPOSE", fontsize=13.5, fontweight="bold", color=NAVY)
ax.text(7, 21.2, "One database in the cloud · two clearly named collections (sswr and swrd) · no website to maintain,\n"
                 "no accounts to manage — and the AI search runs on a small, free model (Google's EmbeddingGemma)\n"
                 "that an ordinary laptop can handle.",
        fontsize=13.2, color=INK, va="top", linespacing=1.5)
ax.text(4, 8.5, "Questions or access requests: Brian Perron · beperron@umich.edu", fontsize=12.5, color=MUTED)
fig.savefig("/Users/beperron/Documents/GitHub/SocialWork-MetaData/assets/three_ways_to_use.png",
            bbox_inches="tight", facecolor="white")
plt.close(fig)
print("rendered 2 cards")
