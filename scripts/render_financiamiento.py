#!/usr/bin/env python3
"""Render Financiamiento (iniciativas con meta y resumen general).

Lee content/pages/financiamiento.yml (editable desde el CMS) y genera
financiamiento.html en la raiz del repo. Reusa el chrome de
ideario-y-valores-rn.html (header, footer, estilos, SEO), igual que
render_tienda.py reusa el de la Tienda: solo reemplaza el <main> y agrega
los estilos propios de esta pagina.

La pagina es publica y el repo tambien, asi que solo maneja totales:
- Iniciativas: meta, total recaudado, cantidad de aportes y los nombres de
  quienes eligieron figurar (sin montos individuales). Las logradas pasan a
  su propia seccion con el resultado.
- Resumen: de donde viene y en que se usa el dinero, en porcentajes.
El detalle completo (cada aporte y cada gasto) queda en la planilla interna
de los miembros, nunca en este repositorio.

Los botones de aportar usan los mismos links de PayPal y Ko-fi (y la cuenta
Prex) que la seccion Colaborar de la portada (content/pages/home.yml). Las
iniciativas abiertas tambien se muestran, resumidas, en esa seccion de
index.html, entre los marcadores <!-- EVENTOS:START --> / <!-- EVENTOS:END -->.

Correr desde la raiz del repo:  python scripts/render_financiamiento.py
Pure stdlib + `yaml`.
"""
import io, os, re, sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "content", "pages", "financiamiento.yml")
HOME_DATA = os.path.join(ROOT, "content", "pages", "home.yml")
TEMPLATE = os.path.join(ROOT, "ideario-y-valores-rn.html")
OUT_NAME = "financiamiento.html"
OUT = os.path.join(ROOT, OUT_NAME)
HOME_PAGE = os.path.join(ROOT, "index.html")
HOME_MARK_A = "<!-- EVENTOS:START -->"
HOME_MARK_B = "<!-- EVENTOS:END -->"
SITE = "https://resurgirnacionaluy.org/"
GEN_MARK = "<!-- generated:financiamiento -->"
TITLE = "Financiamiento"
DESCRIPTION = "Iniciativas de Resurgir Nacional con meta a la vista, y de dónde viene y en qué se usa el dinero del movimiento."

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "setiembre", "octubre", "noviembre", "diciembre"]

# intensidad de cada segmento del resumen (mismo tono, de mas a menos)
SHADES = [100, 70, 48, 32, 20, 12]

