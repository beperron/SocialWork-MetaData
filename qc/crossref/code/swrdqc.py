"""Shared helpers for the Crossref quality-control pass over SWRD.

Read-only throughout. Nothing here writes to the database; the pipeline's
output is a proposed-corrections file for a maintainer to review and apply
through the normal release procedure in docs/DATA_CHANGELOG.md.
"""
from __future__ import annotations

import gzip
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(ROOT, "cache")

# ---------------------------------------------------------------- SWRD API

SWRD_KEY = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
SWRD_URL = "https://kcffctxedcscvvposypb.supabase.co/rest/v1/rpc/run_sql"


def run_sql(query: str, schema: str = "swrd"):
    """POST read-only SQL to the project API. Returns a list of row dicts."""
    req = urllib.request.Request(
        SWRD_URL,
        data=json.dumps({"query": query}).encode(),
        method="POST",
        headers={
            "apikey": SWRD_KEY,
            "Authorization": f"Bearer {SWRD_KEY}",
            "Content-Profile": schema,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def rows(query: str, schema: str = "swrd"):
    """run_sql, but for queries that return many columns.

    The endpoint flattens multi-row multi-column results, so wrap the query in
    a json_agg and parse it back. Callers write plain SQL and get dicts.
    """
    wrapped = f"select json_agg(row_to_json(t))::text as data from ({query}) t"
    out = run_sql(wrapped, schema)
    payload = out[0]["data"] if isinstance(out[0], dict) else out[0]
    return json.loads(payload) if payload else []


# ------------------------------------------------------------ Crossref API

# Crossref asks that heavy users identify themselves; doing so also moves the
# requests into the faster, more reliable "polite pool".
CONTACT = "beperron@umich.edu"
UA = (
    "SocialWorkMetaData-QC/0.1 "
    f"(https://github.com/beperron/SocialWork-MetaData; mailto:{CONTACT})"
)
# The /works/{doi} route rejects `select`, but /works?filter=doi:... accepts
# both `select` and many DOIs at once — ~50 per call instead of one.
SELECT = ",".join([
    "DOI", "title", "subtitle", "container-title", "ISSN", "type",
    "published-print", "published-online", "issued", "author", "publisher",
    "volume", "issue", "page",
])
BATCH = 40


def _get(url: str, tries: int = 5):
    """GET with backoff. Crossref returns 429/503 under load; both are retryable."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            if exc.code == 404:
                return None
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    return None


def crossref_by_dois(dois: list[str]) -> dict[str, dict]:
    """Look up many DOIs in one call. Returns {lowercased doi: record}."""
    found: dict[str, dict] = {}
    for i in range(0, len(dois), BATCH):
        chunk = [d for d in dois[i:i + BATCH] if d]
        if not chunk:
            continue
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
            "filter": ",".join(f"doi:{d}" for d in chunk),
            "select": SELECT,
            "rows": BATCH,
        })
        msg = _get(url)
        for item in (msg or {}).get("message", {}).get("items", []):
            found[item["DOI"].lower()] = item
        time.sleep(0.12)
    return found


def crossref_search(title: str, year=None, issns=None, rows_n: int = 5):
    """Bibliographic search, for records whose DOI is missing or unusable."""
    params = {"query.bibliographic": title[:300], "select": SELECT, "rows": rows_n}
    filters = []
    if year:
        filters.append(f"from-pub-date:{int(year) - 1}-01-01")
        filters.append(f"until-pub-date:{int(year) + 1}-12-31")
    if issns:
        filters.append(f"issn:{issns[0]}")
    if filters:
        params["filter"] = ",".join(filters)
    msg = _get("https://api.crossref.org/works?" + urllib.parse.urlencode(params))
    time.sleep(0.12)
    return (msg or {}).get("message", {}).get("items", [])


# ------------------------------------------------------------------ cache

def cache_path(name: str) -> str:
    return os.path.join(CACHE, f"{name}.jsonl.gz")


def cache_load(name: str) -> dict:
    path = cache_path(name)
    if not os.path.exists(path):
        return {}
    out = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                out[rec["key"]] = rec["value"]
    return out


def cache_save(name: str, mapping: dict) -> None:
    os.makedirs(CACHE, exist_ok=True)
    with gzip.open(cache_path(name), "wt", encoding="utf-8") as f:
        for k, v in mapping.items():
            f.write(json.dumps({"key": k, "value": v}, ensure_ascii=False) + "\n")


# ------------------------------------------------------- matching helpers

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
OAI_JSSW_RE = re.compile(r"^oai:scholarworks\.wmich\.edu:jssw-(\d+)$", re.I)
# Crossref stores many book reviews with a "Book Review:" prefix that the
# source record does not carry. Strip such prefixes before comparing titles.
PREFIX_RE = re.compile(
    r"^\s*(book\s+review|review\s+essay|reviews?|editorial|erratum|correction)\s*[:\-—]\s*",
    re.I,
)


def is_valid_doi(value) -> bool:
    return bool(value) and bool(DOI_RE.match(str(value).strip()))


def norm_title(s: str) -> str:
    s = html.unescape(s or "")
    s = PREFIX_RE.sub("", s)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def title_sim(a: str, b: str) -> float:
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    # A source title truncated by the publisher should not read as a mismatch.
    if na.startswith(nb) or nb.startswith(na):
        # One title is a prefix of the other — usually a subtitle truncated on
        # our side. Scale by how much text is actually shared, rather than
        # returning a flat high score: "Responding to Child Maltreatment" is a
        # prefix of the issue editorial AND of the real article, and a flat 0.97
        # made them indistinguishable, so result order decided. Long shared
        # prefixes still score high; short ones no longer masquerade as matches.
        return max(0.75, min(0.97, len(nb) / len(na) if len(na) > len(nb)
                             else len(na) / len(nb)))
    return SequenceMatcher(None, na, nb).ratio()


def norm_journal(s: str) -> str:
    """Normalise a journal name for comparison across sources."""
    s = html.unescape(s or "").lower().replace("&", " and ")
    s = re.sub(r"^(the)\s+", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def journal_match(our_issns, their_issns, our_name, their_name):
    """Do we and Crossref agree on which journal this is?

    Returns (verdict, basis) where verdict is match / mismatch / unknown.

    ISSN decides it whenever both sides have one — that is the whole point of
    the identifier. Name comparison is the fallback, and it has to tolerate the
    ways the same journal gets written down:

      case and punctuation      'Health & Social Work' vs 'Health and Social Work'
      a leading article         'The Journal of ...' vs 'Journal of ...'
      truncation on one side    prefix match
      bilingual titles reordered
          'Global Social Work / Trabajo Social Global'
          'Trabajo Social Global-Global Social Work'
      ...which are the same journal with the halves swapped, so an ordered
      comparison scores them as different while a token set sees the match.
    """
    ours = {s.strip().upper() for s in (our_issns or []) if s}
    theirs = {s.strip().upper() for s in (their_issns or []) if s}
    if ours and theirs:
        return ("match" if ours & theirs else "mismatch"), "issn"

    a, b = norm_journal(our_name), norm_journal(their_name)
    if not b:
        return "unknown", "no_container_title"
    if a == b or a.startswith(b) or b.startswith(a) or title_sim(a, b) >= 0.85:
        return "match", "name"
    if set(a.split()) == set(b.split()):
        return "match", "name_tokens"
    return "mismatch", "name"


_DIGITS = re.compile(r"\d+")


def digits_conflict(a: str, b: str) -> bool:
    """True when two titles carry different numbers.

    Serial titles differ by a single character — "Letter from the Editors (5)"
    against "(7)" scores 0.98 on any string metric and is a different article.
    Numbers in a title are load-bearing, so a difference in them is disqualifying
    regardless of similarity. Only compares when both sides have digits.
    """
    da, db = _DIGITS.findall(a or ""), _DIGITS.findall(b or "")
    if not da or not db:
        return False
    return [x.lstrip("0") or "0" for x in da] != [x.lstrip("0") or "0" for x in db]


def name_tokens(s: str) -> set[str]:
    """Every meaningful token in a personal name, lowercased.

    Isolating "the surname" cannot work across the formats SWRD holds and the
    compound and non-Western names it contains -- de Jesus, Van Wormer, Rios
    Campos, Truong Thi. Comparing token sets sidesteps the problem: a match on
    any substantive token is evidence, and initials are dropped as noise.
    """
    out = set()
    for tok in re.split(r"[\s,;.]+", (s or "").lower()):
        tok = re.sub(r"[^a-z\u00c0-\u024f]", "", tok)
        if len(tok) > 2:
            out.add(tok)
    return out


def cr_title(item: dict) -> str:
    t = (item.get("title") or [""])[0]
    sub = (item.get("subtitle") or [""])[0]
    return f"{t}: {sub}" if sub and sub.lower() not in t.lower() else t


def cr_years(item: dict) -> set[int]:
    """Every year Crossref associates with the item.

    Online-first publishing means the print year and the online year routinely
    differ, so a single 'correct' year does not exist. Matching against any of
    them is the only defensible rule.
    """
    years = set()
    for field in ("published-print", "published-online", "issued", "created"):
        parts = (item.get(field) or {}).get("date-parts") or []
        for p in parts:
            if p and p[0]:
                years.add(int(p[0]))
    return years


def cr_issns(item: dict) -> set[str]:
    return {s.strip().upper() for s in (item.get("ISSN") or []) if s}


def cr_surnames(item: dict) -> set[str]:
    out = set()
    for a in item.get("author") or []:
        fam = (a.get("family") or "").strip().lower()
        if fam:
            out.add(re.sub(r"[^a-z]", "", fam))
    return out


_INITIALS = re.compile(r"^[A-Za-z]\.?([A-Za-z]\.?)?$")


def swrd_name_tokens(authors: str) -> set[str]:
    """All name tokens across every SWRD author on a record."""
    out = set()
    for chunk in (authors or "").split(";"):
        out |= name_tokens(chunk)
    return out


def cr_name_tokens(item: dict) -> set[str]:
    """All name tokens across every Crossref author, family and given."""
    out = set()
    for a in item.get("author") or []:
        out |= name_tokens(a.get("family", "")) | name_tokens(a.get("given", ""))
    return out


def swrd_surnames(authors: str) -> set[str]:
    """Take the surname out of each SWRD author string.

    SWRD stores names exactly as published, and this corpus contains three
    different orderings — assuming any one of them silently returns nonsense:

        "GILLILAND, D"     surname first, comma
        "Gilliland D."     surname first, no comma, trailing initials
        "Fiona Gardner"    given name first

    An earlier version split on the comma only, so given-name-first strings came
    back as whole names ('richfurman') and never matched a Crossref `family`
    field. That made author overlap read as 0.0 for entire journals.
    """
    out = set()
    for chunk in (authors or "").split(";"):
        name = re.sub(r"\s+", " ", chunk.strip().strip(".,"))
        if not name:
            continue
        if "," in name:
            fam = name.split(",")[0]
        else:
            parts = name.split()
            if len(parts) == 1:
                fam = parts[0]
            elif _INITIALS.match(parts[-1]):
                fam = " ".join(parts[:-1])      # trailing initial -> surname led
            else:
                fam = parts[-1]                 # given name led
        fam = re.sub(r"[^a-z]", "", fam.lower())
        if fam:
            out.add(fam)
    return out


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
