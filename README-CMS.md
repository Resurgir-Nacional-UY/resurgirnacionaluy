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
`Settings › Collaborators` del repo → **Add people**. Cada persona necesita
cuenta de GitHub. Rol **Write**.
Para exigir aprobación de un tercero: `Settings › Branches › Add branch
protection rule` sobre `main` → *Require a pull request before merging* +
*Require approvals: 1*. (Ver también el paso 3.)

### 2. Login

**Opción rápida (sin infraestructura) — token de acceso.**
En `/admin/` elegir *«Iniciar sesión con un token de acceso»*. Cada persona
autorizada crea un *fine-grained PAT* en GitHub
(`Settings › Developer settings › Fine-grained tokens`): acceso *Only select
repositories → resurgirnacionaluy*, permiso *Contents: Read and write* y
*Pull requests: Read and write*. Se pega en el editor. Es lo más simple para
empezar; la contra es que el token caduca y cada quien gestiona el suyo.
Con esta opción **no hace falta** el resto del paso 2.

**Opción cómoda — «Iniciar sesión con GitHub» (worker de OAuth).**
Da login de un clic, sin tokens. Requiere el worker oficial
**`sveltia/sveltia-cms-auth`** en Cloudflare (plan gratis).

1. **GitHub OAuth App**: tu cuenta → `Settings › Developer settings ›
   OAuth Apps › New OAuth App`
   - *Homepage URL*: `https://avvedit-creator.github.io/resurgirnacionaluy/`
   - *Authorization callback URL*: `https://TU-WORKER.workers.dev/callback`
     (se ajusta después de crear el worker)
   - Guardar **Client ID** y generar un **Client Secret**.
2. **Cloudflare Worker**: cuenta gratis en Cloudflare → desplegar
   `github.com/sveltia/sveltia-cms-auth` (su README tiene botón *Deploy to
   Cloudflare*, o usar `wrangler`). Variables del worker:
   - `GITHUB_CLIENT_ID` = Client ID
   - `GITHUB_CLIENT_SECRET` = Client Secret
   - `ALLOWED_DOMAINS` = `avvedit-creator.github.io`
3. Copiar el callback real (`https://TU-WORKER.workers.dev/callback`) a la
   OAuth App.
4. En **`admin/config.yml`** cambiar
   `base_url: https://REEMPLAZAR-POR-TU-WORKER.workers.dev`
   por la URL real del worker y commitear.

### 3. Permisos de GitHub Actions
`Settings › Actions › General › Workflow permissions` →
**Read and write permissions** → *Save*.
(El workflow necesita commitear las páginas generadas.)
Si activaste protección de rama en el paso 1, agregá a `resurgir-bot` /
GitHub Actions como excepción, **o** cambiá el `git push` del workflow por la
creación de un PR.

---

## Uso

1. Ir a **`https://avvedit-creator.github.io/resurgirnacionaluy/admin/`**
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
| `media/formacion/` | Imágenes subidas |
| `scripts/render_articles.py` | Genera las páginas y el listado |
| `.github/workflows/formacion.yml` | Corre el script al cambiar el contenido |
| `<slug>.html` (raíz) | Páginas generadas — no editar a mano |
