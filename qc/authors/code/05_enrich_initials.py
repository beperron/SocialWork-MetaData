#!/usr/bin/env python3
"""
Enrichment — full given names for initials-only authors, as a SEPARATE table.

    python3 qc/authors/code/05_enrich_initials.py [--selftest]

Writes ../data/enrich_initials.csv        every enriched row, with evidence
       ../data/enrich_initials.sql        create table + insert + assertions
       ../data/rollback_enrich_initials.sql
       ../data/enrich_initials_queue.csv  every refusal, with its class

WHAT THIS IS, AND IS NOT

24,007 author rows store a name in initials-only form: 'THYER, BA', 'Xiao Y.',
'Islam M.R.'. That is the name AS PUBLISHED, which the project guarantees to
preserve — so this feature never writes swrd.authors. It builds
swrd.author_name_enrichment: a derived annotation holding the fuller form
Crossref gives on the author's OWN papers, with the full evidence trail, and
only where every checkable paper agrees on the identical rendering.

It is NOT disambiguation. Two author ids sharing a full_name are not thereby
one person, and the table must never be used to merge ids.

ELIGIBILITY — all eight, each independently able to refuse

  form        the stored name is initials-only in any of the three corpus
              orders, including the surname-first collapsed 'Islam M.R.' whose
              misparse broke an earlier fix (mandatory selftest case)
  link        >=1 paper with a real DOI
  unique      exactly one Crossref author on the paper matches the surname
              (letters-only, diacritic-insensitive); two same-family authors
              veto the paper even if initials would disambiguate
  sibling     no OTHER credit on the same paper in swrd.paper_authors shares
              the surname — an SWRD-side check independent of Crossref
  coverage    a paper is discarded as evidence when Crossref lists fewer
              authors than SWRD credits on it (the truncated-deposit class:
              Crossref's 'T. Booth' for a three-author article)
  fullness    our initials match the Crossref given tokens' first letters in
              order, and at least one given token has >=2 letters
  unanimity   every evidence-yielding paper produces the string-identical
              rendered form. 'Renee' vs 'Renée' refuses. 'John' vs 'John R.'
              refuses (queued as partial_agreement, the class a future pass
              might admit — measured now, not admitted now)
  dissent     a paper whose Crossref record carries a same-surname author with
              CONFLICTING initials is a dissenting vote and vetoes the row —
              never a silent skip

Refusals go to the queue with a reason; the partition must be exact
(EXPECTED_CENSUS = enriched + refused) or nothing is emitted.

Read-only. Applying is the maintainer's step.
"""
import csv
import os
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "crossref", "code"))
import swrdqc as Q  # noqa: E402

OUT_CSV = os.path.join(ROOT, "data", "enrich_initials.csv")
OUT_SQL = os.path.join(ROOT, "data", "enrich_initials.sql")
OUT_RB = os.path.join(ROOT, "data", "rollback_enrich_initials.sql")
OUT_Q = os.path.join(ROOT, "data", "enrich_initials_queue.csv")

EXPECTED_CENSUS = 50_393      # initials-only rows over ALL 164,549 authors.
# Larger than the 24,007 quoted in planning for two measured reasons: that
# figure was scoped to authors on 1989+/valid-DOI papers only, and its parser
# missed two orders this one handles -- glued caps ('THYER, BA', 'Lee DB',
# +10,259 rows) and initial-first ('S. Nixon', 'J. E. Gonzalez'). Rows without
# usable DOI evidence still end in the queue, so widening the census widens
# the REFUSAL classes, not the risk.

PARTICLE = {"van", "von", "de", "del", "della", "der", "den", "di", "da", "dos",
            "du", "la", "le", "el", "al", "bin", "ibn", "st", "ter", "ten"}


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(c))


def alpha(s):
    return re.sub(r"[^a-z]", "", strip_accents(s or "").lower())


def initials_token(tok):
    """-> list of initials if the token is an initials rendering, else None.

    'B' -> [B]   'B.A.' / 'B.A' -> [B,A]   'BA' (all caps, <=3) -> [B,A]
    'Bruce' -> None. The undotted-caps rule is what admits 'THYER, BA' and
    'Lee DB'; it cannot swallow a real surname because those carry lowercase.
    """
    t = tok.strip().rstrip(".")
    if not t:
        return None
    parts = t.split(".")
    if all(len(p) == 1 and p.isalpha() for p in parts):
        return [p.upper() for p in parts]
    if t.isalpha() and t.isupper() and 1 <= len(t) <= 3:
        return list(t)
    return None


