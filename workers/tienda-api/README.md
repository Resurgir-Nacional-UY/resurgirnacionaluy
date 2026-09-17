# Tienda API

Backend serverless (Cloudflare Worker) del carrito de la Tienda. El sitio en sí
es estático (GitHub Pages) — este Worker es la única pieza que sabe el precio
real de cada producto y confirma el pago con PayPal, para que nadie pueda
manipular el total desde el navegador. Ver el comentario al principio de
[`src/index.ts`](src/index.ts) para el detalle de las rutas.

**Importante sobre la moneda:** PayPal no admite cobrar en pesos uruguayos, así
que los precios se cargan y se cobran en **dólares (USD)**.

## Antes de arrancar

Necesitás (todo gratis para este volumen):

1. Una cuenta de **Cloudflare** — la misma que ya usan para `sveltia-cms-auth`
   (`avvedit@gmail.com`) sirve.
2. **Node.js** instalado en tu máquina (para correr `npm`/`wrangler`).
3. Credenciales de **PayPal** (Client ID + Secret) desde
   [developer.paypal.com](https://developer.paypal.com) → Apps & Credentials.
   Arrancá con las de **Sandbox** (modo prueba, sin plata real) — recién pasá a
   las de **Live** después de probar el flujo completo.
4. (Opcional, para el aviso por correo de pedidos con envío) Una cuenta de
   [Resend](https://resend.com) — plan gratis, 3.000 emails/mes.

## Pasos de deploy

Desde esta carpeta (`workers/tienda-api/`):

```bash
npm install
npx wrangler login
```

**1. Crear el namespace de KV** (guarda los pedidos):

```bash
npx wrangler kv namespace create ORDERS
```

Copiá el `id` que te devuelve y pegalo en `wrangler.toml`, reemplazando
`<ID>` en la sección `[[kv_namespaces]]`.

**2. Crear el bucket de R2** (donde van los PDF pagos — privado, no público):

```bash
npx wrangler r2 bucket create tienda-digital
```

Si le pusiste otro nombre, actualizá `bucket_name` en `wrangler.toml`.

**3. Cargar los secretos** (nunca van en el repo — uno por uno, te va a pedir
el valor por consola):

```bash
npx wrangler secret put PAYPAL_CLIENT_ID
npx wrangler secret put PAYPAL_CLIENT_SECRET
npx wrangler secret put ADMIN_TOKEN        # inventá una clave larga cualquiera, es para ver /orders
npx wrangler secret put RESEND_API_KEY     # opcional, salteá si todavía no tenés Resend
```

**4. Revisar `wrangler.toml`**: confirmá `MANIFEST_URL` (ya apunta al dominio
real), `PAYPAL_ENV = "sandbox"` (dejalo así hasta terminar de probar), y
`NOTIFY_EMAIL`/`FROM_EMAIL` si querés cambiarlos.

**5. Deploy:**

```bash
npm run deploy
```

Te va a dar una URL tipo `https://tienda-api.<tu-cuenta>.workers.dev`.

## Conectar el Worker con el sitio

En el editor del sitio (`/admin/`) → **Tienda — configuración**:

- **PayPal — Client ID**: el mismo Client ID que cargaste como secreto en el
  paso 3 (este sí es público, se usa en el navegador — el Secret nunca sale
  del Worker).
- **URL base de la función de pago**: la URL que te dio `wrangler deploy`
  (sin barra al final).

Guardá y aprobá el Pull Request que genera el CMS para que se publique.

## Subir un libro digital

Los PDF pagos **no** se suben por el CMS (quedarían públicos). Se suben a
mano al bucket de R2:

```bash
npx wrangler r2 object put tienda-digital/libros/mi-libro.pdf --file=./mi-libro.pdf
```

Después, al cargar el producto en el CMS (tipo "Libro digital"), en el campo
**"Clave del archivo en R2"** poné exactamente `libros/mi-libro.pdf` (la
misma ruta que usaste en el `put`).

## Probar antes de cobrar plata de verdad

1. `npx wrangler dev` (corre el Worker en local).
2. Con `PAYPAL_ENV = "sandbox"`, comprá un producto de prueba usando una
   [cuenta de sandbox de PayPal](https://developer.paypal.com/dashboard/accounts)
   (el Developer Dashboard te da un comprador y un vendedor de prueba, sin
   plata real).
3. Confirmá: el total cobrado es el correcto, un libro digital entrega el
   link de descarga (y no antes de pagar), y un producto físico dispara el
   email a `resurgirnacionaluruguay@gmail.com` con la dirección de envío que
   devolvió PayPal.
4. Recién ahí, cambiá `PAYPAL_ENV` a `"live"`, hacé `npm run deploy` de nuevo,
   y probá una compra real de bajo monto antes de anunciar la tienda.

## Ver pedidos como respaldo

Si un email se pierde, `GET /orders` (con el `ADMIN_TOKEN` del paso 3 como
header `Authorization: Bearer <token>`) devuelve los últimos 100 pedidos en
JSON. Por ejemplo:

```bash
curl -H "Authorization: Bearer TU_ADMIN_TOKEN" https://tienda-api.<tu-cuenta>.workers.dev/orders
```
