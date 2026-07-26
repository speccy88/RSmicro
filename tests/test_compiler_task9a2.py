import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from rsmicro.compiler import compile_project
from rsmicro.model import load_project
from rsmicro.model.deployment import Binding, Device, Endpoint
from rsmicro.native.errors import NativeSimulationError
from rsmicro.native.simulation import NativeSimulator

ROOT = Path(__file__).parents[1]
PROJECT = ROOT / 'examples/integrated_demo/project.rsmproj'


def _project():
    return load_project(PROJECT)


def _write(project, path):
    path.write_text(json.dumps(project.to_dict()), encoding='utf-8')


def _first_instruction(project):
    return project.controllers[0].programs[0].routines[0].rungs[0].nodes[0]


def _deployment_with_binding(project):
    deployment = project.deployments[0]
    tag_id = project.controllers[0].tags[0].tag_id
    deployment.devices.append(Device('test-device', 'test-driver', endpoints=[Endpoint('test-endpoint', 'input', 'BOOL', 0)]))
    deployment.bindings.append(Binding('test-binding', tag_id, 'test-device', 'test-endpoint'))
    return deployment


def _duplicate_binding(project):
    deployment = _deployment_with_binding(project)
    deployment.bindings.append(copy.copy(deployment.bindings[0]))


@pytest.mark.parametrize(
    ('name', 'mutate', 'code'),
    [
        ('project-uuid', lambda p: setattr(p, 'project_id', 'not-a-uuid'), 'RSM-E121'),
        ('controller-uuid', lambda p: setattr(p.controllers[0], 'controller_id', 'not-a-uuid'), 'RSM-E121'),
        ('tag-uuid', lambda p: setattr(p.controllers[0].tags[0], 'tag_id', 'not-a-uuid'), 'RSM-E121'),
        ('program-uuid', lambda p: setattr(p.controllers[0].programs[0], 'program_id', 'not-a-uuid'), 'RSM-E121'),
        ('routine-uuid', lambda p: setattr(p.controllers[0].programs[0].routines[0], 'routine_id', 'not-a-uuid'), 'RSM-E121'),
        ('rung-uuid', lambda p: setattr(p.controllers[0].programs[0].routines[0].rungs[0], 'rung_id', 'not-a-uuid'), 'RSM-E121'),
        ('deployment-uuid', lambda p: setattr(p.deployments[0], 'deployment_id', 'not-a-uuid'), 'RSM-E121'),
        ('instruction-uuid', lambda p: setattr(_first_instruction(p), 'instruction_id', 'not-a-uuid'), 'RSM-E121'),
        ('duplicate-controller-uuid', lambda p: setattr(p.controllers[1], 'controller_id', p.controllers[0].controller_id), 'RSM-E122'),
        ('duplicate-tag-uuid', lambda p: setattr(p.controllers[0].tags[1], 'tag_id', p.controllers[0].tags[0].tag_id), 'RSM-E122'),
        ('duplicate-program-uuid', lambda p: p.controllers[0].programs.append(copy.copy(p.controllers[0].programs[0])), 'RSM-E122'),
        ('duplicate-routine-uuid', lambda p: p.controllers[0].programs[0].routines.append(copy.copy(p.controllers[0].programs[0].routines[0])), 'RSM-E122'),
        ('duplicate-rung-uuid', lambda p: setattr(p.controllers[0].programs[0].routines[0].rungs[1], 'rung_id', p.controllers[0].programs[0].routines[0].rungs[0].rung_id), 'RSM-E122'),
        ('duplicate-deployment-uuid', lambda p: setattr(p.deployments[1], 'deployment_id', p.deployments[0].deployment_id), 'RSM-E122'),
        ('duplicate-instruction-uuid', lambda p: setattr(_first_instruction(p), 'instruction_id', p.controllers[0].programs[0].routines[0].rungs[1].nodes[0].instruction_id), 'RSM-E122'),
        ('empty-tag-name', lambda p: setattr(p.controllers[0].tags[0], 'name', ''), 'RSM-E125'),
        ('duplicate-tag-name', lambda p: setattr(p.controllers[0].tags[1], 'name', p.controllers[0].tags[0].name), 'RSM-E125'),
        ('bad-format', lambda p: setattr(p, 'format', 'other-project'), 'RSM-E123'),
        ('bad-format-version', lambda p: setattr(p, 'format_version', 99), 'RSM-E124'),
        ('missing-deployment-controller', lambda p: setattr(p.deployments[0], 'controller_id', '00000000-0000-4000-8000-000000000000'), 'RSM-E126'),
        ('missing-binding-device', lambda p: setattr(_deployment_with_binding(p).bindings[0], 'device_id', 'missing-device'), 'RSM-E126'),
        ('missing-binding-endpoint', lambda p: setattr(_deployment_with_binding(p).bindings[0], 'endpoint_id', 'missing-endpoint'), 'RSM-E126'),
        ('binding-tag-not-owned', lambda p: setattr(_deployment_with_binding(p).bindings[0], 'tag_id', p.controllers[1].tags[0].tag_id), 'RSM-E126'),
        ('duplicate-binding', _duplicate_binding, 'RSM-E127'),
        ('bad-compatibility-profile', lambda p: setattr(p.controllers[0], 'compatibility_profile', 'RSM-OTHER-1'), 'RSM-E129'),
    ],
)
def test_canonical_admission_has_direct_cli_native_parity(tmp_path, name, mutate, code):
    project = _project()
    controller_id = project.controllers[0].controller_id
    mutate(project)

    direct = compile_project(project, controller_id)
    assert not direct.success
    assert any(item.code == code for item in direct.diagnostics)
    assert all(item.severity == 'ERROR' for item in direct.diagnostics)
    assert all(item.path.startswith('/') for item in direct.diagnostics)
    assert direct.ir is direct.image_bytes is direct.manifest is direct.debug_map is None

    project_path = tmp_path / f'{name}.rsmproj'
    image_path = tmp_path / f'{name}.rsm'
    _write(project, project_path)
    cli = subprocess.run(
        [sys.executable, '-m', 'rsmicro.cli', 'compile', str(project_path), '--controller', controller_id, '--output', str(image_path), '--format', 'json'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert cli.returncode == 1
    payload = json.loads(cli.stdout)
    assert any(item['code'] == code and item['severity'] == 'ERROR' and item['path'].startswith('/') for item in payload)
    assert not image_path.exists()
    assert not Path(str(image_path) + '.manifest.json').exists()
    assert not Path(str(image_path) + '.map.json').exists()

    with pytest.raises(NativeSimulationError, match=re.escape('compilation failed:')) as error:
        NativeSimulator.from_project(project_path, controller_id)
    assert code in str(error.value)


def test_missing_endpoint_never_silently_lowers_to_internal():
    project = _project()
    deployment = _deployment_with_binding(project)
    deployment.bindings[0].endpoint_id = 'missing-endpoint'

    result = compile_project(project, project.controllers[0].controller_id, deployment_id=deployment.deployment_id)

    assert not result.success
    assert [(item.code, item.path) for item in result.diagnostics] == [
        ('RSM-E126', '/deployments/0/bindings/0'),
    ]
    assert result.ir is result.image_bytes is result.manifest is result.debug_map is None