STYLE = """
<style>
  /* Financiamiento */
  .fin-notice { border: 1px solid var(--gold-line); background: color-mix(in srgb, var(--gold-line) 12%, transparent); border-radius: 8px; padding: 0.9rem 1.1rem; font-family: "Archivo", system-ui, sans-serif; font-size: 0.9rem; color: var(--ink); max-width: var(--measure); margin-bottom: 1.4rem; }
  .fin-notice strong { color: var(--gold-text); letter-spacing: 0.08em; text-transform: uppercase; font-size: 0.78rem; margin-right: 0.4rem; }
  .fin-inis { display: grid; gap: 1.5rem; margin-top: 1.6rem; }
  .fin-ini { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
  .fin-ini--img { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); }
  .fin-ini__img { width: 100%; height: 100%; min-height: 14rem; object-fit: cover; display: block; background: var(--line); }
  .fin-ini__body { padding: clamp(1.25rem, 3vw, 2rem); }
  .fin-ini h3 { font-size: var(--step-1); }
  .fin-ini__date { font-family: "Archivo", system-ui, sans-serif; font-size: 0.9rem; color: var(--gold-text); font-weight: 600; margin-top: 0.35rem; }
  .fin-ini__desc { margin-top: 0.8rem; max-width: var(--measure); }
  .fin-goal { margin-top: 1.4rem; }
  .fin-goal__nums { display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap; font-variant-numeric: tabular-nums; }
  .fin-goal__raised { font-family: "Fraunces", Georgia, serif; font-size: var(--step-2); line-height: 1.1; }
  .fin-goal__of { font-family: "Archivo", system-ui, sans-serif; color: var(--ink-soft); font-size: 0.95rem; }
  .fin-goal__track { height: 0.9rem; background: var(--line); border-radius: 999px; margin-top: 0.7rem; overflow: hidden; }
  .fin-goal__fill { display: block; height: 100%; border-radius: 999px; background: var(--blue); }
  .fin-goal__foot { display: flex; justify-content: space-between; gap: 0.4rem 1rem; flex-wrap: wrap; margin-top: 0.55rem; font-family: "Archivo", system-ui, sans-serif; font-size: 0.9rem; color: var(--ink-soft); font-variant-numeric: tabular-nums; }
  .fin-goal__foot strong { color: var(--ink); }
  .fin-give { margin-top: 1.5rem; display: flex; gap: 0.75rem; flex-wrap: wrap; }
  .fin-give .btn--alt { background: transparent; color: var(--blue); border-color: var(--blue); }
  .fin-give .btn--alt:hover { background: color-mix(in srgb, var(--blue) 10%, transparent); }
  .fin-prex { margin-top: 1rem; display: flex; align-items: center; gap: 0.4rem 0.7rem; flex-wrap: wrap; font-family: "Archivo", system-ui, sans-serif; font-size: 0.95rem; }
  .fin-prex strong { font-variant-numeric: tabular-nums; letter-spacing: 0.04em; }
  .fin-copy { font: inherit; font-size: 0.85rem; font-weight: 600; padding: 0.3rem 0.75rem; border-radius: 999px; border: 1px solid var(--line); background: var(--bg); color: var(--blue); cursor: pointer; }
  .fin-copy:hover { border-color: var(--blue); }
  .fin-give__hint { margin-top: 0.8rem; font-size: 0.95rem; color: var(--ink-soft); max-width: var(--measure); }
  .fin-thanks { margin-top: 1.4rem; padding-top: 1rem; border-top: 1px solid var(--line); font-size: 1rem; color: var(--ink-soft); }
  .fin-thanks strong { color: var(--ink); font-family: "Archivo", system-ui, sans-serif; font-weight: 600; }
  .fin-empty { margin-top: 1.6rem; border: 1px dashed var(--line); border-radius: 8px; padding: 1.25rem; max-width: var(--measure); color: var(--ink-soft); }
  .fin-empty strong { display: block; color: var(--ink); font-family: "Fraunces", Georgia, serif; font-weight: 500; font-size: var(--step-1); margin-bottom: 0.3rem; }
  .fin-done { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 17rem), 1fr)); gap: 1rem; margin-top: 1.4rem; }
  .fin-done__card { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
  .fin-done__card img { width: 100%; aspect-ratio: 16 / 9; object-fit: cover; display: block; background: var(--line); }
  .fin-done__body { padding: 1rem 1.15rem 1.2rem; }
  .fin-done__tag { font-family: "Archivo", system-ui, sans-serif; font-weight: 600; font-size: var(--step--1); letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold-text); }
  .fin-done__card h3 { font-size: var(--step-1); margin-top: 0.3rem; }
  .fin-done__meta { font-family: "Archivo", system-ui, sans-serif; font-size: 0.88rem; color: var(--ink-soft); margin-top: 0.35rem; font-variant-numeric: tabular-nums; }
  .fin-done__card p.fin-done__result { margin-top: 0.6rem; font-size: 1rem; line-height: 1.55; }
  .fin-split { display: flex; height: 0.9rem; border-radius: 999px; overflow: hidden; margin-top: 1.6rem; background: var(--line); }
  .fin-split span { display: block; height: 100%; }
  .fin-split span + span { border-left: 2px solid var(--bg); }
  .fin-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr)); gap: 1rem; margin-top: 1.4rem; }
  .fin-card { background: var(--surface); border: 1px solid var(--line); border-top: 3px solid var(--gold-line); border-radius: 8px; padding: 1.1rem 1.25rem 1.25rem; }
  .fin-cards--out .fin-card { border-top-color: var(--blue); }
  .fin-card__num { display: inline-flex; align-items: center; gap: 0.45rem; font-family: "Archivo", system-ui, sans-serif; font-weight: 600; font-size: var(--step--1); letter-spacing: 0.14em; color: var(--gold-text); }
  .fin-cards--out .fin-card__num { color: var(--blue); }
  .fin-card__num--pct { font-family: "Fraunces", Georgia, serif; font-weight: 500; font-size: var(--step-2); letter-spacing: 0; color: var(--ink); }
  .fin-cards--out .fin-card__num--pct { color: var(--ink); }
  .fin-swatch { width: 0.75rem; height: 0.75rem; border-radius: 3px; flex: none; }
  .fin-card h3 { font-size: var(--step-1); margin-top: 0.35rem; }
  .fin-card p { margin-top: 0.45rem; color: var(--ink-soft); font-size: 1rem; line-height: 1.55; }
  .fin-period { font-family: "Archivo", system-ui, sans-serif; color: var(--ink-soft); font-size: 0.9rem; margin-top: 0.4rem; }
  .fin-members { margin-top: 2rem; display: flex; gap: 0.8rem; align-items: flex-start; max-width: var(--measure); padding: 1rem 1.15rem; border-radius: 8px; background: color-mix(in srgb, var(--blue) 8%, transparent); border: 1px solid color-mix(in srgb, var(--blue) 30%, transparent); font-size: 1rem; }
  .fin-members svg { width: 1.2rem; height: 1.2rem; flex: none; margin-top: 0.25rem; fill: var(--blue); }
  @media (max-width: 720px) {
    .fin-ini--img { grid-template-columns: 1fr; }
    .fin-ini__img { min-height: 0; aspect-ratio: 16 / 9; }
  }
</style>
"""

