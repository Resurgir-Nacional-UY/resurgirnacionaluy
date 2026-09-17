#!/usr/bin/env python3
"""Genera og-image-vision.jpg y og-image-formacion.jpg (miniaturas de esas
paginas fijas). Igual que og-image.jpg (portada), estas no forman parte de
render_articles.py ni render_biblioteca.py: se corren a mano cuando se
quiere cambiar el fondo o el texto.

Correr desde la raiz del repo:  python scripts/make_page_og.py
"""
import os

import og_image

ROOT = og_image.ROOT
BACKGROUND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fondo-banderas.jpg")


def main():
    og_image.make_og_image(
        "Documento del movimiento", "Visión de Resurgir Nacional",
        "Visión, valores y estructura de acción del movimiento",
        os.path.join(ROOT, "og-image-vision.jpg"), background=BACKGROUND, fmt="JPEG",
    )
    print("escrito: og-image-vision.jpg")

    og_image.make_og_image(
        "Recursos del movimiento", "Formación",
        "Material para conocer y difundir las ideas del movimiento",
        os.path.join(ROOT, "og-image-formacion.jpg"), background=BACKGROUND, fmt="JPEG",
    )
    print("escrito: og-image-formacion.jpg")


if __name__ == "__main__":
    main()
