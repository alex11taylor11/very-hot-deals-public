#!/usr/bin/env python3
"""Build the Taytino Black Friday Feed static site from data/briefs/*.json.

Outputs:
  index.html                 latest brief
  archive/index.html         list of past briefs
  archive/YYYY-MM-DD.html    one page per brief
  feed.json                  latest brief as JSON

Keeps the newest KEEP_DAYS briefs; older JSON files are deleted.
Standard library only. Schema: see REFRESH.md.
"""
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEFS = ROOT / "data" / "briefs"
ARCHIVE = ROOT / "archive"
KEEP_DAYS = 30
MAX_TOP = 5
MAX_PER_CATEGORY = 3
SITE = "Taytino Black Friday Feed"
TAGLINE = "Genuinely good deals from Australian retailers, price-history checked every morning. Adelaide delivery or pickup."
REQUIRED = ["date", "display_date", "summary", "top"]

# Canonical categories, in display order: (name used in JSON, short label, icon)
CATEGORIES = [
    ("BBQs", "BBQs", "🔥"),
    ("Coffee machines", "Coffee", "☕"),
    ("TVs", "TVs", "📺"),
    ("Office screens", "Monitors", "🖥️"),
    ("Office chairs", "Office chairs", "💺"),
    ("Robotic pool cleaners", "Pool robots", "🏊"),
    ("Large rugs", "Rugs", "🟫"),
    ("Air fryers", "Air fryers", "🍟"),
    ("Microwaves", "Microwaves", "♨️"),
    ("Slow cookers", "Slow cookers", "🍲"),
    ("Kitchenware", "Kitchenware", "🔪"),
    ("Cordless stick vacuums", "Stick vacs", "🧹"),
    ("Robot vacuums", "Robot vacs", "🤖"),
    ("Lawn mowers", "Mowers", "🌱"),
    ("Heat pump dryers", "Dryers", "👕"),
    ("Kettle and toaster packs", "Kettle + toaster", "🍞"),
    ("Outdoor dining settings", "Outdoor dining", "🪑"),
]
CAT_NAMES = [c[0] for c in CATEGORIES]
ICONS = {c[0]: c[2] for c in CATEGORIES}


# ---------------------------------------------------------------- helpers

def e(s):
    return html.escape(str(s or ""), quote=True)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def money(s):
    m = re.search(r"\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)", s or "")
    return float(m.group(1).replace(",", "")) if m else None


def pct_saving(d):
    m = re.search(r"(\d{1,2})\s*%", d.get("saving") or "")
    if m:
        return int(m.group(1))
    p, u = money(d.get("price")), money(d.get("usual"))
    if p and u and u > p:
        return round((u - p) / u * 100)
    return None


def parse_date(s):
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def fmt_day(d):
    return f'{d.strftime("%a")} {d.day} {d.strftime("%b")}'


# ---------------------------------------------------------------- data

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
            print(f"warning: {p.name}: unknown categories shown at the end: {unknown}")
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
    """Fallback: label a deal as previously posted when the same item name
    appeared in an earlier brief (earliest date wins)."""
    first_seen = {}
    for b in reversed(briefs):  # oldest first
        for d in all_deals(b):
            key = norm(d.get("item"))
            if key and not d.get("previously_posted") and key in first_seen and first_seen[key] != b["display_date"]:
                d["previously_posted"] = first_seen[key]
            first_seen.setdefault(key, b["display_date"])


def ordered_categories(b):
    by_name = {c.get("name"): c for c in b.get("categories", [])}
    out = []
    for name, label, icon in CATEGORIES + [(n, n, "🛒") for n in by_name if n not in CAT_NAMES]:
        c = by_name.get(name, {})
        out.append({"name": name, "label": label, "icon": icon,
                    "deals": c.get("deals", [])[:MAX_PER_CATEGORY],
                    "advice": c.get("advice", ""), "notes": c.get("notes", []),
                    "notes_title": c.get("notes_title", "")})
    return out


# ---------------------------------------------------------------- components

