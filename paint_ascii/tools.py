"""Sistema de herramientas (patrón estrategia).

Cada herramienta recibe el lienzo (Canvas) y los eventos de teclado y
decide qué hacer. Las que dibujan exponen una ``preview`` en vivo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .widgets import Canvas


class Tool:
    """Base de todas las herramientas."""

    key: str = ""
    name: str = ""



    consumes_text = False

    def hint(self) -> str:
        return ""

    def handle_key(self, canvas: "Canvas", event: Any) -> bool:
        """Procesa una tecla. Devuelve True si la consumió."""
        return False

    def preview(self, canvas: "Canvas") -> dict[tuple[int, int], str] | None:
        """Celdas a mostrar en vista previa, o None si no hay."""
        return None


class RectanguloTool(Tool):
    key = "1"
    name = "Rectángulo"

    def __init__(self) -> None:
        self.corner: tuple[int, int] | None = None

    def hint(self) -> str:
        return "Enter fija la 1ª esquina · mueve el cursor · Enter dibuja"

    def handle_key(self, canvas: "Canvas", event: Any) -> bool:
        if event.key == "enter":
            if self.corner is None:
                self.corner = (canvas.cursor_x, canvas.cursor_y)
            else:
                canvas.buffer.snapshot("box")
                canvas.buffer.draw_box(self.corner, (canvas.cursor_x, canvas.cursor_y))
                self.corner = None
            canvas.moved()
            return True
        if event.key == "escape" and self.corner is not None:
            self.corner = None
            canvas.refresh()
            return True
        return False

    def preview(self, canvas: "Canvas") -> dict[tuple[int, int], str] | None:
        if self.corner is None:
            return None
        return canvas.buffer.box_cells(self.corner, (canvas.cursor_x, canvas.cursor_y))


class TextoTool(Tool):
    key = "2"
    name = "Texto"

    def __init__(self) -> None:
        self._canvas: "Canvas | None" = None

    def hint(self) -> str:
        return "Enter pide el texto y lo coloca plano en el cursor"

    def handle_key(self, canvas: "Canvas", event: Any) -> bool:
        if event.key == "enter":
            from .screens import TextBoxScreen

            canvas.app.push_screen(TextBoxScreen(), callback=self._place_text)
            self._canvas = canvas
            return True
        return False

    def _place_text(self, text: str | None) -> None:
        """Callback del modal: coloca el texto plano en el cursor, sin marco."""
        canvas = self._canvas
        if canvas is None:
            return
        if text:
            canvas.buffer.snapshot("text")
            canvas.buffer.write_text(canvas.cursor_x, canvas.cursor_y, text)
            canvas.cursor_x += len(text)
        canvas.moved()


class EscribirTool(Tool):
    key = "3"
    name = "Escribir"
    consumes_text = True

    def hint(self) -> str:
        return "Escribe texto · Enter salto · Backspace borra · Esc vuelve a [1]"

    def _back_to_rectangulo(self, canvas: "Canvas") -> None:
        """Esc: vuelve a la herramienta Rectángulo (para poder cambiar con 1-5)."""
        canvas.app.set_tool(1)

    def handle_key(self, canvas: "Canvas", event: Any) -> bool:
        ch = event.character
        if ch is not None and ch.isprintable():
            canvas.buffer.snapshot("type")
            canvas.buffer.insert_char(canvas.cursor_x, canvas.cursor_y, ch)
            canvas.cursor_x += 1
            canvas.moved()
            return True

        key = event.key
        if key == "enter":
            canvas.buffer.snapshot("type")
            canvas.buffer.split_row(canvas.cursor_x, canvas.cursor_y)
            canvas.cursor_x = 0
            canvas.cursor_y += 1
            canvas.moved()
            return True
        if key == "backspace":
            if canvas.cursor_x > 0:
                canvas.buffer.snapshot("erase")
                canvas.buffer.delete_cell(canvas.cursor_x - 1, canvas.cursor_y)
                canvas.cursor_x -= 1


            elif 0 < canvas.cursor_y < len(canvas.buffer.rows):
                canvas.buffer.snapshot("erase")
                prev_len = len(canvas.buffer.rows[canvas.cursor_y - 1])
                canvas.buffer.rows[canvas.cursor_y - 1] += canvas.buffer.rows[canvas.cursor_y]
                del canvas.buffer.rows[canvas.cursor_y]
                canvas.cursor_y -= 1
                canvas.cursor_x = prev_len
            canvas.moved()
            return True
        if key == "delete":
            canvas.buffer.snapshot("erase")
            canvas.buffer.delete_cell(canvas.cursor_x, canvas.cursor_y)
            canvas.moved()
            return True
        if key == "escape":
            self._back_to_rectangulo(canvas)
            return True
        return False


class BotonCheckTool(Tool):
    key = "4"
    name = "Botón/Check"
    consumes_text = True

    def __init__(self) -> None:
        self.label = ""

    def hint(self) -> str:
        if self.label:
            return f"Etiqueta: «{self.label}» · Enter coloca"
        return "Escribe la etiqueta · Enter coloca [ ]"

    def handle_key(self, canvas: "Canvas", event: Any) -> bool:
        ch = event.character
        if ch is not None and ch.isprintable():
            self.label += ch
            canvas.app.refresh_chrome()
            return True
        if event.key == "backspace" and self.label:
            self.label = self.label[:-1]
            canvas.app.refresh_chrome()
            return True
        if event.key == "enter":
            text = f"[ {self.label} ]" if self.label else "[ ]"
            canvas.buffer.snapshot("widget")
            for i, ch in enumerate(text):
                canvas.buffer.set_cell(canvas.cursor_x + i, canvas.cursor_y, ch)
            canvas.cursor_x += len(text)
            self.label = ""
            canvas.moved()
            canvas.app.refresh_chrome()
            return True
        if event.key == "escape":
            self.label = ""
            canvas.app.set_tool(1)
            return True
        return False

    def preview(self, canvas: "Canvas") -> dict[tuple[int, int], str] | None:
        if not self.label:
            return None
        text = f"[ {self.label} ]"
        return {(canvas.cursor_x + i, canvas.cursor_y): ch for i, ch in enumerate(text)}


class LineaTool(Tool):
    key = "5"
    name = "Línea"

    def __init__(self) -> None:
        self.start: tuple[int, int] | None = None
        self.thick = False

    def hint(self) -> str:
        style = "═ ║" if self.thick else "─ │"
        return f"Enter inicio · Enter fin (línea {style}) · t alterna estilo"

    def handle_key(self, canvas: "Canvas", event: Any) -> bool:
        if event.key == "enter":
            if self.start is None:
                self.start = (canvas.cursor_x, canvas.cursor_y)
            else:
                canvas.buffer.snapshot("line")
                canvas.buffer.draw_line(self.start, (canvas.cursor_x, canvas.cursor_y), self.thick)
                self.start = None
            canvas.moved()
            return True
        if event.key == "t":
            self.thick = not self.thick
            canvas.refresh()
            canvas.app.refresh_chrome()
            return True
        if event.key == "escape" and self.start is not None:
            self.start = None
            canvas.refresh()
            return True
        return False

    def preview(self, canvas: "Canvas") -> dict[tuple[int, int], str] | None:
        if self.start is None:
            return None
        return canvas.buffer.line_cells(self.start, (canvas.cursor_x, canvas.cursor_y), self.thick)


TOOLS: list[type[Tool]] = [
    RectanguloTool,
    TextoTool,
    EscribirTool,
    BotonCheckTool,
    LineaTool,
]
