"""Widgets de la interfaz: cabecera, lienzo, barra de herramientas y estado."""

from __future__ import annotations

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Static

CURSOR_STYLE = Style(reverse=True)
PREVIEW_STYLE = Style(bold=True, color="#00ff87")

from .tools import TOOLS


class TitleBar(Static):
    """Cabecera superior estilo nano: ┌── paint-ascii v1.0 ── Archivo: mockup.txt ──┐"""

    def set_state(self, filename: str, dirty: bool) -> None:
        width = max(self.size.width, 30)
        title = " paint-ascii v1.0 "
        info = f" Archivo: {filename} "
        marker = "●" if dirty else "○"

        fixed = len("┌──") + len(title) + len(info) + 1 + len("──┐")
        fill = max(width - fixed, 0)

        text = Text()
        text.append("┌──", style="bold")
        text.append(title, style="bold cyan")
        text.append("─" * fill)
        text.append(info)
        text.append(marker, style="bold red" if dirty else "dim")
        text.append("──┐", style="bold")
        self.update(text)


class Toolbar(Static):
    """Barra de herramientas inferior (estilo del mockup)."""

    def set_active(self, active_key: str) -> None:
        text = Text()
        text.append("  ")
        for tool in TOOLS:
            label = f"[{tool.key}] {tool.name}"
            style = "reverse" if tool.key == active_key else ""
            text.append("  " + label, style=style)
        text.append("   ", style="dim")
        text.append("[^O] Guardar  [^Q] Salir  [^Z] Deshacer  [^Y] Rehacer  [F1] Ayuda", style="dim")
        self.update(text)


class StatusBar(Static):
    """Línea de estado: posición del cursor, dirty y pista de la herramienta."""

    def set_state(self, x: int, y: int, dirty: bool, hint: str) -> None:
        text = Text()
        text.append(f"  x:{x} y:{y}   ")
        text.append("●" if dirty else "○", style="bold red" if dirty else "dim")
        text.append("   ")
        text.append(hint, style="italic cyan")
        self.update(text)


class Canvas(Widget, can_focus=True):
    """Lienzo de celdas con desplazamiento manual y cursor visible."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cursor_x = 0
        self.cursor_y = 0


        self.offset_x = 0
        self.offset_y = 0

    @property
    def buffer(self):
        return self.app.buffer

    @property
    def tool(self):
        return self.app.tool


    def moved(self) -> None:
        """Llamado tras cambiar el cursor o editar: reposiciona y refresca."""
        self._ensure_visible()
        self.refresh()
        self.app.refresh_chrome()

    def _ensure_visible(self) -> None:
        w, h = self.size.width, self.size.height
        if w <= 0 or h <= 0:
            return
        if self.cursor_x < self.offset_x:
            self.offset_x = self.cursor_x
        elif self.cursor_x >= self.offset_x + w:
            self.offset_x = self.cursor_x - w + 1
        if self.cursor_y < self.offset_y:
            self.offset_y = self.cursor_y
        elif self.cursor_y >= self.offset_y + h:
            self.offset_y = self.cursor_y - h + 1
        max_sx = max(self.buffer.width + 1 - w, 0)
        max_sy = max(self.buffer.height + 1 - h, 0)
        self.offset_x = max(0, min(self.offset_x, max_sx))
        self.offset_y = max(0, min(self.offset_y, max_sy))


    def on_key(self, event) -> None:
        key = event.key
        if key == "up":
            self.cursor_y = max(0, self.cursor_y - 1)
        elif key == "down":
            self.cursor_y += 1
        elif key == "left":
            self.cursor_x = max(0, self.cursor_x - 1)
        elif key == "right":
            self.cursor_x += 1
        elif key in "12345" and not self.tool.consumes_text:


            self.app.set_tool(int(key))
            event.stop()
            return
        elif self.tool.handle_key(self, event):
            event.stop()
            return
        else:


            return

        self.app.buffer.reset_group()
        self.moved()
        event.stop()

    def on_click(self, event) -> None:
        self.focus()
        self.cursor_x = max(0, event.x + self.offset_x)
        self.cursor_y = max(0, event.y + self.offset_y)
        self.app.buffer.reset_group()
        self.moved()
        event.stop()

    def on_mouse_scroll_down(self, event) -> None:
        self.offset_y = min(
            self.offset_y + 2,
            max(self.buffer.height + 1 - self.size.height, 0),
        )
        self.refresh()
        event.stop()

    def on_mouse_scroll_up(self, event) -> None:
        self.offset_y = max(0, self.offset_y - 2)
        self.refresh()
        event.stop()


    def render_line(self, y: int) -> Strip:
        row = y + self.offset_y
        width = self.size.width
        preview = self.tool.preview(self)
        segments: list[Segment] = []
        cx, cy = self.cursor_x, self.cursor_y
        for x in range(self.offset_x, self.offset_x + width):
            if (x, row) == (cx, cy):
                segments.append(Segment(self.buffer.cell(x, row), CURSOR_STYLE))
            elif preview is not None and (x, row) in preview:
                segments.append(Segment(preview[(x, row)], PREVIEW_STYLE))
            else:
                segments.append(Segment(self.buffer.cell(x, row)))
        return Strip(segments)
