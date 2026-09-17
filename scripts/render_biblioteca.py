#!/usr/bin/env python3
"""Render Biblioteca (libros en PDF de dominio publico).

Lee content/biblioteca/*.yml (subidos por el CMS o a mano), genera una pagina
standalone <slug>.html por libro (reusa el chrome de lecturas-para-el-uruguay.html, igual
que hace render_articles.py con Formacion) y reescribe la grilla de libros
entre los marcadores <!-- BOOKS:START --> / <!-- BOOKS:END --> dentro de
lecturas-para-el-uruguay.html.

Correr desde la raiz del repo:  python scripts/render_biblioteca.py
Pure stdlib + `yaml` + og_image.py (Pillow) para la portada social.
"""
import io, os, re, sys, glob

import yaml

import og_image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content", "biblioteca")
TEMPLATE = os.path.join(ROOT, "lecturas-para-el-uruguay.html")
OG_DIR = os.path.join(ROOT, "og")
SITE = "https://resurgirnacionaluy.org/"
MARK_A = "<!-- BOOKS:START -->"
MARK_B = "<!-- BOOKS:END -->"
GEN_MARK = "<!-- generated:biblioteca-book -->"
RESERVED = {"index", "vision", "formacion", "sagradocorazondejesus", "biblioteca",
            "admin", "404", "readme", "articulos",
            "ideario-y-valores-rn", "catolicismo-en-uruguay", "cultura-nacional-uruguaya",
            "lecturas-para-el-uruguay"}


def _lp(p):
    """En Windows, rutas >= 260 chars necesitan el prefijo \\\\?\\. No-op en Linux (CI)."""
    p = os.path.abspath(p)
    if os.name == "nt" and len(p) >= 255 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + p
    return p


def rd(p):
    return io.open(_lp(p), encoding="utf-8").read()


def wr(p, s):
    io.open(_lp(p), "w", encoding="utf-8", newline="\n").write(s)


def esc(s):
    import html
    return html.escape(str(s), quote=True)


def load_books():
    books = []
    for path in sorted(glob.glob(os.path.join(CONTENT, "*.yml"))):
        slug = os.path.splitext(os.path.basename(path))[0].lower()
        slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-")
        if not slug or slug in RESERVED:
            print("  skip (slug reservado/invalido): %s" % path)
            continue
        b = yaml.safe_load(rd(path)) or {}
        if not isinstance(b, dict):
            continue
        if b.get("draft") in (True, "true", "True"):
            print("  skip (borrador): %s" % slug)
            continue
        if not b.get("title") or not b.get("pdf"):
            print("  skip (falta titulo o pdf): %s" % slug)
            continue
        b["slug"] = slug
        books.append(b)
    books.sort(key=lambda b: (str(b.get("year", "")), b.get("title", "")), reverse=True)
    return books


def meta_line(b):
    return "%s · %s" % (b.get("author") or "Resurgir Nacional", b.get("year") or "s/f")


def pdf_size_mb(b):
    path = os.path.join(ROOT, b["pdf"])
    try:
        return "%.1f" % (os.path.getsize(_lp(path)) / (1024 * 1024))
    except OSError:
        return None


def og_name(slug):
    # prefijo "libro-" para no compartir namespace con og/<slug>.jpg de Formacion
    # (ambos scripts escriben en el mismo directorio og/, en limpiezas separadas)
    return "libro-" + slug + ".jpg"


def write_og_image(b):
    """Genera og/libro-<slug>.jpg con el titulo real del libro (si cambio)."""
    out = os.path.join(OG_DIR, og_name(b["slug"]))
    tmp = out + ".tmp"
    og_image.make_og_image("Biblioteca · Libro", b["title"], meta_line(b), tmp,
                            background=og_image.BACKGROUND_BIBLIOTECA, fmt="JPEG")
    with open(_lp(tmp), "rb") as f:
        new = f.read()
    old = None
    if os.path.exists(out):
        with open(_lp(out), "rb") as f:
            old = f.read()
    if old == new:
        os.remove(_lp(tmp))
        return False
    os.replace(_lp(tmp), _lp(out))
    return True


