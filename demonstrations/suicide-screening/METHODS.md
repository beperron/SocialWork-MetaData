# Suicide-Focused Social Work Literature Corpus

## Methods and results of database retrieval, abstract screening, classification, and accuracy assessment

**Date completed:** August 2, 2026  
**Local screening model:** `qwen3.6:27b` through Ollama  
**Final screened corpus:** 2,034 records  
**Final suicide-relevant corpus:** 1,331 records

## Overview

This project identified records related to suicide in two Social Work Meta-Data Project databases, screened every candidate individually for substantive relevance, and classified the relevant records by evidence class and method. The source databases included journal articles from the Social Work Research Database (SWRD) and conference presentations from the Society for Social Work and Research database (SSWR).

The workflow had four main stages:

1. Retrieve candidate records whose titles or abstracts explicitly contained a suicide-root term.
2. Screen each candidate independently with the local Ollama model `qwen3.6:27b`.
3. Classify relevant records as Empirical or Non-empirical and, when empirical, as Quantitative, Qualitative, or Review.
4. Assess classification consistency through a 100-record blind model audit and a separate 20-record independent manual spot check, adjudicating and applying corrections.

The final corpus contains 1,331 suicide-relevant records: 1,160 Empirical and 171 Non-empirical. Among the empirical records, 915 were classified as Quantitative, 180 as Qualitative, and 65 as Review.

## Data sources

