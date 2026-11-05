#!/usr/bin/env python3
"""Build the Hot Household Deals - Adelaide static site from data/briefs/*.json.

Outputs:
  index.html                 latest brief (top 3 + one tab per category)
  archive/index.html         list of past briefs
  archive/YYYY-MM-DD.html    one page per brief
  feed.json                  latest brief as JSON

Keeps the newest KEEP_DAYS briefs; older JSON files are deleted.
Standard library only.
"""
import html
import json
import re
import shutil
from datetime import date
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEFS = ROOT / "data" / "briefs"
ARCHIVE = ROOT / "archive"
KEEP_DAYS = 30
SITE = "Hot Household Deals - Adelaide"
TAGLINE = "A daily, hand-checked digest of genuinely good deals from Australian retailers, with Adelaide delivery or pickup."

ICONS = {
    "TVs": "📺", "Air fryers": "🍟", "Coffee machines": "☕", "Cordless stick vacuums": "🧹",
    "Robotic pool cleaners": "🏊", "Lawn mowers": "🌱", "Robot vacuums": "🤖", "Heat pump dryers": "👕",
    "Slow cookers": "🍲", "Kettle and toaster packs": "🍞", "Large rugs": "🟫",
    "Outdoor dining settings": "🪑", "Kitchenware": "🍳",
}

# Canonical categories, in tab order: (name used in JSON, short tab label)
CATEGORIES = [
    ("TVs", "TVs"),
    ("Air fryers", "Air fryers"),
    ("Coffee machines", "Coffee"),
    ("Cordless stick vacuums", "Stick vacs"),
    ("Robotic pool cleaners", "Pool cleaners"),
    ("Lawn mowers", "Mowers"),
    ("Robot vacuums", "Robot vacs"),
    ("Heat pump dryers", "Dryers"),
    ("Slow cookers", "Slow cookers"),
    ("Kettle and toaster packs", "Kettle + toaster"),
    ("Large rugs", "Rugs"),
    ("Outdoor dining settings", "Outdoor dining"),
    ("Kitchenware", "Kitchenware"),
]
CAT_NAMES = [c[0] for c in CATEGORIES]
MAX_PER_CATEGORY = 3
REQUIRED = ["date", "display_date", "summary", "top"]


def e(s):
    return html.escape(str(s or ""), quote=True)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


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
        unknown = [c["name"] for c in d.get("categories", []) if c.get("name") not in CAT_NAMES]
        if unknown:
            print(f"warning: {p.name}: unknown categories shown under their own tab: {unknown}")
        briefs.append(d)
    if not briefs:
        sys.exit("No briefs found in data/briefs/")
    briefs.sort(key=lambda d: d["date"], reverse=True)
    for d in briefs[KEEP_DAYS:]:
        (BRIEFS / f"{d['date']}.json").unlink()
    briefs = briefs[:KEEP_DAYS]
    fill_previously_posted(briefs)
    return briefs


def all_deals(b):
    yield from b.get("top", [])
    for c in b.get("categories", []):
        yield from c.get("deals", [])


def fill_previously_posted(briefs):
    """Fallback: if a deal has no previously_posted value, label it when the
    same item name appeared in an earlier brief (earliest date wins)."""
    first_seen = {}
    for b in reversed(briefs):  # oldest first
        for d in all_deals(b):
            key = norm(d.get("item"))
            if key and not d.get("previously_posted") and key in first_seen and first_seen[key] != b["display_date"]:
                d["previously_posted"] = first_seen[key]
            first_seen.setdefault(key, b["display_date"])


def links_html(links):
    out = [f'<a href="{e(l["url"])}" rel="noopener" target="_blank">{e(l["label"])} ↗</a>'
           for l in links or [] if l.get("url")]
    return f'<div class="links">{"".join(out)}</div>' if out else ""


def badges(d):
    out = []
    s = (d.get("status") or "").strip()
    low = s.lower()
    if d.get("previously_posted"):
        out.append(f'<span class="badge prev">Previously posted · first {e(d["previously_posted"])}</span>')
    if s and not (d.get("previously_posted") and low in ("still on", "price unchanged")):
        cls = "new" if low == "new" else "drop" if "drop" in low else "still"
        out.append(f'<span class="badge {cls}">{e(s)}</span>')
    if d.get("stretch"):
        out.append('<span class="badge stretch">Stretch pick</span>')
    return f'<div class="badges">{"".join(out)}</div>' if out else ""


