

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from paint_ascii.app import PaintAsciiApp
from paint_ascii.screens import ConfirmQuitScreen, FilenameScreen, HelpScreen
from paint_ascii.widgets import Canvas


async def _run(app: PaintAsciiApp, action) -> None:
    async with app.run_test(size=(100, 30)) as pilot:
        await action(app, pilot)
        await pilot.pause(0.05)


class TestApp(unittest.TestCase):
    def test_escribir_tool_typing(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("h", "o", "l", "a")
            self.assertEqual(app.buffer.to_text(), "hola")
            canvas = app.query_one(Canvas)
            self.assertEqual((canvas.cursor_x, canvas.cursor_y), (4, 0))
            self.assertTrue(app.buffer.dirty)

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_enter_splits_line(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("a", "b", "enter", "c")
            self.assertEqual(app.buffer.rows, ["ab", "c"])

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_backspace(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("a", "b", "c")
            await pilot.press("backspace")
            self.assertEqual(app.buffer.to_text(), "ab")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_arrow_keys_move_cursor(self) -> None:
        async def scenario(app, pilot):
            canvas = app.query_one(Canvas)
            await pilot.press("right", "right", "down")
            self.assertEqual((canvas.cursor_x, canvas.cursor_y), (2, 1))

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_rectangulo_tool(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("1")
            await pilot.press("enter")
            await pilot.press("right", "right", "right")
            await pilot.press("down", "down")
            await pilot.press("enter")
            self.assertEqual(app.buffer.to_text(), "┌──┐\n│  │\n└──┘")
            self.assertIsNone(app.tool.corner)

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_escape_cancels_rectangulo(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("1")
            await pilot.press("enter")
            await pilot.press("right", "right")
            await pilot.press("escape")
            self.assertEqual(app.buffer.to_text(), "")
            self.assertIsNone(app.tool.corner)

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_texto_tool_plain_without_frame(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("2")
            await pilot.press("enter")
            await pilot.pause(0.05)
            await pilot.press("H", "o", "l", "a")
            await pilot.press("enter")
            self.assertEqual(app.buffer.to_text(), "Hola")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_boton_check_tool(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("4")
            await pilot.press("G", "u", "a", "r", "d", "a", "r")
            await pilot.press("enter")
            self.assertEqual(app.buffer.to_text(), "[ Guardar ]")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_boton_check_empty(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("4")
            await pilot.press("enter")
            self.assertEqual(app.buffer.to_text(), "[ ]")

    def test_escribir_tool_types_digits_without_switching(self) -> None:
        
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("2", "F", "A")
            self.assertEqual(app.buffer.to_text(), "2FA")
            self.assertEqual(app.tool.name, "Escribir")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_boton_label_with_digits(self) -> None:
        
        async def scenario(app, pilot):
            await pilot.press("4")
            await pilot.press("G", "u", "a", "r", "d", "a", "r", "2")
            await pilot.press("enter")
            self.assertEqual(app.buffer.to_text(), "[ Guardar2 ]")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_backspace_below_last_row_no_crash(self) -> None:
        
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("a")
            await pilot.press("down", "down", "down")
            await pilot.press("backspace")
            self.assertEqual(app.buffer.to_text(), "a")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_escape_in_escribir_returns_to_rectangulo(self) -> None:
        
        async def scenario(app, pilot):
            from paint_ascii.tools import RectanguloTool

            await pilot.press("3")
            await pilot.press("escape")
            self.assertIsInstance(app.tool, RectanguloTool)

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_linea_tool(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("5")
            await pilot.press("enter")
            await pilot.press("right", "right", "right", "right")
            await pilot.press("enter")
            self.assertEqual(app.buffer.to_text(), "─────")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_undo_redo(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("h", "i")
            await pilot.press("ctrl+z")
            self.assertEqual(app.buffer.to_text(), "")
            await pilot.press("ctrl+y")
            self.assertEqual(app.buffer.to_text(), "hi")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_save_without_path_prompts_filename(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("x", "y", "z")
            await pilot.press("ctrl+s")
            await pilot.pause(0.05)
            self.assertIsInstance(app.screen, FilenameScreen)
            await pilot.press("m", "i", "s", "u", "e", "n", "o", "s")
            await pilot.press("enter")
            await pilot.pause(0.05)
            self.assertEqual(app.file_path.name, "misuenos.txt")
            self.assertFalse(app.buffer.dirty)

        import asyncio

        with tempfile.TemporaryDirectory() as td:
            import os

            cwd = os.getcwd()
            os.chdir(td)
            try:
                asyncio.run(_run(PaintAsciiApp(), scenario))
            finally:
                os.chdir(cwd)
            self.assertTrue((Path(td) / "misuenos.txt").exists())

    def test_save_with_path_saves_directly(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("a", "b")
            await pilot.press("ctrl+s")
            self.assertFalse(app.buffer.dirty)

        import asyncio

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "directo.txt"
            asyncio.run(_run(PaintAsciiApp(file_path=path), scenario))
            self.assertEqual(path.read_text(encoding="utf-8"), "ab\n")

    def test_quit_dirty_shows_confirm_and_discard(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("x")
            await pilot.press("ctrl+q")
            await pilot.pause(0.05)
            self.assertIsInstance(app.screen, ConfirmQuitScreen)
            await pilot.click("#discard")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_quit_clean_exits(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("ctrl+q")

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_help_screen(self) -> None:
        async def scenario(app, pilot):
            await pilot.press("f1")
            await pilot.pause(0.05)
            self.assertIsInstance(app.screen, HelpScreen)
            await pilot.press("escape")
            await pilot.pause(0.05)

        import asyncio

        asyncio.run(_run(PaintAsciiApp(), scenario))

    def test_load_existing_file(self) -> None:
        async def scenario(app, pilot):
            self.assertEqual(app.buffer.rows, ["hola", "mundo"])
            self.assertEqual(app.filename, "demo.txt")

        import asyncio

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "demo.txt"
            path.write_text("hola\nmundo\n", encoding="utf-8")
            asyncio.run(_run(PaintAsciiApp(file_path=path), scenario))

    def test_save_with_full_path_creates_subdirs(self) -> None:
        
        async def scenario(app, pilot):
            await pilot.press("3")
            await pilot.press("x", "y")
            await pilot.press("ctrl+s")
            await pilot.pause(0.05)
            self.assertIsInstance(app.screen, FilenameScreen)
            await pilot.press("d", "o", "c", "s", "/", "p", "l", "a", "n")
            await pilot.press("enter")
            await pilot.pause(0.05)

            self.assertEqual(str(app.file_path), "docs/plan.txt")
            self.assertFalse(app.buffer.dirty)

        import asyncio

        with tempfile.TemporaryDirectory() as td:
            import os

            cwd = os.getcwd()
            os.chdir(td)
            try:
                asyncio.run(_run(PaintAsciiApp(), scenario))
            finally:
                os.chdir(cwd)
            self.assertTrue((Path(td) / "docs" / "plan.txt").exists())
            self.assertEqual((Path(td) / "docs" / "plan.txt").read_text(), "xy\n")


if __name__ == "__main__":
    unittest.main()
