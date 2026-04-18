import unittest

from plc_ascii.engine import trace_program_state
from plc_ascii.model import Program, Rung, Step
from plc_ascii.render import render_program


class RenderTests(unittest.TestCase):
    def test_render_uses_numbered_rungs_and_no_name_header(self) -> None:
        program = Program(
            name="render",
            rungs=[Rung(comment="Start rung", conditions=[Step("XIC", "start")], actions=[Step("OTE", "motor")])],
        )
        _, traces = trace_program_state(program, {"start": True})
        rendered = render_program(program, traces=traces)
        self.assertIn("Start rung", rendered)
        self.assertIn("001 | --[ start ]--------( motor )-- |", rendered)
        self.assertNotIn("[ON ]", rendered)

    def test_timer_member_contact_is_allowed(self) -> None:
        step = Step("XIC", "timer1.dn")
        step.validate()
        self.assertEqual(step.tag, "timer1.dn")

    def test_ton_renders_preset_when_not_running(self) -> None:
        program = Program(
            name="timer-render",
            rungs=[Rung(conditions=[Step("XIC", "start")], actions=[Step("TON", "timer1", 10000)])],
        )
        rendered = render_program(program)
        self.assertIn("[TON timer1 pre:10000ms]", rendered)

    def test_ton_renders_accumulator_when_running(self) -> None:
        program = Program(
            name="timer-render",
            rungs=[Rung(conditions=[Step("XIC", "start")], actions=[Step("TON", "timer1", 10000)])],
        )
        _, traces = trace_program_state(program, {"start": True})
        rendered = render_program(program, traces=traces, timer_values={"timer1": {"acc": 250, "pre": 10000, "en": True, "dn": False, "tt": True}})
        self.assertIn("[TON timer1 acc:00250ms]", rendered)


if __name__ == "__main__":
    unittest.main()
