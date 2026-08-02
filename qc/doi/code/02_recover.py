#!/usr/bin/env python3
"""
Step 2 — recover the real DOI for each malformed value.

    python3 qc/doi/code/02_recover.py [--limit N]

Reads  ../data/malformed.json
Writes ../data/recovery.json          one verdict per row, with its evidence
       ../cache/*.jsonl.gz            every Crossref response, so re-runs are free

Two populations, two methods, and they earn different amounts of trust.

  oai  The identifier encodes the article number that forms the real DOI:
       oai:scholarworks.wmich.edu:jssw-NNNN -> 10.15453/0191-5096.NNNN
       Deterministic. Still confirmed against Crossref by title before it is
       proposed, because a rule that is right 100 times can be wrong the 101st.

  dc   The hash is an internal ingest key and encodes nothing. Recovery is a
       Crossref bibliographic search, and it is only trusted when the journal
       also agrees. Without that guard the earlier pilot matched 35 records to
       book reviews of the same work in other journals.

Tiers, carried through to the patch set:

  A  rule-derived and title-confirmed        -> safe to apply in bulk
  B  search-recovered, title AND journal ok  -> apply after the sampled check
  C  anything else                           -> human queue, never auto-applied

Nothing here writes to the database; the endpoint is read-only by design.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

SRC = os.path.join(ROOT, "data", "malformed.json")
OUT = os.path.join(ROOT, "data", "recovery.json")
CACHE = os.path.join(ROOT, "cache")

CONFIRM = 0.90        # title similarity at or above this is the same article
JSSW_PREFIX = "10.15453/0191-5096."

# The nine journal names in this population, verified by hand against the
# database during planning. Journal agreement for the dc/ set is checked against
# ISSN where the journal has one and against this list where it does not.
# Enumerated rather than fuzzy-matched: a similarity threshold loose enough to
# be useful here would also merge distinct journals.
KNOWN_JOURNALS = {
    "the journal of sociology and social welfare",
    "advances in social work",
    "global social work trabajo social global",
    "journal of comparative social work",
    "social work and society",
    "journal of social work education and practice",
    "journal of forensic social work",
    "social work maatskaplike werk",
    "asean social work journal",
}


def cache_path(name):
    return os.path.join(CACHE, f"{name}.jsonl.gz")


def journal_verdict(rec, item):
    """Does Crossref agree with us about which journal this is?

    Delegates to the shared matcher so recovery and the audit cannot drift
    apart, then adds one local refinement: if the disagreement is on a name
    that is not even one of the nine journals known to be in this population,
    say so, because that is a stronger signal than a generic mismatch.
    """
    verdict, basis = Q.journal_match(
        [rec.get("issn_print"), rec.get("issn_online")],
        Q.cr_issns(item),
        rec.get("journal_name"),
        (item.get("container-title") or [None])[0])
    if verdict == "mismatch" and basis == "name":
        b = Q.norm_journal((item.get("container-title") or [None])[0])
        if b not in KNOWN_JOURNALS:
            basis = "name_offlist"
    return verdict, basis


def evidence(rec, item, sim, jv, jb):
    return {
        "crossref_doi": item.get("DOI"),
        "crossref_title": Q.cr_title(item)[:300],
        "crossref_journal": (item.get("container-title") or [None])[0],
        "crossref_years": sorted(Q.cr_years(item)),
        "title_similarity": round(sim, 3),
        "journal_verdict": jv,
        "journal_basis": jb,
        "author_overlap": round(
            Q.jaccard(Q.swrd_surnames(rec.get("authors")), Q.cr_surnames(item)), 3),
    }


def base_of(rec):
    # ISSN and authors travel with the record so that later stages can verify
    # against the identifier rather than re-deriving it from the journal name.
    return {k: rec[k] for k in ("id", "title", "year", "doi", "data_source",
                                "journal_name", "issn_print", "issn_online",
                                "authors", "pattern", "is_scientific",
                                "document_type")}


def recover_oai(records, cache):
    """The deterministic half: derive the DOI, then make Crossref confirm it."""
    want = {}
    for rec in records:
        m = Q.OAI_JSSW_RE.match(rec["doi"])
        if m:
            want[rec["id"]] = f"{JSSW_PREFIX}{m.group(1)}"

    missing = sorted({d.lower() for d in want.values()} - set(cache))
    print(f"  oai: {len(want)} candidates, {len(missing)} to fetch")
    for i in range(0, len(missing), 400):
        got = Q.crossref_by_dois(missing[i:i + 400])
        for k in missing[i:i + 400]:
            cache[k] = got.get(k)
        print(f"    fetched {min(i + 400, len(missing))}/{len(missing)}", flush=True)

    out = []
    for rec in records:
        base = base_of(rec)
        cand = want.get(rec["id"])
        if not cand:
            out.append({**base, "method": "oai_rule", "verdict": "no_rule_match",
                        "tier": "C"})
            continue
        item = cache.get(cand.lower())
        if not item:
            out.append({**base, "method": "oai_rule", "proposed_doi": cand,
                        "verdict": "candidate_not_in_crossref", "tier": "C"})
            continue
        sim = Q.title_sim(rec["title"] or "", Q.cr_title(item))
        jv, jb = journal_verdict(rec, item)
        ev = evidence(rec, item, sim, jv, jb)
        ok = sim >= CONFIRM
        out.append({**base, "method": "oai_rule", "proposed_doi": cand, **ev,
                    "verdict": "recovered" if ok else "title_mismatch",
                    "tier": "A" if ok else "C"})
    return out


def recover_dc(records, scache):
    """The searched half: propose only when title AND journal both agree."""
    todo = [r for r in records if str(r["id"]) not in scache]
    print(f"  dc: {len(records)} records, {len(todo)} to search")
    for n, rec in enumerate(todo, 1):
        issns = [s for s in (rec.get("issn_print"), rec.get("issn_online")) if s]
        scache[str(rec["id"])] = Q.crossref_search(rec.get("title") or "",
                                                   rec.get("year"), issns)
        if n % 100 == 0:
            print(f"    searched {n}/{len(todo)}", flush=True)

    out = []
    for rec in records:
        base = base_of(rec)
        best, best_sim, best_jv, best_jb = None, -1.0, None, None
        for item in scache.get(str(rec["id"])) or []:
            sim = Q.title_sim(rec["title"] or "", Q.cr_title(item))
            if sim > best_sim:
                jv, jb = journal_verdict(rec, item)
                best, best_sim, best_jv, best_jb = item, sim, jv, jb
        if best is None:
            out.append({**base, "method": "crossref_search",
                        "verdict": "no_candidate", "tier": "C"})
            continue
        ev = evidence(rec, best, best_sim, best_jv, best_jb)
        row = {**base, "method": "crossref_search",
               "proposed_doi": best.get("DOI"), **ev}
        if best_sim < CONFIRM:
            row.update(verdict="weak_title", tier="C")
        elif best_jv == "mismatch":
            # Right title, wrong journal: almost always a book review of the same
            # work, or a same-titled paper elsewhere. This is the guard that the
            # pilot proved is load-bearing.
            row.update(verdict="rejected_wrong_journal", tier="C")
        elif best_jv == "unknown":
            row.update(verdict="journal_unverified", tier="C")
        else:
            row.update(verdict="recovered", tier="B")
        out.append(row)
    return out


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    with open(SRC) as f:
        records = json.load(f)
    if limit:
        records = records[:limit]
        print(f"(limited to {limit} records)")

    os.makedirs(CACHE, exist_ok=True)
    Q.CACHE = CACHE                      # keep this pipeline's cache beside its data

    oai = [r for r in records if r["pattern"] == "oai"]
    dc = [r for r in records if r["pattern"] == "dc"]

    dcache = Q.cache_load("doi_lookup")
    findings = recover_oai(oai, dcache)
    Q.cache_save("doi_lookup", dcache)

    scache = Q.cache_load("title_search")
    findings += recover_dc(dc, scache)
    Q.cache_save("title_search", scache)

    findings.sort(key=lambda r: r["id"])
    with open(OUT, "w") as f:
        json.dump(findings, f, indent=1, ensure_ascii=False)

    from collections import Counter
    print("\nverdicts:")
    for (pat, v, t), n in sorted(Counter(
            (r["pattern"], r["verdict"], r["tier"]) for r in findings).items()):
        print(f"  {pat:<4} {v:<28} tier {t}  {n:>5}")
    print("\ntiers:", dict(Counter(r["tier"] for r in findings)))
    print(f"{len(findings)} verdicts -> {OUT}")


if __name__ == "__main__":
    main()
