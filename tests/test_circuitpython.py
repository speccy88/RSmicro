import unittest

from plc_ascii.model import Binding, Program, Rung, Step, Variable
from plc_runtime.circuitpython import build_runtime_bundle
from plc_runtime.circuitpython.plc_runtime_portable import MemoryStorage, PortableRuntime


class FakeBackend:
    def __init__(self) -> None:
        self.inputs: dict[str, object] = {}
        self.outputs: dict[str, object] = {}

    def read(self, address: str) -> object:
        return self.inputs.get(address, False)

    def write(self, address: str, value: object) -> None:
        self.outputs[address] = value


def build_button_led_program() -> Program:
    return Program(
        name="button-led",
        rungs=[Rung(comment="button drives led", elements=[Step("XIC", "PB"), Step("OTE", "LED")])],
        variables=[
            Variable(tag="PB", data_type="bool", initial=False),
            Variable(tag="LED", data_type="bool", initial=False),
        ],
        bindings=[
            Binding(tag="PB", direction="input", address="IO0"),
            Binding(tag="LED", direction="output", address="IO2"),
        ],
    )


class CircuitPythonRuntimeTests(unittest.TestCase):
    def test_portable_runtime_scans_input_to_output(self) -> None:
        backend = FakeBackend()
        backend.inputs["IO0"] = True
        runtime = PortableRuntime(backend, MemoryStorage())
        runtime.load_program(build_button_led_program().to_dict())

        snapshot = runtime.scan_once(50)

        self.assertTrue(snapshot["tags"]["PB"])
        self.assertTrue(snapshot["tags"]["LED"])
        self.assertTrue(backend.outputs["IO2"])

    def test_portable_runtime_upload_returns_program_metadata(self) -> None:
        runtime = PortableRuntime(FakeBackend(), MemoryStorage())
        runtime.load_program(build_button_led_program().to_dict())

        response = runtime.handle_message({"type": "upload_program"})

        self.assertEqual(response["type"], "program")
        self.assertEqual(response["program"]["rungs"][0]["comment"], "button drives led")
        self.assertEqual(response["program"]["variables"][0]["tag"], "PB")

    def test_build_runtime_bundle_includes_program_and_board_runtime_files(self) -> None:
        bundle = build_runtime_bundle(build_button_led_program())

        self.assertIn("code.py", bundle)
        self.assertIn("plc_runtime_board.py", bundle)
        self.assertIn('"address": "IO0"', bundle["plc_program.json"])


if __name__ == "__main__":
    unittest.main()
