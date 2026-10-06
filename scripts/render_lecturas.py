#!/usr/bin/env python3
"""Junta content/lecturas/AAAA-MM-DD.yml y genera:

  * /lecturas.json              -> lo lee la pagina Fe (catolicismo-en-uruguay.html) en el
                                   navegador para mostrar la lectura de hoy (hora de Uruguay).
  * lecturas-de-la-misa-D-de-MES-de-AAAA.html
                                -> una pagina por dia, con URL propia (para que el buscador
                                   encuentre "lecturas de la misa del 6 de octubre de 2026").
                                   Reusa el chrome de lecturas-para-el-uruguay.html, igual que
                                   render_biblioteca.py.
  * lecturas-de-la-misa.html    -> indice con todos los dias (enlaza cada pagina para que se
                                   puedan rastrear).
  * sitemap-lecturas.xml        -> sitemap propio (sitemap.xml es de render_articles.py).

Uso (desde la raiz del repo):
    python scripts/render_lecturas.py
"""
import glob
import html
import io
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "lecturas")
OUT = os.path.join(ROOT, "lecturas.json")
TEMPLATE = os.path.join(ROOT, "lecturas-para-el-uruguay.html")
SITEMAP = os.path.join(ROOT, "sitemap-lecturas.xml")
SITE = "https://resurgirnacionaluy.org/"
INDEX_NAME = "lecturas-de-la-misa.html"
FE_PAGE = "catolicismo-en-uruguay.html"
OG_IMAGE = SITE + "og-image-fe.jpg"
GEN_MARK = "<!-- generated:lecturas-dia -->"
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# Estilos de la lectura (los mismos que la pagina Fe, que las pinta con JavaScript)
CSS = """<style>
  .lecturas__celebracion { font-family: "Fraunces", serif; font-size: var(--step-1); line-height: 1.3; color: var(--ink); margin-top: 0.6rem; max-width: 34ch; }
  .lecturas__santo { color: var(--ink-soft); margin-top: 0.3rem; }
  .lectura { margin-top: 2.2rem; padding-top: 1.6rem; border-top: 1px solid var(--line); max-width: var(--measure); }
  .lectura__tipo { font-family: "Archivo", sans-serif; font-weight: 600; font-size: 0.78rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--gold-text); }
  .lectura__cita { font-family: "Fraunces", serif; font-size: var(--step-1); line-height: 1.25; margin-top: 0.3rem; color: var(--ink); }
  .lectura__lema { font-style: italic; color: var(--ink-soft); margin-top: 0.5rem; }
  .lectura__pres { font-family: "Archivo", sans-serif; font-weight: 600; font-size: 0.9rem; letter-spacing: 0.02em; color: var(--ink); margin-top: 1.1rem; }
  .lectura__texto { margin-top: 0.8rem; display: flex; flex-direction: column; gap: 0.95rem; }
  .lectura__texto p { color: var(--ink); }
  .lectura__texto .lectura__dialogo { padding-left: 1.2rem; border-left: 2px solid var(--gold-line); }
  .lectura__resp { margin-top: 0.9rem; color: var(--ink); }
  .lectura__resp b { font-family: "Archivo", sans-serif; font-weight: 700; color: var(--gold-text); }
  .lectura__estrofa { margin-top: 1rem; white-space: pre-line; color: var(--ink); }
  .lectura__rmark { margin-top: 0.4rem; }
  .lectura__rmark b { font-family: "Archivo", sans-serif; font-weight: 700; color: var(--gold-text); }
  .lectura__cierre { margin-top: 1.1rem; font-family: "Archivo", sans-serif; font-weight: 600; font-size: 0.9rem; color: var(--ink); }
  .lecturas__fuente { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--line); max-width: var(--measure); font-size: 0.85rem; color: var(--ink-soft); }
  .lecturas__pasos { margin-top: 2.2rem; display: flex; flex-wrap: wrap; gap: 0.6rem; max-width: var(--measure); }
  .lecturas__paso { display: flex; flex-direction: column; gap: 0.1rem; min-width: 10.5rem; padding: 0.7rem 1.1rem; border: 1px solid var(--line); border-radius: 14px; color: var(--ink); text-decoration: none; transition: border-color 0.15s ease; }
  .lecturas__paso:hover { border-color: var(--gold-line); }
  .lecturas__paso:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
  .lecturas__paso b { font-family: "Archivo", sans-serif; font-weight: 600; font-size: 0.78rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--gold-text); }
  .lecturas__paso span { font-size: 0.95rem; }
  .lecturas__paso--sig { margin-left: auto; text-align: right; }
  .lecturas__nav { margin-top: 2.2rem; display: flex; flex-wrap: wrap; gap: 0.6rem 1.6rem; }
  .lecturas__nav a { color: var(--ink); }
  .lecturas__mes { margin-top: 2.4rem; font-size: var(--step-1); }
  .lecturas__lista { list-style: none; padding: 0; margin: 0.8rem 0 0; display: flex; flex-direction: column; gap: 0.9rem; max-width: var(--measure); }
  .lecturas__lista a { color: var(--ink); font-weight: 600; }
  .lecturas__lista span { display: block; color: var(--ink-soft); font-size: 0.92rem; }
</style>
"""


