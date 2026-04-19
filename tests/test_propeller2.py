import unittest
from unittest.mock import patch

from plc_ascii.model import Binding, Program, Rung, Step, Variable
from plc_runtime.propeller2 import DEFAULT_BAUDRATE, Propeller2Transport, build_runtime_source, propeller2_baud_candidates


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
    def test_propeller2_baud_candidates_prefer_requested_value_then_known_fallbacks(self) -> None:
        self.assertEqual(propeller2_baud_candidates(115200), [115200, DEFAULT_BAUDRATE])
        self.assertEqual(propeller2_baud_candidates(DEFAULT_BAUDRATE), [DEFAULT_BAUDRATE, 115200])

    def test_runtime_source_contains_upload_snapshot_runner_and_active_low_led_output(self) -> None:
        source = build_runtime_source(build_propeller2_program(), scan_ms=25)

        self.assertIn(': PLC.HELLO ." PLC HELLO 2" CRLF ;', source)
        self.assertIn("128 bytes PLCHOSTBUF", source)
        self.assertIn("VAR PLCHOSTLEN", source)
        self.assertIn("VAR PLCDATA0", source)
        self.assertIn(': PLC.UPLOAD', source)
        self.assertIn(': PLC.SNAPSHOT', source)
        self.assertIn(": PLC.HOST", source)
        self.assertIn(": PLC.HOST.CMD.SNAPSHOT", source)
        self.assertIn(": PLC.INIT", source)
        self.assertIn(": PLC.RUNNER", source)
        self.assertIn(": PLC.START.COG", source)
        self.assertIn("5 ms", source)
        self.assertIn(": PLC.RESTORE.RUNTIME", source)
        self.assertIn(": PLC.FORCE.SET.0", source)
        self.assertIn(": PLC.FORCE.CLEAR.0", source)
        self.assertEqual(source.count(": PLC.START.RUNTIME"), 1)
        self.assertIn("25 PLCDATA1 !", source)
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
        self.assertIn("PLCDATA6 @ PLCDATA1 @ +", source)
        self.assertIn('." PLC TIMER 0 "', source)

    def test_runtime_source_includes_counter_and_timer_setters(self) -> None:
        program = Program(
            name="propeller2-setters",
            rungs=[
                Rung(comment="counter", elements=[Step("XIC", "pulse"), Step("CTU", "C1", arg=5)]),
                Rung(comment="timer", elements=[Step("XIC", "pulse"), Step("TON", "T1", arg=100)]),
            ],
            variables=[
                Variable(tag="pulse", data_type="bool", initial=False),
                Variable(tag="C1", data_type="counter", preset=5),
                Variable(tag="T1", data_type="timer", preset=100),
            ],
            bindings=[],
        )

        source = build_runtime_source(program)

        self.assertIn(": PLC.SET.COUNTER.ACC.0", source)
        self.assertIn(": PLC.SET.COUNTER.PRE.0", source)
        self.assertIn(": PLC.SET.TIMER.ACC.0", source)
        self.assertIn(": PLC.SET.TIMER.PRE.0", source)
        self.assertIn('." PLC COUNTER 0 "', source)
        self.assertIn("@ . SPACE", source)

    def test_transport_keeps_the_detected_working_baudrate(self) -> None:
        with patch("plc_runtime.propeller2.transport.open_taqoz_console", return_value=(object(), object(), DEFAULT_BAUDRATE)):
            transport = Propeller2Transport(port="/dev/null", baudrate=115200)
        self.assertEqual(transport.baudrate, DEFAULT_BAUDRATE)

    def test_prompt_snapshot_reports_forced_scalar_tags(self) -> None:
        with patch("plc_runtime.propeller2.transport.open_taqoz_console", return_value=(object(), object(), DEFAULT_BAUDRATE)):
            transport = Propeller2Transport(port="/dev/null", baudrate=DEFAULT_BAUDRATE)
        transport._set_program_cache(build_propeller2_program())
        snapshot = transport._parse_snapshot(
            [
                "PLC MODE 1",
                "PLC VAR 0 0",
                "PLC VAR 1 1",
                "PLC FORCE 1 1",
            ]
        )
        self.assertEqual(snapshot["mode"], "run")
        self.assertEqual(snapshot["forced"], {"led_56": True})
        self.assertEqual(snapshot["tags"]["led_56"], True)


if __name__ == "__main__":
    unittest.main()
