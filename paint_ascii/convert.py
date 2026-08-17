"""Motor de conversión de imágenes a texto ASCII (JPG/PNG -> texto).

Flujo de trabajo recomendado (mockup en paint -> ASCII):
    1. Dibuja el mockup en Pinta/KolourPaint y guárdalo como JPG (o PNG).
    2. Convierte:  python jpg2ascii.py mockup.jpg -w 100 -m quad -o mockup.txt
    3. Retoca:     python -m paint_ascii mockup.txt

Modos:
    classic  Rampa clásica de brillo  " .:-=+*#%@"  (fotos y cualquier imagen)
    block    Bloques de relleno       " ░▒▓█"       (sombras y degradados)
    binary   Alto contraste           "#" / espacio
    quad     Bloques 2x2              (máxima fidelidad; buen texto)
    box      Caracteres de caja       ─│┌┐└┘┼       (mockups con recuadros)
    mockup   Recuadros + texto OCR    ┌─┐│└┘ + texto (copia casi exacta)
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


RAMP_CLASSIC = " .:-=+*#%@"
RAMP_BLOCK = " ░▒▓█"


QUADS = {
    0b0000: " ",
    0b0001: "▗",
    0b0010: "▖",
    0b0011: "▄",
    0b0100: "▝",
    0b0101: "▐",
    0b0110: "▞",
    0b0111: "▟",
    0b1000: "▘",
    0b1001: "▚",
    0b1010: "▌",
    0b1011: "▙",
    0b1100: "▀",
    0b1101: "▜",
    0b1110: "▛",
    0b1111: "█",
}

MODES = ("classic", "block", "binary", "quad", "box", "mockup")


OCR_LANG = "eng"



CHAR_ASPECT = 0.5



_MAX_POOL_SOURCE = 4_000_000


def image_to_ascii(
    path: str | Path,
    width: int = 100,
    mode: str = "classic",
    invert: bool = False,
    threshold: int = 128,
    contrast: float = 1.0,
    lang: str = OCR_LANG,
    ascii_style: bool = True,
) -> str:
    """Convierte una imagen a texto ASCII y devuelve las líneas con \\n."""
    if mode not in MODES:
        raise ValueError(f"modo desconocido: {mode!r} (válidos: {', '.join(MODES)})")

    img = Image.open(path)
    img = ImageOps.exif_transpose(img)

    if mode == "mockup":

        return _render_mockup(
            img,
            width=width,
            threshold=threshold,
            invert=invert,
            lang=lang,
            ascii_style=ascii_style,
        )

    img = img.convert("L")
    if invert:
        img = ImageOps.invert(img)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)

    src_w, src_h = img.size
    height = max(1, round(src_h / src_w * width * CHAR_ASPECT))

    if mode in ("classic", "block", "binary"):
        if mode == "binary":
            grid = _min_pool(img, width, height)
            return "\n".join(
                "".join("#" if v < threshold else " " for v in row) for row in grid
            )
        ramp = RAMP_CLASSIC if mode == "classic" else RAMP_BLOCK
        small = img.resize((width, height), Image.Resampling.LANCZOS)
        px = small.load()
        n = len(ramp)
        return "\n".join(
            "".join(ramp[(255 - px[x, y]) * (n - 1) // 255] for x in range(width))
            for y in range(height)
        )

    if mode == "quad":

        cols, rows = width * 2, height * 2
        grid = _min_pool(img, cols, rows)
        lines = []
        for y in range(0, rows, 2):
            line = []
            for x in range(0, cols, 2):
                bits = 0
                if grid[y][x] < threshold:
                    bits |= 0b1000
                if grid[y][x + 1] < threshold:
                    bits |= 0b0100
                if grid[y + 1][x] < threshold:
                    bits |= 0b0010
                if grid[y + 1][x + 1] < threshold:
                    bits |= 0b0001
                line.append(QUADS[bits])
            lines.append("".join(line))
        return "\n".join(lines)


    return _render_box_grid(img, width, height, threshold)


def _min_pool(img: Image.Image, cols: int, rows: int) -> list[list[int]]:
    """Reduce la imagen a cols×rows tomando el píxel más oscuro de cada celda.

    Conserva líneas finas (1 px) que un promedio diluiría: sirve para
    convertir mockups dibujados con trazos finos.
    """
    if img.width * img.height > _MAX_POOL_SOURCE:
        ratio = (_MAX_POOL_SOURCE / (img.width * img.height)) ** 0.5
        img = img.resize(
            (max(1, round(img.width * ratio)), max(1, round(img.height * ratio))),
            Image.Resampling.LANCZOS,
        )
    src_w, src_h = img.size
    data = img.tobytes()
    pooled = []
    for ty in range(rows):
        y0 = ty * src_h // rows
        y1 = max(y0 + 1, (ty + 1) * src_h // rows)
        line = []
        for tx in range(cols):
            x0 = tx * src_w // cols
            x1 = max(x0 + 1, (tx + 1) * src_w // cols)
            best = 255
            for yy in range(y0, y1):
                base = yy * src_w
                for xx in range(x0, x1):
                    v = data[base + xx]
                    if v < best:
                        best = v
                        if best == 0:
                            break
                if best == 0:
                    break
            line.append(best)
        pooled.append(line)
    return pooled


def _box_cell(grid: list[list[bool]], w: int, h: int, x: int, y: int) -> str:
    """Clasifica una celda oscura como línea, esquina, cruce o relleno."""

    def at(dx: int, dy: int) -> bool:
        nx, ny = x + dx, y + dy
        return 0 <= nx < w and 0 <= ny < h and grid[ny][nx]

    if not at(0, 0):
        return " "

    if all(at(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)):
        return "█"

    left, right, up, down = at(-1, 0), at(1, 0), at(0, -1), at(0, 1)
    n = left + right + up + down

    if n == 4:
        return "┼"
    if n == 3:
        if not left:
            return "┤"
        if not right:
            return "├"
        if not up:
            return "┬"
        return "┴"
    if left and right:
        return "─"
    if up and down:
        return "│"
    if n == 2:
        if right and down:
            return "┌"
        if left and down:
            return "┐"
        if right and up:
            return "└"
        if left and up:
            return "┘"
    if n == 1:
        return "─" if (left or right) else "│"
    return "▓"





def _render_mockup(
    img: Image.Image,
    width: int = 100,
    threshold: int = 128,
    invert: bool = False,
    lang: str = OCR_LANG,
    ascii_style: bool = True,
) -> str:
    """Modo mockup: recuadros limpios + texto legible vía OCR.

    Detecta los bordes de las cajas en la cuadrícula binarizada y los dibuja
    con caracteres de caja (ASCII +-| por defecto, Unicode ┌─┐ con
    ascii_style=False), y coloca el texto leído por tesseract agrupado en
    líneas compactas en su posición original. Requiere `tesseract` instalado.
    """
    img_gray = img.convert("L")
    if invert:
        img_gray = ImageOps.invert(img_gray)
    src_w, src_h = img_gray.size
    height = max(1, round(src_h / src_w * width * CHAR_ASPECT))

    grid = [[v < threshold for v in row] for row in _min_pool(img_gray, width, height)]
    rects = _merge_rects(_find_rectangles(grid))

    canvas = [[" "] * width for _ in range(height)]


    for x0, y0, x1, y1 in sorted(
        rects, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]), reverse=True
    ):
        _draw_box(canvas, x0, y0, x1, y1, ascii_style=ascii_style)

    for left_px, top_px, text in _group_words_into_lines(_ocr_words(img, lang=lang)):
        gx = round(left_px * width / src_w)
        gy = round(top_px * height / src_h)
        _put_text(canvas, gx, gy, text)

    if not rects and not any(c.isalnum() for row in canvas for c in row):

        return _render_box_grid(img_gray, width, height, threshold)
    return "\n".join("".join(row).rstrip() for row in canvas)


def _render_box_grid(img: Image.Image, width: int, height: int, threshold: int) -> str:
    """Renderiza la cuadrícula con el clasificador de celdas (modo box)."""
    grid = [[v < threshold for v in row] for row in _min_pool(img, width, height)]
    return "\n".join(
        "".join(_box_cell(grid, width, height, x, y) for x in range(width)).rstrip()
        for y in range(height)
    )


def _find_horizontal_lines(grid: list[list[bool]], min_len: int) -> list[tuple[int, int, int]]:
    """Segmentos horizontales: (y, x0, x1) con longitud >= min_len."""
    h, w = len(grid), len(grid[0])
    lines = []
    for y in range(h):
        row = grid[y]
        x = 0
        while x < w:
            if row[x]:
                x0 = x
                while x < w and row[x]:
                    x += 1
                x1 = x - 1
                if x1 - x0 + 1 >= min_len:
                    lines.append((y, x0, x1))
            else:
                x += 1
    return lines


def _find_rectangles(grid: list[list[bool]]) -> list[tuple[int, int, int, int]]:
    """Detecta recuadros (bordes de caja) en la cuadrícula binaria.

    Empareja un borde superior e inferior horizontales y comprueba que los
    lados izquierdo y derecho estén mayormente oscuros entre ambos, con
    tolerancia para bordes inclinados o antialias (los dibujados a mano en
    Pinta suelen estar ligeramente torcidos). Devuelve (x0, y0, x1, y1).
    """
    h, w = len(grid), len(grid[0])
    h_min = max(2, int(w * 0.05))
    h_lines = _find_horizontal_lines(grid, h_min)

    rects: list[tuple[int, int, int, int]] = []
    for i, (y_top, xt0, xt1) in enumerate(h_lines):
        for y_bot, xb0, xb1 in h_lines[i + 1:]:
            if y_bot - y_top < 2:
                continue
            left = max(xt0, xb0)
            right = min(xt1, xb1)
            if right - left < 2:
                continue
            if _side_solid(grid, left, y_top, y_bot) and _side_solid(
                grid, right, y_top, y_bot
            ):
                rects.append((left, y_top, right, y_bot))
    return rects


def _side_solid(
    grid: list[list[bool]], x: int, y_top: int, y_bot: int, tol: int = 1, ratio: float = 0.75
) -> bool:
    """True si la columna x (con tolerancia) está mayormente oscura en el tramo.

    En vez de exigir una línea vertical contigua (frágil con bordes
    inclinados), cuenta cuántas filas del tramo tienen píxel oscuro cerca
    de x y exige una cobertura >= ratio.
    """
    n = y_bot - y_top + 1
    best = 0
    for dx in range(-tol, tol + 1):
        cx = x + dx
        if not (0 <= cx < len(grid[0])):
            continue
        cnt = sum(1 for y in range(y_top, y_bot + 1) if grid[y][cx])
        best = max(best, cnt)
    return best >= max(2, int(n * ratio))


def _merge_rects(rects: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Une recuadros casi idénticos (p. ej. bordes de 2 celdas de grosor) y
    descarta los demasiado delgados (ruido de líneas sueltas)."""
    merged: list[tuple[int, int, int, int]] = []
    for x0, y0, x1, y1 in rects:
        if x1 - x0 < 3 or y1 - y0 < 2:
            continue
        added = False
        for i, (a, b, c, d) in enumerate(merged):
            if abs(a - x0) <= 2 and abs(b - y0) <= 2 and abs(c - x1) <= 2 and abs(d - y1) <= 2:
                merged[i] = (min(a, x0), min(b, y0), max(c, x1), max(d, y1))
                added = True
                break
        if not added:
            merged.append((x0, y0, x1, y1))
    return merged


