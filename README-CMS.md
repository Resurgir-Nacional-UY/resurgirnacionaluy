# Editor de Formación (CMS)

Permite que **usuarios autorizados** publiquen artículos en la sección
*Formación* sin tocar código ni Git. Cada artículo es un archivo Markdown en
`content/formacion/`; un workflow de GitHub Actions lo convierte en página
(`/<slug>.html`) y actualiza el listado de `formacion.html`.

**Con revisión:** al guardar en el editor se abre un *Pull Request*. El artículo
se publica recién cuando alguien con permiso lo aprueba (merge).

---

## Puesta en marcha (una sola vez)

### 1. ¿Quién puede publicar?
El repo vive en la organización **Resurgir-Nacional-UY**. Cada redactor se
agrega al equipo **`redactores`** (`github.com/orgs/Resurgir-Nacional-UY/teams/redactores`
→ *Add a member*), que ya tiene permiso **Write** sobre el repo. Cada persona
necesita cuenta de GitHub.
Para exigir aprobación de un tercero: `Settings › Branches › Add branch
protection rule` sobre `main` → *Require a pull request before merging* +
*Require approvals: 1*. **OJO:** eso rompe el `git push` a `main` del workflow
`formacion.yml` salvo que agregues GitHub Actions como excepción del ruleset.

### 2. Login — YA CONFIGURADO

**«Iniciar sesión con GitHub» (un clic).** Ya está montado:
- Worker `sveltia/sveltia-cms-auth` desplegado en Cloudflare:
  **`https://sveltia-cms-auth.avvedit.workers.dev`** (cuenta CF de avvedit@gmail.com).
  Secrets del worker: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`,
  `ALLOWED_DOMAINS = resurgirnacionaluy.org, *.resurgirnacionaluy.org`.
  Redeploy: `cd C:\rn-sca && npx wrangler deploy` (o `wrangler secret put NOMBRE`).
- OAuth App **«Resurgir Nacional CMS»** en la organización
  (`github.com/organizations/Resurgir-Nacional-UY/settings/applications`) —
  callback `https://sveltia-cms-auth.avvedit.workers.dev/callback`, tokens sin
  expiración. Client ID `Ov23lipR5TYwmDvAFj2u`.
- `admin/config.yml` ya tiene `base_url` apuntando al worker.

La **primera vez** que cada redactor pulsa «Iniciar sesión con GitHub», GitHub
muestra una pantalla de permiso («Authorize Resurgir Nacional CMS») — hay que
pulsar **Authorize** una vez. Después es directo.

**Alternativa — token de acceso.** El botón «Iniciar sesión con un token de
acceso» sigue disponible: *fine-grained PAT* con *Contents: RW* + *Pull
requests: RW* sobre el repo.

### 3. Permisos de GitHub Actions — YA HECHO
Puestos en **Read and write** a nivel organización
(`Settings › Actions › General › Workflow permissions`) y repo.

---

## Uso

1. Ir a **`https://resurgirnacionaluy.org/admin/`**
2. *Sign in with GitHub*
3. *Artículos de Formación* → *New Artículo*
4. Completar Título, Slug, Fecha, Resumen, Cuerpo. Se pueden subir imágenes.
5. *Save*. Se crea un Pull Request.
6. **Publicar:** abrir ese PR en GitHub y hacer *merge*. En 1–2 min el artículo
   aparece en `/formacion.html` y en `/<slug>.html`.

Para despublicar: borrar el `.md` en `content/formacion/` (desde el editor o
GitHub). El workflow elimina la página y lo quita del listado.

---

## Sin el editor (a mano)

Crear `content/formacion/mi-slug.md`:

```markdown
---
title: "Título del artículo"
slug: "mi-slug"
date: 2026-09-15
author: "Resurgir Nacional"
summary: "Una o dos frases para el listado."
source_url: "https://x.com/ResurgirUy/status/..."   # opcional
draft: false
---

Cuerpo en **Markdown**.
```

Al hacer push a `main`, el workflow lo publica.

---

## Piezas

| Archivo | Qué es |
|---|---|
| `admin/` | Editor web (Sveltia CMS) |
| `content/formacion/*.md` | Artículos (fuente) |
| `media/formacion/` | Imágenes subidas (artículos) |
| `scripts/render_articles.py` | Genera las páginas de artículos y el listado |
| `.github/workflows/formacion.yml` | Corre el script al cambiar el contenido |
| `<slug>.html` (raíz) | Páginas de artículo generadas — no editar a mano |
| `content/pages/*.yml` | Textos e imágenes editables de las páginas fijas (fuente) |
| `media/pages/` | Imágenes/videos subidos para las páginas fijas |
| `tools/render_pages.py` | Aplica `content/pages/*.yml` sobre `tools/src/*.html` |
| `tools/build.py` | Arma el sitio completo (llama a `render_pages.py` y a `render_articles.py`) |

## Editar textos e imágenes de la portada, Visión, Fe y Formación

Desde `/admin/` hay una sección **"Páginas"** (además de "Artículos de
Formación") con un formulario por página:

- **Portada**: el texto principal del inicio y los videos de fondo.
- **Visión**: el video de fondo y **todo el texto del documento** — los
  títulos de cada sección, los párrafos, la frase destacada, los doce
  principios (título y texto de cada uno), los recuadros de la cuota y las
  siete actividades. Los principios, recuadros y actividades son una
  cantidad fija (no se pueden agregar ni quitar desde el editor, para no
  romper la numeración ni el diseño) — solo se edita su texto.
- **Fe**: las dos imágenes de fondo y **todo el texto** — bajada, oraciones
  (línea por línea) e invocaciones.
- **Formación**: el ID del video de YouTube de presentación y su miniatura.

Se edita ahí, sin tocar código — funciona igual que un artículo: al guardar
se crea un Pull Request, y se publica cuando alguien con permiso lo aprueba
(merge).
