/**
 * Tienda API — Resurgir Nacional
 *
 * Backend serverless (Cloudflare Worker) para el carrito de la Tienda. El
 * sitio es 100% estatico (GitHub Pages), asi que el navegador NUNCA le dice
 * el precio a PayPal directamente -- este Worker es el unico lugar que
 * calcula el total real (leyendo tienda-manifest.json, que genera
 * scripts/render_tienda.py en cada build) y confirma el pago del lado del
 * servidor. Asi nadie puede pagar de menos manipulando el JS del navegador.
 *
 * Rutas:
 *   POST /create-order   -> crea la orden en PayPal con el total verificado
 *   POST /capture-order  -> confirma el cobro, guarda el pedido, entrega
 *                           los libros digitales pagados
 *   GET  /download        -> sirve un PDF digital via un link temporal
 *                           (emitido solo por /capture-order, no adivinable)
 *   GET  /orders          -> lista de pedidos recientes (protegida con
 *                           ADMIN_TOKEN), respaldo si se pierde el email
 *
 * Ver README.md en esta carpeta para los pasos de deploy.
 */

export interface Env {
  ORDERS: KVNamespace;
  DIGITAL_BOOKS: R2Bucket;
  MANIFEST_URL: string;
  ALLOWED_ORIGIN: string;
  NOTIFY_EMAIL: string;
  FROM_EMAIL: string;
  PAYPAL_ENV: string; // "sandbox" | "live"
  PAYPAL_CLIENT_ID: string;
  PAYPAL_CLIENT_SECRET: string;
  RESEND_API_KEY?: string;
  ADMIN_TOKEN?: string;
}

interface ManifestProduct {
  slug: string;
  title: string;
  price: number;
  type: string;
  stock: number | null;
  variants: string[];
  digital: boolean;
  asset_key: string | null;
}

interface CartItemIn {
  slug: string;
  variant?: string | null;
  qty: number;
}

interface PendingLine {
  slug: string;
  title: string;
  variant: string | null;
  qty: number;
  price: number;
  digital: boolean;
  assetKey: string | null;
}

const MAX_LINES = 20;
const MAX_QTY = 50;
const DOWNLOAD_TTL_SECONDS = 15 * 60;
const PENDING_TTL_SECONDS = 60 * 60 * 24;

function corsHeaders(env: Env): HeadersInit {
  return {
    "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };
}

function json(env: Env, data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders(env) },
  });
}

function paypalBase(env: Env): string {
  return env.PAYPAL_ENV === "live"
    ? "https://api-m.paypal.com"
    : "https://api-m.sandbox.paypal.com";
}

