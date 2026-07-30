import json, os, numpy as np
from collections import Counter
import matplotlib
APA = os.environ.get("APA") == "1"   # APA mode: no title baked into the image
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "DejaVu Sans"

# ---- journal composition (mlabels_v2: E / R(=S) / C) ----
recs = json.load(open("classify_records.json"))
jl = json.load(open("mlabels_v2.json"))
def jlab(i):
    l = jl[str(i)]
    return "S" if l == "R" else l
JERAS = [("Expert systems\n1989–1998", 1989, 1998),
         ("Machine learning\n1999–2022", 1999, 2022),
         ("Generative AI\n2023–2026", 2023, 2026)]
def jcount(lo, hi):
    c = Counter()
    for i, r in enumerate(recs):
        if jl[str(i)] == "X": continue
        if lo <= r["y"] <= hi: c[jlab(i)] += 1
    return c

# ---- conference composition (sswr_labels_final: E / S / C) ----
ver2 = {r["id"]: r for r in json.load(open("sswr_verified2.json"))}
cl = json.load(open("sswr_labels_final.json"))
# blank first row so ML and Generative align with the journal panel's rows
CERAS = [("Expert systems\n(no SSWR records)", None, None),
         ("Machine learning\n2005–2022", 2005, 2022),
         ("Generative AI\n2023–2026", 2023, 2026)]
def ccount(lo, hi):
    c = Counter()
    for i, l in cl.items():
        if l == "X": continue
        if lo <= ver2[i]["year"] <= hi: c[l] += 1
    return c

CATS = [("E", "Empirical AI work"), ("S", "Study of AI (reception)"), ("C", "Commentary & review")]
COL = {"E": "#2a78d6", "S": "#8e6fb0", "C": "#eb6834"}
GRY = {"E": "#3d3d3d", "S": "#9a9a9a", "C": "#d0d0d0"}

def panel(ax, eras, counter, title, cmap):
    totals = [sum(counter(lo, hi).values()) if lo is not None else 0 for _, lo, hi in eras]
    ypos = list(range(len(eras)))[::-1]
    for row, ((lab, lo, hi), t) in enumerate(zip(eras, totals)):
        if lo is None:
            continue  # blank alignment row
        c = counter(lo, hi); y = ypos[row]; left = 0
        for ck, _ in CATS:
            pct = 100.0 * c[ck] / t if t else 0
            if pct <= 0: continue
            ax.barh(y, pct, 0.6, left=left, color=cmap[ck], edgecolor="white", linewidth=1.0, zorder=3)
            if pct >= 8:
                tc = "white" if (cmap is COL or ck == "E") else "#111"
                ax.text(left + pct/2, y, f"{pct:.0f}%\n({c[ck]})", ha="center", va="center",
                        fontsize=7.2, color=tc, linespacing=1.0, zorder=4)
            left += pct
    ax.set_yticks(ypos)
    ax.set_yticklabels([f"{lab}\n(N={t})" if lo is not None else lab
                        for (lab, lo, hi), t in zip(eras, totals)], fontsize=8)
    ax.set_ylim(-0.55, len(eras) - 0.45)   # identical row positions across panels
    ax.set_xlim(0, 100); ax.set_xticks(range(0, 101, 25))
    ax.set_xticklabels([f"{v}%" for v in range(0, 101, 25)], fontsize=7.5)
    ax.set_title(title, fontsize=10, pad=6)
    for s in ["top", "right", "left"]: ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)

def draw(color=True):
    cmap = COL if color else GRY
    # NOT sharey: each panel keeps its own row labels; identical ylim (set in panel) aligns rows
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.9), dpi=300)
    panel(axes[0], JERAS, jcount, "Disciplinary journals (SWRD)", cmap)
    panel(axes[1], CERAS, ccount, "SSWR conference (presentations)", cmap)
    axes[0].set_xlabel("Share of the wave's items", fontsize=8.5)
    axes[1].set_xlabel("Share of the wave's items", fontsize=8.5)
    handles = [Rectangle((0,0),1,1,color=cmap[ck]) for ck,_ in CATS]
    labels = [f"{ck} — {nm}" for ck,nm in CATS]
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.06))
    if not APA:
        fig.suptitle("What AI Scholarship Does: Journals vs. Conference, by Technological Wave",
                     fontsize=10.5, y=1.02)
    fig.tight_layout(rect=[0, 0.02, 1, 1])
    suf = ("apa_" if APA else "") + ("color" if color else "gray")
    fig.savefig(f"figure_wave_sidebyside_{suf}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"figure_wave_sidebyside_{suf}.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote", suf)

for lab, lo, hi in JERAS: print("J", lab.replace(chr(10)," "), dict(jcount(lo,hi)))
for lab, lo, hi in CERAS:
    if lo is not None: print("C", lab.replace(chr(10)," "), dict(ccount(lo,hi)))
draw(True); draw(False); print("done")
