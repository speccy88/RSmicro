from __future__ import annotations

import argparse
import os
import sys

from rsmicro import __version__


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="rsmicro-studio", description="RSmicro Studio engineering environment"
    )
    result.add_argument("project", nargs="?")
    result.add_argument("--new", action="store_true")
    result.add_argument("--safe-mode", action="store_true")
    result.add_argument("--reset-layout", action="store_true")
    result.add_argument("--offscreen", action="store_true")
    result.add_argument("--verify", action="store_true")
    result.add_argument("--run-duration", type=float, default=2)
    result.add_argument("--version", action="version", version=__version__)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.offscreen:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtCore import QSettings, QTimer
        from PySide6.QtWidgets import QApplication

        from .main_window import MainWindow
        from .session import ProjectSession
    except ImportError as exc:
        print("PySide6 is required for RSmicro Studio: " + str(exc), file=sys.stderr)
        return 2

    app = QApplication(sys.argv[:1])
    app.setOrganizationName("RSmicro")
    app.setApplicationName("Studio")
    settings = QSettings()
    session = ProjectSession()
    try:
        if args.project:
            session.open(args.project)
    except Exception as exc:
        print(f"Unable to open project: {exc}", file=sys.stderr)
        return 2
    window = MainWindow(session, settings)
    if session.project:
        window.load_project()
    window.show()
    QTimer.singleShot(0, window.reset_ladder_views)
    if args.verify:
        if session.project:
            routines = sum(
                len(program.routines)
                for controller in session.project.controllers
                for program in controller.programs
            )
            print(
                f"Verified Studio project '{session.project.name}': "
                f"{len(session.project.controllers)} controllers, {routines} routines"
            )
        else:
            print("Verified Studio launch without a project")
        QTimer.singleShot(max(1, int(args.run_duration * 1000)), app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
