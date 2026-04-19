import unittest

from plc_ascii.model import Binding, Program, Rung, Step, Variable
from plc_runtime.micropython import build_runtime_bundle
from plc_runtime.micropython.plc_runtime_portable import MemoryStorage, PortableRuntime


class FakeBackend:
    def __init__(self) -> None:
        self.inputs: dict[int, object] = {}
        self.outputs: dict[int, object] = {}

    def read(self, address: int) -> object:
        return self.inputs.get(address, False)

    def write(self, address: int, value: object) -> None:
        self.outputs[address] = value


def build_pico_led_program() -> Program:
    return Program(
        name="micropython-pico2w",
        runtime_target="micropython",
        rungs=[Rung(comment="drive led", elements=[Step("XIC", "LED_EN"), Step("OTE", "LED")])],
        variables=[
            Variable(tag="LED_EN", data_type="bool", initial=True),
            Variable(tag="LED", data_type="bool", initial=False),
        ],
        bindings=[Binding(tag="LED", direction="output", address=0)],
    )


class MicroPythonRuntimeTests(unittest.TestCase):
    def test_portable_runtime_hello_reports_micropython_platform(self) -> None:
        runtime = PortableRuntime(FakeBackend(), MemoryStorage())

        response = runtime.handle_message({"type": "hello"})

        self.assertEqual(response["type"], "hello")
        self.assertEqual(response["platform"], "micropython")
        self.assertFalse(response["program_loaded"])

    def test_portable_runtime_scans_output_with_integer_gpio_binding(self) -> None:
        backend = FakeBackend()
        runtime = PortableRuntime(backend, MemoryStorage())
        runtime.load_program(build_pico_led_program().to_dict())

        snapshot = runtime.scan_once(50)

        self.assertTrue(snapshot["tags"]["LED_EN"])
        self.assertTrue(snapshot["tags"]["LED"])
        self.assertTrue(backend.outputs[0])

    def test_build_runtime_bundle_uses_main_py_and_omits_program_by_default(self) -> None:
        bundle = build_runtime_bundle()

        self.assertIn("main.py", bundle)
        self.assertIn("plc_runtime_board.py", bundle)
        self.assertNotIn("plc_program.json", bundle)

    def test_build_runtime_bundle_can_include_integer_binding_program(self) -> None:
        bundle = build_runtime_bundle(build_pico_led_program(), include_program=True)

        self.assertIn("plc_program.json", bundle)
        self.assertIn('"address": 0', bundle["plc_program.json"])

    def test_upload_program_reflects_current_counter_preset_after_edit(self) -> None:
        runtime = PortableRuntime(FakeBackend(), MemoryStorage())
        runtime.load_program(
            Program(
                name="counter-edit",
                runtime_target="micropython",
                rungs=[Rung(comment="", elements=[Step("CTU", "counter1", arg=3)])],
                variables=[Variable(tag="counter1", data_type="counter", preset=3)],
                bindings=[],
            ).to_dict()
        )

        runtime.handle_message({"type": "set_tag", "tag": "counter1.pre", "value": 8})
        response = runtime.handle_message({"type": "upload_program"})

        self.assertEqual(response["type"], "program")
        self.assertEqual(response["program"]["variables"][0]["preset"], 8)
        self.assertEqual(response["program"]["rungs"][0]["elements"][0]["arg"], 8)

    def test_start_from_stop_does_not_recount_true_counter_input(self) -> None:
        runtime = PortableRuntime(FakeBackend(), MemoryStorage())
        runtime.load_program(
            Program(
                name="counter-run",
                runtime_target="micropython",
                rungs=[Rung(comment="", elements=[Step("XIC", "pulse"), Step("CTU", "counter1", arg=5)])],
                variables=[
                    Variable(tag="pulse", data_type="bool", initial=False),
                    Variable(tag="counter1", data_type="counter", preset=5),
                ],
                bindings=[],
            ).to_dict()
        )

        runtime.handle_message({"type": "run", "mode": "stop"})
        runtime.handle_message({"type": "set_tag", "tag": "pulse", "value": True})
        runtime.handle_message({"type": "set_tag", "tag": "counter1.acc", "value": 3})
        runtime.handle_message({"type": "run", "mode": "run"})
        snapshot = runtime.scan_once(50)

        self.assertEqual(snapshot["counters"]["counter1"]["acc"], 3)


if __name__ == "__main__":
    unittest.main()
