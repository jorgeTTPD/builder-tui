"""Modelo de datos: lienzo de celdas de caracteres.

El buffer es una lista de filas (cadenas de texto); cada celda es un
carácter. Las celdas fuera de los límites se leen como espacios.
Incluye historial de deshacer/rehacer y guardado atómico a .txt.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

MAX_UNDO = 200


class Buffer:
    """Lienzo de caracteres con operaciones de dibujo y deshacer."""

    def __init__(self, rows: list[str] | None = None) -> None:
        self.rows: list[str] = list(rows) if rows else []
        self.dirty = False
        self._undo: list[list[str]] = []
        self._redo: list[list[str]] = []
        self._last_kind: str | None = None


    @property
    def width(self) -> int:
        return max((len(r) for r in self.rows), default=0)

    @property
    def height(self) -> int:
        return len(self.rows)

    def cell(self, x: int, y: int) -> str:
        """Carácter en (x, y); espacio si está fuera de los límites."""
        if 0 <= y < len(self.rows):
            row = self.rows[y]
            if 0 <= x < len(row):
                return row[x]
        return " "


    def _ensure(self, y: int, x: int) -> None:
        while len(self.rows) <= y:
            self.rows.append("")
        if len(self.rows[y]) < x:
            self.rows[y] = self.rows[y].ljust(x)

    def set_cell(self, x: int, y: int, ch: str) -> None:
        """Fija un carácter en una celda, ampliando el lienzo si hace falta."""
        self._ensure(y, x)
        row = self.rows[y]
        if x >= len(row):
            self.rows[y] = row.ljust(x) + ch
        else:
            self.rows[y] = row[:x] + ch + row[x + 1 :]

    def insert_char(self, x: int, y: int, ch: str) -> None:
        self._ensure(y, x)
        row = self.rows[y]
        self.rows[y] = row[:x] + ch + row[x:]

    def delete_cell(self, x: int, y: int) -> None:
        if 0 <= y < len(self.rows):
            row = self.rows[y]
            if 0 <= x < len(row):
                self.rows[y] = row[:x] + row[x + 1 :]

    def split_row(self, x: int, y: int) -> None:
        """Divide la fila y en dos a la altura de la columna x (tecla Enter)."""
        self._ensure(y, x)
        row = self.rows[y]
        self.rows[y : y + 1] = [row[:x], row[x:]]


    def box_cells(self, p1: tuple[int, int], p2: tuple[int, int]) -> dict[tuple[int, int], str]:
        """Celdas de borde de una caja entre dos esquinas (┌─┐│└┘)."""
        x1, x2 = sorted((p1[0], p2[0]))
        y1, y2 = sorted((p1[1], p2[1]))
        cells: dict[tuple[int, int], str] = {}
        for x in range(x1, x2 + 1):
            cells[(x, y1)] = "─"
            cells[(x, y2)] = "─"
        for y in range(y1, y2 + 1):
            cells[(x1, y)] = "│"
            cells[(x2, y)] = "│"
        cells[(x1, y1)] = "┌"
        cells[(x2, y1)] = "┐"
        cells[(x1, y2)] = "└"
        cells[(x2, y2)] = "┘"
        return cells

    def draw_box(self, p1: tuple[int, int], p2: tuple[int, int]) -> None:
        for (x, y), ch in self.box_cells(p1, p2).items():
            self.set_cell(x, y, ch)

    def line_cells(
        self, p1: tuple[int, int], p2: tuple[int, int], thick: bool = False
    ) -> dict[tuple[int, int], str]:
        """Línea recta horizontal/vertical entre dos puntos (─│ o ═║)."""
        h, v = ("═", "║") if thick else ("─", "│")
        x1, y1 = p1
        x2, y2 = p2
        cells: dict[tuple[int, int], str] = {}
        if abs(x2 - x1) >= abs(y2 - y1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                cells[(x, y1)] = h
        else:
            for y in range(min(y1, y2), max(y1, y2) + 1):
                cells[(x1, y)] = v
        return cells

    def draw_line(self, p1: tuple[int, int], p2: tuple[int, int], thick: bool = False) -> None:
        for (x, y), ch in self.line_cells(p1, p2, thick).items():
            self.set_cell(x, y, ch)

    def write_text(self, x: int, y: int, text: str) -> None:
        """Escribe texto plano en el lienzo a partir de (x, y), sin marco."""
        for i, ch in enumerate(text):
            self.set_cell(x + i, y, ch)


    def snapshot(self, kind: str | None = None) -> None:
        """Guarda el estado actual antes de una mutación.

        Con el mismo ``kind`` consecutivo no se crea una entrada nueva
        (agrupa escritura continua en un solo paso de deshacer).
        """
        if kind is not None and kind == self._last_kind:
            self.dirty = True
            return
        self._undo.append([r for r in self.rows])
        if len(self._undo) > MAX_UNDO:
            self._undo.pop(0)
        self._redo.clear()
        self.dirty = True
        self._last_kind = kind

    def reset_group(self) -> None:
        """Rompe el grupo de deshacer (p. ej. al mover el cursor)."""
        self._last_kind = None

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append([r for r in self.rows])
        self.rows = self._undo.pop()
        self._last_kind = None
        self.dirty = True
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append([r for r in self.rows])
        self.rows = self._redo.pop()
        self._last_kind = None
        self.dirty = True
        return True


    def to_text(self) -> str:
        return "\n".join(r.rstrip() for r in self.rows)

    @classmethod
    def from_text(cls, text: str) -> "Buffer":
        if not text:
            return cls()
        rows = text.split("\n")
        if rows and rows[-1] == "" and text.endswith("\n"):
            rows.pop()
        return cls(rows)

    def save(self, path: Path | str) -> None:
        """Guardado atómico: escribe a un temporal y luego reemplaza.

        Crea el directorio padre si no existe (soporta rutas con subcarpetas).
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = self.to_text()
        content = text + "\n" if text else ""
        fd, tmp = tempfile.mkstemp(dir=str(path.parent or "."), suffix=".tmp", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        self.dirty = False

    @classmethod
    def load(cls, path: Path | str) -> "Buffer":
        return cls.from_text(Path(path).read_text(encoding="utf-8"))