def _draw_box(
    canvas: list[list[str]], x0: int, y0: int, x1: int, y1: int, ascii_style: bool = True
) -> None:
    """Dibuja un recuadro: ASCII (+-|) por defecto o Unicode (┌─┐│└┘)."""
    if ascii_style:
        tl = tr = bl = br = "+"
        hch, vch = "-", "|"
    else:
        tl, tr, bl, br = "┌", "┐", "└", "┘"
        hch, vch = "─", "│"

    for x in range(x0, x1 + 1):
        if canvas[y0][x] == " ":
            canvas[y0][x] = hch if x0 < x < x1 else (tl if x == x0 else tr)
        if canvas[y1][x] == " ":
            canvas[y1][x] = hch if x0 < x < x1 else (bl if x == x0 else br)
    for y in range(y0 + 1, y1):
        if canvas[y][x0] == " ":
            canvas[y][x0] = vch
        if canvas[y][x1] == " ":
            canvas[y][x1] = vch


def _group_words_into_lines(
    words: list[tuple[int, int, int, int, str]],
) -> list[tuple[int, int, str]]:
    """Agrupa palabras del OCR en líneas (mismo top aprox) y las une con espacios.

    Devuelve [(left, top, texto)] por línea: el texto queda compacto
    ("lady gaga reina") en vez de esparcido por los bounding boxes.
    """
    if not words:
        return []
    heights = [w[3] for w in words]
    tol = max(2, int((sum(heights) / len(heights)) * 0.6))
    lines: list[list[tuple[int, int, int, int, str]]] = []
    for word in sorted(words, key=lambda w: (w[1], w[0])):
        for line in lines:
            if abs(line[0][1] - word[1]) <= tol:
                line.append(word)
                break
        else:
            lines.append([word])
    result: list[tuple[int, int, str]] = []
    for line in lines:
        ordered = sorted(line, key=lambda w: w[0])
        text = " ".join(w[4] for w in ordered)
        left = min(w[0] for w in ordered)
        top = min(w[1] for w in ordered)
        result.append((left, top, text))
    return result


