

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from . import __version__

HELP_TEXT = f"""paint-ascii v{__version__} — editor de mockups TUI estilo nano

HERRAMIENTAS (teclas 1-5)
  [1] Rectángulo   Enter fija la 1ª esquina, Enter dibuja el borde
  [2] Texto        Enter pide el texto y lo coloca plano (sin marco)
  [3] Escribir     Texto libre en el cursor
  [4] Botón/Check  Escribe la etiqueta y Enter la coloca en [ etiqueta ]
  [5] Línea        Línea recta (─ │ o ═ ║ con «t»)

  Con [3] Escribir o [4] Botón/Check activos, los dígitos 1-5 se
  teclean como texto (p. ej. «2FA»). Pulsa Esc para volver a [1] y
  luego cambia de herramienta con 1-5.

ATAJOS
  ^O / ^S  Guardar archivo       ^Q  Salir
  ^Z  Deshacer                   ^Y  Rehacer
  Esc       Cancelar operación   F1  Esta ayuda
"""


class _Dialog(Vertical):
    

    DEFAULT_CSS = """
    _Dialog {
        width: auto;
        max-width: 72;
        height: auto;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    _Dialog > Static { margin-bottom: 1; }
    _Dialog Input { margin-bottom: 1; }
    _Dialog Static.hint { margin-bottom: 1; color: $text-muted; }
    _Dialog Horizontal { height: auto; }
    """


class ConfirmQuitScreen(ModalScreen[str]):
    

    BINDINGS = [Binding("escape", "cancel", "Cancelar")]

    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename

    def compose(self) -> ComposeResult:
        with _Dialog():
            yield Static(f"Hay cambios sin guardar en [bold]{self.filename}[/bold]. ¿Qué deseas hacer?")
            with Horizontal():
                yield Button("Guardar y salir", id="save", variant="primary")
                yield Button("Salir sin guardar", id="discard")
                yield Button("Cancelar", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id or "cancel")

    def action_cancel(self) -> None:
        self.dismiss("cancel")


class FilenameScreen(ModalScreen[str | None]):
    







    BINDINGS = [Binding("escape", "cancel", "Cancelar")]

    def __init__(self, default: str = "") -> None:
        super().__init__()
        self.default = default

    def compose(self) -> ComposeResult:
        with _Dialog():
            yield Static("Guardar como (nombre o ruta):")
            yield Input(value=self.default, placeholder="plan.txt  ·  ~/docs/plan.txt")
            yield Static(
                "Solo el nombre guarda en esta carpeta · una ruta guarda allí",
                classes="hint",
            )
            with Horizontal():
                yield Button("Guardar", id="ok", variant="primary")
                yield Button("Cancelar", id="cancel")

    def on_mount(self) -> None:
        input_widget = self.query_one(Input)
        input_widget.focus()
        if self.default:
            input_widget.action_select_all()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(self.query_one(Input).value.strip() or None)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class TextBoxScreen(ModalScreen[str | None]):
    

    BINDINGS = [Binding("escape", "cancel", "Cancelar")]

    def compose(self) -> ComposeResult:
        with _Dialog():
            yield Static("Texto:")
            yield Input(placeholder="Ej. Nombre:")
            with Horizontal():
                yield Button("Colocar", id="ok", variant="primary")
                yield Button("Cancelar", id="cancel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(self.query_one(Input).value.strip() or None)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class HelpScreen(ModalScreen[None]):
    

    BINDINGS = [
        Binding("escape", "close", "Cerrar"),
        Binding("enter", "close", "Cerrar"),
    ]

    def compose(self) -> ComposeResult:
        with _Dialog():
            yield Static(HELP_TEXT)
            with Horizontal():
                yield Button("Cerrar", id="ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