def parse_initials_only(name):
    """-> (surname, [initials]) if the stored name is initials-only, else None.

    Handles the three corpus orders:
        'THYER, BA'   comma; given segment is glued or dotted initials
        'Xiao Y.'     surname first, trailing dotted initials
        'Islam M.R.'  surname first, collapsed initials -- the form whose
                      misparse (initial read as surname) broke fix 3's first
                      version; parsed here surname-first on purpose
    A name with any full given word ('Thyer, Bruce A.') is NOT initials-only.
    """
    raw = re.sub(r"\s+", " ", (name or "").strip())
    if not raw or "@" in raw or re.search(r"\d", raw):
        return None
    # generational suffixes are not initials
    if re.search(r"\b(jr|sr|ii|iii|iv)\b\.?\s*$", raw, re.I):
        return None
    if "," in raw:
        surname, _, given = raw.partition(",")
        toks = given.split()
        if not toks:
            return None
        ini = []
        for t in toks:
            got = initials_token(t)
            if not got:
                return None              # a full given word -> out of scope
            ini.extend(got)
    else:
        toks = raw.split()
        if len(toks) < 2:
            return None
        # order A — surname first, trailing initials: 'Xiao Y.', 'Lee DB'
        ini, i = [], len(toks)
        while i > 1:
            got = initials_token(toks[i - 1])
            if not got:
                break
            ini = got + ini
            i -= 1
        # order B — leading initials, surname last: 'S. Nixon', 'J. E. Gonzalez'
        ini_b, j = [], 0
        while j < len(toks) - 1:
            got = initials_token(toks[j])
            if not got:
                break
            ini_b += got
            j += 1
        a_ok = bool(ini) and i >= 1 and not initials_token(toks[i - 1])
        b_ok = bool(ini_b) and j <= len(toks) - 1 and not initials_token(toks[-1])
        if a_ok and not b_ok:
            surname = " ".join(toks[:i])
        elif b_ok and not a_ok:
            surname, ini = " ".join(toks[j:]), ini_b
        else:
            return None            # both readings viable ('M. C.') or neither
    surname = surname.strip().rstrip(".")
    if not surname or not re.search(r"[A-Za-zÀ-ÿ]{2,}", surname):
        return None
    return surname, ini


def render(family, given):
    return f"{family}, {given}"


def judge_paper(surname, initials, cr_authors, swrd_names_on_paper, own_name):
    """One paper's vote for one author row.

    -> ('ok', family, given) | ('refuse', reason) | ('skip', reason)
    skip = the paper offers no usable evidence; refuse = the paper VETOES.
    """
    sa = alpha(surname)
    # sibling gate: another SWRD credit on this paper shares the surname
    for other in swrd_names_on_paper:
        if other == own_name:
            continue
        po = parse_initials_only(other)
        osur = po[0] if po else re.split(r"[,]", other)[0]
        if alpha(osur) == sa and other != own_name:
            return ("refuse", "sibling_same_surname_on_paper")
    if not cr_authors:
        return ("skip", "no_crossref_record")
    # coverage guard
    if len(cr_authors) < len(swrd_names_on_paper):
        return ("skip", "crossref_author_list_truncated")
    cands = [ca for ca in cr_authors
             if alpha(ca.get("family") or "") == sa
             or (alpha(ca.get("family") or "").startswith(sa) and sa)]
    cands = [ca for ca in cands if alpha(ca.get("family") or "") == sa]
    if not cands:
        return ("skip", "no_matching_crossref_surname")
    if len(cands) > 1:
        return ("refuse", "two_same_surname_authors_on_paper")
    ca = cands[0]
    giv = (ca.get("given") or "").strip()
    if "�" in giv or "�" in (ca.get("family") or ""):
        # U+FFFD in Crossref's own deposit (Springer legacy records store
        # 'Ren� C.' at the registry itself). Verbatim is the rule, but
        # shipping a replacement character is shipping garbage — refuse.
        return ("refuse", "crossref_encoding_damage")
    toks = [t for t in re.split(r"[\s.\-]+", giv) if t]
    if not toks or all(len(t) == 1 for t in toks):
        return ("skip", "crossref_initials_only")
    if len(toks) < len(initials):
        return ("refuse", "initials_conflict")
    for o, g in zip(initials, toks):
        if g[0].upper() != o:
            return ("refuse", "initials_conflict")
    fam = (ca.get("family") or "").strip()
    return ("ok", fam, re.sub(r"\s+", " ", giv))


