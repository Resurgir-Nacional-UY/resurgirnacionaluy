#!/usr/bin/env python3
"""Junta content/calendario/AAAA-MM.yml en /calendario.json.

La pestaña "Calendario" de la página Fe (catolicismo-en-uruguay.html) lee ese JSON
en el navegador y muestra el mes de hoy (hora de Uruguay): la imagen del
calendario y la lista día por día en texto (para buscadores y lectores de pantalla).

Uso (desde la raiz del repo):
    python scripts/render_calendario.py
"""
import glob
import io
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "calendario")
OUT = os.path.join(ROOT, "calendario.json")
MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
TIPOS = {"domingo", "fiesta", "memoria-obligatoria", "memoria-libre", "martirologio", "feria", "evento"}


def fail(msg):
    sys.exit("ERROR: " + msg)


def main():
    meses = {}
    # Sveltia puede guardar con extension .yaml: se leen ambas.
    paths = glob.glob(os.path.join(SRC, "*.yml")) + glob.glob(os.path.join(SRC, "*.yaml"))
    for path in sorted(paths):
        name = os.path.splitext(os.path.basename(path))[0]
        with io.open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        if d.get("draft"):
            continue
        mes = str(d.get("mes", ""))
        if not MES.match(mes) or mes != name:
            fail("%s: 'mes' debe ser AAAA-MM y coincidir con el nombre del archivo" % path)
        imagen = (d.get("imagen") or "").strip()
        if not imagen:
            fail("%s: falta la imagen del calendario" % path)
        if not os.path.exists(os.path.join(ROOT, imagen.lstrip("/"))):
            fail("%s: no existe la imagen %s" % (path, imagen))
        dias, vistos = [], set()
        for x in d.get("dias") or []:
            n = int(x.get("dia"))
            if not 1 <= n <= 31 or n in vistos:
                fail("%s: día %s repetido o fuera de rango" % (path, n))
            vistos.add(n)
            tipo = x.get("tipo")
            if tipo not in TIPOS:
                fail("%s: día %d: tipo '%s' no válido (%s)" % (path, n, tipo, ", ".join(sorted(TIPOS))))
            item = {"dia": n, "nombre": (x.get("nombre") or "").strip(), "tipo": tipo}
            for k in ("tambien", "detalle"):
                if (x.get(k) or "").strip():
                    item[k] = x[k].strip()
            dias.append(item)
        dias.sort(key=lambda i: i["dia"])
        meses[mes] = {
            "titulo": (d.get("titulo") or "").strip(),
            "imagen": imagen,
            "imagen_alt": " ".join(str(d.get("imagen_alt") or "").split()),
            "nota": " ".join(str(d.get("nota") or "").split()),
            "dias": dias,
        }
    data = json.dumps({"meses": meses}, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if not os.path.exists(OUT) or io.open(OUT, encoding="utf-8").read() != data:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(data)
    print("calendario.json: %d mes(es)" % len(meses))


if __name__ == "__main__":
    main()
