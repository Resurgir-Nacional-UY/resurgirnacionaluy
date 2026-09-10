#!/usr/bin/env python3
"""Render Formacion articles.

Reads Markdown files from content/formacion/*.md (written by the CMS or by hand),
turns each into a standalone page <slug>.html at the repo root that reuses the
shared chrome from formacion.html, and rewrites the article list between the
<!-- ARTICLES:START --> / <!-- ARTICLES:END --> markers inside formacion.html.

Run from the repo root:  python scripts/render_articles.py
Pure stdlib + `markdown` + `pyyaml`.
"""
import io, os, re, sys, json, html, glob
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape as xesc

import yaml
import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content", "formacion")
TEMPLATE = os.path.join(ROOT, "formacion.html")
FEED = os.path.join(ROOT, "feed.xml")
SITEMAP = os.path.join(ROOT, "sitemap.xml")
INDEX_NAME = "articulos.html"
INDEX = os.path.join(ROOT, INDEX_NAME)
# Artículos mostrados en la portada de Formación; el resto vive en el índice completo.
HUB_LIMIT = 6
# URL publica del sitio. Cambiar si se pasa a dominio propio (p. ej. https://resurgirnacionaluy.org/)
SITE = "https://resurgirnacionaluy.org/"
STATIC_PAGES = ["", "vision.html", "formacion.html", "SagradoCorazondeJesus.html"]
MARK_A = "<!-- ARTICLES:START -->"
MARK_B = "<!-- ARTICLES:END -->"
GEN_MARK = "<!-- generated:formacion-article -->"
RESERVED = {"index", "vision", "formacion", "sagradocorazondejesus", "admin", "404",
            "readme", "articulos"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_AB = ["ene", "feb", "mar", "abr", "may", "jun", "jul",
            "ago", "sep", "oct", "nov", "dic"]


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def esc(s):
    return html.escape(str(s), quote=True)


def fecha_es(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s or ""))
    if not m:
        return str(s or "")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return "%d de %s de %d" % (d, MESES[mo - 1], y)


def fecha_corta(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s or ""))
    if not m:
        return str(s or "")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return "%d %s %d" % (d, MESES_AB[mo - 1], y)


