

from __future__ import annotations

import sys
from pathlib import Path

from . import __version__
from .app import PaintAsciiApp


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if any(a in ("--version", "-V") for a in args):
        print(f"paint-ascii {__version__}")
        return

    path = Path(args[0]).expanduser() if args else None
    PaintAsciiApp(file_path=path).run()


if __name__ == "__main__":
    main()
