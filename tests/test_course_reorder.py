from __future__ import annotations

import contextlib
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
        self.auth = self.enterContext(mock.patch.object(cli, "resolve_auth", return_value=(
            "https://app.ai-shifu.com", "test-token",
        )))
        self.response = mock.Mock(ok=True)
        self.response.json.return_value = {"code": 0, "data": True}
        self.patch = self.enterContext(mock.patch.object(cli.requests, "patch", return_value=self.response))
        self.get = self.enterContext(mock.patch.object(cli.requests, "get", side_effect=AssertionError(
            "Reorder must not fetch and resubmit a stale tree",
        )))
        self.output = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.stderr = self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def run_reorder(self, order):
        cli.cmd_reorder(types.SimpleNamespace(shifu_bid="course", order=order))

    def assert_order_request(self, bids):
        self.patch.assert_called_once_with(
            "https://app.ai-shifu.com/api/shifu/shifus/course/outlines/reorder",
            headers={"Cookie": "token=test-token", "Content-Type": "application/json"},
            json={"order": bids}, timeout=30,
        )
        self.get.assert_not_called()

    def test_chapter_order_sends_only_selected_bids(self):
        self.run_reorder("chapter-b,chapter-a")
        self.assert_order_request(["chapter-b", "chapter-a"])
        self.assertIn("Reordered 2 outlines", self.output.getvalue())

    def test_lesson_order_trims_whitespace_without_sending_other_groups(self):
        self.run_reorder(" lesson-b , lesson-a ")
        self.assert_order_request(["lesson-b", "lesson-a"])

    def test_single_sibling_uses_the_same_atomic_contract(self):
        self.run_reorder("lesson-c")
        self.assert_order_request(["lesson-c"])

    def test_empty_and_duplicate_ids_fail_before_network_access(self):
        for order in ("", " ", ",", "lesson-a,", "lesson-a,,lesson-b", "lesson-a,lesson-a"):
            with self.subTest(order=order), self.assertRaises(SystemExit) as raised:
                self.run_reorder(order)
            self.assertEqual(raised.exception.code, 1)
        self.patch.assert_not_called()
        self.get.assert_not_called()
        self.auth.assert_not_called()

    def test_old_server_rejection_never_retries_with_a_full_tree(self):
        self.response.json.return_value = {"code": 1000, "message": "Missing parameter: outlines"}
        with self.assertRaises(SystemExit) as raised:
            self.run_reorder("chapter-b,chapter-a")
        self.assertEqual(raised.exception.code, 1)
        self.assert_order_request(["chapter-b", "chapter-a"])
        self.assertNotIn("Reordered", self.output.getvalue())

    def test_server_validation_failure_is_reported_without_fallback(self):
        for order in ("missing", "lesson-a,lesson-c", "lesson-a"):
            with self.subTest(order=order):
                self.patch.reset_mock()
                self.response.json.return_value = {"code": 1000, "message": "Invalid order"}
                with self.assertRaises(SystemExit) as raised:
                    self.run_reorder(order)
                self.assertEqual(raised.exception.code, 1)
                self.assert_order_request(order.split(","))
        self.assertNotIn("Reordered", self.output.getvalue())

    def test_http_failure_is_reported_without_fallback(self):
        self.response.ok = False
        self.response.status_code = 404
        self.response.text = "Not found"
        with self.assertRaises(SystemExit) as raised:
            self.run_reorder("lesson-b,lesson-a")
        self.assertEqual(raised.exception.code, 1)
        self.assert_order_request(["lesson-b", "lesson-a"])
        self.assertNotIn("Reordered", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
