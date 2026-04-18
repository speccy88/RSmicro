import unittest

from plc_ascii.model import Binding, Program, RUNTIME_TARGET_CIRCUITPYTHON, RUNTIME_TARGET_PROPELLER2, Rung, Step
from plc_runtime.runtime import DeviceRuntime


def build_runtime_program() -> Program:
    return Program(
        name="runtime-test",
        rungs=[
            Rung(
                name="drive",
                conditions=[Step("XIC", "start_pb")],
                actions=[Step("OTE", "motor_cmd")],
            )
        ],
        bindings=[
            Binding(tag="start_pb", direction="input", address="D5"),
            Binding(tag="motor_cmd", direction="output", address="D17"),
        ],
    )


class DeviceRuntimeTests(unittest.TestCase):
    def test_program_round_trips_runtime_target(self) -> None:
        program = Program(
            name="targeted",
            runtime_target=RUNTIME_TARGET_PROPELLER2,
            rungs=[],
            variables=[],
            bindings=[],
        )

        restored = Program.from_dict(program.to_dict())

        self.assertEqual(restored.runtime_target, RUNTIME_TARGET_PROPELLER2)

    def test_program_defaults_runtime_target_for_legacy_payloads(self) -> None:
        restored = Program.from_dict({"name": "legacy", "rungs": [], "variables": [], "bindings": []})

        self.assertEqual(restored.runtime_target, RUNTIME_TARGET_CIRCUITPYTHON)

    def test_set_tag_updates_bound_input_backend(self) -> None:
        runtime = DeviceRuntime()
        runtime.load_program(build_runtime_program())
        runtime.handle_message({"type": "set_tag", "tag": "start_pb", "value": True})
        snapshot = runtime.handle_message({"type": "snapshot_request"})
        self.assertTrue(snapshot["tags"]["start_pb"])
        self.assertTrue(snapshot["tags"]["motor_cmd"])
        self.assertTrue(snapshot["rung_power"][0])

    def test_upload_program_returns_full_program_payload(self) -> None:
        runtime = DeviceRuntime()
        program = build_runtime_program()
        runtime.load_program(program)

        response = runtime.handle_message({"type": "upload_program"})

        self.assertEqual(response["type"], "program")
        self.assertEqual(response["program"]["name"], program.name)
        self.assertEqual(response["program"]["bindings"][0]["tag"], "start_pb")


if __name__ == "__main__":
    unittest.main()
