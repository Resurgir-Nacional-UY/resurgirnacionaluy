#!/usr/bin/env python3
"""Render Financiamiento (desglose de ingresos y gastos del movimiento).

Lee content/pages/financiamiento.yml (editable desde el CMS) y genera
financiamiento.html en la raiz del repo. Reusa el chrome de
ideario-y-valores-rn.html (header, footer, estilos, SEO), igual que
render_tienda.py reusa el de la Tienda: solo reemplaza el <main> y agrega
los estilos propios de esta pagina.

Arriba van los eventos: colectas para una ocasion puntual, cada una con su
meta, una barra de progreso y la lista de donantes (anonimo si no hay
nombre). Los botones de donar usan los mismos links de PayPal y Ko-fi que la
seccion Colaborar de la portada (content/pages/home.yml). Las colectas en
curso tambien se muestran, resumidas, en esa seccion de index.html, entre
los marcadores <!-- EVENTOS:START --> / <!-- EVENTOS:END -->.

El periodo destacado es el primero de la lista (el mas reciente); el resto
aparece en la tabla de historial.

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
DESCRIPTION = "Desglose de ingresos y gastos de Resurgir Nacional: de dónde sale el dinero y en qué se usa."

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "setiembre", "octubre", "noviembre", "diciembre"]

STYLE = """
<style>
  /* Financiamiento */
  .fin-notice { border: 1px solid var(--gold-line); background: color-mix(in srgb, var(--gold-line) 12%, transparent); border-radius: 8px; padding: 0.9rem 1.1rem; font-family: "Archivo", system-ui, sans-serif; font-size: 0.9rem; color: var(--ink); max-width: var(--measure); }
  .fin-notice strong { color: var(--gold-text); letter-spacing: 0.08em; text-transform: uppercase; font-size: 0.78rem; margin-right: 0.4rem; }
  .fin-period { font-family: "Archivo", system-ui, sans-serif; color: var(--ink-soft); font-size: 0.9rem; margin-top: 0.4rem; }
  .fin-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 1rem; margin-top: 1.6rem; }
  .fin-stat { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 1.1rem 1.25rem; }
  .fin-stat__label { font-family: "Archivo", system-ui, sans-serif; font-weight: 600; font-size: var(--step--1); letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-soft); }
  .fin-stat__value { font-family: "Fraunces", Georgia, serif; font-size: var(--step-2); line-height: 1.1; margin-top: 0.45rem; font-variant-numeric: tabular-nums; }
  .fin-stat__sub { font-size: 0.9rem; color: var(--ink-soft); margin-top: 0.25rem; }
  .fin-cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); gap: clamp(2rem, 5vw, 3.5rem); margin-top: 1.8rem; }
  .fin-cols h3 { font-size: var(--step-1); }
  .fin-bars { list-style: none; margin: 1.1rem 0 0; padding: 0; display: flex; flex-direction: column; gap: 1.1rem; }
  .fin-bar__head { display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; }
  .fin-bar__name { font-size: 1rem; line-height: 1.35; }
  .fin-bar__amount { font-family: "Archivo", system-ui, sans-serif; font-weight: 600; font-size: 0.9rem; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .fin-bar__amount span { color: var(--ink-soft); font-weight: 500; margin-left: 0.35rem; }
  .fin-bar__track { height: 0.55rem; background: var(--line); border-radius: 999px; margin-top: 0.45rem; overflow: hidden; }
  .fin-bar__fill { display: block; height: 100%; border-radius: 999px; background: var(--blue); }
  .fin-bars--in .fin-bar__fill { background: var(--gold-line); }
  .fin-table-wrap { overflow-x: auto; margin-top: 1.4rem; }
  .fin-table { width: 100%; min-width: 30rem; border-collapse: collapse; font-family: "Archivo", system-ui, sans-serif; font-size: 0.92rem; font-variant-numeric: tabular-nums; }
  .fin-table th, .fin-table td { padding: 0.75rem 0.6rem; border-bottom: 1px solid var(--line); text-align: right; }
  .fin-table th:first-child, .fin-table td:first-child { text-align: left; }
  .fin-table thead th { font-weight: 600; font-size: var(--step--1); letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-soft); }
  .fin-events { display: grid; gap: 1.5rem; margin-top: 1.6rem; }
  .fin-event { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: clamp(1.25rem, 3vw, 2rem); }
  .fin-event h3 { font-size: var(--step-1); }
  .fin-event__date { font-family: "Archivo", system-ui, sans-serif; font-size: 0.9rem; color: var(--ink-soft); margin-top: 0.35rem; }
  .fin-event__desc { margin-top: 0.8rem; max-width: var(--measure); }
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
  .fin-donors { margin-top: 1.6rem; border-top: 1px solid var(--line); padding-top: 1.1rem; }
  .fin-donors__title { font-family: "Archivo", system-ui, sans-serif; font-weight: 600; font-size: var(--step--1); letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-soft); }
  .fin-donors ul { list-style: none; margin: 0.7rem 0 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 13rem), 1fr)); gap: 0 1.5rem; }
  .fin-donors li { display: flex; justify-content: space-between; gap: 1rem; padding: 0.4rem 0; border-bottom: 1px dashed var(--line); font-size: 1rem; }
  .fin-donors li span:last-child { font-family: "Archivo", system-ui, sans-serif; font-size: 0.9rem; color: var(--ink-soft); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .fin-donors .is-anon { font-style: italic; color: var(--ink-soft); }
  .fin-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr)); gap: 1rem; margin-top: 1.6rem; }
  .fin-card { background: var(--surface); border: 1px solid var(--line); border-top: 3px solid var(--gold-line); border-radius: 8px; padding: 1.1rem 1.25rem 1.25rem; }
  .fin-cards--out .fin-card { border-top-color: var(--blue); }
  .fin-card__num { font-family: "Archivo", system-ui, sans-serif; font-weight: 600; font-size: var(--step--1); letter-spacing: 0.14em; color: var(--gold-text); }
  .fin-cards--out .fin-card__num { color: var(--blue); }
  .fin-card h3 { font-size: var(--step-1); margin-top: 0.35rem; }
  .fin-card p { margin-top: 0.45rem; color: var(--ink-soft); font-size: 1rem; line-height: 1.55; }
  .fin-empty { margin-top: 1.6rem; border: 1px dashed var(--line); border-radius: 8px; padding: 1.25rem; max-width: var(--measure); color: var(--ink-soft); }
  .fin-empty strong { display: block; color: var(--ink); font-family: "Fraunces", Georgia, serif; font-weight: 500; font-size: var(--step-1); margin-bottom: 0.3rem; }
  .fin-preview { position: relative; margin-top: 2.2rem; border: 1px solid var(--line); border-radius: 8px; padding: clamp(1.4rem, 3vw, 2rem) clamp(1.1rem, 3vw, 1.75rem) clamp(1.1rem, 3vw, 1.75rem); background: var(--surface); }
  .fin-preview__tag { position: absolute; top: -0.75rem; left: 1.1rem; background: var(--bg); border: 1px solid var(--line); border-radius: 999px; padding: 0.1rem 0.7rem; font-family: "Archivo", system-ui, sans-serif; font-weight: 600; font-size: var(--step--1); letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold-text); }
  .fin-preview .fin-stats { margin-top: 0; }
  .fin-preview .fin-stat { background: var(--bg); }
  .fin-preview .fin-stat__value { color: var(--ink-soft); }
  .fin-preview .fin-bar__fill { background: color-mix(in srgb, var(--ink-soft) 30%, transparent); }
  .fin-preview__caption { margin-top: 1.4rem; font-size: 0.95rem; color: var(--ink-soft); }
  .fin-past { list-style: none; margin: 1rem 0 0; padding: 0; }
  .fin-past li { display: flex; justify-content: space-between; gap: 0.3rem 1rem; flex-wrap: wrap; padding: 0.7rem 0; border-bottom: 1px solid var(--line); }
  .fin-past li span:last-child { font-family: "Archivo", system-ui, sans-serif; font-size: 0.9rem; color: var(--ink-soft); font-variant-numeric: tabular-nums; }
