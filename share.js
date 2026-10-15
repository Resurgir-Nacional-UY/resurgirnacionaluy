/* Botón de compartir de Resurgir Nacional.
   Un solo script para todo el sitio (se carga desde el pie, que es común a todas las páginas).

   - <div data-share></div>  → se llena con un único botón "Compartir"; al pulsarlo se abre un menú con
       WhatsApp, Telegram, Facebook, X, Correo, Copiar enlace (y "Más…" si el navegador puede compartir).
       data-share-url="..."    enlace a compartir (por defecto, la página actual)
       data-share-title="..."  texto que acompaña al enlace (por defecto, el título de la página)
       data-share-wait         no se muestra hasta que otro script le quite el atributo "hidden"
   - Los botones "Compartir" antiguos (.share-btn de los artículos y libros) se reemplazan por este mismo botón.
   - El botón del pie ([data-share-footer]) solo se muestra si la página no tiene otro dentro de <main>. */
(function () {
  'use strict';

  var css = [
    '.share-bar{position:relative;display:block;width:fit-content;max-width:100%;margin-top:1.6rem}',
    '.share-bar[hidden]{display:none}',
    '.share-bar__toggle{display:inline-flex;align-items:center;gap:.45rem;padding:.5rem .95rem;border:1px solid var(--line,#d5d9e0);border-radius:999px;background:var(--surface,transparent);color:var(--ink-soft,#5a6577);font:inherit;font-family:"Archivo",sans-serif;font-weight:600;font-size:.78rem;letter-spacing:.05em;text-transform:uppercase;line-height:1.2;cursor:pointer;transition:color .15s ease,border-color .15s ease}',
    '.share-bar__toggle svg{width:1rem;height:1rem;fill:currentColor}',
    '.share-bar__toggle:hover,.share-bar__toggle:focus-visible,.share-bar__toggle[aria-expanded="true"]{color:var(--blue,#14315C);border-color:var(--gold-line,#c9a24a)}',
    '.share-bar__toggle:focus-visible{outline:2px solid var(--focus,#14315C);outline-offset:2px}',
    '.share-menu{position:absolute;left:0;top:calc(100% + .4rem);z-index:60;display:flex;flex-direction:column;min-width:12.5rem;padding:.35rem;border:1px solid var(--line,#d5d9e0);border-radius:12px;background:var(--surface,#fff);box-shadow:0 10px 30px rgba(0,0,0,.22);transform-origin:top left;animation:share-pop .14s ease-out}',
    '.share-menu[hidden]{display:none}',
    '.share-menu--up{top:auto;bottom:calc(100% + .4rem);transform-origin:bottom left}',
    '.share-menu--right{left:auto;right:0}',
    '.share-menu--right.share-menu--up{transform-origin:bottom right}',
    '.share-menu--right:not(.share-menu--up){transform-origin:top right}',
    '.share-menu__item{display:block;width:100%;padding:.6rem .85rem;border:0;border-radius:8px;background:transparent;color:var(--ink,#1b2230);font:inherit;font-family:"Archivo",sans-serif;font-size:.9rem;text-align:left;text-decoration:none;cursor:pointer}',
    '.share-menu__item:hover,.share-menu__item:focus-visible{background:rgba(127,127,127,.16);color:var(--ink,#1b2230)}',
    '.share-menu__item:focus-visible{outline:2px solid var(--focus,#14315C);outline-offset:-2px}',
    '.share-menu__sep{height:1px;margin:.3rem .5rem;background:var(--line,#d5d9e0)}',
    '.share-bar--footer{margin-top:1.4rem}',
    '.share-bar--footer .share-bar__toggle{background:transparent;border-color:rgba(255,255,255,.35);color:#fff}',
    '.share-bar--footer .share-bar__toggle:hover,.share-bar--footer .share-bar__toggle:focus-visible,.share-bar--footer .share-bar__toggle[aria-expanded="true"]{color:#E7C978;border-color:#E7C978}',
    '.share-bar--footer .share-bar__toggle:focus-visible{outline-color:#E7C978}',
    '.share-bar--footer .share-menu{background:#10264a;border-color:rgba(255,255,255,.28)}',
    '.share-bar--footer .share-menu__item{color:#fff}',
    '.share-bar--footer .share-menu__item:hover,.share-bar--footer .share-menu__item:focus-visible{background:rgba(255,255,255,.12);color:#E7C978}',
    '.share-bar--footer .share-menu__sep{background:rgba(255,255,255,.2)}',
    '.share-toast{position:fixed;left:50%;bottom:1.6rem;z-index:100;transform:translate(-50%,.6rem);padding:.6rem 1.1rem;border-radius:999px;background:#14315C;color:#fff;font-family:"Archivo",sans-serif;font-size:.85rem;opacity:0;pointer-events:none;transition:opacity .2s ease,transform .2s ease}',
    '.share-toast.is-on{opacity:1;transform:translate(-50%,0)}',
    '@keyframes share-pop{from{opacity:0;transform:scale(.97)}to{opacity:1;transform:scale(1)}}',
    '@media (prefers-reduced-motion:reduce){.share-bar__toggle,.share-toast{transition:none}.share-menu{animation:none}}',
    '@media print{.share-bar,.share-toast{display:none}}'
  ].join('\n');

  var ICONO = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>';

  var REDES = [
    { id: 'whatsapp', nombre: 'WhatsApp', url: function (u, t) { return 'https://wa.me/?text=' + encodeURIComponent(t + '\n' + u); } },
    { id: 'telegram', nombre: 'Telegram', url: function (u, t) { return 'https://t.me/share/url?url=' + encodeURIComponent(u) + '&text=' + encodeURIComponent(t); } },
    { id: 'facebook', nombre: 'Facebook', url: function (u) { return 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(u); } },
    { id: 'x', nombre: 'X', url: function (u, t) { return 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(t) + '&url=' + encodeURIComponent(u); } },
    { id: 'correo', nombre: 'Correo', url: function (u, t) { return 'mailto:?subject=' + encodeURIComponent(t) + '&body=' + encodeURIComponent(t + '\n' + u); }, mismaPestana: true }
  ];

  function estilo() {
    if (document.getElementById('share-css')) return;
    var s = document.createElement('style');
    s.id = 'share-css';
    s.textContent = css;
    document.head.appendChild(s);
  }

  // Enlace de la página sin parámetros de seguimiento (?v=...), con el #pestaña si la hay.
  function urlActual() { return location.origin + location.pathname + location.hash; }
  function datos(barra) {
    var u = barra.getAttribute('data-share-url');
    return {
      url: u ? new URL(u, location.href).href : urlActual(),
      titulo: barra.getAttribute('data-share-title') || document.title
    };
  }

  var contador = 0;
  function llenar(barra) {
    barra.textContent = '';
    barra.classList.add('share-bar');
    var id = 'share-menu-' + (++contador);

    var t = document.createElement('button');
    t.type = 'button';
    t.className = 'share-bar__toggle';
    t.setAttribute('aria-haspopup', 'menu');
    t.setAttribute('aria-expanded', 'false');
    t.setAttribute('aria-controls', id);
    t.innerHTML = ICONO + 'Compartir';
    barra.appendChild(t);

    var m = document.createElement('div');
    m.className = 'share-menu';
    m.id = id;
    m.setAttribute('role', 'menu');
    m.setAttribute('aria-label', 'Compartir');
    m.hidden = true;
    var d = datos(barra);
    REDES.forEach(function (r) {
      var a = document.createElement('a');
      a.className = 'share-menu__item';
      a.setAttribute('role', 'menuitem');
      a.setAttribute('data-red', r.id);
      a.href = r.url(d.url, d.titulo);
      if (!r.mismaPestana) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
      a.textContent = r.nombre;
      m.appendChild(a);
    });
    var sep = document.createElement('div');
    sep.className = 'share-menu__sep';
    sep.setAttribute('role', 'separator');
    m.appendChild(sep);
    var c = document.createElement('button');
    c.type = 'button';
    c.className = 'share-menu__item';
    c.setAttribute('role', 'menuitem');
    c.setAttribute('data-red', 'copiar');
    c.textContent = 'Copiar enlace';
    m.appendChild(c);
    if (navigator.share) {
      var n = document.createElement('button');
      n.type = 'button';
      n.className = 'share-menu__item';
      n.setAttribute('role', 'menuitem');
      n.setAttribute('data-red', 'nativo');
      n.textContent = 'Más opciones…';
      m.appendChild(n);
    }
    barra.appendChild(m);
    if (!barra.hasAttribute('data-share-wait')) barra.hidden = false;
  }

  var toast, tt;
  function aviso(msg) {
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'share-toast';
      toast.setAttribute('role', 'status');
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('is-on');
    clearTimeout(tt);
    tt = setTimeout(function () { toast.classList.remove('is-on'); }, 1800);
  }
  function copiarViejo(txt) {
    var ta = document.createElement('textarea');
    ta.value = txt; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.top = '-1000px';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
    aviso('Enlace copiado');
  }
  function copiar(txt) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(function () { aviso('Enlace copiado'); }, function () { copiarViejo(txt); });
    } else { copiarViejo(txt); }
  }

  // Menú abierto (solo puede haber uno)
  var abierto = null;
  function cerrar(devolverFoco) {
    if (!abierto) return;
    var t = abierto.querySelector('.share-bar__toggle');
    abierto.querySelector('.share-menu').hidden = true;
    t.setAttribute('aria-expanded', 'false');
    if (devolverFoco) t.focus();
    abierto = null;
  }
  function abrir(barra) {
    cerrar(false);
    var t = barra.querySelector('.share-bar__toggle');
    var m = barra.querySelector('.share-menu');
    // Los enlaces se recalculan al abrir, por si la página cambió de pestaña (#oraciones, #calendario).
    var d = datos(barra);
    REDES.forEach(function (r) {
      var a = m.querySelector('[data-red="' + r.id + '"]');
      if (a) a.href = r.url(d.url, d.titulo);
    });
    m.classList.remove('share-menu--up', 'share-menu--right');
    m.hidden = false;
    // Si no cabe hacia abajo (p. ej. en el pie) se abre hacia arriba; si no cabe a la derecha, hacia la izquierda.
    var rt = t.getBoundingClientRect(), rm = m.getBoundingClientRect();
    if (rt.bottom + rm.height + 12 > window.innerHeight && rt.top > rm.height + 12) m.classList.add('share-menu--up');
    if (rt.left + rm.width > window.innerWidth - 8) m.classList.add('share-menu--right');
    t.setAttribute('aria-expanded', 'true');
    abierto = barra;
  }

  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target : e.target.parentNode;
    var barra = el.closest ? el.closest('.share-bar') : null;
    if (!barra) { cerrar(false); return; }
    var t = el.closest('.share-bar__toggle');
    if (t) {
      if (abierto === barra) cerrar(false); else abrir(barra);
      return;
    }
    var item = el.closest('.share-menu__item');
    if (!item) return;
    var d = datos(barra);
    var red = item.getAttribute('data-red');
    if (red === 'copiar') { copiar(d.url); cerrar(true); }
    else if (red === 'nativo') { cerrar(false); navigator.share({ title: d.titulo, url: d.url }).catch(function () {}); }
    else { cerrar(false); } // los enlaces de las redes siguen su curso
  });

  document.addEventListener('keydown', function (e) {
    if (!abierto) return;
    if (e.key === 'Escape') { cerrar(true); return; }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      var items = [].slice.call(abierto.querySelectorAll('.share-menu__item'));
      var i = items.indexOf(document.activeElement);
      i = e.key === 'ArrowDown' ? (i + 1) % items.length : (i <= 0 ? items.length - 1 : i - 1);
      items[i].focus();
      e.preventDefault();
    }
  });

  function iniciar() {
    estilo();
    // ¿La página ya trae su propio botón dentro del contenido? Entonces el pie no repite.
    var propia = document.querySelector('main [data-share]:not([data-share-footer]), main .share-btn');
    // Botones antiguos de artículos y libros → mismo botón que el resto.
    [].forEach.call(document.querySelectorAll('.share-btn'), function (b) {
      var barra = document.createElement('div');
      barra.setAttribute('data-share', '');
      b.parentNode.replaceChild(barra, b);
    });
    [].forEach.call(document.querySelectorAll('[data-share]'), function (barra) {
      if (barra.hasAttribute('data-share-footer')) {
        if (propia) { barra.hidden = true; return; }
        barra.classList.add('share-bar--footer');
      }
      llenar(barra);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();

  // Para otros scripts de la página: volver a dibujar un botón (p. ej. si cambió su data-share-url).
  window.rnCompartir = llenar;
})();