def esc(s):
    return html.escape(str(s), quote=True)


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    """Escribe solo si cambio (evita ruido en git)."""
    if os.path.exists(p) and rd(p) == s:
        return False
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    return True


def _bloques(valor):
    """Texto del CMS -> lista de bloques (separados por una línea en blanco)."""
    if not valor:
        return []
    if isinstance(valor, list):
        return valor
    return [b.strip() for b in re.split(r"\n\s*\n", str(valor).strip()) if b.strip()]


def _lectura(l):
    out = {"tipo": l.get("tipo", "")}
    for k in ("cita", "lema", "respuesta", "presentacion", "cierre"):
        v = (l.get(k) or "").strip() if isinstance(l.get(k), str) else l.get(k)
        if v:
            out[k] = v
    texto = _bloques(l.get("texto"))
    if texto:
        out["texto"] = [" ".join(b.split()) for b in texto]
    estrofas = l.get("estrofas")
    if estrofas:
        if isinstance(estrofas, list):
            out["estrofas"] = estrofas
        else:
            out["estrofas"] = [[v.strip() for v in b.splitlines() if v.strip()] for b in _bloques(estrofas)]
    return out


# ---------------------------------------------------------------- fechas y urls
def _fecha_parts(fecha):
    import datetime
    d = datetime.date.fromisoformat(fecha)
    return d, DIAS[d.weekday()], d.day, MESES[d.month - 1], d.year


def slug(fecha):
    _, _, dia, mes, anio = _fecha_parts(fecha)
    return "lecturas-de-la-misa-%d-de-%s-de-%d" % (dia, mes, anio)


def page_name(fecha):
    return slug(fecha) + ".html"


def fecha_corta(fecha):
    _, _, dia, mes, anio = _fecha_parts(fecha)
    return "%d de %s de %d" % (dia, mes, anio)


def fecha_larga(fecha):
    _, sem, _, _, _ = _fecha_parts(fecha)
    return "%s %s" % (sem, fecha_corta(fecha))


# ---------------------------------------------------------------- html de la lectura
def lectura_html(l):
    out = ['      <div class="lectura">']
    out.append('        <div class="lectura__tipo">%s</div>' % esc(l.get("tipo", "")))
    if l.get("cita"):
        out.append('        <div class="lectura__cita">%s</div>' % esc(l["cita"]))
    if l.get("lema"):
        out.append('        <p class="lectura__lema">%s</p>' % esc(l["lema"]))
    if l.get("respuesta"):
        out.append('        <p class="lectura__resp"><b>R. </b>%s</p>' % esc(l["respuesta"]))
    if l.get("presentacion"):
        out.append('        <div class="lectura__pres">%s</div>' % esc(l["presentacion"]))
    if l.get("texto"):
        out.append('        <div class="lectura__texto">')
        for p in l["texto"]:
            cls = ' class="lectura__dialogo"' if p[:1] == "«" else ""
            out.append("          <p%s>%s</p>" % (cls, esc(p)))
        out.append("        </div>")
    for est in l.get("estrofas") or []:
        out.append('        <p class="lectura__estrofa">%s</p>' % esc("\n".join(est)))
        if l.get("respuesta"):
            out.append('        <p class="lectura__rmark"><b>R.</b></p>')
    if l.get("cierre"):
        out.append('        <div class="lectura__cierre">%s</div>' % esc(l["cierre"]))
    out.append("      </div>")
    return "\n".join(out)


def citas(dia):
    vistas, out = set(), []
    for l in dia["lecturas"]:
        c = l.get("cita")
        if c and c not in vistas:
            vistas.add(c)
            out.append(c)
    return out


def recortar(texto, limite=155):
    t = " ".join(texto.split())
    if len(t) <= limite:
        return t
    return t[:limite - 1].rsplit(" ", 1)[0].rstrip(",;:. ") + "…"


