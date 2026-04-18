import unittest

from plc_ascii.engine import LadderEngine
from plc_ascii.model import Program, Rung, Step


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


if __name__ == "__main__":
    unittest.main()
