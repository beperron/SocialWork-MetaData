#!/usr/bin/env python3
"""
Step 6 — build a self-contained page for inspecting the proposed corrections.

    python3 qc/doi/code/06_build_inspector.py

Reads  ../data/recovery.json, ../data/audit.json
Writes ../data/inspector.html

The patch set is 2,973 rows. A CSV is the right thing to apply and the wrong
thing to review: the judgement a reviewer actually makes is "is this Crossref
record the same article as ours", and that means reading two titles side by side.
So this page puts the evidence next to each proposal, and makes the queue
filterable rather than asking anyone to scroll.

Everything is embedded — no network, no build step, opens from disk.
"""
import html
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
REC = os.path.join(ROOT, "data", "recovery.json")
AUD = os.path.join(ROOT, "data", "audit.json")
OUT = os.path.join(ROOT, "data", "inspector.html")

# Trimmed to what a reviewer reads. The full evidence stays in recovery.json.
KEEP = ["id", "journal_name", "year", "doi", "proposed_doi", "tier", "method",
        "verdict", "title_similarity", "journal_verdict", "journal_basis",
        "author_overlap", "title", "crossref_title", "crossref_journal"]


def main():
    with open(REC) as f:
        findings = json.load(f)
    with open(AUD) as f:
        audit = json.load(f)

    proposals = [r for r in findings if r["verdict"] == "recovered"]
    by_doi = Counter(r["proposed_doi"].lower() for r in proposals)
    for r in proposals:
        # Ten DOIs are each proposed for two records — the same article ingested
        # twice. Flag them here so a reviewer sees why they are excluded.
        r["collision"] = by_doi[r["proposed_doi"].lower()] > 1

    rows = []
    for r in findings:
        row = {k: r.get(k) for k in KEEP}
        row["collision"] = r.get("collision", False)
        row["applied"] = r["verdict"] == "recovered" and not row["collision"]
        for k in ("title", "crossref_title", "crossref_journal", "journal_name"):
            if row.get(k):
                row[k] = row[k][:220]
        rows.append(row)

    applied = [r for r in rows if r["applied"]]
    stats = {
        "proposed": len(applied),
        "tier_a": sum(1 for r in applied if r["tier"] == "A"),
        "tier_b": sum(1 for r in applied if r["tier"] == "B"),
        "queue": len(rows) - len(applied),
        "total": len(rows),
        "audited": sum(v["audited"] for v in audit["summary"].values()),
        "confirmed": sum(v["confirmed"] for v in audit["summary"].values()),
        "verdicts": dict(Counter(r["verdict"] for r in rows)),
        "journals": dict(Counter(r["journal_name"] for r in rows).most_common()),
    }

    page = TEMPLATE.replace("__ROWS__", json.dumps(rows, ensure_ascii=False,
                                                  separators=(",", ":")))
    page = page.replace("__STATS__", json.dumps(stats, ensure_ascii=False))
    with open(OUT, "w") as f:
        f.write(page)
    kb = os.path.getsize(OUT) // 1024
    print(f"{len(rows):,} rows ({len(applied):,} proposed, {stats['queue']:,} queued)")
    print(f"-> {OUT}  ({kb:,} KB)")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DOI repair — proposed corrections</title>
