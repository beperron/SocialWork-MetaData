#!/usr/bin/env python3
"""
Step 3 — test the proposals with signals the recovery step did not use.

    python3 qc/doi/code/03_audit.py [--per-stratum N] [--selftest]

Reads  ../data/recovery.json
Writes ../data/audit.json

WHY THIS WAS REWRITTEN
The first version of this audit confirmed a proposal by recomputing
`title_sim >= 0.90` and `journal_match` — the identical predicates, from the
identical functions, that caused the proposal to be accepted in the first place.
For tier B those two tests *are* the acceptance rule, so the audit could not
fail. It reported 120/120 and an adversarial review then found three wrong DOIs,
one of which was inside that very sample. A gate that re-applies the rule it is
gating measures nothing.

So this version deliberately avoids every signal recovery used to accept:

  DOI prefix      Each journal registers under one or two DOI prefixes. A
                  proposal whose prefix is not one of them is pointing at the
                  wrong publisher, whatever its title says. The prefixes are
                  derived from the live column, not hard-coded.
  Year            Recovery used year only as a Crossref *retrieval* filter, never
                  as an acceptance test, so year agreement is genuinely new
                  evidence here. Treated as a soft signal: a disagreement is
                  reported, not fatal, because bulk back-catalogue registration
                  makes Crossref's year unreliable.
  Author tokens   Compared as a magnitude, not the != 0 test recovery applied.
  Digit sequences Numbers in a title are load-bearing.

Sampling is stratified by (tier, journal-agreement basis) with a fixed seed, and
the result is reported as a proportion with a 95% interval, because 60 of 3,399
is a sample and should not be quoted as though it were a census.

--selftest feeds the three DOIs the adversarial review proved wrong. If the
audit passes them, it is broken and says so loudly. A gate that has never
rejected anything has not been tested.
"""
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

SRC = os.path.join(ROOT, "data", "recovery.json")
OUT = os.path.join(ROOT, "data", "audit.json")
CACHE = os.path.join(ROOT, "cache")

SEED = 20260802
DEFAULT_PER_STRATUM = 60
AUTHOR_MIN = 0.10          # both sides name authors -> expect *some* overlap
MIN_BASELINE = 20          # valid DOIs a journal needs before its prefixes mean anything

# The three the adversarial review proved wrong, with the DOI each was given.
# If the audit confirms any of these, it is not testing anything.
SELFTEST = {
    115909: "10.15270/38-4-1430",          # reply article given the original's DOI
    115257: "10.31265/jcsw.v14i2.245",     # issue editorial instead of the article
    117167: "10.1080/1936928x.2014.909682",  # "Editors (5)" matched to "(7)"
}


def wilson(k, n):
    """95% Wilson interval — sane at the edges, unlike normal approximation."""
    if not n:
        return (0.0, 0.0)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def journal_prefixes():
    """The DOI prefixes each journal actually registers under.

    Derived from the live column rather than hard-coded, so it stays true if the
    data changes. Only prefixes carrying at least 5% of a journal's valid DOIs
    count, which keeps a stray mis-filed row from legitimising a wrong prefix.

    A journal needs MIN_BASELINE valid DOIs before the check is applied at all.
    The Journal of Forensic Social Work has three, all 10.1080 — and the journal
    has since moved to a self-hosted 10.15763 prefix, so a baseline of three
    "proved" that its own current prefix was foreign. A check with no baseline
    does not abstain, it invents an answer, which is worse than not running.
    """
    rows = Q.rows(r"""
      select p.journal_id, split_part(p.doi, '/', 1) as prefix, count(*) as n
      from swrd.papers p
      where p.doi ~ '^10\.[0-9]{4,9}/' and p.journal_id is not null
      group by 1, 2
    """)
    by_j = defaultdict(list)
    for r in rows:
        by_j[r["journal_id"]].append((r["prefix"], r["n"]))
    out = {}
    for jid, ps in by_j.items():
        total = sum(n for _, n in ps)
        if total < MIN_BASELINE:
            continue                      # not enough evidence to judge; abstain
        out[jid] = {p for p, n in ps if n / total >= 0.05}
    return out


def check(rec, item, prefixes):
    """Independent verdict on one proposal. Returns (ok, reasons, detail)."""
    reasons = []
    doi = rec["proposed_doi"]

    allowed = prefixes.get(rec.get("journal_id")) or set()
    prefix = doi.split("/")[0]
    # Crossref naming our journal as the container is independent corroboration
    # that outranks a prefix objection: publishers migrate and take new prefixes.
    container_ok = Q.journal_match(
        [rec.get("issn_print"), rec.get("issn_online")], Q.cr_issns(item),
        rec.get("journal_name"), (item.get("container-title") or [None])[0])[0] == "match"
    if allowed and prefix not in allowed and not container_ok:
        reasons.append(f"doi_prefix_{prefix}_not_in_journal_set")

    if Q.digits_conflict(rec.get("title") or "", Q.cr_title(item)):
        reasons.append("digit_sequence_differs")

    ours = Q.swrd_name_tokens(rec.get("authors"))
    theirs = Q.cr_name_tokens(item)
    overlap = Q.jaccard(ours, theirs)
    if ours and theirs and overlap < AUTHOR_MIN:
        reasons.append("authors_do_not_overlap")

    yrs = Q.cr_years(item)
    y = rec.get("year")
    year_ok = (not yrs or y is None) or any(abs(y - c) <= 1 for c in yrs)

    return (not reasons), reasons, {
        "doi_prefix": prefix,
        "journal_prefixes": sorted(allowed),
        "author_token_overlap": round(overlap, 3),
        "our_author_tokens": len(ours), "crossref_author_tokens": len(theirs),
        "year_agrees": year_ok, "crossref_years": sorted(yrs),
        "crossref_title": Q.cr_title(item)[:200],
        "crossref_journal": (item.get("container-title") or [None])[0],
        "crossref_volume": item.get("volume"), "crossref_issue": item.get("issue"),
    }