def _collapse(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def parse_md(text):
    text = text.lstrip("﻿")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            meta = yaml.safe_load(parts[1]) or {}
            return (meta if isinstance(meta, dict) else {}), parts[2].strip()
    return {}, text.strip()


def load_articles():
    arts = []
    for path in sorted(glob.glob(os.path.join(CONTENT, "*.md"))):
        slug = os.path.splitext(os.path.basename(path))[0].lower()
        slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-")
        if not slug or slug in RESERVED:
            print("  skip (slug reservado/invalido): %s" % path)
            continue
        meta, body = parse_md(rd(path))
        if meta.get("draft") in (True, "true", "True"):
            print("  skip (borrador): %s" % slug)
            continue
        if not meta.get("title"):
            print("  skip (sin titulo): %s" % slug)
            continue
        meta["slug"] = slug
        meta["_body"] = body
        arts.append(meta)
    arts.sort(key=lambda a: str(a.get("date", "")), reverse=True)
    return arts


def meta_line(a):
    return "%s · %s" % (fecha_es(a.get("date", "")), a.get("author") or "Resurgir Nacional")


def article_page(tpl, a):
    title = a["title"]
    summary = a.get("summary", "") or title
    body_html = markdown.markdown(a["_body"], extensions=["extra", "sane_lists", "smarty"])
    src = a.get("source_url")
    source_p = ""
    if src:
        source_p = ('\n      <p class="muted" style="margin-top:1.5rem">Publicado tambien en '
                    '<a href="%s" target="_blank" rel="noopener">X</a>.</p>' % esc(src))
    art_url = SITE + a["slug"] + ".html"
    pre = tpl[:tpl.index("<main>")]
    post = tpl[tpl.index("</main>") + len("</main>"):]
    pre = pre.replace("<title>Formación — Resurgir Nacional</title>",
                      "<title>%s · Formación · Resurgir Nacional</title>" % esc(title), 1)
    pre = pre.replace(SITE + "formacion.html", art_url)          # canonical, hreflang, og:url
    pre = pre.replace('<meta property="og:type" content="website" />',
                      '<meta property="og:type" content="article" />', 1)
    pre = re.sub(r'(<meta name="description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(summary) + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(title) + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(summary) + m.group(2), pre, count=1)
    pre = pre.replace("<head>", "<head>\n" + GEN_MARK, 1)
    main_html = (
        '<main>\n'
        '  <article class="doc">\n'
        '    <section>\n'
        '      <span class="label">Formación · Artículo</span>\n'
        '      <h1>%s</h1>\n'
        '      <p class="doc-lead">%s</p>\n'
        '    </section>\n'
        '    <section>\n'
        '      <div class="prose article-body">\n%s\n      </div>%s\n'
        '      <p style="margin-top:2.5rem"><a href="formacion.html">← Volver a Formación</a></p>\n'
        '    </section>\n'
        '  </article>\n'
        '</main>' % (esc(title), esc(meta_line(a)), body_html, source_p)
    )
    return pre + main_html + post


def list_block(arts):
    """Bloque para la portada de Formación: los HUB_LIMIT más recientes + enlace al índice."""
    if not arts:
        return ""
    rows = []
    for a in arts[:HUB_LIMIT]:
        rows.append(
            '        <a class="act" href="%s.html">\n'
            '          <h3>%s</h3>\n'
            '          <p>%s</p>\n'
            '          <span class="act__meta">%s</span>\n'
            '        </a>' % (a["slug"], esc(a["title"]), esc(a.get("summary", "")), esc(meta_line(a)))
        )
    block = '\n      <div class="acts acts--articles">\n' + "\n".join(rows) + "\n      </div>\n"
    if len(arts) > HUB_LIMIT:
        block += ('      <p class="acts__more"><a href="%s">'
                  'Ver todos los artículos (%d)&nbsp;→</a></p>\n' % (INDEX_NAME, len(arts)))
    return block + "      "


INDEX_JS = """      <script>
        (function () {
          var box = document.querySelector('.art-search');
          var rows = [].slice.call(document.querySelectorAll('.art-row'));
          var none = document.querySelector('.art-nores');
          if (!box || !rows.length) return;
          var norm = function (s) {
            return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
          };
          var keys = rows.map(function (r) { return norm(r.getAttribute('data-s') || ''); });
          var apply = function () {
            var q = norm(box.value.trim());
            var shown = 0;
            rows.forEach(function (r, i) {
              var hit = !q || keys[i].indexOf(q) !== -1;
              r.hidden = !hit;
              if (hit) shown += 1;
            });
            [].forEach.call(document.querySelectorAll('.art-rows'), function (g) {
              var any = [].some.call(g.querySelectorAll('.art-row'), function (r) { return !r.hidden; });
              g.hidden = !any;
              var head = g.previousElementSibling;
              if (head && head.classList.contains('art-year')) head.hidden = !any;
            });
            if (none) none.hidden = shown !== 0;
          };
          box.addEventListener('input', apply);
        })();
      </script>"""


def index_rows(arts):
    parts, year = [], None
    for a in arts:
        m = re.match(r"(\d{4})", str(a.get("date", "")))
        y = m.group(1) if m else "Sin fecha"
        if y != year:
            if year is not None:
                parts.append("      </div>")
            parts.append('      <h2 class="art-year">%s</h2>' % esc(y))
            parts.append('      <div class="art-rows">')
            year = y
        summary = _collapse(a.get("summary", ""))
        hay = _collapse("%s %s %s" % (a.get("title", ""), summary, a.get("author", "")))
        parts.append(
            '        <a class="art-row" href="%s.html" data-s="%s">'
            '<span class="art-row__date">%s</span>'
            '<span class="art-row__title">%s</span>'
            '<span class="art-row__sum">%s</span></a>'
            % (a["slug"], esc(hay), esc(fecha_corta(a.get("date", ""))),
               esc(a["title"]), esc(summary))
        )
    if year is not None:
        parts.append("      </div>")
    return "\n".join(parts)


def index_page(tpl, arts):
    """Índice completo: articulos.html, con buscador en vivo. Reusa el chrome de formacion.html."""
    pre = tpl[:tpl.index("<main>")]
    post = tpl[tpl.index("</main>") + len("</main>"):]
    desc = "Todos los artículos de formación del movimiento nacionalista uruguayo Resurgir Nacional."
    pre = pre.replace("<title>Formación — Resurgir Nacional</title>",
                      "<title>Artículos de Formación · Resurgir Nacional</title>", 1)
    pre = pre.replace(SITE + "formacion.html", SITE + INDEX_NAME)   # canonical, hreflang, og:url
    pre = re.sub(r'(<meta name="description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(desc) + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                 lambda m: m.group(1) + "Artículos de Formación — Resurgir Nacional" + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(desc) + m.group(2), pre, count=1)
    pre = pre.replace("<head>", "<head>\n" + GEN_MARK, 1)
    n = len(arts)
    lead = ("%d publicaciones. Buscá por título, resumen o autor." % n) if n \
        else "Todavía no hay artículos publicados."
    main_html = (
        '<main>\n'
        '  <article class="doc">\n'
        '    <section>\n'
        '      <span class="label">Formación</span>\n'
        '      <h1>Artículos</h1>\n'
        '      <p class="doc-lead">%s</p>\n'
        '      <input type="search" class="art-search" placeholder="Buscar…" '
        'aria-label="Buscar artículos" autocomplete="off" />\n'
        '      <p class="art-nores" hidden>No hay artículos que coincidan con la búsqueda.</p>\n'
        '    </section>\n'
        '    <section class="art-index">\n'
        '%s\n'
        '      <p style="margin-top:2.5rem"><a href="formacion.html">← Volver a Formación</a></p>\n'
        '    </section>\n'
        '%s\n'
        '  </article>\n'
        '</main>' % (esc(lead), index_rows(arts), INDEX_JS)
    )
    return pre + main_html + post


def _rfc822(datestr):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(datestr or ""))
    if not m:
        return None
    dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 12, 0, 0, tzinfo=timezone.utc)
    return format_datetime(dt)


def write_feed(arts):
    items, newest = [], None
    for a in arts:
        url = SITE + a["slug"] + ".html"
        pub = _rfc822(a.get("date"))
        if pub and not newest:
            newest = pub
        items.append(
            "  <item>\n"
            "    <title>%s</title>\n"
            "    <link>%s</link>\n"
            '    <guid isPermaLink="true">%s</guid>\n'
            "%s"
            "    <description>%s</description>\n"
            "  </item>" % (
                xesc(a["title"]), xesc(url), xesc(url),
                ("    <pubDate>%s</pubDate>\n" % pub) if pub else "",
                xesc(a.get("summary", "") or a["title"]),
            )
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "<channel>\n"
        "  <title>Resurgir Nacional — Formación</title>\n"
        "  <link>%sformacion.html</link>\n"
        '  <atom:link href="%sfeed.xml" rel="self" type="application/rss+xml" />\n'
        "  <description>Artículos de formación del movimiento Resurgir Nacional.</description>\n"
        "  <language>es-uy</language>\n"
        "%s"
        "%s"
        "</channel>\n"
        "</rss>\n" % (
            SITE, SITE,
            ("  <lastBuildDate>%s</lastBuildDate>\n" % newest) if newest else "",
            ("\n".join(items) + "\n") if items else "",
        )
    )
    if not os.path.exists(FEED) or rd(FEED) != feed:
        wr(FEED, feed)
        print("  feed.xml: %d articulos" % len(arts))


def write_sitemap(arts):
    pages = list(STATIC_PAGES)
    if len(arts) > HUB_LIMIT:
        pages.append(INDEX_NAME)
    rows = ["  <url><loc>%s%s</loc></url>" % (SITE, p) for p in pages]
    for a in arts:
        m = re.match(r"\d{4}-\d{2}-\d{2}", str(a.get("date", "")))
        lm = "<lastmod>%s</lastmod>" % m.group(0) if m else ""
        rows.append("  <url><loc>%s%s.html</loc>%s</url>" % (SITE, a["slug"], lm))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(rows) + "\n</urlset>\n")
    if not os.path.exists(SITEMAP) or rd(SITEMAP) != xml:
        wr(SITEMAP, xml)
        print("  sitemap.xml: %d urls" % len(rows))


