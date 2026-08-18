#!/usr/bin/env python3













from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paint_ascii.convert import MODES, image_to_ascii


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jpg2ascii",
        description="Convierte una imagen a texto ASCII (motor JPG/PNG -> texto).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("imagen", help="ruta de la imagen (JPG, PNG, BMP...)")
    parser.add_argument(
        "-w", "--width", type=int, default=100,
        help="ancho de salida en caracteres",
    )
    parser.add_argument(
        "-m", "--mode", choices=MODES, default="classic",
        help="estilo de conversión (classic, block, binary, quad, box, mockup)",
    )
    parser.add_argument(
        "-l", "--lang", default="eng",
        help="idioma del OCR para -m mockup (instala tesseract-ocr-spa para español)",
    )
    parser.add_argument(
        "--unicode", action="store_true",
        help="usar caracteres Unicode ┌─┐│└┘ en -m mockup (por defecto ASCII +-|)",
    )
    parser.add_argument(
        "-i", "--invert", action="store_true",
        help="invertir claridad (para fondos oscuros)",
    )
    parser.add_argument(
        "-t", "--threshold", type=int, default=128,
        help="umbral 0-255 para binary/quad/box",
    )
    parser.add_argument(
        "-c", "--contrast", type=float, default=1.0,
        help="multiplicador de contraste (1.0 = normal)",
    )
    parser.add_argument(
        "-o", "--out", metavar="ARCHIVO", default=None,
        help="guardar en este archivo .txt (por defecto: junto a la imagen)",
    )
    parser.add_argument(
        "-p", "--print", dest="to_stdout", action="store_true",
        help="imprimir en consola en vez de guardar un archivo",
    )
    args = parser.parse_args(argv)

    if args.width < 1:
        parser.error("--width debe ser al menos 1")

    try:
        text = image_to_ascii(
            args.imagen,
            width=args.width,
            mode=args.mode,
            invert=args.invert,
            threshold=args.threshold,
            contrast=args.contrast,
            lang=args.lang,
            ascii_style=not args.unicode,
        )
    except FileNotFoundError:
        parser.error(f"no se encuentra la imagen: {args.imagen}")
    except ValueError as exc:
        parser.error(str(exc))
    except OSError as exc:
        parser.error(f"no se pudo leer {args.imagen}: {exc}")

    if args.to_stdout:
        print(text)
        return 0

    if args.out:
        out_path = Path(args.out)
    else:


        img_path = Path(args.imagen)
        out_path = img_path.parent / (img_path.stem + ".txt")
    try:
        out_path.write_text(text + "\n", encoding="utf-8")
    except OSError as exc:
        parser.error(f"no se pudo escribir {out_path}: {exc}")
    print(f"Guardado en {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