# "Quedan N dias" a partir de la fecha limite (el HTML trae la fecha fija como
# respaldo sin JS) y botones "Copiar numero" de la cuenta Prex. El aviso usa
# .copy-toast, cuyos estilos ya trae la plantilla.
PAGE_JS = """  <script>
  (function () {
    var DAY = 86400000;
    [].forEach.call(document.querySelectorAll('[data-deadline]'), function (el) {
      var p = el.getAttribute('data-deadline').split('-');
      var end = new Date(+p[0], +p[1] - 1, +p[2], 23, 59, 59);
      var left = Math.ceil((end - new Date()) / DAY);
      if (left > 1) el.textContent = 'Quedan ' + left + ' días';
      else if (left === 1) el.textContent = 'Último día';
      else if (left <= 0) el.textContent = 'Plazo cumplido';
    });

    var btns = document.querySelectorAll('.fin-copy');
    if (!btns.length) return;
    var toast = document.createElement('div');
    toast.className = 'copy-toast';
    toast.setAttribute('role', 'status');
    toast.textContent = 'Número de cuenta copiado';
    document.body.appendChild(toast);
    var t;
    function ping() {
      toast.classList.add('is-on');
      clearTimeout(t);
      t = setTimeout(function () { toast.classList.remove('is-on'); }, 1600);
    }
    function fallback(str) {
      var ta = document.createElement('textarea');
      ta.value = str; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.top = '-1000px';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
      ping();
    }
    [].forEach.call(btns, function (b) {
      b.addEventListener('click', function () {
        var v = b.getAttribute('data-copy');
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(v).then(ping, function () { fallback(v); });
        } else { fallback(v); }
      });
    });
  })();
  </script>
"""

LOCK_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 1a5 5 0 0 0-5 5v3H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 '
             '2-2V11a2 2 0 0 0-2-2h-1V6a5 5 0 0 0-5-5zm-3 8V6a3 3 0 1 1 6 0v3H9z"/></svg>')


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def esc(s):
    import html
    return html.escape(str(s), quote=True)


def money(n, cur):
    """Formato uruguayo: punto como separador de miles, sin decimales."""
    sign = "−" if n < 0 else ""
    return "%s%s %s" % (sign, cur, "{:,.0f}".format(abs(n)).replace(",", "."))


