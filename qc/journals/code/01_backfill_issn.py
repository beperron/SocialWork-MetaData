#!/usr/bin/env python3
"""
Stage 1 — recover an ISSN for every SWRD journal.

    python3 qc/journals/code/01_backfill_issn.py

Writes ../data/proposed_issns.csv     the patch set
       ../data/issn_evidence.json     per-journal votes and rejects
       ../data/issn_review_queue.csv  the ones a person has to decide

84 of 91 journals carry no ISSN. That is why the journal-attribution check
currently rests on comparing names, and name comparison is unsafe here: it maps
"Journal of Comparative Social Welfare" onto "Journal of Comparative Social
Work", and "Journal of Social Work & Human Sexuality" onto "Journal of Social
Work". Different journals in both cases. An identifier removes the guesswork,
which is why this runs before any attribution work.

Two populations, and they earn different amounts of trust.

  vote    A journal with articles carrying valid DOIs gets its ISSN by majority
          vote over the ISSN arrays Crossref returns on those articles. The
          journal's own articles are the strongest available evidence about what
          the journal is.

  lookup  A journal with no valid DOIs has nothing to vote on, so the Crossref
          journals endpoint is queried by title. This is NOT trustworthy on its
          own: asked for "School Social Work Journal" it returns a Korean
          "Journal of School Social Work". Every one of these goes to the review
          queue regardless of how confident it looks.

Nothing here writes to the database.
"""
import csv
import json
import os
import sys
import time
import urllib.parse
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

OUT_CSV = os.path.join(ROOT, "data", "proposed_issns.csv")
OUT_EV = os.path.join(ROOT, "data", "issn_evidence.json")
OUT_Q = os.path.join(ROOT, "data", "issn_review_queue.csv")
CACHE = os.path.join(ROOT, "cache")

SAMPLE_PER_JOURNAL = 120   # enough to settle a majority; more adds cost, not certainty
MIN_VOTES = 10             # below this the vote is reported but not proposed
AGREEMENT = 0.80           # share of sampled articles that must carry the winning ISSN


def sampled_dois():
    """Up to SAMPLE_PER_JOURNAL valid DOIs per journal, spread across its years.

    Spread rather than the first N by id: a journal that changed publisher has
    different ISSNs in different eras, and taking only the oldest articles would
    confidently return a retired identifier.
    """
    return Q.rows(rf"""
      select journal_id, doi from (
        select p.journal_id, p.doi,
               row_number() over (partition by p.journal_id
                                  order by (p.id * 2654435761) % 1000003) as rn
        from swrd.papers p
        where p.doi ~ '^10\.[0-9]{{4,9}}/' and p.journal_id is not null
      ) t where rn <= {SAMPLE_PER_JOURNAL}
    """)


def journals_endpoint(name, cache):
    """Crossref's journal-title search. Evidence only — never auto-applied."""
    if name in cache:
        return cache[name]
    url = "https://api.crossref.org/journals?" + urllib.parse.urlencode(
        {"query": name, "rows": 3})
    msg = Q._get(url) or {}
    items = msg.get("message", {}).get("items", [])
    cache[name] = [{"title": i.get("title"), "ISSN": i.get("ISSN"),
                    "publisher": i.get("publisher")} for i in items]
    time.sleep(0.15)
    return cache[name]


