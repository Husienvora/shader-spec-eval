"""HTML dashboard for the shader benchmark.

Design note: the specimens under test are vividly coloured, so the chrome is
deliberately near-monochrome. The rendered shaders are the only saturated thing
on the page. The grid reads as a contact sheet — models down, difficulty across,
with the human reference pinned at the top as a control.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from .analysis import analyse, base_name
from .bench import Cell

DIFFICULTY = {
    "shader-gradient": ("L1", "linear ramp"),
    "shader-pulse":    ("L2", "radial + time"),
    "shader-tile":     ("L3", "modulo / repetition"),
    "shader-sdf":      ("L4", "signed distance"),
    "shader-polar":    ("L5", "polar / angular"),
}

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=IBM+Plex+Mono:wght@400;500;600&'
         'family=IBM+Plex+Sans:wght@400;500;600&display=swap">')

CSS = """
:root{
  --ground:#faf7f4; --panel:#ffffff; --sunken:#f2ede8;
  --line:#e2d9d0; --line-soft:#eee7e0;
  --ink:#1d1a18; --muted:#7d736c;
  --accent:#a9611a;
  --pass:#3f7d4a; --part:#a8760f; --fail:#a33646;
  --shadow:0 1px 2px rgba(40,30,20,.06);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#141317; --panel:#1c1a20; --sunken:#131217;
    --line:#302c36; --line-soft:#26232b;
    --ink:#f0ecea; --muted:#9a9299;
    --accent:#e0a458;
    --pass:#6fbf73; --part:#d9a441; --fail:#d1596b;
    --shadow:none;
  }
}
:root[data-theme="dark"]{
  --ground:#141317; --panel:#1c1a20; --sunken:#131217;
  --line:#302c36; --line-soft:#26232b;
  --ink:#f0ecea; --muted:#9a9299;
  --accent:#e0a458;
  --pass:#6fbf73; --part:#d9a441; --fail:#d1596b;
  --shadow:none;
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
  font-size:14px; line-height:1.6; -webkit-font-smoothing:antialiased;
}
.mono{font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace}

header{padding:40px 40px 0;max-width:1500px;margin:0 auto}
.eyebrow{
  font-family:"IBM Plex Mono",monospace; font-size:11px; font-weight:500;
  letter-spacing:.16em; text-transform:uppercase; color:var(--accent); margin:0 0 10px;
}
h1{margin:0 0 12px;font-size:30px;font-weight:600;letter-spacing:-.02em;text-wrap:balance}
.lede{margin:0;color:var(--muted);max-width:64ch;font-size:15px}

.strip{
  display:flex;flex-wrap:wrap;gap:0;margin:32px 0 0;
  border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--panel);
}
.stat{padding:14px 22px;flex:1;min-width:150px;border-right:1px solid var(--line-soft)}
.stat:last-child{border-right:0}
.stat .k{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted);display:block;margin-bottom:4px}
.stat .v{font-size:22px;font-weight:600;font-variant-numeric:tabular-nums}
.stat .v small{font-size:13px;color:var(--muted);font-weight:400}

main{padding:28px 40px 72px;max-width:1500px;margin:0 auto}

.note{
  display:flex;gap:12px;align-items:flex-start;
  border:1px solid var(--line);border-left:3px solid var(--part);
  background:var(--panel);border-radius:8px;padding:14px 18px;margin:0 0 26px;
}
.note b{font-weight:600}
.note p{margin:0;color:var(--muted);font-size:13.5px}

.sheet{overflow-x:auto;border:1px solid var(--line);border-radius:12px;
  background:var(--panel);box-shadow:var(--shadow)}
table{border-collapse:separate;border-spacing:0;width:100%}
thead th{
  position:sticky;top:0;z-index:2;background:var(--panel);
  border-bottom:1px solid var(--line);padding:14px 12px;text-align:center;
}
thead .lvl{font-family:"IBM Plex Mono",monospace;font-size:10px;font-weight:600;
  letter-spacing:.14em;color:var(--accent);display:block}
thead .nm{font-size:13px;font-weight:600;display:block;margin-top:3px}
thead .ds{font-size:11px;color:var(--muted);display:block;font-weight:400}
thead th.corner{text-align:left;z-index:3;left:0}

