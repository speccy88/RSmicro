import unittest

from plc_ascii.engine import LadderEngine, trace_program_preview
from plc_ascii.model import Program, Rung, Step, Variable


def build_program() -> Program:
    return Program(
        name="test",
        rungs=[
            Rung(
                name="r1",
                conditions=[Step("XIC", "start"), Step("XIO", "stop")],
                actions=[Step("OTE", "motor")],
            ),
            Rung(
                name="r2",
                conditions=[Step("XIC", "motor")],
                actions=[Step("TON", "t1", 300)],
            ),
        ],
    )


class LadderEngineTests(unittest.TestCase):
    def test_output_logic(self) -> None:
        engine = LadderEngine(build_program())
        engine.set_tag("start", True)
        engine.set_tag("stop", False)
        result = engine.scan(100)
        self.assertTrue(result.tags["motor"])

    def test_timer_done_bit_sets_after_preset(self) -> None:
        engine = LadderEngine(build_program())
        engine.set_tag("start", True)
        engine.set_tag("stop", False)
        engine.scan(100)
        engine.scan(100)
        result = engine.scan(100)
        self.assertTrue(result.timers["t1"]["dn"])
        self.assertEqual(result.timers["t1"]["acc"], 300)
        self.assertEqual(result.timers["t1"]["pre"], 300)
        self.assertTrue(result.tags["t1.dn"])

    def test_timer_bits_can_drive_other_contacts(self) -> None:
        program = Program(
            name="timer-contact",
            rungs=[
                Rung(conditions=[Step("XIC", "start")], actions=[Step("TON", "timer1", 200)]),
                Rung(conditions=[Step("XIC", "timer1.dn")], actions=[Step("OTE", "done")]),
            ],
        )
        engine = LadderEngine(program)
        engine.set_tag("start", True)

        engine.scan(100)
        self.assertFalse(engine.tags.get("done", False))

        result = engine.scan(100)
        self.assertTrue(result.tags["timer1.dn"])
        self.assertTrue(result.tags["done"])

    def test_output_instructions_cannot_write_timer_members(self) -> None:
        with self.assertRaises(ValueError):
            Step("OTE", "timer1.dn").validate()

    def test_force_overrides_logic(self) -> None:
        engine = LadderEngine(build_program())
        engine.set_force("motor", False)
        engine.set_tag("start", True)
        engine.set_tag("stop", False)
        result = engine.scan(100)
        self.assertFalse(result.tags["motor"])

    def test_reset_runtime_clears_tags_and_optionally_forces(self) -> None:
        engine = LadderEngine(build_program())
        engine.set_tag("start", True)
        engine.set_force("motor", True)
        engine.scan(100)

        engine.reset_runtime(clear_forces=False)
        self.assertEqual(engine.tags.get("start"), None)
        self.assertIn("motor", engine.forced)

        engine.reset_runtime(clear_forces=True)
        self.assertNotIn("motor", engine.forced)

    def test_mov_and_cmp_support_integer_constants(self) -> None:
        program = Program(
            name="numeric",
            rungs=[
                Rung(conditions=[Step("XIC", "start")], actions=[Step("MOV", "count", params={"source": 5})]),
                Rung(
                    conditions=[Step("CMP", params={"left": "count", "right": 5, "cmp": "=="})],
                    actions=[Step("OTE", "done")],
                ),
            ],
        )
        engine = LadderEngine(program)
        engine.set_tag("start", True)

        result = engine.scan(100)

        self.assertEqual(result.tags["count"], 5)
        self.assertTrue(result.tags["done"])

    def test_numeric_instructions_support_float_math(self) -> None:
        program = Program(
            name="float-math",
            rungs=[
                Rung(
                    conditions=[Step("XIC", "start")],
                    actions=[
                        Step("MOV", "speed", params={"source": 5.0}),
                        Step("ADD", "sum", params={"left": "speed", "right": 2.5}),
                        Step("SUB", "delta", params={"left": "sum", "right": 1.0}),
                        Step("MUL", "scaled", params={"left": "delta", "right": 2}),
                        Step("DIV", "ratio", params={"left": "scaled", "right": 2}),
                        Step("NEG", "negated", params={"source": "ratio"}),
                        Step("ABS", "absolute", params={"source": "negated"}),
                    ],
                )
            ],
        )
        engine = LadderEngine(program)
        engine.set_tag("start", True)

        result = engine.scan(100)

        self.assertEqual(result.tags["speed"], 5.0)
        self.assertEqual(result.tags["sum"], 7.5)
        self.assertEqual(result.tags["delta"], 6.5)
        self.assertEqual(result.tags["scaled"], 13.0)
        self.assertEqual(result.tags["ratio"], 6.5)
        self.assertEqual(result.tags["negated"], -6.5)
        self.assertEqual(result.tags["absolute"], 6.5)

    def test_compare_shortcuts_drive_rung_power(self) -> None:
        program = Program(
            name="compare-shortcuts",
            rungs=[
                Rung(
                    conditions=[Step("GTE", params={"left": "temp", "right": 5.0})],
                    actions=[Step("OTE", "alarm")],
                ),
                Rung(
                    conditions=[Step("NE", params={"left": "temp", "right": 0})],
                    actions=[Step("OTE", "nonzero")],
                ),
            ],
        )
        engine = LadderEngine(program)
        engine.set_tag("temp", 5.0)

        result = engine.scan(100)

        self.assertTrue(result.tags["alarm"])
        self.assertTrue(result.tags["nonzero"])

    def test_numeric_write_instructions_cannot_write_timer_members(self) -> None:
        with self.assertRaises(ValueError):
            Step("MOV", "timer1.acc", params={"source": 5}).validate()

    def test_counter_counts_only_on_rising_edge(self) -> None:
        program = Program(
            name="counter",
            variables=[Variable(tag="counter1", data_type="counter", preset=2)],
            rungs=[Rung(conditions=[Step("XIC", "pulse")], actions=[Step("CTU", "counter1")])],
        )
        engine = LadderEngine(program)

        engine.set_tag("pulse", True)
        result = engine.scan(100)
        self.assertEqual(result.counters["counter1"]["acc"], 1)
        self.assertFalse(result.counters["counter1"]["dn"])

        result = engine.scan(100)
        self.assertEqual(result.counters["counter1"]["acc"], 1)

        engine.set_tag("pulse", False)
        engine.scan(100)
        engine.set_tag("pulse", True)
        result = engine.scan(100)
        self.assertEqual(result.counters["counter1"]["acc"], 2)
        self.assertTrue(result.counters["counter1"]["dn"])

    def test_ctu_instruction_validates(self) -> None:
        Step("CTU", "counter1").validate()

    def test_restore_initial_values_uses_program_variable_defaults(self) -> None:
        program = Program(
            name="monitor-defaults",
            variables=[
                Variable(tag="i1", data_type="int", initial=7),
                Variable(tag="f1", data_type="float", initial=2.5),
                Variable(tag="t1", data_type="timer", preset=1200),
                Variable(tag="c1", data_type="counter", preset=4),
            ],
            rungs=[],
        )
        engine = LadderEngine(program)
        engine.set_value("i1", 99)
        engine.set_value("f1", 9.5)
        engine.set_value("t1.acc", 800)
        engine.set_value("c1.acc", 3)

        engine.restore_initial_values()

        self.assertEqual(engine.read_tag("i1"), 7)
        self.assertEqual(engine.read_tag("f1"), 2.5)
        self.assertEqual(engine.read_tag("t1.pre"), 1200)
        self.assertEqual(engine.read_tag("t1.acc"), 0)
        self.assertEqual(engine.read_tag("c1.pre"), 4)
        self.assertEqual(engine.read_tag("c1.acc"), 0)

    def test_clear_boolean_values_preserves_numeric_values(self) -> None:
        program = Program(
            name="clear-bools",
            variables=[
                Variable(tag="x1", data_type="bool", initial=True),
                Variable(tag="y1", data_type="bool", initial=True),
                Variable(tag="n7", data_type="int", initial=12),
                Variable(tag="f8", data_type="float", initial=2.5),
            ],
            rungs=[],
        )
        engine = LadderEngine(program)
        engine.set_tag("x1", True)
        engine.set_tag("y1", True)
        engine.set_tag("n7", 99)
        engine.set_tag("f8", 7.25)

        engine.clear_boolean_values()

        self.assertFalse(engine.read_tag("x1"))
        self.assertFalse(engine.read_tag("y1"))
        self.assertEqual(engine.read_tag("n7"), 99)
        self.assertEqual(engine.read_tag("f8"), 7.25)

    def test_preview_trace_does_not_energize_output_from_forced_input(self) -> None:
        program = Program(
            name="preview-force",
            rungs=[Rung(elements=[Step("XIC", "x1"), Step("OTE", "y1")])],
        )

        rung_power, traces = trace_program_preview(program, {"x1": True, "y1": False}, forced={"x1": True})

        step_traces = traces[0]
        self.assertEqual(rung_power, [False])
        self.assertTrue(step_traces[0].truth)
        self.assertFalse(step_traces[0].power_out)
        self.assertFalse(step_traces[1].truth)

    def test_preview_trace_shows_forced_output_as_true(self) -> None:
        program = Program(
            name="preview-force-output",
            rungs=[Rung(elements=[Step("XIC", "x1"), Step("OTE", "y1")])],
        )

        _, traces = trace_program_preview(program, {"x1": False, "y1": True}, forced={"y1": True})

        self.assertTrue(traces[0][1].truth)

    def test_stop_offline_drops_ote_outputs_without_restoring_saved_values(self) -> None:
        program = Program(
            name="stop-outputs",
            variables=[
                Variable(tag="x1", data_type="bool", initial=False),
                Variable(tag="y1", data_type="bool", initial=True),
                Variable(tag="n7", data_type="int", initial=33),
            ],
            rungs=[Rung(elements=[Step("XIC", "x1"), Step("OTE", "y1")])],
        )
        engine = LadderEngine(program)
        engine.set_tag("x1", True)
        engine.scan(100)
        engine.set_tag("n7", 99)

        self.assertTrue(engine.read_tag("y1"))

        engine.stop_offline(reset_numeric=False, clear_forces=False)

        self.assertFalse(engine.read_tag("x1"))
        self.assertFalse(engine.read_tag("y1"))
        self.assertEqual(engine.read_tag("n7"), 99)

    def test_stop_offline_clears_forces_on_second_stop(self) -> None:
        program = Program(
            name="stop-clear-forces",
            variables=[
                Variable(tag="x1", data_type="bool", initial=False),
                Variable(tag="n7", data_type="int", initial=0),
            ],
            rungs=[],
        )
        engine = LadderEngine(program)
        engine.set_force("x1", True)
        engine.set_force("n7", 12)

        engine.stop_offline(reset_numeric=False, clear_forces=True)

        self.assertFalse(engine.read_tag("x1"))
        self.assertEqual(engine.read_tag("n7"), 12)
        self.assertEqual(engine.forced, {})

    def test_forced_coil_stays_true_in_scan_trace_even_with_false_rung(self) -> None:
        program = Program(
            name="forced-coil-trace",
            variables=[
                Variable(tag="x1", data_type="bool", initial=False),
                Variable(tag="y1", data_type="bool", initial=False),
            ],
            rungs=[Rung(elements=[Step("XIC", "x1"), Step("OTE", "y1")])],
        )
        engine = LadderEngine(program)
        engine.set_force("y1", True)

        result = engine.scan(100)

        self.assertFalse(result.rung_power[0])
        self.assertTrue(result.tags["y1"])
        self.assertTrue(result.traces[0][1].truth)
        self.assertFalse(result.traces[0][1].power_out)


if __name__ == "__main__":
    unittest.main()