def _put_text(canvas: list[list[str]], gx: int, gy: int, text: str) -> None:
    """Coloca texto en el lienzo sin pisar los bordes ya dibujados."""
    if gy < 0 or gy >= len(canvas):
        return
    for i, ch in enumerate(text):
        x = gx + i
        if 0 <= x < len(canvas[0]) and canvas[gy][x] == " ":
            canvas[gy][x] = ch


def _ocr_words(img: Image.Image, lang: str = OCR_LANG) -> list[tuple[int, int, int, int, str]]:
    """OCR con tesseract: devuelve [(left, top, width, height, texto)].

    Usa la salida TSV para obtener la posición de cada palabra. Si tesseract
    no está instalado, devuelve lista vacía (el modo mockup solo dibuja cajas).
    """
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return []


    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        base = Image.new("RGBA", img.size, (255, 255, 255, 255))
        base.alpha_composite(img.convert("RGBA"))
        img = base.convert("RGB")
    else:
        img = img.convert("RGB")
    scale = 2 if max(img.size) < 1000 else 1
    big = img.resize((img.width * scale, img.height * scale), Image.Resampling.LANCZOS)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ocr.png"
            big.save(path)
            proc = subprocess.run(
                [tesseract, str(path), "stdout", "tsv", "-l", lang, "--psm", "11"],
                capture_output=True,
                text=True,
                timeout=120,
            )
    except (OSError, subprocess.SubprocessError):
        return []

    words: list[tuple[int, int, int, int, str]] = []
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        try:
            conf = float(parts[10])
            text = parts[11].strip()
        except ValueError:
            continue
        if not text or conf < 30 or not any(c.isalnum() for c in text):
            continue
        left, top = int(parts[6]) // scale, int(parts[7]) // scale
        w, h = int(parts[8]) // scale, int(parts[9]) // scale
        words.append((left, top, w, h, text))
    return words