def links_html(links, primary_label=None):
    links = [l for l in links or [] if l.get("url")]
    if not links:
        return ""
    first, rest = links[0], links[1:]
    label = primary_label or first.get("label") or "View deal"
    out = [f'<a class="btn" href="{e(first["url"])}" rel="noopener" target="_blank">{e(label)}<span aria-hidden="true">↗</span></a>']
    out += [f'<a class="btn ghost" href="{e(l["url"])}" rel="noopener" target="_blank">{e(l.get("label"))}<span aria-hidden="true">↗</span></a>'
            for l in rest]
    return f'<div class="actions">{"".join(out)}</div>'


def badges(d):
    out = []
    v = (d.get("verified") or "").strip().lower()
    if v == "verified":
        out.append('<span class="pill ok" title="At least 15% below its 90-day price, or at its lowest on record">✓ Verified deal</span>')
    elif v == "unverified":
        out.append('<span class="pill warn" title="No price history found; compared with other retailers only">Unverified</span>')
    s = (d.get("status") or "").strip()
    low = s.lower()
    if "drop" in low:
        out.append(f'<span class="pill hot">↓ {e(s[0].upper() + s[1:])}</span>')
    elif low == "new" and not d.get("previously_posted"):
        out.append('<span class="pill new">New today</span>')
    if d.get("previously_posted"):
        out.append(f'<span class="pill muted">Listed since {e(d["previously_posted"])}</span>')
    if d.get("stretch"):
        out.append('<span class="pill violet">Stretch pick</span>')
    return f'<div class="pills">{"".join(out)}</div>' if out else ""




def deal_card(d, cat=None, rank=None):
    cat = cat or d.get("category") or ""
    saving = pct_saving(d)
    price = money(d.get("price"))
    v = (d.get("verified") or "").strip().lower()
    text = norm(" ".join(str(d.get(k) or "") for k in ("item", "retailer", "why")) + " " + cat)

    usual = f'<s class="was">{e(d["usual"])}</s>' if d.get("usual") else ""
    save = f'<span class="save">{e(d["saving"])}</span>' if d.get("saving") else ""
    facts = []
    if d.get("retailer"):
        facts.append(f'<span>{e(d["retailer"])}</span>')
    if d.get("ends"):
        facts.append(f'<span>Ends {e(d["ends"])}</span>')
    if d.get("reviews"):
        facts.append(f'<span>★ {e(d["reviews"])}</span>')

    detail = []
    for label, key in (("Lowest on record", "lowest"), ("Price history", "price_source"),
                       ("Delivery", "delivery"), ("Reviews", "reviews")):
        if d.get(key):
            detail.append(f"<dt>{label}</dt><dd>{e(d[key])}</dd>")
    details = (f'<details class="more"><summary>Price check &amp; delivery</summary><dl>{"".join(detail)}</dl></details>'
               if detail else "")
    retailer = d.get("retailer")
    rank_html = f'<span class="rank" aria-label="Rank {rank}">{rank}</span>' if rank else ""
    eyebrow = (f'<div class="eyebrow">{rank_html}{e(cat)}</div>' if rank else "")

    return f"""<article class="card deal{' is-top' if rank else ''}" data-verified="{e(v)}" data-saving="{saving or 0}" data-price="{price or 0}" data-text="{e(text)}">
  <div class="content">
    {eyebrow}<h3>{e(d.get('item'))}</h3>
    <div class="priceline"><span class="price">{e(d.get('price'))}</span>{usual}{save}</div>
    {badges(d)}
    {f'<div class="facts">{"".join(facts)}</div>' if facts else ''}
    {f'<p class="why">{e(d.get("why"))}</p>' if d.get('why') else ''}
    {details}
    {links_html(d.get('links'), f"View at {retailer}" if retailer else None)}
  </div>
</article>"""


def top_section(b):
    deals = b.get("top", [])[:MAX_TOP]
    head = f'<div class="sec-head"><h2>Today\'s top {len(deals) or MAX_TOP}</h2><p>The best verified deals across every category.</p></div>'
    if not deals:
        return f'<section id="top" class="sec">{head}<p class="empty">Nothing met the bar today. Check the categories below for prices to watch.</p></section>'
    cards = "".join(deal_card(d, rank=i + 1) for i, d in enumerate(deals))
    return f'<section id="top" class="sec">{head}<div class="grid top-grid">{cards}</div></section>'


