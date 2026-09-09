#!/usr/bin/env python3
# Patches index.html, injects shared SVG defs into vision.html,
# and emits standalone repo/ copies for GitHub Pages.
import io, re, sys

HOME = "https://avvedit-creator.github.io/resurgirnacionaluy/"
VISION_ABS = HOME + "vision.html"

def rd(p): return io.open(p, encoding="utf-8").read()
def wr(p, s): io.open(p, "w", encoding="utf-8", newline="\n").write(s)

idx = rd("index.html")

# --- extract the shared <svg> defs block (emblem/flag/saltire, with data URIs) ---
d0 = idx.index("<!-- Marcas de marca")
d1 = idx.index("</svg>", d0) + len("</svg>")
defs = idx[d0:d1]

# ---------------- patch index.html ----------------
if 'href="%svision.html"' % HOME not in idx:
    idx = idx.replace(
        '      <a href="#ideario">Ideario</a>\n      <a href="#propuestas">Propuestas</a>',
        '      <a href="#ideario">Ideario</a>\n      <a href="%svision.html">Visión</a>\n      <a href="#propuestas">Propuestas</a>' % HOME, 1)
    idx = idx.replace(
        '        <a href="#ideario">Ideario</a>\n        <a href="#propuestas">Propuestas</a>',
        '        <a href="#ideario">Ideario</a>\n        <a href="%svision.html">Visión</a>\n        <a href="#propuestas">Propuestas</a>' % HOME, 1)

idx = idx.replace(
    '<p class="label hero__eyebrow">Movimiento cívico-patriótico · Uruguay</p>',
    '<p class="label hero__eyebrow">Movimiento nacionalista · Tercera Posición · Uruguay</p>')
idx = idx.replace(
    '<p class="hero__lead">Soberanía, trabajo propio e instituciones limpias. Un proyecto para devolver a los uruguayos el gobierno de su país.</p>',
    '<p class="hero__lead">La regeneración política, cultural y social del Uruguay. Que Dios, la Patria y la Familia vuelvan a ser la base de la sociedad.</p>')
idx = idx.replace(
    '<a class="btn btn--light" href="#ideario">Lee el ideario</a>',
    '<a class="btn btn--light" href="%svision.html">Lee nuestra visión</a>' % HOME)

idx = idx.replace(
    'Resurgir Nacional — movimiento cívico-patriótico del Uruguay. [Naturaleza jurídica y, en su caso, inscripción ante la Corte Electoral con número —]. Sede: [dirección]. Contacto: [correo]. Financiación conforme a la Ley N.º 18.485.',
    'Resurgir Nacional — movimiento nacionalista del Uruguay. Contacto: resurgirnacionaluruguay@gmail.com · resurgirnacional@proton.me. [Naturaleza jurídica pendiente de definición.]')

# CSS for the value list
idx = idx.replace("\n</style>", """
  /* ---------- Lista de valores (resumen) ---------- */
  .vlist { margin-top: 1.6rem; max-width: 780px; columns: 2; column-gap: 2.75rem; }
  .vlist li { break-inside: avoid; padding: 0.7rem 0; border-top: 1px solid var(--line); }
  .vlist b { font-family: "Fraunces", serif; font-weight: 500; display: block; }
  .vlist span { color: var(--ink-soft); font-size: 0.9rem; }
  @media (max-width: 620px) { .vlist { columns: 1; } }
</style>""", 1)

# Replace the provisional ideario block
idx = re.sub(
    r'<div class="band__head">\s*<span class="label">Ideario</span>.*?</ol>',
    '''<div class="band__head">
        <span class="label">Ideario</span>
        <h2>Dios, Patria y Familia</h2>
        <p>Resurgir Nacional busca la regeneración política, cultural y social del Uruguay desde una Tercera Posición: fuera de la vieja disputa de izquierdas y derechas y del dogma democrático liberal. Estos son los doce valores que nos guían.</p>
      </div>
      <ul class="vlist">
        <li><b>Orgullo Nacional</b><span>Un Uruguay soberano que protege su identidad y su historia.</span></li>
        <li><b>Valores Cristianos</b><span>La fe cristiana como guía para vivir con justicia y dignidad.</span></li>
        <li><b>Familia, pilar de la Nación</b><span>Núcleo de la sociedad y base de un futuro próspero.</span></li>
        <li><b>Salud y fortaleza física</b><span>Vida sana, alimentación natural y vigor espiritual.</span></li>
        <li><b>Defensa de la tierra</b><span>Ganadería tradicional y soberanía alimentaria.</span></li>
        <li><b>Resistencia al globalismo</b><span>Frente a la ideología de género y la descomposición cultural.</span></li>
        <li><b>Unidad y solidaridad nacional</b><span>Comunidad y colaboración por un Uruguay unido.</span></li>
        <li><b>Disciplina</b><span>Trabajo con perseverancia y determinación.</span></li>
        <li><b>Preservación cultural</b><span>Defensa del legado y las tradiciones nacionales.</span></li>
        <li><b>Anti-liberalismo</b><span>Todo orden político subordinado a un orden superior.</span></li>
        <li><b>Anti-marxismo</b><span>Frente al materialismo, una concepción espiritual del mundo.</span></li>
        <li><b>Anti-democratismo liberal</b><span>La raíz del mal está en el sistema político imperante.</span></li>
      </ul>
      <p style="margin-top:2rem"><a class="btn" href="%svision.html">Lee la visión completa</a></p>''' % HOME,
    idx, count=1, flags=re.S)

wr("index.html", idx)

# ---------------- inject defs into vision.html ----------------
vis = rd("vision.html").replace("<!--DEFS-->", defs, 1)
wr("vision.html", vis)

# ---------------- emit standalone repo/ copies ----------------
HEAD = ('<!doctype html>\n<html lang="es">\n<head>\n'
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        '<meta name="theme-color" content="#14315C" />\n'
        '<style>*{box-sizing:border-box}img{max-width:100%;height:auto}[hidden]{display:none!important}</style>\n')

def to_repo(src):
    s = src
    s = s.replace(VISION_ABS, "vision.html")
    s = s.replace(HOME + "#", "index.html#")
    s = s.replace('href="' + HOME + '"', 'href="index.html"')
    s = s.replace(HOME, "index.html")  # any stragglers
    hb = s.index("</style>") + len("</style>")
    return HEAD + s[:hb] + "\n</head>\n<body style=\"margin:0\">\n" + s[hb:] + "\n</body>\n</html>\n"

wr("repo/index.html", to_repo(rd("index.html")))
wr("repo/vision.html", to_repo(rd("vision.html")))
print("built: index.html, vision.html, repo/index.html, repo/vision.html")
