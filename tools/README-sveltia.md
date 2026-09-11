# Actualizar el CMS (Sveltia)

`admin/sveltia-cms.js` es una copia local (vendorizada) del editor, en vez de
cargarlo desde un CDN de terceros en cada visita. Es una medida de seguridad:
el CMS maneja el login y los tokens de GitHub de cada redactor, así que no
conviene que su código pueda cambiar sin que alguien lo decida.

La contra es que **no se actualiza solo**. Cada tanto (cuando haya un cambio
que interese, o al menos un par de veces al año) conviene traer la versión
nueva:

```bash
curl -s "https://cdn.jsdelivr.net/npm/@sveltia/cms@X.Y.Z/dist/sveltia-cms.js" -o admin/sveltia-cms.js
```

Reemplazando `X.Y.Z` por la versión que se quiera (ver
`https://github.com/sveltia/sveltia-cms/releases` para el changelog).
Probar el editor en `/admin/` después de actualizar, y commitear.

Versión vendorizada actualmente: **0.209.2** (2026-09-11).