# ---------------------------------------------------------------- selftest

def selftest():
    ok = lambda f, g: ("ok", f, g)  # noqa: E731
    P = [{"family": "Thyer", "given": "Bruce A."}]
    P2 = [{"family": "Lee", "given": "Sunwoo"}, {"family": "Lee", "given": "Sangwoo"}]
    PSHORT = [{"family": "Booth", "given": "T."}]
    cases = [
        # --- parser: the three orders, and the traps
        ("parse THYER, BA", parse_initials_only("THYER, BA"), ("THYER", ["B", "A"])),
        ("parse Xiao Y.", parse_initials_only("Xiao Y."), ("Xiao", ["Y"])),
        ("parse Islam M.R. (fix-3 trap)", parse_initials_only("Islam M.R."),
         ("Islam", ["M", "R"])),
        ("full name is out of scope", parse_initials_only("Thyer, Bruce A."), None),
        ("suffix is not initials", parse_initials_only("Coldon, Lawrence, 3rd"), None),
        ("@-alias out of scope", parse_initials_only("Zuraini J.@.O."), None),
        ("bare surname out of scope", parse_initials_only("Gottlieb"), None),
        # --- paper judge
        ("unique match enriches",
         judge_paper("Thyer", ["B", "A"], P, ["THYER, BA"], "THYER, BA"),
         ok("Thyer", "Bruce A.")),
        ("two same-family crossref authors refuse",
         judge_paper("Lee", ["S"], P2, ["Lee S."], "Lee S."),
         ("refuse", "two_same_surname_authors_on_paper")),
        ("crossref initials-only is no evidence",
         judge_paper("Booth", ["T"], PSHORT, ["Booth T."], "Booth T."),
         ("skip", "crossref_initials_only")),
        ("coverage guard: fewer crossref authors than swrd credits",
         judge_paper("Booth", ["T"], PSHORT,
                     ["Booth T.", "Wendy Smith", "David McConnell"], "Booth T."),
         ("skip", "crossref_author_list_truncated")),
        ("glued caps parse: Lee DB", parse_initials_only("Lee DB"), ("Lee", ["D", "B"])),
        ("bare caps fragment is not a name", parse_initials_only("MC"), None),
        ("initial-first parse: S. Nixon", parse_initials_only("S. Nixon"),
         ("Nixon", ["S"])),
        ("initial-first parse: J. E. Gonzalez", parse_initials_only("J. E. Gonzalez"),
         ("Gonzalez", ["J", "E"])),
        ("both readings viable is refused", parse_initials_only("M. C."), None),
        ("initials out of order refuse",
         judge_paper("Thyer", ["A", "B"], P, ["Thyer A.B."], "Thyer A.B."),
         ("refuse", "initials_conflict")),
        ("swrd sibling same surname refuses",
         judge_paper("Thyer", ["B"], P, ["Thyer B.", "Thyer, Wendy"], "Thyer B."),
         ("refuse", "sibling_same_surname_on_paper")),
        ("diacritic surname matches",
         judge_paper("Cronjé", ["F"], [{"family": "Cronje", "given": "Freek"}],
                     ["Cronjé F."], "Cronjé F."),
         ok("Cronje", "Freek")),
    ]
    bad = 0
    for name, got, want in cases:
        good = got == want
        bad += not good
        print(f"  {'ok  ' if good else 'FAIL'}  {name:<44} -> {got}")
    print("\nselftest passed" if not bad else f"\n{bad} SELFTEST FAILURES")
    return 1 if bad else 0


# ---------------------------------------------------------------- main

