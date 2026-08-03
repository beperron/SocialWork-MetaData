# Independent verification of the duplicate-credit fix

The gates used cached Crossref, so cached Crossref cannot confirm them — it would
be the same source marking its own work. This checks the proposal against sources
it never consulted.

## 1. Census against OpenAlex — all 4,855 groups, not a sample

OpenAlex runs its own author disambiguation and assigns persistent author IDs, so
"are these two credits one person" is a question it answers independently.

Author lists retrieved for **2,868 of 2,885** affected DOIs (99.4%).

| result | groups | share |
|---|---:|---:|
| confirmed — exactly one OpenAlex person carries this surname | 4,772 | 98.3% |
| surname absent from OpenAlex's list | 45 | 0.9% |
| no OpenAlex record | 27 | 0.6% |
| apparent contradiction | 10 | 0.2% |

**All 10 apparent contradictions are artifacts of the check, not the patch.** The
comparison tests whether the group's surname tokens are a subset of an OpenAlex
author's, which over-matches compound surnames:

| group key | OpenAlex names that falsely matched |
|---|---|
| `jones` | Sharon D. Jones-Eversley |
| `tripodi` | Miriam Potocky-Tripodi |
| `smith` | Tracy Smith-Carrier |
| `boehm` | Esther Boehm-Tabib |
| `romero` | Melissa Romero Williams |
| `martinez-martinez` | Javier Reyes-Martínez |

The `de marco` case is the interesting one and it vindicates the grouping. OpenAlex
lists **Molly De Marco and Allison C. De Marco** on paper 119542, and SWRD carries
each of them twice. The fix produces two separate groups — `marco` and `de marco` —
and merges within each. Two people in, two people out.

Of the 45 unmatched, 43 are merges of byte-identical strings, safe whatever the
external source says. The residual 2 are bare surnames folded into the same full
name on the same paper (`Katenga-Kaunda`, `Gusak`).

### An unrelated finding worth recording

The first pass reported 223 unmatched and 1 contradiction, all spurious: OpenAlex
writes `Osei‐Hwedie`, `Phillips‐Fein` and `D’Andrade` with U+2010 hyphen and a
curly apostrophe, which ASCII comparison misses. Normalising those brought 178
groups into agreement. This is a comparison bug, not a data bug, but the same class
of thing would bite any future name matching in this repo.

## 2. 74.7% need no external source at all

3,627 of the 4,855 groups merge credits that are **the same string** once case and
punctuation are stripped — `Zanis, David A.` with `Zanis, David A`, `John A. Kayser`
with `John A Kayser`. No lookup can make those two people.

The 1,228 groups where the renderings genuinely differ are where external evidence
actually matters, and that is what the next check samples.

## 3. Publisher bylines — 16 drawn at random from those 1,228

Read off each journal's own article page, seed `20260803`.

| paper | kept ← dropped | publisher byline | |
|---|---|---|:-:|
| 46974 | `Roux, Adrie` ← ×2 | Julita Van der Westhuizen, **Adrie Roux**, Corinne Strydom | ✓ |
| 61435 | `Jacobs, Leone` ← ×2 | **Leoné Jacobs**, Stephan Geyer | ✓ |
| 100662 | `Edith Abrahams` ← `Abrahams` | **Edith Abrahams**, Coen Reynolds | ✓ |
| 100112 | `Siv Oltedal` ← `Oltedal` | **Siv Oltedal** | ✓ |
| 39174 | `Williams, Marili` ← ×2 | **Marili Williams** | ✓ |
| 88005 | `Rebecca Bowen` ← `Bowen R.` | Stoddard-Dare, DeBoth, Wendland, Suder, Niederriter, **Rebecca Bowen**, Dugan, Tedor | ✓ |
| 100138 | `Eulalia Temba` ← `Temba` | Anne Ryen, **Eulalia Temba**, Edmund C.S. Matotay | ✓ |
| 88032 | `Deborah Gioia` ← `Gioia D.` | Joan Pittman and **Deborah Gioia** | ✓ |
| 72858 | `Sara Hultqvist` ← `Hultqvist S.` | Caswell, Gjersøe, **Sara Hultqvist**, Oltedal | ✓ |
| 50503 | `Strydom, Herman` ← ×2 | Korita Olivier, **Herman Strydom** | ✓ |
| 42508 | `Green, Sulina` ← ×2 | **Sulina Green** | ✓ |
| 46989 | `Wade, Barbara` ← ×2 | **Barbara Wade** and Rinie Schenck | ✓ |
| 59122 | `Bhagwan, Raisuyah` ← ×2 | Roxanne Groger, **Raisuyah Bhagwan** | ✓ |
| 100769 | `Warwick, Danelia` ← `Warwick` | **Danelia Warwick**, Marichen Van der Westhuizen, Nicky Alpaslan | ✓ |
| 100716 | `H Strydom` ← `Strydom` | **H Strydom** | ✓ |
| 100137 | `Johans Tveit Sandvin` ← `Sandvin` | **Johans Tveit Sandvin**, Frode Bjørgo, Gunn Strand Hutchinson | ✓ |

**16 of 16 correct.** In every case the byline names the person once, and SWRD
credits them two or three times.

On its own a clean 16 supports a true rate of at least 80.6% (Wilson 95% lower
bound) — a small sample cannot do better than that. Its value is as ground truth on
the *hardest* subpopulation, sitting on top of the 4,855-group census.

Two of these papers also show the surname veto is not paranoid: papers 46974 and
100769 carry **Julita** Van der Westhuizen and **Marichen** Van der Westhuizen
respectively — same surname, different people, in the same journal.

## Sources

Journal of Social Work / Maatskaplike Werk (`socialwork.journals.ac.za`), Journal of
Comparative Social Work (`journals.uis.no`), Advances in Social Work
(`journals.indianapolis.iu.edu`), OpenAlex API (`api.openalex.org`).
