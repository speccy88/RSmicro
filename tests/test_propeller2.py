import unittest

from plc_ascii.model import Binding, Program, Rung, Step, Variable
from plc_runtime.propeller2 import build_runtime_source


def build_propeller2_program() -> Program:
    return Program(
        name="propeller2-led56",
        rungs=[Rung(comment="led command drives LED", elements=[Step("XIC", "led_cmd"), Step("OTE", "led_56")])],
        variables=[
            Variable(tag="led_cmd", data_type="bool", initial=False),
            Variable(tag="led_56", data_type="bool", initial=False),
        ],
        bindings=[Binding(tag="led_56", direction="output", address="56")],
    )


class Propeller2RuntimeTests(unittest.TestCase):
    def test_runtime_source_contains_upload_snapshot_and_active_low_led_output(self) -> None:
        source = build_runtime_source(build_propeller2_program(), scan_ms=25)

        self.assertIn(': PLC.HELLO ." PLC HELLO 1" CRLF ;', source)
        self.assertIn(': PLC.UPLOAD', source)
        self.assertIn(': PLC.SNAPSHOT', source)
        self.assertIn(": PLC.INIT", source)
        self.assertIn("25 $", source)
        self.assertIn("56 LOW ELSE 56 HIGH", source)

    def test_runtime_source_includes_timer_logic(self) -> None:
        program = Program(
            name="propeller2-ton",
            rungs=[Rung(comment="timer", elements=[Step("XIC", "start_pb"), Step("TON", "T1", arg=1000)])],
            variables=[
                Variable(tag="start_pb", data_type="bool", initial=False),
                Variable(tag="T1", data_type="timer", preset=1000),
            ],
            bindings=[Binding(tag="start_pb", direction="input", address="0")],
        )

        source = build_runtime_source(program)

        self.assertIn(": PLC.TON.0", source)
        self.assertIn("@ $12004 @ +", source)
        self.assertIn('." PLC TIMER 0 "', source)


if __name__ == "__main__":
    unittest.main()
