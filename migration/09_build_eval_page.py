#!/usr/bin/env python3
"""Build evaluation.html from eval_results.json.

Layered presentation: headline stats → model summary → category scores →
six expandable category sections, each question further expandable to show
the reference answer and every model's verbatim SQL and outcome.
Post-hoc failure classifications live in eval_defensible.json
as [[model, question_index], ...] — those cells render △ instead of ✗.
"""
import json, html, os, datetime, importlib.util

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
r = json.load(open(os.path.join(repo, "eval_results.json")))
try:
    DEFENSIBLE = {tuple(x) for x in json.load(open(os.path.join(repo, "eval_defensible.json")))}
except FileNotFoundError:
    DEFENSIBLE = set()

spec = importlib.util.spec_from_file_location("ev", os.path.join(repo, "migration/08_eval_local_models.py"))
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)

MODELS = [
  ("granite4.1:3b",            "IBM Granite 4.1 3B", "3B dense",             "2.1 GB"),
  ("ornith:9b",                "Ornith 9B",          "9B dense",             "5.6 GB"),
  ("gemma4:26b",               "Google Gemma 4 26B", "26B dense",            "16 GB"),
  ("qwen3.6:27b",              "Qwen3.6-27B",        "27B dense",            "17 GB"),
  ("nemotron-cascade-2:latest","NVIDIA Nemotron-Cascade-2", "30B MoE (3B active)", "24 GB"),
  ("gemma4:31b-mlx",           "Google Gemma 4 31B", "31B dense (MLX)",      "20 GB"),
  ("ornith:35b",               "Ornith 35B",         "35B dense",            "21 GB"),
  ("qwen3.6:latest",           "Qwen3.6-35B",        "36B MoE",              "23 GB"),
]
MODELS = [m for m in MODELS if m[0] in r["models"]]
qs, cats = r["questions"], r["categories"]
cat_order = list(dict.fromkeys(cats))
N = len(qs)

print("computing reference answers…")
TRUTHS = []
for item in ev.QUESTIONS:
    rows = ev.run_sql(item["truth_sql"])
    if isinstance(rows, list):
        vals = []
        for row in rows[:6]:
            vals.append(" · ".join(str(v) for v in row.values()))
        TRUTHS.append("; ".join(vals) + ("…" if len(rows) > 6 else ""))
    else:
        TRUTHS.append("?")

def mark(m, i):
    a = r["models"][m]["answers"][i]
    if a["ok"]: return "✓", "#1E8A4A"
    if (m, i) in DEFENSIBLE: return "△", "#B45309"
    return "✗", "#B91C1C"

def stats(m, idxs=None):
    idxs = list(idxs) if idxs is not None else list(range(N))
    ans = r["models"][m]["answers"]
    strict = sum(1 for i in idxs if ans[i]["ok"])
    dfn = strict + sum(1 for i in idxs if not ans[i]["ok"] and (m, i) in DEFENSIBLE)
    avg = sum(ans[i]["secs"] for i in idxs) / max(1, len(idxs))
    return strict, dfn, avg

short = {k: k.replace(":latest", "").replace("-mlx", "").replace("nemotron-cascade-2", "nemotron-c2") for k, *_ in MODELS}

# ---------- model summary table ----------
srows = []
for key, name, arch, disk in MODELS:
    s, d, avg = stats(key)
    srows.append(f'<tr><td><span class="mono">{key}</span><br><span style="color:#71717A; font-size:12.5px;">{name}</span></td>'
                 f'<td>{arch} · {disk}</td><td><strong>{s} / {N}</strong></td><td><strong>{d} / {N}</strong></td><td>{avg:.1f} s</td></tr>')
summary = "\n".join(srows)

# ---------- category score table ----------
cat_head = "".join(f'<th style="text-align:center;" class="mono">{short[m[0]]}</th>' for m in MODELS)
crows = []
for cat in cat_order:
    idxs = [i for i, c in enumerate(cats) if c == cat]
    cells = "".join(f'<td style="text-align:center;">{stats(m[0], idxs)[0]}/{len(idxs)}</td>' for m in MODELS)
    crows.append(f'<tr><td style="font-weight:600;">{html.escape(cat)}</td>{cells}</tr>')
