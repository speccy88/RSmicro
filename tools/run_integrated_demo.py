#!/usr/bin/env python3
"""Bounded deterministic compiler smoke test with honest scope reporting."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=120)


def command_detail(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stdout + result.stderr).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true", help="accepted for compatibility; no GUI is launched")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--artifacts-dir")
    parser.add_argument("--keep-artifacts", action="store_true")
    args = parser.parse_args(argv)

    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    images: dict[str, dict[str, str]] = {}
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "QT_QPA_PLATFORM": "offscreen"}
    holder: tempfile.TemporaryDirectory[str] | None = None
    if args.artifacts_dir:
        artifacts = Path(args.artifacts_dir).resolve()
        artifacts.mkdir(parents=True, exist_ok=True)
    else:
        holder = tempfile.TemporaryDirectory(prefix="rsmicro-integrated-")
        artifacts = Path(holder.name)

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            failures.append(f"{name}: {detail}")

    try:
        validation = run([sys.executable, "tools/validate_repository.py", "--format", "json"], env)
        check("repository_validation", validation.returncode == 0, command_detail(validation))
        images: dict[str, dict[str, str]] = {}
        for controller in ("controller-a", "controller-b"):
            outputs = [artifacts / f"{controller}.first.rsm", artifacts / f"{controller}.second.rsm"]
            compile_results = []
            for output in outputs:
                compile_results.append(run([
                    sys.executable, "-m", "rsmicro.cli", "compile", "examples/integrated_demo/project.rsmproj",
                    "--controller", controller, "--output", str(output), "--format", "json",
                ], env))
            compiled = all(result.returncode == 0 for result in compile_results) and all(output.exists() for output in outputs)
            detail = "\n".join(command_detail(result) for result in compile_results if result.returncode)
            check(f"compile:{controller}", compiled, detail)
            if not compiled:
                continue
            first_bytes, second_bytes = (output.read_bytes() for output in outputs)
            same_bytes = first_bytes == second_bytes
            check(f"deterministic_bytes:{controller}", same_bytes, "separate compilation outputs differ")
            images[controller] = {
                "first_sha256": hashlib.sha256(first_bytes).hexdigest(),
                "second_sha256": hashlib.sha256(second_bytes).hexdigest(),
            }
            for output in outputs:
                inspected = run([sys.executable, "-m", "rsmicro.cli", "inspect-image", str(output), "--format", "json"], env)
                check(f"inspect:{output.name}", inspected.returncode == 0, command_detail(inspected))
    except (OSError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))

    payload = {
        "success": not failures,
        "repository_commit": run(["git", "rev-parse", "HEAD"], env).stdout.strip(),
        "checks": checks,
        "images": images,
        "artifacts_path": str(artifacts),
        "not_implemented": {
            "live_node_broker_lifecycle": "NOT_IMPLEMENTED: this smoke does not start nodes or rsmicro-tagd",
            "studio": "NOT_IMPLEMENTED: this smoke does not start Studio",
            "scada": "NOT_IMPLEMENTED: this smoke does not start standalone SCADA",
            "routing_and_fail_safe": "NOT_IMPLEMENTED: live routing/fail-safe behavior requires an orchestrated service test",
        },
        "scope": "repository validation plus deterministic compile-to-separate-files and image inspection only",
        "failures": failures,
    }
    (artifacts / "integrated-demo-summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("Integrated deterministic smoke: " + ("PASS" if payload["success"] else "FAIL"))
        for item in checks:
            print(("PASS" if item["passed"] else "FAIL") + " " + item["name"])
        print(f"Artifacts: {artifacts}")
    if holder and not args.keep_artifacts:
        holder.cleanup()
    return 0 if payload["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
