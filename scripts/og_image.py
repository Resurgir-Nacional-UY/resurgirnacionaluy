#!/usr/bin/env python3
"""Genera la imagen social (og:image) de cada articulo de Formacion.

Cada articulo tiene su propia tarjeta 1200x630 con su titulo real, en vez de
reutilizar siempre el mismo og-image.jpg generico del sitio. Se llama desde
render_articles.py; no tiene dependencias fuera de Pillow + los assets de
este repo (fuentes locales + favicon-192.png), asi que corre igual en CI.
"""
import os
from PIL import Image, ImageDraw, ImageFont


def _lp(p):
    """En Windows, rutas >= 260 chars necesitan el prefijo \\\\?\\. No-op en Linux (CI)."""
    p = os.path.abspath(p)
    if os.name == "nt" and len(p) >= 255 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + p
    return p


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
EMBLEM = os.path.join(ROOT, "favicon-192.png")
BACKGROUND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fondo-minia.jpg")
BACKGROUND_BIBLIOTECA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fondo-biblioteca.jpg")

W, H = 1200, 630
PAD = 72

NAVY_TOP = (36, 87, 156)      # #24579C
NAVY_MID = (27, 63, 115)      # #1B3F73
NAVY_BOTTOM = (20, 49, 92)    # #14315C
GOLD = (212, 177, 94)         # #D4B15E
WHITE = (244, 242, 234)       # #F4F2EA
MUTED = (170, 187, 212)


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def _wrap(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_title(draw, text, max_width, max_lines=3, start=64, minimum=38):
    size = start
    while size >= minimum:
        font = _font("Fraunces-SemiBold.ttf", size)
        lines = _wrap(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines, size
        size -= 2
    # ultima pasada al tamano minimo: recorta con puntos suspensivos
    font = _font("Fraunces-SemiBold.ttf", minimum)
    lines = _wrap(draw, text, font, max_width)[:max_lines]
    if lines:
        last = lines[-1]
        while draw.textlength(last + "…", font=font) > max_width and len(last) > 1:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return font, lines, minimum


def _vertical_gradient(w, h, stops):
    """stops: lista de (pos_0_a_1, color_rgb)."""
    img = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        lo, hi = stops[0], stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                lo, hi = stops[i], stops[i + 1]
                break
        span = max(hi[0] - lo[0], 1e-6)
        f = (t - lo[0]) / span
        c = tuple(int(lo[1][k] + (hi[1][k] - lo[1][k]) * f) for k in range(3))
        img.putpixel((0, y), c)
    return img.resize((w, h))


def _cover(img, w, h):
    """Escala la imagen para cubrir w x h y recorta el sobrante centrado."""
    scale = max(w / img.width, h / img.height)
    rw, rh = round(img.width * scale), round(img.height * scale)
    img = img.resize((rw, rh), Image.LANCZOS)
    x0 = (rw - w) // 2
    y0 = (rh - h) // 2
    return img.crop((x0, y0, x0 + w, y0 + h))


def _left_scrim(w, h, color=(13, 32, 62), start_alpha=232, end_alpha=10):
    """Velo degradado de izquierda (oscuro, para el texto) a derecha (claro)."""
    row = Image.new("RGBA", (w, 1))
    for x in range(w):
        t = (x / max(w - 1, 1)) ** 1.25
        a = int(start_alpha + (end_alpha - start_alpha) * t)
        row.putpixel((x, 0), color + (a,))
    return row.resize((w, h))


def _background(w, h, background=BACKGROUND):
    if background and os.path.exists(background):
        bg = _cover(Image.open(background).convert("RGB"), w, h).convert("RGBA")
    else:
        bg = _vertical_gradient(w, h, [(0.0, NAVY_TOP), (0.5, NAVY_MID), (1.0, NAVY_BOTTOM)]).convert("RGBA")
    bg.alpha_composite(_left_scrim(w, h))
    return bg


def make_og_image(kicker, title, byline, out_path, background=BACKGROUND, fmt=None):
    """kicker: p.ej. 'Formacion . Articulo'. title/byline: texto plano."""
    img = _background(W, H, background)

    draw = ImageDraw.Draw(img)

    # Fila de marca: icono + "RESURGIR NACIONAL"
    if os.path.exists(EMBLEM):
        icon = Image.open(EMBLEM).convert("RGBA").resize((56, 56), Image.LANCZOS)
        img.alpha_composite(icon, (PAD, PAD))
    brand_font = _font("Archivo-Bold.ttf", 25)
    draw.text((PAD + 56 + 18, PAD + 14), "RESURGIR NACIONAL", font=brand_font, fill=WHITE)

    # Kicker (categoria)
    kicker_font = _font("Archivo-Bold.ttf", 24)
    kicker_y = PAD + 56 + 46
    draw.text((PAD, kicker_y), kicker.upper(), font=kicker_font, fill=GOLD)

    # Titulo
    max_w = W - PAD * 2
    title_font, lines, size = _fit_title(draw, title, max_w, max_lines=3, start=66, minimum=38)
    line_h = int(size * 1.18)
    title_y = kicker_y + 56
    for i, line in enumerate(lines):
        draw.text((PAD, title_y + i * line_h), line, font=title_font, fill=WHITE)

    # Linea de fecha / autor
    byline_font = _font("Archivo-Medium.ttf", 24)
    byline_y = title_y + len(lines) * line_h + 22
    draw.text((PAD, byline_y), byline, font=byline_font, fill=MUTED)

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(_lp(out_dir), exist_ok=True)
    # JPEG: con fondo fotografico (bandera), un PNG pesa 700-800KB y WhatsApp
    # no genera vista previa con imagenes tan pesadas. En JPEG calidad 85 el
    # mismo diseno pesa ~100-150KB, sin perdida visible.
    # OJO: no inferir el formato de la extension de out_path -- los llamadores
    # suelen escribir primero a "<final>.tmp" (ext ".tmp") y renombrar despues,
    # asi que hay que pasar `fmt` explicito en vez de confiar en el sniffing.
    real_fmt = fmt or ("JPEG" if os.path.splitext(out_path)[1].lower() in (".jpg", ".jpeg") else "PNG")
    if real_fmt == "JPEG":
        img.convert("RGB").save(_lp(out_path), "JPEG", quality=85, optimize=True)
    else:
        img.convert("RGB").save(_lp(out_path), "PNG", optimize=True)
