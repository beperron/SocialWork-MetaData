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

# The system prompt IS the published skill files, verbatim — the same documents
# any user hands to their assistant — plus a strict output-format footer.
import pathlib as _pl
_repo = _pl.Path(__file__).resolve().parent.parent
SYSTEM = (
    (_repo / "skills/swrd-database-skill.md").read_text()
    + "\n\n---\n\n"
    + (_repo / "skills/sswr-database-skill.md").read_text()
    + "\n\n---\n\nYou are answering research questions against these two databases. "
      "Respond with a SINGLE SQL SELECT statement and nothing else — no explanation, "
      "no markdown fences, no semicolon. Schema-qualify all tables (swrd.papers, sswr.papers)."
)

QUESTIONS = [
  # ============ A · Simple retrieval & counts ============
  {"cat": "A · Simple retrieval", "q": "How many records does the SWRD papers table contain in total, across all years including the historical supplement?",
   "truth_sql": "select count(*) as n from swrd.papers"},
  {"cat": "A · Simple retrieval", "q": "How many SWRD records are from before 1989?",
   "truth_sql": "select count(*) as n from swrd.papers where publication_year < 1989"},
  {"cat": "A · Simple retrieval", "q": "How many journals are in the SWRD's journal list?",
   "truth_sql": "select count(*) as n from swrd.journals"},
  {"cat": "A · Simple retrieval", "q": "How many SWRD articles, across all years, were published in the journal named 'Child & Family Social Work'?",
   "truth_sql": "select count(*) as n from swrd.papers p join swrd.journals j on j.id=p.journal_id where j.name = 'Child & Family Social Work'"},
  {"cat": "A · Simple retrieval", "q": "How many presentations were given at the 2024 SSWR conference?",
   "truth_sql": "select count(*) as n from sswr.papers where year = 2024"},
  {"cat": "A · Simple retrieval", "q": "How many presentations does the SSWR database contain in total?",
   "truth_sql": "select count(*) as n from sswr.papers"},
  {"cat": "A · Simple retrieval", "q": "How many canonical (disambiguated) authors are in the SSWR authors table?",
   "truth_sql": "select count(*) as n from sswr.authors"},
  {"cat": "A · Simple retrieval", "q": "How many presentations were given at the 2005 SSWR conference?",
   "truth_sql": "select count(*) as n from sswr.papers where year = 2005"},

  # ============ B · Vocabulary & schema fidelity ============
  {"cat": "B · Vocabulary fidelity", "q": "List the exact distinct values of the research_method field in the SWRD.",
   "truth_sql": "select distinct research_method from swrd.papers where research_method is not null"},
  {"cat": "B · Vocabulary fidelity", "q": "How many SWRD articles, across all years, have research_method 'Mixed-Methods'?",
   "truth_sql": "select count(*) as n from swrd.papers where research_method = 'Mixed-Methods'"},
  {"cat": "B · Vocabulary fidelity", "q": "How many SWRD articles, across all years, have research_method 'Review'?",
   "truth_sql": "select count(*) as n from swrd.papers where research_method = 'Review'"},
  {"cat": "B · Vocabulary fidelity", "q": "How many SWRD articles, across all years, are flagged scientific but NOT flagged empirical?",
   "truth_sql": "select count(*) as n from swrd.papers where is_scientific and not is_empirical"},
  {"cat": "B · Vocabulary fidelity", "q": "List the exact distinct values of the methodology field in the SSWR database.",
   "truth_sql": "select distinct methodology from sswr.papers where methodology is not null"},
  {"cat": "B · Vocabulary fidelity", "q": "How many SSWR presentations have methodology 'other'?",
   "truth_sql": "select count(*) as n from sswr.papers where methodology = 'other'"},
  {"cat": "B · Vocabulary fidelity", "q": "How many SSWR presentations have methodology 'mixed_methods'?",
   "truth_sql": "select count(*) as n from sswr.papers where methodology = 'mixed_methods'"},
  {"cat": "B · Vocabulary fidelity", "q": "How many distinct values does the format field take in the SSWR papers table?",
   "truth_sql": "select count(distinct format) as n from sswr.papers where format is not null"},

  # ============ C · Joins & relational reasoning ============
  {"cat": "C · Joins & relations", "q": "Which journal has published the most SWRD articles from 1989 onward, and how many?",
   "truth_sql": "select j.name, count(*) as n from swrd.papers p join swrd.journals j on j.id=p.journal_id where p.publication_year>=1989 group by 1 order by 2 desc limit 1"},
  {"cat": "C · Joins & relations", "q": "How many SWRD articles from 1989 onward appeared in the journal named 'Research on Social Work Practice'?",
   "truth_sql": "select count(*) as n from swrd.papers p join swrd.journals j on j.id=p.journal_id where j.name = 'Research on Social Work Practice' and p.publication_year >= 1989"},
  {"cat": "C · Joins & relations", "q": "How many distinct organizations are linked (via author affiliations) to SWRD papers published in 2020?",
   "truth_sql": "select count(distinct aa.organization_id) as n from swrd.author_affiliations aa join swrd.papers p on p.id = aa.paper_id where p.publication_year = 2020"},
  {"cat": "C · Joins & relations", "q": "How many SWRD authorship records (paper-author links) exist for papers published in 2019?",
   "truth_sql": "select count(*) as n from swrd.paper_authors pa join swrd.papers p on p.id = pa.paper_id where p.publication_year = 2019"},
  {"cat": "C · Joins & relations", "q": "Which single institution had the most first-authored SSWR presentations between 2020 and 2026, using the normalized institution field? Give the institution and the count.",
   "truth_sql": "select pa.institution_normalized, count(*) as n from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id where pa.author_order = 1 and p.year between 2020 and 2026 group by 1 order by 2 desc limit 1"},
  {"cat": "C · Joins & relations", "q": "How many presentations is the SSWR canonical author with id 108089 linked to?",
   "truth_sql": "select count(*) as n from sswr.paper_authors where author_id = 108089"},
  {"cat": "C · Joins & relations", "q": "How many distinct canonical authors are linked to presentations at the 2015 SSWR conference?",
   "truth_sql": "select count(distinct pa.author_id) as n from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id where p.year = 2015"},
  {"cat": "C · Joins & relations", "q": "How many first-authored SSWR presentations, across all years, list 'University of Michigan' as the normalized institution?",
   "truth_sql": "select count(*) as n from sswr.paper_authors pa where pa.author_order = 1 and pa.institution_normalized = 'University of Michigan'"},

  # ============ D · Aggregation & trends ============
  {"cat": "D · Aggregation & trends", "q": "Between 1989 and 2023, which single publication year had the most SWRD scientific articles with abstracts?",
   "truth_sql": "select publication_year from swrd.papers where publication_year between 1989 and 2023 and is_scientific and abstract is not null group by 1 order by count(*) desc limit 1"},
  {"cat": "D · Aggregation & trends", "q": "How many SWRD scientific articles with abstracts were published in 2020 and flagged empirical?",
   "truth_sql": "select count(*) as n from swrd.papers where publication_year = 2020 and is_scientific and abstract is not null and is_empirical"},
  {"cat": "D · Aggregation & trends", "q": "How many SWRD scientific articles with abstracts were published between 2010 and 2019 inclusive?",
   "truth_sql": "select count(*) as n from swrd.papers where publication_year between 2010 and 2019 and is_scientific and abstract is not null"},
  {"cat": "D · Aggregation & trends", "q": "What is the mean number of authors per SWRD paper for papers published from 1989 onward, rounded to 2 decimal places?",
   "truth_sql": "select round(avg(a.n),2) as mean_authors from (select paper_id, count(*) as n from swrd.paper_authors group by 1) a join swrd.papers p on p.id = a.paper_id where p.publication_year >= 1989"},
  {"cat": "D · Aggregation & trends", "q": "What is the earliest SSWR conference year with more than 1,000 presentations?",
   "truth_sql": "select min(year) as y from (select year, count(*) as c from sswr.papers group by 1) t where c > 1000"},
  {"cat": "D · Aggregation & trends", "q": "Which SSWR conference year had the most presentations overall?",
   "truth_sql": "select year from sswr.papers group by year order by count(*) desc limit 1"},
  {"cat": "D · Aggregation & trends", "q": "How many presentations at the 2010 SSWR conference used qualitative methods?",
   "truth_sql": "select count(*) as n from sswr.papers where year = 2010 and methodology = 'qualitative'"},
  {"cat": "D · Aggregation & trends", "q": "Which SSWR conference year had the most mixed_methods presentations?",
   "truth_sql": "select year from sswr.papers where methodology = 'mixed_methods' group by year order by count(*) desc limit 1"},

  # ============ E · Search-function usage ============
  {"cat": "E · Search functions", "q": "Using the SWRD keyword search function, what is the id of the top-ranked article about 'food insecurity'?",
   "truth_sql": "select id from swrd.search_papers_keyword('food insecurity', 1)"},
  {"cat": "E · Search functions", "q": "Using the SWRD keyword search function with match_count 20, how many of the top 20 results for 'homelessness' were published in 2015 or later?",
   "truth_sql": "select count(*) as n from swrd.search_papers_keyword('homelessness', 20) where publication_year >= 2015"},
  {"cat": "E · Search functions", "q": "Using the SWRD keyword search function, which journal published the top-ranked article for 'child welfare workforce turnover'?",
   "truth_sql": "select journal_name from swrd.search_papers_keyword('child welfare workforce turnover', 1)"},
  {"cat": "E · Search functions", "q": "Using the SWRD keyword search function with match_count 10, how many of the top 10 results for 'social work education' appeared in the journal named 'Journal of Social Work Education'?",
   "truth_sql": "select count(*) as n from swrd.search_papers_keyword('social work education', 10) where journal_name = 'Journal of Social Work Education'"},
  {"cat": "E · Search functions", "q": "Using the SSWR keyword search function, what is the id of the top-ranked presentation about 'opioid overdose'?",
   "truth_sql": "select id from sswr.search_papers_keyword('opioid overdose', 1)"},
  {"cat": "E · Search functions", "q": "Using the SSWR keyword search function with match_count 20, how many of the top 20 results for 'food insecurity' are from year 2020 or later?",
   "truth_sql": "select count(*) as n from sswr.search_papers_keyword('food insecurity', 20) where year >= 2020"},
  {"cat": "E · Search functions", "q": "Using the SSWR keyword search function, in what year was the top-ranked presentation about 'artificial intelligence' given?",
   "truth_sql": "select year from sswr.search_papers_keyword('artificial intelligence', 1)"},
  {"cat": "E · Search functions", "q": "Using the SSWR keyword search function with match_count 15, how many of the top 15 results for 'telehealth' use quantitative methodology?",
   "truth_sql": "select count(*) as n from sswr.search_papers_keyword('telehealth', 15) where methodology = 'quantitative'"},

  # ============ F · Complex analytical ============
  {"cat": "F · Complex analytical", "q": "Among SWRD journals with at least 1,000 articles from 1989 onward, which journal has the highest proportion of Qualitative articles among its empirical articles? Give the journal name.",
   "truth_sql": "select j.name from swrd.papers p join swrd.journals j on j.id = p.journal_id where p.publication_year >= 1989 and p.is_empirical group by j.id, j.name having count(*) filter (where true) >= 0 and (select count(*) from swrd.papers p2 where p2.journal_id = j.id and p2.publication_year >= 1989) >= 1000 order by (count(*) filter (where p.research_method = 'Qualitative'))::float / count(*) desc limit 1"},
  {"cat": "F · Complex analytical", "q": "How many SWRD papers from 1989 onward have more than 5 authors (based on authorship records)?",
   "truth_sql": "select count(*) as n from (select pa.paper_id, count(*) as c from swrd.paper_authors pa join swrd.papers p on p.id = pa.paper_id where p.publication_year >= 1989 group by 1 having count(*) > 5) t"},
  {"cat": "F · Complex analytical", "q": "Between 1989 and 2023, which single publication year had the most SWRD articles with research_method 'Review'?",
   "truth_sql": "select publication_year from swrd.papers where publication_year between 1989 and 2023 and research_method = 'Review' group by 1 order by count(*) desc limit 1"},
  {"cat": "F · Complex analytical", "q": "How many SWRD journals published at least one article in 1989 AND at least one article in 2025?",
   "truth_sql": "select count(*) as n from (select journal_id from swrd.papers where publication_year = 1989 intersect select journal_id from swrd.papers where publication_year = 2025) t"},
  {"cat": "F · Complex analytical", "q": "Which SSWR canonical author (give the name) had the most first-authored presentations between 2010 and 2015?",
   "truth_sql": "select a.name from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id join sswr.authors a on a.id = pa.author_id where pa.author_order = 1 and p.year between 2010 and 2015 group by a.id, a.name order by count(*) desc limit 1"},
  {"cat": "F · Complex analytical", "q": "How many SSWR canonical authors presented at BOTH the 2005 and 2026 conferences?",
   "truth_sql": "select count(*) as n from (select pa.author_id from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id where p.year = 2005 intersect select pa.author_id from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id where p.year = 2026) t"},
  {"cat": "F · Complex analytical", "q": "Which SSWR conference year had the largest number of distinct normalized institutions among first authors?",
   "truth_sql": "select p.year from sswr.paper_authors pa join sswr.papers p on p.id = pa.paper_id where pa.author_order = 1 and pa.institution_normalized is not null group by p.year order by count(distinct pa.institution_normalized) desc limit 1"},
  {"cat": "F · Complex analytical", "q": "How many SSWR presentations have more than 6 authors (based on authorship records)?",
   "truth_sql": "select count(*) as n from (select paper_id, count(*) as c from sswr.paper_authors group by 1 having count(*) > 6) t"},
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
    }, timeout=int(os.environ.get("OLLAMA_TIMEOUT", "600")))
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
    args = sys.argv[1:]
    only = None                       # --only 35,42  → rerun just those questions (1-based), merge into existing answers
    if "--only" in args:
        k = args.index("--only")
        only = [int(x) - 1 for x in args[k + 1].split(",")]
        args = args[:k] + args[k + 2:]
    models = args
    truths = []
    for item in QUESTIONS:
        truths.append(values_of(run_sql(item["truth_sql"])))
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval_results.json")
    if os.path.exists(out_path):
        results = json.load(open(out_path))
        results["questions"] = [q["q"] for q in QUESTIONS]
        results["categories"] = [q["cat"] for q in QUESTIONS]
    else:
        results = {"questions": [q["q"] for q in QUESTIONS], "categories": [q["cat"] for q in QUESTIONS], "models": {}}
    for model in models:
        prev = results["models"].get(model, {}).get("answers")
        if only is not None:
            if not prev or len(prev) != len(QUESTIONS):
                print(f"[{model}] --only requires existing full results; skipping", flush=True)
                continue
            per_q = list(prev)
            idxs = only
        else:
            per_q = [None] * len(QUESTIONS)
            idxs = range(len(QUESTIONS))
        for i in idxs:
            item = QUESTIONS[i]
            t0 = time.time()
            rows = None
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
            per_q[i] = {"ok": ok, "sql": sql, "detail": detail, "secs": round(time.time()-t0, 1), "rows": (rows[:3] if isinstance(rows, list) else rows)}
            print(f"[{model}] Q{i+1} {'PASS' if ok else 'FAIL'} ({per_q[-1]['secs']}s) {detail[:100]}", flush=True)
        score = sum(1 for r in per_q if r["ok"])
        results["models"][model] = {"score": score, "total": len(QUESTIONS), "answers": per_q}
        print(f"[{model}] TOTAL {score}/{len(QUESTIONS)}", flush=True)
    json.dump(results, open(out_path, "w"), indent=1)
    print("wrote", out_path)

if __name__ == "__main__":
    main()
