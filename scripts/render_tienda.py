#!/usr/bin/env python3
"""Render Tienda (merchandising y libros a la venta, pago via PayPal).

Lee content/tienda/*.yml (subidos por el CMS o a mano), genera una pagina
standalone <slug>.html por producto (reusa el chrome de
tienda-resurgir-nacional.html, igual que render_biblioteca.py con
Biblioteca) y reescribe la grilla de productos entre los marcadores
<!-- PRODUCTS:START --> / <!-- PRODUCTS:END --> dentro de
tienda-resurgir-nacional.html.

Tambien escribe tienda-manifest.json en la raiz del repo: un catalogo
publico (slug/titulo/precio/tipo/stock, sin secretos) que el Worker de pago
usa como fuente de verdad de los precios -- el carrito del navegador NUNCA
le dice el precio al servidor, asi nadie puede pagar de menos manipulando
el JS. Ver workers/tienda-api/.

Correr desde la raiz del repo:  python scripts/render_tienda.py
Pure stdlib + `yaml` + og_image.py (Pillow) para la portada social.
"""
import io, os, re, sys, json, glob

import yaml

import og_image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content", "tienda")
TEMPLATE = os.path.join(ROOT, "tienda-resurgir-nacional.html")
MANIFEST = os.path.join(ROOT, "tienda-manifest.json")
OG_DIR = os.path.join(ROOT, "og")
SITE = "https://resurgirnacionaluy.org/"
MARK_A = "<!-- PRODUCTS:START -->"
MARK_B = "<!-- PRODUCTS:END -->"
GEN_MARK = "<!-- generated:tienda-product -->"
RESERVED = {"index", "vision", "formacion", "sagradocorazondejesus", "biblioteca",
            "admin", "404", "readme", "articulos",
            "ideario-y-valores-rn", "catolicismo-en-uruguay", "cultura-nacional-uruguaya",
            "lecturas-para-el-uruguay", "tienda-resurgir-nacional"}

TYPE_LABELS = {
    "merch": "Merchandising",
    "libro_digital": "Libro digital",
    "libro_fisico": "Libro físico",
}


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


def fmt_price(price):
    """PayPal no admite cobrar en pesos uruguayos: el precio se carga y se
    cobra en dolares (USD), con dos decimales."""
    try:
        return "%.2f" % float(price)
    except (TypeError, ValueError):
        return "0.00"


def variant_list(p):
    raw = (p.get("variant_options") or "").strip()
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


def load_products():
    products = []
    # Sveltia CMS puede guardar estos archivos como .yml o .yaml segun la
    # config (ver el bug ya conocido con Biblioteca) -- se leen ambas.
    paths = glob.glob(os.path.join(CONTENT, "*.yml")) + glob.glob(os.path.join(CONTENT, "*.yaml"))
    for path in sorted(paths):
        slug = os.path.splitext(os.path.basename(path))[0].lower()
        slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-")
        if not slug or slug in RESERVED:
            print("  skip (slug reservado/invalido): %s" % path)
            continue
        p = yaml.safe_load(rd(path)) or {}
        if not isinstance(p, dict):
            continue
        if p.get("draft") in (True, "true", "True"):
            print("  skip (borrador): %s" % slug)
            continue
        if not p.get("title") or p.get("price") in (None, ""):
            print("  skip (falta titulo o precio): %s" % slug)
            continue
        if p.get("type") not in TYPE_LABELS:
            print("  skip (tipo invalido): %s" % slug)
            continue
        p["slug"] = slug
        p["images"] = p.get("images") or []
        products.append(p)
    products.sort(key=lambda p: p.get("title", ""))
    return products


def meta_line(p):
    return "%s · US$ %s" % (TYPE_LABELS.get(p["type"], p["type"]), fmt_price(p["price"]))


def og_name(slug):
    # prefijo "producto-" para no compartir namespace con og/<slug>.jpg de
    # Formacion ni og/libro-<slug>.jpg de Biblioteca (mismo directorio og/,
    # limpiezas separadas).
    return "producto-" + slug + ".jpg"


