"""Aplicación principal paint-ascii (Python + Textual)."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding

from .buffer import Buffer
from .screens import ConfirmQuitScreen, FilenameScreen, HelpScreen
from .tools import RectanguloTool, TOOLS
from .widgets import Canvas, StatusBar, TitleBar, Toolbar


class PaintAsciiApp(App[None]):
    """Editor de mockups TUI inspirado en nano."""

    TITLE = "paint-ascii v1.0"
    SUB_TITLE = "Editor de mockups TUI estilo nano"

    CSS = """
    Screen { background: $surface; }
    TitleBar { height: 1; }
    Toolbar { height: 1; }
    StatusBar { height: 1; }
    Canvas { width: 1fr; height: 1fr; }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Guardar"),
        Binding("ctrl+o", "save", "Guardar"),
        Binding("ctrl+q", "quit", "Salir"),
        Binding("ctrl+z", "undo", "Deshacer"),
        Binding("ctrl+y", "redo", "Rehacer"),
        Binding("f1", "help", "Ayuda"),
    ]

    def __init__(self, file_path: Path | str | None = None) -> None:
        super().__init__()
        self.file_path = Path(file_path).expanduser() if file_path else None
        self.buffer = Buffer()
        self._load_error: str | None = None
        if self.file_path is not None and self.file_path.exists():
            try:
                self.buffer = Buffer.load(self.file_path)
            except OSError as exc:
                self._load_error = f"No se pudo abrir {self.file_path.name}: {exc}"
        # Herramienta por defecto: [1] Rectángulo (no captura texto, así las
        # teclas 1-5 siempre cambian de herramienta al arrancar).
        self.tool = RectanguloTool()

    # ------------------------------------------------------------- propiedades
    @property
    def filename(self) -> str:
        return self.file_path.name if self.file_path else "sin nombre"

    # ------------------------------------------------------------- composición
    def compose(self) -> ComposeResult:
        yield TitleBar()
        yield Canvas()
        yield Toolbar()
        yield StatusBar()

    def on_mount(self) -> None:
        self.query_one(Canvas).focus()
        self.refresh_chrome()
        if self._load_error:
            self.notify(self._load_error, severity="error", timeout=5)

    def refresh_chrome(self) -> None:
        canvas = self.query_one(Canvas)
        self.query_one(TitleBar).set_state(self.filename, self.buffer.dirty)
        self.query_one(Toolbar).set_active(self.tool.key)
        self.query_one(StatusBar).set_state(
            canvas.cursor_x,
            canvas.cursor_y,
            self.buffer.dirty,
            self.tool.hint(),
        )

    # ------------------------------------------------------------- herramientas
    def set_tool(self, n: int) -> None:
        self.tool = TOOLS[n - 1]()
        self.buffer.reset_group()  # cambiar de herramienta rompe los grupos de undo
        self.refresh_chrome()
        self.query_one(Canvas).refresh()

    # ------------------------------------------------------------- acciones
    def action_undo(self) -> None:
        if self.buffer.undo():
            # moved() recoloca el desplazamiento y refresca todo el chrome
            self.query_one(Canvas).moved()
        else:
            self.notify("Nada que deshacer")

    def action_redo(self) -> None:
        if self.buffer.redo():
            self.query_one(Canvas).moved()
        else:
            self.notify("Nada que rehacer")

    def action_help(self) -> None:
        if self._modal_open():
            return
        self.push_screen(HelpScreen())

    def action_save(self) -> None:
        if self._modal_open():
            return
        if self.file_path is None:
            self.push_screen(FilenameScreen(), callback=self._on_filename)
        else:
            self._do_save()

    def _on_filename(self, name: str | None) -> None:
        if not name:
            return
        self.file_path = self._normalize_name(name)
        self._do_save()

    def _do_save(self) -> None:
        assert self.file_path is not None
        try:
            self.buffer.save(self.file_path)
        except OSError as exc:
            self.notify(f"No se pudo guardar: {exc}", severity="error", timeout=5)
            return
        self.refresh_chrome()
        self.notify(f"Guardado: {self.file_path.name}")

    def action_quit(self) -> None:
        if self._modal_open():
            return
        if not self.buffer.dirty:
            self.exit()
            return
        self.push_screen(ConfirmQuitScreen(self.filename), callback=self._on_quit_choice)

    def _on_quit_choice(self, choice: str | None) -> None:
        if choice == "save":
            if self.file_path is None:
                self.push_screen(FilenameScreen(), callback=self._on_quit_filename)
            else:
                self._do_save()
                if not self.buffer.dirty:
                    self.exit()
        elif choice == "discard":
            self.exit()
        # "cancel": no hacer nada

    def _on_quit_filename(self, name: str | None) -> None:
        if not name:
            return
        self.file_path = self._normalize_name(name)
        self._do_save()
        if not self.buffer.dirty:
            self.exit()

    def _modal_open(self) -> bool:
        """True si ya hay un diálogo modal abierto."""
        return len(self.screen_stack) > 1

    @staticmethod
    def _normalize_name(name: str) -> Path:
        path = Path(name).expanduser()
        if not path.suffix:
            path = path.with_suffix(".txt")
        return path