tbody th{
  position:sticky;left:0;z-index:1;background:var(--panel);
  text-align:left;padding:14px 16px;font-weight:500;font-size:13.5px;
  white-space:nowrap;min-width:210px;border-right:1px solid var(--line-soft);
}
tbody th .agg{display:block;font-family:"IBM Plex Mono",monospace;font-size:11px;
  color:var(--muted);margin-top:2px;font-variant-numeric:tabular-nums}
tbody tr:not(:last-child) th,tbody tr:not(:last-child) td{border-bottom:1px solid var(--line-soft)}
tbody tr.ref th{border-left:3px solid var(--accent)}
tbody tr.ref th .agg{color:var(--accent)}
td{padding:14px 12px;text-align:center;vertical-align:top}

.cell{display:inline-flex;flex-direction:column;align-items:center;gap:8px;
  cursor:pointer;border:0;background:none;padding:0;font:inherit;color:inherit;
  border-radius:8px}
.cell:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
.thumb{width:112px;height:112px;border-radius:7px;border:1px solid var(--line);
  image-rendering:pixelated;background:#000;display:block;transition:transform .14s ease}
.cell:hover .thumb{transform:scale(1.05)}
.thumb.empty{display:grid;place-items:center;background:var(--sunken);
  color:var(--fail);font-family:"IBM Plex Mono",monospace;font-size:9.5px;
  letter-spacing:.1em;text-align:center;padding:8px;line-height:1.5}

.verdict{display:flex;align-items:center;gap:7px;font-family:"IBM Plex Mono",monospace;
  font-size:12px;font-weight:600;font-variant-numeric:tabular-nums}
.dot{width:7px;height:7px;border-radius:50%;flex:none}
.s-pass .dot{background:var(--pass)} .s-pass{color:var(--pass)}
.s-part .dot{background:var(--part)} .s-part{color:var(--part)}
.s-fail .dot{background:var(--fail)} .s-fail{color:var(--fail)}
.meter{width:112px;height:3px;border-radius:2px;background:var(--sunken);overflow:hidden}
.meter i{display:block;height:100%}

.verdict{margin-top:32px;border:1px solid var(--line);border-radius:12px;
  background:var(--panel);overflow:hidden;box-shadow:var(--shadow)}
.verdict .vh{padding:20px 24px;border-bottom:1px solid var(--line);
  border-left:4px solid var(--fail)}
.verdict.good .vh{border-left-color:var(--pass)}
.verdict .vtag{font-family:"IBM Plex Mono",monospace;font-size:10px;font-weight:600;
  letter-spacing:.16em;text-transform:uppercase;color:var(--fail);display:block;margin-bottom:6px}
.verdict.good .vtag{color:var(--pass)}
.verdict .vh h2{margin:0;font-size:17px;font-weight:600;letter-spacing:-.01em}
.vbody{display:grid;grid-template-columns:1fr 1fr;gap:0}
@media(max-width:860px){.vbody{grid-template-columns:1fr}}
.vcol{padding:20px 24px}
.vcol+.vcol{border-left:1px solid var(--line-soft)}
@media(max-width:860px){.vcol+.vcol{border-left:0;border-top:1px solid var(--line-soft)}}
.vcol h3{margin:0 0 12px;font-family:"IBM Plex Mono",monospace;font-size:10px;
  letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:600}
.vcol ul{margin:0;padding:0;list-style:none}
.vcol li{padding:7px 0 7px 18px;position:relative;font-size:13px;
  border-bottom:1px solid var(--line-soft)}
.vcol li:last-child{border-bottom:0}
.vcol li:before{content:"";position:absolute;left:0;top:14px;width:6px;height:6px;
  border-radius:50%;background:var(--muted)}
.vcol.bad li:before{background:var(--fail)}
.vcol.fix li:before{background:var(--accent)}
.metrics{display:flex;flex-wrap:wrap;gap:0;border-top:1px solid var(--line)}
.metric{flex:1;min-width:130px;padding:14px 24px;border-right:1px solid var(--line-soft)}
.metric:last-child{border-right:0}
.metric .k{font-family:"IBM Plex Mono",monospace;font-size:9.5px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--muted);display:block;margin-bottom:3px}
.metric .v{font-size:18px;font-weight:600;font-variant-numeric:tabular-nums;
  font-family:"IBM Plex Mono",monospace}

