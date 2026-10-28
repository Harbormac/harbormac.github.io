#!/usr/bin/env python3
"""Builds Harbor's website from src/ into docs/, the folder GitHub Pages publishes, then checks it.

    python3 src/build.py

Each page in src/pages/ starts with its settings in a comment:

    <!--page
    {"path": "/download/", "title": "...", "description": "...", "jsonld": [...]}
    -->

and the rest is the page's <main> content. The script puts every page in src/layout.html, fills in
the placeholders below, writes docs/<path>index.html, the sitemap, robots.txt and the assets, and
then checks what search engines and visitors rely on: one <h1> per page, unique titles and
descriptions of a sensible length, alt text and dimensions on every image, internal links and anchors
that resolve, and structured data that parses. It stops with a list of problems if any check fails.

To move to a custom domain, change SITE and rebuild.
"""
import datetime, hashlib, html, json, os, re, shutil, sys
from html.parser import HTMLParser

SITE = "https://harbormac.github.io"
VERSION = "0.7.0"
RELEASES_URL = "https://github.com/BuiltByArgo/Harbor/releases"
DOWNLOAD_URL = "https://github.com/BuiltByArgo/Harbor/releases/latest"
KOFI_URL = "https://ko-fi.com/A2H229BWWV"
SUPPORT_EMAIL = "builtbyargo@proton.me"
ZIP_SHA256 = "bcb76a69bde68e041b3b3b583e9b0936284622a4e5187b8e0c6dcf73fe7dbf4a"
# Google Search Console's HTML-tag verification code, once there is one (only the content="…" value).
GOOGLE_VERIFICATION = ""

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "docs")
SHOT_SIZES = {"library": (1600, 1203), "bottles": (1600, 1203), "game-settings": (1600, 1203),
              "snapshots": (1600, 1203), "component-updates": (1600, 1203)}


def shot(match):
    """{{shot name "alt text"}} or {{shot name "alt text" eager}}: a screenshot at 800 and 1600 px."""
    name, alt, eager = match.group(1), match.group(2), bool(match.group(3))
    width, height = SHOT_SIZES[name]
    loading = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    return ('<img class="shot" src="/assets/%s-1600.jpg" srcset="/assets/%s-800.jpg 800w, /assets/%s-1600.jpg 1600w" '
            'sizes="(max-width: 1080px) 100vw, 1040px" width="%d" height="%d" alt="%s" %s decoding="async">'
            % (name, name, name, width, height, html.escape(alt, quote=True), loading))


def fill(text, values):
    for key, value in values.items():
        text = text.replace("{{%s}}" % key, value)
    return text


def read_pages():
    pages = []
    for name in sorted(os.listdir(os.path.join(SRC, "pages"))):
        if not name.endswith(".html"):
            continue
        text = open(os.path.join(SRC, "pages", name), encoding="utf-8").read()
        match = re.match(r"\s*<!--page\s*(\{.*?\})\s*-->\s*", text, re.S)
        if not match:
            sys.exit("%s has no <!--page {...} --> settings" % name)
        meta = json.loads(match.group(1))
        meta["file"] = name
        meta["body"] = text[match.end():]
        pages.append(meta)
    return pages


