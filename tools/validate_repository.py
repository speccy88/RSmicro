#!/usr/bin/env python3
"""Deterministic repository release-readiness checks for checked-in artifacts.

This is deliberately a static/configuration validator.  It does not claim that
nodes, a broker, routing, Studio, or SCADA have been started.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CURRENT_COMPATIBILITY_DOCS = (
    "README.md",
    "profiles/rsm-logix-core-1/README.md",
    "docs/current-status.md",
    "docs/instruction-profile.md",
    "docs/native-binding.md",
    "docs/release-readiness.md",
    "docs/runtime-abi.md",
    "docs/program-image.md",
)


def validate_screen_references(project_path: Path, project: Any) -> list[str]:
    """Use the production loader for every project-declared screen."""
    from rsmicro.scada_screen_loader import ScreenLoadError, load_screen_reference

    errors: list[str] = []
    for index, reference in enumerate(project.scada.screens):
        try:
            load_screen_reference(project, project_path, reference)
        except (ScreenLoadError, OSError, TypeError, ValueError) as exc:
            errors.append(f"screen[{index}] invalid: {exc}")
    return errors


def find_hardcoded_report_claims(paths: list[Path]) -> list[str]:
    """Reject assertions masquerading as smoke evidence rather than measured data."""
    patterns = {
        "hardcoded-success": r"[\"']success[\"']\s*:\s*(?:True|False)\b",
        "hardcoded-coverage": r"[\"']controller_[ab]_instruction_coverage[\"']\s*:",
        "hardcoded-fail-safe": r"[\"']controller_[ab]_fail_safe[\"']\s*:",
        "hardcoded-routing": r"[\"']routing[\"']\s*:\s*\{[^}]*[\"'](?:safe_fallback|quality_companions)[\"']\s*:",
        "hardcoded-integration": r"[\"']deterministic_compilation[\"']\s*:\s*",
    }
    errors: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in patterns.items():
            if re.search(pattern, text, flags=re.DOTALL):
                errors.append(f"{name}: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    return errors


def compatibility_errors(root: Path) -> list[str]:
    """Compare active compatibility declarations, while leaving historical baselines alone."""
    sys.path.insert(0, str(root / "src"))
    from rsmicro.compiler.generated_opcodes import INSTRUCTION_ABI, PROFILE_ID, PROFILE_VERSION
    from rsmicro.compiler.image import VERSION as IMAGE_VERSION
    from rsmicro.compiler.profile import load_profile
    from rsmicro.native.abi import RUNTIME_ABI

    profile = load_profile()
    image_format = ".".join(map(str, IMAGE_VERSION))
    expected = {
        "profile": PROFILE_ID,
        "profile_version": PROFILE_VERSION,
        "instruction_abi": str(INSTRUCTION_ABI),
        "image_format": image_format,
        "runtime_abi": ".".join(map(str, RUNTIME_ABI)),
    }
    errors: list[str] = []
    if profile.get("profile_id") != expected["profile"]:
        errors.append("profile.yaml profile_id disagrees with generated registry")
    if str(profile.get("profile_version")) != expected["profile_version"]:
        errors.append("profile.yaml profile_version disagrees with generated registry")
    if str(profile.get("instruction_abi")) != expected["instruction_abi"]:
        errors.append("profile.yaml instruction_abi disagrees with generated registry")

    runtime = (root / "runtime/core/src/rsm_runtime.c").read_text(encoding="utf-8")
    for function, value in (
        ("rsm_runtime_abi_major", str(RUNTIME_ABI[0])),
        ("rsm_runtime_abi_minor", str(RUNTIME_ABI[1])),
        ("rsm_instruction_abi", expected["instruction_abi"]),
        ("rsm_image_format_major", str(IMAGE_VERSION[0])),
        ("rsm_image_format_minor", str(IMAGE_VERSION[1])),
    ):
        match = re.search(rf"{function}\(void\)\{{return (\d+)u;\}}", runtime)
        if not match or match.group(1) != value:
            errors.append(f"runtime {function} disagrees with compiler compatibility contract")

    # Only current compatibility pages are checked.  task-*-baseline.md files
    # intentionally document historical formats and must remain valid history.
    for relative in CURRENT_COMPATIBILITY_DOCS:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        required = [expected["instruction_abi"], image_format]
        if relative != "docs/program-image.md":
            required.append(expected["runtime_abi"])
        if relative not in {"docs/program-image.md", "docs/runtime-abi.md"}:
            required.extend((expected["profile"], expected["profile_version"]))
        for value in required:
            if value not in text:
                errors.append(f"current compatibility document lacks {value}: {relative}")
                break
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": bool(condition), "detail": detail})
        if not condition:
            errors.append(f"{name}: {detail}")

    for path in ("src/rsmicro", "runtime/core", "runtime/node", "protocol", "profiles", "schemas", "examples/integrated_demo"):
        check(f"required:{path}", (ROOT / path).exists(), "required path is missing")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for entry in ("rsmicro =", "rsmicro-tagd =", "plc-ascii =", "plc-runtime ="):
        check(f"entry-point:{entry[:-2]}", entry in pyproject, "entry point is missing")

    cmake = "\n".join(path.read_text(errors="replace") for path in ROOT.rglob("CMakeLists.txt"))
    for target in ("rsmcore", "rsmnode", "rsmlink"):
        check(f"cmake-target:{target}", target in cmake, "target is missing")

    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
    check("no-tracked-build", not any(item.startswith(("build/", "build-")) for item in tracked), "tracked build output")
    check("no-tracked-bytecode", not any(item.endswith((".pyc", ".pyo")) for item in tracked), "tracked Python bytecode")

    source = [item for item in tracked if item.endswith((".py", ".c", ".h", ".json", ".toml", ".yml", ".yaml", ".md"))]
    cloud_paths: list[str] = []
    external_bindings: list[str] = []
    for relative in source:
        value = (ROOT / relative).read_text(errors="replace")
        if relative != "tools/validate_repository.py" and ("/workspace/" in value or "/root/" in value):
            cloud_paths.append(relative)
        if relative.startswith(("src/", "runtime/", "protocol/", "examples/")) and re.search(r"(?<![\w.])0\.0\.0\.0(?![\w.])", value):
            external_bindings.append(relative)
    check("no-cloud-paths", not cloud_paths, ", ".join(cloud_paths))
    check("loopback-defaults", not external_bindings, "external bind in production/example source: " + ", ".join(external_bindings))

    claim_errors = find_hardcoded_report_claims([ROOT / "tools/run_integrated_demo.py"])
    check("no-hardcoded-smoke-claims", not claim_errors, "; ".join(claim_errors))
    contract_errors = compatibility_errors(ROOT)
    check("compatibility-contract-consistent", not contract_errors, "; ".join(contract_errors))

    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    from rsmicro.model import load_project
    from rsmicro.scada.configuration import load_config

    try:
        config = load_config(ROOT / "examples/integrated_demo/tagd.json")
        check("integrated-tagd-config-valid", len(config.controllers) == 2, "expected two configured controllers")
    except Exception as exc:
        check("integrated-tagd-config-valid", False, str(exc))

    project_path = ROOT / "examples/integrated_demo/project.rsmproj"
    result = subprocess.run([sys.executable, "-m", "rsmicro.cli", "validate", str(project_path)], cwd=ROOT, env=env, capture_output=True, text=True)
    check("integrated-project-valid", result.returncode == 0, (result.stdout + result.stderr).strip())
    try:
        screen_errors = validate_screen_references(project_path, load_project(project_path))
        check("integrated-screens-valid", not screen_errors, "; ".join(screen_errors))
    except Exception as exc:
        check("integrated-screens-valid", False, str(exc))

    for tool in ("generate_instruction_registry.py", "generate_c_conformance_fixtures.py", "generate_rsm_link_registry.py"):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / tool), "--check"], cwd=ROOT, capture_output=True, text=True)
        check(f"generated:{tool}", result.returncode == 0, (result.stdout + result.stderr).strip())

    payload = {"success": not errors, "checks": checks, "errors": errors, "warnings": []}
    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        for item in checks:
            suffix = f": {item['detail']}" if item["detail"] and not item["passed"] else ""
            print(("PASS" if item["passed"] else "FAIL") + " " + item["name"] + suffix)
        print(f"\n{len(checks) - len(errors)} passed, {len(errors)} errors, 0 warnings")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