def fecha(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s or ""))
    if not m:
        return str(s or "")
    return "%d de %s de %s" % (int(m.group(3)), MESES[int(m.group(2)) - 1], m.group(1))


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _true(v):
    return v in (True, "true", "True")


def load():
    d = yaml.safe_load(rd(DATA)) or {}
    d["moneda"] = d.get("moneda") or "$"

    inis = []
    for e in d.get("iniciativas") or []:
        if not isinstance(e, dict) or not e.get("nombre"):
            continue
        e["meta"] = _num(e.get("meta")) or 0.0
        e["recaudado"] = _num(e.get("recaudado")) or 0.0
        e["aportes"] = int(_num(e.get("aportes")) or 0)
        e["nombres"] = [str(n).strip() for n in (e.get("nombres") or []) if str(n or "").strip()]
        e["lograda"] = _true(e.get("lograda"))
        inis.append(e)
    d["iniciativas"] = inis

    for k in ("fuentes", "usos"):
        rows = []
        for r in d.get(k) or []:
            if isinstance(r, dict) and r.get("nombre"):
                r["porcentaje"] = _num(r.get("porcentaje"))
                rows.append(r)
        d[k] = rows
        total = sum(r["porcentaje"] or 0 for r in rows)
        if total and abs(total - 100) > 1:
            print("  AVISO: los porcentajes de %s suman %g, no 100" % (k, total))

    home = yaml.safe_load(rd(HOME_DATA)) if os.path.exists(HOME_DATA) else {}
    home = home if isinstance(home, dict) else {}
    d["give_links"] = [(label, home[k]) for label, k in
                       (("Aportar por PayPal", "aporta_paypal"), ("Aportar por Ko-fi", "aporta_kofi"))
                       if home.get(k)]
    d["prex"] = str(home.get("aporta_prex") or "").strip()
    return d


def progress(e):
    pct = min(100.0, e["recaudado"] / e["meta"] * 100) if e["meta"] else 0.0
    return pct, max(0.0, e["meta"] - e["recaudado"])


def thanks(e):
    n = e["aportes"]
    if not n:
        return "Todavía no hay aportes: el primero puede ser el tuyo."
    head = "<strong>%d %s</strong>" % (n, "aporte" if n == 1 else "aportes")
    names = e["nombres"]
    if not names:
        return head + ". ¡Gracias!"
    rest = max(0, n - len(names))
    shown = ", ".join(esc(x) for x in names)
    if rest:
        shown += " y %d %s" % (rest, "persona más" if rest == 1 else "personas más")
    elif len(names) > 1:
        shown = ", ".join(esc(x) for x in names[:-1]) + " y " + esc(names[-1])
    return "%s. Gracias a %s." % (head, shown)