def sale_card(s, today):
    starts, ends = parse_date(s.get("starts")), parse_date(s.get("ends"))
    if starts and starts > today:
        n = (starts - today).days
        chip, cls, when = ("Starts tomorrow" if n == 1 else f"Starts in {n} days"), "soon", fmt_day(starts)
    elif ends:
        n = (ends - today).days
        chip = "Ends today" if n <= 0 else "Ends tomorrow" if n == 1 else f"{n} days left"
        cls, when = ("urgent" if n <= 2 else "live"), f"Until {fmt_day(ends)}"
    else:
        chip, cls, when = "Live now", "live", ""
    rumour = '' if s.get("confirmed", True) else '<span class="pill warn">Unconfirmed</span>'
    title = s.get("title") or s.get("text") or ""
    text = s.get("text") if s.get("title") else ""
    links = "".join(f'<a href="{e(l["url"])}" rel="noopener" target="_blank">{e(l.get("label"))} ↗</a>'
                    for l in s.get("links") or [] if l.get("url"))
    return f"""<li class="sale card">
  <div class="sale-top"><span class="status {cls}">{e(chip)}</span>{rumour}</div>
  <h3>{e(title)}</h3>
  {f'<div class="when">{e(when)}</div>' if when else ''}
  {f'<p>{e(text)}</p>' if text else ''}
  {f'<div class="sale-links">{links}</div>' if links else ''}
</li>"""


def sales_section(b):
    sales = b.get("sales") or []
    if not sales:
        return ""
    today = parse_date(b["date"]) or date.today()
    return (f'<section id="sales" class="sec"><div class="sec-head"><h2>What\'s on</h2>'
            f'<p>Sales live now or starting in the next 7 days.</p></div>'
            f'<ul class="rail">{"".join(sale_card(s, today) for s in sales)}</ul></section>')


def stores_section(b):
    stores = (b.get("stores") or [])[:5]
    if not stores:
        return ""
    rows = []
    for i, s in enumerate(stores):
        link = next((l for l in s.get("links") or [] if l.get("url")), None)
        go = (f'<a class="btn ghost sm" href="{e(link["url"])}" rel="noopener" target="_blank">{e(link.get("label") or "Shop")} ↗</a>'
              if link else "")
        why = f'<p>{e(s["why"])}</p>' if s.get("why") else ""
        rows.append(f'<li><span class="srank">{i + 1}</span><div class="sinfo"><b>{e(s.get("name"))}</b>'
                    f'{why}</div>{go}</li>')
    return (f'<section id="stores" class="sec"><div class="sec-head"><h2>Best stores right now</h2>'
            f'<p>Retailers with the broadest genuine discounts today.</p></div>'
            f'<ol class="stores card">{"".join(rows)}</ol></section>')


def category_sections(b):
    cats = ordered_categories(b)
    full = [c for c in cats if c["deals"]]
    empty = [c for c in cats if not c["deals"]]
    out = []
    for c in full:
        sid = "c-" + slug(c["name"])
        advice = (f'<p class="advice"><b>Buy now or wait?</b> {e(c["advice"])}</p>' if c["advice"] else "")
        notes = ""
        if c["notes"]:
            t = f'<b>{e(c["notes_title"])}</b>' if c["notes_title"] else ""
            notes = f'<div class="cat-notes">{t}<ul>{"".join(f"<li>{e(n)}</li>" for n in c["notes"])}</ul></div>'
        cards = "".join(deal_card(d, cat=c["name"]) for d in c["deals"])
        out.append(f'<section id="{sid}" class="cat sec-sub" data-cat="{e(c["name"])}">'
                   f'<div class="cat-head"><h3>{e(c["name"])}</h3>'
                   f'<span class="count">{len(c["deals"])}</span></div>{advice}'
                   f'<div class="grid">{cards}</div>{notes}</section>')
    nothing = ""
    if empty:
        items = []
        for c in empty:
            extra = ""
            if c["advice"] or c["notes"]:
                bits = ([e(c["advice"])] if c["advice"] else []) + [e(n) for n in c["notes"]]
                extra = f'<span class="nd-note">{" · ".join(bits)}</span>'
            items.append(f'<li><b>{e(c["name"])}</b>{extra}</li>')
        nothing = (f'<details class="nothing card"><summary>Nothing worth buying today in {len(empty)} '
                   f'categor{"y" if len(empty) == 1 else "ies"}</summary><ul>{"".join(items)}</ul></details>')
    toolbar = """<div class="toolbar" role="search">
  <label class="search"><input type="search" id="q" placeholder="Search deals, brands, stores" aria-label="Search deals"></label>
  <label class="toggle"><input type="checkbox" id="verified-only"> Verified only</label>
  <label class="sort">Sort <select id="sort" aria-label="Sort deals"><option value="best">Best match</option><option value="saving">Biggest saving</option><option value="price">Lowest price</option></select></label>
</div>"""
    return (f'<section id="categories" class="sec"><div class="sec-head"><h2>All deals by category</h2>'
            f'<p>Up to three of the best deals in each category.</p></div>{toolbar}'
            f'<div id="cat-list">{"".join(out)}</div>'
            f'<p id="no-results" class="empty" hidden>No deals match those filters.</p>{nothing}</section>')