def write_og_image(p):
    """Genera og/producto-<slug>.jpg con el titulo real del producto (si cambio)."""
    out = os.path.join(OG_DIR, og_name(p["slug"]))
    tmp = out + ".tmp"
    og_image.make_og_image("Tienda", p["title"], meta_line(p), tmp,
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


def variant_select_html(p, idprefix=""):
    opts = variant_list(p)
    if not opts:
        return ""
    label = p.get("variant_label") or "Opción"
    rows = "\n".join('          <option value="%s">%s</option>' % (esc(o), esc(o)) for o in opts)
    return (
        '      <label class="sr-only" for="%svariant-%s">%s</label>\n'
        '      <select class="shop-card__variant" id="%svariant-%s">\n%s\n      </select>\n'
        % (idprefix, p["slug"], esc(label), idprefix, p["slug"], rows)
    )


def add_button_html(p, extra_class=""):
    img = p["images"][0] if p["images"] else ""
    return (
        '      <button type="button" class="btn btn--rounded shop-add %s" '
        'data-slug="%s" data-title="%s" data-price="%s" data-image="%s">'
        'Agregar al carrito</button>\n'
        % (extra_class, esc(p["slug"]), esc(p["title"]), esc(p["price"]), esc(img))
    )


def product_page(tpl, p):
    title = p["title"]
    summary = p.get("summary", "") or title
    lead = meta_line(p)
    images = p["images"]
    product_url = SITE + p["slug"] + ".html"
    pre = tpl[:tpl.index("<main>")]
    post = tpl[tpl.index("</main>") + len("</main>"):]
    pre = re.sub(r"<title>.*?</title>", lambda m: "<title>%s · Tienda · Resurgir Nacional</title>" % esc(title), pre, count=1, flags=re.S)
    pre = pre.replace(SITE + "tienda-resurgir-nacional.html", product_url)  # canonical, hreflang, og:url
    pre = re.sub(r'(<meta name="description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(summary) + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(title) + m.group(2), pre, count=1)
    pre = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(summary) + m.group(2), pre, count=1)
    pre = re.sub(r'<meta property="og:image" content="[^"]*" />',
                 '<meta property="og:image" content="%sog/%s" />' % (SITE, og_name(p["slug"])),
                 pre, count=1)
    pre = pre.replace("<head>", "<head>\n" + GEN_MARK, 1)

    gallery = ""
    if images:
        main_img = '<img src="%s" alt="%s" style="width:100%%;max-width:32rem;border-radius:8px" />' % (esc(images[0]), esc(title))
        thumbs = "".join(
            '<img src="%s" alt="" style="width:4.5rem;height:4.5rem;object-fit:cover;border-radius:4px;margin:0.5rem 0.5rem 0 0" />' % esc(im)
            for im in images[1:]
        )
        gallery = '<div style="margin-top:1rem">%s<div>%s</div></div>' % (main_img, thumbs)

    description = p.get("description") or ""
    desc_html = ("<p>%s</p>" % esc(description)) if description else ""
    pages = p.get("pages")
    if pages:
        desc_html += "<p class=\"muted\">%s páginas</p>" % esc(pages)

    variant_html = variant_select_html(p, idprefix="pp-")
    stock = p.get("stock")
    stock_note = ""
    if stock is not None and str(stock).strip() != "":
        try:
            if int(stock) <= 0:
                stock_note = '<p class="muted" style="margin-top:0.6rem">Sin stock por el momento — escribinos si querés que te avisemos.</p>'
        except (TypeError, ValueError):
            pass

    main_html = (
        '<main>\n'
        '  <article class="doc">\n'
        '    <section>\n'
        '      <span class="label">Tienda · %s</span>\n'
        '      <h1>%s</h1>\n'
        '      <p class="doc-lead">%s</p>\n'
        '      <button type="button" class="share-btn" aria-label="Compartir este producto">'
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>'
        'Compartir</button>\n'
        '    </section>\n'
        '    <section>\n'
        '      %s\n'
        '      <div class="prose">%s</div>\n'
        '      <div class="shop-card" style="max-width:22rem;margin-top:1.6rem;border:none;background:none">\n'
        '%s'
        '%s'
        '      </div>\n'
        '      %s\n'
        '      <p style="margin-top:2.5rem"><a href="tienda-resurgir-nacional.html">← Volver a la Tienda</a></p>\n'
        '    </section>\n'
        '  </article>\n'
        '</main>' % (
            esc(TYPE_LABELS.get(p["type"], p["type"])), esc(title), esc(lead),
            gallery, desc_html, variant_html, add_button_html(p), stock_note,
        )
    )
    return pre + main_html + post


def cards_block(products):
    if not products:
        return ""
    rows = []
    for p in products:
        img = p["images"][0] if p["images"] else ""
        img_html = ('<img src="%s" alt="" loading="lazy" />' % esc(img)) if img else ""
        rows.append(
            '        <div class="shop-card">\n'
            '          <a class="shop-card__media" href="%s.html">%s</a>\n'
            '          <div class="shop-card__body">\n'
            '            <span class="shop-card__kind">%s</span>\n'
            '            <a class="shop-card__title" href="%s.html">%s</a>\n'
            '%s'
            '            <span class="shop-card__price">US$ %s</span>\n'
            '%s'
            '          </div>\n'
            '        </div>' % (
                p["slug"], img_html,
                esc(TYPE_LABELS.get(p["type"], p["type"])),
                p["slug"], esc(p["title"]),
                variant_select_html(p),
                fmt_price(p["price"]),
                add_button_html(p),
            )
        )
    return "\n" + "\n".join(rows) + "\n        "


def write_manifest(products):
    # Publico (sin secretos): el Worker de pago lo usa como fuente de verdad
    # de precios, para que el carrito del navegador nunca le diga el precio
    # al servidor. asset_key (solo libros digitales) es la clave del objeto
    # en R2 -- exponerla no da acceso a nadie sin el binding del Worker, asi
    # que es segura de publicar junto al resto.
    data = [
        {
            "slug": p["slug"],
            "title": p["title"],
            "price": float(p["price"]),
            "type": p["type"],
            "stock": p.get("stock"),
            "variants": variant_list(p),
            "digital": p["type"] == "libro_digital",
            "asset_key": p.get("digital_asset_key") or None,
        }
        for p in products
    ]
    new_json = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if not os.path.exists(MANIFEST) or rd(MANIFEST) != new_json:
        wr(MANIFEST, new_json)
        print("  tienda-manifest.json: actualizado (%d productos)" % len(products))


def main():
    if not os.path.isdir(CONTENT):
        os.makedirs(CONTENT, exist_ok=True)
    if not os.path.exists(TEMPLATE):
        print("ERROR: falta tienda-resurgir-nacional.html (correr tools/build.py primero)")
        return 1
    tpl = rd(TEMPLATE)
    if MARK_A not in tpl or MARK_B not in tpl:
        print("ERROR: faltan los marcadores PRODUCTS en tienda-resurgir-nacional.html")
        return 1

    # Salvaguarda: cualquier archivo en content/tienda/ que no sea .yml/.yaml
    # queda invisible para load_products() sin ningun aviso -- el mismo bug
    # que dejo sin publicar un libro de Biblioteca (extension ".yaml" vs
    # ".yml"). En vez de fallar en silencio, esto corta el build con un
    # error bien visible en el log de GitHub Actions.
    known_ext = {".yml", ".yaml"}
    unmatched = [f for f in os.listdir(CONTENT)
                 if not f.startswith(".") and os.path.splitext(f)[1].lower() not in known_ext]
    if unmatched:
        print("ERROR: archivos en content/tienda/ con extension no reconocida (no se van a publicar):")
        for f in sorted(unmatched):
            print("  - %s" % f)
        return 1

    products = load_products()

    written = set()
    for p in products:
        out = os.path.join(ROOT, p["slug"] + ".html")
        page = product_page(tpl, p)
        if not os.path.exists(out) or rd(out) != page:
            wr(out, page)
            print("  escrito: %s.html" % p["slug"])
        if write_og_image(p):
            print("  og/%s: imagen social actualizada" % og_name(p["slug"]))
        written.add(p["slug"] + ".html")

    # remove stale generated product pages
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

    # remove stale per-product OG images (solo las propias: prefijo "producto-")
    slugs = {p["slug"] for p in products}
    if os.path.isdir(OG_DIR):
        for path in glob.glob(os.path.join(OG_DIR, "producto-*.jpg")):
            slug = os.path.basename(path)[len("producto-"):-len(".jpg")]
            if slug not in slugs:
                os.remove(_lp(path))
                print("  eliminado (obsoleto): og/%s" % os.path.basename(path))

    i = tpl.index(MARK_A) + len(MARK_A)
    j = tpl.index(MARK_B)
    new_tpl = tpl[:i] + cards_block(products) + tpl[j:]
    if new_tpl != tpl:
        wr(TEMPLATE, new_tpl)
        print("  tienda-resurgir-nacional.html: grilla actualizada (%d productos)" % len(products))
    else:
        print("  tienda-resurgir-nacional.html: sin cambios (%d productos)" % len(products))

    write_manifest(products)
    return 0


if __name__ == "__main__":
    sys.exit(main())
