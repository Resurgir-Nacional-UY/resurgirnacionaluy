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


def sub_by_marker(page, key, value):
    """<tag ... data-cms="key">...texto...</tag>: reemplaza el texto interno de un
    único elemento marcado por su atributo data-cms (sin HTML propio)."""
    if value is None:
        return page
    pat = re.compile(
        r'(<([a-zA-Z0-9]+)\b[^>]*\bdata-cms="%s"[^>]*>).*?(</\2>)' % re.escape(key), re.S)
    return pat.sub(lambda m: m.group(1) + esc(value) + m.group(3), page, count=1)


def sub_lines_br(page, key, value):
    """Como sub_by_marker, pero cada salto de línea del valor se vuelve <br />
    (para textos cortos de una o dos líneas, p. ej. invocaciones)."""
    if value is None:
        return page
    inner = "<br />".join(esc(line) for line in str(value).split("\n"))
    pat = re.compile(
        r'(<([a-zA-Z0-9]+)\b[^>]*\bdata-cms="%s"[^>]*>).*?(</\2>)' % re.escape(key), re.S)
    return pat.sub(lambda m: m.group(1) + inner + m.group(3), page, count=1)


def sub_list(page, prefix, items, fields):
    """items: lista de dicts (del widget "list" del CMS). Para cada ítem i
    (arrancando en 1) y cada subcampo, sustituye el elemento marcado con
    data-cms="{prefix}{i}-{subcampo}". La cantidad de ítems en el HTML es fija
    (min == max en el CMS), así que ítems de más o de menos en el YAML se
    ignoran / dejan el marcador sin tocar."""
    if not items:
        return page
    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        for f in fields:
            page = sub_by_marker(page, "%s%d-%s" % (prefix, i, f), item.get(f))
    return page


def apply_home(page):
    d = load("home")
    page = sub_text(page, "p", "hero__lead", d.get("hero_lead"))
    page = sub_video_src(page, "hero__flag", d.get("hero_video"))
    page = sub_video_src(page, "sumate__video", d.get("sumate_video"))
    return page


def apply_vision(page):
    d = load("vision")
    page = sub_video_src(page, "doc-hero__flag", d.get("hero_video"))
    page = sub_by_marker(page, "sec1-heading", d.get("sec1_heading"))
    page = sub_by_marker(page, "sec1-p1", d.get("sec1_p1"))
    page = sub_by_marker(page, "sec1-pullquote", d.get("sec1_pullquote"))
    page = sub_by_marker(page, "sec1-p2", d.get("sec1_p2"))
    page = sub_by_marker(page, "sec1-p3", d.get("sec1_p3"))
    page = sub_by_marker(page, "sec1-p4", d.get("sec1_p4"))
    page = sub_by_marker(page, "sec2-heading", d.get("sec2_heading"))
    page = sub_by_marker(page, "sec2-p1", d.get("sec2_p1"))
    page = sub_by_marker(page, "sec2-p2", d.get("sec2_p2"))
    page = sub_by_marker(page, "sec3-heading", d.get("sec3_heading"))
    page = sub_list(page, "v", d.get("sec3_values") or [], ["title", "body"])
    page = sub_by_marker(page, "sec4-heading", d.get("sec4_heading"))
    page = sub_by_marker(page, "sec4-p1", d.get("sec4_p1"))
    page = sub_by_marker(page, "sec4-p2", d.get("sec4_p2"))
    page = sub_by_marker(page, "sec4-p3", d.get("sec4_p3"))
    page = sub_list(page, "f", d.get("sec4_facts") or [], ["big", "label"])
    page = sub_by_marker(page, "sec5-heading", d.get("sec5_heading"))
    page = sub_list(page, "a", d.get("sec5_acts") or [], ["title", "body"])
    return page


def apply_fe(page):
    d = load("fe")
    page = sub_tag_src(page, "img", "scj-bg", d.get("bg_scj"))
    page = sub_tag_src(page, "img", "icdm-bg", d.get("bg_icdm"))
    page = sub_by_marker(page, "sec1-lead", d.get("sec1_lead"))
    page = sub_by_marker(page, "sec1-p1", d.get("sec1_p1"))
    page = sub_by_marker(page, "sec2-heading", d.get("sec2_heading"))
    page = sub_by_marker(page, "sec2-p1", d.get("sec2_p1"))
    page = sub_by_marker(page, "sec2-p2", d.get("sec2_p2"))
    page = sub_by_marker(page, "sec2-p3", d.get("sec2_p3"))
    page = sub_by_marker(page, "sec2-p4", d.get("sec2_p4"))
    page = sub_by_marker(page, "sec2-p5", d.get("sec2_p5"))
    page = sub_by_marker(page, "sec2-p6", d.get("sec2_p6"))
    page = sub_lines_br(page, "sec2-invocations", d.get("sec2_invocations"))
    page = sub_by_marker(page, "sec3-heading", d.get("sec3_heading"))
    page = sub_by_marker(page, "sec3-p1", d.get("sec3_p1"))
    page = sub_by_marker(page, "sec3-p2", d.get("sec3_p2"))
    page = sub_by_marker(page, "sec3-p3", d.get("sec3_p3"))
    page = sub_by_marker(page, "sec3-p4", d.get("sec3_p4"))
    page = sub_by_marker(page, "sec3-p5", d.get("sec3_p5"))
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