def thumb_html(d, cat_name):
    icon = ICONS.get(cat_name or d.get("category"), "🛒")
    img = d.get("image") or ""
    if img.startswith("https://"):
        return (f'<div class="thumb"><img src="{e(img)}" alt="" loading="lazy" referrerpolicy="no-referrer" '
                f'onerror="this.parentNode.classList.add(\'fallback\');this.remove()"><span>{icon}</span></div>')
    return f'<div class="thumb fallback"><span>{icon}</span></div>'


def deal_html(d, rank=None, show_cat=False, cat_name=None):
    meta = []
    if d.get("usual"):
        meta.append(f"Usually {e(d['usual'])}")
    if d.get("saving"):
        meta.append(e(d["saving"]))
    if d.get("ends"):
        meta.append(f"Ends: {e(d['ends'])}")
    cat = f'<div class="cat">{e(d["category"])}</div>' if show_cat and d.get("category") else ""
    rank_html = f'<div class="rank">{rank}</div>' if rank else ""
    return f"""<article class="deal{' top' if rank else ''}">
  {rank_html}{thumb_html(d, cat_name)}<div class="body">
    {cat}<h3>{e(d.get('item'))}</h3>
    <div class="priceline"><span class="price">{e(d.get('price'))}</span><span class="retailer">@ {e(d.get('retailer'))}</span></div>
    {badges(d)}
    {f'<div class="meta">{" · ".join(meta)}</div>' if meta else ''}
    {f'<p>{e(d.get("why"))}</p>' if d.get('why') else ''}
    {links_html(d.get('links'))}
  </div>
</article>"""


def tabs_html(b):
    by_name = {c.get("name"): c for c in b.get("categories", [])}
    cats = list(CATEGORIES) + [(n, n) for n in by_name if n not in CAT_NAMES]
    first_with_deals = next((n for n, _ in cats if by_name.get(n, {}).get("deals")), cats[0][0])
    tabs, panels = [], []
    for name, label in cats:
        c = by_name.get(name, {})
        deals = c.get("deals", [])[:MAX_PER_CATEGORY]
        notes = c.get("notes", [])
        sid = slug(name)
        sel = name == first_with_deals
        count = f'<span class="count">{len(deals)}</span>' if deals else ""
        tabs.append(f'<button role="tab" id="tab-{sid}" aria-controls="p-{sid}" aria-selected="{"true" if sel else "false"}"'
                    f' class="{"has" if deals else "none"}" data-tab="{sid}">{e(label)}{count}</button>')
        inner = [f'<h2 class="panel-h">{e(name)}</h2>']
        inner += [deal_html(d, cat_name=name) for d in deals]
        if not deals:
            inner.append('<p class="empty">No deals met the bar today.</p>')
        if notes:
            if c.get("notes_title"):
                inner.append(f'<p class="notes-title">{e(c["notes_title"])}</p>')
            inner.append('<ul class="notes">' + "".join(f"<li>{e(n)}</li>" for n in notes) + "</ul>")
        panels.append(f'<section role="tabpanel" id="p-{sid}" aria-labelledby="tab-{sid}" class="panel"'
                      f'{"" if sel else " hidden"}>{"".join(inner)}</section>')
    return ('<h2>By category</h2><div class="tabs" role="tablist" aria-label="Categories">'
            + "".join(tabs) + "</div>" + "".join(panels))


def parse_date(s):
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def sale_html(s, today):
    starts, ends = parse_date(s.get("starts")), parse_date(s.get("ends"))
    if starts and starts > today:
        n = (starts - today).days
        chip, cls, tile = ("Tomorrow" if n == 1 else f"In {n} days"), "soon", starts
    elif ends:
        n = (ends - today).days
        chip = "Ends today" if n <= 0 else "Ends tomorrow" if n == 1 else f"Ends in {n} days"
        cls, tile = ("urgent" if n <= 2 else "live"), ends
    else:
        chip, cls, tile = "Live now", "live", None
    if tile:
        label = "Ends" if cls in ("live", "urgent") else tile.strftime("%a")
        tile_html = (f'<div class="tile"><small>{label}</small><b>{tile.day}</b>'
                     f'<small>{tile.strftime("%b")}</small></div>')
    else:
        tile_html = '<div class="tile flame"><b>🔥</b><small>Now</small></div>'
    rumour = '' if s.get("confirmed", True) else '<span class="chip rumour">Rumoured</span>'
    title = s.get("title") or ""
    return f"""<article class="sale {cls}">{tile_html}<div class="sbody">
<div class="chips"><span class="chip {cls}">{e(chip)}</span>{rumour}</div>
{f'<h3>{e(title)}</h3>' if title else ''}<p>{e(s.get("text"))}</p>{links_html(s.get("links"))}</div></article>"""