def build():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets"))
    css = open(os.path.join(SRC, "style.css"), "rb").read()
    open(os.path.join(OUT, "assets", "style.css"), "wb").write(css)
    for name in os.listdir(os.path.join(SRC, "assets", "generated")):
        shutil.copy2(os.path.join(SRC, "assets", "generated", name), os.path.join(OUT, "assets", name))
    layout = open(os.path.join(SRC, "layout.html"), encoding="utf-8").read()
    common = {"site": SITE, "version": VERSION, "download_url": DOWNLOAD_URL, "releases_url": RELEASES_URL,
              "kofi_url": KOFI_URL, "support_email": SUPPORT_EMAIL, "zip_sha256": ZIP_SHA256}
    pages = read_pages()
    for page in pages:
        path = page["path"]
        body = re.sub(r'\{\{shot ([\w-]+) "(.*?)"( eager)?\}\}', shot, page["body"])
        body = fill(body, common)
        jsonld = list(page.get("jsonld", []))
        if page.get("faq"):
            # FAQPage data from the page's own <details> questions, so the two never differ.
            def plain(fragment):
                return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()
            questions = re.findall(r"<details[^>]*>\s*<summary>(.*?)</summary>(.*?)</details>", body, re.S)
            jsonld.append({"@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": plain(q), "acceptedAnswer": {"@type": "Answer", "text": plain(a)}} for q, a in questions]})
        graph = {"@context": "https://schema.org", "@graph": jsonld}
        values = dict(common)
        values.update({
            "title": html.escape(fill(page["title"], common)),
            "social_title": html.escape(fill(page.get("social_title", page["title"]), common)),
            "description": html.escape(fill(page["description"], common), quote=True),
            "canonical": SITE + (path if path != "/404.html" else "/"),
            "robots": "noindex" if page.get("noindex") else "index, follow, max-image-preview:large",
            "verification": ('<meta name="google-site-verification" content="%s">\n' % GOOGLE_VERIFICATION) if GOOGLE_VERIFICATION else "",
            "css_version": hashlib.sha256(css).hexdigest()[:10],
            "jsonld": fill(json.dumps(graph, indent=1, ensure_ascii=False), common),
            "body": body.strip(),
        })
        out = fill(layout, values)
        # Mark the current page in the main navigation.
        out = out.replace('<li><a href="%s">' % path, '<li><a href="%s" aria-current="page">' % path, 1)
        target = os.path.join(OUT, "404.html") if path == "/404.html" else os.path.join(OUT, path.strip("/"), "index.html")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, "w", encoding="utf-8").write(out)
        page["output"] = target
    today = datetime.date.today().isoformat()
    urls = "".join("  <url><loc>%s%s</loc><lastmod>%s</lastmod></url>\n" % (SITE, p["path"], today)
                   for p in pages if not p.get("noindex"))
    open(os.path.join(OUT, "sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % urls)
    open(os.path.join(OUT, "robots.txt"), "w").write("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)
    # Plain files: GitHub Pages must not run them through Jekyll.
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    return pages


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1 = 0
        self.ids, self.links, self.images, self.jsonld = set(), [], [], []
        self.title = self.description = ""
        self._in_title = self._in_jsonld = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "h1":
            self.h1 += 1
        elif tag == "a" and "href" in a:
            self.links.append(a["href"])
        elif tag == "img":
            self.images.append(a)
        elif tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("name") == "description":
            self.description = a.get("content", "")
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._in_jsonld = True
            self.jsonld.append("")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            self._in_jsonld = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_jsonld:
            self.jsonld[-1] += data


def check(pages):
    problems, parsed, titles, descriptions = [], {}, {}, {}
    for page in pages:
        parser = Page()
        parser.feed(open(page["output"], encoding="utf-8").read())
        parsed[page["path"]] = parser
    for path, p in parsed.items():
        where = path
        if p.h1 != 1:
            problems.append("%s: %d <h1> elements" % (where, p.h1))
        if not 25 <= len(p.title) <= 65:
            problems.append("%s: title is %d characters" % (where, len(p.title)))
        if not 70 <= len(p.description) <= 160:
            problems.append("%s: description is %d characters" % (where, len(p.description)))
        titles.setdefault(p.title, []).append(where)
        descriptions.setdefault(p.description, []).append(where)
        for img in p.images:
            if "alt" not in img or not img.get("width") or not img.get("height"):
                problems.append("%s: image %s lacks alt, width or height" % (where, img.get("src")))
            src = img.get("src", "")
            if src.startswith("/") and not os.path.exists(os.path.join(OUT, src.lstrip("/"))):
                problems.append("%s: image %s does not exist" % (where, src))
        for block in p.jsonld:
            try:
                json.loads(block)
            except ValueError as error:
                problems.append("%s: structured data does not parse (%s)" % (where, error))
        for href in p.links:
            if not href.startswith("/"):
                continue
            target, _, anchor = href.partition("#")
            if target not in parsed and not os.path.exists(os.path.join(OUT, target.lstrip("/"))):
                problems.append("%s: link to %s, which does not exist" % (where, href))
            elif anchor and target in parsed and anchor not in parsed[target].ids:
                problems.append("%s: link to %s, but that page has no id %s" % (where, href, anchor))
    for kind, seen in (("title", titles), ("description", descriptions)):
        for text, paths in seen.items():
            if len(paths) > 1:
                problems.append("same %s on %s" % (kind, ", ".join(paths)))
    return problems


if __name__ == "__main__":
    pages = build()
    problems = check(pages)
    for page in pages:
        print("built %-34s %s" % (page["path"], os.path.relpath(page["output"], ROOT)))
    if problems:
        print("\n%d problem(s):" % len(problems))
        for problem in problems:
            print("  " + problem)
        sys.exit(1)
    print("\nAll checks passed: %d pages, sitemap.xml, robots.txt." % len(pages))