def avoid_section(b):
    avoid = b.get("avoid") or []
    if not avoid:
        return ""
    items = []
    for a in avoid:
        if isinstance(a, dict):
            r = f' <span class="muted">@ {e(a["retailer"])}</span>' if a.get("retailer") else ""
            items.append(f'<li><b>{e(a.get("item"))}</b>{r}<p>{e(a.get("why"))}</p></li>')
        else:
            items.append(f"<li>{e(a)}</li>")
    return (f'<section id="avoid" class="sec"><div class="sec-head"><h2>Not as good as they look</h2>'
            f'<p>Advertised discounts that don\'t stand up to the price history.</p></div>'
            f'<ul class="avoid card">{"".join(items)}</ul></section>')


def stats(b):
    cats = ordered_categories(b)
    n_deals = len({norm(d.get("item")) for d in all_deals(b)})
    n_cats = sum(1 for c in cats if c["deals"])
    n_ver = len({norm(d.get("item")) for d in all_deals(b) if (d.get("verified") or "").lower() == "verified"})
    n_sales = len(b.get("sales") or [])
    out = [f"<li><b>{n_deals}</b> deals</li>", f"<li><b>{n_cats}</b> of {len(cats)} categories</li>"]
    if n_ver:
        out.append(f"<li><b>{n_ver}</b> verified</li>")
    if n_sales:
        out.append(f"<li><b>{n_sales}</b> sales on</li>")
    return f'<ul class="stats">{"".join(out)}</ul>'


def nav_html(b):
    links = ['<a href="#top">Top deals</a>']
    if b.get("sales"):
        links.append('<a href="#sales">What\'s on</a>')
    if b.get("stores"):
        links.append('<a href="#stores">Stores</a>')
    for c in ordered_categories(b):
        if c["deals"]:
            links.append(f'<a href="#c-{slug(c["name"])}">{e(c["label"])} <span>{len(c["deals"])}</span></a>')
    if b.get("avoid"):
        links.append('<a href="#avoid">Avoid</a>')
    return f'<nav class="jump" aria-label="Sections"><div class="jump-inner">{"".join(links)}</div></nav>'


def brief_html(b, daynav):
    notes = "".join(f'<p class="heads-up"><b>{e(n.get("label"))}:</b> {e(n.get("text"))}</p>'
                    for n in b.get("notes", []))
    hero = f"""<section class="hero">
  <div class="hero-inner">
    <div class="dateline"><span class="live-dot" aria-hidden="true"></span>Updated {e(b["display_date"])}{daynav}</div>
    <p class="headline">{e(b["summary"])}</p>
    {stats(b)}
  </div>
</section>"""
    body = [hero, nav_html(b), '<main class="wrap">', notes, top_section(b), sales_section(b),
            stores_section(b), category_sections(b), avoid_section(b), "</main>"]
    return "\n".join(x for x in body if x)


# ---------------------------------------------------------------- page shell

