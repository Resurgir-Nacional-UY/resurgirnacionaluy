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

import yaml
import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content", "formacion")
TEMPLATE = os.path.join(ROOT, "formacion.html")
MARK_A = "<!-- ARTICLES:START -->"
MARK_B = "<!-- ARTICLES:END -->"
GEN_MARK = "<!-- generated:formacion-article -->"
RESERVED = {"index", "vision", "formacion", "sagradocorazondejesus", "admin", "404", "readme"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


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
    pre = tpl[:tpl.index("<main>")]
    post = tpl[tpl.index("</main>") + len("</main>"):]
    pre = pre.replace("<title>Formación</title>",
                      "<title>%s · Formación · Resurgir Nacional</title>" % esc(title), 1)
    pre = re.sub(r'<meta name="description" content="[^"]*"',
                 '<meta name="description" content="%s"' % esc(summary), pre, count=1)
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
    if not arts:
        return ""
    rows = []
    for a in arts:
        rows.append(
            '        <a class="act" href="%s.html">\n'
            '          <h3>%s</h3>\n'
            '          <p>%s</p>\n'
            '          <span class="act__meta">%s</span>\n'
            '        </a>' % (a["slug"], esc(a["title"]), esc(a.get("summary", "")), esc(meta_line(a)))
        )
    return '\n      <div class="acts acts--articles">\n' + "\n".join(rows) + "\n      </div>\n      "


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
