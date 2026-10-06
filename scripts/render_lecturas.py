#!/usr/bin/env python3
"""Junta content/lecturas/AAAA-MM-DD.yml en /lecturas.json.

La página Fe (catolicismo-en-uruguay.html) lee ese JSON en el navegador y muestra
la lectura de la fecha de hoy en Uruguay. Si no hay archivo para hoy, la sección
queda oculta.

Uso (desde la raíz del repo):
    python scripts/render_lecturas.py
"""
import glob
import io
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "lecturas")
OUT = os.path.join(ROOT, "lecturas.json")
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main():
    dias = {}
    for path in sorted(glob.glob(os.path.join(SRC, "*.yml"))):
        name = os.path.splitext(os.path.basename(path))[0]
        with io.open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        if d.get("draft"):
            continue
        fecha = str(d.get("fecha", ""))
        if not FECHA.match(fecha) or fecha != name:
            sys.exit("ERROR: %s: 'fecha' debe ser AAAA-MM-DD y coincidir con el nombre del archivo" % path)
        if not d.get("lecturas"):
            sys.exit("ERROR: %s: falta 'lecturas'" % path)
        dias[fecha] = {
            "celebracion": d.get("celebracion", ""),
            "santo": d.get("santo", ""),
            "lecturas": d["lecturas"],
        }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"dias": dias}, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("lecturas.json: %d día(s)" % len(dias))


if __name__ == "__main__":
    main()
