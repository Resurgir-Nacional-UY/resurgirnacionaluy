#!/usr/bin/env python3
"""Genera og-image.png (miniatura al compartir la portada del sitio).

A diferencia de og/<slug>.png (uno por articulo/libro, generados en cada
build), esta es la unica imagen de la portada: se corre a mano cuando se
quiere cambiar el fondo o el texto. No forma parte de render_articles.py
ni render_biblioteca.py.

Correr desde la raiz del repo:  python scripts/make_home_og.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

import og_image  # reusa _cover, _left_scrim, _lp, fuentes

ROOT = og_image.ROOT
FONTS = og_image.FONTS
BACKGROUND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fondo-banderas.jpg")
SEAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "seal-badge.png")
OUT = os.path.join(ROOT, "og-image.png")

W, H = 1200, 630
GOLD = (212, 177, 94)
WHITE = (244, 242, 234)
MUTED = (214, 221, 232)


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def main():
    bg = og_image._cover(Image.open(og_image._lp(BACKGROUND)).convert("RGB"), W, H).convert("RGBA")
    bg.alpha_composite(og_image._left_scrim(W, H, color=(10, 24, 48), start_alpha=225, end_alpha=60))

    seal = Image.open(og_image._lp(SEAL)).convert("RGBA")
    seal_d = 346
    seal = seal.resize((seal_d, seal_d), Image.LANCZOS)
    seal_x, seal_y = 96, (H - seal_d) // 2
    bg.alpha_composite(seal, (seal_x, seal_y))

    draw = ImageDraw.Draw(bg)
    text_x = seal_x + seal_d + 78

    title_font = _font("Archivo-Bold.ttf", 68)
    draw.text((text_x, 222), "RESURGIR", font=title_font, fill=WHITE)
    draw.text((text_x, 292), "NACIONAL", font=title_font, fill=WHITE)

    line_y = 372
    draw.line((text_x, line_y, text_x + 300, line_y), fill=GOLD, width=3)

    sub_font = _font("Archivo-Bold.ttf", 27)
    draw.text((text_x, line_y + 20), "Movimiento nacionalista del Uruguay", font=sub_font, fill=GOLD)

    tag_font = _font("Archivo-Medium.ttf", 22)
    draw.text((text_x, line_y + 62), "· La Patria o la tumba ·", font=tag_font, fill=MUTED)

    bg.convert("RGB").save(og_image._lp(OUT), "PNG", optimize=True)
    print("escrito:", OUT)


if __name__ == "__main__":
    main()
