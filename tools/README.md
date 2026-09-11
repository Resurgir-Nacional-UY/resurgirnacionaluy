# Build de las páginas fijas

Esta carpeta es el **respaldo de continuidad** del sitio: contiene el código
fuente editable de las 4 páginas fijas (`src/index.html`, `src/vision.html`,
`src/SagradoCorazondeJesus.html`, `src/formacion.html`) y el script que las
convierte en las páginas publicadas en la raíz del repo.

Antes esto solo existía en la máquina de quien mantenía el sitio. Si esa
máquina o esa sesión se perdía, no había forma de reconstruir ni modificar el
header, el footer, el SEO o cualquier otro elemento compartido — solo se
podían tocar los artículos de Formación (que sí vivían en `content/`). Ahora
todo el sitio se puede reconstruir desde este repositorio solo.

## Editar el header, el footer o cualquier página fija

1. Editar el archivo correspondiente en `tools/src/`.
   - `src/index.html` es la fuente de verdad del "chrome" compartido: el
     `<header>`, el `<footer>`, los `<defs>` de SVG (emblema, bandera, íconos)
     y algunas reglas CSS (`.footer-legal`, `.footer-links`, `.nav-cross`).
     Cualquier cambio ahí se copia automáticamente a las demás páginas.
2. Correr, parado en la raíz del repo:
   ```
   python tools/build.py
   ```
   Requiere Python 3 y las librerías `markdown` y `pyyaml` (`pip install markdown pyyaml`).
3. Revisar los cambios (`git diff`) y commitear.

## Qué hace

- Sincroniza el chrome compartido de `src/index.html` hacia `src/vision.html`,
  `src/SagradoCorazondeJesus.html` y `src/formacion.html` (reescribe los
  anchors internos para que funcionen desde la subpágina, y marca
  `aria-current="page"` en el enlace de la página actual).
- Envuelve cada página como HTML standalone (agrega `<!doctype>`, etc.) y la
  escribe en la raíz del repo — ahí es donde GitHub Pages sirve el sitio.
- Al final corre `scripts/render_articles.py`, que genera las páginas de
  artículos de Formación, el índice `articulos.html`, `feed.xml` y
  `sitemap.xml` a partir de `content/formacion/*.md`.

Es idempotente: correrlo sin haber cambiado nada en `src/` no modifica ningún
archivo.

## Nota sobre rutas largas en Windows

Si se corre en Windows desde una carpeta con una ruta muy larga, algunos
nombres de archivo generados (slugs largos de artículos) pueden superar el
límite de 260 caracteres de Windows. `scripts/render_articles.py` ya maneja
esto internamente; no hace falta nada especial acá.