.cards{margin-top:24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:22px;box-shadow:var(--shadow)}
.card h2{margin:0 0 4px;font-size:15px;font-weight:600}
.card .sub{margin:0 0 16px;font-size:12.5px;color:var(--muted)}
.card table{font-size:13px}
.card th,.card td{padding:8px 10px;text-align:left;border:0;
  border-bottom:1px solid var(--line-soft);position:static;background:none;min-width:0}
.card thead th{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);font-weight:500}
.card tbody tr:last-child td{border-bottom:0}
.num{text-align:right;font-variant-numeric:tabular-nums;font-family:"IBM Plex Mono",monospace}
.pos{color:var(--pass)} .neg{color:var(--fail)}

dialog{border:1px solid var(--line);border-radius:14px;background:var(--panel);
  color:var(--ink);max-width:980px;width:93vw;padding:0;box-shadow:0 24px 60px rgba(0,0,0,.3)}
dialog::backdrop{background:rgba(12,10,14,.76)}
.dh{padding:18px 24px;border-bottom:1px solid var(--line);display:flex;
  justify-content:space-between;align-items:center;gap:20px}
.dh .t{font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:600}
.dh .m{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--muted);margin-top:3px}
.db{padding:22px 24px 26px;display:grid;grid-template-columns:300px 1fr;gap:26px}
@media(max-width:760px){.db{grid-template-columns:1fr}}
.db img{width:100%;border-radius:9px;border:1px solid var(--line);image-rendering:pixelated;display:block}
.checks{list-style:none;margin:0 0 18px;padding:0}
.checks li{display:flex;gap:10px;padding:7px 0;border-bottom:1px solid var(--line-soft);font-size:12.5px}
.checks li:last-child{border-bottom:0}
.checks .n{min-width:210px;font-family:"IBM Plex Mono",monospace;font-weight:500}
.checks .d{color:var(--muted)}
pre{margin:0;background:var(--sunken);border:1px solid var(--line);border-radius:9px;
  padding:14px;overflow:auto;max-height:330px;font-size:12px;line-height:1.6;
  font-family:"IBM Plex Mono",monospace}
button.close{background:none;border:1px solid var(--line);color:var(--muted);
  border-radius:8px;padding:6px 13px;cursor:pointer;font:inherit;font-size:12.5px;flex:none}
