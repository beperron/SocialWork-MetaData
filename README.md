# 📚 The Social Work Meta-Data Project

The Social Work Meta-Data Project maintains two curated bibliographic databases documenting the scholarly record of social work: the **Social Work Research Database (SWRD)**, covering the discipline's journal literature, and the **SSWR Conference Database**, covering presentations at the Society for Social Work and Research annual conference. Together they provide an infrastructure for scientometric analysis, literature discovery, and the study of knowledge production in the discipline.

Each database consists of structured records — title, abstract, authors and affiliations, publication venue, year, and classification labels — rather than full texts. Records link to source articles through their DOIs.

---

## 🤖 Instant access for AI assistants: the skill files

The fastest way to work with these data is to hand one of these two files to an AI assistant (Claude, ChatGPT, or any comparable system — they are platform-agnostic):

| | |
|---|---|
| 📗 **[SWRD skill file](skills/swrd-database-skill.md)** | Equips an assistant to query the journal-article database |
| 📘 **[SSWR skill file](skills/sswr-database-skill.md)** | Equips an assistant to query the conference database |

Each file is a self-contained instruction set. Once an assistant has read it, it can immediately: run any read-only analysis query, search the literature **by meaning** (with a one-time, free local setup it will walk through), and pull filtered slices of records — all with the built-in public access key. **No password, no account, and no software installation is required for querying**; every command in these files has been tested against the live databases. Simply download the file and attach or paste it into your AI assistant's conversation.

---

## At a glance

| | 📗 **The SWRD** | 📘 **SSWR Conference Database** |
|---|---|---|
| **Coverage** | Articles in disciplinary social work journals | Presentations at the SSWR annual conference |
| **Years** | 1989–2025 (plus a historical supplement) | 2005–2026, all conferences |
| **Core corpus** | 62,602 research articles with abstracts | 23,793 presentations |
| **Distinguishing feature** | Document-type and methodology classification on every abstract | Author identities resolved across all years |

---

## 📗 The Social Work Research Database (SWRD)

The SWRD contains article records from **91 disciplinary social work journals, 1989–2025**, compiled through multi-source integration and deduplication as described in Perron, Victor, and Qi (2026) — the authoritative account of the database's construction, sources, and validation.

Its analytic core is **62,602 research articles with abstracts**, each classified on two dimensions:

- 🔬 **Scientific communication** — original research contributions, distinguished from editorials, book reviews, letters, and other content
- 📊 **Methodology** — quantitative, qualitative, mixed methods, or systematic/other review

Classification was performed with a supervised language-model procedure validated against human raters (κ ≥ .85 required for each task). Surrounding this core are additional records from the same journals and period — **87,329 in all** — including articles whose abstracts were never digitized by any indexing service.

The database also stores per-article citation counts (via CrossRef) and open-access status.

### 🕰️ The SWRD Supplement

A separate historical collection holds **23,289 records from the same journal population, 1920–1988**. Coverage in this period is substantially incomplete — abstracts and author details are frequently absent, reflecting the limits of retrospective digitization rather than the publication record itself. The Supplement supports historical inquiry, with the caveat that counts from this era should be interpreted as lower bounds.

| Collection | Years | Records | Coverage |
|---|---|---|---|
| 📗 The SWRD | 1989–2025 | 87,329 | Systematically compiled and validated |
| 🕰️ The SWRD Supplement | 1920–1988 | 23,289 | Partial; interpret counts as lower bounds |

---

## 📘 The SSWR Conference Database

The SSWR Conference Database contains **all 23,793 presentations — papers, posters, and symposia — from every SSWR annual conference, 2005 through 2026**, compiled from official conference programs (Perron, Victor, & Qi, 2026, in press).

- 📄 Every record includes the full abstract and a research-method classification
- 🧑‍🤝‍🧑 The **21,209 presenting authors have been disambiguated across years**, with name variants resolved to canonical identities
- 📈 Author-level disambiguation supports longitudinal analyses of individual scholars, institutions, and topics across two decades of the field's principal research meeting

---

## 🗂️ Record structure

Records in both databases share a common structure:

