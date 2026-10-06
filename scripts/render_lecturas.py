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


def _bloques(valor):
    """Texto del CMS -> lista de bloques (separados por una línea en blanco)."""
    if not valor:
        return []
    if isinstance(valor, list):
        return valor
    return [b.strip() for b in re.split(r"\n\s*\n", str(valor).strip()) if b.strip()]


def _lectura(l):
    out = {"tipo": l.get("tipo", "")}
    for k in ("cita", "lema", "respuesta", "presentacion", "cierre"):
        v = (l.get(k) or "").strip() if isinstance(l.get(k), str) else l.get(k)
        if v:
            out[k] = v
    texto = _bloques(l.get("texto"))
    if texto:
        out["texto"] = [" ".join(b.split()) for b in texto]
    estrofas = l.get("estrofas")
    if estrofas:
        if isinstance(estrofas, list):
            out["estrofas"] = estrofas
        else:
            out["estrofas"] = [[v.strip() for v in b.splitlines() if v.strip()] for b in _bloques(estrofas)]
    return out


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
            "fuente": d.get("fuente", ""),
            "lecturas": [_lectura(l) for l in d["lecturas"]],
        }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"dias": dias}, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("lecturas.json: %d día(s)" % len(dias))


if __name__ == "__main__":
    main()
