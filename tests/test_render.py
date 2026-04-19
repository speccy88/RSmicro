import unittest

from plc_ascii.engine import trace_program_state
from plc_ascii.model import Program, Rung, Step
from plc_ascii.render import LadderRenderer, ROLE_ELEMENT_OFF, ROLE_ELEMENT_ON, render_program


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

    def test_forced_contact_is_marked_in_render(self) -> None:
        program = Program(
            name="forced-render",
            rungs=[Rung(conditions=[Step("XIC", "x1")], actions=[Step("OTE", "y1")])],
        )
        rendered = render_program(program, forced_tags={"x1"})
        self.assertIn("[f x1]", rendered)

    def test_numeric_instructions_render_in_ascii_view(self) -> None:
        program = Program(
            name="numeric-render",
            rungs=[
                Rung(
                    comment="Math rung",
                    conditions=[Step("CMP", params={"left": "count", "right": 5, "cmp": ">="})],
                    actions=[
                        Step("MOV", "dest", params={"source": 5}),
                        Step("ADD", "sum", params={"left": "dest", "right": 2}),
                    ],
                )
            ],
        )

        rendered = render_program(program)

        self.assertIn("[CMP count >= 5]", rendered)
        self.assertIn("[MOV 5 -> dest]", rendered)
        self.assertIn("[ADD dest 2 -> sum]", rendered)

    def test_counter_instruction_renders(self) -> None:
        program = Program(
            name="counter-render",
            rungs=[Rung(conditions=[Step("XIC", "pulse")], actions=[Step("CTU", "counter1")])],
        )

        rendered = render_program(program)

        self.assertIn("[CTU counter1 pre:0 acc:0]", rendered)

    def test_done_counter_renders_as_on_role(self) -> None:
        program = Program(
            name="counter-done",
            rungs=[Rung(conditions=[Step("XIC", "pulse")], actions=[Step("CTU", "counter1")])],
        )

        document = LadderRenderer(
            program,
            counter_values={"counter1": {"pre": 10, "acc": 10, "dn": True}},
        ).render()
        counter_text = "[CTU counter1 pre:10 acc:10]"
        line_index = next(index for index, line in enumerate(document.lines) if counter_text in line)
        start = document.lines[line_index].index(counter_text)
        end = start + len(counter_text)

        self.assertTrue(
            any(
                span.tag == ROLE_ELEMENT_ON and span.line == line_index and span.start <= start and span.end >= end
                for span in document.role_spans
            )
        )

    def test_not_done_counter_renders_as_off_role(self) -> None:
        program = Program(
            name="counter-not-done",
            rungs=[Rung(conditions=[Step("XIC", "pulse")], actions=[Step("CTD", "counter1")])],
        )

        document = LadderRenderer(
            program,
            counter_values={"counter1": {"pre": 10, "acc": 3, "dn": False}},
        ).render()
        counter_text = "[CTD counter1 pre:10 acc:3]"
        line_index = next(index for index, line in enumerate(document.lines) if counter_text in line)
        start = document.lines[line_index].index(counter_text)
        end = start + len(counter_text)

        self.assertTrue(
            any(
                span.tag == ROLE_ELEMENT_OFF and span.line == line_index and span.start <= start and span.end >= end
                for span in document.role_spans
            )
        )


if __name__ == "__main__":
    unittest.main()