cat_table = "\n".join(crows)

# ---------- expandable category sections ----------
sections = []
for cat in cat_order:
    idxs = [i for i, c in enumerate(cats) if c == cat]
    agg = sum(stats(m[0], idxs)[0] for m in MODELS)
    qblocks = []
    for i in idxs:
        db = "SWRD" if "SWRD" in qs[i] else "SSWR"
        dbc = "#B45309" if db == "SWRD" else "#00274C"
        icons = "".join(f'<span title="{html.escape(short[m[0]])}" style="color:{mark(m[0], i)[1]}; font-weight:700; padding:0 3px;">{mark(m[0], i)[0]}</span>' for m in MODELS)
        mrows = []
        for key, name, *_ in MODELS:
            a = r["models"][key]["answers"][i]
            sym, col = mark(key, i)
            outcome = "correct" if a["ok"] else html.escape(a["detail"][:160])
            sql = html.escape(a["sql"]) if a["sql"] else "<em>(no SQL produced)</em>"
            mrows.append(
              f'<div style="border-top:1px solid #EFEDE8; padding:12px 0;">'
              f'<div style="display:flex; gap:10px; align-items:baseline; flex-wrap:wrap;">'
              f'<span style="color:{col}; font-weight:700;">{sym}</span>'
              f'<span class="mono" style="font-size:12.5px; font-weight:600;">{html.escape(short[key])}</span>'
              f'<span class="mono" style="font-size:11.5px; color:#A1A1AA;">{a["secs"]} s</span>'
              f'<span style="font-size:12.5px; color:#71717A;">{outcome}</span></div>'
              f'<pre class="sql">{sql}</pre></div>')
        qblocks.append(
          f'<details class="q"><summary>'
          f'<span class="mono" style="color:#A1A1AA; flex:0 0 28px;">{i+1:02d}</span>'
          f'<span class="mono" style="font-size:10.5px; color:{dbc}; flex:0 0 44px;">{db}</span>'
          f'<span style="flex:1; font-size:13.5px;">{html.escape(qs[i])}</span>'
          f'<span style="flex:0 0 auto; white-space:nowrap;">{icons}</span></summary>'
          f'<div style="padding:4px 16px 16px 88px;">'
          f'<p style="margin:8px 0 4px; font-size:13px;"><strong>Reference answer:</strong> <span class="mono" style="font-size:12.5px; color:#00274C;">{html.escape(TRUTHS[i])}</span></p>'
          + "".join(mrows) + '</div></details>')
    sections.append(
      f'<details class="cat"><summary><span style="flex:1;">{html.escape(cat)}</span>'
      f'<span class="mono" style="font-size:12.5px; color:#71717A;">{len(idxs)} questions · {agg}/{len(idxs)*len(MODELS)} strict passes · click to expand</span></summary>'
      f'<div style="padding:4px 0 8px;">' + "\n".join(qblocks) + '</div></details>')
category_sections = "\n".join(sections)

tot_s = sum(stats(m[0])[0] for m in MODELS)
tot_d = sum(stats(m[0])[1] for m in MODELS)
tot_cells = N * len(MODELS)
perfect = [short[m[0]] for m in MODELS if stats(m[0])[0] == N]
best_key = max(MODELS, key=lambda m: stats(m[0])[0])[0]
best_s = stats(best_key)[0]
best_line = f"{best_s} / {N}"
best_sub = (f"perfect scores: {', '.join(perfect)}" if perfect else f"best score ({short[best_key]})")
today = datetime.date.today().strftime("%B %Y")

