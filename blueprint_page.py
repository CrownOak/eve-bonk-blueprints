#!/usr/bin/env python3
"""
BONK Blueprint Scanner : shared page renderer.
Renders the "best builds by ISK/hour" HTML (written to disk each run, client-side
encrypted, then published). Same lock model as the sibling EVE tools.
"""
import html, os, tempfile

REFRESH_SECONDS = 3600  # monthly tool; light refresh


def _esc(v):
    return "" if v is None or v == "" else html.escape(str(v))


def _isk(v):
    try:
        v = float(v or 0)
    except (TypeError, ValueError):
        return ""
    a = abs(v)
    if a >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    if a >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if a >= 1_000:
        return f"{v/1_000:.0f}k"
    return f"{v:.0f}"


def _qty(n):
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


TIPS = {
    "#": "Rank within this category by ISK per hour.",
    "ITEM": "What you build. Click for its EVE Ref page (market + manufacturing).",
    "ISK/HR": "Profit per hour of build time, across the whole run. This is the ranking metric.",
    "OUT": "Units produced per build run. Some blueprints (bombs, charges) make a batch, so the run totals cover all of them.",
    "SELL/U": "Product sell price PER UNIT at Jita. This matches what you see on the market / EVE Ref.",
    "MAT/U": "Material cost per unit (run material cost divided by units per run), at Jita sell, ME-adjusted.",
    "MARGIN": "Profit as a percent of total cost.",
    "PROFIT/RUN": "Profit from one full build run (all OUT units): sell minus materials minus ~5% fee.",
    "HRS": "Build time in hours for one run at the assumed Material Efficiency.",
    "VOL/DAY": "Daily units sold on the market (liquidity; low = hard to offload).",
}


def _th(label):
    return f"<th data-tip=\"{html.escape(TIPS.get(label, ''))}\">{label}</th>"


def render_page(state):
    """state = {generated_at, me_level, basis, count, rows:[...]}"""
    if not state or not state.get("rows"):
        body = '<div class="empty">No results yet. The monthly run will populate this page.</div>'
        sub = "waiting for first run"
    else:
        gen = _esc(state.get("generated_at"))
        me = _esc(state.get("me_level"))
        basis = _esc(state.get("basis"))
        per = _esc(state.get("per_cat") or "5")
        sub = (f"top {per} per category by ISK/hour &middot; ME{me} &middot; {basis} &middot; "
               f"generated {gen} UTC")
        groups = {}
        for r in state["rows"]:
            groups.setdefault(r.get("category") or "Other", []).append(r)
        order = ["Ships", "Modules", "Ammo", "Drones"]
        cats = [c for c in order if c in groups] + [c for c in groups if c not in order]
        sections = []
        for cat in cats:
            trs = []
            for r in groups[cat]:
                name = _esc(r.get("name"))
                link = "https://everef.net/types/" + str(r.get("type_id", ""))
                iskhr = r.get("isk_per_hour", 0) or 0
                cls = "good" if iskhr >= 5_000_000 else ("warn" if iskhr >= 1_000_000 else "")
                outq = int(r.get("out_qty", 1) or 1)
                bp = r.get("build_path") or {}
                plan = bp.get("plan") or []
                comps = bp.get("components") or []
                detail = ""
                if plan or comps:
                    title = ("Mining plan &middot; mine these, then build" if plan
                             else "Materials &middot; build or buy")
                    table_html = ""
                    total_html = ""
                    if plan:
                        prows = "".join(
                            f"<tr><td class='who'>{_esc(p.get('mineral'))}</td>"
                            f"<td class='num'>{_qty(p.get('qty'))}</td>"
                            f"<td>{_esc(p.get('ore'))}</td>"
                            f"<td class='sec'>{_esc(p.get('sec'))}</td>"
                            f"<td class='num'>{_qty(p.get('units'))}</td>"
                            f"<td class='num'>{_qty(p.get('m3'))}</td></tr>" for p in plan)
                        table_html = (
                            "<table class='bpmine'><thead><tr><th>MINERAL</th><th>NEED</th><th>MINE</th>"
                            "<th>SPACE</th><th>ORE UNITS</th><th>~m&sup3;</th></tr></thead>"
                            f"<tbody>{prows}</tbody></table>")
                        total_html = (
                            f"<div class='bptot'>~{_qty(bp.get('total_m3'))} m&sup3; of raw ore total "
                            "(per-mineral upper bound; the richest ores drop byproducts that cover others, "
                            "so real volume is less). Lo/Null minerals can also just be bought.</div>")
                    comptxt = " &middot; ".join(f"{_esc(n)} &times;{_qty(q)}" for n, q in comps)
                    compline = f"<div class='bpcomp'>Build or buy: {comptxt}</div>" if comps else ""
                    detail = (
                        "<tr class='detail' style='display:none'><td colspan='10'>"
                        f"<div class='bpath'><div class='bptitle'>{title}</div>"
                        f"{table_html}{compline}{total_html}"
                        "</div></td></tr>")
                toggle = "<button class='exp' aria-label='build path'>&#9662;</button> " if detail else ""
                trs.append(
                    f"<tr><td class='rank'>{_esc(r.get('rank'))}</td>"
                    f"<td class='who'>{toggle}<a href='{_esc(link)}' target='_blank' rel='noopener'>{name}</a></td>"
                    f"<td class='num strong {cls}'>{_isk(iskhr)}</td>"
                    f"<td class='num'>{('&times;' + str(outq)) if outq > 1 else '1'}</td>"
                    f"<td class='num'>{_isk(r.get('unit_sell'))}</td>"
                    f"<td class='num'>{_isk(r.get('unit_mat'))}</td>"
                    f"<td class='num'>{_esc(round(r.get('margin_pct', 0) or 0))}%</td>"
                    f"<td class='num'>{_isk(r.get('profit'))}</td>"
                    f"<td class='num'>{_esc(round(r.get('build_hours', 0) or 0, 2))}</td>"
                    f"<td class='num'>{_esc(int(r.get('daily_volume', 0) or 0))}</td></tr>"
                    + detail)
            sections.append(
                f"<div class='thead' style='margin-top:22px'>{_esc(cat)}</div>"
                "<table><thead><tr>"
                + _th("#") + _th("ITEM") + _th("ISK/HR") + _th("OUT") + _th("SELL/U")
                + _th("MAT/U") + _th("MARGIN") + _th("PROFIT/RUN") + _th("HRS") + _th("VOL/DAY")
                + "</tr></thead><tbody>" + "".join(trs) + "</tbody></table>")
        body = "".join(sections)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>BONK - Blueprint Scanner</title>