def sales_html(b):
    if not b.get("sales"):
        return ""
    today = parse_date(b["date"])
    return ('<section class="sales-strip"><h2>📅 Sales in the next 7 days</h2><div class="sales">'
            + "".join(sale_html(s, today) for s in b["sales"]) + "</div></section>")


def brief_html(b):
    parts = [f'<p class="summary">{e(b["summary"])}</p>', sales_html(b)]
    parts.append('<section class="hero"><h2>Top 3 deals today</h2>')
    if b["top"]:
        parts.append('<div class="grid">')
        parts += [deal_html(d, i + 1, show_cat=True) for i, d in enumerate(b["top"][:3])]
        parts.append("</div>")
    else:
        parts.append('<p class="empty">Nothing met the bar today.</p>')
    parts.append("</section>")
    parts.append(tabs_html(b))
    for n in b.get("notes", []):
        parts.append(f'<p class="note"><b>{e(n.get("label"))}:</b> {e(n.get("text"))}</p>')
    return "\n".join(parts)


CSS = """
:root{--bg:#fbf8f5;--card:#fff;--ink:#1c1917;--muted:#6b6460;--line:#ebe4de;--hot:#d9480f;--hot-soft:#fff0e8;--ok:#2b8a3e;--ok-soft:#ebfbee;--blue:#1864ab;--blue-soft:#e7f1fb;--violet:#6741d9;--violet-soft:#f1edff;--amber:#8a5a00;--amber-soft:#fff6db}
@media (prefers-color-scheme:dark){:root{--bg:#141110;--card:#1f1b19;--ink:#f2ece8;--muted:#a59c96;--line:#332c28;--hot:#ff8a4c;--hot-soft:#3a2117;--ok:#69db7c;--ok-soft:#1b2e1f;--blue:#74c0fc;--blue-soft:#172634;--violet:#b197fc;--violet-soft:#251f3a;--amber:#ffd43b;--amber-soft:#2f2712}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--hot)}
.wrap{max-width:820px;margin:0 auto;padding:0 16px 48px}
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
.hero{background:linear-gradient(180deg,var(--hot-soft),transparent);border-radius:18px;padding:4px 14px 14px;margin:20px -14px 0}
.hero h2{color:var(--hot);font-size:15px;margin-top:18px}
.grid{display:grid;gap:12px}
.deal{display:flex;gap:14px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:12px}
.grid .deal{margin:0}
.deal.top{border-color:color-mix(in srgb,var(--hot) 40%,var(--line));box-shadow:0 2px 10px color-mix(in srgb,var(--hot) 10%,transparent)}
.deal.top h3{font-size:19px}
.rank{flex:none;width:36px;height:36px;border-radius:50%;background:var(--hot);color:#fff;display:grid;place-items:center;font-weight:800}
.body{min-width:0;flex:1}
.cat{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.deal h3{margin:2px 0 6px;font-size:17px;line-height:1.3}
.priceline{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px}
.price{font-size:20px;font-weight:800;color:var(--hot)}
.deal.top .price{font-size:24px}
.retailer{color:var(--muted)}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.badge{font-size:12px;font-weight:600;padding:2px 8px;border-radius:999px}
.badge.new{background:var(--ok-soft);color:var(--ok)}
.badge.still{background:var(--blue-soft);color:var(--blue)}
.badge.drop{background:var(--hot-soft);color:var(--hot)}
.badge.prev{background:var(--amber-soft);color:var(--amber)}
.badge.stretch{background:var(--violet-soft);color:var(--violet)}
.meta{font-size:14px;color:var(--muted);margin-top:6px}
.deal p{margin:8px 0 0;font-size:15px}
.links{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.links a{font-size:14px;text-decoration:none;border:1px solid var(--line);padding:4px 10px;border-radius:8px;background:var(--bg)}
.tabs{display:flex;gap:6px;overflow-x:auto;padding-bottom:8px;margin:0 -16px 14px;padding-left:16px;padding-right:16px;scrollbar-width:thin}
.tabs button{flex:none;font:inherit;font-size:14px;font-weight:600;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:7px 12px;border-radius:999px;cursor:pointer;display:flex;align-items:center;gap:6px}
.tabs button.none{color:var(--muted);font-weight:500}
.tabs button[aria-selected=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.tabs .count{font-size:12px;background:var(--hot);color:#fff;border-radius:999px;padding:0 7px;line-height:18px}
.panel-h{display:none}
.notes-title{font-weight:600;margin:14px 0 6px;font-size:15px}
@media (min-width:700px){.tabs{flex-wrap:wrap;overflow:visible}}
.nojs .tabs{display:none}
.nojs .panel[hidden]{display:block}
.nojs .panel-h{display:block}
.notes{padding-left:20px;margin:0}
.notes li{margin-bottom:8px}
.panel .notes{margin-top:8px;color:var(--muted);font-size:15px}
.note{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:12px 0}
.empty{color:var(--muted);background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:14px;margin:0 0 12px}
.archive li{margin:6px 0}
.thumb{flex:none;width:72px;height:72px;border-radius:12px;background:#fff;border:1px solid var(--line);display:grid;place-items:center;overflow:hidden}
.deal.top .thumb{width:96px;height:96px}
.thumb img{width:100%;height:100%;object-fit:contain;padding:4px}
.thumb span{display:none;font-size:34px}
.deal.top .thumb span{font-size:44px}
.thumb.fallback{background:var(--hot-soft)}
.thumb.fallback span{display:block}
@media (max-width:480px){.deal{flex-wrap:wrap}.deal.top .thumb,.thumb{width:64px;height:64px}.deal.top .thumb span,.thumb span{font-size:30px}.deal .body{flex-basis:100%}.deal.top .body{flex-basis:100%}}
.sales-strip h2{margin-top:22px}
.sales{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;margin:0 -16px;padding:2px 16px 10px}
.sale{flex:none;width:270px;scroll-snap-align:start;display:flex;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;border-top:4px solid var(--blue)}
.sale.live{border-top-color:var(--ok)}
.sale.urgent{border-top-color:var(--hot)}
.sale .tile{flex:none;width:52px;height:60px;border-radius:10px;background:var(--bg);border:1px solid var(--line);display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.1}
.sale .tile b{font-size:22px}
.sale .tile small{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.sale.urgent .tile{background:var(--hot-soft);border-color:transparent}
.sale.urgent .tile b{color:var(--hot)}
.sbody{min-width:0}
.sale h3{margin:6px 0 2px;font-size:16px;line-height:1.25}
.sale p{margin:0;font-size:14px;color:var(--muted)}
.sale .links{margin-top:8px}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;padding:2px 8px;border-radius:999px}
.chip.live{background:var(--ok-soft);color:var(--ok)}
.chip.urgent{background:var(--hot);color:#fff}
.chip.soon{background:var(--blue-soft);color:var(--blue)}
.chip.rumour{background:var(--amber-soft);color:var(--amber)}
@media (min-width:700px){.sales{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));overflow:visible;margin:0;padding:0}.sale{width:auto}}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
"""