# per-category totals for the narrative
cat_tot = {cat: sum(stats(m[0], [i for i, c in enumerate(cats) if c == cat])[0] for m in MODELS) for cat in cat_order}
per_cat = len(MODELS) * (N // len(cat_order))
narrative = ("Accuracy by category: " + " · ".join(
    f"{c.split('·')[1].strip()} {cat_tot[c]}/{per_cat}" for c in cat_order) +
    ". The gradient is the story: simple retrieval and vocabulary questions are near-ceiling for every size, while joins, nested search-function calls, and multi-step analytical queries separate the models — this is where parameter count (and training focus) earns its keep.")

page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Text-to-SQL with Small Local Models — The Social Work Meta-Data Project</title>
<meta name="description" content="A {N}-question, {len(MODELS)}-model empirical evaluation of whether small local language models can query the Social Work Meta-Data databases. Performed entirely on a MacBook Pro (Apple M5).">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  html {{ -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }}
  body {{ margin: 0; background: #FFFFFF; color: #18181B; font-family: 'IBM Plex Sans', system-ui, sans-serif; font-size: 15px; line-height: 1.55; -webkit-font-smoothing: antialiased; }}
  *, *::before, *::after {{ box-sizing: border-box; }}
  a {{ color: #00274C; text-decoration: none; border-bottom: 1px solid transparent; }}
  a:hover {{ border-bottom-color: currentColor; }}
  ::selection {{ background: #FFCB05; color: #00274C; }}
  table.results {{ width: 100%; border-collapse: collapse; }}
  table.results th, table.results td {{ text-align: left; padding: 11px 13px; border-bottom: 1px solid #E7E5E0; font-size: 13.5px; vertical-align: top; }}
  table.results th {{ font-size: 11px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: #71717A; background: #FAFAF9; }}
  .mono {{ font-family: 'IBM Plex Mono', monospace; }}
  pre.sql {{ margin: 8px 0 0; padding: 12px 14px; background: #0F1B2D; color: #DCE6F2; border-radius: 6px; font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; line-height: 1.55; white-space: pre-wrap; overflow-x: auto; }}
  details.cat {{ background: #FFFFFF; border: 1px solid #E7E5E0; border-radius: 8px; margin-bottom: 14px; box-shadow: 0 1px 2px rgba(24,24,27,0.04); overflow: hidden; }}
  details.cat > summary {{ display: flex; align-items: baseline; gap: 14px; padding: 18px 22px; cursor: pointer; font-size: 15.5px; font-weight: 600; list-style: none; }}
  details.cat > summary::before {{ content: "▸"; color: #B45309; font-size: 13px; transition: transform 150ms; }}
  details.cat[open] > summary::before {{ content: "▾"; }}
  details.cat > summary:hover {{ background: #FAFAF9; }}
  details.cat[open] > summary {{ border-bottom: 1px solid #E7E5E0; background: #FAFAF9; }}
  details.q {{ border-bottom: 1px solid #F0EEE9; }}
  details.q > summary {{ display: flex; align-items: baseline; gap: 10px; padding: 12px 22px; cursor: pointer; list-style: none; }}
  details.q > summary:hover {{ background: #FCFBF9; }}
  details.q[open] {{ background: #FCFBF9; }}
  summary::-webkit-details-marker {{ display: none; }}
  @media (max-width: 880px) {{ .g2, .g3 {{ grid-template-columns: 1fr !important; }} .nav-links a.nav-item {{ display: none; }} details.q > summary {{ flex-wrap: wrap; }} }}
</style>
</head>
<body>

<header style="position:sticky; top:0; z-index:50; background:rgba(255,255,255,0.86); backdrop-filter:blur(8px); border-bottom:1px solid #E7E5E0;">
  <div style="max-width:1180px; margin:0 auto; padding:0 clamp(20px,3vw,32px); height:60px; display:flex; align-items:center; justify-content:space-between; gap:24px;">
    <a href="index.html" style="font-size:15px; font-weight:700; letter-spacing:-0.01em; color:#00274C; border:none;">Social Work Meta-Data</a>
    <nav class="nav-links" style="display:flex; align-items:center; gap:28px;">
      <a class="nav-item" href="index.html#databases" style="font-size:13.5px; font-weight:500; color:#3F3F46; border:none;">Databases</a>
      <a class="nav-item" href="index.html#access" style="font-size:13.5px; font-weight:500; color:#3F3F46; border:none;">AI access</a>
      <a class="nav-item" href="index.html#download" style="font-size:13.5px; font-weight:500; color:#3F3F46; border:none;">Download</a>
      <a class="nav-item" href="demonstrations.html" style="font-size:13.5px; font-weight:600; color:#00274C; border:none;">Demonstrations</a>
      <a href="mailto:beperron@umich.edu" style="display:inline-flex; align-items:center; height:34px; padding:0 16px; background:#00274C; color:#FFFFFF; font-size:13.5px; font-weight:600; border-radius:6px; border:none;">Contact</a>
    </nav>
  </div>
</header>

<section style="position:relative; overflow:hidden; background:radial-gradient(1200px 700px at 78% -10%, #1F3A5F 0%, #00274C 42%, #001A33 100%);">
  <div aria-hidden="true" style="position:absolute; inset:0; background-image:radial-gradient(rgba(255,255,255,0.09) 1px, transparent 1.4px); background-size:26px 26px; mask-image:linear-gradient(180deg, #000 0%, #000 55%, transparent 100%); -webkit-mask-image:linear-gradient(180deg, #000 0%, #000 55%, transparent 100%);"></div>
  <div style="position:relative; max-width:1180px; margin:0 auto; padding:clamp(56px,6vw,80px) clamp(20px,3vw,32px);">
    <p style="margin:0 0 20px; font-size:11.5px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:#FFCB05;">Demonstrations · Report 01 · Text-to-SQL · {N} questions · {len(MODELS)} models · {today}</p>
    <h1 style="margin:0; max-width:22ch; font-size:clamp(32px,4.4vw,48px); line-height:1.08; font-weight:600; letter-spacing:-0.022em; color:#FFFFFF;">Text-to-SQL with Small Local Models</h1>
    <p style="margin:22px 0 0; max-width:62ch; font-size:clamp(15px,1.8vw,18px); line-height:1.55; color:#C7D2E0;">Can free, locally-run language models query these databases? We gave {len(MODELS)} open-weight models — 3&thinsp;B to 36&thinsp;B parameters — the same instructions any assistant gets and {N} research questions across six task categories, executing their SQL verbatim against the live databases through the public endpoint. <strong style="color:#FFFFFF;">Everything ran locally on a single MacBook Pro (Apple M5)</strong> — no cloud AI involved.</p>
  </div>
</section>

<section style="border-bottom:1px solid #E7E5E0; background:#FAFAF9;">
  <div class="g3" style="max-width:1180px; margin:0 auto; padding:0 clamp(20px,3vw,32px); display:grid; grid-template-columns:repeat(3,1fr);">
    <div style="padding:32px 24px 30px 0; border-right:1px solid #E7E5E0;">
      <div style="font-size:clamp(28px,3.4vw,38px); font-weight:600; letter-spacing:-0.02em; color:#00274C; line-height:1;">{tot_s} / {tot_cells}</div>
      <div style="margin-top:8px; font-size:13px; color:#71717A;">strict passes across all models<br>({tot_d}/{tot_cells} correct or defensibly stricter)</div>
    </div>
    <div style="padding:32px 24px 30px 24px; border-right:1px solid #E7E5E0;">
      <div style="font-size:clamp(28px,3.4vw,38px); font-weight:600; letter-spacing:-0.02em; color:#00274C; line-height:1;">{best_line}</div>
      <div style="margin-top:8px; font-size:13px; color:#71717A;">{best_sub}</div>
    </div>
    <div style="padding:32px 0 30px 24px;">
      <div style="font-size:clamp(28px,3.4vw,38px); font-weight:600; letter-spacing:-0.02em; color:#00274C; line-height:1;">1 laptop</div>
      <div style="margin-top:8px; font-size:13px; color:#71717A;">MacBook Pro, Apple M5 —<br>models pulled, run, and purged in place</div>
    </div>
  </div>
</section>

<section style="max-width:1180px; margin:0 auto; padding:clamp(56px,6vw,80px) clamp(20px,3vw,32px);">
  <div style="display:flex; align-items:baseline; gap:14px; margin-bottom:8px;">
    <span class="mono" style="font-size:12px; color:#A1A1AA;">01</span>
    <span style="height:1px; flex:0 0 40px; background:#D4D4D0; align-self:center;"></span>
    <span style="font-size:11.5px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:#71717A;">Method</span>
  </div>
  <h2 style="margin:0; font-size:clamp(24px,3vw,32px); font-weight:600; letter-spacing:-0.018em;">Blind questions, six task categories, pre-registered answers</h2>
  <p style="margin:16px 0 0; max-width:72ch; font-size:15.5px; color:#3F3F46;">Each model ran locally through <a href="https://ollama.com">Ollama</a> at temperature 0 on a MacBook Pro (Apple M5) and was prompted with the project's two <a href=\"index.html#access\" style=\"color:#00274C;\">published skill files, verbatim</a> — the exact documents any user downloads — plus a one-line output-format instruction. It answered {N} questions, one at a time, in six categories of increasing demand: <strong>A</strong> simple retrieval &amp; counts · <strong>B</strong> vocabulary &amp; schema fidelity · <strong>C</strong> joins &amp; relational reasoning · <strong>D</strong> aggregation &amp; trends · <strong>E</strong> search-function usage · <strong>F</strong> complex analytical queries. Questions are balanced across the SWRD and SSWR databases. Each model's SQL was executed <em>verbatim</em> through the same public read-only endpoint available to everyone and compared with a reference answer computed before the run; all reference queries were verified deterministic. A <strong>strict pass</strong> (✓) reproduces the reference value; inspected failures that applied the documented corpus rules more strictly than the reference are marked <strong>defensible</strong> (△); genuine mistakes are ✗.</p>
  <p style="margin:12px 0 0; max-width:72ch; font-size:15.5px; color:#3F3F46;"><strong>The feedback loop.</strong> A pilot round with a hand-condensed prompt surfaced recurring failure patterns — models reaching into the wrong database's tables, calling search functions without SELECT, treating the relevance score as a row position, and forgetting that authorship tables carry no year column. Each pattern became an explicit rule in the skill files ("SQL rules that prevent the most common errors"), and this final round was run against those hardened skills. That loop — evaluate, harden, re-evaluate — is the recommended way to maintain the skills as models and questions evolve.</p>

  <h3 style="margin:36px 0 14px; font-size:17px; font-weight:600;">The models</h3>
  <div style="border:1px solid #E7E5E0; border-radius:8px; overflow-x:auto; box-shadow:0 1px 2px rgba(24,24,27,0.04);">
    <table class="results">
      <tr><th>Model (Ollama tag)</th><th>Architecture · disk size</th><th>Strict</th><th>Correct or defensible</th><th>Avg / question</th></tr>
      {summary}
    </table>
  </div>
  <p style="margin:12px 0 0; font-size:13px; color:#71717A;">Models not already on the machine were pulled, evaluated, and deleted afterward. Timings are Ollama generation only.</p>
</section>

<section style="background:#FAFAF9; border-top:1px solid #E7E5E0; border-bottom:1px solid #E7E5E0;">
  <div style="max-width:1180px; margin:0 auto; padding:clamp(56px,6vw,80px) clamp(20px,3vw,32px);">
    <div style="display:flex; align-items:baseline; gap:14px; margin-bottom:8px;">
      <span class="mono" style="font-size:12px; color:#A1A1AA;">02</span>
      <span style="height:1px; flex:0 0 40px; background:#D4D4D0; align-self:center;"></span>
      <span style="font-size:11.5px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:#71717A;">Scores by task category</span>
    </div>
    <h2 style="margin:0 0 24px; font-size:clamp(24px,3vw,32px); font-weight:600; letter-spacing:-0.018em;">Where difficulty actually bites</h2>
    <div style="background:#FFFFFF; border:1px solid #E7E5E0; border-radius:8px; overflow-x:auto; box-shadow:0 1px 2px rgba(24,24,27,0.04);">
      <table class="results">
        <tr><th>Category (strict passes)</th>{cat_head}</tr>
        {cat_table}
      </table>
    </div>
    <p style="margin:18px 0 0; max-width:72ch; font-size:14.5px; color:#3F3F46;">{narrative}</p>
  </div>
</section>

<section style="max-width:1180px; margin:0 auto; padding:clamp(56px,6vw,80px) clamp(20px,3vw,32px);">
  <div style="display:flex; align-items:baseline; gap:14px; margin-bottom:8px;">
    <span class="mono" style="font-size:12px; color:#A1A1AA;">03</span>
    <span style="height:1px; flex:0 0 40px; background:#D4D4D0; align-self:center;"></span>
    <span style="font-size:11.5px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:#71717A;">Explore the full results</span>
  </div>
  <h2 style="margin:0 0 10px; font-size:clamp(24px,3vw,32px); font-weight:600; letter-spacing:-0.018em;">Every question, every model, every line of SQL</h2>
  <p style="margin:0 0 24px; max-width:70ch; font-size:14.5px; color:#3F3F46;">Expand a category to see its questions with per-model marks (✓ strict · △ defensible · ✗ error, in model order from smallest to largest). Expand a question to see the reference answer and each model's verbatim SQL, timing, and outcome.</p>
  {category_sections}
</section>

<section style="background:#00274C; position:relative; overflow:hidden;">
  <div aria-hidden="true" style="position:absolute; inset:0; background-image:radial-gradient(rgba(255,255,255,0.06) 1px, transparent 1.4px); background-size:26px 26px;"></div>
  <div style="position:relative; max-width:1180px; margin:0 auto; padding:clamp(56px,6vw,80px) clamp(20px,3vw,32px);">
    <div style="display:flex; align-items:baseline; gap:14px; margin-bottom:8px;">
      <span class="mono" style="font-size:12px; color:#5E7794;">04</span>
      <span style="height:1px; flex:0 0 40px; background:rgba(255,255,255,0.25); align-self:center;"></span>
      <span style="font-size:11.5px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:#8FA6BF;">Honest limits &amp; reproduction</span>
    </div>
    <h2 style="margin:0; max-width:26ch; font-size:clamp(24px,3vw,32px); font-weight:600; letter-spacing:-0.018em; color:#FFFFFF;">What this shows — and how to rerun it</h2>
    <div class="g2" style="margin-top:28px; display:grid; grid-template-columns:1fr 1fr; gap:20px;">
      <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:24px;">
        <p style="margin:0; font-size:14.5px; color:#E4EAF1;"><strong style="color:#FFFFFF;">It shows</strong> that free, local models can reliably answer routine research questions against these databases, that precise skill files carry small models a long way, and that model scale principally buys reliability on joins, tool calls, and multi-step queries.</p>
      </div>
      <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:24px;">
        <p style="margin:0; font-size:14.5px; color:#E4EAF1;"><strong style="color:#FFFFFF;">It doesn't show</strong> multi-turn analysis, semantic-search orchestration, or robustness across phrasings — single-turn questions, one run each, temperature 0. A structured existence proof, not a leaderboard.</p>
      </div>
    </div>
    <p style="margin:22px 0 0; font-size:13px; color:#8FA6BF;">Reproduce with any Ollama model: <span class="mono">python migration/08_eval_local_models.py &lt;model&gt; …</span> — harness, questions, reference queries, and raw outputs are in the <a href="https://github.com/beperron/SocialWork-MetaData" style="color:#C7D2E0;">repository</a>.</p>
  </div>
</section>

<footer style="background:#001A33;">
  <div style="max-width:1180px; margin:0 auto; padding:36px clamp(20px,3vw,32px); display:flex; flex-wrap:wrap; justify-content:space-between; gap:16px; align-items:center;">
    <a href="demonstrations.html" class="mono" style="font-size:11.5px; color:#5E7794; border:none;">← All demonstrations</a>
    <a href="https://parallel42.ai" class="mono" style="font-size:11.5px; color:#5E7794; border:none;">Brian Perron · parallel42.ai</a>
  </div>
</footer>

</body>
</html>
'''
open(os.path.join(repo, "text-to-sql.html"), "w").write(page)
print(f"text-to-sql.html: {len(MODELS)} models × {N} questions · strict {tot_s}/{tot_cells} · defensible {tot_d}/{tot_cells} · {len(page)//1024} KB")
