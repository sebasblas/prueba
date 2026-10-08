# Libros para colorear KDP

Programa para armar libros para colorear listos para Amazon KDP (tapa blanda 6" x 9", con sangrado).

## Cómo armar un libro

```
pip install pillow reportlab
python3 download_images.py cozy-cryptids   # baja los dibujos de Magnific
python3 build_book.py cozy-cryptids        # arma los PDF
```

Resultado en `cozy-cryptids/output/`:

| Archivo | Para qué |
|---|---|
| `interior.pdf` | Manuscrito (6.125" x 9.25" con sangrado, 34 páginas) |
| `cover_fullwrap.pdf` | Portada completa para subir a KDP |
| `cover_preview.png` | Vista previa con líneas de corte (rojo), lomo (celeste) y código de barras (naranja) |
| `CAMPOS_KDP_AMAZON.txt` | Todo lo que va en cada campo de KDP |

## Nuevo libro

Copia la carpeta `cozy-cryptids`, cambia `book.json` (título, textos, palabras clave) y
`scenes.txt` (una escena por línea), pon los dibujos como `pages/p01.png`, `pages/p02.png`...
y la portada como `cover/front.png` y `cover/back.png`.
