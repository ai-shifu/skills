from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills/ai-shifu-course-creator/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
if "dotenv" not in sys.modules:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda **_kwargs: None
    dotenv.set_key = lambda *_args, **_kwargs: None
    dotenv.dotenv_values = lambda *_args, **_kwargs: {}
    sys.modules["dotenv"] = dotenv
spec = importlib.util.spec_from_file_location("course_reorder_cli", SCRIPT_DIR / "shifu-cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class CourseReorderTests(unittest.TestCase):
    def setUp(self):
        # GET /shifus/<bid>/outlines returns SimpleOutlineDto nodes with bid,
        # name and children. PATCH uses ReorderOutlineDto: {outlines: [...]},
        # whose recursive ReorderOutlineItemDto contains only bid and children.
        self.tree = [
            {"bid": "chapter-a", "name": "First chapter", "children": [
                {"bid": "lesson-a", "name": "First lesson", "children": [
                    {"bid": "nested", "name": "Nested", "children": []},
                ]},
                {"bid": "lesson-b", "name": "Second lesson", "children": []},
            ]},
            {"bid": "chapter-b", "name": "Second chapter", "children": [
                {"bid": "lesson-c", "name": "Other lesson", "children": []},
            ]},
        ]
        self.payload = [
            {"bid": "chapter-a", "children": [
                {"bid": "lesson-a", "children": [{"bid": "nested", "children": []}]},
                {"bid": "lesson-b", "children": []},
            ]},
            {"bid": "chapter-b", "children": [{"bid": "lesson-c", "children": []}]},
        ]
        self.auth = self.enterContext(mock.patch.object(cli, "resolve_auth", return_value=(
            "https://app.ai-shifu.com", "test-token",
        )))
        self.api = self.enterContext(mock.patch.object(cli, "api", side_effect=[self.tree, True]))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.stderr = self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def run_reorder(self, order):
        cli.cmd_reorder(types.SimpleNamespace(shifu_bid="course", order=order))

    def assert_payload(self, outlines):
        self.assertEqual(self.api.call_args_list, [
            mock.call("https://app.ai-shifu.com", "test-token", "get", "/shifus/course/outlines"),
            mock.call("https://app.ai-shifu.com", "test-token", "patch",
                      "/shifus/course/outlines/reorder", json={"outlines": outlines}),
        ])

    def test_reorders_chapters_with_complete_backend_tree_payload(self):
        self.run_reorder("chapter-b,chapter-a")
        self.assert_payload(list(reversed(self.payload)))

    def test_reorders_lessons_preserving_other_chapters_and_descendants(self):
        original = copy.deepcopy(self.tree)
        self.run_reorder(" lesson-b , lesson-a ")
        self.payload[0]["children"].reverse()
        self.assert_payload(self.payload)
        self.assertEqual(self.tree, original)

    def test_single_sibling_preserves_the_complete_tree(self):
        self.run_reorder("lesson-c")
        self.assert_payload(self.payload)

    def test_null_and_missing_children_are_empty_without_changing_source(self):
        self.tree[0]["children"][0]["children"][0]["children"] = None
        del self.tree[0]["children"][1]["children"]
        self.tree[1]["children"] = None
        original = copy.deepcopy(self.tree)
        self.run_reorder("lesson-b,lesson-a")
        self.payload[0]["children"].reverse()
        self.payload[1]["children"] = []
        self.assert_payload(self.payload)
        self.assertEqual(self.tree, original)

    def test_empty_and_duplicate_ids_fail_before_network_access(self):
        for order in ("", " ", ",", "lesson-a,", "lesson-a,,lesson-b", "lesson-a,lesson-a"):
            with self.subTest(order=order), self.assertRaises(SystemExit) as raised:
                self.run_reorder(order)
            self.assertEqual(raised.exception.code, 1)
        self.api.assert_not_called()
        self.auth.assert_not_called()

    def test_unknown_cross_parent_and_incomplete_orders_never_write(self):
        for order, message in (
            ("missing", "Unknown outline BIDs"),
            ("lesson-a,lesson-c", "same parent"),
            ("chapter-a,lesson-a", "same parent"),
            ("lesson-a", "every outline"),
            ("chapter-a", "every outline"),
        ):
            with self.subTest(order=order):
                self.api.reset_mock(side_effect=True)
                self.api.return_value = self.tree
                with self.assertRaises(SystemExit) as raised:
                    self.run_reorder(order)
                self.assertEqual(raised.exception.code, 1)
                self.assertEqual(self.api.call_count, 1)
                self.assertIn(message, self.stderr.getvalue())

    def test_malformed_platform_trees_never_write(self):
        for tree in (
            None, {}, [], [None], [{}], [{"bid": 12}],
            [{"bid": "chapter-a", "children": {}}],
            [{"bid": "chapter-a", "children": False}],
            [{"bid": "chapter-a", "children": 0}],
            [{"bid": "chapter-a", "children": ""}],
            [{"bid": "chapter-a", "children": "invalid"}],
            [{"bid": "chapter-a", "children": [{"bid": "chapter-a"}]}],
            [{"bid": "chapter-a"}, {"bid": "chapter-a"}],
        ):
            with self.subTest(tree=tree):
                self.api.reset_mock(side_effect=True)
                self.api.return_value = tree
                with self.assertRaises(SystemExit) as raised:
                    self.run_reorder("chapter-a")
                self.assertEqual(raised.exception.code, 1)
                self.assertEqual(self.api.call_count, 1)

    def test_failed_outline_read_never_writes(self):
        self.api.side_effect = SystemExit(1)
        with self.assertRaises(SystemExit):
            self.run_reorder("chapter-b,chapter-a")
        self.assertEqual(self.api.call_count, 1)


if __name__ == "__main__":
    unittest.main()
