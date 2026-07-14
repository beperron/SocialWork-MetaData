#!/usr/bin/env python3
"""Evaluate whether small local LLMs (via Ollama) can answer research questions
against the live databases by writing SQL executed through the PUBLIC run_sql
endpoint — the same pipeline the skill files give to any assistant.

Usage: python 08_eval_local_models.py model1 [model2 ...]
Writes results to eval_results.json in the repo root.
"""
import json, re, sys, time, os
import requests

KEY  = "sb_publishable_RY5wIh9k-D_41VZJdtCv7Q_NV--EQP5"
BASE = "https://kcffctxedcscvvposypb.supabase.co/rest/v1"
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
     "Content-Profile": "swrd", "Content-Type": "application/json"}

SYSTEM = """You write SQL for a read-only PostgreSQL database of social work research. Respond with a SINGLE SQL SELECT statement and nothing else — no explanation, no markdown fences, no semicolon.

DATABASE 1 — swrd (journal articles; always schema-qualify: swrd.papers):
- swrd.papers: id, doi, title, abstract, publication_year, journal_id, document_type, open_access, is_scientific (bool), is_empirical (bool), research_method (values exactly: 'Quantitative','Qualitative','Mixed-Methods','Review')
- swrd.journals: id, name  |  join: papers.journal_id = journals.id
- The SWRD's core corpus = publication_year >= 1989 AND is_scientific AND abstract IS NOT NULL. Records before 1989 are an incomplete historical supplement.
- swrd.search_papers_keyword(query_text, match_count) returns ranked full-text matches (id, title, abstract, publication_year, journal_name, rank).

DATABASE 2 — sswr (conference presentations; schema-qualify: sswr.papers):
- sswr.papers: id (text like '2019-O-0142'), year, title, abstract, format, methodology (values exactly: 'quantitative','qualitative','mixed_methods','review','other')
- sswr.authors: id, name, total_papers — canonical, disambiguated author identities
- sswr.paper_authors: paper_id, author_id, author_order (1 = first author), institution_normalized
- sswr.search_papers_keyword(query_text, match_count) returns ranked full-text matches (id, title, abstract, year, methodology, rank, authors).

Rules: single SELECT only; no semicolon; use the exact label capitalizations shown."""

QUESTIONS = [
  {"q": "How many research articles with abstracts does the SWRD contain from 1989 onward? (research articles = flagged scientific)",
   "truth_sql": "select count(*) as n from swrd.papers where publication_year >= 1989 and is_scientific and abstract is not null"},
  {"q": "Which journal has published the most articles in the SWRD (1989 onward), and how many?",
   "truth_sql": "select j.name, count(*) as n from swrd.papers p join swrd.journals j on j.id=p.journal_id where p.publication_year>=1989 group by 1 order by 2 desc limit 1"},
  {"q": "How many SWRD articles from 1989 onward mention 'kinship care' in the title or abstract?",
   "truth_sql": "select count(*) as n from swrd.papers where publication_year >= 1989 and (title ilike '%kinship care%' or abstract ilike '%kinship care%')"},
  {"q": "How many empirical articles in the SWRD used qualitative methods?",
   "truth_sql": "select count(*) as n from swrd.papers where is_empirical and research_method = 'Qualitative'"},
  {"q": "How many presentations were given at the 2024 SSWR conference?",
   "truth_sql": "select count(*) as n from sswr.papers where year = 2024"},
  {"q": "How many SSWR presentations used mixed methods?",
   "truth_sql": "select count(*) as n from sswr.papers where methodology = 'mixed_methods'"},
  {"q": "Who are the three most prolific presenters in the SSWR database, by total presentations?",
   "truth_sql": "select name from sswr.authors order by total_papers desc limit 3"},
  {"q": "Using the SSWR keyword search function, what is the id of the top-ranked presentation about 'opioid overdose'?",
   "truth_sql": "select id from sswr.search_papers_keyword('opioid overdose', 1)"},
]

def run_sql(q):
    r = requests.post(f"{BASE}/rpc/run_sql", headers=H, json={"query": q}, timeout=60)
    if r.status_code != 200:
        return {"error": r.json().get("message", r.text[:200])}
    return r.json()

def ollama_sql(model, question):
    r = requests.post("http://localhost:11434/api/chat", json={
        "model": model, "stream": False,
        "options": {"temperature": 0},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": question}],
    }, timeout=600)
    r.raise_for_status()
    text = r.json()["message"]["content"]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)      # strip reasoning tags
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.S)      # strip fences if any
    sql = (m.group(1) if m else text).strip().rstrip(";").strip()
    m2 = re.search(r"(select\b.*)$", sql, flags=re.S | re.I)        # take from first SELECT
    return (m2.group(1).strip() if m2 else sql), text

def values_of(rows):
    vals = set()
    if isinstance(rows, list):
        for r in rows:
            if isinstance(r, dict):
                for v in r.values():
                    vals.add(str(v).strip().lower())
    return vals

def main():
    models = sys.argv[1:]
    truths = []
    for item in QUESTIONS:
        truths.append(values_of(run_sql(item["truth_sql"])))
    results = {"questions": [q["q"] for q in QUESTIONS], "models": {}}
    for model in models:
        per_q = []
        for i, item in enumerate(QUESTIONS):
            t0 = time.time()
            try:
                sql, raw = ollama_sql(model, item["q"])
                rows = run_sql(sql)
                if isinstance(rows, dict) and "error" in rows:
                    ok, detail = False, f"SQL error: {rows['error'][:120]}"
                else:
                    got = values_of(rows)
                    ok = bool(truths[i] & got)
                    detail = "correct" if ok else f"expected one of {sorted(truths[i])[:3]}, got {sorted(got)[:3]}"
            except Exception as e:
                sql, ok, detail = "", False, f"harness error: {e}"
            per_q.append({"ok": ok, "sql": sql, "detail": detail, "secs": round(time.time()-t0, 1)})
            print(f"[{model}] Q{i+1} {'PASS' if ok else 'FAIL'} ({per_q[-1]['secs']}s) {detail[:100]}", flush=True)
        score = sum(1 for r in per_q if r["ok"])
        results["models"][model] = {"score": score, "total": len(QUESTIONS), "answers": per_q}
        print(f"[{model}] TOTAL {score}/{len(QUESTIONS)}", flush=True)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval_results.json")
    json.dump(results, open(out, "w"), indent=1)
    print("wrote", out)

if __name__ == "__main__":
    main()
