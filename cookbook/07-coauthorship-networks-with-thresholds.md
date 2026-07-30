# 07 · Co-Authorship Networks People Can Actually Read

**Goal:** turn a verified topical corpus into a legible co-authorship network with disambiguated names, an explicit inclusion threshold, and node coloring that describes each author's work without scoring it.

**Skills used:** `swrd-database` (journal authors), `sswr-database` (its `canonical_author_id` gives conference disambiguation for free).


## Do this with Claude or Codex

Run this on a verified corpus. The two things worth insisting on in the prompt: an explicit inclusion threshold, and colors presented as a continuum rather than a score.

Copy, edit the bracketed parts, and paste:

> I'm using the Social Work Meta-Data Project (https://beperron.github.io/SocialWork-MetaData/), and I have a verified corpus of [TOPIC] items [attach or reference it]. Build a co-authorship network of the frequent authors: disambiguate names first (SSWR has canonical author IDs; for journals merge by surname plus given-name compatibility), then include only authors above an explicit frequency threshold, stated in the caption, chosen so about 20-30 authors appear. Color each node along a continuum of the author's work from commentary to empirical, with verbal labels and no numeric score, put each author's counts in a key beside the graph, make sure no nodes overlap, and outline nodes in black. Tell me which authors form connected groups and which work alone.

**What to check when it finishes.** Confirm the threshold sentence appears in the caption and that the author key's counts sum sensibly against the corpus. If you are in the network yourself, the writeup should say so.

## Under the hood — the steps the assistant runs

**Worked artifact:** [`analyses/ai-in-social-work/`](../analyses/ai-in-social-work/) contains both networks with data and the generating script.

### Step 1 — Disambiguate before counting

Journal author strings need merging (surname plus given-name compatibility: "Ryan, Joseph" = "Ryan, Joseph P."; "Zhao, Yunmeng" ≠ "Zhao, Yong"). The SSWR database ships disambiguated canonical IDs:

```sql
select paper_id, canonical_author_id, name
from sswr.paper_authors
where paper_id in (...)  -- your verified presentation ids
```

Report the resulting author universe (for example, 720 unique journal authors on 289 articles) before any filtering, and keep one author universe per analysis; mixing windows produces irreconcilable denominators.

### Step 2 — Threshold with a stated rule, not a top-N

A full network of hundreds of one-time authors is unreadable, and "top 30" silently breaks ties. Use a frequency threshold and say it in the caption: "authors with three or more verified articles (n = 22); a two-article cutoff would add 55 authors." If you build parallel networks for two venues, pick each venue's threshold to yield comparable set sizes and explain the difference.

### Step 3 — Color as a continuum, not a score

Coloring nodes by each author's mix of work (share empirical vs. commentary) reads as a description; labeling the same axis 0-to-1 reads as a grade. Use a diverging colormap with verbal anchors only ("Commentary — Study of AI — Empirical"), drop the numeric ticks, and put each author's raw counts in a key beside the graph (for example "17 (8/2/7)").

### Step 4 — Make every node visible

Spring layouts pile connected hubs on top of each other. After layout, run a collision pass:

```python
from scipy.spatial import cKDTree
for _ in range(400):
    pairs = cKDTree(P).query_pairs(MIN_DIST)
    if not pairs: break
    # push each overlapping pair apart by half the deficit
```

Outline nodes in black so pale mid-scale colors stay visible, and use dark numerals on light fills.

### Step 5 — Read the structure, then say only what it supports

Typical honest findings: one connected collaborative core amid isolates; authors specializing toward one end of the continuum rather than mixing; venue contrasts (a conference network dominated by empirical teams, a journal network spanning the full continuum). Position in a force layout carries no meaning beyond connectivity — say so in the caption. If the analysts appear in the network, disclose it.