def open_card(e, d):
    cur = d["moneda"]
    pct, falta = progress(e)
    img = e.get("imagen") or ""
    date = ('        <p class="fin-ini__date" data-deadline="%s">Hasta el %s</p>\n'
            % (esc(e["fecha_limite"]), esc(fecha(e["fecha_limite"])))) if e.get("fecha_limite") else ""
    desc = ('        <p class="fin-ini__desc">%s</p>\n' % esc(e["descripcion"])) if e.get("descripcion") else ""
    status = ("Faltan <strong>%s</strong>" % money(falta, cur)) if falta else "<strong>¡Meta alcanzada!</strong> Gracias a todos."

    give = ""
    if falta and (d["give_links"] or d["prex"]):
        buttons = "".join(
            '<a class="btn btn--rounded%s" href="%s" target="_blank" rel="noopener">%s</a>'
            % ("" if i == 0 else " btn--alt", esc(url), esc(label))
            for i, (label, url) in enumerate(d["give_links"])
        )
        prex = (
            '        <p class="fin-prex">Por Prex, a la cuenta <strong>%s</strong> '
            '<button type="button" class="fin-copy" data-copy="%s">Copiar número</button></p>\n'
            % (esc(d["prex"]), esc(d["prex"]))
        ) if d["prex"] else ""
        give = (
            '%s%s'
            '        <p class="fin-give__hint">En el mensaje o concepto del pago escribí «%s» y, si querés '
            'figurar en los agradecimientos, tu nombre. Sin nombre, tu aporte suma igual.</p>\n'
            % (('        <div class="fin-give">%s</div>\n' % buttons) if buttons else "", prex, esc(e["nombre"]))
        )

    body = (
        '      <div class="fin-ini__body">\n'
        '        <h3>%s</h3>\n%s%s'
        '        <div class="fin-goal">\n'
        '          <div class="fin-goal__nums"><span class="fin-goal__raised">%s</span><span class="fin-goal__of">de %s</span></div>\n'
        '          <div class="fin-goal__track" role="progressbar" aria-label="Recaudado para %s" aria-valuemin="0" aria-valuemax="%d" aria-valuenow="%d">'
        '<span class="fin-goal__fill" style="width:%.1f%%"></span></div>\n'
        '          <div class="fin-goal__foot"><span>%d%% de la meta</span><span>%s</span></div>\n'
        '        </div>\n%s'
        '        <p class="fin-thanks">%s</p>\n'
        '      </div>\n' % (
            esc(e["nombre"]), date, desc,
            money(e["recaudado"], cur), money(e["meta"], cur),
            esc(e["nombre"]), e["meta"], min(e["recaudado"], e["meta"]), pct,
            round(pct), status, give, thanks(e),
        )
    )
    if img:
        return ('      <article class="fin-ini fin-ini--img">\n'
                '        <img class="fin-ini__img" src="%s" alt="" loading="lazy" />\n%s'
                '      </article>' % (esc(img), body))
    return '      <article class="fin-ini">\n%s      </article>' % body


def done_card(e, cur):
    img = e.get("resultado_imagen") or e.get("imagen") or ""
    if e["meta"] and e["recaudado"] >= e["meta"]:
        meta = "Meta de %s alcanzada" % money(e["meta"], cur)
    else:
        meta = "Se juntaron %s de %s" % (money(e["recaudado"], cur), money(e["meta"], cur))
    if e["aportes"]:
        meta += " · %d %s" % (e["aportes"], "aporte" if e["aportes"] == 1 else "aportes")
    return (
        '        <article class="fin-done__card">%s<div class="fin-done__body">'
        '<span class="fin-done__tag">Lograda</span><h3>%s</h3>'
        '<p class="fin-done__meta">%s</p>%s</div></article>' % (
            ('<img src="%s" alt="" loading="lazy" />' % esc(img)) if img else "",
            esc(e["nombre"]), meta,
            ('<p class="fin-done__result">%s</p>' % esc(e["resultado"])) if e.get("resultado") else "",
        )
    )


def initiatives_html(d, notice):
    abiertas = [e for e in d["iniciativas"] if not e["lograda"]]
    logradas = [e for e in d["iniciativas"] if e["lograda"]]
    out = [
        '    <section id="iniciativas">\n%s'
        '      <span class="label">Iniciativas</span>\n'
        '      <h2>Aportá a algo concreto</h2>\n'
        '      <div class="prose"><p>Cada iniciativa tiene una meta y una fecha. La barra muestra cuánto se juntó '
        'y cuánto falta; cuando se cumple, publicamos qué se hizo.</p></div>\n' % notice
    ]
    if abiertas:
        out.append('      <div class="fin-inis">\n%s\n      </div>\n'
                   % "\n".join(open_card(e, d) for e in abiertas))
    else:
        out.append('      <p class="fin-empty"><strong>No hay iniciativas abiertas por ahora</strong>'
                   'Cuando lancemos la próxima, va a aparecer acá y en la portada.</p>\n')
    if logradas:
        out.append('      <h3 style="margin-top:2.6rem;font-size:var(--step-1)">Iniciativas logradas</h3>\n'
                   '      <div class="fin-done">\n%s\n      </div>\n'
                   % "\n".join(done_card(e, d["moneda"]) for e in logradas))
    out.append('    </section>\n\n')
    return "".join(out)