async function paypalToken(env: Env): Promise<string> {
  const auth = btoa(`${env.PAYPAL_CLIENT_ID}:${env.PAYPAL_CLIENT_SECRET}`);
  const res = await fetch(`${paypalBase(env)}/v1/oauth2/token`, {
    method: "POST",
    headers: {
      Authorization: `Basic ${auth}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: "grant_type=client_credentials",
  });
  if (!res.ok) {
    throw new Error("paypal auth failed: " + (await res.text()));
  }
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

async function fetchManifest(env: Env): Promise<ManifestProduct[]> {
  const res = await fetch(env.MANIFEST_URL, {
    cf: { cacheTtl: 30, cacheEverything: true },
  });
  if (!res.ok) throw new Error("manifest fetch failed");
  return (await res.json()) as ManifestProduct[];
}

class CartError extends Error {}

function validateCart(
  items: CartItemIn[],
  manifest: ManifestProduct[]
): { total: number; hasPhysical: boolean; lines: PendingLine[] } {
  if (!Array.isArray(items) || items.length === 0) {
    throw new CartError("El carrito está vacío.");
  }
  if (items.length > MAX_LINES) {
    throw new CartError("Demasiados productos distintos en un mismo pedido.");
  }
  const bySlug = new Map(manifest.map((p) => [p.slug, p]));
  let total = 0;
  let hasPhysical = false;
  const lines: PendingLine[] = [];
  for (const it of items) {
    const p = bySlug.get(String(it.slug || ""));
    if (!p) throw new CartError("Producto no encontrado: " + it.slug);
    const qty = Math.floor(Number(it.qty));
    if (!Number.isFinite(qty) || qty <= 0 || qty > MAX_QTY) {
      throw new CartError("Cantidad inválida para " + p.title);
    }
    let variant: string | null = null;
    if (p.variants && p.variants.length) {
      variant = it.variant ? String(it.variant) : null;
      if (!variant || !p.variants.includes(variant)) {
        throw new CartError("Elegí una opción válida para " + p.title);
      }
    }
    if (p.stock !== null && p.stock !== undefined && qty > p.stock) {
      throw new CartError("No hay stock suficiente de " + p.title);
    }
    total += p.price * qty;
    if (p.type !== "libro_digital") hasPhysical = true;
    lines.push({
      slug: p.slug,
      title: p.title,
      variant,
      qty,
      price: p.price,
      digital: p.digital,
      assetKey: p.asset_key,
    });
  }
  return { total: Math.round(total * 100) / 100, hasPhysical, lines };
}

async function handleCreateOrder(req: Request, env: Env): Promise<Response> {
  let body: { items: CartItemIn[] };
  try {
    body = await req.json();
  } catch {
    return json(env, { error: "Solicitud inválida." }, 400);
  }

  let manifest: ManifestProduct[];
  try {
    manifest = await fetchManifest(env);
  } catch {
    return json(env, { error: "No pudimos leer el catálogo. Probá de nuevo." }, 502);
  }

  let cart;
  try {
    cart = validateCart(body.items, manifest);
  } catch (e) {
    const msg = e instanceof CartError ? e.message : "Carrito inválido.";
    return json(env, { error: msg }, 400);
  }

  let token: string;
  try {
    token = await paypalToken(env);
  } catch {
    return json(env, { error: "No pudimos conectar con PayPal." }, 502);
  }

  const purchaseUnit: Record<string, unknown> = {
    amount: { currency_code: "USD", value: cart.total.toFixed(2) },
  };

  const orderRes = await fetch(`${paypalBase(env)}/v2/checkout/orders`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      intent: "CAPTURE",
      purchase_units: [purchaseUnit],
      application_context: {
        shipping_preference: cart.hasPhysical ? "GET_FROM_FILE" : "NO_SHIPPING",
      },
    }),
  });
  if (!orderRes.ok) {
    return json(env, { error: "PayPal no pudo iniciar el pago." }, 502);
  }
  const order = (await orderRes.json()) as { id: string };

  // Guarda el detalle REAL del carrito (precios del manifest, no del
  // navegador) para usarlo al capturar el pago -- capture-order nunca vuelve
  // a confiar en nada que mande el cliente salvo el orderID.
  await env.ORDERS.put(
    "pending:" + order.id,
    JSON.stringify({
      items: cart.lines,
      total: cart.total,
      hasPhysical: cart.hasPhysical,
      createdAt: new Date().toISOString(),
    }),
    { expirationTtl: PENDING_TTL_SECONDS }
  );

  return json(env, { id: order.id });
}

async function issueDownloadUrl(
  env: Env,
  req: Request,
  assetKey: string,
  filename: string
): Promise<string> {
  const token = crypto.randomUUID();
  await env.ORDERS.put(
    "dl:" + token,
    JSON.stringify({ key: assetKey, filename }),
    { expirationTtl: DOWNLOAD_TTL_SECONDS }
  );
  const origin = new URL(req.url).origin;
  return `${origin}/download?token=${token}`;
}

async function notifyOwner(
  env: Env,
  order: {
    id: string;
    items: PendingLine[];
    total: number;
    payer: { name?: string; email?: string };
    shipping: unknown;
    hasPhysical: boolean;
  }
): Promise<void> {
  if (!env.RESEND_API_KEY) return;
  const itemsList = order.items
    .map((i) => `- ${i.title}${i.variant ? " (" + i.variant + ")" : ""} x${i.qty} — US$ ${i.price.toFixed(2)}`)
    .join("\n");
  let shippingText = "Sin productos físicos en este pedido.";
  if (order.hasPhysical) {
    const s = order.shipping as
      | { name?: { full_name?: string }; address?: Record<string, string> }
      | null;
    if (s && s.address) {
      const a = s.address;
      shippingText =
        `${s.name?.full_name || "(sin nombre)"}\n` +
        `${a.address_line_1 || ""} ${a.address_line_2 || ""}\n` +
        `${a.admin_area_2 || ""}, ${a.admin_area_1 || ""} ${a.postal_code || ""}\n` +
        `${a.country_code || ""}`;
    } else {
      shippingText = "Hay un producto físico pero PayPal no devolvió la dirección — escribile al comprador.";
    }
  }
  const text =
    `Nuevo pedido #${order.id}\n\n` +
    `Productos:\n${itemsList}\n\n` +
    `Total: US$ ${order.total.toFixed(2)}\n` +
    `Comprador: ${order.payer.name || "(sin nombre)"} <${order.payer.email || "sin email"}>\n\n` +
    `ENVÍO:\n${shippingText}`;

  try {
    await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: env.FROM_EMAIL,
        to: env.NOTIFY_EMAIL,
        subject: `Nuevo pedido en la Tienda — US$ ${order.total.toFixed(2)}`,
        text,
      }),
    });
  } catch {
    // El pedido ya quedo guardado en KV (/orders) aunque el email falle.
  }
}

