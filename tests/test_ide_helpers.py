import unittest

from plc_ascii.ide import first_step_path, normalize_nodes, offline_live_locked, populate_program_variables
from plc_ascii.model import Branch, Program, Rung, Step, Variable


class IdeHelperTests(unittest.TestCase):
    def test_offline_live_locked_only_when_running_or_stepped(self) -> None:
        self.assertTrue(offline_live_locked("offline", "running"))
        self.assertTrue(offline_live_locked("offline", "stepped"))
        self.assertFalse(offline_live_locked("offline", "stopped"))
        self.assertFalse(offline_live_locked("online", "running"))

    def test_first_step_path_finds_first_nested_instruction(self) -> None:
        nodes = [
            Branch(
                lanes=[
                    [Step("XIC", "a")],
                    [Step("XIC", "b")],
                ]
            ),
            Step("OTE", "out"),
        ]

        self.assertEqual(first_step_path(nodes), (0, 0, 0))

    def test_normalize_nodes_preserves_multi_lane_branch(self) -> None:
        nodes = [
            Branch(
                lanes=[
                    [Step("XIC", "a")],
                    [Step("XIC", "b")],
                ]
            )
        ]

        normalized = normalize_nodes(nodes)

        self.assertEqual(len(normalized), 1)
        self.assertIsInstance(normalized[0], Branch)
        self.assertEqual(len(normalized[0].lanes), 2)

    def test_populate_program_variables_infers_boolean_and_integer_tags(self) -> None:
        program = Program(
            name="monitor-infer",
            rungs=[
                Rung(elements=[Step("XIC", "a"), Step("XIO", "b"), Step("OTE", "c")]),
                Rung(elements=[Step("ADD", "sum", params={"left": "a_int", "right": "b_int"})]),
            ],
        )

        populate_program_variables(program)

        variables = {variable.tag: variable for variable in program.variables}
        self.assertEqual(variables["a"].data_type, "bool")
        self.assertEqual(variables["b"].data_type, "bool")
        self.assertEqual(variables["c"].data_type, "bool")
        self.assertEqual(variables["sum"].data_type, "int")
        self.assertEqual(variables["a_int"].data_type, "int")
        self.assertEqual(variables["b_int"].data_type, "int")

    def test_populate_program_variables_preserves_current_scalar_values_for_save(self) -> None:
        program = Program(
            name="monitor-save",
            variables=[Variable(tag="count", data_type="int", initial=0)],
            rungs=[Rung(elements=[Step("OTE", "motor")])],
        )

        populate_program_variables(program, current_values={"count": 12, "motor": True})

        variables = {variable.tag: variable for variable in program.variables}
        self.assertEqual(variables["count"].initial, 12)
        self.assertTrue(variables["motor"].initial)


if __name__ == "__main__":
    unittest.main()
