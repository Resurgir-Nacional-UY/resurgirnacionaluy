#!/usr/bin/env python3
"""Rellena "Oraciones por Uruguay" en la página Fe desde content/oraciones/*.yml.

El HTML se escribe en catolicismo-en-uruguay.html entre los marcadores
<!-- ORACIONES:START --> y <!-- ORACIONES:END -->. Si no hay ninguna oración
publicada, la pestaña no se muestra. Todo el texto se escapa: el CMS no admite
HTML crudo.

Uso (desde la raíz del repo):
    python scripts/render_oraciones.py
Es idempotente: sin cambios en content/oraciones/ no modifica nada.
"""
import glob
import html
import io
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "oraciones")
PAGE = os.path.join(ROOT, "catolicismo-en-uruguay.html")
MARK_A = "<!-- ORACIONES:START -->"
MARK_B = "<!-- ORACIONES:END -->"


def esc(s):
    return html.escape(str(s), quote=True)


def load():
    out = []
    # *.yml y *.yaml: el CMS escribe .yml, pero no se descarta nada por la extensión.
    paths = sorted(glob.glob(os.path.join(SRC, "*.yml")) + glob.glob(os.path.join(SRC, "*.yaml")))
    for path in paths:
        with io.open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        if d.get("draft"):
            continue
        title = str(d.get("title") or "").strip()
        body = str(d.get("body") or "").strip()
        if not title or not body:
            sys.exit("ERROR: %s: faltan 'title' o 'body'" % path)
        try:
            orden = int(d.get("orden", 100))
        except (TypeError, ValueError):
            orden = 100
        out.append({
            "title": title,
            "orden": orden,
            "intro": str(d.get("intro") or "").strip(),
            "body": body,
            "fuente": str(d.get("fuente") or "").strip(),
            "name": os.path.basename(path),
        })
    out.sort(key=lambda o: (o["orden"], o["title"].lower(), o["name"]))
    return out


def prayer_html(o):
    parts = ['<details class="oracion">',
             '  <summary>%s</summary>' % esc(o["title"]),
             '  <div class="oracion__cuerpo">']
    if o["intro"]:
        parts.append('    <p class="oracion__intro">%s</p>' % esc(o["intro"]))
    for bloque in re.split(r"\n\s*\n", o["body"]):
        lineas = [esc(l.strip()) for l in bloque.strip().splitlines() if l.strip()]
        if lineas:
            parts.append("    <p>%s</p>" % "<br>\n      ".join(lineas))
    if o["fuente"]:
        parts.append('    <p class="oracion__fuente">%s</p>' % esc(o["fuente"]))
    parts += ["  </div>", "</details>"]
    return "\n".join("    " + l for l in parts)


def section(oraciones):
    """Contenido del panel "Oraciones por Uruguay" (el panel y la pestaña los pone la página Fe)."""
    if not oraciones:
        return ""
    cuerpo = "\n".join(prayer_html(o) for o in oraciones)
    return (
        '\n        <span class="label">Oración</span>\n'
        '        <h2 id="oraciones-titulo">Oraciones por Uruguay</h2>\n'
        '        <div class="oraciones__lista">\n%s\n        </div>\n        ' % cuerpo
    )


def main():
    with io.open(PAGE, encoding="utf-8") as f:
        page = f.read()
    if MARK_A not in page or MARK_B not in page:
        sys.exit("ERROR: faltan los marcadores %s / %s en catolicismo-en-uruguay.html" % (MARK_A, MARK_B))
    i = page.index(MARK_A) + len(MARK_A)
    j = page.index(MARK_B)
    oraciones = load()
    nuevo = page[:i] + section(oraciones) + page[j:]
    if nuevo != page:
        with io.open(PAGE, "w", encoding="utf-8", newline="\n") as f:
            f.write(nuevo)
        print("catolicismo-en-uruguay.html: %d oración(es)" % len(oraciones))
    else:
        print("oraciones: sin cambios (%d oración(es))" % len(oraciones))


if __name__ == "__main__":
    main()
