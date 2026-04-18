import unittest

from plc_ascii.ide import first_step_path, normalize_nodes
from plc_ascii.model import Branch, Step


class IdeHelperTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
