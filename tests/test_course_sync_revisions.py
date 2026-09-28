"""Regression tests against the platform's separate content/revision contract."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills/ai-shifu-course-creator/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location("sync_revision_cli", SCRIPT_DIR / "shifu-cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

BASE = "https://app.ai-shifu.com"
TREE = [{"bid": "chapter", "name": "Chapter", "children": [
    {"bid": "lesson", "name": "Lesson", "children": []},
]}]


class CourseSyncRevisionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.output = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.errors = self.enterContext(contextlib.redirect_stderr(io.StringIO()))
        self.enterContext(mock.patch.object(cli, "resolve_auth", return_value=(BASE, "test-token")))
        self.api = self.enterContext(mock.patch.object(cli, "api", side_effect=self.platform))
        self.safe = self.enterContext(mock.patch.object(cli, "api_safe", return_value={"revision": 8}))
        self.post = self.enterContext(mock.patch.object(cli, "api_conflict_aware", return_value=("ok", {"new_revision": 12})))

    def platform(self, base, token, method, path, **kwargs):
        if path.endswith("/detail"):
            return {"name": "Course", "description": "", "system_prompt": "Course prompt"}
        if path.endswith("/outlines"):
            return TREE
        if path.endswith("/draft-meta?outline_bid=lesson"):
            return {"revision": 10}
        if path.endswith("/mdflow/history/10"):
            return {"version_id": 10, "content": "Content at revision 10"}
        # The live mdflow GET returns only text; it must not be used for a
        # versioned snapshot, even if the cloud advances between these reads.
        if path.endswith("/mdflow"):
            return "Concurrent content at revision 11"
        self.fail(f"Unexpected request: {method} {path}")

    def pull(self):
        return cli._pull_into_dir(BASE, "test-token", "course", self.root)

    def args(self, course_dir=True):
        return types.SimpleNamespace(shifu_bid="course", outline_bid="lesson",
            teaching_prompt_file=str(self.root / "lessons/lesson-01.md"),
            course_dir=str(self.root) if course_dir else None, exit_code=True)

    def save_manifest(self, manifest):
        (self.root / ".shifu-sync.json").write_text(json.dumps(manifest))

    def test_pull_pairs_immutable_content_and_revision_then_push_uses_baseline(self):
        manifest = self.pull()
        lesson = next(x for x in manifest["lessons"] if not x["is_chapter"])
        self.assertEqual(lesson["revision"], 10)
        path = self.root / lesson["file"]
        self.assertEqual(path.read_text(), "Content at revision 10")
        self.assertEqual(lesson["content_sha256"], cli._sha256_text(path.read_text()))
        self.assertFalse(any(c.args[3].endswith("/mdflow") for c in self.api.call_args_list))
        path.write_text("My edit")
        cli.cmd_update_lesson(self.args())
        self.assertEqual(self.post.call_args.kwargs["json"], {"data": "My edit", "base_revision": 10})
        after = json.loads((self.root / ".shifu-sync.json").read_text())
        self.assertEqual(next(x for x in after["lessons"] if not x["is_chapter"])["revision"], 12)

    def test_failed_snapshot_preserves_existing_content_and_manifest(self):
        self.pull()
        local = self.root / "lessons/lesson-01.md"
        local.write_text("Unsaved local edit")
        original = (self.root / ".shifu-sync.json").read_bytes()
        real = self.platform
        def malformed(*args, **kwargs):
            if args[3].endswith("/mdflow/history/10"):
                return {"version_id": 11, "content": "Wrong revision"}
            return real(*args, **kwargs)
        self.api.side_effect = malformed
        with self.assertRaises(SystemExit) as caught:
            self.pull()
        self.assertEqual(caught.exception.code, 1)
        self.assertEqual(local.read_text(), "Unsaved local edit")
        self.assertEqual((self.root / ".shifu-sync.json").read_bytes(), original)

    def test_old_manifest_with_no_lesson_revision_refuses_to_push(self):
        manifest = self.pull()
        manifest["lessons"][-1]["revision"] = None
        self.save_manifest(manifest)
        local = self.root / "lessons/lesson-01.md"
        local.write_text("Keep this unsaved edit")
        self.api.reset_mock()
        with self.assertRaises(SystemExit) as caught:
            cli.cmd_update_lesson(self.args())
        self.assertEqual(caught.exception.code, 1)
        self.post.assert_not_called()
        self.api.assert_not_called()
        self.assertEqual(local.read_text(), "Keep this unsaved edit")
        self.assertIn("reapply your edits", self.errors.getvalue())

    def test_later_snapshot_failure_preserves_all_existing_files(self):
        tree = [{"bid": "chapter", "name": "Chapter", "children": [
            {"bid": "lesson", "name": "Lesson", "children": []},
            {"bid": "second", "name": "Second lesson", "children": []},
        ]}]

        def two_lessons(*args, **kwargs):
            path = args[3]
            if path.endswith("/outlines"):
                return tree
            if path.endswith("/draft-meta?outline_bid=second"):
                return {"revision": 20}
            if path.endswith("/second/mdflow/history/20"):
                return {"version_id": 20, "content": "Second lesson content"}
            return self.platform(*args, **kwargs)

        self.api.side_effect = two_lessons
        self.pull()
        (self.root / "lessons/lesson-01.md").write_text("First unsaved edit")
        (self.root / "lessons/lesson-02.md").write_text("Second unsaved edit")
        original = {path.relative_to(self.root): path.read_bytes()
                    for path in self.root.rglob("*") if path.is_file()}

        def fail_second(*args, **kwargs):
            if args[3].endswith("/second/mdflow/history/20"):
                return {"version_id": 21, "content": "Mismatched snapshot"}
            return two_lessons(*args, **kwargs)

        self.api.side_effect = fail_second
        with self.assertRaises(SystemExit) as caught:
            self.pull()
        self.assertEqual(caught.exception.code, 1)
        after = {path.relative_to(self.root): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(after, original)

    def test_standalone_update_reads_revision_from_metadata(self):
        self.pull()
        self.api.reset_mock()
        cli.cmd_update_lesson(self.args(course_dir=False))
        self.api.assert_called_once_with(BASE, "test-token", "get", "/shifus/course/draft-meta?outline_bid=lesson")
        self.assertEqual(self.post.call_args.kwargs["json"]["base_revision"], 10)

    def test_missing_metadata_never_results_in_unversioned_write(self):
        self.pull()
        for metadata in ({}, None, {"revision": "10"}, {"revision": True}, {"revision": 0}):
            with self.subTest(metadata=metadata):
                self.api.side_effect = None
                self.api.return_value = metadata
                with self.assertRaises(SystemExit):
                    cli.cmd_update_lesson(self.args(course_dir=False))
                self.post.assert_not_called()

    def test_status_detects_remote_lesson_change_after_pull(self):
        self.pull()
        self.safe.side_effect = lambda *a, **kw: {"revision": 11 if "outline_bid" in a[3] else 8}
        with self.assertRaises(SystemExit) as caught:
            cli.cmd_status(self.args())
        self.assertEqual(caught.exception.code, 1)
        self.assertIn("local rev 10 < cloud 11", self.output.getvalue())
        self.assertIn("Up to date: 0 lessons", self.output.getvalue())

    def test_status_marks_missing_local_or_remote_lesson_revision_unknown(self):
        for missing_local in (True, False):
            with self.subTest(missing_local=missing_local):
                self.safe.side_effect = None
                self.safe.return_value = {"revision": 8}
                manifest = self.pull()
                if missing_local:
                    manifest["lessons"][-1]["revision"] = None
                    self.save_manifest(manifest)
                else:
                    self.safe.side_effect = lambda *a, **kw: None if "outline_bid" in a[3] else {"revision": 8}
                self.output.truncate(0)
                self.output.seek(0)
                with self.assertRaises(SystemExit) as caught:
                    cli.cmd_status(self.args())
                self.assertEqual(caught.exception.code, 1)
                self.assertIn("Unknown lesson revisions", self.output.getvalue())
                self.assertIn("Up to date: 0 lessons", self.output.getvalue())

    def test_status_treats_invalid_course_and_lesson_revisions_as_unknown(self):
        for scope in ("course", "lesson"):
            for location in ("local", "cloud"):
                for invalid in (None, 0, -1, True, False, "10", 10.0):
                    with self.subTest(scope=scope, location=location, revision=invalid):
                        self.safe.side_effect = None
                        self.safe.return_value = {"revision": 8}
                        manifest = self.pull()
                        if location == "local":
                            entry = manifest["course"] if scope == "course" else manifest["lessons"][-1]
                            entry["revision"] = invalid
                            self.save_manifest(manifest)

                        def metadata(*args, **kwargs):
                            is_lesson = "outline_bid" in args[3]
                            revision = 10 if is_lesson else 8
                            if location == "cloud" and is_lesson == (scope == "lesson"):
                                revision = invalid
                            return {"revision": revision}

                        self.safe.side_effect = metadata
                        self.output.truncate(0)
                        self.output.seek(0)
                        with self.assertRaises(SystemExit) as caught:
                            cli.cmd_status(self.args())
                        self.assertEqual(caught.exception.code, 1)
                        if scope == "lesson":
                            self.assertIn("Unknown lesson revisions", self.output.getvalue())
                            self.assertIn("Up to date: 0 lessons", self.output.getvalue())
                        else:
                            self.assertIn("Course meta: unknown", self.output.getvalue())
                            self.assertNotIn("Course meta: up to date", self.output.getvalue())

    def test_server_conflict_keeps_recorded_baseline_for_recovery(self):
        self.pull()
        self.post.return_value = ("conflict", {"revision": 11})
        with mock.patch.object(cli, "_auto_pull_overwrite") as recover:
            with self.assertRaises(SystemExit) as caught:
                cli.cmd_update_lesson(self.args())
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(self.post.call_args.kwargs["json"]["base_revision"], 10)
        self.assertEqual(recover.call_args.kwargs["scope"], "lesson")


if __name__ == "__main__":
    unittest.main()
