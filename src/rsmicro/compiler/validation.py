import math
from uuid import UUID

from .diagnostics import CompilerDiagnostic as D
from .generated_opcodes import ALIASES, OPCODES
from rsmicro.model.logic import Branch, TagOperand

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


def validate_compile_project(project, controller, deployment=None):
    """Validate every source-model invariant required before lowering an image.

    This is deliberately compiler-owned: callers may use model validation for
    editor feedback, but a successful compiler result must never depend on it.
    """
    diagnostics = []
    controller_index = _controller_path(project, controller)
    base = f'/controllers/{controller_index}'
    tags = {tag.tag_id: tag for tag in controller.tags}

    def add(code, message, path):
        diagnostics.append(D('ERROR', code, message, path))

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
            # The canonical model historically allowed a composite preset in
            # initial_value; retain that representation while validating the
            # single effective value that lowering serializes.
            preset = tag.preset if tag.preset is not None else tag.initial_value
            preset_path = 'preset' if tag.preset is not None else 'initial_value'
            if type(preset) is not int or not 0 <= preset <= INT32_MAX:
                add('RSM-E117', f'{data_type} preset must be a nonnegative signed 32-bit integer', f'{path}/{preset_path}')

    writes: dict[tuple[str, str | None], list[str]] = {}
    seen_instruction_ids = set()

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
            if node.instruction_id in seen_instruction_ids:
                add('RSM-E113', 'duplicate instruction UUID', instruction_path)
            seen_instruction_ids.add(node.instruction_id)
            mnemonic = node.mnemonic.upper()
            if mnemonic in ALIASES:
                diagnostics.append(D('WARNING', 'RSM-W204', f'deprecated mnemonic alias {mnemonic} normalized to {ALIASES[mnemonic]}', instruction_path))
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
            diagnostics.append(D('WARNING', 'RSM-W200', 'multiple destructive writes to one tag', paths[-1]))

    if deployment is not None and deployment.controller_id != controller.controller_id:
        add('RSM-E118', 'selected deployment belongs to a different controller', '/deployments')

    # Produced and consumed records retain canonical UUIDs for later node/broker
    # consumers.  Check them before they can be serialized into an image.
    produced_ids = set()
    for route_index, route in enumerate(controller.produced_tags):
        path = f'{base}/produced_tags/{route_index}'
        if not _valid_uuid(route.produced_tag_id) or route.produced_tag_id in produced_ids or not _valid_uuid(route.source_tag_id) or route.source_tag_id not in tags or _has_nonfinite(route.to_dict()):
            add('RSM-E119', 'malformed or unknown produced-tag reference', path)
        produced_ids.add(route.produced_tag_id)

    controllers = {candidate.controller_id: candidate for candidate in project.controllers}
    consumed_ids = set()
    for route_index, route in enumerate(controller.consumed_tags):
        path = f'{base}/consumed_tags/{route_index}'
        source = controllers.get(route.source_controller_id)
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
    return validate_compile_project(SimpleNamespace(controllers=[controller]), controller)
