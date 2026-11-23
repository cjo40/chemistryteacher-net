#!/usr/bin/env python3
"""Build chemistryteacher.net into the public/ folder.

How it works (plain English):
  * Every file in activities/ becomes a page. activities/gas-laws.html -> chemistryteacher.net/gas-laws
  * site.json holds the search-friendly title, description, unit and "About" text for each activity.
    If an activity is not in site.json yet, it still goes on the site using its own <title>.
  * The script adds search-engine tags and a small "Home / About this activity" button to each activity,
    then makes the home page, sitemap.xml, robots.txt, 404 page and redirects.

Only the Python standard library is used, so Cloudflare Pages can run it with: python3 build.py
"""
import datetime
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACT_DIR = ROOT / "activities"
ASSETS = ROOT / "assets"
OUT = ROOT / "public"
TODAY = datetime.date.today().isoformat()

FLASK_SVG = ('<svg viewBox="0 0 32 32" aria-hidden="true" width="{s}" height="{s}"><path d="M12 3h8v2h-1v7.2l7.6 12.4A3.5 3.5 0 0 1 23.6 30H8.4a3.5 3.5 0 0 1-3-5.4L13 12.2V5h-1z" fill="#0f766e"/>'
             '<path d="M9.2 22h13.6l2 3.3a1.6 1.6 0 0 1-1.4 2.4H8.6a1.6 1.6 0 0 1-1.4-2.4z" fill="#5eead4"/><circle cx="14" cy="24.5" r="1.1" fill="#0f766e"/><circle cx="18.5" cy="23.6" r=".8" fill="#0f766e"/></svg>')