def main():
    per = DEFAULT_PER_STRATUM
    if "--per-stratum" in sys.argv:
        per = int(sys.argv[sys.argv.index("--per-stratum") + 1])
    selftest = "--selftest" in sys.argv

    with open(SRC) as f:
        findings = json.load(f)
    Q.CACHE = CACHE

    by_id = {r["id"]: r for r in findings}
    proposals = [r for r in findings if r["verdict"] == "recovered"]

    strata = defaultdict(list)
    for r in proposals:
        strata[(r["tier"], r.get("journal_basis") or "none")].append(r)

    rng = random.Random(SEED)
    sample = []
    for key in sorted(strata):
        pool = sorted(strata[key], key=lambda r: r["id"])
        sample += rng.sample(pool, min(per, len(pool)))

    # Feed the known-bad proposals through the same code path.
    planted = []
    if selftest:
        for rid, bad_doi in SELFTEST.items():
            if rid in by_id:
                planted.append({**by_id[rid], "proposed_doi": bad_doi,
                                "tier": "SELFTEST", "journal_basis": "selftest"})
        sample += planted
        print(f"selftest: {len(planted)} known-bad proposals planted in the sample")

    print(f"auditing {len(sample)} proposals ({per} per stratum, seed {SEED})")
    print("  deriving each journal's DOI prefixes from the live column…")
    prefixes = journal_prefixes()

    cache = Q.cache_load("audit_lookup")
    missing = sorted({r["proposed_doi"].lower() for r in sample} - set(cache))
    print(f"  {len(missing)} Crossref lookups")
    for i in range(0, len(missing), 400):
        got = Q.crossref_by_dois(missing[i:i + 400])
        for k in missing[i:i + 400]:
            cache[k] = got.get(k)
    Q.cache_save("audit_lookup", cache)

    results = []
    for r in sample:
        item = cache.get(r["proposed_doi"].lower())
        row = {"id": r["id"], "tier": r["tier"],
               "stratum": f"{r['tier']}/{r.get('journal_basis')}",
               "proposed_doi": r["proposed_doi"],
               "journal_name": r.get("journal_name"),
               "title": (r.get("title") or "")[:160]}
        if not item:
            results.append({**row, "confirmed": False, "reasons": ["not_in_crossref"]})
            continue
        ok, reasons, detail = check(r, item, prefixes)
        results.append({**row, "confirmed": ok, "reasons": reasons, **detail})

    # ---- selftest verdict -------------------------------------------------
    selftest_ok = True
    if selftest:
        print("\nselftest — the audit must REJECT all of these:")
        for r in results:
            if r["tier"] != "SELFTEST":
                continue
            verdict = "rejected (good)" if not r["confirmed"] else "CONFIRMED — AUDIT IS BLIND"
            print(f"  {r['id']}: {verdict}  reasons={r['reasons']}")
            if r["confirmed"]:
                selftest_ok = False
        results = [r for r in results if r["tier"] != "SELFTEST"]

    print("\nprecision by stratum (95% Wilson interval):")
    summary = {}
    for key in sorted(strata):
        name = f"{key[0]}/{key[1]}"
        rs = [x for x in results if x["stratum"] == name]
        if not rs:
            continue
        ok = sum(1 for x in rs if x["confirmed"])
        lo, hi = wilson(ok, len(rs))
        summary[name] = {"audited": len(rs), "confirmed": ok,
                         "precision": round(ok / len(rs), 4),
                         "ci95": [lo, hi], "population": len(strata[key]),
                         "reasons": dict(Counter(
                             y for x in rs for y in x.get("reasons", [])))}
        print(f"  {name:<22} {ok:>3}/{len(rs):<3} = {100 * ok / len(rs):5.1f}%  "
              f"[{100 * lo:.1f}–{100 * hi:.1f}]   population {len(strata[key]):,}")

    failed = [x for x in results if not x["confirmed"]]
    with open(OUT, "w") as f:
        json.dump({"seed": SEED, "per_stratum": per,
                   "selftest_run": selftest, "selftest_passed": selftest_ok,
                   "independent_signals": ["doi_prefix", "digit_sequence",
                                           "author_tokens", "year"],
                   "summary": summary, "records": results}, f,
                  indent=1, ensure_ascii=False)
    print(f"\n-> {OUT}")

    if failed:
        print(f"\n{len(failed)} did not confirm:")
        for x in failed[:12]:
            print(f"  {x['id']} [{x['stratum']}] {x['reasons']}")
            print(f"     ours: {x['title'][:70]}")
            print(f"     xref: {(x.get('crossref_title') or '(absent)')[:70]}")

    if selftest and not selftest_ok:
        sys.exit("\nSELFTEST FAILED — the audit confirmed a known-wrong proposal.")


if __name__ == "__main__":
    main()
