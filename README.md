# 📚 The Social Work Research Databases

**A plain-language guide. No technical background needed.**

This page describes two large, carefully organized collections of information about social work research — one for **journal articles**, one for **conference presentations**. They were built for social work researchers, educators, and students.

> [!NOTE]
> **First time on GitHub?** GitHub is simply a website where researchers share their work. This page is just a document to read — nothing to install, no account needed.

> [!TIP]
> **Two words worth knowing.**
> 📇 A **database** is an organized, searchable collection of information — like a library's card catalog, but electronic.
> 🗂️ A **record** is one entry in that catalog: the key information *about* one study (title, abstract, authors, year) — not the full paper itself.

---

## At a glance

| | 📗 **The SWRD** | 📘 **SSWR Conference Database** |
|---|---|---|
| **What it covers** | Articles from social work journals | Presentations at the SSWR annual conference |
| **Years** | 1989–2025 (plus an older supplement) | 2005–2026, every conference |
| **Size** | 62,602 research articles with abstracts | 23,793 presentations |
| **Special strength** | Every article labeled by study type | Every researcher name-matched across years |

---

## 📗 The Social Work Research Database (SWRD)

The SWRD holds records for articles published in **91 social work journals from 1989 through 2025** — the journals our discipline itself publishes, from *Social Work* to the *British Journal of Social Work* to *Research on Social Work Practice*.

**At its heart are 62,602 research articles with abstracts.** Every one of them carries two labels:

- 🔬 **Is it a research study?** — as opposed to an editorial, book review, or letter
- 📊 **What kind?** — quantitative (numbers and statistics), qualitative (interviews, observations, texts), mixed methods, or a review that synthesizes other studies

The labels were applied by a carefully supervised computer program and accepted only after its judgments were checked against trained human readers and found to agree at a high level.

Around those labeled articles sit more records from the same journals and years — **87,329 in all** — including articles whose abstracts were never digitized.

The SWRD, and exactly how it was assembled, is fully described in a 2026 article in *Research on Social Work Practice* — the citation is at the bottom of this page. That article is the authoritative account of where every record came from.

### 🕰️ The SWRD Supplement — a window into the field's past

Alongside the SWRD sits a separate historical collection: **23,289 records from the same journals, reaching back to 1920**.

These older records are kept apart for an honest reason: **they are much less complete.** Many are missing abstracts or author details — not because anyone was careless, but because that information was never digitized. They remain genuinely useful for historical questions (*when did our journals first publish about foster care? about evidence-based practice?*). Just treat counts from those early decades as a floor, not a full accounting.

| Collection | Years | Records | Completeness |
|---|---|---|---|
| 📗 The SWRD | 1989–2025 | 87,329 | Carefully compiled |
| 🕰️ The SWRD Supplement | 1920–1988 | 23,289 | Partial — use with care |

---

## 📘 The SSWR Conference Database

The second collection covers the **Society for Social Work and Research annual conference** — the field's largest research meeting. It holds **all 23,793 presentations from every conference, 2005 through 2026**: papers, posters, and symposia alike.

- 📄 **Every record has the full abstract** and a research-method label
- 🧑‍🤝‍🧑 **All 21,209 presenters have been name-matched across years** — if someone presented as "M. Smith" in 2008 and "Mary Smith" in 2019, the database knows they're the same person
- 📈 That means you can follow a scholar's, a topic's, or a school's full trajectory across two decades of conferences

---

## 🗂️ What one record contains

Every record in both collections follows the same tidy structure:

| Field | What it holds |
|---|---|
| 📌 **Title** | The study's full title |
| 🧑‍🤝‍🧑 **Authors** | Every author, in order, with their institution |
| 📓 **Where & when** | Journal (or conference), year, volume/issue/pages |
| 📝 **Abstract** | The full abstract, when one exists |
| 🏷️ **Study type** | Research study or not; quantitative / qualitative / mixed / review |
| 🔗 **Impact & link** | How often it's been cited, and its permanent web link (called a **DOI**) |

The full papers themselves are not stored — records describe and point to them, the way a catalog card points to a book.

---

## 🤝 A few honest notes

Every real dataset has quirks. These are the ones worth knowing, in plain terms:

- **SWRD author names appear exactly as the journals printed them.** No name-matching has been done there yet — "J. Garcia" and "Jennifer Garcia" may be separate entries even if they're the same person. Counting *articles* is reliable; counting *unique people* is not, yet. (The SSWR collection **is** name-matched.)
- **Not every SWRD article has an abstract.** About seven in ten records from 1989 onward include one; older and smaller journals are thinner. Study-type labels exist only where an abstract exists.
- **The Supplement undercounts its era.** Records from 1920–1988 reflect what survived digitization, not everything that was published.

---

## ❓ What kinds of questions can these answer?

| If you're wondering… | The databases can show you… |
|---|---|
| *What has the field published on kinship care?* | Every matching article and presentation, across decades — including ones that used different wording |
| *Is social work research becoming more empirical?* | Yes — research studies rose from 43% of publications in the 1990s to 72% in the 2020s, one of many trends you can trace |
| *How has a scholar's work evolved?* | Their full run of SSWR presentations, year by year |
| *What's understudied?* | Topics, populations, and journals where the record runs thin — the gaps are as visible as the trends |

*A friendly, step-by-step guide to using the data yourself is coming soon. In the meantime, a slice of the data for your question is easy to share — see the contact below.*

---

## 🔍 The search tool inside, gently explained

Both collections include a newer kind of search that finds studies by their **meaning**, not just their exact words.

> [!TIP]
> **What is an "embedding model"?** A small computer program that *reads* text and gives it a kind of **meaning fingerprint**. Two passages about the same idea get similar fingerprints — even if they share no words. That's the whole trick. It never writes anything, never chats, and never makes anything up. It only reads and compares.

**Why it matters:** traditional keyword search — what most library databases still use — matches only the exact words you type. Search *"kinship care"* and it can silently miss an excellent study that said *"relative caregivers"* instead. Meaning-based search finds it anyway, because it recognizes the idea, not just the letters.

**How we chose the tool.** Before settling on one, we tested more than a dozen of these programs head-to-head on tens of thousands of social work abstracts. Three findings, simply put:

1. 🥇 **Every meaning-based tool beat old-style keyword search** — none of them did worse.
2. 💵 **The free tools matched or outperformed the paid subscription services** on social work literature.
3. 🪶 **The best fit was also one of the smallest: EmbeddingGemma**, a free tool released by Google.

**About EmbeddingGemma, in plain terms.** Its size is described as "300M" — 300 million internal settings — which sounds enormous but is *tiny* in this field (popular chatbots are thousands of times larger). Being tiny is the point:

- 💻 It runs on an ordinary laptop — no special equipment, no subscription
- 🔒 It runs privately — nothing is sent to any company
- 💰 It is free — permanently

Every abstract in both collections has already been read and fingerprinted this way, so meaning-based search is simply **ready, built in**.

---

## 📖 How to cite these databases

If these data contribute to your work, please cite the article describing the collection you used.

**For the SWRD (journal articles):**

> Perron, B. E., Victor, B. G., & Qi, Z. (2026). Evolution of social work knowledge production over 35 years: An AI-enabled analysis of trends in empiricism, methodology, collaboration, citation patterns, and output. *Research on Social Work Practice*. https://doi.org/10.1177/10497315261416833

**For the SSWR Conference Database:**

> Perron, B. E., Victor, B. G., & Qi, Z. (2026). AI-assisted curation of conference scholarship: Compiling, structuring, and analyzing two decades of presentations at the Society for Social Work and Research. *arXiv*. https://doi.org/10.48550/arXiv.2603.06814 — in press, *Journal of the Society for Social Work and Research*.

*(The SWRD's original version, covering 1989–2013, was introduced in Perron et al., 2017, Research on Social Work Practice, 27(7), 802–812.)*

---

## ✉️ Questions, ideas, and access

This is a living resource, and collaboration is genuinely welcome — whether you want to explore the data, request a slice of it for a project, or talk through whether it fits a study you have in mind.

**Brian Perron** · University of Michigan School of Social Work · **beperron@umich.edu**

<sub>Technically inclined? Documentation for working with the databases directly lives in the [docs folder](docs/TECHNICAL_OVERVIEW.md).</sub>