CSS = """
:root{
  --bg:#f6f6f4;--surface:#fff;--surface-2:#f0efec;--ink:#18181b;--ink-2:#3f3f46;--muted:#71717a;--line:#e4e4e0;
  --accent:#ea580c;--accent-ink:#fff;--accent-soft:#fff1e7;
  --ok:#15803d;--ok-soft:#e8f6ec;--warn:#a16207;--warn-soft:#fdf5d9;--violet:#6d28d9;--violet-soft:#f1ebff;--blue:#1d4ed8;--blue-soft:#e9effe;
  --hero:#0c0c0e;--hero-ink:#fafafa;--hero-muted:#a1a1aa;
  --r:16px;--r-sm:10px;--shadow:0 1px 2px rgb(0 0 0/.04),0 4px 16px rgb(0 0 0/.04);
  color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{
  --bg:#0f0f11;--surface:#18181b;--surface-2:#202024;--ink:#f4f4f5;--ink-2:#d4d4d8;--muted:#a1a1aa;--line:#2a2a2f;
  --accent:#fb923c;--accent-ink:#1a0d03;--accent-soft:#2b1a0e;
  --ok:#4ade80;--ok-soft:#10261a;--warn:#facc15;--warn-soft:#2a2410;--violet:#a78bfa;--violet-soft:#211a36;--blue:#93b4ff;--blue-soft:#172040;
  --hero:#000;--shadow:none}}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:72px;-webkit-text-size-adjust:100%}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important;animation:none!important}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-feature-settings:"cv11","ss01";-webkit-font-smoothing:antialiased}
a{color:inherit}
h1,h2,h3{letter-spacing:-.02em;line-height:1.2}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px 64px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}

/* masthead + hero */
.masthead{background:var(--hero);color:var(--hero-ink)}
.masthead .bar{max-width:1120px;margin:0 auto;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;font-weight:800;font-size:17px;letter-spacing:-.02em}
.logo{width:32px;height:32px;border-radius:9px;display:grid;place-items:center;background:linear-gradient(135deg,#f97316,#e11d48);color:#fff;font-size:16px;font-weight:900}
.masthead .archive-link{color:var(--hero-muted);font-size:14px;text-decoration:none}
.masthead .archive-link:hover{color:var(--hero-ink)}
.hero{background:var(--hero);color:var(--hero-ink);padding:8px 0 40px}
.hero-inner{max-width:1120px;margin:0 auto;padding:0 20px}
.dateline{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;color:var(--hero-muted);font-size:14px;font-weight:500}
.dateline a{color:var(--hero-muted);text-decoration:none;border-bottom:1px solid #3f3f46}
.dateline a:hover{color:var(--hero-ink)}
.live-dot{width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 4px rgb(34 197 94/.2)}
.headline{font-size:clamp(22px,3.2vw,32px);font-weight:700;letter-spacing:-.025em;line-height:1.25;margin:12px 0 20px;max-width:30ch;text-wrap:balance}
.stats{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.stats li{background:#1c1c20;border:1px solid #2a2a30;border-radius:999px;padding:6px 14px;font-size:14px;color:var(--hero-muted)}
.stats b{color:var(--hero-ink);font-weight:700}
.tagline{color:var(--hero-muted);font-size:14px;margin:18px 0 0;max-width:60ch}

/* jump nav */
.jump{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 85%,transparent);backdrop-filter:saturate(1.6) blur(12px);-webkit-backdrop-filter:saturate(1.6) blur(12px);border-bottom:1px solid var(--line)}
.jump-inner{max-width:1120px;margin:0 auto;padding:10px 20px;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;mask-image:linear-gradient(90deg,#000 92%,transparent)}
.jump-inner::-webkit-scrollbar{display:none}
.jump a{flex:none;text-decoration:none;font-size:14px;font-weight:600;color:var(--ink-2);padding:7px 12px;border-radius:999px;border:1px solid transparent;white-space:nowrap}
.jump a span{font-size:12px;color:var(--muted);margin-left:2px}
.jump a:hover{background:var(--surface-2)}
.jump a.active{background:var(--ink);color:var(--bg)}
.jump a.active span{color:inherit;opacity:.7}

/* sections */
.sec{margin-top:48px}
.sec-head{margin-bottom:16px}
.sec-head h2{font-size:24px;margin:0}
.sec-head p{margin:4px 0 0;color:var(--muted);font-size:15px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow)}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr))}
.top-grid{grid-template-columns:repeat(auto-fill,minmax(min(100%,320px),1fr))}

.empty{color:var(--muted);background:var(--surface);border:1px dashed var(--line);border-radius:var(--r);padding:18px;margin:0}
.heads-up{margin:24px 0 0;background:var(--blue-soft);border-radius:var(--r-sm);padding:12px 16px}

/* deal card */
.deal{display:flex;flex-direction:column;overflow:hidden;transition:transform .15s ease,box-shadow .15s ease}
.deal:hover{transform:translateY(-2px);box-shadow:0 2px 4px rgb(0 0 0/.04),0 12px 32px rgb(0 0 0/.08)}
.rank{width:24px;height:24px;border-radius:50%;display:inline-grid;place-items:center;background:var(--accent);color:var(--accent-ink);font-weight:800;font-size:13px;letter-spacing:0}

.content{padding:16px 18px 18px;display:flex;flex-direction:column;gap:10px;flex:1}
.eyebrow{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--accent)}
.eyebrow+h3{margin-top:-2px}
.deal h3{margin:0;font-size:17px;font-weight:700;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.priceline{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px}
.price{font-size:28px;font-weight:800;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.was{color:var(--muted);font-size:15px}
.save{font-size:13px;font-weight:700;color:var(--ok);background:var(--ok-soft);padding:2px 8px;border-radius:6px}
.pills{display:flex;flex-wrap:wrap;gap:6px}
.pill{font-size:12px;font-weight:600;padding:3px 9px;border-radius:999px;background:var(--surface-2);color:var(--ink-2);white-space:nowrap}
.pill.ok{background:var(--ok-soft);color:var(--ok)}
.pill.warn{background:var(--warn-soft);color:var(--warn)}
.pill.hot{background:var(--accent-soft);color:var(--accent)}
.pill.new{background:var(--blue-soft);color:var(--blue)}
.pill.violet{background:var(--violet-soft);color:var(--violet)}
.pill.muted{color:var(--muted)}
.facts{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:14px;color:var(--muted)}
.why{margin:0;font-size:15px;color:var(--ink-2)}
.more{font-size:14px;border-top:1px solid var(--line);padding-top:8px}
.more summary{cursor:pointer;font-weight:600;color:var(--ink-2);list-style:none;display:flex;align-items:center;gap:6px}
.more summary::-webkit-details-marker{display:none}
.more summary::after{content:"";width:7px;height:7px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(45deg) translateY(-2px);margin-left:2px;transition:transform .15s}
.more[open] summary::after{transform:rotate(-135deg) translateY(-1px)}
.more dl{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin:8px 0 0}
.more dt{color:var(--muted)}
.more dd{margin:0}
.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:auto;padding-top:4px}
.btn{display:inline-flex;align-items:center;gap:6px;text-decoration:none;font-weight:700;font-size:14px;padding:10px 16px;border-radius:var(--r-sm);background:var(--ink);color:var(--bg);border:1px solid var(--ink)}
.btn:hover{opacity:.88}
.is-top .btn:not(.ghost){background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.btn.ghost{background:transparent;color:var(--ink);border-color:var(--line)}
.btn.ghost:hover{background:var(--surface-2);opacity:1}
.btn.sm{padding:6px 12px;font-size:13px}

/* sales rail */
.rail{list-style:none;margin:0 -20px;padding:4px 20px 12px;display:grid;grid-auto-flow:column;grid-auto-columns:minmax(240px,280px);gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:thin}
.sale{padding:16px;scroll-snap-align:start;display:flex;flex-direction:column;gap:6px}
.sale-top{display:flex;gap:6px;flex-wrap:wrap}
.sale h3{margin:4px 0 0;font-size:16px}
.sale .when{font-size:13px;color:var(--muted);font-weight:600}
.sale p{margin:0;font-size:14px;color:var(--ink-2)}
.sale-links{margin-top:auto;padding-top:4px;display:flex;gap:10px;font-size:14px;font-weight:600}
.sale-links a{color:var(--accent);text-decoration:none}
.status{font-size:12px;font-weight:700;padding:3px 9px;border-radius:999px}
.status.live{background:var(--ok-soft);color:var(--ok)}
.status.urgent{background:var(--accent);color:var(--accent-ink)}
.status.soon{background:var(--blue-soft);color:var(--blue)}
@media (min-width:1000px){.rail{margin:0;padding:4px 0 12px;grid-auto-flow:row;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));overflow:visible}}

/* stores */
.stores{list-style:none;margin:0;padding:4px 0}
.stores li{display:flex;align-items:center;gap:14px;padding:14px 18px}
.stores li+li{border-top:1px solid var(--line)}
.srank{flex:none;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--surface-2);font-weight:800;font-size:14px}
.stores li:first-child .srank{background:var(--accent);color:var(--accent-ink)}
.sinfo{flex:1;min-width:0}
.sinfo p{margin:2px 0 0;color:var(--muted);font-size:14px}

/* toolbar + categories */
.toolbar{position:sticky;top:57px;z-index:5;display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:12px 0;margin-bottom:8px;background:var(--bg)}
.search{flex:1 1 260px;display:flex;align-items:center;gap:8px;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);padding:0 12px}
.search input{flex:1;border:0;background:transparent;font:inherit;font-size:15px;padding:10px 0;color:var(--ink);outline:none;min-width:0}
.search:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.toggle,.sort{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);padding:9px 12px;cursor:pointer}
.toggle input{accent-color:var(--accent);width:16px;height:16px}
.sort select{font:inherit;border:0;background:transparent;color:var(--ink);font-weight:600;cursor:pointer}
.cat{margin-top:28px}
.cat-head{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.cat-head h3{margin:0;font-size:19px}
.count{font-size:12px;font-weight:700;background:var(--surface-2);color:var(--muted);border-radius:999px;padding:2px 8px}
.advice{margin:0 0 12px;font-size:14px;background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:var(--r-sm);padding:10px 14px}
.cat-notes{margin-top:12px;font-size:14px;color:var(--muted)}
.cat-notes ul{margin:4px 0 0;padding-left:18px}
.nothing{margin-top:28px;padding:0}
.nothing summary{cursor:pointer;padding:14px 18px;font-weight:600;color:var(--ink-2)}
.nothing ul{list-style:none;margin:0;padding:0 18px 14px;display:grid;gap:8px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.nothing li{font-size:14px}
.nd-note{display:block;color:var(--muted);font-size:13px;margin-left:24px}

/* avoid */
.avoid{list-style:none;margin:0;padding:4px 0}
.avoid li{padding:12px 18px}
.avoid li+li{border-top:1px solid var(--line)}
.avoid p{margin:2px 0 0;color:var(--muted);font-size:14px}
.muted{color:var(--muted)}

/* archive */
.archive-list{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.archive-list a{display:block;padding:14px 18px;text-decoration:none}
.archive-list b{display:block}
.archive-list span{color:var(--muted);font-size:14px}

footer{max-width:1120px;margin:0 auto;padding:24px 20px 40px;border-top:1px solid var(--line);font-size:13px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 24px;justify-content:space-between}

@media (max-width:560px){
  .wrap{padding:0 16px 48px}.jump-inner,.hero-inner,.masthead .bar{padding-left:16px;padding-right:16px}
  .sec{margin-top:36px}.sec-head h2{font-size:21px}
  .price{font-size:24px}
  .is-top       .btn{padding:9px 14px}
  .toolbar{top:53px}.sort{flex:1}.toggle{flex:1}
  .rail{margin:0 -16px;padding:4px 16px 12px}
  .stores li{flex-wrap:wrap}.stores .btn{margin-left:42px}
}
.nojs .toolbar{display:none}
"""

