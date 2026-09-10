# Boletín por correo (MailerLite + RSS)

Cuando se publica un artículo en Formación, el sitio actualiza
`https://avvedit-creator.github.io/resurgirnacionaluy/feed.xml`.
MailerLite vigila ese feed y envía un correo con el enlace a cada suscriptor.

El sitio ya tiene todo lo suyo hecho:
- el feed `feed.xml` (se regenera solo en cada publicación),
- el formulario de suscripción en `formacion.html` — **oculto** hasta que
  completes los dos datos del paso 3.

Plan gratuito de MailerLite: 1.000 suscriptores y 12.000 correos por mes.

---

## 1. Cuenta y remitente

1. Crear cuenta en **mailerlite.com** (gratis).
2. `Settings › Sender identities` (o el asistente inicial): agregar y **verificar**
   un correo de envío, p. ej. `boletin@resurgirnacionaluy.org` o el Gmail del
   movimiento. Sin remitente verificado no se puede enviar.
3. Crear un **grupo**: `Subscribers › Groups › Create group` → «Boletín Formación».

## 2. Formulario de suscripción

1. `Forms › Embedded forms › Create embedded form`. Nombre: «Boletín Formación».
2. Asignarlo al grupo «Boletín Formación».
3. Dejar activado el **doble opt-in** (confirmación por correo) — es lo correcto
   legalmente y viene activado por defecto.
4. En **Preview & done → Embed form**, elegir la variante **sin JavaScript / HTML**.
   En ese código hay una URL así:

   ```
   https://assets.mailerlite.com/jsonp/123456/forms/7890123/subscribe
   ```

   Anotá los dos números: `123456` es el **ACCOUNT** y `7890123` el **FORM**.

## 3. Conectar el formulario del sitio

En `formacion.html`:

1. Reemplazar `__ML_ACCOUNT__` por el número ACCOUNT y `__ML_FORM__` por el FORM.
2. Quitar el atributo `hidden` de `<section class="boletin" hidden>`.
3. `python build.py`, luego commit y push.

(O pasarle esos dos números a quien mantiene el sitio y lo hace en un minuto.)

El formulario ya está maquetado con el estilo del sitio y muestra un
«¡Gracias! Revisá tu correo…» al enviar. La baja la gestiona MailerLite.

## 4. Envío automático al publicar (campaña RSS)

1. `Campaigns › Create campaign › RSS campaign`.
2. **RSS feed URL:**
   `https://avvedit-creator.github.io/resurgirnacionaluy/feed.xml`
3. **Cuándo enviar:** «cuando haya un ítem nuevo» si está disponible; si no,
   una revisión diaria.
4. **Destinatarios:** grupo «Boletín Formación».
5. **Contenido del correo:** asunto sugerido `Nuevo artículo — {$rss_item_title}`;
   cuerpo con el título, el resumen (`{$rss_item_description}`) y un botón al
   artículo (`{$rss_item_url}`). Los nombres exactos de las variables aparecen
   en el editor RSS de MailerLite.
6. Guardar y **activar**.

> Si la campaña RSS no estuviera en el plan gratuito vigente: alternativa sin
> costo con el mismo `feed.xml` → **follow.it** (los suscriptores se anotan en
> su formulario y follow.it hace el envío; no gestionás la lista).

## 5. Probar

Publicar un artículo de prueba (`draft: false`), esperar a que MailerLite
detecte el feed (unos minutos u horas según la frecuencia), confirmar que llega
el correo, y borrar el artículo de prueba.

---

## Si cambia el dominio

Si el sitio pasa a `resurgirnacionaluy.org`, actualizar la constante `SITE`
en `scripts/render_articles.py` y la URL del feed en la campaña RSS.
