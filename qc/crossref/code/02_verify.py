#!/usr/bin/env python3
"""
Step 2 — verify the sample against Crossref and propose corrections.

    python3 02_verify.py

Reads  ../data/pilot_sample.json
Writes ../data/findings.json          one verdict per record, with evidence
       ../cache/crossref_*.jsonl.gz   every Crossref response, for re-runs

Nothing here writes to the database. Every proposal carries the evidence that
produced it and a tier saying how much trust it has earned:

  A  deterministic and confirmed — the correction follows from a rule and
     Crossref agrees on the title. Safe to apply in bulk.
  B  high confidence, single field — apply after a sampled human check.
  C  ambiguous or unresolved — human queue only, never auto-applied.

Crossref is treated as evidence, not truth. Its coverage of older, regional,
and small-publisher journals is patchy and its own metadata contains errors,
so "Crossref disagrees" produces a review item, never an overwrite.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swrdqc as Q

SAMPLE = os.path.join(Q.DATA, "pilot_sample.json")
OUT = os.path.join(Q.DATA, "findings.json")

# Title-similarity thresholds. 0.90 is where a differing-but-same title
# (punctuation, subtitle handling, HTML entities) stops and a different paper
# begins; below 0.75 the two are unrelated.
CONFIRM, REVIEW = 0.90, 0.75


def compare(rec, item):
    """Field-by-field comparison of one SWRD record against one Crossref item."""
    sim = Q.title_sim(rec["title"] or "", Q.cr_title(item))

    yrs = Q.cr_years(item)
    y = rec.get("year")
    if not yrs or y is None:
        year_verdict = "unknown"
    elif y in yrs:
        year_verdict = "match"
    elif any(abs(y - c) <= 1 for c in yrs):
        year_verdict = "match_offset_1"      # online-first vs issue year
    else:
        year_verdict = "mismatch"

    # ISSN is the reliable key, but only 7 of 91 SWRD journals carry one, so it
    # answers "unknown" almost everywhere. Fall back to comparing journal names.
    # Without some journal check, a bibliographic search happily matches a book
    # review of the same work in an entirely different journal — which is where
    # the pilot's false positives came from.
    ours = {s.strip().upper() for s in (rec.get("issn_print"), rec.get("issn_online")) if s}
    theirs = Q.cr_issns(item)
    if ours and theirs:
        journal_verdict = "match" if ours & theirs else "mismatch"
        journal_basis = "issn"
    else:
        a, b = Q.norm_journal(rec.get("journal_name")), Q.norm_journal(
            (item.get("container-title") or [None])[0])
        if not b:
            journal_verdict, journal_basis = "unknown", "no_container_title"
        elif a and (a == b or a.startswith(b) or b.startswith(a)
                    or Q.title_sim(a, b) >= 0.85):
            journal_verdict, journal_basis = "match", "name"
        else:
            journal_verdict, journal_basis = "mismatch", "name"

    return {
        "crossref_doi": item.get("DOI"),
        "crossref_title": Q.cr_title(item)[:300],
        "crossref_journal": (item.get("container-title") or [None])[0],
        "crossref_issn": sorted(theirs),
        "crossref_type": item.get("type"),
        "crossref_years": sorted(yrs),
        "title_similarity": round(sim, 3),
        "year_verdict": year_verdict,
        "journal_verdict": journal_verdict,
        "journal_basis": journal_basis,
        "author_overlap": round(
            Q.jaccard(Q.swrd_surnames(rec.get("authors")), Q.cr_surnames(item)), 3),
    }


def main():
    with open(SAMPLE) as f:
        sample = json.load(f)

    # ---- pass 1: everything that already has a usable DOI ----------------
    direct = [r for r in sample if Q.is_valid_doi(r.get("doi"))]
    # ---- plus the deterministic OAI -> DOI candidates ---------------------
    oai_candidates = {}
    for r in sample:
        m = Q.OAI_JSSW_RE.match(str(r.get("doi") or ""))
        if m:
            oai_candidates[r["id"]] = f"10.15453/0191-5096.{m.group(1)}"

    lookup = sorted({r["doi"].strip().lower() for r in direct} |
                    {d.lower() for d in oai_candidates.values()})
    cache = Q.cache_load("crossref_by_doi")
    missing = [d for d in lookup if d not in cache]
    print(f"DOI lookups: {len(lookup)} needed, {len(lookup) - len(missing)} cached, "
          f"{len(missing)} to fetch")
    if missing:
        for i in range(0, len(missing), 200):
            got = Q.crossref_by_dois(missing[i:i + 200])
            for k in missing[i:i + 200]:
                cache[k] = got.get(k)          # None records a real 'not found'
            print(f"  fetched {min(i + 200, len(missing))}/{len(missing)}")
        Q.cache_save("crossref_by_doi", cache)

    findings = []
    needs_search = []

    for rec in sample:
        doi = str(rec.get("doi") or "").strip()
        base = {k: rec[k] for k in
                ("id", "stratum", "title", "year", "doi", "journal_name",
                 "document_type", "is_scientific", "has_abstract")}

        if Q.is_valid_doi(doi):
            item = cache.get(doi.lower())
            if not item:
                findings.append({**base, "check": "doi_lookup",
                                 "verdict": "doi_not_in_crossref", "tier": "C",
                                 "note": "DOI is well-formed but Crossref has no record"})
                continue
            cmp = compare(rec, item)
            issues = []
            if cmp["title_similarity"] < REVIEW:
                issues.append("title")
            if cmp["year_verdict"] == "mismatch":
                issues.append("year")
            if cmp["journal_verdict"] == "mismatch":
                issues.append("journal")
            findings.append({
                **base, "check": "doi_lookup", **cmp,
                "verdict": "confirmed" if not issues else "field_mismatch",
                "mismatched_fields": issues,
                "tier": "A" if not issues else
                        ("B" if cmp["title_similarity"] >= CONFIRM else "C"),
            })
            continue

        if rec["id"] in oai_candidates:
            cand = oai_candidates[rec["id"]]
            item = cache.get(cand.lower())
            if not item:
                findings.append({**base, "check": "oai_conversion",
                                 "verdict": "candidate_not_in_crossref", "tier": "C",
                                 "proposed_doi": cand})
                continue
            cmp = compare(rec, item)
            ok = cmp["title_similarity"] >= CONFIRM
            findings.append({
                **base, "check": "oai_conversion", **cmp, "proposed_doi": cand,
                "verdict": "recovered" if ok else "candidate_rejected",
                "tier": "A" if ok else "C",
            })
            continue

        needs_search.append(rec)

    # ---- pass 2: bibliographic search for the rest ------------------------
    print(f"bibliographic searches: {len(needs_search)}")
    scache = Q.cache_load("crossref_search")
    for n, rec in enumerate(needs_search, 1):
        key = str(rec["id"])
        if key not in scache:
            issns = [s for s in (rec.get("issn_print"), rec.get("issn_online")) if s]
            scache[key] = Q.crossref_search(rec.get("title") or "",
                                            rec.get("year"), issns)
        if n % 25 == 0:
            print(f"  searched {n}/{len(needs_search)}")
        base = {k: rec[k] for k in
                ("id", "stratum", "title", "year", "doi", "journal_name",
                 "document_type", "is_scientific", "has_abstract")}
        check = "search_malformed" if rec.get("doi") else "search_null_doi"

        best, best_cmp = None, None
        for item in scache[key] or []:
            cmp = compare(rec, item)
            if best_cmp is None or cmp["title_similarity"] > best_cmp["title_similarity"]:
                best, best_cmp = item, cmp
        if best_cmp is None:
            findings.append({**base, "check": check, "verdict": "no_candidate", "tier": "C"})
        elif (best_cmp["title_similarity"] >= CONFIRM
              and best_cmp["year_verdict"] != "mismatch"
              and best_cmp["journal_verdict"] != "mismatch"):
            findings.append({**base, "check": check, **best_cmp,
                             "proposed_doi": best.get("DOI"),
                             "verdict": "recovered", "tier": "B"})
        elif best_cmp["journal_verdict"] == "mismatch":
            # Right title, wrong journal: almost always a book review of the same
            # work, or a same-titled paper elsewhere. Never auto-apply.
            findings.append({**base, "check": check, **best_cmp,
                             "proposed_doi": best.get("DOI"),
                             "verdict": "rejected_wrong_journal", "tier": "C"})
        else:
            findings.append({**base, "check": check, **best_cmp,
                             "proposed_doi": best.get("DOI"),
                             "verdict": "weak_candidate", "tier": "C"})
    Q.cache_save("crossref_search", scache)

    with open(OUT, "w") as f:
        json.dump(findings, f, indent=1, ensure_ascii=False)
    print(f"\n{len(findings)} findings -> {OUT}")


if __name__ == "__main__":
    main()