Connection and schema instructions were retrieved from the [Social Work Meta-Data Project agent guide](https://beperron.github.io/SocialWork-MetaData/llms.txt). The complete guide was verified by confirming that it included the database schemas and ended with `END OF GUIDE`. The prescribed reachability probe returned `HTTP/2 401`, which is the expected unauthenticated response and confirmed that the execution environment could reach the database host.

Queries were submitted to the project's Supabase `rpc/run_sql` endpoint as HTTPS POST requests. Each request included the public read-only authorization headers and the appropriate `Content-Profile` header. The API was queried from Python or the shell rather than through a web-page retrieval tool.

### SWRD

SWRD contains journal records from disciplinary social work journals. Following the database guide, the analysis was restricted to the recommended 1989-and-later corpus. The incomplete pre-1989 supplement was excluded. SWRD records supplied titles, abstracts, publication years, journal names, authors, DOIs, document types, and existing database research-method metadata.

The 2024–2025 SWRD years are subject to publisher-indexing lag and are incomplete. They are retained in the record-level corpus but should not be used to make unqualified trend claims.

### SSWR

SSWR contains presentations from the annual Society for Social Work and Research conference from 2005 through 2026. Records supplied titles, complete abstracts, years, canonical author identifiers, presentation formats, and database methodology labels. SSWR presentations do not have journal or DOI fields; their venue was recorded as the SSWR annual conference.

The two databases were queried separately. No SQL query joined SWRD and SSWR because their schemas and identifier types differ.

## Candidate-record construction

### Operational search rule

The high-recall candidate set was defined by a case-insensitive regular-expression match in the title or abstract:

```sql
(coalesce(title, '') || ' ' || coalesce(abstract, '')) ~* '\msuicid'
```

The word-start marker followed by the open stem `suicid` captures forms such as *suicide*, *suicidal*, and *suicidality*. This rule was selected to retrieve every record in the two databases that explicitly used a suicide-root term while avoiding automatic inclusion of nonsuicidal self-injury or self-harm records that did not substantively refer to suicide.

The database's ranked keyword-search function was also checked with multiple phrasings, including `suicide prevention`, `suicide risk`, `suicidal behavior`, and `self harm`. The first three phrasings returned records already covered by the explicit suicide-root sweep. Alternate self-harm vocabulary produced adjacent records, many of which concerned nonsuicidal self-injury rather than suicide; these were not automatically added to the main candidate set.

The rule is reproducible but does not claim to recover suicide studies that use no suicide-root term in either title or abstract.

### Pagination and metadata export

The API returns no more than 1,000 rows per call. Records were retrieved in pages of 700 to avoid truncation. Each exported record included:

- source database and source record identifier;
- year, title, and abstract;
- authors and, for SSWR, canonical author identifiers;
- journal or conference venue;
- DOI when available;
- record/document type;
- existing database method and empirical indicators;
- flags indicating whether the suicide-root match occurred in the title or abstract.

The existing database method and empirical fields were retained for provenance but were **not supplied to the Ollama model**. Primary model decisions used only the title and abstract.

### SWRD deduplication

The initial SWRD query returned 804 candidate database rows. In accordance with the database guide, possible duplicate indexing was identified using normalized title plus publication year:

```text
lowercase(remove every non-alphanumeric character from title)) + "|" + publication year
```

Eight duplicate SWRD rows were removed, leaving 796 unique SWRD papers. When duplicate rows differed, the retained row was selected by preferring the record with a DOI, then the longest abstract, and then the most complete author string. The removed source identifiers were retained in `duplicate_record_ids`.

SSWR contributed 1,238 candidate presentations. The combined candidate set therefore contained 2,034 unique records:

| Source | Candidate database rows | Unique records screened |
|---|---:|---:|
| SWRD journal articles | 804 | 796 |
| SSWR presentations | 1,238 | 1,238 |
| **Combined** | **2,042** | **2,034** |

Of the 2,034 candidates, 966 had the suicide-root term in the title and 1,068 were additional abstract-only matches. Sixty-two SWRD records had no abstract and required title-only screening.

## Screening and classification protocol

### Model and execution settings

Every candidate record was screened locally with Ollama model tag `qwen3.6:27b`. The final primary protocol was identified as `suicide-screen-v1.4-one-record-labels`.

The model was called sequentially with exactly one bibliographic record per request. Records were never batched. Primary requests used:

- temperature: `0`;
- random seed: `42`;
- context window: `4,096` tokens;
- thinking mode: disabled for the primary pass;
- structured JSON-schema output;
- title and abstract as the only substantive classification inputs.

The output schema required three decisions:

1. `is_relevant`: true or false;
2. `evidence_class`: Empirical, Non-empirical, or Not applicable;
3. `empirical_method`: Quantitative, Qualitative, Review, or Not applicable.

Each completed decision was immediately appended to a JSONL checkpoint and flushed to disk. Interrupted runs could therefore resume without repeating completed records. API or parsing failures were retried up to four times. Responses were rejected and retried if they violated the logical taxonomy.

### Relevance definition

A record was considered relevant when suicide was a central substantive focus or a distinctly analyzed component. Included topics comprised:

- suicidal ideation, attempts, deaths, and suicidality;
- suicide risk and protective factors;
- suicide prevention, intervention, postvention, screening, and assessment;
- suicide bereavement and suicide-loss survivors;
- attitudes, training, policy, or professional behavior specifically related to suicide;
- suicide as one of several outcomes when the abstract showed that it was separately analyzed or reported.

A record was considered irrelevant when suicide was only:

- background context;
- an illustrative example;
- one unexamined item in a broad list of mental-health concerns;
- a descriptive sample characteristic that was not analyzed;
- an adjacent topic such as nonsuicidal self-injury, self-harm, euthanasia, or general mental health without substantive suicide analysis.

### Evidence-class definition

Relevant records were classified as **Empirical** when they analyzed primary or secondary observations or data. This included surveys, trials, experiments, administrative or clinical data, statistical models, qualitative interviews, focus groups, observations, qualitative text, empirical case studies, and program evaluations.

Systematic reviews, meta-analyses, and scoping reviews were also defined as Empirical for this project, as requested. A review could be classified as Empirical—Review when the title or abstract explicitly identified systematic, meta-analytic, or scoping methods, or clearly described a reproducible systematic search and study-selection process.

Relevant records were classified as **Non-empirical** when they were narrative or traditional literature reviews, conceptual or theoretical articles, commentaries, editorials, book reviews, practice overviews, policy arguments without analyzed data, illustrative clinical vignettes without a research design, or protocols without results. Narrative reviews were always classified as Non-empirical. A paper described simply as a review was not assigned to the empirical Review category unless systematic methods were apparent from the title or abstract.

### Empirical-method definition

Every Empirical record was assigned exactly one method:

- **Quantitative:** numerical or statistical analyses, surveys, experiments, trials, administrative data, psychometric studies, or mixed-methods studies with a central quantitative component;
- **Qualitative:** predominantly qualitative interviews, focus groups, ethnography, observation, qualitative case analysis, or thematic/textual analysis without a central quantitative component;
- **Review:** systematic review, meta-analysis, scoping review, or another clearly systematic evidence synthesis.

The requested taxonomy did not include a Mixed-methods category. Mixed-methods records with a central quantitative component were therefore mapped to Quantitative; otherwise, the predominant method was selected.

### Missing abstracts

Sixty-two records lacked abstracts. These records were screened from their titles under a conservative forced-choice rule. If a title clearly established suicide relevance but did not provide defensible evidence of an empirical design, the record was classified as Non-empirical. Of the 62 title-only records, 54 were retained as relevant and classified as Non-empirical; eight were excluded as irrelevant.

## Primary screening results

Before accuracy-audit corrections, the model classified 1,336 records as relevant and 698 as irrelevant. The initial relevant set contained:

| Initial classification | Records |
|---|---:|
| Non-empirical | 171 |
| Empirical—Quantitative | 915 |
| Empirical—Qualitative | 185 |
| Empirical—Review | 65 |
| **All relevant** | **1,336** |

## Accuracy assessment and adjudication

### Stratified blind model audit

A reproducible stratified sample was drawn from the five primary outcome groups:

- Irrelevant;
- Relevant Non-empirical;
- Quantitative;
- Qualitative;
- Review.

Using random seed `20260802`, 20 records were sampled from each group, producing 100 audited records. Each sampled title and abstract was rescreened blindly by `qwen3.6:27b`, one record at a time, without showing the primary classification. The blind pass used the same substantive rubric but required concise rationales for relevance and evidence design.

Agreement required an exact match on the full label tuple: relevance, evidence class, and empirical method. Blind full-label agreement was 92% overall:

| Primary group | Audited | Full-label agreements | Agreement rate |
|---|---:|---:|---:|
| Irrelevant | 20 | 18 | 90% |
| Relevant Non-empirical | 20 | 19 | 95% |
| Quantitative | 20 | 19 | 95% |
| Qualitative | 20 | 16 | 80% |
| Review | 20 | 20 | 100% |
| **Total** | **100** | **92** | **92%** |

All eight disagreements underwent a third adjudication pass. The adjudicator received the title, abstract, primary decision, blind decision, and blind rationales. Adjudication used the same local model with thinking mode enabled. Six of the eight sampled records were corrected in the final data.

The model audit changed the corpus from 1,336 to 1,331 relevant records. After adjudication, the counts were 171 Non-empirical, 914 Quantitative, 181 Qualitative, and 65 Review.

The 92% value measures same-model reproducibility under blind rescreening. It is not an estimate of sensitivity, specificity, or agreement with an external human gold standard.

### Independent manual spot check

A second random sample was drawn using seed `20260803`. The 100 records from the model audit were excluded so that the second check covered new records. Four records were sampled from each of the five groups, producing 20 records. Their titles and full abstracts were independently inspected by Codex against the prespecified rubric rather than resubmitted for another primary-label model pass.

Agreement was 18 of 20 records, or 90%:

| Group | Audited | Agreements | Agreement rate |
|---|---:|---:|---:|
| Irrelevant | 4 | 3 | 75% |
| Relevant Non-empirical | 4 | 4 | 100% |
| Quantitative | 4 | 4 | 100% |
| Qualitative | 4 | 3 | 75% |
| Review | 4 | 4 | 100% |
| **Total** | **20** | **18** | **90%** |

Two additional errors were corrected:

1. **“Gender Differences in the Pathways from Sexual Abuse to Risky Sexual Behavior in Homeless Youth”** was changed from Irrelevant to Empirical—Quantitative because suicidal ideation was included in a regression model as an analyzed mechanism and had a separately reported significant association.
2. **“An Exploration of Knowledge and Attitudes about Victims or Survivors of Domestic Violence with Mental Health Disability”** was changed from Empirical—Qualitative to Irrelevant because suicide and self-harm were minor items within a broader service-needs assessment and were not distinctly analyzed.

These two changes offset one another in the overall relevant count. They increased the Quantitative count by one and reduced the Qualitative count by one.

The manual spot check is also not a definitive accuracy estimate. It included only four records per category and was performed by Codex rather than by independent subject-matter experts.

## Final results

After both audits and all adjudicated corrections, 1,331 of 2,034 candidates were retained as suicide-relevant, corresponding to 65.4% of the candidate set. A total of 703 candidates were excluded as incidental or otherwise outside the substantive relevance definition.

### Evidence class and empirical method

| Final classification | Records | Percentage of relevant records |
|---|---:|---:|
| Non-empirical | 171 | 12.8% |
| Empirical—Quantitative | 915 | 68.7% |
| Empirical—Qualitative | 180 | 13.5% |
| Empirical—Review | 65 | 4.9% |
| **All relevant** | **1,331** | **100.0%** |

Overall, 1,160 relevant records were Empirical (87.2%) and 171 were Non-empirical (12.8%). Within the 1,160 Empirical records:

- 915 were Quantitative (78.9%);
- 180 were Qualitative (15.5%);
- 65 were Reviews (5.6%).

### Results by source database

| Source | Screened | Relevant | Non-empirical | Quantitative | Qualitative | Review |
|---|---:|---:|---:|---:|---:|---:|
| SWRD | 796 | 584 | 171 | 301 | 83 | 29 |
| SSWR | 1,238 | 747 | 0 | 614 | 97 | 36 |
| **Combined** | **2,034** | **1,331** | **171** | **915** | **180** | **65** |

The relevance rate was 73.4% among SWRD candidates and 60.3% among SSWR candidates. The absence of SSWR records classified as Non-empirical reflects the decisions produced under this abstract-based protocol and the structured empirical nature of the retained conference presentations; it should not be interpreted as proof that SSWR contains no non-empirical scholarship outside this candidate set.

### Classification flow

| Processing stage | Relevant | Irrelevant | Non-empirical | Quantitative | Qualitative | Review |
|---|---:|---:|---:|---:|---:|---:|
| Primary one-by-one screen | 1,336 | 698 | 171 | 915 | 185 | 65 |
| After blind-audit adjudication | 1,331 | 703 | 171 | 914 | 181 | 65 |
| **After independent manual spot check** | **1,331** | **703** | **171** | **915** | **180** | **65** |

## Data validation

Final automated checks confirmed that:

- all 2,034 candidates were present exactly once;
- all 2,034 source record keys were unique;
- every irrelevant record had `Not applicable` for evidence class and method;
- every relevant Non-empirical record had `Not applicable` for empirical method;
- every Empirical record had exactly one permitted method;
- the relevant-only JSON contained exactly the same 1,331 record keys as the relevant subset of the complete screening JSON;
- all six model-audit corrections and both independent spot-check corrections were retained with audit provenance.

## Limitations

1. **Database scope.** This is a suicide-focused corpus within selected social work journals and SSWR conference presentations. It is not a comprehensive search of all suicide scholarship across medicine, psychology, public health, sociology, or other disciplines.
2. **Vocabulary-based candidate retrieval.** Initial recall depends on a suicide-root term appearing in the title or abstract. Relevant records expressed only through alternate terminology may be absent. Self-harm and nonsuicidal self-injury records were not automatically treated as suicide studies.
3. **Abstract-level screening.** Decisions were based on titles and abstracts rather than full texts. Some abstracts did not report enough methodological detail to distinguish systematic from narrative review methods or qualitative from mixed-methods designs.
4. **Missing abstracts.** Sixty-two records were screened from title alone. The conservative fallback likely reduces false empirical classifications but may misclassify genuinely empirical older studies as Non-empirical.
5. **Forced method categories.** The requested taxonomy did not contain Mixed-methods, case-study, or other method categories. Mixed-methods work was mapped to Quantitative when quantitative analysis was central; otherwise, the predominant method was used.
6. **Model dependence.** Primary screening and the 100-record blind audit used the same local model. The 92% audit agreement is therefore an internal-consistency measure and may overstate agreement with independent reviewers.
7. **Limited independent inspection.** The second audit inspected only 20 records and was performed by Codex, not by trained human suicide-research reviewers. Its 90% agreement should be treated as a diagnostic spot check, not a corpus-wide accuracy estimate.
8. **Stratified audit estimates.** The audits deliberately sampled equal numbers from each category. Their overall agreement rates are not prevalence-weighted estimates for the complete corpus.
9. **Recent SWRD incompleteness.** Publisher-indexing lag makes the 2024–2025 SWRD records incomplete, limiting trend analyses involving recent journal years.
10. **Residual database duplication or metadata variation.** SWRD records were deduplicated by normalized title and year as recommended, but additional nonidentical duplicate records may remain. SWRD author strings are not identity-disambiguated.

Future validation should use independent dual review by trained subject-matter experts, report interrater agreement, and adjudicate a larger probability sample. A targeted search for alternate suicide terminology could also assess retrieval sensitivity beyond the explicit `suicid*` rule.

## Reproducibility files

The principal outputs are:

- [`suicide_relevant_articles.json`](suicide_relevant_articles.json): final relevant-only corpus;
- [`suicide_abstract_screening_results.json`](suicide_abstract_screening_results.json): all 2,034 candidates and final decisions;
- [`screening_summary.json`](screening_summary.json): final counts and audit metadata;
- [`accuracy_audit.json`](accuracy_audit.json): 100-record blind model audit and adjudications;
- [`independent_manual_spot_check.json`](independent_manual_spot_check.json): 20-record independent spot check and corrections.

The workflow scripts are:

- [`../../fetch_suicide_papers.py`](../../fetch_suicide_papers.py): API retrieval, pagination, export, and SWRD deduplication;
- [`../../screen_suicide_abstracts_ollama.py`](../../screen_suicide_abstracts_ollama.py): one-record-at-a-time Ollama screening and checkpointing;
- [`../../audit_suicide_screening.py`](../../audit_suicide_screening.py): stratified blind audit and thinking-mode adjudication;
- [`../../apply_independent_spot_check.py`](../../apply_independent_spot_check.py): recording and application of the independent spot-check decisions.

## Suggested database citations

**SWRD**  
Perron, B. E., Victor, B. G., & Qi, Z. (2026). *Evolution of social work knowledge production over 35 years*. Research on Social Work Practice. https://doi.org/10.1177/10497315261416833

**SSWR**  
Perron, B. E., Victor, B. G., & Qi, Z. (2026). *AI-assisted curation of conference scholarship*. arXiv. https://doi.org/10.48550/arXiv.2603.06814