def main():
    if not os.path.isdir(CONTENT):
        os.makedirs(CONTENT, exist_ok=True)
    tpl = rd(TEMPLATE)
    if MARK_A not in tpl or MARK_B not in tpl:
        print("ERROR: faltan los marcadores ARTICLES en formacion.html")
        return 1
    arts = load_articles()

    # write / refresh each article page
    written = set()
    for a in arts:
        out = os.path.join(ROOT, a["slug"] + ".html")
        page = article_page(tpl, a)
        if not os.path.exists(out) or rd(out) != page:
            wr(out, page)
            print("  escrito: %s.html" % a["slug"])
        written.add(a["slug"] + ".html")

    # índice completo articulos.html — solo si hay más artículos que los de la portada
    if len(arts) > HUB_LIMIT:
        page = index_page(tpl, arts)
        if not os.path.exists(INDEX) or rd(INDEX) != page:
            wr(INDEX, page)
            print("  escrito: %s (%d articulos)" % (INDEX_NAME, len(arts)))
        written.add(INDEX_NAME)
    # si no supera el límite, sobra: lo borra la limpieza de abajo (lleva GEN_MARK)

    # remove stale generated article pages
    for path in glob.glob(os.path.join(ROOT, "*.html")):
        name = os.path.basename(path)
        if name in written:
            continue
        try:
            head = rd(path)[:2000]
        except Exception:
            continue
        if GEN_MARK in head:
            os.remove(path)
            print("  eliminado (obsoleto): %s" % name)

    # rewrite the list region inside formacion.html
    i = tpl.index(MARK_A) + len(MARK_A)
    j = tpl.index(MARK_B)
    new_tpl = tpl[:i] + list_block(arts) + tpl[j:]
    if new_tpl != tpl:
        wr(TEMPLATE, new_tpl)
        print("  formacion.html: lista actualizada (%d articulos)" % len(arts))
    else:
        print("  formacion.html: sin cambios (%d articulos)" % len(arts))

    write_feed(arts)
    write_sitemap(arts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
