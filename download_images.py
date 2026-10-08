#!/usr/bin/env python3
"""Descarga las imagenes listadas en <carpeta>/urls.txt.  Uso: python3 download_images.py cozy-cryptids"""
import sys
import urllib.request
from pathlib import Path

folder = Path(__file__).resolve().parent / sys.argv[1]
for line in (folder / "urls.txt").read_text().split("\n"):
    if not line.strip():
        continue
    dest, url = line.split(" ", 1)
    out = folder / dest
    if out.exists():
        continue
    out.parent.mkdir(parents=True, exist_ok=True)
    print("Descargando", dest)
    urllib.request.urlretrieve(url, out)
print("Listo")