def main():
    Q.CACHE = CACHE
    os.makedirs(CACHE, exist_ok=True)

    journals = {j["id"]: j for j in Q.rows(
        "select id, name, publisher, issn_print, issn_online from swrd.journals")}
    print(f"{len(journals)} journals; "
          f"{sum(1 for j in journals.values() if not (j['issn_print'] or j['issn_online']))} "
          f"without an ISSN")

    print("sampling DOIs…")
    by_journal = {}
    for r in sampled_dois():
        by_journal.setdefault(r["journal_id"], []).append(r["doi"])
    print(f"  {sum(len(v) for v in by_journal.values()):,} DOIs across "
          f"{len(by_journal)} journals")

    cache = Q.cache_load("issn_lookup")
    wanted = sorted({d.lower() for v in by_journal.values() for d in v})
    missing = [d for d in wanted if d not in cache]
    print(f"Crossref: {len(wanted):,} DOIs, {len(missing):,} to fetch")
    for i in range(0, len(missing), 400):
        got = Q.crossref_by_dois(missing[i:i + 400])
        for k in missing[i:i + 400]:
            cache[k] = got.get(k)
        print(f"  {min(i + 400, len(missing)):,}/{len(missing):,}", flush=True)
    Q.cache_save("issn_lookup", cache)

    jcache = Q.cache_load("journals_endpoint")
    rows, queue, evidence = [], [], {}

    for jid, j in sorted(journals.items()):
        dois = by_journal.get(jid, [])
        votes = Counter()
        containers = Counter()
        for d in dois:
            item = cache.get(d.lower())
            if not item:
                continue
            issns = tuple(sorted(Q.cr_issns(item)))
            if issns:
                votes[issns] += 1
            ct = (item.get("container-title") or [None])[0]
            if ct:
                containers[ct] += 1

        ev = {"journal_id": jid, "name": j["name"],
              "current": {"issn_print": j["issn_print"], "issn_online": j["issn_online"]},
              "sampled_dois": len(dois), "with_issn": sum(votes.values()),
              "votes": [{"issn": list(k), "n": v} for k, v in votes.most_common(5)],
              "crossref_containers": containers.most_common(3)}

        if votes:
            winner, n = votes.most_common(1)[0]
            total = sum(votes.values())
            agree = n / total
            ev.update(method="vote", winner=list(winner),
                      agreement=round(agree, 3), n_votes=n, total=total)
            ok = n >= MIN_VOTES and agree >= AGREEMENT
            # Print and online cannot be told apart from Crossref's flat array.
            # Sorted order is a convention, not a fact, so both are recorded and
            # the distinction is left for a human if it ever matters.
            issn_print = winner[0] if winner else None
            issn_online = winner[1] if len(winner) > 1 else None
            row = {"journal_id": jid, "name": j["name"],
                   "current_print": j["issn_print"] or "",
                   "current_online": j["issn_online"] or "",
                   "issn_print": issn_print or "", "issn_online": issn_online or "",
                   "method": "vote", "n_votes": n, "sampled": total,
                   "agreement": round(agree, 3),
                   "tier": "A" if ok else "C",
                   "crossref_container": containers.most_common(1)[0][0] if containers else ""}
            (rows if ok else queue).append(row)
            if not ok:
                row["reason"] = ("too few votes" if n < MIN_VOTES
                                 else f"agreement {agree:.0%} below {AGREEMENT:.0%}")
        else:
            cands = journals_endpoint(j["name"], jcache)
            best = cands[0] if cands else None
            ev.update(method="lookup", candidates=cands)
            queue.append({
                "journal_id": jid, "name": j["name"],
                "current_print": j["issn_print"] or "",
                "current_online": j["issn_online"] or "",
                "issn_print": (best or {}).get("ISSN", [""])[0] if best else "",
                "issn_online": ((best or {}).get("ISSN") or ["", ""])[1]
                               if best and len((best or {}).get("ISSN") or []) > 1 else "",
                "method": "lookup", "n_votes": 0, "sampled": 0, "agreement": "",
                "tier": "C",
                "crossref_container": (best or {}).get("title", "") if best else "",
                "reason": "no articles with a valid DOI — title lookup only, must be "
                          "confirmed by hand"})
        evidence[str(jid)] = ev

    Q.cache_save("journals_endpoint", jcache)

    cols = ["journal_id", "name", "current_print", "current_online", "issn_print",
            "issn_online", "method", "n_votes", "sampled", "agreement", "tier",
            "crossref_container"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["journal_id"]))
    with open(OUT_Q, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["reason"], extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(queue, key=lambda r: r["journal_id"]))
    with open(OUT_EV, "w") as f:
        json.dump(evidence, f, indent=1, ensure_ascii=False)

    print(f"\nproposed : {len(rows):>3}  -> {OUT_CSV}")
    print(f"queued   : {len(queue):>3}  -> {OUT_Q}")
    print(f"  by method: {dict(Counter(r['method'] for r in queue))}")

    # The four journals that already carry an ISSN are the only ground truth
    # available. If the method disagrees with them, the method is wrong.
    print("\ncross-check against the journals that already have an ISSN:")
    for r in rows + queue:
        cur = {x for x in (r["current_print"], r["current_online"]) if x}
        if not cur:
            continue
        got = {x for x in (r["issn_print"], r["issn_online"]) if x}
        mark = "agrees" if cur & got else "*** DISAGREES ***"
        print(f"  {r['name'][:44]:<44} have={sorted(cur)} found={sorted(got)}  {mark}")


if __name__ == "__main__":
    main()