def shade(kind, i):
    base = "var(--gold-line)" if kind == "in" else "var(--blue)"
    return "color-mix(in srgb, %s %d%%, var(--surface))" % (base, SHADES[min(i, len(SHADES) - 1)])


def summary_block(rows, kind):
    """Tarjetas de fuentes/usos; con porcentajes, ademas una barra repartida."""
    with_pct = any(r["porcentaje"] for r in rows)
    split = ""
    if with_pct:
        segs = [(r, i) for i, r in enumerate(rows) if r["porcentaje"]]
        split = '      <div class="fin-split" role="img" aria-label="%s">%s</div>\n' % (
            esc(", ".join("%s %g %%" % (r["nombre"], r["porcentaje"]) for r, _ in segs)),
            "".join('<span style="width:%g%%;background:%s"></span>' % (r["porcentaje"], shade(kind, i)) for r, i in segs),
        )
    items = []
    for i, r in enumerate(rows):
        if with_pct and r["porcentaje"]:
            num = ('<span class="fin-card__num fin-card__num--pct"><i class="fin-swatch" style="background:%s"></i>%g %%</span>'
                   % (shade(kind, i), r["porcentaje"]))
        else:
            num = '<span class="fin-card__num">%02d</span>' % (i + 1)
        items.append('        <div class="fin-card">%s<h3>%s</h3>%s</div>' % (
            num, esc(r["nombre"]), ("<p>%s</p>" % esc(r["descripcion"])) if r.get("descripcion") else ""))
    return '%s      <div class="fin-cards%s">\n%s\n      </div>\n' % (
        split, " fin-cards--out" if kind == "out" else "", "\n".join(items))


def summary_html(d):
    period = ('      <p class="fin-period">Resumen %s</p>\n' % esc(d["resumen_periodo"])) if d.get("resumen_periodo") else ""
    out = []
    if d["fuentes"]:
        out.append(
            '    <section>\n'
            '      <span class="label">Cómo se financia</span>\n'
            '      <h2>De dónde viene el dinero</h2>\n%s%s'
            '    </section>\n\n' % (period, summary_block(d["fuentes"], "in"))
        )
    if d["usos"]:
        out.append(
            '    <section>\n'
            '      <span class="label">En qué se usa</span>\n'
            '      <h2>A dónde va</h2>\n%s%s'
            '      <p class="fin-members">%s<span>Los miembros activos reciben el detalle completo de las cuentas: '
            'cada aporte, cada gasto y sus comprobantes.</span></p>\n'
            '    </section>\n\n' % ("" if d["fuentes"] else period, summary_block(d["usos"], "out"), LOCK_ICON)
        )
    return "".join(out)


def home_block(d):
    """Resumen de las iniciativas abiertas para la seccion Colaborar de la portada."""
    cur = d["moneda"]
    cards = []
    for e in d["iniciativas"]:
        if e["lograda"]:
            continue
        pct, falta = progress(e)
        cards.append(
            '<div class="give-event">'
            '<span class="label">Iniciativa en curso</span>'
            '<p class="give-event__name">%s</p>'
            '<div class="give-event__track" role="progressbar" aria-label="Recaudado para %s" '
            'aria-valuemin="0" aria-valuemax="%d" aria-valuenow="%d"><span style="width:%.1f%%"></span></div>'
            '<p class="give-event__nums"><strong>%s</strong> de %s · %s</p>%s'
            '<a href="financiamiento.html#iniciativas">%s →</a>'
            '</div>' % (
                esc(e["nombre"]), esc(e["nombre"]), e["meta"], min(e["recaudado"], e["meta"]), pct,
                money(e["recaudado"], cur), money(e["meta"], cur),
                ("Faltan <strong>%s</strong>" % money(falta, cur)) if falta else "<strong>¡Meta alcanzada!</strong>",
                ('<p class="give-event__note">%d %s</p>' % (e["aportes"], "aporte" if e["aportes"] == 1 else "aportes"))
                if e["aportes"] else "",
                "Ver la iniciativa y aportar" if falta else "Ver la iniciativa",
            )
        )
    return "".join(cards)


