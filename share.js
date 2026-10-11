/* Botones de compartir de Resurgir Nacional.
   Un solo script para todo el sitio (se carga desde el pie, que es común a todas las páginas).

   - <div data-share></div>  → se llena con la fila "Compartir: WhatsApp · Telegram · Facebook · X · Correo · Copiar enlace".
       data-share-url="..."    enlace a compartir (por defecto, la página actual)
       data-share-title="..."  texto que acompaña al enlace (por defecto, el título de la página)
       data-share-wait         no se muestra hasta que otro script le quite el atributo "hidden"
   - Los botones "Compartir" antiguos (.share-btn de los artículos y libros) se reemplazan por esta misma fila.
   - La fila del pie ([data-share-footer]) solo se muestra si la página no tiene otra fila dentro de <main>. */
(function () {
  'use strict';

  var css = [
    '.share-bar{display:flex;flex-wrap:wrap;align-items:center;gap:.45rem;margin-top:1.6rem;max-width:100%}',
    '.share-bar[hidden]{display:none}',
    '.share-bar__label{margin-right:.35rem;font-family:"Archivo",sans-serif;font-weight:600;font-size:.74rem;letter-spacing:.16em;text-transform:uppercase;color:var(--ink-soft,#5a6577)}',
    '.share-bar__btn{display:inline-flex;align-items:center;padding:.42rem .85rem;border:1px solid var(--line,#d5d9e0);border-radius:999px;background:var(--surface,transparent);color:var(--ink-soft,#5a6577);font:inherit;font-family:"Archivo",sans-serif;font-weight:600;font-size:.74rem;letter-spacing:.05em;text-transform:uppercase;text-decoration:none;line-height:1.2;cursor:pointer;transition:color .15s ease,border-color .15s ease}',
    '.share-bar__btn:hover,.share-bar__btn:focus-visible{color:var(--blue,#14315C);border-color:var(--gold-line,#c9a24a)}',
    '.share-bar__btn:focus-visible{outline:2px solid var(--focus,#14315C);outline-offset:2px}',
    '.share-bar--footer{margin-top:1.4rem;gap:.55rem}',
    '.share-bar--footer .share-bar__label{color:#E7C978}',
    '.share-bar--footer .share-bar__btn{background:transparent;border-color:rgba(255,255,255,.35);color:#fff}',
    '.share-bar--footer .share-bar__btn:hover,.share-bar--footer .share-bar__btn:focus-visible{color:#E7C978;border-color:#E7C978}',
    '.share-bar--footer .share-bar__btn:focus-visible{outline-color:#E7C978}',
    '.share-toast{position:fixed;left:50%;bottom:1.6rem;z-index:100;transform:translate(-50%,.6rem);padding:.6rem 1.1rem;border-radius:999px;background:#14315C;color:#fff;font-family:"Archivo",sans-serif;font-size:.85rem;opacity:0;pointer-events:none;transition:opacity .2s ease,transform .2s ease}',
    '.share-toast.is-on{opacity:1;transform:translate(-50%,0)}',
    '@media (prefers-reduced-motion:reduce){.share-bar__btn,.share-toast{transition:none}}',
    '@media print{.share-bar,.share-toast{display:none}}'
  ].join('\n');

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

  function llenar(barra) {
    barra.textContent = '';
    barra.classList.add('share-bar');
    var et = document.createElement('span');
    et.className = 'share-bar__label';
    et.textContent = 'Compartir';
    barra.appendChild(et);
    var d = datos(barra);
    REDES.forEach(function (r) {
      var a = document.createElement('a');
      a.className = 'share-bar__btn';
      a.setAttribute('data-red', r.id);
      a.href = r.url(d.url, d.titulo);
      if (!r.mismaPestana) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
      a.textContent = r.nombre;
      a.setAttribute('aria-label', 'Compartir en ' + r.nombre);
      barra.appendChild(a);
    });
    var c = document.createElement('button');
    c.type = 'button';
    c.className = 'share-bar__btn';
    c.setAttribute('data-red', 'copiar');
    c.textContent = 'Copiar enlace';
    barra.appendChild(c);
    if (navigator.share) {
      var n = document.createElement('button');
      n.type = 'button';
      n.className = 'share-bar__btn';
      n.setAttribute('data-red', 'nativo');
      n.textContent = 'Más…';
      n.setAttribute('aria-label', 'Compartir con otras aplicaciones');
      barra.appendChild(n);
    }
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

  // Un solo manejador para todas las filas. Los enlaces se recalculan al hacer clic,
  // por si la página cambió de pestaña (#oraciones, #calendario) desde que se dibujó la fila.
  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('.share-bar__btn') : null;
    if (!b) return;
    var barra = b.closest('.share-bar');
    var d = datos(barra);
    var red = b.getAttribute('data-red');
    if (red === 'copiar') { copiar(d.url); return; }
    if (red === 'nativo') { navigator.share({ title: d.titulo, url: d.url }).catch(function () {}); return; }
    REDES.forEach(function (r) { if (r.id === red) b.href = r.url(d.url, d.titulo); });
  });

  function iniciar() {
    estilo();
    // ¿La página ya trae su propia fila dentro del contenido? Entonces el pie no repite.
    var propia = document.querySelector('main [data-share]:not([data-share-footer]), main .share-btn');
    // Botones antiguos de artículos y libros → misma fila que el resto.
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

  // Para otros scripts de la página: volver a dibujar una fila (p. ej. si cambió su data-share-url).
  window.rnCompartir = llenar;
})();
