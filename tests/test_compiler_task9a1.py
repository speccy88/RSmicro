import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from rsmicro.compiler import compile_project, inspect_image
from rsmicro.model import load_project
from rsmicro.model.logic import Branch
from rsmicro.model.tags import TagType
from rsmicro.native.errors import NativeSimulationError
from rsmicro.native import NativeRuntime
from rsmicro.native.simulation import NativeSimulator

ROOT = Path(__file__).parents[1]


def _project():
    return load_project(ROOT / 'examples/compiler_demo/project.rsmproj')


def _write(project, path):
    path.write_text(json.dumps(project.to_dict()), encoding='utf-8')


def _codes(result):
    return [item.code for item in result.diagnostics]


def _diagnostics(result):
    return [(item.code, item.message) for item in result.diagnostics]


@pytest.mark.parametrize(
    ('mutate', 'code'),
    [
        (lambda p: setattr(p.controllers[0].programs[0].routines[0].rungs[0], 'nodes', []), 'RSM-E107'),
        (lambda p: p.controllers[0].programs[0].routines[0].rungs[0].nodes.__setitem__(0, Branch([[]])), 'RSM-E108'),
        (lambda p: p.controllers[0].programs[0].routines[0].rungs[0].nodes.__setitem__(0, Branch([[], []])), 'RSM-E109'),
        (lambda p: setattr(p.controllers[0].tags[0], 'initial_value', 'not-a-bool'), 'RSM-E114'),
        (lambda p: (setattr(p.controllers[0].tags[0], 'data_type', TagType.DINT), setattr(p.controllers[0].tags[0], 'initial_value', 2**31)), 'RSM-E116'),
        (lambda p: (setattr(p.controllers[0].tags[0], 'data_type', TagType.REAL), setattr(p.controllers[0].tags[0], 'initial_value', math.nan)), 'RSM-E115'),
        (lambda p: (setattr(p.controllers[0].tags[0], 'data_type', TagType.TIMER), setattr(p.controllers[0].tags[0], 'initial_value', None), setattr(p.controllers[0].tags[0], 'preset', -1)), 'RSM-E117'),
    ],
)
def test_compiler_admission_rejects_invalid_source_without_emitting_image(mutate, code):
    project = _project()
    mutate(project)
    result = compile_project(project, project.controllers[0].controller_id)
    assert not result.success
    assert code in _codes(result)
    assert result.image_bytes is result.manifest is result.debug_map is None


@pytest.mark.parametrize(
    ("name", "mutate", "expected"),
    [
        ("empty-rung", lambda rung: setattr(rung, "nodes", []), [("RSM-E107", "rung cannot be empty")]),
        ("one-lane", lambda rung: rung.nodes.__setitem__(0, Branch([[]])), [("RSM-E108", "branch requires at least two lanes"), ("RSM-E109", "branch lane cannot be empty"), ("RSM-W200", "multiple destructive writes to one tag")]),
        ("empty-lanes", lambda rung: rung.nodes.__setitem__(0, Branch([[], []])), [("RSM-E109", "branch lane cannot be empty"), ("RSM-E109", "branch lane cannot be empty"), ("RSM-W200", "multiple destructive writes to one tag")]),
    ],
)
def test_invalid_rung_admission_is_identical_for_direct_cli_and_native_simulator(tmp_path, name, mutate, expected):
    project = _project()
    controller = project.controllers[0].controller_id
    mutate(project.controllers[0].programs[0].routines[0].rungs[0])
    direct = compile_project(project, controller)
    assert not direct.success
    assert _diagnostics(direct) == expected
    assert direct.image_bytes is direct.manifest is direct.debug_map is None

    path = tmp_path / f'{name}.rsmproj'
    output = tmp_path / f'{name}.rsm'
    _write(project, path)
    cli = subprocess.run(
        [sys.executable, '-m', 'rsmicro.cli', 'compile', str(path), '--controller', controller, '--output', str(output), '--format', 'json'],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert cli.returncode == 1
    assert [(item['code'], item['message']) for item in json.loads(cli.stdout)] == expected
    assert not output.exists()
    native_error = "compilation failed: " + "; ".join(f"{code}: {message}" for code, message in expected)
    with pytest.raises(NativeSimulationError, match=__import__('re').escape(native_error)):
        NativeSimulator.from_project(path, controller)


def test_rejects_deployment_for_other_controller_before_lowering():
    project = load_project(ROOT / 'examples/integrated_demo/project.rsmproj')
    deployment = project.deployments[0]
    deployment.controller_id = project.controllers[1].controller_id
    result = compile_project(project, project.controllers[0].controller_id, deployment_id=deployment.deployment_id)
    assert not result.success
    assert 'RSM-E118' in _codes(result)
    assert result.image_bytes is None


@pytest.mark.parametrize('mutate', [
    lambda p: setattr(p.controllers[0].produced_tags[0], 'source_tag_id', 'not-a-uuid'),
    lambda p: setattr(p.controllers[1].consumed_tags[0], 'destination_tag_id', 'not-a-uuid'),
    lambda p: setattr(p.controllers[1].consumed_tags[0], 'source_controller_id', '00000000-0000-4000-8000-000000000000'),
    lambda p: setattr(p.controllers[1].consumed_tags[0], 'source_produced_tag_id', '00000000-0000-4000-8000-000000000000'),
])
def test_malformed_produced_consumed_references_are_rejected(mutate):
    project = load_project(ROOT / 'examples/integrated_demo/project.rsmproj')
    mutate(project)
    # The producer validates producer records; the consumer validates every
    # source/destination/produced reference it itself serializes.
    target = project.controllers[0] if 'not-a-uuid' == project.controllers[0].produced_tags[0].source_tag_id else project.controllers[1]
    result = compile_project(project, target.controller_id)
    assert not result.success
    assert 'RSM-E119' in _codes(result) or 'RSM-E120' in _codes(result)
    assert result.image_bytes is None


def test_produced_consumed_metadata_is_deterministic_and_round_trips_through_inspection():
    project = load_project(ROOT / 'examples/integrated_demo/project.rsmproj')
    for controller in project.controllers:
        first = compile_project(project, controller.controller_id)
        second = compile_project(project, controller.controller_id)
        assert first.success and second.success
        assert first.image_bytes == second.image_bytes
        assert first.manifest == second.manifest
        inspected = inspect_image(first.image_bytes)
        expected_produced = sorted((route.to_dict() for route in controller.produced_tags), key=lambda route: route['produced_tag_id'])
        expected_consumed = sorted((route.to_dict() for route in controller.consumed_tags), key=lambda route: route['consumed_tag_id'])
        assert first.manifest['produced_tags'] == inspected['produced_tags'] == expected_produced
        assert first.manifest['consumed_tags'] == inspected['consumed_tags'] == expected_consumed
        assert first.manifest['produced_tags'] or first.manifest['consumed_tags']


def test_native_core_loads_metadata_bearing_image():
    project = load_project(ROOT / 'examples/integrated_demo/project.rsmproj')
    result = compile_project(project, project.controllers[0].controller_id)
    assert result.success and result.manifest['produced_tags']
    # Let native discovery select the platform library.  Windows CI supplies
    # its Visual Studio Release artifact via RSMICRO_CORE_LIBRARY.
    with NativeRuntime().load_image(result.image_bytes, result.manifest, result.debug_map) as runtime:
        assert runtime.mode.name == 'PROGRAM'