<style>
  :root{
    --bg:#F7F8F8; --surface:#FFFFFF; --line:#E3E6E5; --ink:#141817; --ink2:#4A5250;
    --mut:#78817F; --accent:#0F5257; --accent-soft:#EAF3F1;
    --a:#0F5257; --b:#C97B3E; --c:#8A8F98; --warn:#B0472B;
    --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
  }
  @media (prefers-color-scheme:dark){
    :root{ --bg:#0E1413; --surface:#161D1C; --line:#273230; --ink:#E8EDEB;
           --ink2:#B4BFBC; --mut:#7F8B88; --accent:#5FBFAE; --accent-soft:#172523; }
  }
  :root[data-theme="dark"]{ --bg:#0E1413; --surface:#161D1C; --line:#273230;
    --ink:#E8EDEB; --ink2:#B4BFBC; --mut:#7F8B88; --accent:#5FBFAE; --accent-soft:#172523; }
  :root[data-theme="light"]{ --bg:#F7F8F8; --surface:#FFFFFF; --line:#E3E6E5;
    --ink:#141817; --ink2:#4A5250; --mut:#78817F; --accent:#0F5257; --accent-soft:#EAF3F1; }

  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
  .wrap{max-width:1240px;margin:0 auto;padding:0 20px}
  header{background:var(--surface);border-bottom:1px solid var(--line);padding:22px 0 18px}
  h1{margin:0;font-size:20px;font-weight:650;letter-spacing:-.01em}
  header p{margin:5px 0 0;color:var(--ink2);font-size:14px;max-width:78ch}

  .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:10px;margin:18px 0 0}
  .tile{background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:12px 14px}
  .tile b{display:block;font-size:23px;font-weight:650;font-variant-numeric:tabular-nums;line-height:1.15}
  .tile span{font-size:11.5px;color:var(--mut);letter-spacing:.03em;text-transform:uppercase}
  .tile.ok b{color:var(--accent)}

  .bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 12px}
  .chip{font:inherit;font-size:13px;padding:6px 13px;border:1px solid var(--line);
        background:var(--surface);color:var(--ink2);border-radius:20px;cursor:pointer}
  .chip:hover{border-color:var(--mut)}
  .chip.on{background:var(--accent);color:#fff;border-color:var(--accent)}
  .chip:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  input[type=search]{flex:1;min-width:220px;font:inherit;font-size:13.5px;padding:7px 12px;
    border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink)}
  .count{font-size:13px;color:var(--mut);font-variant-numeric:tabular-nums}
  .themebtn{margin-left:auto}

  .tablewrap{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}
  table{border-collapse:collapse;width:100%;font-size:13.5px}
  th{position:sticky;top:0;background:var(--surface);text-align:left;padding:10px 12px;
     border-bottom:1px solid var(--line);font-size:11.5px;letter-spacing:.04em;
     text-transform:uppercase;color:var(--mut);font-weight:600;white-space:nowrap;cursor:pointer}
  th.no{cursor:default}
  td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
  tr.r{cursor:pointer}
  tr.r:hover td{background:var(--accent-soft)}
  .num{text-align:right;font-variant-numeric:tabular-nums}
  .mono{font-family:var(--mono);font-size:12px}
  .ttl{max-width:400px}

  .pill{display:inline-block;padding:1px 8px;border-radius:11px;font-size:11px;font-weight:600;
        letter-spacing:.02em;white-space:nowrap}
  .pill.A{background:var(--a);color:#fff}
  .pill.B{background:var(--b);color:#fff}
  .pill.C{background:var(--c);color:#fff}
  .stripe{display:inline-block;width:3px;height:15px;border-radius:2px;vertical-align:-3px;margin-right:7px}
  .flag{color:var(--warn);font-weight:600;font-size:11.5px}

  .ev{background:var(--bg)}
  .ev td{padding:0 12px 16px}
  .evbox{display:grid;grid-template-columns:80px 1fr;gap:6px 14px;font-size:13px;padding-top:4px}
  .evbox dt{color:var(--mut);font-size:11.5px;letter-spacing:.03em;text-transform:uppercase;padding-top:2px}
  .evbox dd{margin:0;color:var(--ink2)}
  .same{color:var(--accent);font-weight:600}
  a{color:var(--accent)}
  footer{color:var(--mut);font-size:12.5px;padding:26px 0 40px}
</style>
</head>
<body>
<header><div class="wrap">
  <h1>DOI repair — proposed corrections</h1>
  <p>Every SWRD record whose <span class="mono">doi</span> field held something that is not a DOI, with
     the recovered value and the evidence behind it. Click any row to compare our title against
     Crossref's. Nothing here has been applied to the database.</p>
  <div class="tiles" id="tiles"></div>
</div></header>

<div class="wrap">
  <div class="bar">
    <button class="chip on" data-f="applied">Proposed</button>
    <button class="chip" data-f="A">Tier A</button>
    <button class="chip" data-f="B">Tier B</button>
    <button class="chip" data-f="queue">Review queue</button>
    <button class="chip" data-f="collision">Collisions</button>
    <button class="chip" data-f="all">All</button>
    <input type="search" id="q" placeholder="Search title, DOI, journal, or record id…" aria-label="Search">
    <button class="chip themebtn" id="theme">Theme</button>
  </div>
  <p class="count" id="count"></p>

  <div class="tablewrap">
    <table>
      <thead><tr>
        <th class="no">Record</th><th class="no">Journal</th><th data-s="year" class="num">Year</th>
        <th class="no">Current → proposed</th><th data-s="title_similarity" class="num">Title</th>
        <th class="no">Journal check</th><th data-s="author_overlap" class="num">Authors</th>
        <th data-s="tier">Tier</th>
      </tr></thead>
      <tbody id="tb"></tbody>
    </table>
  </div>
  <footer id="foot"></footer>
</div>

<script>
const ROWS = __ROWS__;
const STATS = __STATS__;

const tiles = [
  ["proposed","Proposed corrections","ok"], ["tier_a","Tier A · rule",""],
  ["tier_b","Tier B · searched",""], ["queue","Review queue",""],
];
document.getElementById("tiles").innerHTML =
  tiles.map(([k,label,cls]) =>
    `<div class="tile ${cls}"><b>${STATS[k].toLocaleString()}</b><span>${label}</span></div>`).join("")
  + `<div class="tile ok"><b>${STATS.confirmed}/${STATS.audited}</b><span>Audit precision</span></div>`;

let filter = "applied", sortKey = null, sortDir = -1, query = "";

function passes(r){
  if (filter === "applied" && !r.applied) return false;
  if (filter === "queue" && r.applied) return false;
  if (filter === "collision" && !r.collision) return false;
  if ((filter === "A" || filter === "B") && !(r.applied && r.tier === filter)) return false;
  if (query){
    const hay = [r.id, r.title, r.doi, r.proposed_doi, r.journal_name, r.crossref_title]
                .join(" ").toLowerCase();
    if (!hay.includes(query)) return false;
  }
  return true;
}

function esc(s){ return String(s ?? "").replace(/[&<>"]/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

function jcell(r){
  if (!r.journal_verdict) return '<span style="color:var(--mut)">—</span>';
  const good = r.journal_verdict === "match";
  return `<span style="color:${good ? "var(--accent)" : "var(--warn)"}">${esc(r.journal_verdict)}</span>`
       + `<br><span style="font-size:11px;color:var(--mut)">${esc(r.journal_basis || "")}</span>`;
}

function render(){
  let rows = ROWS.filter(passes);
  if (sortKey) rows.sort((a,b) => ((a[sortKey] ?? -1) - (b[sortKey] ?? -1)) * sortDir);

  document.getElementById("count").textContent =
    `${rows.length.toLocaleString()} of ${STATS.total.toLocaleString()} records`;

  // Cap the DOM at a readable slice; the filters exist to narrow, not to page.
  const shown = rows.slice(0, 400);
  document.getElementById("tb").innerHTML = shown.map((r,i) => `
    <tr class="r" data-i="${i}">
      <td class="mono">${r.id}${r.collision ? '<br><span class="flag">collision</span>' : ""}</td>
      <td>${esc(r.journal_name)}</td>
      <td class="num">${r.year ?? ""}</td>
      <td class="mono"><span style="color:var(--mut)">${esc(r.doi)}</span><br>
          ${r.proposed_doi ? `<span class="same">→ ${esc(r.proposed_doi)}</span>` : '<span style="color:var(--mut)">— none —</span>'}</td>
      <td class="num">${r.title_similarity ?? ""}</td>
      <td>${jcell(r)}</td>
      <td class="num">${r.author_overlap ?? ""}</td>
      <td><span class="pill ${r.tier}">${r.tier}</span>${
          r.applied ? "" : `<br><span style="font-size:11px;color:var(--mut)">${esc(r.verdict)}</span>`}</td>
    </tr>
    <tr class="ev" id="ev${i}" hidden><td colspan="8"><dl class="evbox">
      <dt>Ours</dt><dd>${esc(r.title)}</dd>
      <dt>Crossref</dt><dd>${esc(r.crossref_title) || '<span style="color:var(--mut)">no record retrieved</span>'}</dd>
      <dt>Journal</dt><dd>${esc(r.journal_name)} &nbsp;·&nbsp; Crossref: ${esc(r.crossref_journal) || "—"}</dd>
      <dt>Verdict</dt><dd>${esc(r.verdict)} &nbsp;·&nbsp; method ${esc(r.method || "—")}</dd>
      ${r.proposed_doi ? `<dt>Resolve</dt><dd><a href="https://doi.org/${encodeURIComponent(r.proposed_doi)}" target="_blank" rel="noopener">doi.org/${esc(r.proposed_doi)}</a></dd>` : ""}
    </dl></td></tr>`).join("");

  document.getElementById("foot").textContent = rows.length > shown.length
    ? `Showing the first ${shown.length} of ${rows.length.toLocaleString()} — narrow with a filter or search.`
    : "";
}

document.getElementById("tb").addEventListener("click", e => {
  const tr = e.target.closest("tr.r"); if (!tr) return;
  const ev = document.getElementById("ev" + tr.dataset.i);
  ev.hidden = !ev.hidden;
});
document.querySelectorAll(".chip[data-f]").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll(".chip[data-f]").forEach(x => x.classList.remove("on"));
  b.classList.add("on"); filter = b.dataset.f; render();
}));
document.querySelectorAll("th[data-s]").forEach(th => th.addEventListener("click", () => {
  const k = th.dataset.s;
  sortDir = (sortKey === k) ? -sortDir : -1; sortKey = k; render();
}));
document.getElementById("q").addEventListener("input", e => {
  query = e.target.value.trim().toLowerCase(); render();
});
document.getElementById("theme").addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const dark = cur ? cur === "dark"
             : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
});
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
