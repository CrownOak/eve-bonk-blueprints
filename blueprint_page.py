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


def render_page(state):
    """state = {generated_at, me_level, basis, count, rows:[...]}"""
    if not state or not state.get("rows"):
        body = '<div class="empty">No results yet. The monthly run will populate this page.</div>'
        sub = "waiting for first run"
    else:
        gen = _esc(state.get("generated_at"))
        me = _esc(state.get("me_level"))
        basis = _esc(state.get("basis"))
        cnt = _esc(state.get("count"))
        sub = (f"{cnt} profitable builds &middot; ME{me} &middot; {basis} &middot; "
               f"generated {gen} UTC")
        trs = []
        for r in state["rows"]:
            tid = _esc(r.get("type_id"))
            name = _esc(r.get("name"))
            link = "https://market.fuzzwork.co.uk/types/" + str(r.get("type_id", "")) + "/"
            iskhr = r.get("isk_per_hour", 0) or 0
            cls = "good" if iskhr >= 5_000_000 else ("warn" if iskhr >= 1_000_000 else "")
            trs.append(
                f"<tr><td class='rank'>{_esc(r.get('rank'))}</td>"
                f"<td class='who'><a href='{_esc(link)}' target='_blank' rel='noopener'>{name}</a></td>"
                f"<td class='cat'>{_esc(r.get('category'))}</td>"
                f"<td class='num strong {cls}'>{_isk(iskhr)}</td>"
                f"<td class='num'>{_isk(r.get('profit'))}</td>"
                f"<td class='num'>{_esc(round(r.get('build_hours', 0) or 0, 2))}</td>"
                f"<td class='num'>{_esc(round(r.get('margin_pct', 0) or 0))}%</td>"
                f"<td class='num'>{_isk(r.get('product_value'))}</td>"
                f"<td class='num'>{_isk(r.get('material_cost'))}</td>"
                f"<td class='num'>{_esc(int(r.get('daily_volume', 0) or 0))}</td></tr>")
        body = (
            "<table><thead><tr>"
            "<th>#</th><th>ITEM</th><th>CAT</th><th>ISK/HR</th><th>PROFIT/BUILD</th>"
            "<th>HRS</th><th>MARGIN</th><th>SELL</th><th>MAT COST</th><th>VOL/DAY</th>"
            "</tr></thead><tbody>" + "".join(trs) + "</tbody></table>")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>BONK - Blueprint Scanner</title>
<style>
  :root {{ --ink:#0d1310; --panel:#141d18; --line:#21302a; --txt:#e6efe9; --mut:#8fa89a; --grn:#5fd9a0; --link:#73e0b4; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--ink); color:var(--txt);
         font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  header {{ padding:22px 28px 14px; border-bottom:1px solid var(--line); }}
  h1 {{ margin:0; font-size:19px; letter-spacing:.06em; font-weight:800; color:var(--grn); }}
  .sub {{ color:var(--mut); margin-top:6px; font-size:12.5px; }}
  .wrap {{ padding:18px 28px 40px; }}
  table {{ border-collapse:collapse; width:100%; background:var(--panel);
           border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
  th {{ text-align:left; background:#0a110d; color:#c5d6cd; font-size:11px;
        letter-spacing:.05em; text-transform:uppercase; padding:10px 12px; }}
  td {{ padding:9px 12px; border-top:1px solid var(--line); }}
  tr:hover td {{ background:#1c2a23; }}
  .rank {{ color:var(--mut); width:34px; }}
  .who a {{ color:var(--link); text-decoration:none; font-weight:600; }}
  .who a:hover {{ text-decoration:underline; }}
  .cat {{ color:var(--mut); font-size:12px; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .strong {{ font-weight:800; }}
  .good {{ color:var(--grn); }} .warn {{ color:#e9c46a; }}
  .empty {{ padding:40px; text-align:center; color:var(--mut);
            background:var(--panel); border:1px solid var(--line); border-radius:8px; }}
  footer {{ color:var(--mut); font-size:11.5px; padding:0 28px 30px; }}
</style></head>
<body>
  <header>
    <h1>BONK &middot; BLUEPRINT PROFITABILITY SCANNER</h1>
    <div class="sub">{sub}</div>
  </header>
  <div class="wrap">{body}</div>
  <footer>Most profitable T1 builds by ISK/hour, from EVE SDE + live Jita prices. Profit assumes
  Jita fills; treat as a directional guide. Top of the list = what to train toward and mine for.
  Click an item for its Fuzzwork market page. Auto-refreshes every {REFRESH_SECONDS//60}m.</footer>
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
