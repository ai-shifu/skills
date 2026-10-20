from __future__ import annotations

import contextlib
import copy
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
                # Older platform exports may still contain temperature fields;
                # importing their content must not send those settings back.
                self.assertIn("llm_temperature", self.data["shifu"])
                self.assertIn("ask_llm_temperature", self.data["shifu"])
                for call in self.api.call_args_list + self.api_safe.call_args_list:
                    payload = call.kwargs.get("json", {})
                    self.assertFalse(any("temperature" in key for key in payload), payload)

    def test_build_output_still_imports_course_prompt(self):
        lessons = self.root / "lessons"
        lessons.mkdir()
        (lessons / "lesson-01.md").write_text("Lesson content\n", encoding="utf-8")
        (self.root / "course-prompt.md").write_text("Builder Course Prompt", encoding="utf-8")
        built_path = cli._build_import_json(str(self.root), title="Built course")
        self.data = json.loads(Path(built_path).read_text(encoding="utf-8"))
        for shifu_bid in ("existing-course", None):
            with self.subTest(shifu_bid=shifu_bid):
                self.lesson_contents.clear()
                self.assertEqual(self.import_data(shifu_bid), shifu_bid or "new-course")
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


class CourseImportPreflightTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.data = {
            "shifu": {"title": "Course", "description": "Course description"},
            "outline_items": [
                {"outline_item_bid": "chapter", "title": "Chapter"},
                {"outline_item_bid": "lesson", "title": "Lesson",
                 "parent_bid": "chapter", "content": "Lesson content"},
            ],
        }
        self.api = self.enterContext(mock.patch.object(cli, "api", side_effect=self.request))
        self.api_safe = self.enterContext(mock.patch.object(cli, "api_safe", side_effect=self.safe_request))
        self.enterContext(mock.patch.object(cli.time, "sleep"))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.errors = self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def request(self, base_url, token, method, path, **kwargs):
        if method == "put" and path == "/shifus":
            return {"bid": "new-course"}
        if method == "put" and path.endswith("/outlines"):
            return {"bid": f"created-outline-{self.api.call_count}"}
        if method == "post" and path.endswith("/mdflow"):
            return {}
        self.fail(f"Unexpected request: {method} {path}")

    def safe_request(self, base_url, token, method, path, **kwargs):
        if method == "post" and path.endswith("/detail"):
            return {}
        if method == "get" and path.endswith("/outlines"):
            return [{"bid": "old-chapter", "children": [{"bid": "old-lesson"}]}]
        if method == "delete":
            return {}
        self.fail(f"Unexpected safe request: {method} {path}")

    def write_data(self, data):
        path = self.root / "course.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def assert_rejected_before_platform(self, data, field):
        path = self.write_data(data)
        for shifu_bid in ("existing-course", None):
            with self.subTest(shifu_bid=shifu_bid):
                self.api.reset_mock()
                self.api_safe.reset_mock()
                self.errors.seek(0)
                self.errors.truncate()
                with self.assertRaises(SystemExit) as caught:
                    cli._import_flat("https://app.ai-shifu.com", "test-token", path, shifu_bid)
                self.assertEqual(caught.exception.code, 1)
                self.assertIn(field, self.errors.getvalue())
                self.api.assert_not_called()
                self.api_safe.assert_not_called()

    def test_rejects_invalid_top_level_and_required_container_shapes(self):
        for data in (None, False, 1, "course", []):
            with self.subTest(data=data):
                self.assert_rejected_before_platform(data, "object")
        for field, invalid_values in (
            ("shifu", (None, False, 1, "course", [])),
            ("outline_items", (None, False, 1, "outlines", {})),
        ):
            data = copy.deepcopy(self.data)
            del data[field]
            with self.subTest(field=field, missing=True):
                self.assert_rejected_before_platform(data, field)
            for value in invalid_values:
                data = copy.deepcopy(self.data)
                data[field] = value
                with self.subTest(field=field, value=value):
                    self.assert_rejected_before_platform(data, field)

    def test_rejects_unreadable_and_malformed_json_before_platform(self):
        for contents in (None, b"{broken JSON", b"\xff"):
            for shifu_bid in ("existing-course", None):
                with self.subTest(contents=contents, shifu_bid=shifu_bid):
                    path = self.root / "unreadable-course.json"
                    if contents is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(contents)
                    with self.assertRaises(SystemExit) as caught:
                        cli._import_flat("https://app.ai-shifu.com", "test-token", path, shifu_bid)
                    self.assertEqual(caught.exception.code, 1)
                    self.assertIn("import JSON", self.errors.getvalue())
                    self.api.assert_not_called()
                    self.api_safe.assert_not_called()

    def test_rejects_non_object_outline_members(self):
        for value in (None, False, 1, "lesson", []):
            with self.subTest(value=value):
                data = copy.deepcopy(self.data)
                data["outline_items"][1] = value
                self.assert_rejected_before_platform(data, "outline_items[1]")

    def test_rejects_missing_or_blank_course_and_outline_titles(self):
        missing = object()
        for scope, field in (("shifu", "shifu.title"), ("outline", "outline_items[0].title")):
            for value in (missing, None, False, 0, [], {}, "", " \t\n"):
                with self.subTest(scope=scope, missing=value is missing, value=value):
                    data = copy.deepcopy(self.data)
                    target = data["shifu"] if scope == "shifu" else data["outline_items"][0]
                    if value is missing:
                        del target["title"]
                    else:
                        target["title"] = value
                    self.assert_rejected_before_platform(data, field)

    def test_rejects_non_string_description_and_lesson_content(self):
        for scope, key, field in (
            ("shifu", "description", "shifu.description"),
            ("outline", "content", "outline_items[1].content"),
        ):
            for value in (None, False, 0, [], {}):
                with self.subTest(field=field, value=value):
                    data = copy.deepcopy(self.data)
                    target = data["shifu"] if scope == "shifu" else data["outline_items"][1]
                    target[key] = value
                    self.assert_rejected_before_platform(data, field)

    def test_rejects_invalid_unicode_in_consumed_text_before_platform(self):
        fields = (
            ("shifu", "title", "shifu.title"),
            ("shifu", "description", "shifu.description"),
            ("shifu", "course_prompt", "shifu.course_prompt"),
            ("shifu", "llm_system_prompt", "shifu.llm_system_prompt"),
            ("outline", "title", "outline_items[1].title"),
            ("outline", "content", "outline_items[1].content"),
        )
        for scope, key, field in fields:
            for text in ("bad\ud800", "bad\udfff"):
                with self.subTest(field=field, text=ascii(text)):
                    data = copy.deepcopy(self.data)
                    target = data["shifu"] if scope == "shifu" else data["outline_items"][1]
                    target[key] = text
                    self.assert_rejected_before_platform(data, field)

    def test_valid_unicode_text_is_preserved_without_normalization(self):
        text = "  👍🏽你好 e\u0301👩‍💻\n"
        for prompt_key in ("course_prompt", "llm_system_prompt"):
            for shifu_bid in ("existing-course", None):
                with self.subTest(prompt_key=prompt_key, shifu_bid=shifu_bid):
                    data = copy.deepcopy(self.data)
                    data["shifu"].update({"title": text, "description": text, prompt_key: text})
                    # Fields not consumed by import remain outside text validation.
                    data["ignored"] = "metadata\ud800"
                    if prompt_key == "course_prompt":
                        data["shifu"]["llm_system_prompt"] = "shadowed\ud800"
                    for outline in data["outline_items"]:
                        outline.update({"title": text, "content": text, "course_prompt": "unused\ud800"})
                    path = self.write_data(data)
                    self.api.reset_mock()
                    self.api_safe.reset_mock()
                    result = cli._import_flat("https://app.ai-shifu.com", "test-token", path, shifu_bid)
                    self.assertEqual(result, shifu_bid or "new-course")
                    detail = next(call.kwargs["json"] for call in self.api_safe.call_args_list
                                  if call.args[2:] == ("post", f"/shifus/{result}/detail"))
                    self.assertEqual(detail, {"name": text, "description": text, "system_prompt": text})
                    created = [call.kwargs["json"] for call in self.api.call_args_list
                               if call.args[2] == "put" and call.args[3].endswith("/outlines")]
                    self.assertEqual([item["name"] for item in created], [text, text])
                    contents = [call.kwargs["json"]["data"] for call in self.api.call_args_list
                                if call.args[2] == "post" and call.args[3].endswith("/mdflow")]
                    self.assertEqual(contents, [text, text])

    def test_rejects_invalid_outline_identifiers_and_parent_types(self):
        for key in ("outline_item_bid", "parent_bid"):
            for value in (False, 0, [], {}):
                with self.subTest(key=key, value=value):
                    data = copy.deepcopy(self.data)
                    data["outline_items"][1][key] = value
                    self.assert_rejected_before_platform(data, f"outline_items[1].{key}")

    def test_rejects_duplicate_outline_identifiers(self):
        data = copy.deepcopy(self.data)
        data["outline_items"][1]["outline_item_bid"] = "chapter"
        self.assert_rejected_before_platform(data, "outline_items[1].outline_item_bid")

    def test_rejects_dangling_self_referencing_cyclic_and_deep_parents(self):
        invalid_outlines = (
            [{"outline_item_bid": "lesson", "title": "Lesson", "parent_bid": "missing"}],
            [{"outline_item_bid": "lesson", "title": "Lesson", "parent_bid": "lesson"}],
            [{"outline_item_bid": "first", "title": "First", "parent_bid": "second"},
             {"outline_item_bid": "second", "title": "Second", "parent_bid": "first"}],
            [{"outline_item_bid": "chapter", "title": "Chapter"},
             {"outline_item_bid": "lesson", "title": "Lesson", "parent_bid": "chapter"},
             {"outline_item_bid": "nested", "title": "Nested", "parent_bid": "lesson"}],
        )
        for outlines in invalid_outlines:
            with self.subTest(outlines=outlines):
                data = copy.deepcopy(self.data)
                data["outline_items"] = outlines
                self.assert_rejected_before_platform(data, "parent_bid")

    def test_root_items_without_identifiers_and_optional_content_remain_valid(self):
        data = {"shifu": {"title": "Course"}, "outline_items": [
            {"title": "Root with omitted parent and identifier", "content": "Root lesson content"},
            {"title": "Root with empty parent and identifier", "parent_bid": "", "outline_item_bid": ""},
            {"title": "Root with null parent and identifier", "parent_bid": None, "outline_item_bid": None,
             "content": ""},
        ]}
        path = self.write_data(data)
        for shifu_bid in ("existing-course", None):
            with self.subTest(shifu_bid=shifu_bid):
                self.api.reset_mock()
                self.api_safe.reset_mock()
                result = cli._import_flat("https://app.ai-shifu.com", "test-token", path, shifu_bid)
                self.assertEqual(result, shifu_bid or "new-course")
                detail = next(call.kwargs["json"] for call in self.api_safe.call_args_list
                              if call.args[2:] == ("post", f"/shifus/{result}/detail"))
                self.assertEqual(detail, {"name": "Course", "description": ""})
                created = [call.kwargs["json"] for call in self.api.call_args_list
                           if call.args[2] == "put" and call.args[3].endswith("/outlines")]
                self.assertEqual(len(created), 3)
                self.assertTrue(all("parent_bid" not in payload for payload in created))
                saved_contents = [call.kwargs["json"]["data"] for call in self.api.call_args_list
                                  if call.args[2] == "post" and call.args[3].endswith("/mdflow")]
                self.assertEqual(saved_contents, ["Root lesson content"])

    def test_child_before_parent_input_maps_to_the_new_parent(self):
        data = copy.deepcopy(self.data)
        data["outline_items"].reverse()
        path = self.write_data(data)
        created = []

        def create_outline(base_url, token, method, path, **kwargs):
            if method == "put" and path.endswith("/outlines"):
                payload = kwargs["json"]
                created.append(payload)
                return {"bid": "new-chapter" if payload["name"] == "Chapter" else "new-lesson"}
            return self.request(base_url, token, method, path, **kwargs)

        self.api.side_effect = create_outline
        for shifu_bid in ("existing-course", None):
            with self.subTest(shifu_bid=shifu_bid):
                created.clear()
                result = cli._import_flat("https://app.ai-shifu.com", "test-token", path, shifu_bid)
                self.assertEqual(result, shifu_bid or "new-course")
                self.assertEqual(created, [{"name": "Chapter"}, {"name": "Lesson", "parent_bid": "new-chapter"}])

    def test_empty_outline_list_remains_valid(self):
        data = {"shifu": {"title": "Empty course"}, "outline_items": []}
        path = self.write_data(data)
        for shifu_bid in ("existing-course", None):
            with self.subTest(shifu_bid=shifu_bid):
                result = cli._import_flat("https://app.ai-shifu.com", "test-token", path, shifu_bid)
                self.assertEqual(result, shifu_bid or "new-course")

    def test_ignored_metadata_and_shadowed_legacy_prompt_remain_compatible(self):
        data = copy.deepcopy(self.data)
        data.update({"version": {}, "structure": None, "unrecognized": [1, 2]})
        data["shifu"].update({"course_prompt": "", "llm_system_prompt": {}, "price": {}})
        data["outline_items"][0].update({"position": {}, "hidden": [], "course_prompt": None})
        path = self.write_data(data)
        for shifu_bid in ("existing-course", None):
            with self.subTest(shifu_bid=shifu_bid):
                self.api_safe.reset_mock()
                result = cli._import_flat("https://app.ai-shifu.com", "test-token", path, shifu_bid)
                self.assertEqual(result, shifu_bid or "new-course")
                detail = next(call.kwargs["json"] for call in self.api_safe.call_args_list
                              if call.args[2:] == ("post", f"/shifus/{result}/detail"))
                self.assertEqual(detail["system_prompt"], "")
                self.assertNotIn("price", detail)

    def test_directory_import_validates_payload_before_remote_revision_preflight(self):
        course_dir = self.root / "course"
        (course_dir / "lessons").mkdir(parents=True)
        (course_dir / "lessons" / "lesson-01.md").write_text("Lesson", encoding="utf-8")
        (course_dir / "structure.json").write_text(json.dumps({"chapters": [
            {"title": "", "lessons": [{"file": "lesson-01.md", "title": "Lesson"}]},
        ]}), encoding="utf-8")
        (course_dir / ".shifu-sync.json").write_text(json.dumps({
            "schema_version": 1, "base_url": "https://app.ai-shifu.com", "shifu_bid": "existing-course",
            "course": {"revision": 1}, "lessons": [],
        }), encoding="utf-8")
        args = cli.build_parser().parse_args(["import", "existing-course", "--course-dir", str(course_dir)])
        with mock.patch.object(cli, "resolve_auth", return_value=("https://app.ai-shifu.com", "test-token")):
            with self.assertRaises(SystemExit) as caught:
                cli.cmd_import(args)
        self.assertEqual(caught.exception.code, 1)
        self.assertIn("outline_items[0].title", self.errors.getvalue())
        self.api.assert_not_called()
        self.api_safe.assert_not_called()

    def test_directory_import_uses_validated_content_when_json_changes_during_preflight(self):
        course_dir = self.root / "course"
        (course_dir / "lessons").mkdir(parents=True)
        (course_dir / "lessons" / "lesson-01.md").write_text("Validated lesson", encoding="utf-8")
        (course_dir / ".shifu-sync.json").write_text(json.dumps({
            "schema_version": 1, "base_url": "https://app.ai-shifu.com", "shifu_bid": "existing-course",
            "course": {"revision": 1}, "lessons": [],
        }), encoding="utf-8")
        import_path = course_dir / "shifu-import.json"
        changed = {"shifu": {"title": "Changed after validation"}, "outline_items": []}

        def remote_preflight(base_url, token, method, path, **kwargs):
            if method == "get" and path.endswith("/draft-meta"):
                self.assertTrue(import_path.exists(), "The payload must be built before remote preflight")
                import_path.write_text(json.dumps(changed), encoding="utf-8")
                return {"revision": 1}
            return self.safe_request(base_url, token, method, path, **kwargs)

        self.api_safe.side_effect = remote_preflight
        args = cli.build_parser().parse_args([
            "import", "existing-course", "--course-dir", str(course_dir), "--title", "Validated title",
        ])
        with (
            mock.patch.object(cli, "resolve_auth", return_value=("https://app.ai-shifu.com", "test-token")),
            mock.patch.object(cli, "_pull_into_dir"),
        ):
            cli.cmd_import(args)

        self.assertEqual(json.loads(import_path.read_text(encoding="utf-8")), changed)
        detail = next(call.kwargs["json"] for call in self.api_safe.call_args_list
                      if call.args[2:] == ("post", "/shifus/existing-course/detail"))
        self.assertEqual(detail["name"], "Validated title")
        lesson_contents = [call.kwargs["json"]["data"] for call in self.api.call_args_list
                           if call.args[2] == "post" and call.args[3].endswith("/mdflow")]
        self.assertEqual(lesson_contents, ["Validated lesson"])