def fail(msg):
    print("BUILD ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def esc(s):
    return html.escape(str(s), quote=True)


def last_changed(path):
    """Date the file last changed in git (falls back to today)."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(path)], cwd=ROOT,
                             capture_output=True, text=True, timeout=20).stdout.strip()
        return out or TODAY
    except Exception:
        return TODAY


def load_config():
    try:
        return json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"site.json has a typo near line {e.lineno}, column {e.colno}: {e.msg}")


def own_title(text, slug):
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    return html.unescape(m.group(1)).strip() if m else slug.replace("-", " ").title()


def collect(cfg):
    if not ACT_DIR.is_dir():
        fail("the activities folder is missing")
    acts = []
    for f in sorted(ACT_DIR.glob("*.html")):
        slug = f.stem
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
            fail(f"'{f.name}' needs a lowercase-hyphen name, like gas-laws.html")
        text = f.read_text(encoding="utf-8", errors="replace")
        meta = dict(cfg["activities"].get(slug, {}))
        name = meta.get("name") or own_title(text, slug)
        meta.setdefault("name", name)
        meta.setdefault("title", f"{name}: Free Interactive Chemistry Activity")
        meta.setdefault("description", f"{name}: a free interactive chemistry activity for high school students. Runs in the browser, no login.")
        meta.setdefault("unit", "More Activities")
        meta.setdefault("order", 99)
        meta.setdefault("card", meta["description"])
        meta.setdefault("topics", [])
        meta.setdefault("about", meta["description"])
        meta.setdefault("how", [])
        meta.setdefault("classroom", "")
        meta["slug"] = slug
        meta["url"] = f"{cfg['base_url']}/{slug}"
        meta["lastmod"] = last_changed(f)
        meta["src"] = f
        meta["text"] = text
        meta["has_preview"] = (ASSETS / "previews" / f"{slug}.jpg").exists()
        acts.append(meta)
    if not acts:
        fail("no activities found in the activities folder")
    units = cfg["units"]
    acts.sort(key=lambda a: (units.index(a["unit"]) if a["unit"] in units else len(units), a["order"], a["name"]))
    return acts


def preview_url(cfg, a):
    return f"{cfg['base_url']}/assets/previews/{a['slug']}.jpg" if a and a["has_preview"] else f"{cfg['base_url']}/assets/og-default.jpg"


def head_tags(cfg, a, related):
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "LearningResource",
                "name": a["name"],
                "headline": a["title"],
                "description": a["description"],
                "url": a["url"],
                "image": preview_url(cfg, a),
                "inLanguage": "en",
                "isAccessibleForFree": True,
                "educationalLevel": "High school",
                "learningResourceType": "Interactive simulation",
                "interactivityType": "active",
                "audience": {"@type": "EducationalAudience", "educationalRole": ["student", "teacher"]},
                "about": [{"@type": "Thing", "name": t} for t in (a["topics"] or [a["name"]])],
                "teaches": a["topics"] or [a["name"]],
                "dateModified": a["lastmod"],
                "publisher": {"@type": "Organization", "name": cfg["site_name"], "url": cfg["base_url"] + "/"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": cfg["site_name"], "item": cfg["base_url"] + "/"},
                    {"@type": "ListItem", "position": 2, "name": a["name"], "item": a["url"]},
                ],
            },
        ],
    }
    img = preview_url(cfg, a)
    return f"""
<!-- chemistryteacher.net: search and sharing tags (added by build.py) -->
<meta name="description" content="{esc(a['description'])}">
<link rel="canonical" href="{esc(a['url'])}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#0f766e">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(cfg['site_name'])}">
<meta property="og:title" content="{esc(a['title'])}">
<meta property="og:description" content="{esc(a['description'])}">
<meta property="og:url" content="{esc(a['url'])}">
<meta property="og:image" content="{esc(img)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(a['title'])}">
<meta name="twitter:description" content="{esc(a['description'])}">
<meta name="twitter:image" content="{esc(img)}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>
#ct-bar{{position:fixed;z-index:2147483000;font:600 14px/1.2 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#0f172a}}
#ct-bar.pos-bl{{left:8px;bottom:8px}} #ct-bar.pos-br{{right:8px;bottom:8px}} #ct-bar.pos-tl{{left:8px;top:8px}} #ct-bar.pos-tr{{right:8px;top:8px}} #ct-bar.pos-tc{{left:50%;top:8px;transform:translateX(-50%)}} #ct-bar.pos-th{{left:34%;top:8px}} #ct-bar.pos-bc{{left:50%;bottom:8px;transform:translateX(-50%)}}
#ct-fab{{all:unset;cursor:pointer;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.95);border:1px solid #b6c2cc;box-shadow:0 1px 6px rgba(0,0,0,.22);opacity:.9}}
#ct-fab:hover,#ct-fab[aria-expanded="true"]{{opacity:1;border-color:#0f766e}}
#ct-fab:focus-visible{{outline:2px solid #0f766e;outline-offset:2px}}
#ct-menu{{position:absolute;min-width:220px;background:#fff;border:1px solid #cbd5e1;border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.25);padding:6px;display:none}}
#ct-bar.pos-bl #ct-menu,#ct-bar.pos-br #ct-menu,#ct-bar.pos-bc #ct-menu{{bottom:42px}} #ct-bar.pos-tl #ct-menu,#ct-bar.pos-tr #ct-menu,#ct-bar.pos-tc #ct-menu,#ct-bar.pos-th #ct-menu{{top:42px}}
#ct-bar.pos-bl #ct-menu,#ct-bar.pos-tl #ct-menu,#ct-bar.pos-th #ct-menu{{left:0}} #ct-bar.pos-br #ct-menu,#ct-bar.pos-tr #ct-menu{{right:0}} #ct-bar.pos-tc #ct-menu,#ct-bar.pos-bc #ct-menu{{left:50%;transform:translateX(-50%)}}
#ct-bar.ct-open #ct-menu{{display:block}}
#ct-menu a,#ct-menu button{{all:unset;cursor:pointer;display:flex;align-items:center;gap:8px;width:100%;box-sizing:border-box;padding:9px 12px;border-radius:8px;color:#0f172a;white-space:nowrap}}
#ct-menu a:hover,#ct-menu button:hover{{background:#e6f4f1}}
#ct-menu a:focus-visible,#ct-menu button:focus-visible{{outline:2px solid #0f766e}}
#ct-panel{{position:fixed;inset:0;z-index:2147483001;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;padding:16px;visibility:hidden;opacity:0;transition:opacity .15s}}
#ct-panel.ct-open{{visibility:visible;opacity:1}}
#ct-panel .ct-card{{background:#fff;color:#0f172a;max-width:680px;width:100%;max-height:88vh;overflow:auto;border-radius:14px;padding:22px 26px;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;text-align:left;box-shadow:0 10px 40px rgba(0,0,0,.35);user-select:text;-webkit-user-select:text}}
#ct-panel h1{{font-size:22px;margin:0 0 6px;line-height:1.25}}
#ct-panel h2{{font-size:17px;margin:18px 0 6px}}
#ct-panel p{{margin:0 0 10px}}
#ct-panel ol,#ct-panel ul{{margin:0 0 10px;padding-left:22px}}
#ct-panel li{{margin:3px 0}}
#ct-panel a{{color:#0f766e;font-weight:600}}
#ct-panel .ct-top{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}}
#ct-panel .ct-close{{all:unset;cursor:pointer;font-size:22px;line-height:1;padding:4px 8px;border-radius:8px;color:#475569}}
#ct-panel .ct-close:hover{{background:#f1f5f9}}
#ct-panel .ct-foot{{font-size:13px;color:#64748b;border-top:1px solid #e2e8f0;margin-top:16px;padding-top:10px}}
@media print{{#ct-bar,#ct-panel{{display:none!important}}}}
</style>
<!-- /chemistryteacher.net -->
"""


def body_widget(cfg, a, related):
    how = "".join(f"<li>{esc(h)}</li>" for h in a["how"])
    rel = "".join(f'<li><a href="/{r["slug"]}">{esc(r["name"])}</a>: {esc(r["card"])}</li>' for r in related)
    topics = ", ".join(a["topics"])
    return f"""
<!-- chemistryteacher.net: home link and About panel (added by build.py) -->
<nav id="ct-bar" class="pos-{a.get('bar','bl')}" aria-label="ChemistryTeacher.net">
  <button type="button" id="ct-fab" aria-expanded="false" aria-controls="ct-menu" title="ChemistryTeacher.net: more activities and About">{FLASK_SVG.format(s=20)}<span style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">ChemistryTeacher.net menu</span></button>
  <div id="ct-menu">
    <a href="/">{FLASK_SVG.format(s=16)} All chemistry activities</a>
    <button type="button" id="ct-about-btn" aria-haspopup="dialog" aria-controls="ct-panel">&#9432; About this activity</button>
  </div>
</nav>
<section id="ct-panel" role="dialog" aria-modal="true" aria-labelledby="ct-h1" aria-hidden="true">
  <div class="ct-card">
    <div class="ct-top"><h1 id="ct-h1">{esc(a['name'])}</h1><button type="button" class="ct-close" id="ct-close" aria-label="Close">&#10005;</button></div>
    <p><strong>{esc(a['description'])}</strong></p>
    <h2>About this activity</h2>
    <p>{esc(a['about'])}</p>
    {f'<h2>How to use it</h2><ol>{how}</ol>' if how else ''}
    {f'<h2>In the classroom</h2><p>{esc(a["classroom"])}</p>' if a['classroom'] else ''}
    {f'<h2>Topics</h2><p>{esc(topics)}</p>' if topics else ''}
    {f'<h2>Related activities</h2><ul>{rel}</ul>' if rel else ''}
    <p><a href="/">See all free chemistry activities at {esc(cfg['site_name'])}</a></p>
    <p class="ct-foot">{esc(cfg['license'])} Works on Chromebooks, laptops, tablets and projectors. No login, no ads, no student data collected.</p>
  </div>
</section>
<script>
(function(){{
  var bar=document.getElementById('ct-bar'),p=document.getElementById('ct-panel');
  function open(){{p.classList.add('ct-open');p.setAttribute('aria-hidden','false');document.getElementById('ct-close').focus();}}
  function close(){{p.classList.remove('ct-open');p.setAttribute('aria-hidden','true');}}
  document.getElementById('ct-about-btn').addEventListener('click',open);
  document.getElementById('ct-close').addEventListener('click',close);
  p.addEventListener('click',function(e){{if(e.target===p)close();}});
  document.addEventListener('keydown',function(e){{if(e.key==='Escape'&&p.classList.contains('ct-open')){{e.stopPropagation();close();}}}},true);
  ['keydown','keyup','keypress','pointerdown','mousedown','touchstart'].forEach(function(t){{p.addEventListener(t,function(e){{e.stopPropagation();}});}});
  var fab=document.getElementById('ct-fab');
  function menu(o){{bar.classList.toggle('ct-open',o);fab.setAttribute('aria-expanded',o?'true':'false');}}
  fab.addEventListener('click',function(e){{e.stopPropagation();menu(!bar.classList.contains('ct-open'));}});
  document.addEventListener('click',function(e){{if(!bar.contains(e.target))menu(false);}});
  document.getElementById('ct-about-btn').addEventListener('click',function(){{menu(false);}});
  ['keydown','keyup','keypress','pointerdown','mousedown','touchstart'].forEach(function(t){{bar.addEventListener(t,function(e){{e.stopPropagation();}});}});
}})();
</script>
<!-- /chemistryteacher.net -->
"""


def self_host_fonts(text):
    """Swap Google Fonts links for copies hosted on this site (school filters often block Google Fonts)."""
    text = re.sub(r'<link[^>]+rel="preconnect"[^>]+fonts\.(googleapis|gstatic)\.com[^>]*>\s*', "", text)
    text = re.sub(r'<link[^>]+href="https://fonts\.googleapis\.com/css2\?family=Atkinson\+Hyperlegible[^"]*"[^>]*>',
                  '<link rel="stylesheet" href="/assets/fonts/atkinson-hyperlegible.css">', text)
    return text


def build_activity(cfg, a, acts):
    text = self_host_fonts(a["text"])
    same = [r for r in acts if r["unit"] == a["unit"] and r["slug"] != a["slug"]]
    others = [r for r in acts if r["unit"] != a["unit"]]
    related = (same + others)[:4]
    # New title, remove any old description/canonical so there is only one of each.
    if re.search(r"<title[^>]*>.*?</title>", text, re.S | re.I):
        text = re.sub(r"<title[^>]*>.*?</title>", f"<title>{esc(a['title'])}</title>", text, count=1, flags=re.S | re.I)
    else:
        text = re.sub(r"<head[^>]*>", lambda m: m.group(0) + f"\n<title>{esc(a['title'])}</title>", text, count=1, flags=re.I)
    text = re.sub(r'<meta\s+name="description"[^>]*>\s*', "", text, flags=re.I)
    text = re.sub(r'<link\s+rel="canonical"[^>]*>\s*', "", text, flags=re.I)
    if not re.search(r"</head>", text, re.I) or not re.search(r"</body>", text, re.I):
        fail(f"{a['src'].name} is missing </head> or </body>")
    text = re.sub(r"</head>", lambda m: head_tags(cfg, a, related) + m.group(0), text, count=1, flags=re.I)
    idx = [m.start() for m in re.finditer(r"</body>", text, re.I)][-1]
    text = text[:idx] + body_widget(cfg, a, related) + text[idx:]
    (OUT / f"{a['slug']}.html").write_text(text, encoding="utf-8")


PAGE_CSS = """
*{box-sizing:border-box}
:root{--ink:#0f172a;--ink2:#475569;--line:#e2e8f0;--bg:#f8fafc;--teal:#0f766e;--teal2:#14b8a6;--card:#fff}
html{-webkit-text-size-adjust:100%}
body{margin:0;font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--teal)}
.wrap{max-width:1160px;margin:0 auto;padding:0 20px}
header.site{background:#fff;border-bottom:1px solid var(--line)}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:64px}
.logo{display:flex;align-items:center;gap:10px;font-weight:800;font-size:20px;color:var(--ink);text-decoration:none;letter-spacing:-.2px}
.logo span b{color:var(--teal)}
nav.top a{margin-left:18px;color:var(--ink2);text-decoration:none;font-weight:600;font-size:15px}
nav.top a:hover{color:var(--teal)}
.hero{background:linear-gradient(135deg,#0f766e 0%,#115e59 55%,#134e4a 100%);color:#fff;padding:46px 0 40px}
.hero h1{font-size:clamp(28px,4.4vw,44px);line-height:1.12;margin:0 0 12px;letter-spacing:-.6px;max-width:820px}
.hero p{font-size:clamp(16px,2vw,19px);max-width:760px;margin:0;color:#ccfbf1}
.pills{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.pills span{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.25);padding:5px 12px;border-radius:999px;font-size:14px;font-weight:600}
.jump{display:flex;flex-wrap:wrap;gap:8px;margin:26px 0 6px}
.jump a{background:#fff;border:1px solid var(--line);padding:6px 12px;border-radius:999px;text-decoration:none;color:var(--ink);font-size:14px;font-weight:600}
.jump a:hover{border-color:var(--teal);color:var(--teal)}
section.unit{padding:18px 0 8px}
section.unit h2{font-size:24px;margin:18px 0 14px;letter-spacing:-.3px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;text-decoration:none;color:inherit;transition:transform .12s,box-shadow .12s,border-color .12s}
.card:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(15,23,42,.10);border-color:#99f6e4}
.card img{width:100%;height:auto;aspect-ratio:1200/630;object-fit:cover;object-position:top;display:block;background:#e2e8f0;border-bottom:1px solid var(--line)}
.card .ph{aspect-ratio:1200/630;display:flex;align-items:center;justify-content:center;background:#ecfdf5;border-bottom:1px solid var(--line)}
.card .body{padding:14px 16px 16px;display:flex;flex-direction:column;gap:6px;flex:1}
.card h3{margin:0;font-size:19px;line-height:1.25}
.card p{margin:0;color:var(--ink2);font-size:15px;flex:1}
.card .go{font-weight:700;color:var(--teal);font-size:15px;margin-top:4px}
.about{background:#fff;border-top:1px solid var(--line);margin-top:36px;padding:30px 0}
.about h2{margin:0 0 10px;font-size:22px}
.about .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px}
.about p,.about li{color:var(--ink2);font-size:16px}
.about ul{padding-left:20px;margin:0}
footer.site{padding:22px 0 30px;color:var(--ink2);font-size:14px;border-top:1px solid var(--line);background:#fff}
footer.site .wrap{display:flex;flex-wrap:wrap;justify-content:space-between;gap:10px}
.nf{padding:60px 0}
.nf h1{font-size:34px;margin:0 0 8px}
.nf ul{columns:2;padding-left:20px}
@media (max-width:640px){nav.top{display:none}.nf ul{columns:1}}
"""


def page_shell(cfg, title, description, canonical, body, extra_head="", robots="index,follow,max-image-preview:large"):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{f'<link rel="canonical" href="{esc(canonical)}">' if canonical else ''}
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#0f766e">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(cfg['site_name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical or cfg['base_url'] + '/')}">
<meta property="og:image" content="{cfg['base_url']}/assets/og-default.jpg">
<meta name="twitter:card" content="summary_large_image">
{extra_head}
<style>{PAGE_CSS}</style>
</head>
<body>
<header class="site"><div class="wrap">
  <a class="logo" href="/">{FLASK_SVG.format(s=34)}<span>Chemistry<b>Teacher</b>.net</span></a>
  <nav class="top"><a href="/#activities">Activities</a><a href="/#about">About</a></nav>
</div></header>
{body}
<footer class="site"><div class="wrap">
  <span>&copy; {datetime.date.today().year} {esc(cfg['site_name'])}. {esc(cfg['license'])}</span>
  <span>No login &middot; No ads &middot; No student data collected</span>
</div></footer>
</body>
</html>
"""


def card_html(a, eager=False):
    img = (f'<img src="/assets/previews/{a["slug"]}.jpg" alt="Screenshot of the {esc(a["name"])} activity" width="1200" height="630" loading="{"eager" if eager else "lazy"}" decoding="async">'
           if a["has_preview"] else f'<div class="ph">{FLASK_SVG.format(s=64)}</div>')
    return (f'<a class="card" href="/{a["slug"]}">{img}<div class="body"><h3>{esc(a["name"])}</h3>'
            f'<p>{esc(a["card"])}</p><span class="go">Open activity &rarr;</span></div></a>')


def unit_id(u):
    return re.sub(r"[^a-z0-9]+", "-", u.lower()).strip("-")


def build_home(cfg, acts):
    units = [u for u in cfg["units"] if any(a["unit"] == u for a in acts)]
    units += sorted({a["unit"] for a in acts} - set(units))
    jump = "".join(f'<a href="#{unit_id(u)}">{esc(u)}</a>' for u in units)
    secs, n = [], 0
    for u in units:
        cards = []
        for a in acts:
            if a["unit"] == u:
                cards.append(card_html(a, eager=n < 3))
                n += 1
        secs.append(f'<section class="unit" id="{unit_id(u)}"><h2>{esc(u)}</h2><div class="grid">{"".join(cards)}</div></section>')
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": cfg["site_name"], "url": cfg["base_url"] + "/", "description": cfg["home_description"], "inLanguage": "en"},
            {"@type": "ItemList", "name": "Free chemistry simulations", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": a["url"], "name": a["name"]} for i, a in enumerate(acts)]},
        ],
    }
    body = f"""
<main>
<div class="hero"><div class="wrap">
  <h1>Free Interactive Chemistry Simulations for High School</h1>
  <p>{esc(cfg['home_intro'])}</p>
  <div class="pills"><span>{len(acts)} free activities</span><span>No login</span><span>Chromebook ready</span><span>Projector friendly</span></div>
</div></div>
<div class="wrap" id="activities">
  <nav class="jump" aria-label="Jump to a unit">{jump}</nav>
  {''.join(secs)}
</div>
<section class="about" id="about"><div class="wrap cols">
  <div><h2>About ChemistryTeacher.net</h2><p>{esc(cfg['about_site'])}</p></div>
  <div><h2>For teachers</h2><ul>
    <li>Every activity is free and runs in a web browser. Nothing to install.</li>
    <li>No accounts, no ads and no student data collected.</li>
    <li>Link any activity in Google Classroom or your LMS: each one has its own short address, like chemistryteacher.net/gas-laws.</li>
    <li>Open the About button on any activity for how-to steps and classroom ideas.</li>
  </ul></div>
</div></section>
</main>"""
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
    (OUT / "index.html").write_text(page_shell(cfg, cfg["home_title"], cfg["home_description"], cfg["base_url"] + "/", body, extra), encoding="utf-8")


def build_404(cfg, acts):
    items = "".join(f'<li><a href="/{a["slug"]}">{esc(a["name"])}</a></li>' for a in acts)
    body = f'<main class="wrap nf"><h1>Page not found</h1><p>That page isn\'t here. Try one of these free activities:</p><ul>{items}</ul><p><a href="/">Go to the home page</a></p></main>'
    (OUT / "404.html").write_text(page_shell(cfg, "Page not found | " + cfg["site_name"], "Page not found.", "", body, robots="noindex"), encoding="utf-8")


def build_meta_files(cfg, acts):
    newest = max(a["lastmod"] for a in acts)
    urls = [f"  <url><loc>{cfg['base_url']}/</loc><lastmod>{newest}</lastmod></url>"]
    urls += [f"  <url><loc>{esc(a['url'])}</loc><lastmod>{a['lastmod']}</lastmod></url>" for a in acts]
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {cfg['base_url']}/sitemap.xml\n", encoding="utf-8")
    slugs = {a["slug"] for a in acts}
    lines = []
    for old, new in cfg.get("redirects", {}).items():
        if old.strip("/") not in slugs:
            lines.append(f"{old} {new} 301")
    lines.append("/index /  301")
    (OUT / "_redirects").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()\n\n"
        "/assets/*\n  Cache-Control: public, max-age=604800\n", encoding="utf-8")


def main():
    cfg = load_config()
    acts = collect(cfg)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    if ASSETS.is_dir():
        shutil.copytree(ASSETS, OUT / "assets")
    for name in ("favicon.svg", "favicon.ico", "apple-touch-icon.png"):
        if (ASSETS / name).exists():
            shutil.copy(ASSETS / name, OUT / name)
    for a in acts:
        build_activity(cfg, a, acts)
    build_home(cfg, acts)
    build_404(cfg, acts)
    build_meta_files(cfg, acts)
    missing = [a["slug"] for a in acts if a["slug"] not in cfg["activities"]]
    print(f"Built {len(acts)} activities into public/: " + ", ".join(a["slug"] for a in acts))
    if missing:
        print("Note: no site.json entry yet (using defaults) for: " + ", ".join(missing))


if __name__ == "__main__":
    main()