# ---------------------------------------------------------------- paginas
def _head(tpl, page, title, desc, og_title, ld):
    pre = tpl[:tpl.index("<main>")]
    pre = re.sub(r"<title>.*?</title>", lambda m: "<title>%s</title>" % esc(title), pre, count=1, flags=re.S)
    pre = pre.replace(SITE + "lecturas-para-el-uruguay.html", SITE + page)     # canonical, hreflang, og:url
    pre = re.sub(r'(<meta name="description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(desc) + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(og_title) + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(desc) + m.group(2), pre, count=1)
    pre = re.sub(r'<meta property="og:image" content="[^"]*" />',
                 '<meta property="og:image" content="%s" />' % OG_IMAGE, pre, count=1)
    pre = pre.replace("<head>", "<head>\n" + GEN_MARK, 1)
    ld_tag = ('<script type="application/ld+json">%s</script>\n'
              % json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"))
    return pre.replace("</head>", CSS + ld_tag + "</head>", 1)


def _crumbs(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u}
        for i, (n, u) in enumerate(items)]}


def day_page(tpl, fecha, dia, prev_f, next_f):
    larga = fecha_larga(fecha)
    page = page_name(fecha)
    title = "Lecturas de la Santa Misa y Evangelio del %s" % fecha_corta(fecha)
    cs = citas(dia)
    desc = recortar("Lecturas de la Santa Misa del %s: %s. %s." % (larga, "; ".join(cs), dia["celebracion"]))
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "headline": "Lecturas de la Santa Misa del %s" % larga,
         "description": desc, "url": SITE + page, "mainEntityOfPage": SITE + page,
         "datePublished": fecha, "dateModified": fecha, "inLanguage": "es-UY",
         "image": OG_IMAGE,
         "author": {"@type": "Organization", "name": "Resurgir Nacional"},
         "publisher": {"@type": "Organization", "name": "Resurgir Nacional",
                       "url": SITE}},
        _crumbs([("Inicio", ""), ("Fe", FE_PAGE), ("Lecturas de la Santa Misa", INDEX_NAME),
                 (fecha_corta(fecha), page)]),
    ]}
    pre = _head(tpl, page, title, desc, "Lecturas de la Santa Misa del %s" % larga, ld)
    post = tpl[tpl.index("</main>") + len("</main>"):]
    cuerpo = "\n".join(lectura_html(l) for l in dia["lecturas"])
    pasos = []
    if prev_f:
        pasos.append('<a class="lecturas__paso" href="%s" rel="prev"><b>← Día anterior</b><span>%s</span></a>'
                     % (page_name(prev_f), esc(fecha_larga(prev_f).capitalize())))
    if next_f:
        pasos.append('<a class="lecturas__paso lecturas__paso--sig" href="%s" rel="next"><b>Día siguiente →</b><span>%s</span></a>'
                     % (page_name(next_f), esc(fecha_larga(next_f).capitalize())))
    pasos_html = ('      <div class="lecturas__pasos">%s</div>\n' % "".join(pasos)) if pasos else ""
    nav = ['<a href="%s">Lecturas de otros días</a>' % INDEX_NAME,
           '<a href="%s#oraciones">Oraciones por Uruguay</a>' % FE_PAGE]
    main = (
        '<main>\n'
        '  <article class="doc">\n'
        '    <section>\n'
        '      <span class="label">Fe · Lecturas de la Santa Misa</span>\n'
        '      <h1>Lecturas de la Santa Misa del %s</h1>\n'
        '      <p class="lecturas__celebracion">%s</p>\n'
        '%s'
        '%s\n'
        '%s'
        '%s'
        '      <nav class="lecturas__nav" aria-label="Más lecturas">%s</nav>\n'
        '    </section>\n'
        '  </article>\n'
        '</main>' % (
            esc(larga), esc(dia["celebracion"]),
            ('      <p class="lecturas__santo">%s</p>\n' % esc(dia["santo"])) if dia["santo"] else "",
            cuerpo,
            ('      <p class="lecturas__fuente">%s</p>\n' % esc(dia["fuente"])) if dia["fuente"] else "",
            pasos_html, " ".join(nav)))
    return pre + main + post


