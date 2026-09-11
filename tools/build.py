#!/usr/bin/env python3
"""Build de las páginas fijas (portada, Visión, Fe, Formación).

Este script y su carpeta `src/` son el respaldo de continuidad del sitio:
antes solo existían en la máquina/sesión de quien lo mantenía; si eso se
perdía, no había forma de reconstruir ni modificar la estructura del sitio
(header, footer, SEO, chrome compartido). Ahora viven en el repositorio.

`src/index.html` es la fuente de verdad del "chrome" compartido (SVG defs,
<header>, <footer>, reglas CSS de CHROME_CSS): en cada build se copia a las
páginas de SUBPAGES, con los anchors internos reescritos a `index.html#...`
para que funcionen también desde la subpágina. Después todas las páginas se
envuelven como HTML standalone y se escriben en la raíz del repo (un nivel
arriba de esta carpeta), que es donde GitHub Pages sirve el sitio.

Uso (parado en cualquier lado, con Python 3 + `markdown` y `pyyaml` instalados
para el paso final):
    python tools/build.py
Es idempotente: correrlo sin cambios en `src/` no modifica nada.
"""
import io, re, os

TOOLS = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(TOOLS, "src")
ROOT = os.path.dirname(TOOLS)   # raíz del repo (carpeta que sirve GitHub Pages)

# Aplica primero los campos editables sin código (colección Sveltia "Páginas":
# content/pages/*.yml) sobre las fuentes en src/, antes de leerlas más abajo.
import render_pages
render_pages.main()

HOME = "https://resurgirnacionaluy.org/"
VISION_ABS = HOME + "vision.html"
SUBPAGES = ["vision.html", "SagradoCorazondeJesus.html", "formacion.html"]
# per-page footer background video override (data-file, data-poster)
FOOTER_VIDEO = {"SagradoCorazondeJesus.html": ("cielo.mp4", "cielo_poster.jpg")}


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def span(s, start, end):
    i = s.index(start); j = s.index(end, i) + len(end)
    return s[i:j], i, j


idx = rd(os.path.join(SRC, "index.html"))
defs, _, _ = span(idx, "<!-- Marcas de marca", "</svg>")

# CSS rules that belong to the shared chrome and must match index.html everywhere
CHROME_CSS = [r'\.footer-legal', r'\.footer-links', r'\.nav-cross']


def sync_css(page):
    for pat in CHROME_CSS:
        m = re.search(r'\n  ' + pat + r' \{[^}]*\}', idx)
        if not m:
            continue
        rule = m.group(0)
        if re.search(r'\n  ' + pat + r' \{[^}]*\}', page):
            page = re.sub(r'\n  ' + pat + r' \{[^}]*\}', lambda _m: rule, page, count=1)
        else:  # rule missing on this page -> add it before </style>
            page = page.replace("\n</style>", rule + "\n</style>", 1)
    return page


chrome = {tag: span(idx, tag, end)[0]
          for tag, end in (('<header class="site-header">', '</header>'),
                            ('<footer class="site-footer">', '</footer>'))}


def for_subpage(block, current):
    b = block.replace('<a class="brand" href="#top">', '<a class="brand" href="index.html">')
    b = re.sub(r'(<a\b[^>]*\bhref=")#', r'\1index.html#', b)          # anchor links only
    b = b.replace(VISION_ABS, "vision.html")
    b = re.sub(r'(<a\b(?![^>]*aria-current)[^>]*\bhref="' + re.escape(current) + r'")',
               r'\1 aria-current="page"', b)                          # mark current page
    return b


built = {}
for name in SUBPAGES:
    path = os.path.join(SRC, name)
    if not os.path.exists(path):
        continue
    page = rd(path); before = page
    if "<!--DEFS-->" in page:
        page = page.replace("<!--DEFS-->", defs, 1)
    elif "<!-- Marcas de marca" in page:
        old, i, j = span(page, "<!-- Marcas de marca", "</svg>")
        if old != defs:
            page = page[:i] + defs + page[j:]
    for tag, block in chrome.items():
        end = '</header>' if 'header' in tag else '</footer>'
        want = for_subpage(block, name)
        if tag in page:
            old, i, j = span(page, tag, end)
            if old != want:
                page = page[:i] + want + page[j:]
    fv = FOOTER_VIDEO.get(name)
    if fv:
        page = page.replace('data-file="footer.mp4"', 'data-file="%s"' % fv[0])
        page = page.replace('data-poster="footer_poster.jpg"', 'data-poster="%s"' % fv[1])
    page = sync_css(page)
    if page != before:
        wr(path, page)
    built[name] = page

# --- emit standalone pages for GitHub Pages ---
HEAD = ('<!doctype html>\n<html lang="es">\n<head>\n'
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        '<meta name="theme-color" content="#14315C" />\n'
        '<link rel="icon" href="favicon.ico" sizes="any" />\n'
        '<link rel="icon" href="favicon-32.png" sizes="32x32" type="image/png" />\n'
        '<link rel="icon" href="favicon-192.png" sizes="192x192" type="image/png" />\n'
        '<link rel="apple-touch-icon" href="apple-touch-icon.png" />\n'
        '<style>*{box-sizing:border-box}img{max-width:100%;height:auto}[hidden]{display:none!important}</style>\n')


def to_repo(src):
    s = src
    s = s.replace(VISION_ABS, "vision.html")
    s = s.replace(HOME + "#", "index.html#")
    s = s.replace('href="' + HOME + '"', 'href="index.html"')
    s = s.replace(HOME, "index.html")
    s = s.replace("@@SITE@@", HOME)   # expand SEO absolute-URL token (canonical, og:*)
    s = re.sub(r'poster="data:image/[^"]+"\s+data-poster="([^"]+)"', r'poster="\1"', s)
    s = re.sub(r'src="data:video/mp4;base64,[^"]+"\s+type="video/mp4"\s+data-file="([^"]+)"',
               r'src="\1" type="video/mp4"', s)
    hb = s.index("</style>") + len("</style>")
    return HEAD + s[:hb] + '\n</head>\n<body style="margin:0">\n' + s[hb:] + "\n</body>\n</html>\n"


wr(os.path.join(ROOT, "index.html"), to_repo(idx))
for name, page in built.items():
    wr(os.path.join(ROOT, name), to_repo(page))
print("built:", ", ".join(["index.html"] + list(built)))

# render Formacion articles (content/formacion/*.md -> <slug>.html + article list)
import subprocess, sys
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "render_articles.py")], cwd=ROOT)
if r.returncode:
    print("WARNING: render_articles.py salio con codigo", r.returncode)