def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    authors = Q.rows("""
      select a.id, a.name from swrd.authors a order by a.id""")
    elig = {}
    for a in authors:
        p = parse_initials_only(a["name"])
        if p:
            elig[a["id"]] = {"name": a["name"], "surname": p[0], "initials": p[1]}
    print(f"initials-only census: {len(elig):,}  (expected {EXPECTED_CENSUS:,})")
    if len(elig) != EXPECTED_CENSUS:
        sys.exit("census drifted — re-measure before generating")

    links = defaultdict(list)
    paper_names = defaultdict(list)
    for r in Q.rows("""
      select pa.paper_id, pa.author_id, p.doi, a.name
      from swrd.paper_authors pa
      join swrd.papers p on p.id = pa.paper_id
      join swrd.authors a on a.id = pa.author_id"""):
        paper_names[r["paper_id"]].append(r["name"])
        if r["author_id"] in elig:
            links[r["author_id"]].append((r["paper_id"], r["doi"]))

    dois = sorted({(d or "").lower() for ls in links.values() for _, d in ls
                   if d and d.startswith("10.")})
    Q.CACHE = os.path.join(ROOT, "..", "doi", "cache")
    merged = {}
    for name in ("column_lookup", "doi_lookup", "audit_lookup"):
        try:
            for k, v in Q.cache_load(name).items():
                if isinstance(v, dict) and v.get("DOI"):
                    merged[v["DOI"].lower()] = v
        except Exception:
            pass
    Q.CACHE = os.path.join(ROOT, "cache")
    extra = Q.cache_load("trunc_lookup")
    for k, v in extra.items():
        if isinstance(v, dict) and v.get("DOI"):
            merged.setdefault(k, v)
    missing = [d for d in dois if d not in merged]
    print(f"papers to consult: {len(dois):,}  (fetching {len(missing):,})")
    if missing:
        cache = Q.cache_load("enrich_lookup")
        todo = [d for d in missing if d not in cache]
        for i in range(0, len(todo), 400):
            got = Q.crossref_by_dois(todo[i:i + 400])
            for d in todo[i:i + 400]:
                cache[d] = got.get(d)
            if i % 4000 == 0:
                Q.cache_save("enrich_lookup", cache)
                print(f"  {min(i + 400, len(todo)):,}/{len(todo):,}", flush=True)
        Q.cache_save("enrich_lookup", cache)
        for k, v in cache.items():
            if isinstance(v, dict) and v.get("DOI"):
                merged.setdefault(k, v)

    rows, queued = [], []
    for aid, info in sorted(elig.items()):
        ls = links.get(aid)
        if not ls:
            queued.append({"author_id": aid, "name": info["name"],
                           "reason": "orphaned_row_no_links"})
            continue
        votes, skips = [], []
        vetoed = None
        for pid, doi in ls:
            d = (doi or "").lower()
            if not d.startswith("10."):
                skips.append("paper_has_no_doi")
                continue
            x = merged.get(d)
            v = judge_paper(info["surname"], info["initials"],
                            (x or {}).get("author"), paper_names[pid], info["name"])
            if v[0] == "ok":
                votes.append((v[1], v[2], d))
            elif v[0] == "refuse":
                vetoed = v[1]
                break
            else:
                skips.append(v[1])
        if vetoed:
            queued.append({"author_id": aid, "name": info["name"], "reason": vetoed})
            continue
        if not votes:
            reason = skips[0] if skips else "paper_has_no_doi"
            queued.append({"author_id": aid, "name": info["name"], "reason": reason})
            continue
        forms = {render(f, g) for f, g, _ in votes}
        if len(forms) > 1:
            # distinguish partial extension from真 disagreement
            givens = sorted({g for _, g, _ in votes}, key=len)
            short, long_ = givens[0], givens[-1]
            if all(long_.startswith(s) or s.startswith(long_) is False and long_.startswith(s)
                   for s in givens[:-1]) and long_.startswith(short):
                queued.append({"author_id": aid, "name": info["name"],
                               "reason": f"partial_agreement: {short} | {long_}"})
            else:
                queued.append({"author_id": aid, "name": info["name"],
                               "reason": "papers_disagree: " + " | ".join(sorted(forms)[:3])})
            continue
        fam, giv, _ = votes[0]
        full = render(fam, giv)
        if full == info["name"]:
            queued.append({"author_id": aid, "name": info["name"],
                           "reason": "already_identical"})
            continue
        rows.append({"author_id": aid, "name_as_published": info["name"],
                     "full_name": full, "family": fam, "given_full": giv,
                     "evidence_dois": "|".join(sorted({d for _, _, d in votes})),
                     "n_papers_linked": len(ls), "n_papers_checked": len(votes),
                     "n_papers_agreeing": len(votes)})

    print(f"\nenriched : {len(rows):,}")
    print(f"queued   : {len(queued):,}")
    reasons = defaultdict(int)
    for q in queued:
        reasons[q["reason"].split(":")[0]] += 1
    for k, v in sorted(reasons.items(), key=lambda t: -t[1]):
        print(f"   {k:<36} {v:,}")
    if len(rows) + len(queued) != EXPECTED_CENSUS:
        sys.exit("partition is not exact — refusing to emit")

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(OUT_Q, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["author_id", "name", "reason"])
        w.writeheader()
        w.writerows(queued)

    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True, cwd=ROOT).stdout.strip()
    gen = f"qc/authors/code/05_enrich_initials.py@{sha}"

    def lit(s):
        return "'" + s.replace("'", "''") + "'"

    vals = ",\n".join(
        "  ({id}, {nap}, {fn}, {fam}, {gv}, array[{dois}], {nl}, {nc}, {na})".format(
            id=r["author_id"], nap=lit(r["name_as_published"]),
            fn=lit(r["full_name"]), fam=lit(r["family"]), gv=lit(r["given_full"]),
            dois=",".join(lit(d) for d in r["evidence_dois"].split("|")),
            nl=r["n_papers_linked"], nc=r["n_papers_checked"],
            na=r["n_papers_agreeing"])
        for r in rows)
    with open(OUT_SQL, "w") as f:
        f.write(f"""-- swrd.author_name_enrichment: derived fuller names for {len(rows)}
-- initials-only author rows, unanimous across every checkable paper.
-- swrd.authors is NOT written; this is an annotation, not a correction, and
-- must never be used to merge author ids.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f enrich_initials.sql

begin;

drop table if exists swrd.author_name_enrichment;
create table swrd.author_name_enrichment (
  author_id          int  primary key references swrd.authors(id),
  name_as_published  text not null,
  full_name          text not null,
  family             text not null,
  given_full         text not null,
  source             text not null default 'crossref' check (source = 'crossref'),
  evidence_dois      text[] not null check (cardinality(evidence_dois) >= 1),
  n_papers_linked    int  not null check (n_papers_linked >= 1),
  n_papers_checked   int  not null check (n_papers_checked >= 1),
  n_papers_agreeing  int  not null,
  generated_at       timestamptz not null default now(),
  generator          text not null default {lit(gen)},
  batch              text not null default 'v1.4',
  check (n_papers_agreeing = n_papers_checked),
  check (n_papers_agreeing = cardinality(evidence_dois)),
  check (full_name <> name_as_published),
  check (n_papers_checked <= n_papers_linked)
);
grant select on swrd.author_name_enrichment to anon;

insert into swrd.author_name_enrichment
  (author_id, name_as_published, full_name, family, given_full, evidence_dois,
   n_papers_linked, n_papers_checked, n_papers_agreeing)
values
{vals};

do $$
declare n int; stale int; before int;
begin
  select count(*) into n from swrd.author_name_enrichment;
  if n <> {len(rows)} then
    raise exception 'expected {len(rows)} enrichment rows, found %', n;
  end if;
  select count(*) into stale from swrd.author_name_enrichment e
    join swrd.authors a on a.id = e.author_id
   where a.name <> e.name_as_published;
  if stale <> 0 then
    raise exception '% rows whose name_as_published does not match the live name', stale;
  end if;
  select count(*) into before from swrd.authors;
  if before <> 164549 then
    raise exception 'swrd.authors moved: % rows', before;
  end if;
  raise notice 'enrichment loaded: % rows, swrd.authors untouched', n;
end $$;

commit;
""")
    with open(OUT_RB, "w") as f:
        f.write("""-- Reverse of enrich_initials.sql. Nothing else was written, so the rollback
-- destroys nothing observed — the first change in this project for which that
-- is true.
--   psql "$TGT" -v ON_ERROR_STOP=1 -f rollback_enrich_initials.sql
drop table if exists swrd.author_name_enrichment;
""")
    print(f"\n-> {OUT_CSV}\n-> {OUT_SQL}\n-> {OUT_RB}\n-> {OUT_Q}")


if __name__ == "__main__":
    main()