def index_page(tpl, dias):
    fechas = sorted(dias, reverse=True)
    title = "Lecturas de la Santa Misa de cada día · Resurgir Nacional"
    desc = ("Lecturas de la Santa Misa día por día: primera lectura, salmo y Evangelio, "
            "con la fiesta o el santo del día. Del %s al %s."
            % (fecha_corta(fechas[-1]), fecha_corta(fechas[0])))
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": "Lecturas de la Santa Misa de cada día",
         "description": desc, "url": SITE + INDEX_NAME, "inLanguage": "es-UY"},
        _crumbs([("Inicio", ""), ("Fe", FE_PAGE), ("Lecturas de la Santa Misa", INDEX_NAME)]),
    ]}
    pre = _head(tpl, INDEX_NAME, title, recortar(desc), "Lecturas de la Santa Misa de cada día", ld)
    post = tpl[tpl.index("</main>") + len("</main>"):]
    bloques, mes_actual = [], None
    for f in fechas:
        _, _, _, mes, anio = _fecha_parts(f)
        clave = (anio, mes)
        if clave != mes_actual:
            if mes_actual:
                bloques.append("      </ul>")
            bloques.append('      <h2 class="lecturas__mes">%s de %d</h2>\n      <ul class="lecturas__lista">' % (mes.capitalize(), anio))
            mes_actual = clave
        d = dias[f]
        bloques.append('        <li><a href="%s">%s</a><span>%s · %s</span></li>'
                       % (page_name(f), esc(fecha_larga(f).capitalize()), esc(d["celebracion"]),
                          esc("; ".join(citas(d)))))
    bloques.append("      </ul>")
    main = (
        '<main>\n'
        '  <article class="doc">\n'
        '    <section>\n'
        '      <span class="label">Fe</span>\n'
        '      <h1>Lecturas de la Santa Misa</h1>\n'
        '      <p class="doc-lead">Primera lectura, salmo y Evangelio de cada día.</p>\n'
        '%s\n'
        '      <nav class="lecturas__nav" aria-label="Más de Fe">'
        '<a href="%s#lecturas">Lectura de hoy</a> <a href="%s#oraciones">Oraciones por Uruguay</a></nav>\n'
        '    </section>\n'
        '  </article>\n'
        '</main>' % ("\n".join(bloques), FE_PAGE, FE_PAGE))
    return pre + main + post


def sitemap(fechas):
    """<lastmod> solo para dias que ya llegaron: una fecha futura en el sitemap no es valida."""
    import datetime
    hoy = datetime.date.today().isoformat()
    lm = lambda f: "<lastmod>%s</lastmod>" % f if f <= hoy else ""
    pasados = [f for f in fechas if f <= hoy]
    rows = ['  <url><loc>%s%s</loc>%s</url>' % (SITE, INDEX_NAME, lm(max(pasados)) if pasados else "")]
    for f in sorted(fechas, reverse=True):
        rows.append('  <url><loc>%s%s</loc>%s</url>' % (SITE, page_name(f), lm(f)))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def main():
    dias = {}
    for path in sorted(glob.glob(os.path.join(SRC, "*.yml"))):
        name = os.path.splitext(os.path.basename(path))[0]
        with io.open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        if d.get("draft"):
            continue
        fecha = str(d.get("fecha", ""))
        if not FECHA.match(fecha) or fecha != name:
            sys.exit("ERROR: %s: 'fecha' debe ser AAAA-MM-DD y coincidir con el nombre del archivo" % path)
        if not d.get("lecturas"):
            sys.exit("ERROR: %s: falta 'lecturas'" % path)
        try:
            _fecha_parts(fecha)
        except ValueError:
            sys.exit("ERROR: %s: fecha inexistente" % path)
        dias[fecha] = {
            "celebracion": d.get("celebracion", ""),
            "santo": d.get("santo", ""),
            "fuente": d.get("fuente", ""),
            "url": page_name(fecha),
            "lecturas": [_lectura(l) for l in d["lecturas"]],
        }
    data = json.dumps({"dias": dias}, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    wr(OUT, data)
    print("lecturas.json: %d día(s)" % len(dias))

    # Paginas por dia: necesitan el chrome del sitio (lecturas-para-el-uruguay.html, que
    # genera build.py). Si falta (p. ej. en el workflow del CMS) se deja lo que ya existe.
    if not os.path.exists(TEMPLATE):
        print("  (sin %s: no se regeneran las páginas por día)" % os.path.basename(TEMPLATE))
        return
    tpl = rd(TEMPLATE)
    fechas = sorted(dias)
    escritos = set()
    for i, f in enumerate(fechas):
        prev_f = fechas[i - 1] if i > 0 else None
        next_f = fechas[i + 1] if i + 1 < len(fechas) else None
        if wr(os.path.join(ROOT, page_name(f)), day_page(tpl, f, dias[f], prev_f, next_f)):
            print("  escrito: %s" % page_name(f))
        escritos.add(page_name(f))
    if fechas:
        if wr(os.path.join(ROOT, INDEX_NAME), index_page(tpl, dias)):
            print("  escrito: %s" % INDEX_NAME)
        escritos.add(INDEX_NAME)
        wr(SITEMAP, sitemap(fechas))
    # paginas generadas que ya no corresponden (dia borrado o en borrador)
    for path in glob.glob(os.path.join(ROOT, "lecturas-de-la-misa*.html")):
        name = os.path.basename(path)
        if name not in escritos and GEN_MARK in rd(path)[:2000]:
            os.remove(path)
            print("  eliminado (obsoleto): %s" % name)
    if not fechas and os.path.exists(SITEMAP):
        os.remove(SITEMAP)


if __name__ == "__main__":
    main()
