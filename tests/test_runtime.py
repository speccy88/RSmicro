import unittest

from plc_ascii.model import Binding, Program, Rung, Step
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
    def test_set_tag_updates_bound_input_backend(self) -> None:
        runtime = DeviceRuntime()
        runtime.load_program(build_runtime_program())
        runtime.handle_message({"type": "set_tag", "tag": "start_pb", "value": True})
        snapshot = runtime.handle_message({"type": "snapshot_request"})
        self.assertTrue(snapshot["tags"]["start_pb"])
        self.assertTrue(snapshot["tags"]["motor_cmd"])
        self.assertTrue(snapshot["rung_power"][0])


if __name__ == "__main__":
    unittest.main()
