# Resurgir Nacional — web

Sitio del movimiento **Resurgir Nacional** (Uruguay). Lema: *La Patria o la tumba*.

## Páginas

- [`index.html`](index.html) — portada: ideario resumido, propuestas, actualidad, aportaciones y contacto.
- [`vision.html`](vision.html) — «Visión de Resurgir Nacional»: visión y valores, doce principios, estructura de acción, actividades y contacto. Transcripción del documento interno del movimiento.

## Estado

Las propuestas, la actualidad y algunos datos de la portada son **provisionales**.
La página de Visión es contenido oficial del movimiento.

## Cómo se construye

Sin compilación. Se editan los fuentes en la raíz del workspace y `build.py`
genera estas dos páginas ya envueltas (`<!doctype>`, `<meta charset>`, etc.) para
GitHub Pages, reescribiendo los enlaces absolutos a relativos.

Publicado con GitHub Pages desde la rama `main`.

## Pendiente

- Revisar «Propuestas» y «Actualidad» de la portada (hoy son ejemplos).
- Datos legales del movimiento (naturaleza jurídica, sede).
- Backend real para el formulario «Súmate».