JS = """
document.documentElement.classList.remove('nojs');
(function(){
  var tabs=[].slice.call(document.querySelectorAll('[role=tab]'));
  if(!tabs.length)return;
  function pick(id,focus){
    tabs.forEach(function(t){
      var on=t.dataset.tab===id;
      t.setAttribute('aria-selected',on);t.tabIndex=on?0:-1;
      document.getElementById('p-'+t.dataset.tab).hidden=!on;
      if(on&&focus)t.focus();
      if(on){var bar=t.parentNode,l=t.offsetLeft-bar.offsetLeft;
        if(l<bar.scrollLeft||l+t.offsetWidth>bar.scrollLeft+bar.clientWidth)bar.scrollLeft=l-16;}
    });
  }
  tabs.forEach(function(t,i){
    t.addEventListener('click',function(){pick(t.dataset.tab);history.replaceState(null,'','#'+t.dataset.tab);});
    t.addEventListener('keydown',function(ev){
      var j=ev.key==='ArrowRight'?i+1:ev.key==='ArrowLeft'?i-1:null;
      if(j===null)return;ev.preventDefault();pick(tabs[(j+tabs.length)%tabs.length].dataset.tab,true);
    });
  });
  var h=location.hash.slice(1);
  if(h&&document.getElementById('p-'+h))pick(h);
  else{var s=tabs.filter(function(t){return t.getAttribute('aria-selected')==='true'})[0];pick(s.dataset.tab);}
})();
"""


def page(title, body, rel=""):
    return f"""<!doctype html>
<html lang="en-AU" class="nojs"><head>
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
</div><script>{JS}</script></body></html>
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
