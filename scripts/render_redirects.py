#!/usr/bin/env python3
"""Genera paginas de redireccion en las URLs viejas que cambiaron de nombre.

Lee content/redirects.yml (lista de {from, to}) y escribe en la raiz del
repo una pagina minima en <from>.html que reenvia a <to>.html (meta refresh
+ canonical), para que los enlaces ya compartidos (WhatsApp, redes,
buscadores) sigan funcionando en vez de romperse.

Se corre al FINAL de tools/build.py, despues de render_articles.py y
render_biblioteca.py: esos scripts ya borraron por su cuenta las paginas
viejas que dejaron de corresponder a un articulo/libro actual (por el
renombre), asi que el nombre viejo esta libre para la redireccion.

Correr desde la raiz del repo:  python scripts/render_redirects.py
Pure stdlib + `pyyaml`.
"""
import io, os
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REDIRECTS_FILE = os.path.join(ROOT, "content", "redirects.yml")
SITE = "https://resurgirnacionaluy.org/"
GEN_MARK = "<!-- generated:redirect -->"

PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
%s
<title>Resurgir Nacional</title>
<link rel="canonical" href="%s%s.html" />
<meta name="robots" content="noindex" />
<meta http-equiv="refresh" content="0; url=%s.html" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
</head>
<body>
<p>Esta página se mudó a <a href="%s.html">%s.html</a>.</p>
</body>
</html>
"""


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


def main():
    if not os.path.exists(REDIRECTS_FILE):
        print("  sin content/redirects.yml, nada que redirigir")
        return 0
    entries = yaml.safe_load(rd(REDIRECTS_FILE)) or []
    n = 0
    for e in entries:
        old, new = e["from"], e["to"]
        out = os.path.join(ROOT, old + ".html")
        page = PAGE % (GEN_MARK, SITE, new, new, new, new)
        if not os.path.exists(out) or rd(out) != page:
            wr(out, page)
            n += 1
            print("  escrito: %s.html -> %s.html" % (old, new))
    if not n:
        print("  redirects: sin cambios (%d entradas)" % len(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
