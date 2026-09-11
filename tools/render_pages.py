#!/usr/bin/env python3
"""Aplica los campos "editables sin código" (colección Sveltia "Páginas") a las
páginas fuente en tools/src/.

Lee content/pages/*.yml (uno por página: home, vision, fe, formacion) y
reemplaza, en el HTML fuente, el contenido de un elemento puntual —siempre
localizado por su class/atributo, nunca por el valor actual— así que es
idempotente: correrlo de nuevo sin cambios no modifica nada, y correrlo tras
cambiar un campo en el CMS actualiza justo ese punto sin tocar el resto.

Se corre antes de envolver las páginas para repo/ (build.py lo llama solo).
"""
import io, os, re, html
import yaml

TOOLS = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(TOOLS, "src")
ROOT = os.path.dirname(TOOLS)
CONTENT = os.path.join(ROOT, "content", "pages")


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def esc(s):
    return html.escape(str(s), quote=True)


def load(name):
    p = os.path.join(CONTENT, name + ".yml")
    if not os.path.exists(p):
        return {}
    data = yaml.safe_load(rd(p))
    return data if isinstance(data, dict) else {}


def sub_video_src(page, cls, value):
    """<video class="cls" ...><source src="...">: cambia el src del <source>."""
    if not value:
        return page
    pat = re.compile(
        r'(<video\b[^>]*\bclass="%s"[^>]*>.*?<source\b[^>]*\bsrc=")[^"]*("[^>]*/?>.*?</video>)'
        % re.escape(cls), re.S)
    return pat.sub(lambda m: m.group(1) + esc(value) + m.group(2), page, count=1)


def sub_tag_src(page, tag, cls, value):
    """<tag class="cls" ... src="...">: cambia src (class antes que src)."""
    if not value:
        return page
    pat = re.compile(r'(<%s\b[^>]*\bclass="%s"[^>]*\bsrc=")[^"]*(")' % (tag, re.escape(cls)))
    return pat.sub(lambda m: m.group(1) + esc(value) + m.group(2), page, count=1)


def sub_text(page, tag, cls, value):
    """<tag class="cls">...texto...</tag>: reemplaza el texto interno (sin HTML propio)."""
    if value is None:
        return page
    pat = re.compile(r'(<%s\b[^>]*\bclass="%s"[^>]*>).*?(</%s>)' % (tag, re.escape(cls), tag), re.S)
    return pat.sub(lambda m: m.group(1) + esc(value) + m.group(2), page, count=1)


def sub_data_attr(page, tag, cls, attr, value):
    """<tag class="cls" ... attr="...">: reemplaza el valor de un atributo data-*."""
    if not value:
        return page
    pat = re.compile(r'(<%s\b[^>]*\bclass="%s"[^>]*\b%s=")[^"]*(")' % (tag, re.escape(cls), attr))
    return pat.sub(lambda m: m.group(1) + esc(value) + m.group(2), page, count=1)


def apply_home(page):
    d = load("home")
    page = sub_text(page, "p", "hero__lead", d.get("hero_lead"))
    page = sub_video_src(page, "hero__flag", d.get("hero_video"))
    page = sub_video_src(page, "sumate__video", d.get("sumate_video"))
    return page


def apply_vision(page):
    d = load("vision")
    page = sub_video_src(page, "doc-hero__flag", d.get("hero_video"))
    return page


def apply_fe(page):
    d = load("fe")
    page = sub_tag_src(page, "img", "scj-bg", d.get("bg_scj"))
    page = sub_tag_src(page, "img", "icdm-bg", d.get("bg_icdm"))
    return page


def apply_formacion(page):
    d = load("formacion")
    page = sub_data_attr(page, "div", "yt-lite", "data-id", d.get("video_youtube_id"))
    page = sub_tag_src(page, "img", "yt-lite__thumb", d.get("video_thumb"))
    return page


APPLIERS = {
    "index.html": apply_home,
    "vision.html": apply_vision,
    "SagradoCorazondeJesus.html": apply_fe,
    "formacion.html": apply_formacion,
}


def main():
    if not os.path.isdir(CONTENT):
        os.makedirs(CONTENT, exist_ok=True)
    for name, fn in APPLIERS.items():
        path = os.path.join(SRC, name)
        if not os.path.exists(path):
            continue
        before = rd(path)
        after = fn(before)
        if after != before:
            wr(path, after)
            print("  aplicado: %s" % name)


if __name__ == "__main__":
    main()
