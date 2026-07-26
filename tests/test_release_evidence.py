import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from rsmicro.model import load_project
from rsmicro.scada.configuration import load_config
from rsmicro.scada.errors import ConfigurationError
from rsmicro.scada_screen_loader import load_project_screens


ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "QT_QPA_PLATFORM": "offscreen"}


def _validator_module():
    spec = importlib.util.spec_from_file_location("validate_repository", ROOT / "tools" / "validate_repository.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_integrated_tagd_config_loads_with_two_loopback_controllers():
    config = load_config(ROOT / "examples/integrated_demo/tagd.json")
    assert [controller.controller_id for controller in config.controllers] == [
        "09d4dc32-8813-5abc-9a4e-1a78e1780591",
        "1c479764-d825-5c32-a104-87d304ed619d",
    ]
    assert all(controller.host == "127.0.0.1" for controller in config.controllers)
    assert config.resolved_project_path == str((ROOT / "examples/integrated_demo/project.rsmproj").resolve())


def test_tagd_config_rejects_names_unknown_ids_and_missing_projects(tmp_path):
    source = json.loads((ROOT / "examples/integrated_demo/tagd.json").read_text(encoding="utf-8"))
    shutil.copy2(ROOT / "examples/integrated_demo/project.rsmproj", tmp_path / "project.rsmproj")
    config_path = tmp_path / "tagd.json"

    source["controllers"][0]["controller_id"] = "controller-a"
    config_path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="canonical UUID"):
        load_config(config_path)

    source["controllers"][0]["controller_id"] = "00000000-0000-4000-8000-000000000000"
    config_path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not present"):
        load_config(config_path)

    source["project"] = "missing.rsmproj"
    config_path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_config(config_path)


def test_repository_validator_reports_green_json():
    result = subprocess.run(
        [sys.executable, "tools/validate_repository.py", "--format", "json"],
        cwd=ROOT,
        env=ENV,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout)["success"] is True


def test_smoke_reports_determinism_and_unimplemented_live_scope(tmp_path):
    result = subprocess.run(
        [sys.executable, "tools/run_integrated_demo.py", "--headless", "--format", "json", "--artifacts-dir", str(tmp_path)],
        cwd=ROOT,
        env=ENV,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    assert report["success"] is True
    assert report["images"]["controller-a"]["first_sha256"] == report["images"]["controller-a"]["second_sha256"]
    assert report["not_implemented"]["live_node_broker_lifecycle"].startswith("NOT_IMPLEMENTED")
    assert report["not_implemented"]["routing_and_fail_safe"].startswith("NOT_IMPLEMENTED")
    assert "does not start" in report["not_implemented"]["scada"]


def test_repository_validator_rejects_missing_and_unknown_project_declared_screens(tmp_path):
    validator = _validator_module()
    project_path = ROOT / "examples/integrated_demo/project.rsmproj"
    project = load_project(project_path)
    project.scada.screens = [{"screen_id": "missing", "name": "missing", "path": "screens/missing.json"}]
    assert validator.validate_screen_references(tmp_path / "project.rsmproj", project) == [
        "screen[0] invalid: screen file does not exist: screens/missing.json"
    ]

    screen = json.loads((ROOT / "examples/integrated_demo/screens/overview.json").read_text(encoding="utf-8"))
    bound = next(obj for obj in screen["objects"] if obj.get("binding", {}).get("tag_uuid"))
    bound["binding"]["tag_uuid"] = "00000000-0000-4000-8000-000000000000"
    (tmp_path / "screens").mkdir()
    (tmp_path / "screens/overview.json").write_text(json.dumps(screen), encoding="utf-8")
    project.scada.screens = [{"screen_id": screen["screen_id"], "name": screen["name"], "path": "screens/overview.json"}]
    assert validator.validate_screen_references(tmp_path / "project.rsmproj", project) == [
        "screen[0] invalid: invalid screen screens/overview.json: unknown tag UUID: 00000000-0000-4000-8000-000000000000"
    ]


def test_all_integrated_screens_use_the_production_loader_and_render_objects():
    project_path = ROOT / "examples/integrated_demo/project.rsmproj"
    project = load_project(project_path)
    screens = load_project_screens(project, project_path)
    assert [screen.name for screen in screens] == [
        "overview", "controller_a", "controller_b", "alarms", "trends"
    ]
    assert all(screen.objects for screen in screens)
    for screen in screens:
        result = subprocess.run(
            [sys.executable, "-m", "rsmicro.scada_runtime.main", "--project", str(project_path),
             "--screen", screen.name, "--offscreen", "--verify", "--run-duration", "0.01"],
            cwd=ROOT, env=ENV, text=True, capture_output=True, check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert f"{len(screen.objects)} objects" in result.stdout


def test_studio_opens_integrated_project_headlessly():
    result = subprocess.run(
        [sys.executable, "-m", "rsmicro.studio.main",
         "examples/integrated_demo/project.rsmproj", "--offscreen", "--verify",
         "--run-duration", "0.01"],
        cwd=ROOT, env=ENV, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "2 controllers, 2 routines" in result.stdout


def test_repository_validator_rejects_hardcoded_smoke_claims(tmp_path):
    validator = _validator_module()
    smoke = tmp_path / "smoke.py"
    smoke.write_text("report = {'success': True, 'controller_a_instruction_coverage': 24, 'controller_b_fail_safe': True}\n", encoding="utf-8")
    claims = validator.find_hardcoded_report_claims([smoke])
    assert {claim.split(":", 1)[0] for claim in claims} == {
        "hardcoded-success",
        "hardcoded-coverage",
        "hardcoded-fail-safe",
    }


def test_repository_validator_rejects_runtime_abi_drift(tmp_path):
    validator = _validator_module()
    for relative in validator.CURRENT_COMPATIBILITY_DOCS:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    runtime = tmp_path / "runtime/core/src/rsm_runtime.c"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    source = (ROOT / "runtime/core/src/rsm_runtime.c").read_text(encoding="utf-8")
    runtime.write_text(
        source.replace("rsm_runtime_abi_minor(void){return 2u;}",
                       "rsm_runtime_abi_minor(void){return 9u;}"),
        encoding="utf-8",
    )
    errors = validator.compatibility_errors(tmp_path)
    assert "runtime rsm_runtime_abi_minor disagrees with compiler compatibility contract" in errors