JS = r"""
document.documentElement.classList.remove('nojs');
(function(){
  // Highlight the section in view in the jump nav
  var links=[].slice.call(document.querySelectorAll('.jump a'));
  var map={};links.forEach(function(a){var t=document.querySelector(a.getAttribute('href'));if(t)map[t.id]=a;});
  if('IntersectionObserver' in window){
    var current=null;
    var io=new IntersectionObserver(function(entries){
      entries.forEach(function(en){if(en.isIntersecting)current=en.target.id;});
      links.forEach(function(a){a.classList.toggle('active',map[current]===a);});
      var a=map[current];if(a){var bar=a.parentNode,l=a.offsetLeft-bar.offsetLeft;
        if(l<bar.scrollLeft||l+a.offsetWidth>bar.scrollLeft+bar.clientWidth)bar.scrollTo({left:l-20,behavior:'smooth'});}
    },{rootMargin:'-80px 0px -70% 0px'});
    Object.keys(map).forEach(function(id){io.observe(document.getElementById(id));});
  }
  // Search, verified-only filter and sort for the category list
  var q=document.getElementById('q'),vo=document.getElementById('verified-only'),so=document.getElementById('sort');
  if(!q)return;
  var cats=[].slice.call(document.querySelectorAll('#cat-list .cat'));
  cats.forEach(function(c){[].slice.call(c.querySelectorAll('.deal')).forEach(function(d,i){d.dataset.i=i;});});
  try{vo.checked=localStorage.getItem('tbf-verified')==='1';so.value=localStorage.getItem('tbf-sort')||'best';}catch(e){}
  function apply(){
    var term=q.value.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim(),any=false;
    try{localStorage.setItem('tbf-verified',vo.checked?'1':'0');localStorage.setItem('tbf-sort',so.value);}catch(e){}
    cats.forEach(function(c){
      var grid=c.querySelector('.grid'),deals=[].slice.call(grid.children),shown=0;
      deals.sort(function(a,b){
        if(so.value==='saving')return(+b.dataset.saving)-(+a.dataset.saving);
        if(so.value==='price')return(+a.dataset.price||1e9)-(+b.dataset.price||1e9);
        return a.dataset.i-b.dataset.i;}).forEach(function(d){grid.appendChild(d);});
      deals.forEach(function(d){
        var ok=(!term||d.dataset.text.indexOf(term)>-1)&&(!vo.checked||d.dataset.verified==='verified');
        d.hidden=!ok;if(ok)shown++;});
      c.hidden=!shown;c.querySelector('.count').textContent=shown;if(shown)any=true;
    });
    document.getElementById('no-results').hidden=any;
  }
  [q,vo,so].forEach(function(el){el.addEventListener('input',apply);el.addEventListener('change',apply);});
  apply();
})();
"""


