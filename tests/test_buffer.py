

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from paint_ascii.buffer import Buffer


class TestBuffer(unittest.TestCase):
    def test_cell_out_of_bounds_returns_space(self) -> None:
        b = Buffer()
        self.assertEqual(b.cell(0, 0), " ")
        self.assertEqual(b.cell(10, 10), " ")

    def test_set_cell_grows_rows_and_columns(self) -> None:
        b = Buffer()
        b.set_cell(2, 1, "x")
        self.assertEqual(b.height, 2)
        self.assertEqual(b.width, 3)
        self.assertEqual(b.cell(2, 1), "x")
        self.assertEqual(b.cell(0, 1), " ")

    def test_insert_delete_split(self) -> None:
        b = Buffer(["abc"])
        b.insert_char(1, 0, "Z")
        self.assertEqual(b.rows[0], "aZbc")
        b.delete_cell(1, 0)
        self.assertEqual(b.rows[0], "abc")
        b.split_row(1, 0)
        self.assertEqual(b.rows, ["a", "bc"])

    def test_draw_box(self) -> None:
        b = Buffer()
        b.draw_box((0, 0), (3, 2))
        self.assertEqual(b.to_text(), "┌──┐\n│  │\n└──┘")

    def test_draw_box_reversed_corners(self) -> None:
        b = Buffer()
        b.draw_box((3, 2), (0, 0))
        self.assertEqual(b.to_text(), "┌──┐\n│  │\n└──┘")

    def test_draw_line_horizontal_and_vertical(self) -> None:
        b = Buffer()
        b.draw_line((0, 0), (4, 0))
        self.assertEqual(b.to_text(), "─────")

        b2 = Buffer()
        b2.draw_line((0, 0), (0, 2))
        self.assertEqual(b2.to_text(), "│\n│\n│")

    def test_draw_line_thick(self) -> None:
        b = Buffer()
        b.draw_line((0, 0), (3, 0), thick=True)
        self.assertEqual(b.to_text(), "════")

    def test_write_text_plain_without_frame(self) -> None:
        b = Buffer()
        b.write_text(0, 0, "Hola")
        self.assertEqual(b.to_text(), "Hola")

    def test_write_text_at_position(self) -> None:
        b = Buffer()
        b.write_text(5, 2, "abc")
        self.assertEqual(b.height, 3)
        self.assertEqual(b.width, 8)
        self.assertEqual(b.cell(5, 2), "a")
        self.assertEqual(b.cell(7, 2), "c")
        self.assertEqual(b.cell(0, 2), " ")

    def test_undo_redo_groups(self) -> None:
        b = Buffer()
        b.snapshot("type")
        b.insert_char(0, 0, "h")
        b.snapshot("type")
        b.insert_char(1, 0, "o")
        self.assertEqual(len(b._undo), 1)

        b.snapshot("erase")
        b.delete_cell(1, 0)
        self.assertEqual(len(b._undo), 2)

        self.assertTrue(b.undo())
        self.assertEqual(b.to_text(), "ho")
        self.assertTrue(b.undo())
        self.assertEqual(b.to_text(), "")
        self.assertFalse(b.undo())

        self.assertTrue(b.redo())
        self.assertEqual(b.to_text(), "ho")
        self.assertTrue(b.redo())
        self.assertEqual(b.to_text(), "h")

    def test_dirty_flag(self) -> None:
        b = Buffer()
        self.assertFalse(b.dirty)
        b.snapshot("type")
        self.assertTrue(b.dirty)

    def test_save_load_roundtrip(self) -> None:
        b = Buffer(["hola", "mundo"])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "salida.txt"
            b.save(path)
            self.assertFalse(b.dirty)
            loaded = Buffer.load(path)
            self.assertEqual(loaded.rows, ["hola", "mundo"])

    def test_save_adds_trailing_newline(self) -> None:
        b = Buffer(["abc"])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "salida.txt"
            b.save(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "abc\n")

    def test_save_creates_missing_parent_dirs(self) -> None:
        
        b = Buffer(["hola"])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "docs" / "sub" / "plan.txt"
            b.save(path)
            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(encoding="utf-8"), "hola\n")

    def test_from_text(self) -> None:
        self.assertEqual(Buffer.from_text("a\nb\n").rows, ["a", "b"])
        self.assertEqual(Buffer.from_text("").rows, [])


if __name__ == "__main__":
    unittest.main()