async function handleCaptureOrder(req: Request, env: Env): Promise<Response> {
  let body: { orderID?: string };
  try {
    body = await req.json();
  } catch {
    return json(env, { error: "Solicitud inválida." }, 400);
  }
  if (!body.orderID) return json(env, { error: "Falta el ID de la orden." }, 400);

  const pendingRaw = await env.ORDERS.get("pending:" + body.orderID);
  if (!pendingRaw) {
    return json(env, { error: "Esa orden no existe o ya venció." }, 400);
  }
  const pending = JSON.parse(pendingRaw) as {
    items: PendingLine[];
    total: number;
    hasPhysical: boolean;
  };

  let token: string;
  try {
    token = await paypalToken(env);
  } catch {
    return json(env, { error: "No pudimos conectar con PayPal." }, 502);
  }

  const capRes = await fetch(
    `${paypalBase(env)}/v2/checkout/orders/${body.orderID}/capture`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    }
  );
  const capData = (await capRes.json()) as {
    status?: string;
    payer?: { name?: { given_name?: string; surname?: string }; email_address?: string };
    purchase_units?: { shipping?: unknown }[];
  };
  if (!capRes.ok || capData.status !== "COMPLETED") {
    return json(env, { error: "El pago no se pudo confirmar." }, 402);
  }

  const payerName = capData.payer?.name
    ? `${capData.payer.name.given_name || ""} ${capData.payer.name.surname || ""}`.trim()
    : undefined;
  const shipping = capData.purchase_units?.[0]?.shipping || null;

  const downloads: { slug: string; url: string }[] = [];
  for (const item of pending.items) {
    if (!item.digital || !item.assetKey) continue;
    const url = await issueDownloadUrl(env, req, item.assetKey, item.slug + ".pdf");
    downloads.push({ slug: item.slug, url });
  }

  const orderRecord = {
    id: body.orderID,
    items: pending.items,
    total: pending.total,
    payer: { name: payerName, email: capData.payer?.email_address },
    shipping,
    hasPhysical: pending.hasPhysical,
    capturedAt: new Date().toISOString(),
  };
  await env.ORDERS.put("order:" + body.orderID, JSON.stringify(orderRecord));
  await env.ORDERS.delete("pending:" + body.orderID);

  if (pending.hasPhysical) {
    // Solo pedidos con algo fisico necesitan que alguien lo despache;
    // notifyOwner tambien es un no-op si falta RESEND_API_KEY.
    await notifyOwner(env, orderRecord);
  }

  return json(env, { ok: true, downloads, hasPhysical: pending.hasPhysical });
}

async function handleDownload(req: Request, env: Env): Promise<Response> {
  const url = new URL(req.url);
  const token = url.searchParams.get("token");
  if (!token) return new Response("Falta el link de descarga.", { status: 400 });
  const raw = await env.ORDERS.get("dl:" + token);
  if (!raw) {
    return new Response(
      "Este link de descarga venció (dura 15 minutos). Escribinos si necesitás uno nuevo.",
      { status: 404 }
    );
  }
  const { key, filename } = JSON.parse(raw) as { key: string; filename: string };
  const obj = await env.DIGITAL_BOOKS.get(key);
  if (!obj) return new Response("No encontramos el archivo. Escribinos.", { status: 404 });
  return new Response(obj.body, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="${filename}"`,
    },
  });
}

async function handleOrders(req: Request, env: Env): Promise<Response> {
  const auth = req.headers.get("Authorization") || "";
  if (!env.ADMIN_TOKEN || auth !== `Bearer ${env.ADMIN_TOKEN}`) {
    return json(env, { error: "No autorizado." }, 401);
  }
  const list = await env.ORDERS.list({ prefix: "order:", limit: 100 });
  const orders = await Promise.all(
    list.keys.map(async (k) => {
      const raw = await env.ORDERS.get(k.name);
      return raw ? JSON.parse(raw) : null;
    })
  );
  return json(env, { orders: orders.filter(Boolean) });
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);

    if (req.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(env) });
    }

    try {
      if (url.pathname === "/create-order" && req.method === "POST") {
        return await handleCreateOrder(req, env);
      }
      if (url.pathname === "/capture-order" && req.method === "POST") {
        return await handleCaptureOrder(req, env);
      }
      if (url.pathname === "/download" && req.method === "GET") {
        return await handleDownload(req, env);
      }
      if (url.pathname === "/orders" && req.method === "GET") {
        return await handleOrders(req, env);
      }
    } catch (e) {
      return json(env, { error: "Error inesperado del servidor." }, 500);
    }

    return json(env, { error: "No encontrado." }, 404);
  },
};