def page(title, body, rel=""):
    return f"""<!doctype html>
<html lang="en-AU" class="nojs"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(TAGLINE)}">
<meta name="theme-color" content="#0c0c0e">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔥</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap">
<style>{CSS}</style>
</head><body>
<header class="masthead"><div class="bar">
  <a class="brand" href="{rel}index.html"><span class="logo" aria-hidden="true">T</span>{SITE}</a>
  <a class="archive-link" href="{rel}archive/index.html">Past days</a>
</div></header>
{body}
<footer><span>{e(TAGLINE)}</span><span>Prices and stock change quickly: check the retailer before buying. Not affiliated with any retailer; no affiliate links.</span></footer>
<script>{JS}</script></body></html>
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
        nav.append('<a href="../index.html">Today</a>')
        body = brief_html(b, "".join(nav))
        (ARCHIVE / f"{b['date']}.html").write_text(
            page(f"{SITE} – {b['display_date']}", body, "../"), encoding="utf-8")

    items = "".join(f'<li class="card"><a href="{b["date"]}.html"><b>{e(b["display_date"])}</b>'
                    f'<span>{e(b["summary"])}</span></a></li>' for b in briefs)
    (ARCHIVE / "index.html").write_text(page(
        f"{SITE} – Past days",
        f'<main class="wrap"><section class="sec"><div class="sec-head"><h2>Past days</h2>'
        f'<p>The last {KEEP_DAYS} days of deals.</p></div><ul class="archive-list">{items}</ul></section></main>',
        "../"), encoding="utf-8")

    prev = f'<a href="archive/{briefs[1]["date"]}.html">← {e(briefs[1]["display_date"])}</a>' if len(briefs) > 1 else ""
    (ROOT / "index.html").write_text(page(f"{SITE} – Today's best deals", brief_html(latest, prev)),
                                     encoding="utf-8")
    (ROOT / "feed.json").write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built {len(briefs)} brief(s); latest {latest['date']}")


if __name__ == "__main__":
    main()
