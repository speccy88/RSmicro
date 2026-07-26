import math
from typing import Any
from uuid import UUID

from rsmicro.model.logic import Branch, TagOperand

from .diagnostics import CompilerDiagnostic as D
from .generated_opcodes import ALIASES, OPCODES, PROFILE_ID

MEMBERS = {'TIMER': {'PRE', 'ACC', 'EN', 'TT', 'DN'}, 'COUNTER': {'PRE', 'ACC', 'CU', 'CD', 'DN', 'OV', 'UN'}}
OWNED = {'TIMER': {'ACC', 'EN', 'TT', 'DN'}, 'COUNTER': {'ACC', 'CU', 'CD', 'DN', 'OV', 'UN'}}
INT32_MIN = -2147483648
INT32_MAX = 2147483647


def _valid_uuid(value):
    try:
        UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def _has_nonfinite(value):
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_has_nonfinite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_nonfinite(item) for item in value)
    return False


def _controller_path(project, controller):
    for index, candidate in enumerate(project.controllers):
        if candidate is controller:
            return index
    return -1


def validate_compile_project(project, controller=None, deployment=None):
    """Validate every canonical-model invariant required before lowering.

    This gate intentionally does not depend on editor/model validation.  It
    validates the complete project before a controller is selected, so malformed
    source data cannot escape into image construction or be reinterpreted by
    lowering.
    """
    diagnostics = []

    def add(code, message, path):
        diagnostics.append(D('ERROR', code, message, path))

    def warn(code, message, path):
        diagnostics.append(D('WARNING', code, message, path))

    seen_ids = set()

    def identity(value, path):
        if not _valid_uuid(value):
            add('RSM-E121', 'invalid UUID', path)
            return
        if value in seen_ids:
            add('RSM-E122', 'duplicate UUID', path)
        seen_ids.add(value)

    # Canonical project structure.  These rules intentionally cover every
    # controller, not just the selected target: a compilation result certifies
    # the project it was produced from, and deployments can refer across it.
    if project.format != 'rsmicro-project':
        add('RSM-E123', 'unsupported project format', '/format')
    if project.format_version != 1:
        add('RSM-E124', 'unsupported project format version', '/format_version')
    identity(project.project_id, '/project_id')

    controllers_by_id: dict[str, Any] = {}
    controller_tag_ids: dict[str, set[str]] = {}
    for controller_index, candidate in enumerate(project.controllers):
        base = f'/controllers/{controller_index}'
        identity(candidate.controller_id, f'{base}/controller_id')
        # Keep the first object for ownership checks.  A duplicate controller
        # UUID is already a fatal canonical identity error.
        controllers_by_id.setdefault(candidate.controller_id, candidate)
        if candidate.compatibility_profile not in (None, PROFILE_ID):
            add('RSM-E129', f'unsupported controller compatibility profile {candidate.compatibility_profile}', f'{base}/compatibility_profile')

        tag_ids = set()
        tag_names = set()
        for tag_index, tag in enumerate(candidate.tags):
            path = f'{base}/tags/{tag_index}'
            identity(tag.tag_id, f'{path}/tag_id')
            tag_ids.add(tag.tag_id)
            if not tag.name or tag.name in tag_names:
                add('RSM-E125', 'empty or duplicate tag name', f'{path}/name')
            tag_names.add(tag.name)
        controller_tag_ids[candidate.controller_id] = tag_ids

        def canonical_nodes(nodes, path):
            for node_index, node in enumerate(nodes):
                node_path = f'{path}/nodes/{node_index}'
                if isinstance(node, Branch):
                    for lane_index, lane in enumerate(node.lanes):
                        canonical_nodes(lane, f'{node_path}/lanes/{lane_index}')
                else:
                    identity(node.instruction_id, f'{node_path}/instruction_id')

        for program_index, program in enumerate(candidate.programs):
            program_path = f'{base}/programs/{program_index}'
            identity(program.program_id, f'{program_path}/program_id')
            for routine_index, routine in enumerate(program.routines):
                routine_path = f'{program_path}/routines/{routine_index}'
                identity(routine.routine_id, f'{routine_path}/routine_id')
                for rung_index, rung in enumerate(routine.rungs):
                    rung_path = f'{routine_path}/rungs/{rung_index}'
                    identity(rung.rung_id, f'{rung_path}/rung_id')
                    canonical_nodes(rung.nodes, rung_path)

    for deployment_index, candidate in enumerate(project.deployments):
        base = f'/deployments/{deployment_index}'
        identity(candidate.deployment_id, f'{base}/deployment_id')
        owner = controllers_by_id.get(candidate.controller_id)
        if owner is None:
            add('RSM-E126', 'deployment controller is missing', f'{base}/controller_id')
        endpoints = {
            (device.device_id, endpoint.endpoint_id)
            for device in candidate.devices
            for endpoint in device.endpoints
        }
        owner_tags = controller_tag_ids.get(candidate.controller_id, set())
        bound_tags = set()
        for binding_index, binding in enumerate(candidate.bindings):
            binding_path = f'{base}/bindings/{binding_index}'
            if binding.tag_id not in owner_tags:
                add('RSM-E126', 'deployment binding tag is not owned by its controller', f'{binding_path}/tag_id')
            if (binding.device_id, binding.endpoint_id) not in endpoints:
                add('RSM-E126', 'deployment binding device or endpoint is missing', binding_path)
            if binding.tag_id in bound_tags:
                add('RSM-E127', 'tag has multiple deployment bindings', f'{binding_path}/tag_id')
            bound_tags.add(binding.tag_id)

    # Without a selected controller this is the structural preflight used by
    # compile_project before UUID-or-name resolution.
    if controller is None:
        return diagnostics

    controller_index = _controller_path(project, controller)
    base = f'/controllers/{controller_index}'
    tags = {tag.tag_id: tag for tag in controller.tags}

    # Values are serialized into both binary runtime records and strict JSON.
    for tag_index, tag in enumerate(controller.tags):
        path = f'{base}/tags/{tag_index}'
        data_type = str(tag.data_type)
        value = tag.initial_value
        if data_type == 'BOOL' and value is not None and type(value) is not bool:
            add('RSM-E114', 'BOOL initial value must be boolean', f'{path}/initial_value')
        elif data_type == 'DINT' and value is not None:
            if type(value) is not int:
                add('RSM-E114', 'DINT initial value must be an integer', f'{path}/initial_value')
            elif not INT32_MIN <= value <= INT32_MAX:
                add('RSM-E116', 'DINT initial value out of range', f'{path}/initial_value')
        elif data_type == 'REAL' and value is not None:
            if type(value) not in (int, float):
                add('RSM-E114', 'REAL initial value must be numeric', f'{path}/initial_value')
            elif not math.isfinite(value):
                add('RSM-E115', 'non-finite REAL initial value', f'{path}/initial_value')
        elif data_type in {'TIMER', 'COUNTER'}:
            preset = tag.preset if tag.preset is not None else tag.initial_value
            preset_path = 'preset' if tag.preset is not None else 'initial_value'
            if type(preset) is not int or not 0 <= preset <= INT32_MAX:
                add('RSM-E117', f'{data_type} preset must be a nonnegative signed 32-bit integer', f'{path}/{preset_path}')

    writes: dict[tuple[str, str | None], list[str]] = {}

    def validate_nodes(nodes, path):
        for node_index, node in enumerate(nodes):
            node_path = f'{path}/nodes/{node_index}'
            if isinstance(node, Branch):
                if len(node.lanes) < 2:
                    add('RSM-E108', 'branch requires at least two lanes', node_path)
                for lane_index, lane in enumerate(node.lanes):
                    lane_path = f'{node_path}/lanes/{lane_index}'
                    if not lane:
                        add('RSM-E109', 'branch lane cannot be empty', lane_path)
                    validate_nodes(lane, lane_path)
                continue

            instruction_path = f'{node_path}/instruction_id'
            mnemonic = node.mnemonic.upper()
            if mnemonic in ALIASES:
                warn('RSM-W204', f'deprecated mnemonic alias {mnemonic} normalized to {ALIASES[mnemonic]}', instruction_path)
                mnemonic = ALIASES[mnemonic]
            if mnemonic not in OPCODES:
                add('RSM-E101', f'unsupported instruction {mnemonic}', instruction_path)
                continue
            from .profile import load_instruction

            spec = load_instruction(mnemonic)
            legacy_zero_ons = mnemonic == 'ONS' and not node.operands
            if len(node.operands) != len(spec['operands']) and not legacy_zero_ons:
                add('RSM-E102', f'{mnemonic} expects {len(spec["operands"])} operands, got {len(node.operands)}', instruction_path)
                continue
            for operand_index, (operand, rule) in enumerate(zip(node.operands, spec['operands'])):
                operand_path = f'{node_path}/operands/{operand_index}'
                if isinstance(operand, TagOperand):
                    tag = tags.get(operand.tag_id)
                    if not tag:
                        add('RSM-E103', f'missing tag {operand.tag_id}', operand_path)
                        continue
                    data_type = str(tag.data_type)
                    member = operand.member.upper() if operand.member else None
                    if member:
                        if data_type not in MEMBERS or member not in MEMBERS[data_type]:
                            add('RSM-E104', f'invalid member {operand.member} for {data_type}', operand_path)
                            continue
                        data_type = 'DINT' if member in {'PRE', 'ACC'} else 'BOOL'
                    if data_type not in rule['types']:
                        add('RSM-E105', f'operand {operand_index + 1}: {data_type} not in {rule["types"]}', operand_path)
                    if rule['writable'] and (not tag.writable or (member and member in OWNED.get(str(tag.data_type), set()))):
                        add('RSM-E106', 'destination is not writable', operand_path)
                    if rule['writable']:
                        writes.setdefault((tag.tag_id, member), []).append(instruction_path)
                else:
                    value = operand.value
                    if not rule['literal']:
                        add('RSM-E105', 'literal not permitted', operand_path)
                    if isinstance(value, int) and not isinstance(value, bool) and not INT32_MIN <= value <= INT32_MAX:
                        add('RSM-E116', 'DINT literal out of range', operand_path)
                    if isinstance(value, float) and not math.isfinite(value):
                        add('RSM-E115', 'non-finite REAL literal', operand_path)

    for program_index, program in enumerate(controller.programs):
        for routine_index, routine in enumerate(program.routines):
            for rung_index, rung in enumerate(routine.rungs):
                rung_path = f'{base}/programs/{program_index}/routines/{routine_index}/rungs/{rung_index}'
                if not rung.nodes:
                    add('RSM-E107', 'rung cannot be empty', rung_path)
                validate_nodes(rung.nodes, rung_path)

    for paths in writes.values():
        if len(paths) > 1:
            warn('RSM-W200', 'multiple destructive writes to one tag', paths[-1])

    if deployment is not None and deployment.controller_id != controller.controller_id:
        add('RSM-E118', 'selected deployment belongs to a different controller', '/deployments')

    produced_ids = set()
    for route_index, route in enumerate(controller.produced_tags):
        path = f'{base}/produced_tags/{route_index}'
        if not _valid_uuid(route.produced_tag_id) or route.produced_tag_id in produced_ids or not _valid_uuid(route.source_tag_id) or route.source_tag_id not in tags or _has_nonfinite(route.to_dict()):
            add('RSM-E119', 'malformed or unknown produced-tag reference', path)
        produced_ids.add(route.produced_tag_id)

    consumed_ids = set()
    for route_index, route in enumerate(controller.consumed_tags):
        path = f'{base}/consumed_tags/{route_index}'
        source = controllers_by_id.get(route.source_controller_id)
        source_produced = {item.produced_tag_id for item in source.produced_tags} if source else set()
        malformed = (
            not _valid_uuid(route.consumed_tag_id) or route.consumed_tag_id in consumed_ids
            or not _valid_uuid(route.destination_tag_id) or route.destination_tag_id not in tags
            or not _valid_uuid(route.source_controller_id) or source is None
            or not _valid_uuid(route.source_produced_tag_id) or route.source_produced_tag_id not in source_produced
            or _has_nonfinite(route.to_dict())
        )
        quality = route.quality_handling
        for key in ('good_tag_id', 'stale_tag_id', 'bad_tag_id'):
            if key in quality and (not _valid_uuid(quality[key]) or quality[key] not in tags):
                malformed = True
        if malformed:
            add('RSM-E120', 'malformed or unknown consumed-tag reference', path)
        consumed_ids.add(route.consumed_tag_id)
    return diagnostics


def validate_controller(controller):
    """Compatibility wrapper for callers which only have a controller."""
    from types import SimpleNamespace

    return validate_compile_project(SimpleNamespace(
        format='rsmicro-project',
        format_version=1,
        project_id='00000000-0000-4000-8000-000000000000',
        controllers=[controller],
        deployments=[],
    ), controller)