class CourseTemperatureOutputTests(unittest.TestCase):
    def test_course_config_snapshot_omits_temperature_and_preserves_other_settings(self):
        detail = {
            "model": "teaching-model",
            "ask_model": "follow-up-model",
            "temperature": 0.7,
            "ask_temperature": 0.4,
            "price": 25,
            "keywords": "course,learning",
            "tts_enabled": True,
            "tts_voice_id": "course-voice",
            "ask_system_prompt": "Answer follow-up questions",
        }
        with tempfile.TemporaryDirectory() as directory:
            cli._write_course_config(directory, cli._course_config_from_detail(detail))
            snapshot = json.loads(
                (Path(directory) / cli.COURSE_CONFIG_NAME).read_text(encoding="utf-8")
            )
        self.assertFalse(any("temperature" in key for key in snapshot), snapshot)
        for key in ("model", "ask_model", "price", "tts_enabled", "tts_voice_id",
                    "ask_system_prompt"):
            self.assertEqual(snapshot[key], detail[key])
        self.assertEqual(snapshot["keywords"], ["course", "learning"])

    def test_single_and_multiple_chapter_builds_omit_all_temperature_fields(self):
        for multiple_chapters in (False, True):
            with self.subTest(multiple_chapters=multiple_chapters):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    lessons = root / "lessons"
                    lessons.mkdir()
                    (lessons / "lesson-01.md").write_text("First lesson\n", encoding="utf-8")
                    (lessons / "lesson-02.md").write_text("Second lesson\n", encoding="utf-8")
                    (root / "course-prompt.md").write_text("Course Prompt", encoding="utf-8")
                    if multiple_chapters:
                        (root / "structure.json").write_text(json.dumps({
                            "chapters": [
                                {"title": "First chapter", "lessons": [
                                    {"file": "lesson-01.md", "title": "First lesson"},
                                ]},
                                {"title": "Second chapter", "lessons": [
                                    {"file": "lesson-02.md", "title": "Second lesson"},
                                ]},
                            ],
                        }), encoding="utf-8")
                    with contextlib.redirect_stdout(io.StringIO()):
                        output_path = cli._build_import_json(directory, title="Built course")
                    data = json.loads(Path(output_path).read_text(encoding="utf-8"))

                for record in [data["shifu"], *data["outline_items"]]:
                    self.assertFalse(any("temperature" in key for key in record), record)
                self.assertEqual(data["shifu"]["course_prompt"], "Course Prompt")
                chapters = [item for item in data["outline_items"] if not item["parent_bid"]]
                built_lessons = [item for item in data["outline_items"] if item["parent_bid"]]
                self.assertEqual(len(chapters), 2 if multiple_chapters else 1)
                self.assertEqual([item["content"] for item in built_lessons],
                                 ["First lesson\n", "Second lesson\n"])
                self.assertTrue(all(item["course_prompt"] == "Course Prompt"
                                    for item in built_lessons))


if __name__ == "__main__":
    unittest.main()