| Field | Contents |
|---|---|
| 📌 **Title** | Full title |
| 🧑‍🤝‍🧑 **Authors** | All authors in order, with institutional affiliations |
| 📓 **Venue** | Journal (or conference), year, volume/issue/pages |
| 📝 **Abstract** | Full abstract, where available |
| 🏷️ **Classification** | Scientific/non-scientific; methodology category |
| 🔗 **Impact & identifiers** | Citation count; DOI |

---

## 🤝 Known limitations

- **SWRD author names are preserved as published.** Author disambiguation has not yet been performed in the SWRD; name variants (e.g., "J. Garcia" and "Jennifer Garcia") may appear as distinct entries. Article-level analyses are unaffected; author-level counts in the SWRD should be treated with caution. The SSWR database *is* disambiguated.
- **Abstract coverage is uneven.** Roughly 72% of SWRD records from 1989 onward include abstracts; older publications and smaller journals are less complete. Classification labels exist only where abstracts exist.
- **The Supplement undercounts its era**, reflecting what has survived digitization rather than the full publication record.

---

## ❓ Analytic possibilities

| Research question | What the databases support |
|---|---|
| Topical literature mapping | Retrieval of all matching articles and presentations across decades, robust to terminological variation |
| Disciplinary trends | E.g., empirical work rose from 43% of publications in the 1990s to 72% in the 2020s; mean authors per article grew from 1.85 to 3.35 |
| Scholar and institutional trajectories | Longitudinal records of SSWR presentation activity, supported by author disambiguation |
| Gap identification | Under-studied topics, populations, venues, and periods |

*A guide to working with the data directly is forthcoming. Extracts tailored to a specific research question are available on request.*

---

## 🔍 Semantic search

Both databases support retrieval by **meaning** in addition to conventional keyword matching. Each abstract has been encoded with a text-embedding model — a model that maps a passage to a numerical representation of its semantics, such that passages about the same construct receive similar representations regardless of surface vocabulary. A query for *kinship care* therefore retrieves relevant work phrased as *relative caregivers*, a class of misses to which keyword systems are systematically prone.

The embedding model was selected through benchmarking of more than a dozen candidates on this corpus (Perron et al., manuscript in preparation). Three results informed the choice:

1. Every embedding model outperformed keyword retrieval.
2. Open-weight models matched or exceeded commercial embedding services on social work literature.
3. **EmbeddingGemma** (Google; 300M parameters) offered the strongest quality-to-size ratio.

Its small size is a deliberate advantage: the model runs locally on standard hardware, at no cost, with no data transmitted to external services — relevant wherever queries or corpora are sensitive. All abstracts in both databases are already encoded, so semantic retrieval requires no additional setup.

---

## 📖 Citing the databases

**The SWRD:**

> Perron, B. E., Victor, B. G., & Qi, Z. (2026). Evolution of social work knowledge production over 35 years: An AI-enabled analysis of trends in empiricism, methodology, collaboration, citation patterns, and output. *Research on Social Work Practice*. https://doi.org/10.1177/10497315261416833

**The SSWR Conference Database:**

> Perron, B. E., Victor, B. G., & Qi, Z. (2026). AI-assisted curation of conference scholarship: Compiling, structuring, and analyzing two decades of presentations at the Society for Social Work and Research. *arXiv*. https://doi.org/10.48550/arXiv.2603.06814 — in press, *Journal of the Society for Social Work and Research*.

The SWRD's original version (1989–2013) was introduced in Perron, B. E., Victor, B. G., Hodge, D. R., Salas-Wright, C. P., Vaughn, M. G., & Taylor, R. J. (2017). Laying the foundations for scientometric research: A data science approach. *Research on Social Work Practice, 27*(7), 802–812. https://doi.org/10.1177/1049731515624966

---

## ✉️ Access and collaboration

Inquiries, collaboration proposals, and requests for data extracts are welcome.

**Brian Perron** · University of Michigan School of Social Work · **beperron@umich.edu**

<sub>Technical documentation for working with the databases directly is in the [docs folder](docs/TECHNICAL_OVERVIEW.md).</sub>
