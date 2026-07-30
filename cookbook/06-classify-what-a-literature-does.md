# 06 · Classify What a Literature Actually Does

**Goal:** characterize a topical corpus not by its keywords but by what each item does — build and test, measure reception, or discuss — and compare that composition across venues and technological eras.

**Skills used:** `swrd-database`, `sswr-database`.


## Do this with Claude or Codex

Run this after recipe 05 (or on any verified corpus). The value is in the category definitions, so paste them into the prompt rather than letting the assistant invent its own.

Copy, edit the bracketed parts, and paste:

> I'm using the Social Work Meta-Data Project (https://beperron.github.io/SocialWork-MetaData/), and I have a verified corpus of [TOPIC] items [attach or reference it]. Classify every item by reading its abstract into exactly three categories: empirical work (builds, applies, or tests a system on data, benchmarking included; traditional statistics alone do not count), reception studies (original data on attitudes or adoption, no system run), and commentary/review. Then cut the composition by technological era, naming each era by its dominant technology and stating the boundary years as conveniences. Show the result as 100 percent stacked bars per era and flag any percentage resting on a small N. Release the full labeled list so I can check it.

**What to check when it finishes.** Read 10 of its labels yourself, especially items near the empirical/reception boundary. If you have both journal and conference corpora, ask for the side-by-side comparison; the venue gap is usually the finding.

## Under the hood — the steps the assistant runs

**Worked artifact:** [`analyses/ai-in-social-work/`](../analyses/ai-in-social-work/) applies this recipe to 289 journal articles and 180 conference presentations.

### Step 1 — Define categories by the work, not the topic

Three categories cover most technology literatures:

- **Empirical work** — builds, applies, or tests a system on data. Include benchmarking: running a model and measuring its output is hands-on work. Exclude traditional statistics used alone (logistic regression is not AI); in a clean corpus those appear only as comparison baselines.
- **Reception studies** — original data about people's attitudes, adoption, or perceptions of the technology; no system is run.
- **Commentary and review** — conceptual, ethical, educational, critical writing; no original data.

Write the boundary rules down before coding, and read every abstract; keyword proxies for "empirical" fail on exactly the interesting cases.

### Step 2 — Code both venues with the same scheme

The SSWR database's presentation abstracts code the same way journal abstracts do. Coding both venues turns a description into a comparison: SSWR is an empirical conference by design, so its composition shows what the field's researchers do, while the journal composition shows what the field publishes. The gap between them is the finding.

### Step 3 — Cut by technological era, honestly

Name each era by its dominant technology (expert systems, machine learning, generative AI) and state the boundary years as conveniences, not discoveries; earlier technologies persist inside later eras. Then compute within-era composition:

```python
waves = [("Expert systems", 1989, 1998), ("Machine learning", 1999, 2022), ("Generative AI", 2023, 2026)]
for name, lo, hi in waves:
    sub = [r for r in corpus if lo <= r["year"] <= hi]
    shares = Counter(r["label"] for r in sub)
    # report counts AND percentages; small-N eras make percentages fragile
```

Flag fragile margins explicitly (a 52% vs 46% split inside a 65-item era can flip on three recodes).

### Step 4 — Present the composition as 100% stacked bars per era, per venue

One bar per era, filled to 100%, split by category, venues side by side with aligned rows. Readers can then see in one glance both the within-venue evolution and the between-venue inversion. Mark external landmarks (for example, the ChatGPT release) as dashed lines on companion time-series charts, positioned between years, labeled as events rather than causes.

### Step 5 — Release the labels

Single-coder classification is the honest default at this scale, and its check is the release: publish the labeled list, invite double-coding, and disclose if the coder has work in the corpus.
