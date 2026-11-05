#!/usr/bin/env python3
"""Build the Very Hot Deals static site from data/briefs/*.json.

Outputs:
  index.html                 latest brief
  archive/index.html         list of past briefs
  archive/YYYY-MM-DD.html    one page per brief
  feed.json                  latest brief as JSON (for anything that wants it)

Keeps the newest KEEP_DAYS briefs; older JSON files are deleted.
Standard library only.
"""
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEFS = ROOT / "data" / "briefs"
ARCHIVE = ROOT / "archive"
KEEP_DAYS = 30
SITE = "Very Hot Deals"
TAGLINE = "A daily, hand-checked digest of genuinely good deals from Australian retailers, with Adelaide delivery or pickup."

REQUIRED = ["date", "display_date", "summary", "top"]


def e(s):
    return html.escape(str(s or ""), quote=True)


def load():
    briefs = []
    for p in sorted(BRIEFS.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            sys.exit(f"Invalid JSON in {p.name}: {err}")
        missing = [k for k in REQUIRED if k not in d]
        if missing:
            sys.exit(f"{p.name} is missing fields: {', '.join(missing)}")
        if d["date"] != p.stem:
            sys.exit(f"{p.name}: 'date' must match the file name")
        briefs.append(d)
    if not briefs:
        sys.exit("No briefs found in data/briefs/")
    briefs.sort(key=lambda d: d["date"], reverse=True)
    for d in briefs[KEEP_DAYS:]:
        (BRIEFS / f"{d['date']}.json").unlink()
    return briefs[:KEEP_DAYS]


def links_html(links):
    out = [f'<a href="{e(l["url"])}" rel="noopener" target="_blank">{e(l["label"])} ↗</a>'
           for l in links or [] if l.get("url")]
    return f'<div class="links">{"".join(out)}</div>' if out else ""


def status_badge(status):
    s = (status or "").strip()
    if not s:
        return ""
    low = s.lower()
    cls = "new" if low == "new" else "drop" if "drop" in low else "still"
    return f'<span class="badge {cls}">{e(s)}</span>'


def deal_html(d, rank=None):
    meta = []
    if d.get("usual"):
        meta.append(f"Usually {e(d['usual'])}")
    if d.get("saving"):
        meta.append(e(d["saving"]))
    if d.get("ends"):
        meta.append(f"Ends: {e(d['ends'])}")
    badges = status_badge(d.get("status"))
    if d.get("stretch"):
        badges += '<span class="badge stretch">stretch pick</span>'
    cat = f'<div class="cat">{e(d["category"])}</div>' if d.get("category") else ""
    rank_html = f'<div class="rank">{rank}</div>' if rank else ""
    return f"""<article class="deal{' top' if rank else ''}">
  {rank_html}<div class="body">
    {cat}<h3>{e(d.get('item'))}</h3>
    <div class="priceline"><span class="price">{e(d.get('price'))}</span><span class="retailer">@ {e(d.get('retailer'))}</span>{badges}</div>
    {f'<div class="meta">{" · ".join(meta)}</div>' if meta else ''}
    {f'<p>{e(d.get("why"))}</p>' if d.get('why') else ''}
    {links_html(d.get('links'))}
  </div>
</article>"""


def brief_html(b):
    parts = [f'<p class="summary">{e(b["summary"])}</p>']
    if b["top"]:
        parts.append('<h2>Top deals today</h2><div class="grid">')
        parts += [deal_html(d, i + 1) for i, d in enumerate(b["top"])]
        parts.append("</div>")
    else:
        parts.append('<p class="empty">Nothing met the bar today.</p>')
    for c in b.get("categories", []):
        parts.append(f'<h2>{e(c["name"])}</h2>')
        parts += [deal_html(d) for d in c.get("deals", [])]
        if c.get("notes"):
            parts.append('<ul class="notes">' + "".join(f"<li>{e(n)}</li>" for n in c["notes"]) + "</ul>")
    for n in b.get("notes", []):
        parts.append(f'<p class="note"><b>{e(n.get("label"))}:</b> {e(n.get("text"))}</p>')
    if b.get("nothing_today"):
        parts.append('<p class="note muted"><b>Nothing worthwhile today:</b> '
                     + e(", ".join(b["nothing_today"])) + "</p>")
    if b.get("sales"):
        parts.append('<h2>Sales in the next 7 days</h2><ul class="sales">')
        for s in b["sales"]:
            parts.append(f'<li>{e(s.get("text"))}{links_html(s.get("links"))}</li>')
        parts.append("</ul>")
    return "\n".join(parts)


CSS = """
:root{--bg:#fbf8f5;--card:#fff;--ink:#1c1917;--muted:#6b6460;--line:#ebe4de;--hot:#d9480f;--hot-soft:#fff0e8;--ok:#2b8a3e;--ok-soft:#ebfbee;--blue:#1864ab;--blue-soft:#e7f1fb;--violet:#6741d9;--violet-soft:#f1edff}
@media (prefers-color-scheme:dark){:root{--bg:#141110;--card:#1f1b19;--ink:#f2ece8;--muted:#a59c96;--line:#332c28;--hot:#ff8a4c;--hot-soft:#3a2117;--ok:#69db7c;--ok-soft:#1b2e1f;--blue:#74c0fc;--blue-soft:#172634;--violet:#b197fc;--violet-soft:#251f3a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--hot)}
.wrap{max-width:760px;margin:0 auto;padding:0 16px 48px}
header{padding:28px 0 8px;border-bottom:1px solid var(--line);margin-bottom:20px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink)}
.brand .flame{font-size:28px}
.brand b{font-size:24px;letter-spacing:-.02em}
.tag{color:var(--muted);margin:6px 0 0;font-size:14px}
.dateline{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-top:14px}
.dateline .d{font-weight:700;font-size:18px}
.dateline a{font-size:14px}
.summary{font-size:18px;margin:0 0 8px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:32px 0 12px}
.grid{display:grid;gap:12px}
.deal{display:flex;gap:14px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:12px}
.grid .deal{margin:0}
.deal.top{border-color:color-mix(in srgb,var(--hot) 35%,var(--line))}
.rank{flex:none;width:34px;height:34px;border-radius:50%;background:var(--hot);color:#fff;display:grid;place-items:center;font-weight:700}
.body{min-width:0;flex:1}
.cat{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.deal h3{margin:2px 0 6px;font-size:17px;line-height:1.3}
.priceline{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px}
.price{font-size:20px;font-weight:800;color:var(--hot)}
.retailer{color:var(--muted)}
.badge{font-size:12px;font-weight:600;padding:2px 8px;border-radius:999px}
.badge.new{background:var(--ok-soft);color:var(--ok)}
.badge.still{background:var(--blue-soft);color:var(--blue)}
.badge.drop{background:var(--hot-soft);color:var(--hot)}
.badge.stretch{background:var(--violet-soft);color:var(--violet)}
.meta{font-size:14px;color:var(--muted);margin-top:4px}
.deal p{margin:8px 0 0;font-size:15px}
.links{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.links a{font-size:14px;text-decoration:none;border:1px solid var(--line);padding:4px 10px;border-radius:8px;background:var(--bg)}
.notes,.sales{padding-left:20px;margin:0}
.notes li,.sales li{margin-bottom:8px}
.sales .links{margin-top:4px}
.note{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:12px 0}
.muted{color:var(--muted)}
.empty{color:var(--muted)}
.archive li{margin:6px 0}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
"""


def page(title, body, rel=""):
    return f"""<!doctype html>
<html lang="en-AU"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(TAGLINE)}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔥</text></svg>">
<style>{CSS}</style>
</head><body><div class="wrap">
<header><a class="brand" href="{rel}index.html"><span class="flame">🔥</span><b>{SITE}</b></a>
<p class="tag">{e(TAGLINE)}</p></header>
{body}
<footer>Updated every morning (Adelaide time). Prices and stock change quickly: always check the retailer before buying. Not affiliated with any retailer; no affiliate links.</footer>
</div></body></html>
"""


def main():
    briefs = load()
    latest = briefs[0]
    if ARCHIVE.exists():
        shutil.rmtree(ARCHIVE)
    ARCHIVE.mkdir()

    for i, b in enumerate(briefs):
        nav = []
        if i + 1 < len(briefs):
            nav.append(f'<a href="{briefs[i + 1]["date"]}.html">← {e(briefs[i + 1]["display_date"])}</a>')
        if i > 0:
            nav.append(f'<a href="{briefs[i - 1]["date"]}.html">{e(briefs[i - 1]["display_date"])} →</a>')
        nav.append('<a href="index.html">All days</a>')
        body = (f'<div class="dateline"><span class="d">{e(b["display_date"])}</span>'
                f'<span>{" · ".join(nav)}</span></div>' + brief_html(b))
        (ARCHIVE / f"{b['date']}.html").write_text(
            page(f"{SITE} – {b['display_date']}", body, "../"), encoding="utf-8")

    items = "".join(f'<li><a href="{b["date"]}.html">{e(b["display_date"])}</a> – {e(b["summary"])}</li>'
                    for b in briefs)
    (ARCHIVE / "index.html").write_text(
        page(f"{SITE} – Archive", f'<h2>Past briefs</h2><ul class="archive">{items}</ul>', "../"),
        encoding="utf-8")

    body = (f'<div class="dateline"><span class="d">{e(latest["display_date"])}</span>'
            f'<a href="archive/index.html">Past days</a></div>' + brief_html(latest))
    (ROOT / "index.html").write_text(page(f"{SITE} – Today's best deals", body), encoding="utf-8")
    (ROOT / "feed.json").write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built {len(briefs)} brief(s); latest {latest['date']}")


if __name__ == "__main__":
    main()
