from __future__ import annotations

import argparse
import os
import sys

from rsmicro import __version__
from rsmicro.model import load_project
from rsmicro.scada_screen_loader import load_project_screens


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="rsmicro-scada", description="Standalone RSmicro SCADA operator runtime"
    )
    result.add_argument("--project", required=True)
    result.add_argument("--screen", required=True)
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", type=int, default=7590)
    result.add_argument(
        "--role", choices=("viewer", "operator", "engineering"), default="viewer"
    )
    result.add_argument("--fullscreen", action="store_true")
    result.add_argument("--windowed", action="store_true")
    result.add_argument("--width", type=int)
    result.add_argument("--height", type=int)
    result.add_argument("--kiosk", action="store_true")
    result.add_argument("--no-write", action="store_true")
    result.add_argument("--offscreen", action="store_true")
    result.add_argument("--log-level", default="INFO")
    result.add_argument("--json-logs", action="store_true")
    result.add_argument("--verify", action="store_true")
    result.add_argument("--run-duration", type=float, default=3)
    result.add_argument("--version", action="version", version=__version__)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.offscreen:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        from .window import ScadaWindow
    except ImportError as exc:
        print("PySide6 is required for RSmicro SCADA: " + str(exc), file=sys.stderr)
        return 2
    try:
        project = load_project(args.project)
        screens = load_project_screens(project, args.project)
        screen = next(item for item in screens if item.screen_id == args.screen or item.name == args.screen)
    except Exception as exc:
        print(f"Cannot load SCADA screen: {exc}", file=sys.stderr)
        return 2

    app = QApplication(sys.argv[:1])
    window = ScadaWindow(screen, args.no_write or args.role == "viewer")
    if args.width and args.height:
        window.resize(args.width, args.height)
    if args.fullscreen or args.kiosk:
        window.showFullScreen()
    else:
        window.show()
    if args.verify:
        print(f"Verified SCADA screen '{screen.name}': {len(screen.objects)} objects")
        QTimer.singleShot(max(1, int(args.run_duration * 1000)), app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
