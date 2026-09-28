from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_course_creator_cli import course_creator_cli as cli


class CourseImportPromptTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        # Platform export shape observed during the US-site smoke test, with
        # synthetic identifiers and content. It deliberately has no course_prompt.
        fixture = Path(__file__).parent / "fixtures" / "course-platform-export.json"
        self.data = json.loads(fixture.read_text(encoding="utf-8"))
        self.saved_prompt = "Existing Course Prompt"
        self.detail_payloads = []
        self.outline_payloads = []
        self.lesson_contents = []
        self.api = self.enterContext(mock.patch.object(cli, "api", side_effect=self.request))
        self.api_safe = self.enterContext(mock.patch.object(cli, "api_safe", side_effect=self.safe_request))
        self.enterContext(mock.patch.object(cli.time, "sleep"))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.errors = self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def request(self, base_url, token, method, path, **kwargs):
        if method == "put" and path == "/shifus":
            self.saved_prompt = "Platform default"
            return {"bid": "new-course"}
        if method == "put" and path.endswith("/outlines"):
            self.outline_payloads.append(kwargs["json"])
            return {"bid": f"new-outline-{len(self.outline_payloads)}"}
        if method == "post" and path.endswith("/mdflow"):
            self.lesson_contents.append(kwargs["json"]["data"])
            return {}
        self.fail(f"Unexpected request: {method} {path}")

    def safe_request(self, base_url, token, method, path, **kwargs):
        if method == "post" and path.endswith("/detail"):
            payload = kwargs["json"]
            self.detail_payloads.append(payload)
            self.saved_prompt = payload.get("system_prompt", self.saved_prompt)
            return {}
        if method == "get" and path.endswith("/outlines"):
            return []
        self.fail(f"Unexpected safe request: {method} {path}")

    def import_data(self, shifu_bid="existing-course"):
        path = self.root / "course.json"
        path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        return cli._import_flat("https://app.ai-shifu.com", "test-token", path, shifu_bid)

    def test_platform_export_preserves_course_prompt_and_lesson_content(self):
        for shifu_bid in ("existing-course", None):
            with self.subTest(shifu_bid=shifu_bid):
                self.outline_payloads.clear()
                self.lesson_contents.clear()
                actual_bid = self.import_data(shifu_bid)
                self.assertEqual(actual_bid, shifu_bid or "new-course")
                self.assertEqual(self.saved_prompt, self.data["shifu"]["llm_system_prompt"])
                self.assertEqual(self.detail_payloads[-1]["name"], self.data["shifu"]["title"])
                self.assertEqual(self.lesson_contents, [self.data["outline_items"][1]["content"]])
                self.assertEqual(self.outline_payloads[1]["parent_bid"], "new-outline-1")

    def test_build_output_still_imports_course_prompt(self):
        lessons = self.root / "lessons"
        lessons.mkdir()
        (lessons / "lesson-01.md").write_text("Lesson content\n", encoding="utf-8")
        (self.root / "course-prompt.md").write_text("Builder Course Prompt", encoding="utf-8")
        built_path = cli._build_import_json(str(self.root), title="Built course")
        self.data = json.loads(Path(built_path).read_text(encoding="utf-8"))
        self.import_data()
        self.assertEqual(self.saved_prompt, "Builder Course Prompt")
        self.assertEqual(self.lesson_contents, ["Lesson content\n"])

    def test_missing_prompt_preserves_existing_or_new_default(self):
        self.data["shifu"].pop("llm_system_prompt")
        self.import_data()
        self.assertEqual(self.saved_prompt, "Existing Course Prompt")
        self.assertNotIn("system_prompt", self.detail_payloads[-1])
        self.import_data(None)
        self.assertEqual(self.saved_prompt, "Platform default")
        self.assertNotIn("system_prompt", self.detail_payloads[-1])

    def test_explicit_empty_prompt_clears_for_either_schema(self):
        self.data["shifu"].pop("llm_system_prompt")
        for key in ("course_prompt", "llm_system_prompt"):
            with self.subTest(key=key):
                self.saved_prompt = "Existing Course Prompt"
                self.data["shifu"][key] = ""
                self.import_data()
                self.assertEqual(self.saved_prompt, "")
                self.assertEqual(self.detail_payloads[-1]["system_prompt"], "")
                del self.data["shifu"][key]

    def test_builder_key_takes_precedence_even_when_explicitly_empty(self):
        for preferred in ("Preferred Course Prompt", ""):
            with self.subTest(preferred=preferred):
                self.data["shifu"]["course_prompt"] = preferred
                self.import_data()
                self.assertEqual(self.saved_prompt, preferred)

    def test_invalid_selected_prompt_fails_before_any_platform_call(self):
        self.data["shifu"].pop("llm_system_prompt")
        for key in ("course_prompt", "llm_system_prompt"):
            for value in (None, 0, False, [], {}):
                for shifu_bid in ("existing-course", None):
                    with self.subTest(key=key, value=value, shifu_bid=shifu_bid):
                        self.data["shifu"][key] = value
                        with self.assertRaises(SystemExit) as error:
                            self.import_data(shifu_bid)
                        self.assertEqual(error.exception.code, 1)
                        self.api.assert_not_called()
                        self.api_safe.assert_not_called()
                        self.assertIn(f"shifu.{key} must be a string", self.errors.getvalue())
                        del self.data["shifu"][key]

    def test_invalid_preferred_key_does_not_fall_back_to_exported_prompt(self):
        self.data["shifu"]["course_prompt"] = None
        with self.assertRaises(SystemExit) as error:
            self.import_data()
        self.assertEqual(error.exception.code, 1)
        self.api.assert_not_called()
        self.api_safe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
