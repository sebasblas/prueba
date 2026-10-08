#!/usr/bin/env python3
"""Arma un libro para colorear listo para Amazon KDP (paperback).

Uso:  python3 build_book.py <carpeta-del-libro>

La carpeta debe tener:
  book.json        configuracion (titulo, autor, textos, colores)
  scenes.txt       una escena por linea (solo informativo / prompts)
  pages/pNN.png    dibujos en blanco y negro (p01.png, p02.png, ...)
  cover/front.png  arte a color de la portada (sin texto)
  cover/back.png   arte a color de la contraportada (opcional)

Genera en <carpeta>/output/:
  interior.pdf         manuscrito con sangrado
  cover_fullwrap.pdf   portada completa (contraportada + lomo + portada)
  cover_preview.png    vista previa con guias de corte y zona del codigo de barras
  CAMPOS_KDP_AMAZON.txt
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "cozy-cryptids" / "fonts"
DPI = 300
PT = 72

# Grosor de pagina en pulgadas segun KDP (help topic G201953020)
PAPER_THICKNESS = {
    "white_bw": 0.002252,
    "cream_bw": 0.0025,
    "white_color": 0.002347,
}
PAPER_LABEL = {
    "white_bw": "Black & white interior with white paper",
    "cream_bw": "Black & white interior with cream paper",
    "white_color": "Premium color interior with white paper",
}

# Margen de seguridad: KDP pide >= 0.375" desde el borde con sangrado y
# >= 0.375" de medianil para 24-150 paginas. Usamos 0.5" para ir sobrados.
SAFE_IN = 0.5


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def register_fonts():
    for n in ["LuckiestGuy-Regular", "Sniglet-Regular", "Sniglet-ExtraBold", "PatrickHand-Regular"]:
        pdfmetrics.registerFont(TTFont(n, str(FONTS / f"{n}.ttf")))


def clean_lineart(path, box_w_px, box_h_px):
    """Convierte el dibujo a lineas negras puras sobre blanco y lo ajusta a la caja."""
    im = Image.open(path).convert("L")
    scale = min(box_w_px / im.width, box_h_px / im.height)
    if abs(scale - 1) > 0.01:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    # Umbral suave: blancos casi puros a blanco, conserva antialias de las lineas
    im = im.point(lambda v: 255 if v > 200 else (0 if v < 60 else v))
    return im


def centered(c, text, y, fontname, size, page_w):
    c.setFont(fontname, size)
    c.drawCentredString(page_w / 2, y, text)


def wrap(text, fontname, size, max_w):
    lines = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w in words:
            t = (line + " " + w).strip()
            if pdfmetrics.stringWidth(t, fontname, size) <= max_w:
                line = t
            else:
                lines.append(line)
                line = w
        lines.append(line)
    return lines


def build_interior(book, folder, out):
    trim_w, trim_h = book["trim_in"]
    bleed = book["bleed_in"]
    pw, ph = (trim_w + bleed) * PT, (trim_h + 2 * bleed) * PT
    c = canvas.Canvas(str(out), pagesize=(pw, ph))
    c.setTitle(f"{book['title']}: {book['subtitle']}")
    c.setAuthor(f"{book['author_first']} {book['author_last']}")
    author = f"{book['author_first']} {book['author_last']}"
    pages = 0

    def new_page():
        nonlocal pages
        c.showPage()
        pages += 1

    # 1. Portadilla
    centered(c, book["title"].upper(), ph * 0.62, "LuckiestGuy-Regular", 40, pw)
    y = ph * 0.62 - 40
    for line in wrap(book["subtitle"], "Sniglet-Regular", 15, pw - 2 * SAFE_IN * PT - 20):
        centered(c, line, y, "Sniglet-Regular", 15, pw)
        y -= 20
    centered(c, f"by {author}", ph * 0.25, "PatrickHand-Regular", 18, pw)
    new_page()

    # 2. Copyright
    c.setFont("PatrickHand-Regular", 10.5)
    lines = [
        f"{book['title']}: {book['subtitle']}",
        f"Copyright © {book['year']} {author}. All rights reserved.",
        "",
        "No part of this book may be reproduced, stored or transmitted in any form",
        "or by any means without written permission from the author, except for",
        "brief quotations in reviews. Coloring pages may be colored and shared",
        "for personal, non-commercial use.",
        "",
        "Tip: place a sheet of paper behind the page you are coloring",
        "to protect the next illustration from markers and bleed-through.",
    ]
    y = ph * 0.30
    for ln in lines:
        c.drawString(SAFE_IN * PT + 6, y, ln)
        y -= 14
    new_page()

    # 3. Este libro pertenece a
    centered(c, "THIS BOOK", ph * 0.60, "LuckiestGuy-Regular", 34, pw)
    centered(c, "BELONGS TO", ph * 0.60 - 40, "LuckiestGuy-Regular", 34, pw)
    c.setLineWidth(1.5)
    c.line(SAFE_IN * PT + 30, ph * 0.40, pw - SAFE_IN * PT - 30, ph * 0.40)
    new_page()

    # 4..N. Dibujos
    box_w, box_h = pw - 2 * SAFE_IN * PT, ph - 2 * SAFE_IN * PT
    box_w_px, box_h_px = round(box_w / PT * DPI), round(box_h / PT * DPI)
    page_files = sorted((folder / "pages").glob("p*.png"))
    n_scenes = len((folder / "scenes.txt").read_text().strip().splitlines())
    missing = []
    for i in range(1, n_scenes + 1):
        f = folder / "pages" / f"p{i:02d}.png"
        if f.exists():
            im = clean_lineart(f, box_w_px, box_h_px)
            w, h = im.width / DPI * PT, im.height / DPI * PT
            c.drawImage(ImageReader(im), (pw - w) / 2, (ph - h) / 2, w, h)
        else:
            missing.append(i)
            c.setDash(4, 4)
            c.rect(SAFE_IN * PT, SAFE_IN * PT, box_w, box_h)
            c.setDash()
            centered(c, f"MISSING PAGE {i}", ph / 2, "Sniglet-ExtraBold", 20, pw)
        new_page()

    # Ultima: gracias + resena
    centered(c, "THANK YOU!", ph * 0.62, "LuckiestGuy-Regular", 36, pw)
    for k, ln in enumerate([
        "We hope you had a cozy time coloring",
        "with the cryptids.",
        "",
        "If you enjoyed this book, a short review on Amazon",
        "would mean the world and helps other colorists find it.",
    ]):
        centered(c, ln, ph * 0.52 - k * 18, "PatrickHand-Regular", 14, pw)
    new_page()

    if pages % 2:
        new_page()  # KDP: numero par de paginas
    c.save()
    return pages, missing, len(page_files)


def cover_size(book, pages):
    trim_w, trim_h = book["trim_in"]
    bleed = book["bleed_in"]
    spine = pages * PAPER_THICKNESS[book["paper"]]
    return 2 * trim_w + spine + 2 * bleed, trim_h + 2 * bleed, spine


def fill_crop(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, t, l + w, t + h))


def outlined_text(draw, xy, text, fnt, fill, outline, width, anchor="mm"):
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor,
              stroke_width=width, stroke_fill=outline)


def fit_font(name, text, max_w, start):
    size = start
    while size > 10 and font(name, size).getlength(text) > max_w:
        size -= 2
    return font(name, size)


def build_cover(book, folder, pages, out_pdf, out_preview):
    W_in, H_in, spine_in = cover_size(book, pages)
    trim_w, _ = book["trim_in"]
    bleed = book["bleed_in"]
    W, H = round(W_in * DPI), round(H_in * DPI)
    back_w = round((bleed + trim_w) * DPI)
    spine_px = round(spine_in * DPI)
    front_x = back_w + spine_px
    front_w = W - front_x
    col = book["cover_colors"]

    canvas_im = Image.new("RGB", (W, H), col["panel"])
    front_src = folder / "cover" / "front.png"
    back_src = folder / "cover" / "back.png"
    if front_src.exists():
        front = Image.open(front_src).convert("RGB")
        canvas_im.paste(fill_crop(front, front_w, H), (front_x, 0))
        back = Image.open(back_src).convert("RGB") if back_src.exists() else \
            front.filter(ImageFilter.GaussianBlur(25))
        canvas_im.paste(fill_crop(back, back_w + spine_px, H), (0, 0))
    d = ImageDraw.Draw(canvas_im, "RGBA")
    safe = round((bleed + 0.25) * DPI)

    # Portada: titulo, subtitulo, autor
    cx = front_x + (front_w - round(bleed * DPI)) // 2
    max_w = front_w - round(bleed * DPI) - 2 * safe
    sub_lines, line = [], ""
    sf = font("Sniglet-ExtraBold.ttf", 64)
    for w in book["subtitle"].split():
        t = (line + " " + w).strip()
        if sf.getlength(t) <= max_w:
            line = t
        else:
            sub_lines.append(line)
            line = w
    sub_lines.append(line)
    panel_bottom = safe + 410 + 84 * (len(sub_lines) - 1) + 70
    d.rounded_rectangle((front_x + safe - 30, safe - 20, W - safe - round(bleed * DPI) + 30, panel_bottom),
                        radius=60, fill=(20, 10, 35, 150))
    tf = fit_font("LuckiestGuy-Regular.ttf", book["title"].upper(), max_w, 260)
    outlined_text(d, (cx, safe + 200), book["title"].upper(), tf, col["title"], col["title_outline"], 14)
    y = safe + 410
    for ln in sub_lines:
        outlined_text(d, (cx, y), ln, sf, col["subtitle"], col["title_outline"], 6)
        y += 84
    af = font("Sniglet-ExtraBold.ttf", 78)
    author = f"by {book['author_first']} {book['author_last']}"
    aw = af.getlength(author)
    d.rounded_rectangle((cx - aw / 2 - 40, H - safe - 150, cx + aw / 2 + 40, H - safe),
                        radius=40, fill=(20, 10, 35, 170))
    outlined_text(d, (cx, H - safe - 75), author, af, col["subtitle"], col["title_outline"], 4)

    # Contraportada: texto + zona libre para el codigo de barras (2" x 1.2")
    bx0 = round(bleed * DPI) + safe - round(bleed * DPI) + 40
    bx1 = back_w - safe
    bf = font("Sniglet-Regular.ttf", 50)
    text_lines = []
    for para in book["back_blurb"].split("\n"):
        if not para.strip():
            text_lines.append("")
            continue
        line = ""
        for w in para.split():
            t = (line + " " + w).strip()
            if bf.getlength(t) <= bx1 - bx0 - 80:
                line = t
            else:
                text_lines.append(line)
                line = w
        text_lines.append(line)
    lh = 64
    box_h = len(text_lines) * lh + 120
    by0 = safe + 40
    d.rounded_rectangle((bx0, by0, bx1, by0 + box_h), radius=50, fill=(255, 250, 240, 225))
    y = by0 + 60
    for ln in text_lines:
        d.text((bx0 + 40, y), ln, font=bf, fill="#2A1A3A")
        y += lh
    barcode = (back_w - safe - round(2.0 * DPI), H - safe - round(1.2 * DPI), back_w - safe, H - safe)
    d.rectangle(barcode, fill="white")

    canvas_im.save(out_pdf, "PDF", resolution=DPI, quality=92)

    prev = canvas_im.copy()
    pd = ImageDraw.Draw(prev)
    b = round(bleed * DPI)
    pd.rectangle((b, b, W - b, H - b), outline="red", width=6)
    pd.line((back_w, 0, back_w, H), fill="cyan", width=6)
    pd.line((front_x, 0, front_x, H), fill="cyan", width=6)
    pd.rectangle(barcode, outline="orange", width=8)
    prev.thumbnail((1800, 1800))
    prev.save(out_preview)
    return W_in, H_in, spine_in


def print_cost(book, pages):
    # Tarifas KDP Amazon.com (vigentes desde jun-2025), tamano normal <= 6.12 x 9"
    if book["paper"] in ("white_bw", "cream_bw"):
        return 2.30 if pages <= 108 else 1.00 + 0.012 * pages
    return 0.85 + 0.07 * pages if pages <= 40 else 1.00 + 0.07 * pages


def write_fields(book, pages, W_in, H_in, spine_in, out):
    cost = print_cost(book, pages)
    trim = f'{book["trim_in"][0]}" x {book["trim_in"][1]}"'
    rows = []
    for price in (7.99, 8.99, 9.99, 11.99, 12.99):
        rows.append(f"    ${price:<7} | -${cost:.2f} | 60% = ${price*0.6:.2f} | ROYALTY = ${price*0.6-cost:.2f}")
    kw = "\n".join(f"    Keyword {i+1}: {k}" for i, k in enumerate(book["keywords"]))
    cats = "\n".join(f"    Category {i+1}: {k}" for i, k in enumerate(book["categories"]))
    text = f"""==============================================================================
            FIELDS FOR PUBLISHING ON AMAZON KDP  -  PAPERBACK
