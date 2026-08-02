#!/usr/bin/env python3
"""
Step 3 — measure how often the recovered DOIs are actually right.

    python3 qc/doi/code/03_audit.py [--per-tier N]

Reads  ../data/recovery.json
Writes ../data/audit.json

This is the gate. Nothing is proposed to the maintainer, and stage 2 does not
start, until the per-tier precision here is known.

The check is deliberately independent of the rule that produced the proposal.
A recovered DOI is confirmed by asking Crossref for that DOI directly and
requiring three things to line up at once:

    title    similarity >= 0.90 against the record we hold
    journal  ISSN match, or journal-name agreement
    authors  surname overlap, reported as corroboration

Titles alone are not enough. The earlier pilot found that a title can match
perfectly while the record is a book review of the same work in a different
journal, which is why journal agreement is a hard requirement rather than a
tiebreak. Authors are reported but not decisive: a real article can legitimately
have no author metadata in Crossref, and an editorial often has none anywhere.

Sampling is stratified by tier with a fixed seed, so the same sample is drawn on
every run and the numbers are reproducible.
"""
import json
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
CONFIRM = 0.90
DEFAULT_PER_TIER = 60


def main():
    per_tier = DEFAULT_PER_TIER
    if "--per-tier" in sys.argv:
        per_tier = int(sys.argv[sys.argv.index("--per-tier") + 1])

    with open(SRC) as f:
        findings = json.load(f)

    Q.CACHE = CACHE
    proposals = [r for r in findings if r.get("proposed_doi")
                 and r["verdict"] == "recovered"]

    # Stratify by tier *and* method: tier A is one deterministic rule against one
    # journal, tier B is a search across eight, and they can fail differently.
    strata = defaultdict(list)
    for r in proposals:
        strata[(r["tier"], r["method"])].append(r)

    rng = random.Random(SEED)
    sample = []
    for key in sorted(strata):
        pool = sorted(strata[key], key=lambda r: r["id"])
        sample += rng.sample(pool, min(per_tier, len(pool)))
    print(f"auditing {len(sample)} of {len(proposals)} proposals "
          f"({per_tier} per stratum, seed {SEED})")

    # Fetch each proposed DOI on its own terms, not via the record that proposed it
    cache = Q.cache_load("audit_lookup")
    missing = sorted({r["proposed_doi"].lower() for r in sample} - set(cache))
    print(f"  {len(missing)} to fetch")
    for i in range(0, len(missing), 400):
        got = Q.crossref_by_dois(missing[i:i + 400])
        for k in missing[i:i + 400]:
            cache[k] = got.get(k)
        print(f"    {min(i + 400, len(missing))}/{len(missing)}", flush=True)
    Q.cache_save("audit_lookup", cache)

    results = []
    for r in sample:
        item = cache.get(r["proposed_doi"].lower())
        row = {"id": r["id"], "tier": r["tier"], "method": r["method"],
               "pattern": r["pattern"], "proposed_doi": r["proposed_doi"],
               "title": (r["title"] or "")[:160],
               "journal_name": r["journal_name"]}
        if not item:
            results.append({**row, "confirmed": False, "reason": "doi_not_in_crossref"})
            continue

        sim = Q.title_sim(r["title"] or "", Q.cr_title(item))
        jverdict, jbasis = Q.journal_match(
            [r.get("issn_print"), r.get("issn_online")],
            Q.cr_issns(item),
            r.get("journal_name"),
            (item.get("container-title") or [None])[0])
        jrn = jverdict == "match"
        auth = Q.jaccard(Q.swrd_surnames(r.get("authors")), Q.cr_surnames(item))

        reason = ("ok" if sim >= CONFIRM and jrn else
                  "title_below_threshold" if sim < CONFIRM else "journal_disagrees")
        results.append({**row, "confirmed": reason == "ok", "reason": reason,
                        "title_similarity": round(sim, 3),
                        "journal_ok": jrn, "journal_basis": jbasis,
                        "author_overlap": round(auth, 3),
                        "crossref_title": Q.cr_title(item)[:200],
                        "crossref_journal": (item.get("container-title") or [None])[0]})

    print("\nprecision by stratum:")
    summary = {}
    for key in sorted(strata):
        tier, method = key
        rs = [x for x in results if x["tier"] == tier and x["method"] == method]
        if not rs:
            continue
        ok = sum(1 for x in rs if x["confirmed"])
        summary[f"{tier}/{method}"] = {
            "audited": len(rs), "confirmed": ok,
            "precision": round(ok / len(rs), 4),
            "population": len(strata[key]),
            "reasons": dict(Counter(x["reason"] for x in rs)),
        }
        print(f"  tier {tier} ({method:<16}) {ok:>3}/{len(rs):<3} = "
              f"{100 * ok / len(rs):5.1f}%   population {len(strata[key]):,}")

    # Corroboration, not a pass criterion — see the module docstring.
    withauth = [x for x in results if x.get("author_overlap") is not None
                and x["author_overlap"] > 0]
    print(f"\nauthor surnames corroborate on {len(withauth)}/{len(results)} audited")

    with open(OUT, "w") as f:
        json.dump({"seed": SEED, "per_tier": per_tier, "summary": summary,
                   "records": results}, f, indent=1, ensure_ascii=False)
    print(f"\n-> {OUT}")

    failed = [x for x in results if not x["confirmed"]]
    if failed:
        print(f"\n{len(failed)} did not confirm — inspect before applying:")
        for x in failed[:10]:
            print(f"  SWRD {x['id']} [{x['tier']}] {x['reason']} "
                  f"sim={x.get('title_similarity')}")
            print(f"     ours: {x['title'][:70]}")
            print(f"     xref: {(x.get('crossref_title') or '(absent)')[:70]}")


if __name__ == "__main__":
    main()
