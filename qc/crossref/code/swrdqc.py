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
        return 0.97
    return SequenceMatcher(None, na, nb).ratio()


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


def swrd_surnames(authors: str) -> set[str]:
    """SWRD stores 'Surname, Given; Surname, Given'. Take the surnames."""
    out = set()
    for chunk in (authors or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        fam = chunk.split(",")[0].strip().lower()
        fam = re.sub(r"[^a-z]", "", fam)
        if fam:
            out.add(fam)
    return out


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