==============================================================================

SECTION 1: BOOK DETAILS
------------------------------------------------------------------------------
1. Language ............ English
2. Book title .......... {book['title']}
3. Subtitle ............ {book['subtitle']}
   (Title + subtitle must match the cover exactly)
4. Series .............. (none)
5. Edition number ...... 1
6. Author .............. First name: {book['author_first']}   Last name: {book['author_last']}
7. Contributors ........ (none)

8. Description (HTML):
{book['description_html']}

9. Publishing rights ... I own the copyright and I hold necessary publishing rights
10. Primary audience ... Sexually explicit: No | Low-content book: No
    Reading age: leave empty (adult coloring book)
11. Primary marketplace  Amazon.com

12. Categories (choose up to 3):
{cats}

13. Keywords (7):
{kw}

SECTION 2: PAPERBACK CONTENT
------------------------------------------------------------------------------
14. ISBN ............... Get a free KDP ISBN
15. Publication date ... leave empty (= date you publish)
16. Print options:
    Ink and paper ...... {PAPER_LABEL[book['paper']]}
    Trim size .......... {trim}  (MUST be exactly this, or the cover is rejected)
    Bleed settings ..... Bleed (PDF only)
    Cover finish ....... Glossy
17. Manuscript ......... output/interior.pdf  ({pages} pages)
18. Book cover ......... "Upload a cover you already have" -> output/cover_fullwrap.pdf
    Cover size ......... {W_in:.3f}" x {H_in:.3f}"  (spine {spine_in:.4f}")
    No spine text (KDP only allows it from 79 pages).
19. AI-generated content: YES
    Images: "Many AI-generated images with extensive editing" -> tool: Magnific (Seedream)
    Text: "Some AI-generated sections" if you used AI for the description

SECTION 3: PRICING (Amazon.com, 60% royalty)
------------------------------------------------------------------------------
    Printing cost: ${cost:.2f} ({pages} pages, {PAPER_LABEL[book['paper']].lower()})
{chr(10).join(rows)}

    Recommended list price: $8.99
    Verify in KDP's calculator before publishing; rates can change.

FINAL CHECKLIST
------------------------------------------------------------------------------
[ ] Trim size {trim} with Bleed selected
[ ] Interior PDF uploaded, previewer shows no errors
[ ] Full-wrap cover uploaded, barcode area is clear (bottom-right of back)
[ ] Title/subtitle/author identical to the cover
[ ] AI content declared
"""
    out.write_text(text)


def main():
    folder = (ROOT / sys.argv[1]).resolve()
    book = json.loads((folder / "book.json").read_text())
    out = folder / "output"
    out.mkdir(exist_ok=True)
    register_fonts()
    pages, missing, found = build_interior(book, folder, out / "interior.pdf")
    W_in, H_in, spine_in = build_cover(book, folder, pages, out / "cover_fullwrap.pdf", out / "cover_preview.png")
    write_fields(book, pages, W_in, H_in, spine_in, out / "CAMPOS_KDP_AMAZON.txt")
    print(f"Interior: {pages} pages ({found} drawings, missing: {missing or 'none'})")
    print(f'Cover: {W_in:.3f}" x {H_in:.3f}"  spine {spine_in:.4f}"')
    if not (folder / "cover" / "front.png").exists():
        print("WARNING: cover/front.png missing (cover has plain background)")


if __name__ == "__main__":
    main()