button.close:hover{color:var(--ink);border-color:var(--muted)}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
"""


def _tone(c: Cell) -> str:
    if getattr(c, "transient", False):
        return "s-part"
    if not c.compiled:
        return "s-fail"
    if c.perfect:
        return "s-pass"
    return "s-part" if c.score >= 0.6 else "s-fail"


def _tone_var(c: Cell) -> str:
    return {"s-pass": "var(--pass)", "s-part": "var(--part)", "s-fail": "var(--fail)"}[_tone(c)]


def _cell(c: Cell, idx: int) -> str:
    tone = _tone(c)
    if not c.compiled:
        label = "DID NOT<br>COMPILE" if c.compile_log else "NO OUTPUT"
        thumb = f'<span class="thumb empty">{label}</span>'
        verdict = f'0 / {c.total or "—"}'
        width = 0
    else:
        thumb = (f'<img class="thumb" src="data:image/png;base64,{c.png_b64}" alt="">'
                 if c.png_b64 else '<span class="thumb empty">NO PNG</span>')
        verdict = f"{c.passed} / {c.total}"
        width = c.score * 100

    return (
        f'<button class="cell" onclick="openDlg({idx})" aria-label="{html.escape(c.model)} on {html.escape(c.task)}">'
        f'{thumb}'
        f'<span class="verdict {tone}"><i class="dot"></i>{verdict}</span>'
        f'<span class="meter"><i style="width:{width:.0f}%;background:{_tone_var(c)}"></i></span>'
        f'</button>'
    )


def render_dashboard(cells: list[Cell], tasks: list[str], models: list[str],
                     swe_scores: dict[str, float] | None = None) -> str:
    by = {(c.model, c.task): c for c in cells}
    index = {(c.model, c.task): i for i, c in enumerate(cells)}
    payload = [{
        "model": c.model, "task": c.task, "source": c.source, "png": c.png_b64,
        "compiled": c.compiled, "log": c.compile_log or c.error,
        "checks": [{"n": k.name, "p": k.passed, "d": k.detail} for k in c.checks],
        "passed": c.passed, "total": c.total,
        "seconds": round(c.seconds, 1),
    } for c in cells]

    # header row
    head = []
    for t in tasks:
        lvl, desc = DIFFICULTY.get(t, ("", ""))
        head.append(
            f'<th><span class="lvl">{lvl}</span>'
            f'<span class="nm">{html.escape(t.replace("shader-", ""))}</span>'
            f'<span class="ds">{html.escape(desc)}</span></th>')

    # aggregates
    agg = {}
    for m in models:
        cs = [by[(m, t)] for t in tasks if (m, t) in by]
        if cs:
            agg[m] = (sum(c.score for c in cs) / len(cs),
                      sum(1 for c in cs if c.perfect), len(cs))

    body = []
    for m in models:
        is_ref = m.startswith("reference")
        score, perfect, n = agg.get(m, (0, 0, 0))
        tds = "".join(
            f"<td>{_cell(by[(m, t)], index[(m, t)])}</td>" if (m, t) in by else "<td>—</td>"
            for t in tasks)
        body.append(
            f'<tr class="{"ref" if is_ref else ""}"><th>{html.escape(m)}'
            f'<span class="agg">{score*100:.0f}% · {perfect}/{n} clean</span></th>{tds}</tr>')

    ranked = sorted(agg.items(), key=lambda kv: -kv[1][0])
    rank_rows = "".join(
        f'<tr><td class="num">{i+1}</td><td>{html.escape(m)}</td>'
        f'<td class="num">{s*100:.0f}%</td><td class="num">{p}/{n}</td></tr>'
        for i, (m, (s, p, n)) in enumerate(ranked))

    # ceiling warning — honest information design, not decoration
    non_ref = [(m, v) for m, v in ranked if not m.startswith("reference")]
    saturated = sum(1 for _, (s, *_ ) in non_ref if s >= 0.999)
    note = ""
    if saturated >= 1 and len(non_ref) > 1:
        note = (f'<div class="note"><b>⚠</b><p><b>The ladder saturates.</b> '
                f'{saturated} of {len(non_ref)} models scored 100%, so this set cannot '
                f'discriminate at the top. Harder tiers are needed before ranking '
                f'frontier models against each other.</p></div>')

    cmp_card = ""
    if swe_scores:
        vis = {m: i for i, (m, _) in enumerate(non_ref)}
        known = sorted(((m, swe_scores[m]) for m, _ in non_ref if m in swe_scores),
                       key=lambda r: -r[1])
        txt = {m: i for i, (m, _) in enumerate(known)}
        rows = "".join(
            f'<tr><td>{html.escape(m)}</td><td class="num">#{vis[m]+1}</td>'
            f'<td class="num">#{txt[m]+1}</td>'
            f'<td class="num {"pos" if txt[m]-vis[m] > 0 else ("neg" if txt[m]-vis[m] < 0 else "")}">'
            f'{txt[m]-vis[m]:+d}</td></tr>'
            for m in sorted(vis, key=lambda m: vis[m]) if m in txt)
        if rows:
            cmp_card = f"""<div class="card"><h2>Visual rank vs text-coding rank</h2>
            <p class="sub">A shift means the two abilities diverge — the model reasons about
            space better or worse than its coding benchmark predicts.</p>
            <table><thead><tr><th>model</th><th class="num">visual</th>
            <th class="num">text</th><th class="num">shift</th></tr></thead>
            <tbody>{rows}</tbody></table></div>"""

    # ---- verdict --------------------------------------------------------
    ext = {}
    if swe_scores:
        for label, rec in swe_scores.items():
            if isinstance(rec, dict) and "metrics" in rec:
                ext[base_name(label)] = rec["metrics"]
    v = analyse(cells, tasks, ext or None)
    st = v.stats
    mrow = []
    for k, lbl, fmt in (("signal_to_noise", "signal / noise", "{:.2f}"),
                        ("between_sd", "between-model SD", "{:.3f}"),
                        ("within_sd", "within-model SD", "{:.3f}"),
                        ("rho_spatial", "rho vs spatial", "{:+.2f}"),
                        ("rho_code_generation", "rho vs coding", "{:+.2f}")):
        val = st.get(k)
        if val is not None:
            mrow.append(f'<div class="metric"><span class="k">{lbl}</span>'
                        f'<span class="v">{fmt.format(val)}</span></div>')
    verdict_html = f"""
    <section class="verdict {'good' if v.reliable else ''}">
      <div class="vh"><span class="vtag">
        {'Verdict — usable' if v.reliable else 'Verdict — not yet trustworthy'}</span>
        <h2>{html.escape(v.headline)}</h2></div>
      <div class="vbody">
        <div class="vcol bad"><h3>What the numbers say</h3>
          <ul>{''.join(f'<li>{html.escape(r)}</li>' for r in v.reasons)}</ul></div>
        <div class="vcol fix"><h3>What would fix it</h3>
          <ul>{''.join(f'<li>{html.escape(f)}</li>' for f in v.fixes) or '<li>Nothing outstanding.</li>'}</ul></div>
      </div>
      {'<div class="metrics">' + ''.join(mrow) + '</div>' if mrow else ''}
    </section>"""

    n_models = len(non_ref)
    total_cells = sum(1 for c in cells if not c.model.startswith("reference"))
    compiled = sum(1 for c in cells
                   if not c.model.startswith("reference") and c.compiled)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Shader Spec Eval</title>
{FONTS}
<style>{CSS}</style></head>
<body>
<header>
  <p class="eyebrow">Shader Spec Eval · experimental</p>
  <h1>Do generated shaders satisfy the specification?</h1>
  <p class="lede">Every model wrote the same five shaders from the same
  natural-language specs. Each was rendered headlessly and scored against
  properties derived from the spec — tiling period, rotational symmetry, edge
  sharpness, animation — never against a reference image, and never by another
  model.</p>
  <div class="strip">
    <div class="stat"><span class="k">Models</span><span class="v">{n_models}</span></div>
    <div class="stat"><span class="k">Difficulty tiers</span><span class="v">{len(tasks)}</span></div>
    <div class="stat"><span class="k">Shaders rendered</span><span class="v">{total_cells}</span></div>
    <div class="stat"><span class="k">Compiled</span><span class="v">{compiled}<small> / {total_cells}</small></span></div>
  </div>
</header>
<main>
  {note}
  <div class="sheet"><table>
    <thead><tr><th class="corner">model</th>{''.join(head)}</tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table></div>

  {verdict_html}

  <div class="cards">
    <div class="card"><h2>Visual code ranking</h2>
      <p class="sub">Mean fraction of spec properties satisfied across all tiers.</p>
      <table><thead><tr><th class="num">#</th><th>model</th>
      <th class="num">score</th><th class="num">clean</th></tr></thead>
      <tbody>{rank_rows}</tbody></table></div>
    {cmp_card}
  </div>
</main>

<dialog id="dlg">
  <div class="dh"><div><div class="t" id="dt"></div><div class="m" id="dm"></div></div>
    <button class="close" onclick="document.getElementById('dlg').close()">Close</button></div>
  <div class="db"><div><img id="di" alt=""></div>
    <div><ul class="checks" id="dc"></ul><pre id="ds"></pre></div></div>
</dialog>

<script>
const DATA = {json.dumps(payload)};
function openDlg(i){{
  const d = DATA[i], dlg = document.getElementById('dlg');
  document.getElementById('dt').textContent = d.model + '  →  ' + d.task;
  document.getElementById('dm').textContent = d.compiled
    ? d.passed + '/' + d.total + ' properties · ' + d.seconds + 's'
    : (d.log || 'did not compile');
  const img = document.getElementById('di');
  if (d.png) {{ img.src = 'data:image/png;base64,' + d.png; img.style.display=''; }}
  else img.style.display = 'none';
  document.getElementById('dc').innerHTML = d.checks.map(c =>
    '<li><span class="n ' + (c.p ? 's-pass' : 's-fail') + '">' +
    (c.p ? 'PASS' : 'FAIL') + '  ' + c.n + '</span><span class="d">' + c.d + '</span></li>'
  ).join('');
  document.getElementById('ds').textContent = d.source || d.log || '(no source returned)';
  dlg.showModal();
}}
</script>
</body></html>"""


def write_dashboard(cells: list[Cell], tasks: list[str], models: list[str],
                    out: Path, swe_scores: dict[str, float] | None = None) -> Path:
    rendered = render_dashboard(cells, tasks, models, swe_scores)
    rendered = "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"
    out.write_text(rendered, encoding="utf-8")
    return out