def book_page(tpl, b):
    title = b["title"]
    summary = b.get("summary", "") or title
    size_mb = pdf_size_mb(b)
    size_txt = " (%s MB)" % size_mb if size_mb else ""
    pages = b.get("pages")
    lead = meta_line(b) + (" · %s páginas" % pages if pages else "")
    book_url = SITE + b["slug"] + ".html"
    pre = tpl[:tpl.index("<main>")]
    post = tpl[tpl.index("</main>") + len("</main>"):]
    pre = pre.replace("<title>Biblioteca — Resurgir Nacional</title>",
                      "<title>%s · Biblioteca · Resurgir Nacional</title>" % esc(title), 1)
    pre = pre.replace(SITE + "lecturas-para-el-uruguay.html", book_url)          # canonical, hreflang, og:url
    pre = re.sub(r'(<meta name="description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(summary) + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(title) + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(summary) + m.group(2), pre, count=1)
    pre = re.sub(r'<meta property="og:image" content="[^"]*" />',
                 '<meta property="og:image" content="%sog/%s" />' % (SITE, og_name(b["slug"])),
                 pre, count=1)
    pre = pre.replace("<head>", "<head>\n" + GEN_MARK, 1)
    main_html = (
        '<main>\n'
        '  <article class="doc">\n'
        '    <section>\n'
        '      <span class="label">Biblioteca · Libro</span>\n'
        '      <h1>%s</h1>\n'
        '      <p class="doc-lead">%s</p>\n'
        '      <button type="button" class="share-btn" aria-label="Compartir este libro">'
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>'
        'Compartir</button>\n'
        '    </section>\n'
        '    <section>\n'
        '      <div class="prose"><p>%s</p></div>\n'
        '      <p style="margin-top:1.6rem"><a class="btn btn--rounded" href="%s" target="_blank" '
        'rel="noopener">Descargar PDF%s →</a></p>\n'
        '      <p style="margin-top:2.5rem"><a href="lecturas-para-el-uruguay.html">← Volver a Biblioteca</a></p>\n'
        '    </section>\n'
        '  </article>\n'
        '</main>' % (esc(title), esc(lead), esc(summary), esc(b["pdf"]), esc(size_txt))
    )
    return pre + main_html + post


def cards_block(books):
    if not books:
        return ""
    rows = []
    for b in books:
        rows.append(
            '        <a class="act" href="%s.html">\n'
            '          <h3>%s</h3>\n'
            '          <p>%s</p>\n'
            '          <span class="act__meta">%s</span>\n'
            '        </a>' % (b["slug"], esc(b["title"]), esc(b.get("summary", "")), esc(meta_line(b)))
        )
    return '\n      <div class="acts acts--articles">\n' + "\n".join(rows) + "\n      </div>\n      "


def main():
    if not os.path.isdir(CONTENT):
        os.makedirs(CONTENT, exist_ok=True)
    if not os.path.exists(TEMPLATE):
        print("ERROR: falta lecturas-para-el-uruguay.html (correr tools/build.py primero)")
        return 1
    tpl = rd(TEMPLATE)
    if MARK_A not in tpl or MARK_B not in tpl:
        print("ERROR: faltan los marcadores BOOKS en lecturas-para-el-uruguay.html")
        return 1
    books = load_books()

    written = set()
    for b in books:
        out = os.path.join(ROOT, b["slug"] + ".html")
        page = book_page(tpl, b)
        if not os.path.exists(out) or rd(out) != page:
            wr(out, page)
            print("  escrito: %s.html" % b["slug"])
        if write_og_image(b):
            print("  og/%s: imagen social actualizada" % og_name(b["slug"]))
        written.add(b["slug"] + ".html")

    # remove stale generated book pages
    for path in glob.glob(os.path.join(ROOT, "*.html")):
        name = os.path.basename(path)
        if name in written:
            continue
        try:
            head = rd(path)[:2000]
        except Exception:
            continue
        if GEN_MARK in head:
            os.remove(_lp(path))
            print("  eliminado (obsoleto): %s" % name)

    # remove stale per-book OG images (solo las propias: prefijo "libro-")
    slugs = {b["slug"] for b in books}
    if os.path.isdir(OG_DIR):
        for path in glob.glob(os.path.join(OG_DIR, "libro-*.jpg")):
            slug = os.path.basename(path)[len("libro-"):-len(".jpg")]
            if slug not in slugs:
                os.remove(_lp(path))
                print("  eliminado (obsoleto): og/%s" % os.path.basename(path))

    i = tpl.index(MARK_A) + len(MARK_A)
    j = tpl.index(MARK_B)
    new_tpl = tpl[:i] + cards_block(books) + tpl[j:]
    if new_tpl != tpl:
        wr(TEMPLATE, new_tpl)
        print("  lecturas-para-el-uruguay.html: grilla actualizada (%d libros)" % len(books))
    else:
        print("  lecturas-para-el-uruguay.html: sin cambios (%d libros)" % len(books))

    return 0


if __name__ == "__main__":
    sys.exit(main())
