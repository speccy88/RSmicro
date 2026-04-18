from __future__ import annotations

import argparse
import cmd
import shlex
import threading
import time
from pathlib import Path

from .engine import LadderEngine
from .model import Binding, Program, Rung, Step
from .program_io import load_program, save_program
from .remote import RemoteSession
from .render import render_program
from .serial_link import SerialJsonTransport
from .subprocess_link import SubprocessJsonTransport


def parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "on", "yes"}:
        return True
    if value in {"0", "false", "off", "no"}:
        return False
    raise ValueError(f"Cannot parse boolean from '{raw}'")


class WorkbenchShell(cmd.Cmd):
    intro = "PLC ASCII workbench. Type help or ? to list commands."
    prompt = "plc> "

    def __init__(self, program: Program | None = None) -> None:
        super().__init__()
        self.program = program or Program(name="untitled")
        self.engine = LadderEngine(self.program)
        self._runner: threading.Thread | None = None
        self._stop_runner = threading.Event()
        self.remote: RemoteSession | None = None
        self.remote_label: str | None = None

    def _reload_engine(self) -> None:
        self.engine = LadderEngine(self.program)

    def _require_remote(self) -> RemoteSession | None:
        if self.remote is None:
            print("No remote runtime connected")
            return None
        return self.remote

    def do_new(self, arg: str) -> None:
        """new PROGRAM_NAME"""
        name = arg.strip() or "untitled"
        self.program = Program(name=name)
        self._reload_engine()
        print(f"Created program '{name}'")

    def do_load(self, arg: str) -> None:
        """load PATH"""
        path = Path(arg.strip())
        self.program = load_program(path)
        self._reload_engine()
        print(f"Loaded {path}")

    def do_save(self, arg: str) -> None:
        """save PATH"""
        path = Path(arg.strip())
        save_program(self.program, path)
        print(f"Saved {path}")

    def do_show(self, arg: str) -> None:
        """show"""
        print(render_program(self.program))

    def do_tags(self, arg: str) -> None:
        """tags"""
        snapshot = self.engine.snapshot()
        print("Tags:")
        for tag, value in snapshot["tags"].items():
            forced = " (forced)" if tag in snapshot["forced"] else ""
            print(f"- {tag} = {int(value)}{forced}")
        if not snapshot["tags"]:
            print("- none")
        print("Timers:")
        if not snapshot["timers"]:
            print("- none")
        for name, timer in snapshot["timers"].items():
            print(
                f"- {name}: ACC={timer['acc']} PRE={timer['pre']} "
                f"EN={int(timer['en'])} TT={int(timer['tt'])} DN={int(timer['dn'])}"
            )

    def do_addrung(self, arg: str) -> None:
        """addrung [COMMENT]"""
        parts = shlex.split(arg)
        comment = " ".join(parts)
        self.program.rungs.append(Rung(comment=comment))
        self._reload_engine()
        print(f"Added rung {len(self.program.rungs) - 1}")

    def do_cond(self, arg: str) -> None:
        """cond RUNG_INDEX XIC|XIO TAG"""
        parts = shlex.split(arg)
        if len(parts) != 3:
            print("Usage: cond RUNG_INDEX XIC|XIO TAG")
            return
        rung_index = int(parts[0])
        step = Step(op=parts[1].upper(), tag=parts[2])
        self.program.rungs[rung_index].elements.append(step)
        self._reload_engine()
        print(f"Added {step.op} {step.tag} to rung {rung_index}")

    def do_act(self, arg: str) -> None:
        """act RUNG_INDEX OTE|OTL|OTU TAG | act RUNG_INDEX TON TIMER_NAME PRESET_MS"""
        parts = shlex.split(arg)
        if len(parts) not in {3, 4}:
            print("Usage: act RUNG_INDEX OTE|OTL|OTU TAG | act RUNG_INDEX TON TIMER_NAME PRESET_MS")
            return
        rung_index = int(parts[0])
        op = parts[1].upper()
        if op == "TON":
            step = Step(op=op, tag=parts[2], arg=int(parts[3]))
        else:
            step = Step(op=op, tag=parts[2])
        self.program.rungs[rung_index].elements.append(step)
        self.program.validate()
        self._reload_engine()
        print(f"Added {step.op} {step.tag} to rung {rung_index}")

    def do_bind(self, arg: str) -> None:
        """bind TAG input|output ADDRESS"""
        parts = shlex.split(arg)
        if len(parts) != 3:
            print("Usage: bind TAG input|output ADDRESS")
            return
        binding = Binding(tag=parts[0], direction=parts[1], address=parts[2])
        binding.validate()
        self.program.bindings = [b for b in self.program.bindings if b.tag != binding.tag]
        self.program.bindings.append(binding)
        print(f"Bound {binding.tag} -> {binding.direction}:{binding.address}")

    def do_connect_demo(self, arg: str) -> None:
        """connect_demo"""
        if self.remote is not None:
            print(f"Already connected to {self.remote_label}")
            return
        session = RemoteSession(SubprocessJsonTransport())
        hello = session.hello()
        if not hello:
            print("Failed to connect to demo runtime")
            session.transport.close()
            return
        self.remote = session
        self.remote_label = "demo-runtime"
        print(f"Connected to {self.remote_label}: {hello}")

    def do_connect_serial(self, arg: str) -> None:
        """connect_serial PORT [BAUD]"""
        parts = shlex.split(arg)
        if not parts:
            print("Usage: connect_serial PORT [BAUD]")
            return
        port = parts[0]
        baud = int(parts[1]) if len(parts) > 1 else 115200
        try:
            session = RemoteSession(SerialJsonTransport(port=port, baudrate=baud))
            hello = session.hello()
        except Exception as exc:  # pragma: no cover
            print(f"Serial connection failed: {exc}")
            return
        self.remote = session
        self.remote_label = f"serial:{port}"
        print(f"Connected to {self.remote_label}: {hello}")

    def do_disconnect(self, arg: str) -> None:
        """disconnect"""
        if self.remote is None:
            print("No remote runtime connected")
            return
        self.remote.transport.close()
        print(f"Disconnected from {self.remote_label}")
        self.remote = None
        self.remote_label = None

    def do_set(self, arg: str) -> None:
        """set TAG 0|1"""
        parts = shlex.split(arg)
        if len(parts) != 2:
            print("Usage: set TAG 0|1")
            return
        self.engine.set_tag(parts[0], parse_bool(parts[1]))
        print(f"{parts[0]} = {parts[1]}")

    def do_force(self, arg: str) -> None:
        """force TAG 0|1"""
        parts = shlex.split(arg)
        if len(parts) != 2:
            print("Usage: force TAG 0|1")
            return
        self.engine.set_force(parts[0], parse_bool(parts[1]))
        print(f"Forced {parts[0]} = {parts[1]}")

    def do_unforce(self, arg: str) -> None:
        """unforce TAG"""
        tag = arg.strip()
        self.engine.clear_force(tag)
        print(f"Removed force from {tag}")

    def do_remote_download(self, arg: str) -> None:
        """remote_download"""
        remote = self._require_remote()
        if remote is None:
            return
        print(remote.download_program(self.program))

    def do_remote_snapshot(self, arg: str) -> None:
        """remote_snapshot"""
        remote = self._require_remote()
        if remote is None:
            return
        print(remote.request_snapshot())

    def do_remote_set(self, arg: str) -> None:
        """remote_set TAG 0|1"""
        remote = self._require_remote()
        if remote is None:
            return
        parts = shlex.split(arg)
        if len(parts) != 2:
            print("Usage: remote_set TAG 0|1")
            return
        print(remote.set_tag(parts[0], parse_bool(parts[1])))

    def do_remote_force(self, arg: str) -> None:
        """remote_force TAG 0|1"""
        remote = self._require_remote()
        if remote is None:
            return
        parts = shlex.split(arg)
        if len(parts) != 2:
            print("Usage: remote_force TAG 0|1")
            return
        print(remote.force_tag(parts[0], enabled=True, value=parse_bool(parts[1])))

    def do_remote_unforce(self, arg: str) -> None:
        """remote_unforce TAG"""
        remote = self._require_remote()
        if remote is None:
            return
        tag = arg.strip()
        print(remote.force_tag(tag, enabled=False, value=False))

    def do_remote_bind(self, arg: str) -> None:
        """remote_bind TAG input|output ADDRESS"""
        remote = self._require_remote()
        if remote is None:
            return
        parts = shlex.split(arg)
        if len(parts) != 3:
            print("Usage: remote_bind TAG input|output ADDRESS")
            return
        print(remote.bind_tag(parts[0], parts[1], parts[2]))

    def do_watchremote(self, arg: str) -> None:
        """watchremote [COUNT] [DELAY_MS]"""
        remote = self._require_remote()
        if remote is None:
            return
        parts = shlex.split(arg)
        count = int(parts[0]) if parts else 5
        delay_ms = int(parts[1]) if len(parts) > 1 else 250
        for _ in range(count):
            print(remote.request_snapshot())
            time.sleep(delay_ms / 1000)

    def do_step(self, arg: str) -> None:
        """step [SCAN_MS]"""
        scan_ms = int(arg.strip() or "100")
        result = self.engine.scan(scan_ms=scan_ms)
        print(f"Scanned {result.scan_ms} ms")
        for rung_name, powered in result.rung_power.items():
            print(f"- {rung_name}: {'ON' if powered else 'OFF'}")

    def _run_loop(self, iterations: int, scan_ms: int) -> None:
        try:
            for _ in range(iterations):
                if self._stop_runner.is_set():
                    return
                self.engine.scan(scan_ms=scan_ms)
                time.sleep(scan_ms / 1000)
        finally:
            self._runner = None
            self._stop_runner.clear()

    def do_run(self, arg: str) -> None:
        """run [ITERATIONS] [SCAN_MS]"""
        parts = shlex.split(arg)
        iterations = int(parts[0]) if parts else 20
        scan_ms = int(parts[1]) if len(parts) > 1 else 100
        if self._runner and self._runner.is_alive():
            print("A run loop is already active")
            return
        self._stop_runner.clear()
        self._runner = threading.Thread(
            target=self._run_loop,
            args=(iterations, scan_ms),
            daemon=True,
        )
        self._runner.start()
        print(f"Running {iterations} scans at {scan_ms} ms")

    def do_stop(self, arg: str) -> None:
        """stop"""
        self._stop_runner.set()
        print("Stopping run loop")

    def do_delete(self, arg: str) -> None:
        """delete RUNG_INDEX"""
        index = int(arg.strip())
        removed = self.program.rungs.pop(index)
        self._reload_engine()
        print(f"Deleted rung {removed.name}")

    def do_quit(self, arg: str) -> bool:
        """quit"""
        self._stop_runner.set()
        if self.remote is not None:
            self.remote.transport.close()
        return True

    def do_EOF(self, arg: str) -> bool:
        print()
        return self.do_quit(arg)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ASCII ladder workbench")
    parser.add_argument("program", nargs="?", help="Optional program JSON file to load")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    program = load_program(args.program) if args.program else None
    WorkbenchShell(program).cmdloop()


if __name__ == "__main__":
    main()
