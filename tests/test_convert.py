"""Tests del motor JPG -> ASCII (paint_ascii.convert)."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from jpg2ascii import main
from paint_ascii.convert import MODES, image_to_ascii

TMP = Path(__file__).parent / "_mockup_test.png"


def _make_mockup(path: Path = TMP, with_box: bool = True) -> Path:
    """Genera una imagen de prueba: fondo blanco + caja negra + texto."""
    img = Image.new("RGB", (200, 100), "white")
    draw = ImageDraw.Draw(img)
    if with_box:
        draw.rectangle((20, 15, 180, 85), outline="black", width=3)
    draw.text((60, 40), "Hola", fill="black")
    img.save(path, "PNG")
    return path


class ConvertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.img = _make_mockup()

    @classmethod
    def tearDownClass(cls):
        cls.img.unlink(missing_ok=True)

    def test_modes_are_known(self):
        self.assertEqual(
            MODES, ("classic", "block", "binary", "quad", "box", "mockup")
        )

    def test_classic_width_and_lines(self):
        text = image_to_ascii(self.img, width=80, mode="classic")
        lines = text.splitlines()
        self.assertTrue(lines)
        self.assertTrue(all(len(line) == 80 for line in lines))

    def test_box_mode_uses_box_characters(self):
        text = image_to_ascii(self.img, width=80, mode="box")
        for ch in "┌┐└┘─│":
            self.assertIn(ch, text)

    def test_binary_only_two_chars(self):
        text = image_to_ascii(self.img, width=80, mode="binary")
        lines = text.splitlines()
        self.assertTrue(all(ch in "# " for line in lines for ch in line))

    def test_box_nested_boxes_make_t_junctions(self):
        # Caja interior apoyada en el borde superior de la exterior: uniones T.
        img = Image.new("RGB", (200, 100), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle((20, 15, 180, 85), outline="black", width=3)
        draw.rectangle((60, 15, 140, 50), outline="black", width=3)
        path = Path(__file__).parent / "_mockup_nested.png"
        img.save(path, "PNG")
        try:
            text = image_to_ascii(path, width=80, mode="box")
        finally:
            path.unlink(missing_ok=True)
        for ch in "┬├┤┴┼":
            self.assertIn(ch, text)

    def test_quad_uses_block_elements(self):
        text = image_to_ascii(self.img, width=80, mode="quad")
        self.assertTrue(any(ch in "▀▄█▌▐" for ch in text))

    def test_invert_changes_output(self):
        normal = image_to_ascii(self.img, width=40, mode="classic")
        flipped = image_to_ascii(self.img, width=40, mode="classic", invert=True)
        self.assertNotEqual(normal, flipped)

    def test_threshold_affects_binary(self):
        low = image_to_ascii(self.img, width=40, mode="binary", threshold=10)
        high = image_to_ascii(self.img, width=40, mode="binary", threshold=250)
        self.assertNotEqual(low, high)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            image_to_ascii(Path("/no/existe.jpg"), width=40)

    @unittest.skipUnless(shutil.which("tesseract"), "tesseract no instalado")
    def test_mockup_places_ocr_text(self):
        """End-to-end: el texto de la imagen aparece legible en la salida."""
        img = Image.new("RGB", (300, 100), "white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 32)
        except OSError:
            self.skipTest("fuente DejaVuSans no disponible")
        draw.text((20, 30), "Hola mundo", fill="black", font=font)
        path = Path(__file__).parent / "_mockup_text.png"
        img.save(path, "PNG")
        try:
            text = image_to_ascii(path, width=80, mode="mockup")
        finally:
            path.unlink(missing_ok=True)
        self.assertIn("Hola", text)
        self.assertIn("mundo", text)

    def test_mockup_draws_clean_boxes(self):
        """El modo mockup dibuja recuadros limpios (ASCII +-| por defecto)."""
        img = Image.new("RGB", (300, 150), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle((30, 20, 270, 130), outline="black", width=3)
        draw.rectangle((60, 50, 200, 100), outline="black", width=3)
        path = Path(__file__).parent / "_mockup_boxes.png"
        img.save(path, "PNG")
        try:
            text = image_to_ascii(path, width=80, mode="mockup")
        finally:
            path.unlink(missing_ok=True)
        for ch in "+-|":
            self.assertIn(ch, text)
        # Los bordes deben verse limpios y abundantes.
        self.assertGreater(text.count("-"), 10)
        self.assertGreater(text.count("|"), 4)

    def test_mockup_slanted_boxes(self):
        """Bordes ligeramente inclinados (dibujados a mano) también se detectan."""
        img = Image.new("RGB", (300, 150), "white")
        draw = ImageDraw.Draw(img)
        # Rectángulo con el lateral DERECHO inclinado (x=253 arriba, x=247 abajo):
        # simula un trazo manual que rompería los runs verticales contiguos.
        pts = [(40, 20), (253, 20), (247, 130), (40, 127)]
        draw.polygon(pts, outline="black", width=3)
        path = Path(__file__).parent / "_mockup_slanted.png"
        img.save(path, "PNG")
        try:
            text = image_to_ascii(path, width=80, mode="mockup")
        finally:
            path.unlink(missing_ok=True)
        for ch in "+-|":
            self.assertIn(ch, text)
        self.assertGreater(text.count("-"), 10)

    def test_mockup_unicode_style(self):
        """Con ascii_style=False el modo mockup usa caracteres Unicode."""
        img = Image.new("RGB", (300, 150), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle((30, 20, 270, 130), outline="black", width=3)
        path = Path(__file__).parent / "_mockup_unicode.png"
        img.save(path, "PNG")
        try:
            text = image_to_ascii(path, width=80, mode="mockup", ascii_style=False)
        finally:
            path.unlink(missing_ok=True)
        for ch in "┌┐└┘─│":
            self.assertIn(ch, text)

    def test_cli_saves_txt_next_to_image(self):
        """Sin -o, la CLI guarda el .txt en la misma carpeta que la imagen."""
        tmpdir = Path(tempfile.mkdtemp(prefix="jpg2ascii_"))
        try:
            img = tmpdir / "mockup.png"
            shutil.copy(self.img, img)
            rc = main([str(img), "-w", "40", "-m", "binary"])
            out = tmpdir / "mockup.txt"
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists(), "debería crear mockup.txt junto a la imagen")
            self.assertIn("#", out.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_cli_stdout_with_print_flag(self):
        """Con --print, imprime en consola y no crea archivo."""
        tmpdir = Path(tempfile.mkdtemp(prefix="jpg2ascii_print_"))
        try:
            img = tmpdir / "mockup.png"
            shutil.copy(self.img, img)
            buf = StringIO()
            with redirect_stdout(buf):
                rc = main([str(img), "-w", "40", "-m", "binary", "--print"])
            self.assertEqual(rc, 0)
            self.assertIn("#", buf.getvalue())
            self.assertFalse((tmpdir / "mockup.txt").exists())
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_cli_no_suffix_image_name(self):
        """Nombres de imagen sin extensión no deben romper la ruta de salida."""
        tmpdir = Path(tempfile.mkdtemp(prefix="jpg2ascii_nosuffix_"))
        try:
            img = tmpdir / "prueba"
            shutil.copy(self.img, img)
            rc = main([str(img), "-w", "40", "-m", "binary"])
            self.assertEqual(rc, 0)
            self.assertTrue((tmpdir / "prueba.txt").exists())
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
