#!/usr/bin/env python3
"""
Step 1b — the semantic recall audit: find the articles the keyword net missed
because they describe the topic in words nobody thought to search for.

Keyword search matches strings. Semantic search matches *meaning*: every
abstract in the database is stored as a 768-dimension vector, and a question
embedded the same way retrieves its nearest neighbours regardless of wording.
That is how this corpus recovered pre-2000 articles that describe
"computer-based statistical models" or "automated assessment" and never once
say "artificial intelligence".

THE EMBEDDING MODEL — this matters, and there is no substitute
-------------------------------------------------------------
  model      embeddinggemma:300m   (Google EmbeddingGemma, 300M parameters)
  dimensions 768
  served by  Ollama, locally, at http://localhost:11434
  size       ~620 MB, downloaded once

Both databases' abstracts were embedded with THIS model. A query vector from
any other model — OpenAI, Cohere, a different Gemma, even a different
quantisation of a similar size — is not comparable and returns noise. There is
no server-side embedding endpoint: you generate the query vector locally.

The model was chosen by benchmarking on this corpus: every embedding model
tested beat keyword retrieval, open-weight models matched or exceeded
commercial APIs, and EmbeddingGemma had the best quality-to-size ratio.

REQUIRED PROMPT PREFIX
----------------------
EmbeddingGemma is trained with task prefixes. Queries must be embedded as

    task: search result | query: {your question}

Documents were embedded as `title: {title} | text: {abstract}` — already done.
Omitting the query prefix degrades results badly; it is the single most common
mistake.

SETUP
-----
    # macOS:  brew install ollama      (or https://ollama.com/download)
    # Linux:  curl -fsSL https://ollama.com/install.sh | sh
    ollama pull embeddinggemma:300m
    ollama serve            # if it is not already running

    python3 semantic_audit.py
"""
import json, os, sys
import urllib.request, urllib.error

KEY    = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE   = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
OLLAMA = "http://localhost:11434"
MODEL  = "embeddinggemma:300m"
DIMS   = 768
HERE   = os.path.dirname(__file__)
CORPUS = os.path.join(HERE, "..", "data", "ai_corpus_labeled.json")
OUT    = os.path.join(HERE, "..", "data", "semantic_audit_candidates.json")

# Natural-language statements of what the corpus is about. Several phrasings are
# used because each probes a different direction in the embedding space, and the
# search function returns at most ~40 rows per call regardless of match_count —
# unioning phrasings is how you retrieve a deeper neighbourhood.
STATEMENTS = [
    "applications of artificial intelligence, machine learning, and expert systems in social work practice",
    "predictive risk modeling, algorithmic decision-making, and automated decision support in human services",
    "social workers' and students' attitudes toward chatbots, generative AI, and social robots",
    "computer-based decision aids and automated assessment tools for caseworkers",
]
SIM_FLOOR = 0.50

def post(url, payload, headers):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 method="POST", headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def preflight():
    """Check Ollama is running and the exact model is present before doing work."""
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/version", timeout=4) as r:
            json.loads(r.read())
    except Exception:
        sys.exit(f"Ollama is not reachable at {OLLAMA}.\n"
                 f"  Install: https://ollama.com/download   then:  ollama serve")
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=6) as r:
            tags = [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        tags = []
    if not any(t.startswith(MODEL.split(":")[0]) for t in tags):
        sys.exit(f"The model {MODEL} is not installed.\n  Run:  ollama pull {MODEL}")
    v = embed("test")
    if len(v) != DIMS:
        sys.exit(f"Expected {DIMS} dimensions, got {len(v)} — wrong model.")
    print(f"embedding endpoint ok — {MODEL}, {DIMS} dimensions")

def embed(text):
    out = post(f"{OLLAMA}/api/embed",
               {"model": MODEL, "input": [f"task: search result | query: {text}"]},
               {"Content-Type": "application/json"})
    return out["embeddings"][0]

def semantic_search(vec, match_count=100, min_year=1989):
    return post(f"{BASE}/rpc/search_papers_semantic",
                {"query_embedding": vec, "match_count": match_count, "min_year": min_year},
                {"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Profile": "swrd", "Content-Type": "application/json"})

def main():
    preflight()
    with open(CORPUS) as f:
        have = {r["id"] for r in json.load(f) if r["source"] == "swrd"}
    print(f"corpus already holds {len(have)} database records\n")

    found = {}
    for s in STATEMENTS:
        hits = semantic_search(embed(s))
        new = [h for h in hits if h["similarity"] >= SIM_FLOOR and h["id"] not in have]
        for h in new:
            found.setdefault(h["id"], h)
        print(f"  {len(hits):3d} hits (>= {SIM_FLOOR}: {sum(1 for h in hits if h['similarity'] >= SIM_FLOOR):3d}) "
              f"| {len(new):3d} not already in corpus | {s[:58]}…")

    ranked = sorted(found.values(), key=lambda h: -h["similarity"])
    with open(OUT, "w") as f:
        json.dump(ranked, f, indent=1)
    print(f"\n{len(ranked)} candidates for review -> {os.path.relpath(OUT)}")
    print("\nA similarity score is a hypothesis, not a finding: read every candidate's")
    print("abstract and admit it only with a note naming the vocabulary gap that")
    print("explains why the keyword net missed it. Most will be near-neighbours that")
    print("do not belong — in this corpus, roughly one in ten was a genuine recovery.\n")
    for h in ranked[:10]:
        print(f"  {h['similarity']:.3f}  {h['publication_year']}  {h['title'][:76]}")

if __name__ == "__main__":
    main()
