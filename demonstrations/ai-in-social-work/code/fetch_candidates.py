#!/usr/bin/env python3
"""
Step 1 of the demonstration — retrieval.

Casts the era-spanning keyword net over the SWRD journal database and writes
every candidate record (id, year, title, abstract, journal) to
data/candidates_raw.json for screening.

No credentials, no setup: the database is hosted and read-only, and the key
below is public by design.

    python3 fetch_candidates.py

Screening (deciding which candidates are genuinely about AI) is the step this
script does NOT do — that requires reading every abstract. See the README.
"""
import json, os, sys
import urllib.request

KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
OUT  = os.path.join(os.path.dirname(__file__), "..", "data", "candidates_raw.json")

# Era-spanning vocabulary. Word-boundary anchors (\m ... \M) matter enormously:
# an unanchored "ai" matches "AI/AN" (American Indian/Alaska Native), "Appreciative
# Inquiry", the Italian preposition "ai", and author initials.
PATTERNS = [
    # 1st wave — expert systems / knowledge-based systems
    r"expert system", r"knowledge[- ]based system", r"knowledge acquisition",
    r"case[- ]based reasoning", r"inference engine", r"production rule",
    r"decision support system", r"decision aid", r"computer[- ]assisted decision",
    # 2nd wave — statistical learning
    r"artificial intelligence", r"\mAI\M", r"\mA\.I\.\M",
    r"machine learning", r"neural network", r"deep learning",
    r"predictive analytic", r"predictive risk model", r"predictive model",
    r"random forest", r"support vector", r"decision tree", r"classification and regression tree",
    r"natural language processing", r"\mNLP\M", r"text mining", r"data mining",
    r"sentiment analysis", r"topic model", r"computer vision", r"facial recognition",
    r"algorithmic", r"algorithmically", r"automated decision",
    # 3rd wave — generative
    r"generative a\.?i", r"large language model", r"\mLLMs?\M", r"chatgpt", r"\mGPT-?[0-9]",
    r"chatbot", r"conversational agent", r"foundation model", r"transformer model",
    r"social robot", r"socially assistive robot", r"robotic process automation",
]

def run_sql(query, schema="swrd"):
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        f"{BASE}/rpc/run_sql", data=body, method="POST",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Profile": schema, "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def main():
    regex = "(" + "|".join(PATTERNS) + ")"
    sql = f"""
      select p.id, p.publication_year as year, p.title, p.abstract, p.doi,
             j.name as journal
      from swrd.papers p
      left join swrd.journals j on j.id = p.journal_id
      where p.publication_year >= 1989
        and (coalesce(p.title,'') || ' ' || coalesce(p.abstract,'')) ~* '{regex}'
      order by p.publication_year, p.id
    """.replace("\n", " ")
    rows = run_sql(sql)
    if isinstance(rows, dict) and rows.get("message"):
        sys.exit(f"database error: {rows['message']}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rows, f, indent=1)
    print(f"{len(rows)} candidate records -> {os.path.relpath(OUT)}")
    print("Roughly half will be false positives. Every one must be read; see README.md.")

if __name__ == "__main__":
    main()
