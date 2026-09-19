#!/usr/bin/env python3
"""Genera admin/config-redactores.yml a partir de admin/config.yml.

Es la versión del CMS para articulistas: solo las colecciones Formación y
Biblioteca. Se abre en /admin/redactores.html. Esto solo simplifica el menú;
lo que un articulista puede publicar de verdad lo limita el ruleset de main
+ .github/CODEOWNERS (no editar el permiso aquí).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "admin", "config.yml")
DST = os.path.join(ROOT, "admin", "config-redactores.yml")

HEADER_NOTE = (
    "# GENERADO por scripts/make_admin_redactores.py desde admin/config.yml.\n"
    "# No editar a mano: se pisa en el próximo build.\n"
    "# CMS reducido para articulistas (solo Formación y Biblioteca).\n\n"
)

lines = open(SRC, encoding="utf-8").read().splitlines(keepends=True)

def find(prefix):
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    if len(idx) != 1:
        raise SystemExit("make_admin_redactores: esperaba una sola línea %r, hay %d" % (prefix, len(idx)))
    return idx[0]

i_coll = find("collections:")
i_form = find("  - name: formacion")
i_bib = find("  - name: biblioteca")
i_tienda = find("  - name: tienda")
if not (i_form < i_bib < i_tienda):
    raise SystemExit("make_admin_redactores: orden de colecciones inesperado")

out = HEADER_NOTE + "".join(lines[:i_coll + 1]) + "\n" + "".join(lines[i_form:i_tienda]).rstrip() + "\n"
with open(DST, "w", encoding="utf-8", newline="\n") as f:
    f.write(out)
print("admin/config-redactores.yml escrito")