<link rel="stylesheet" href="https://crownoak.github.io/wdeve/common.css?v=3">
<style>
  button.exp{{ background:transparent; border:1px solid var(--line); color:var(--ore); cursor:pointer;
    font-family:var(--mono); font-size:10px; line-height:1; padding:2px 6px; margin-right:7px; vertical-align:middle; }}
  button.exp:hover{{ border-color:var(--ore); background:rgba(70,255,94,.12); }}
  tr.detail>td{{ background:var(--black); padding:0 12px 16px; border-top:0; }}
  .bpath{{ border-left:2px solid var(--ore); background:var(--steel); padding:13px 16px; text-align:left; }}
  .bptitle{{ font-family:var(--mono); font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--ore); margin-bottom:10px; }}
  table.bpmine{{ width:auto; min-width:520px; background:transparent; border:0; margin:0 0 8px; }}
  table.bpmine th{{ position:static; background:transparent; font-size:10px; border-bottom:1px solid var(--line); }}
  table.bpmine td{{ border-top:1px solid var(--line-soft); }}
  .bpcomp{{ color:var(--silver-dim); font-family:var(--mono); font-size:11.5px; margin:8px 0 4px; }}
  .bptot{{ color:var(--muted); font-family:var(--mono); font-size:11px; margin-top:6px; max-width:760px; line-height:1.5; }}
</style></head>
<body>
  <header>
    <h1>BONK &middot; BLUEPRINT PROFITABILITY SCANNER</h1>
    <div class="sub">{sub}</div>
  </header>
  <div class="wrap">{body}</div>
  <footer>Most profitable T1 builds by ISK/hour, from EVE SDE + live Jita prices. Profit assumes
  Jita fills; treat as a directional guide. Top of the list = what to train toward and mine for.
  Click an item for its EVE Ref page (market + manufacturing). Auto-refreshes every {REFRESH_SECONDS//60}m.</footer>
<script>
Array.prototype.forEach.call(document.querySelectorAll("button.exp"),function(b){{
  b.onclick=function(){{ var tr=b.closest("tr").nextElementSibling;
    if(tr&&tr.classList.contains("detail")){{ var s=tr.style.display==="none";
      tr.style.display=s?"":"none"; b.innerHTML=s?"&#9652;":"&#9662;"; }} }};
}});
</script>
<script src="https://crownoak.github.io/wdeve/nav.js"></script>
</body></html>"""


def write_html(path, state, password=None, allow_plain=False):
    """Atomically write render_page(state). FAIL-CLOSED: refuses to write a plaintext
    page unless allow_plain=True, so a missing password can never leak content."""
    if not password and not allow_plain:
        raise ValueError("refusing to write an unlocked page: no password (set EVE_PAGE_PASSWORD, "
                         "or pass allow_plain=True for explicit local-only output)")
    text = render_page(state)
    if password:
        import page_lock
        text = page_lock.lock_page(text, password, title="BONK - Blueprint Scanner")
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(suffix=".html", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try: os.remove(tmp)
        except OSError: pass
        raise
    return path
