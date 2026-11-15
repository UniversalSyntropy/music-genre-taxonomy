#!/usr/bin/env python3
"""Build the static site into _site/ (git-ignored).

Usage: python tools/build_site.py [--out DIR]
Copies site/, data/ and schema/. Writes one page per genre, the A to Z index,
sitemap.xml, robots.txt, 404.html and .nojekyll. Stdlib only. Output is
deterministic: same input, same bytes.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import unicodedata
from collections import defaultdict, deque
from html import escape
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://universalsyntropy.github.io/music-genre-taxonomy/"
REPO = "https://github.com/UniversalSyntropy/music-genre-taxonomy"
NOT_AFFILIATED = "Not affiliated with Discogs, MetaBrainz, MusicBrainz or the Wikimedia Foundation."
SITE_NAME = "Music Genre Taxonomy"
SRC_NAMES = {"discogs": "Discogs", "musicbrainz": "MusicBrainz", "wikidata": "Wikidata", "hand": "Hand-added"}

CSS = """\
:root{--bg:#f4f2ec;--panel:#e9e6de;--line:#d6d2c8;--text:#161616;--muted:#5f5c56;--ink:#b43a08;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#19191a;--panel:#222224;--line:#303033;--text:#ebeae6;--muted:#908d86;--ink:#ff5a1f;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
a{color:var(--ink)}
:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
header,main,footer{max-width:46rem;margin:0 auto;padding:0 16px}
header{padding-top:16px;padding-bottom:8px}
.site{font-weight:650;text-decoration:none;color:var(--text)}
nav.crumbs{color:var(--muted);font-size:14px;margin:8px 0 0}
nav.crumbs ol{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:2px 6px}
nav.crumbs li+li::before{content:"/";margin-right:6px;color:var(--muted)}
h1{font-size:2rem;line-height:1.2;margin:16px 0 4px;overflow-wrap:anywhere}
h2{font-size:1.15rem;margin:28px 0 6px}
.key{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:14px;color:var(--muted)}
ul.plain{margin:0;padding-left:20px}
ul.plain li{margin:4px 0}
ul.cols{columns:2 14rem;column-gap:24px;padding-left:20px;margin:0}
ul.cols li{break-inside:avoid;margin:3px 0}
.small{color:var(--muted);font-size:14px}
.pill{display:inline-block;border:1px solid var(--ink);color:var(--ink);border-radius:99px;padding:0 8px;font-size:13px;font-weight:650}
.btn{display:inline-block;margin-top:20px;padding:10px 16px;min-height:44px;border:1px solid var(--ink);border-radius:6px;text-decoration:none;font-weight:600}
.btn:hover{background:var(--panel)}
.az{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 0;padding:0;list-style:none}
.az a{display:inline-block;min-width:44px;min-height:44px;line-height:42px;text-align:center;border:1px solid var(--line);border-radius:6px;text-decoration:none}
footer{margin-top:40px;padding-top:16px;padding-bottom:32px;border-top:1px solid var(--line);color:var(--muted);font-size:14px}
footer p{margin:4px 0}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""

ROBOTS = "User-agent: *\nAllow: /\n\nSitemap: " + BASE + "sitemap.xml\n"


def fold(s: str) -> str:
    """ASCII-ish fold for sorting and the A to Z letter."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()


def url_key(key: str) -> str:
    return quote(key, safe="")


def page_url(key: str) -> str:
    return BASE + "genre/" + url_key(key) + ".html"


def jld(obj) -> str:
    """JSON for a script tag: no raw <, > or & can close the tag."""
    s = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def ext_links(n: dict) -> list:
    e = n["external"]
    out = []
    if e.get("wikidata_id"):
        out.append(("Wikipedia", "https://www.wikidata.org/wiki/Special:GoToLinkedPage/enwiki/" + e["wikidata_id"]))
        out.append(("Wikidata", "https://www.wikidata.org/wiki/" + e["wikidata_id"]))
    if e.get("musicbrainz_id"):
        out.append(("MusicBrainz", "https://musicbrainz.org/genre/" + e["musicbrainz_id"]))
    if e.get("discogs_name"):
        kind = "genre" if e.get("discogs_kind") == "genre" else "style"
        out.append(("Discogs", "https://www.discogs.com/" + kind + "/"
                    + quote(e["discogs_name"].lower(), safe="!'()*").replace("%20", "+")))
    out.append(("Beatport search", "https://www.beatport.com/search?q=" + quote(n["name"], safe="!'()*")))
    return out


def cut(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    s = s[: n - 1].rsplit(" ", 1)[0].rstrip(",;: ")
    return s + "…"


def head(title: str, desc: str, canon: str, extra: str = "", css: str = "genre.css") -> str:
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{escape(title)}</title>\n"
        f"<meta name=\"description\" content=\"{escape(desc, quote=True)}\">\n"
        f"<link rel=\"canonical\" href=\"{escape(canon, quote=True)}\">\n"
        "<meta name=\"theme-color\" content=\"#f4f2ec\" media=\"(prefers-color-scheme: light)\">\n"
        "<meta name=\"theme-color\" content=\"#19191a\" media=\"(prefers-color-scheme: dark)\">\n"
        f"<meta property=\"og:type\" content=\"website\">\n<meta property=\"og:site_name\" content=\"{SITE_NAME}\">\n"
        f"<meta property=\"og:title\" content=\"{escape(title, quote=True)}\">\n"
        f"<meta property=\"og:description\" content=\"{escape(desc, quote=True)}\">\n"
        f"<meta property=\"og:url\" content=\"{escape(canon, quote=True)}\">\n"
        f"<meta property=\"og:image\" content=\"{BASE}og.png\">\n"
        "<meta name=\"twitter:card\" content=\"summary_large_image\">\n"
        f"<meta name=\"twitter:title\" content=\"{escape(title, quote=True)}\">\n"
        f"<meta name=\"twitter:description\" content=\"{escape(desc, quote=True)}\">\n"
        f"<meta name=\"twitter:image\" content=\"{BASE}og.png\">\n"
        "<link rel=\"icon\" href=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
        "%3Crect width='32' height='32' rx='6' fill='%2319191a'/%3E%3Ccircle cx='9' cy='16' r='4' fill='%23ff5a1f'/%3E"
        "%3Ccircle cx='24' cy='9' r='3' fill='%23ebeae6'/%3E%3Ccircle cx='24' cy='23' r='3' fill='%23ebeae6'/%3E%3C/svg%3E\">\n"
        f"<link rel=\"stylesheet\" href=\"{css}\">\n{extra}</head>\n"
    )


def foot(rel_root: str) -> str:
    return (
        "<footer>\n"
        f"<p><a href=\"{rel_root}\">Tree viewer</a> · <a href=\"{rel_root}genre/\">All genres A to Z</a> · "
        f"<a href=\"{REPO}\">GitHub repository</a> · <a href=\"{rel_root}data/taxonomy.json\">Data file (JSON)</a></p>\n"
        "<p>Licence: <a href=\"https://creativecommons.org/licenses/by/4.0/\">CC BY 4.0</a>. "
        "Parent links come from Wikidata and Discogs, names from Discogs, MusicBrainz and Wikidata.</p>\n"
        f"<p>{NOT_AFFILIATED}</p>\n</footer>\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "_site"))
    out = Path(ap.parse_args().out).resolve()

    doc = json.loads((ROOT / "data" / "taxonomy.json").read_text(encoding="utf-8"))
    nodes = {n["key"]: n for n in doc["nodes"]}
    if len({k.lower() for k in nodes}) != len(nodes):
        sys.exit("error: two keys differ only by case; file names would collide")

    # The page and its JSON-LD must match the data.
    index_src = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    for needle in (f"{len(nodes):,} music genres", f'"version": "{doc["version"]}"'):
        if needle not in index_src:
            sys.exit(f"error: site/index.html is out of date with the data (missing: {needle})")

    parents = defaultdict(list)  # child -> [link]
    kids = defaultdict(list)  # parent -> [child key]
    for l in doc["links"]:
        parents[l["child"]].append(l)
        kids[l["parent"]].append(l["child"])
    aliases = defaultdict(list)
    for a in doc["aliases"]:
        seen = {nodes[a["node"]]["name"].casefold()} | {x.casefold() for x in aliases[a["node"]]}
        if a["name"].casefold() not in seen:  # skip the name itself and case-only variants
            aliases[a["node"]].append(a["name"])

    def porder(l):
        return (0 if l["source"] == "wikidata" else 1, l["parent"])

    for k in parents:
        parents[k].sort(key=porder)
    for k in kids:
        kids[k].sort(key=lambda c: (fold(nodes[c]["name"]), c))

    def crumb_path(key):
        """Shortest parent chain from a root down to key (BFS up, wikidata parents first)."""
        prev = {key: None}
        dq = deque([key])
        while dq:
            cur = dq.popleft()
            if not parents.get(cur):
                path = []
                while cur is not None:
                    path.append(cur)
                    cur = prev[cur]
                return path  # root ... key
            for l in parents[cur]:
                if l["parent"] not in prev:
                    prev[l["parent"]] = cur
                    dq.append(l["parent"])
        return [key]  # cycle only

    if out.exists():
        shutil.rmtree(out)
    (out / "genre").mkdir(parents=True)

    def copytree(src: Path, dst: Path):
        for p in sorted(src.rglob("*")):
            if p.is_file() and p.name != ".DS_Store":
                t = dst / p.relative_to(src)
                t.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, t)

    copytree(ROOT / "site", out)
    copytree(ROOT / "data", out / "data")
    copytree(ROOT / "schema", out / "schema")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "robots.txt").write_text(ROBOTS, encoding="utf-8")
    (out / "genre" / "genre.css").write_text(CSS, encoding="utf-8")

    n_tag = sum(1 for n in nodes.values() if n["tag_level"])
    ordered = sorted(nodes.values(), key=lambda n: (fold(n["name"]), n["key"]))

    # ---- genre pages ----
    for n in ordered:
        key, name = n["key"], n["name"]
        ps, ks, ak = parents.get(key, []), kids.get(key, []), aliases.get(key, [])
        path = crumb_path(key)
        canon = page_url(key)

        # description
        bits = [f"{name} is a {'tag-level ' if n['tag_level'] else ''}music genre."]
        if ps:
            names = [nodes[l["parent"]]["name"] for l in ps[:3]]
            bits.append("Parent genre" + ("s" if len(ps) > 1 else "") + ": " + ", ".join(names) + (" and more" if len(ps) > 3 else "") + ".")
        else:
            bits.append("It has no parent genre.")
        if ks:
            bits.append(f"{len(ks)} subgenre" + ("s" if len(ks) != 1 else "") + ".")
        if ak:
            bits.append("Also known as " + ", ".join(ak[:2]) + ".")
        desc = cut(" ".join(bits), 158)
        title = f"{name}: subgenres, parent genres and aliases | {SITE_NAME}"

        same = [u for t, u in ext_links(n) if t in ("Wikidata", "MusicBrainz")]
        term = {"@context": "https://schema.org", "@type": "DefinedTerm", "name": name, "identifier": key, "url": canon,
                "inDefinedTermSet": BASE}
        if ak:
            term["alternateName"] = ak
        if same:
            term["sameAs"] = same
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement":
                  [{"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": BASE}] +
                  [{"@type": "ListItem", "position": i + 2, "name": nodes[k]["name"], "item": page_url(k)} for i, k in enumerate(path)]}
        extra = (f"<script type=\"application/ld+json\">\n{jld(term)}\n</script>\n"
                 f"<script type=\"application/ld+json\">\n{jld(crumbs)}\n</script>\n")

        h = [head(title, desc, canon, extra), "<body>\n<header>\n<a class=\"site\" href=\"../\">", escape(SITE_NAME), "</a>\n",
             "<nav class=\"crumbs\" aria-label=\"Breadcrumb\"><ol>\n<li><a href=\"../\">Home</a></li>\n"]
        for k in path[:-1]:
            h.append(f"<li><a href=\"{url_key(k)}.html\">{escape(nodes[k]['name'])}</a></li>\n")
        h.append(f"<li aria-current=\"page\">{escape(name)}</li>\n</ol></nav>\n</header>\n<main>\n")
        h.append(f"<h1>{escape(name)}</h1>\n<div class=\"key\">{escape(key)}</div>\n")

        h.append("<h2>Parent genres</h2>\n")
        if ps:
            h.append("<ul class=\"plain\">\n")
            for l in ps:
                h.append(f"<li><a href=\"{url_key(l['parent'])}.html\">{escape(nodes[l['parent']]['name'])}</a>"
                         f" <span class=\"small\">(source: {escape(SRC_NAMES.get(l['source'], l['source']))}, {escape(l['basis'])}; {escape(l['evidence'])})</span></li>\n")
            h.append("</ul>\n")
        else:
            h.append("<p>None. This genre sits at the top of the tree.</p>\n")

        h.append("<h2>Subgenres</h2>\n")
        if ks:
            h.append("<ul class=\"cols\">\n" + "".join(
                f"<li><a href=\"{url_key(c)}.html\">{escape(nodes[c]['name'])}</a></li>\n" for c in ks) + "</ul>\n")
        else:
            h.append("<p>None listed.</p>\n")

        if ak:
            h.append("<h2>Also known as</h2>\n<ul class=\"plain\">\n" + "".join(f"<li>{escape(a)}</li>\n" for a in ak) + "</ul>\n")

        h.append("<h2>Tag level</h2>\n")
        if n["tag_level"]:
            h.append("<p><span class=\"pill\">Tag level</span> This genre is broad enough to write as a genre tag on a track, "
                     "and fine enough to be useful. It is one of " f"{n_tag} such genres.</p>\n")
        else:
            h.append("<p>This genre is not marked as tag level. It is broader or narrower than the depth that a file's genre tag usually uses.</p>\n")

        h.append("<h2>External links</h2>\n<ul class=\"plain\">\n")
        for t, u in ext_links(n):
            h.append(f"<li><a href=\"{escape(u, quote=True)}\" target=\"_blank\" rel=\"noopener noreferrer\">{escape(t)}</a> <span class=\"small\">(opens in a new tab)</span></li>\n")
        h.append("</ul>\n")
        h.append(f"<p><a class=\"btn\" href=\"../?g={url_key(key)}\">Open in the tree viewer</a></p>\n</main>\n{foot('../')}</body>\n</html>\n")
        (out / "genre" / f"{key}.html").write_text("".join(h), encoding="utf-8")

    # ---- A to Z index ----
    groups = defaultdict(list)
    for n in ordered:
        c = fold(n["name"])[:1].upper()
        groups[c if c.isalpha() else "#"].append(n)
    letters = sorted(groups, key=lambda c: (c == "#", c))
    idx_desc = f"All {len(nodes):,} music genres and subgenres in the Music Genre Taxonomy, from A to Z. {n_tag} are tag-level genres."
    h = [head(f"All {len(nodes):,} music genres A to Z | {SITE_NAME}", idx_desc, BASE + "genre/"),
         "<body>\n<header>\n<a class=\"site\" href=\"../\">", escape(SITE_NAME), "</a>\n</header>\n<main>\n",
         f"<h1>All {len(nodes):,} music genres, A to Z</h1>\n<p>Tag-level genres are marked <span class=\"pill\">tag</span>. "
         "Open a genre for its parents, subgenres and links, or use the <a href=\"../\">tree viewer</a>.</p>\n",
         "<ul class=\"az\">" + "".join(f"<li><a href=\"#l-{'0' if c == '#' else c}\">{escape(c)}</a></li>" for c in letters) + "</ul>\n"]
    for c in letters:
        h.append(f"<h2 id=\"l-{'0' if c == '#' else c}\">{escape(c)}</h2>\n<ul class=\"cols\">\n")
        for n in groups[c]:
            tag = " <span class=\"pill\">tag</span>" if n["tag_level"] else ""
            h.append(f"<li><a href=\"{url_key(n['key'])}.html\">{escape(n['name'])}</a>{tag}</li>\n")
        h.append("</ul>\n")
    h.append(f"</main>\n{foot('../')}</body>\n</html>\n")
    (out / "genre" / "index.html").write_text("".join(h), encoding="utf-8")

    # ---- 404 ----
    css_inline = CSS.replace("</", "<\\/")
    nf = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
          "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
          f"<title>Page not found | {SITE_NAME}</title>\n<meta name=\"robots\" content=\"noindex\">\n"
          f"<style>\n{css_inline}</style>\n</head>\n<body>\n<header><a class=\"site\" href=\"{BASE}\">{SITE_NAME}</a></header>\n<main>\n"
          f"<h1>Page not found</h1>\n<p>This page does not exist. Try the <a href=\"{BASE}\">tree viewer</a> "
          f"or the <a href=\"{BASE}genre/\">A to Z list of genres</a>.</p>\n</main>\n"
          f"<footer><p>{NOT_AFFILIATED}</p></footer>\n</body>\n</html>\n")
    (out / "404.html").write_text(nf, encoding="utf-8")

    # ---- sitemap ----
    urls = [BASE, BASE + "genre/"] + [page_url(n["key"]) for n in ordered]
    (out / "sitemap.xml").write_text(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        + "".join(f"<url><loc>{escape(u)}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")

    files = [p for p in out.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"built {out}: {len(files)} files, {size / 1e6:.1f} MB, {len(nodes)} genre pages, {len(urls)} sitemap URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