def main_html(d):
    notice = ""
    if _true(d.get("ejemplo")):
        notice = ('      <p class="fin-notice"><strong>Datos de ejemplo</strong>'
                  'Los montos de esta página son ilustrativos y todavía no corresponden '
                  'a las cuentas reales del movimiento.</p>\n')
    lead = d.get("lead") or DESCRIPTION
    return (
        '<main>\n'
        '  <section class="doc-hero">\n'
        '    <video class="doc-hero__flag" autoplay muted loop playsinline preload="auto" aria-hidden="true" poster="bandera-ondea-lentamente-poster.jpg">\n'
        '      <source src="bandera-ondea-lentamente.mp4" type="video/mp4" />\n'
        '    </video>\n'
        '    <div class="doc-hero__scrim" aria-hidden="true"></div>\n'
        '    <div class="wrap">\n'
        '      <p class="label">Transparencia</p>\n'
        '      <h1>%s</h1>\n'
        '      <p class="doc-hero__sub">%s</p>\n'
        '    </div>\n'
        '  </section>\n\n'
        '  <div class="doc">\n%s%s'
        '    <section>\n'
        '      <span class="label">Colaborar</span>\n'
        '      <h2>El movimiento se sostiene con sus miembros</h2>\n'
        '      <div class="prose"><p>Además de las iniciativas, podés sumarte con la cuota o con un aporte libre.</p></div>\n'
        '      <p style="margin-top:1.4rem"><a class="btn btn--rounded" href="index.html#aporta">Aportar →</a></p>\n'
        '    </section>\n'
        '  </div>\n%s'
        '</main>' % (TITLE, esc(lead), initiatives_html(d, notice), summary_html(d), PAGE_JS)
    )


def page(tpl, d):
    pre = tpl[:tpl.index("<main>")]
    post = tpl[tpl.index("</main>") + len("</main>"):]
    url = SITE + OUT_NAME
    pre = re.sub(r"<title>.*?</title>", lambda m: "<title>%s · Resurgir Nacional</title>" % TITLE, pre, count=1, flags=re.S)
    pre = pre.replace(SITE + "ideario-y-valores-rn.html", url)  # canonical, hreflang, og:url
    for attr, val in (('name="description"', DESCRIPTION),
                      ('property="og:title"', TITLE + " — Resurgir Nacional"),
                      ('property="og:description"', DESCRIPTION)):
        pre = re.sub(r'(<meta %s content=")[^"]*(")' % re.escape(attr),
                     lambda m: m.group(1) + esc(val) + m.group(2), pre, count=1)
    pre = pre.replace(' aria-current="page"', "")
    post = post.replace(' aria-current="page"', "")
    pre = pre.replace("<head>", "<head>\n" + GEN_MARK, 1)
    pre = pre.replace("</head>", STYLE + "</head>", 1)
    return pre + main_html(d) + post


def main():
    if not os.path.exists(DATA):
        print("ERROR: falta content/pages/financiamiento.yml")
        return 1
    if not os.path.exists(TEMPLATE):
        print("ERROR: falta ideario-y-valores-rn.html (correr tools/build.py primero)")
        return 1
    d = load()
    html_out = page(rd(TEMPLATE), d)
    if not os.path.exists(OUT) or rd(OUT) != html_out:
        wr(OUT, html_out)
        print("  escrito: %s" % OUT_NAME)
    else:
        print("  %s: sin cambios" % OUT_NAME)

    home = rd(HOME_PAGE)
    if HOME_MARK_A not in home or HOME_MARK_B not in home:
        print("ERROR: faltan los marcadores EVENTOS en index.html (correr tools/build.py)")
        return 1
    i = home.index(HOME_MARK_A) + len(HOME_MARK_A)
    j = home.index(HOME_MARK_B)
    new_home = home[:i] + home_block(d) + home[j:]
    if new_home != home:
        wr(HOME_PAGE, new_home)
        print("  index.html: iniciativas en curso actualizadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
