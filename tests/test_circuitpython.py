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
    def test_portable_runtime_hello_reports_idle_when_no_program_is_stored(self) -> None:
        runtime = PortableRuntime(FakeBackend(), MemoryStorage())

        response = runtime.handle_message({"type": "hello"})

        self.assertEqual(response["type"], "hello")
        self.assertEqual(response["platform"], "circuitpython")
        self.assertEqual(response["mode"], "run")
        self.assertFalse(response["program_loaded"])

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
        self.assertEqual(response["program"]["runtime_target"], "circuitpython")

    def test_set_tag_can_update_timer_members(self) -> None:
        runtime = PortableRuntime(FakeBackend(), MemoryStorage())
        runtime.load_program(
            Program(
                name="timer-edit",
                runtime_target="circuitpython",
                rungs=[Rung(comment="", elements=[Step("TON", "timer1", arg=1000)])],
                variables=[Variable(tag="timer1", data_type="timer", preset=1000)],
                bindings=[],
            ).to_dict()
        )

        response = runtime.handle_message({"type": "set_tag", "tag": "timer1.pre", "value": 250})
        snapshot = runtime.handle_message({"type": "snapshot_request"})

        self.assertEqual(response["type"], "ack")
        self.assertEqual(snapshot["timers"]["timer1"]["pre"], 250)
        self.assertEqual(snapshot["tags"]["timer1.pre"], 250)

    def test_upload_program_reflects_current_counter_preset_after_edit(self) -> None:
        runtime = PortableRuntime(FakeBackend(), MemoryStorage())
        runtime.load_program(
            Program(
                name="counter-edit",
                runtime_target="circuitpython",
                rungs=[Rung(comment="", elements=[Step("CTU", "counter1", arg=2)])],
                variables=[Variable(tag="counter1", data_type="counter", preset=2)],
                bindings=[],
            ).to_dict()
        )

        runtime.handle_message({"type": "set_tag", "tag": "counter1.pre", "value": 9})
        response = runtime.handle_message({"type": "upload_program"})

        self.assertEqual(response["type"], "program")
        self.assertEqual(response["program"]["variables"][0]["preset"], 9)
        self.assertEqual(response["program"]["rungs"][0]["elements"][0]["arg"], 9)

    def test_start_from_stop_does_not_recount_true_counter_input(self) -> None:
        runtime = PortableRuntime(FakeBackend(), MemoryStorage())
        runtime.load_program(
            Program(
                name="counter-run",
                runtime_target="circuitpython",
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

    def test_build_runtime_bundle_omits_program_file_for_runtime_only_install(self) -> None:
        bundle = build_runtime_bundle()

        self.assertIn("code.py", bundle)
        self.assertIn("plc_runtime_board.py", bundle)
        self.assertNotIn("plc_program.json", bundle)

    def test_build_runtime_bundle_can_include_program_when_requested(self) -> None:
        bundle = build_runtime_bundle(build_button_led_program(), include_program=True)

        self.assertIn("plc_program.json", bundle)
        self.assertIn('"address": "IO0"', bundle["plc_program.json"])


if __name__ == "__main__":
    unittest.main()