</style>
"""


# Botones "Copiar número" (cuenta Prex). Usa el mismo aviso .copy-toast que
# el correo del pie, cuyos estilos ya trae la plantilla.
COPY_JS = """  <script>
  (function () {
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


def load():
    d = yaml.safe_load(rd(DATA)) or {}
    periodos = []
    for p in d.get("periodos") or []:
        if not isinstance(p, dict) or not p.get("nombre"):
            continue
        rows = {}
        for k in ("ingresos", "gastos"):
            rows[k] = [
                {"concepto": r["concepto"], "monto": float(r.get("monto") or 0)}
                for r in (p.get(k) or []) if isinstance(r, dict) and r.get("concepto")
            ]
        p["ingresos"], p["gastos"] = rows["ingresos"], rows["gastos"]
        p["total_in"] = sum(r["monto"] for r in p["ingresos"])
        p["total_out"] = sum(r["monto"] for r in p["gastos"])
        periodos.append(p)
    d["periodos"] = periodos
    d["moneda"] = d.get("moneda") or "$"

    eventos = []
    for e in d.get("eventos") or []:
        if not isinstance(e, dict) or not e.get("nombre"):
            continue
        e["donaciones"] = [
            {"nombre": str(r.get("nombre") or "").strip(), "monto": float(r.get("monto") or 0)}
            for r in (e.get("donaciones") or []) if isinstance(r, dict)
        ]
        e["recaudado"] = sum(r["monto"] for r in e["donaciones"])
        e["meta"] = float(e.get("meta") or 0)
        e["cerrado"] = e.get("cerrado") in (True, "true", "True")
        eventos.append(e)
    d["eventos"] = eventos

    home = yaml.safe_load(rd(HOME_DATA)) if os.path.exists(HOME_DATA) else {}
    home = home if isinstance(home, dict) else {}
    d["give_links"] = [(label, home[k]) for label, k in
                       (("Donar por PayPal", "aporta_paypal"), ("Donar por Ko-fi", "aporta_kofi"))
                       if home.get(k)]
    d["prex"] = str(home.get("aporta_prex") or "").strip()

    for k in ("fuentes", "usos"):
        d[k] = [r for r in (d.get(k) or []) if isinstance(r, dict) and r.get("nombre")]
    return d


def bars(rows, total, cur, mod):
    items = []
    for r in sorted(rows, key=lambda r: -r["monto"]):
        pct = (r["monto"] / total * 100) if total else 0
        items.append(
            '          <li>\n'
            '            <div class="fin-bar__head"><span class="fin-bar__name">%s</span>'
            '<span class="fin-bar__amount">%s<span>%d%%</span></span></div>\n'
            '            <div class="fin-bar__track" aria-hidden="true"><span class="fin-bar__fill" style="width:%.1f%%"></span></div>\n'
            '          </li>' % (esc(r["concepto"]), money(r["monto"], cur), round(pct), pct)
        )
    return '        <ul class="fin-bars %s">\n%s\n        </ul>' % (mod, "\n".join(items))


def event_card(e, cur, give_links, prex):
    rec, meta = e["recaudado"], e["meta"]
    pct = min(100.0, rec / meta * 100) if meta else 0
    falta = max(0.0, meta - rec)
    status = ("Faltan <strong>%s</strong>" % money(falta, cur)) if falta else "<strong>¡Meta cumplida!</strong> Gracias a todos."
    date = ('        <p class="fin-event__date">%s</p>\n' % esc(fecha(e["fecha"]))) if e.get("fecha") else ""
    desc = ('        <p class="fin-event__desc">%s</p>\n' % esc(e["descripcion"])) if e.get("descripcion") else ""

    give = ""
    if give_links or prex:
        buttons = "".join(
            '<a class="btn btn--rounded%s" href="%s" target="_blank" rel="noopener">%s</a>'
            % ("" if i == 0 else " btn--alt", esc(url), esc(label))
            for i, (label, url) in enumerate(give_links)
        )
        prex_html = (
            '        <p class="fin-prex">Por Prex, a la cuenta <strong>%s</strong> '
            '<button type="button" class="fin-copy" data-copy="%s">Copiar número</button></p>\n'
            % (esc(prex), esc(prex))
        ) if prex else ""
        give = (
            '%s%s'
            '        <p class="fin-give__hint">En el mensaje o concepto del pago escribí «%s» y el nombre con el que querés '
            'aparecer en la lista. Si preferís no figurar, no pongas nombre: aparecés como «Anónimo».</p>\n'
            % (('        <div class="fin-give">%s</div>\n' % buttons) if buttons else "", prex_html, esc(e["nombre"]))
        )

    donors = ""
    if e["donaciones"]:
        rows = "\n".join(
            '            <li><span%s>%s</span><span>%s</span></li>' % (
                "" if r["nombre"] else ' class="is-anon"', esc(r["nombre"] or "Anónimo"), money(r["monto"], cur))
            for r in e["donaciones"]
        )
        n = len(e["donaciones"])
        donors = (
            '        <div class="fin-donors">\n'
            '          <p class="fin-donors__title">%d %s</p>\n'
            '          <ul>\n%s\n          </ul>\n'
            '        </div>\n' % (n, "donación" if n == 1 else "donaciones", rows)
        )

    return (
        '      <article class="fin-event">\n'
        '        <h3>%s</h3>\n%s%s'
        '        <div class="fin-goal">\n'
        '          <div class="fin-goal__nums"><span class="fin-goal__raised">%s</span><span class="fin-goal__of">recaudados de %s</span></div>\n'
        '          <div class="fin-goal__track" role="progressbar" aria-label="Recaudado para %s" aria-valuemin="0" aria-valuemax="%d" aria-valuenow="%d">'
        '<span class="fin-goal__fill" style="width:%.1f%%"></span></div>\n'
        '          <div class="fin-goal__foot"><span>%d%% de la meta</span><span>%s</span></div>\n'
        '        </div>\n%s%s'
        '      </article>' % (
            esc(e["nombre"]), date, desc,
            money(rec, cur), money(meta, cur),
            esc(e["nombre"]), meta, min(rec, meta), pct,
            round(pct), status, give if falta else "", donors,
        )
    )


def events_html(d, cur, notice):
    activos = [e for e in d["eventos"] if not e["cerrado"]]
    cerrados = [e for e in d["eventos"] if e["cerrado"]]
    if not activos and not cerrados:
        return ""
    parts = ['    <section id="eventos">\n%s' % notice]
    if activos:
        parts.append(
            '      <span class="label"%s>Eventos</span>\n'
            '      <h2>Colectas en curso</h2>\n'
            '      <div class="prose"><p>Para actividades puntuales abrimos una colecta con su propia meta. '
            'Cada donación se suma a la barra y a la lista.</p></div>\n'
            '      <div class="fin-events">\n%s\n      </div>\n' % (
                ' style="margin-top:1.4rem"' if notice else "",
                "\n".join(event_card(e, cur, d["give_links"], d["prex"]) for e in activos))
        )
    if cerrados:
        rows = "\n".join(
            '        <li><span>%s%s</span><span>%s de %s</span></li>' % (
                esc(e["nombre"]), (" · " + esc(fecha(e["fecha"]))) if e.get("fecha") else "",
                money(e["recaudado"], cur), money(e["meta"], cur))
            for e in cerrados
        )
        parts.append(
            '      %s\n'
            '      <ul class="fin-past">\n%s\n      </ul>\n' % (
                '<h3 style="margin-top:2.2rem;font-size:var(--step-1)">Colectas anteriores</h3>' if activos
                else '<span class="label"%s>Eventos</span>\n      <h2>Colectas anteriores</h2>' % (' style="margin-top:1.4rem"' if notice else ""),
                rows)
        )
    parts.append('    </section>\n\n')
    return "".join(parts)


def cards(rows, mod=""):
    items = "\n".join(
        '        <div class="fin-card"><span class="fin-card__num">%02d</span><h3>%s</h3>%s</div>' % (
            i + 1, esc(r["nombre"]),
            ("<p>%s</p>" % esc(r["descripcion"])) if r.get("descripcion") else "")
        for i, r in enumerate(rows)
    )
    return '      <div class="fin-cards%s">\n%s\n      </div>\n' % (mod, items)


# anchos fijos de las barras de la vista previa: decorativos, no son datos
GHOST_WIDTHS = [72, 48, 30, 20, 12]


def ghost_bars(rows):
    items = "\n".join(
        '          <li>\n'
        '            <div class="fin-bar__head"><span class="fin-bar__name">%s</span><span class="fin-bar__amount">—</span></div>\n'
        '            <div class="fin-bar__track" aria-hidden="true"><span class="fin-bar__fill" style="width:%d%%"></span></div>\n'
        '          </li>' % (esc(r["nombre"]), GHOST_WIDTHS[min(i, len(GHOST_WIDTHS) - 1)])
        for i, r in enumerate(rows)
    )
    return '        <ul class="fin-bars">\n%s\n        </ul>' % items


def generic_html(d, notice, has_events):
    """Pagina sin cuentas publicadas: muestra la estructura sin numeros."""
    first = ' style="margin-top:1.4rem"' if notice else ""
    out = []
    if d["fuentes"]:
        out.append(
            '    <section>\n%s'
            '      <span class="label"%s>Cómo se financia</span>\n'
            '      <h2>De dónde viene el dinero</h2>\n%s'
            '    </section>\n\n' % (notice, first, cards(d["fuentes"]))
        )
        notice, first = "", ""
    if d["usos"]:
        out.append(
            '    <section>\n%s'
            '      <span class="label"%s>En qué se usa</span>\n'
            '      <h2>A dónde va</h2>\n%s'
            '    </section>\n\n' % (notice, first, cards(d["usos"], " fin-cards--out"))
        )
        notice, first = "", ""
    if not has_events:
        out.append(
            '    <section id="eventos">\n%s'
            '      <span class="label"%s>Eventos</span>\n'
            '      <h2>Colectas por evento</h2>\n'
            '      <div class="prose"><p>Para actividades puntuales abrimos una colecta con su propia meta. '
            'Una barra muestra cuánto se juntó y cuánto falta, y se puede donar con nombre o de forma anónima.</p></div>\n'
            '      <p class="fin-empty"><strong>No hay colectas abiertas por ahora</strong>'
            'Cuando organicemos la próxima, va a aparecer acá y en la portada.</p>\n'
            '    </section>\n\n' % (notice, first)
        )
        notice, first = "", ""

    preview = ""
    if d["fuentes"] or d["usos"]:
        tiles = "".join(
            '        <div class="fin-stat"><div class="fin-stat__label">%s</div><div class="fin-stat__value">—</div></div>\n' % t
            for t in ("Ingresos", "Gastos", "Saldo")
        )
        preview = (
            '      <div class="fin-preview">\n'
            '        <span class="fin-preview__tag">Vista previa</span>\n'
            '        <div class="fin-stats">\n%s        </div>\n'
            '        <div class="fin-cols">\n'
            '          <div>\n          <h3>En qué se gastó</h3>\n%s\n          </div>\n'
            '          <div>\n          <h3>De dónde vino</h3>\n%s\n          </div>\n'
            '        </div>\n'
            '        <p class="fin-preview__caption">Así se va a ver cada período: los totales, el desglose '
            'por categoría y el historial completo.</p>\n'
            '      </div>\n' % (tiles, ghost_bars(d["usos"]), ghost_bars(d["fuentes"]))
        )
    out.append(
        '    <section>\n%s'
        '      <span class="label"%s>Cuentas</span>\n'
        '      <h2>Próximamente</h2>\n'
        '      <div class="prose"><p>Acá vamos a publicar, período por período, cuánto dinero recibe '
        'el movimiento, de dónde viene y en qué se usa.</p></div>\n%s'
        '    </section>\n' % (notice, first, preview)
    )
    return "".join(out)


def home_block(d):
    """Resumen de las colectas en curso para la seccion Colaborar de la portada."""
    cur = d["moneda"]
    cards = []
    for e in d["eventos"]:
        if e["cerrado"]:
            continue
        rec, meta = e["recaudado"], e["meta"]
        pct = min(100.0, rec / meta * 100) if meta else 0
        falta = max(0.0, meta - rec)
        cards.append(
            '<div class="give-event">'
            '<span class="label">Colecta en curso</span>'
            '<p class="give-event__name">%s</p>'
            '<div class="give-event__track" role="progressbar" aria-label="Recaudado para %s" '
            'aria-valuemin="0" aria-valuemax="%d" aria-valuenow="%d"><span style="width:%.1f%%"></span></div>'
            '<p class="give-event__nums"><strong>%s</strong> de %s · %s</p>%s'
            '<a href="financiamiento.html#eventos">%s →</a>'
            '</div>' % (
                esc(e["nombre"]), esc(e["nombre"]), meta, min(rec, meta), pct,
                money(rec, cur), money(meta, cur),
                ("Faltan <strong>%s</strong>" % money(falta, cur)) if falta else "<strong>¡Meta cumplida!</strong>",
                '<p class="give-event__note">Datos de ejemplo.</p>' if d.get("ejemplo") in (True, "true", "True") else "",
                "Ver la colecta y donar" if falta else "Ver la colecta",
            )
        )
    return "".join(cards)


def main_html(d):
    cur = d["moneda"]
    notice = ""
    if d.get("ejemplo") in (True, "true", "True"):
        notice = ('      <p class="fin-notice"><strong>Datos de ejemplo</strong>'
                  'Los montos de esta página son ilustrativos y todavía no corresponden '
                  'a las cuentas reales del movimiento.</p>\n')
    lead = d.get("lead") or DESCRIPTION
    updated = ('      <p class="fin-period">Actualizado el %s</p>\n' % esc(fecha(d["actualizado"]))
               if d.get("actualizado") else "")

    out = [
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
        '  <div class="doc">\n' % (TITLE, esc(lead))
    ]

    # el aviso de datos de ejemplo va una sola vez, en la primera seccion
    ev = events_html(d, cur, notice)
    if ev:
        out.append(ev)
        notice = ""

    if not d["periodos"]:
        out.append(generic_html(d, notice, bool(ev)))
    else:
        p = d["periodos"][0]
        saldo = p["total_in"] - p["total_out"]
        uso = (p["total_out"] / p["total_in"] * 100) if p["total_in"] else 0
        out.append(
            '    <section>\n'
            '%s'
            '      <span class="label"%s>Último período</span>\n'
            '      <h2>%s</h2>\n'
            '%s'
            '      <div class="fin-stats">\n'
            '        <div class="fin-stat"><div class="fin-stat__label">Ingresos</div><div class="fin-stat__value">%s</div></div>\n'
            '        <div class="fin-stat"><div class="fin-stat__label">Gastos</div><div class="fin-stat__value">%s</div>'
            '<div class="fin-stat__sub">%d%% de lo recaudado</div></div>\n'
            '        <div class="fin-stat"><div class="fin-stat__label">%s</div><div class="fin-stat__value">%s</div>'
            '<div class="fin-stat__sub">%s</div></div>\n'
            '      </div>\n'
            '    </section>\n\n'
            '    <section>\n'
            '      <span class="label">Desglose</span>\n'
            '      <h2>De dónde viene y a dónde va</h2>\n'
            '      <div class="fin-cols">\n'
            '        <div>\n'
            '        <h3>En qué se gastó</h3>\n%s\n'
            '        </div>\n'
            '        <div>\n'
            '        <h3>De dónde vino</h3>\n%s\n'
            '        </div>\n'
            '      </div>\n'
            '    </section>\n' % (
                notice, ' style="margin-top:1.4rem"' if notice else "", esc(p["nombre"]), updated,
                money(p["total_in"], cur), money(p["total_out"], cur), round(uso),
                "Saldo" if saldo >= 0 else "Déficit", money(saldo, cur),
                "Queda para el próximo período" if saldo >= 0 else "Cubierto con fondos anteriores",
                bars(p["gastos"], p["total_out"], cur, "fin-bars--out"),
                bars(p["ingresos"], p["total_in"], cur, "fin-bars--in"),
            )
        )

        rows = "\n".join(
            '            <tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                esc(q["nombre"]), money(q["total_in"], cur), money(q["total_out"], cur),
                money(q["total_in"] - q["total_out"], cur))
            for q in d["periodos"]
        )
        out.append(
            '\n    <section>\n'
            '      <span class="label">Historial</span>\n'
            '      <h2>Todos los períodos</h2>\n'
            '      <div class="fin-table-wrap">\n'
            '        <table class="fin-table">\n'
            '          <thead><tr><th scope="col">Período</th><th scope="col">Ingresos</th><th scope="col">Gastos</th><th scope="col">Saldo</th></tr></thead>\n'
            '          <tbody>\n%s\n          </tbody>\n'
            '        </table>\n'
            '      </div>\n'
            '%s'
            '    </section>\n' % (
                rows,
                ('      <div class="prose"><p class="muted">%s</p></div>\n' % esc(d["nota"])) if d.get("nota") else "",
            )
        )

    out.append(
        '\n    <section>\n'
        '      <span class="label">Colaborar</span>\n'
        '      <h2>El movimiento se sostiene con sus miembros</h2>\n'
        '      <div class="prose"><p>Cada aporte se suma a esta cuenta y se publica acá.</p></div>\n'
        '      <p style="margin-top:1.4rem"><a class="btn btn--rounded" href="index.html#aporta">Aportar →</a></p>\n'
        '    </section>\n'
        '  </div>\n'
        '%s'
        '</main>' % (COPY_JS if d["prex"] else "")
    )
    return "".join(out)


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
    post = post.replace('<a href="financiamiento.html">', '<a href="financiamiento.html" aria-current="page">')
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
        print("  index.html: colectas en curso actualizadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
