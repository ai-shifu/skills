from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = (Path(__file__).resolve().parents[1] / "skills"
              / "ai-shifu-course-creator" / "scripts")
sys.path.insert(0, str(SCRIPT_DIR))
if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda **_kwargs: None
    dotenv_stub.dotenv_values = lambda *_args, **_kwargs: {}
    dotenv_stub.set_key = lambda *_args, **_kwargs: None
    sys.modules["dotenv"] = dotenv_stub
spec = importlib.util.spec_from_file_location(
    "course_profile_sync_cli", SCRIPT_DIR / "shifu-cli.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load the course creator CLI")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


CN = "https://app.ai-shifu.cn"
COM = "https://app.ai-shifu.com"


class CourseProfileSyncTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.course_dir = self.root / "course"
        self.course_dir.mkdir()
        self.sync = self.course_dir / ".shifu-sync.json"
        self.stderr = self.enterContext(contextlib.redirect_stderr(io.StringIO()))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.api = self.enterContext(mock.patch.object(cli, "api"))
        self.api_safe = self.enterContext(mock.patch.object(cli, "api_safe"))
        self.upload = self.enterContext(mock.patch.object(cli, "api_upload"))

    def bind(self, base_url=CN, bid="same-course", **extra):
        manifest = {
            "schema_version": 1, "base_url": base_url, "shifu_bid": bid,
            "course": {"name": "Course", "revision": 1}, "lessons": [],
            **extra,
        }
        self.sync.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    def args(self, **kwargs):
        return types.SimpleNamespace(
            course_dir=str(self.course_dir), **kwargs,
        )

    def assert_no_platform_calls(self):
        self.api.assert_not_called()
        self.api_safe.assert_not_called()
        self.upload.assert_not_called()

    def test_same_bid_on_another_site_is_rejected_before_pull_even_with_force(self):
        self.bind(COM)
        before = self.sync.read_bytes()
        with self.assertRaises(SystemExit) as exc:
            cli._pull_into_dir(CN, "fake-token", "same-course", self.course_dir,
                               force=True)
        self.assertEqual(exc.exception.code, 1)
        self.assert_no_platform_calls()
        self.assertEqual(self.sync.read_bytes(), before)
        self.assertFalse((self.course_dir / "lessons").exists())

    def test_main_rejects_wrong_site_before_platform_handlers_and_tracking(self):
        self.bind(COM)
        context = types.SimpleNamespace(
            name="domestic", base_url=CN, directory=self.root / "profile",
            token="fake-token",
        )
        store = mock.Mock()
        store.resolve.return_value = context
        commands = [
            ["status"],
            ["pull", "same-course", "--force"],
            ["set-access", "same-course", "lesson", "--access", "trial"],
            ["set-avatar", "same-course", "--file", "unread-image.png"],
            ["upload-image", "--url", "https://source.example/image.png"],
            ["import", "same-course"],
        ]
        for arguments in commands:
            with (
                self.subTest(command=arguments[0]),
                mock.patch.object(cli, "load_env"),
                mock.patch.object(cli, "profile_store", return_value=store),
                mock.patch.object(cli, "track") as track,
                mock.patch.object(sys, "argv", [
                    "shifu-cli.py", *arguments,
                    "--course-dir", str(self.course_dir),
                ]),
            ):
                with self.assertRaises(SystemExit) as exc:
                    cli.main()
                self.assertEqual(exc.exception.code, 1)
                track.assert_not_called()
                self.assert_no_platform_calls()
        self.assertFalse((self.course_dir / "lessons").exists())

    def test_same_site_different_course_is_rejected(self):
        self.bind()
        with self.assertRaises(SystemExit):
            cli.validate_course_binding(
                self.args(command="update-meta", shifu_bid="other-course"), CN,
            )
        self.assert_no_platform_calls()

    def test_legacy_url_binding_accepts_normalized_url_without_profile(self):
        original = self.bind(CN + "/")
        result = cli.validate_course_binding(
            self.args(command="status", profile="renamed-profile"), CN,
        )
        self.assertEqual(result, original)
        self.assertNotIn("profile", json.loads(self.sync.read_text()))

    def test_profile_name_is_provenance_not_a_site_selector(self):
        original = self.bind(profile="old-profile-name")
        result = cli.validate_course_binding(
            self.args(command="status", profile="new-profile-name"), CN,
        )
        self.assertEqual(result, original)

    def test_new_import_requires_an_unbound_directory(self):
        self.bind()
        with self.assertRaises(SystemExit):
            cli.validate_course_binding(
                self.args(command="import", new=True, shifu_bid=None), CN,
            )
        self.assert_no_platform_calls()

    def test_absent_manifest_keeps_a_new_directory_unbound(self):
        self.assertIsNone(cli.validate_course_binding(
            self.args(command="import", new=True, shifu_bid=None), CN,
        ))
        self.assertFalse(self.sync.exists())

    def test_damaged_and_unsafe_manifests_never_fall_back_to_unbound(self):
        valid = self.bind()
        invalid = [
            "{", "[]", "null", json.dumps({}),
            json.dumps({**valid, "base_url": None}),
            json.dumps({**valid, "base_url": "https://user:secret@evil.example"}),
            json.dumps({**valid, "base_url": CN + "?token=fake"}),
            json.dumps({**valid, "base_url": "http://public.example"}),
            json.dumps({**valid, "shifu_bid": ""}),
            json.dumps({key: value for key, value in valid.items()
                        if key != "course"}),
            json.dumps({**valid, "course": None}),
            json.dumps({**valid, "course": []}),
            json.dumps({**valid, "lessons": None}),
            json.dumps({**valid, "lessons": [None]}),
        ]
        for content in invalid:
            with self.subTest(content=content):
                self.sync.write_text(content, encoding="utf-8")
                with self.assertRaises(SystemExit) as exc:
                    cli.validate_course_binding(self.args(command="status"), CN)
                self.assertEqual(exc.exception.code, 1)
                self.assertEqual(self.sync.read_text(), content)
                self.assert_no_platform_calls()

    def test_dangling_manifest_symlink_is_not_an_unbound_directory(self):
        self.sync.symlink_to(self.root / "missing.json")
        with self.assertRaises(SystemExit):
            cli.validate_course_binding(self.args(command="status"), CN)
        self.assert_no_platform_calls()

    def test_conflict_recovery_checks_binding_before_writing_backups(self):
        self.bind(COM)
        before = sorted(path.name for path in self.course_dir.iterdir())
        with self.assertRaises(SystemExit):
            cli._auto_pull_overwrite(
                CN, "fake-token", "same-course", self.course_dir,
                scope="lesson", attempted_content="Unpushed lesson",
                outline_bid="lesson",
            )
        self.assertEqual(sorted(path.name for path in self.course_dir.iterdir()),
                         before)
        self.assert_no_platform_calls()

    def test_pull_records_selected_profile_and_custom_url_prefix(self):
        base_url = "https://school.example:8443/academy"
        self.bind(base_url)
        self.api.side_effect = [{"name": "Course", "description": ""}, []]
        self.api_safe.return_value = {"revision": 2}
        manifest = cli._pull_into_dir(
            base_url, "fake-token", "same-course", self.course_dir,
            profile_name="school",
        )
        self.assertEqual(manifest["base_url"], base_url)
        self.assertEqual(manifest["profile"], "school")
        self.assertEqual(manifest["course"]["revision"], 2)
        self.assertEqual(json.loads(self.sync.read_text()), manifest)
        for call in self.api.call_args_list:
            self.assertEqual(call.args[0], base_url)

    def test_temporary_pull_clears_previous_profile_provenance(self):
        self.bind(profile="previous-account")
        self.api.side_effect = [{"name": "Course", "description": ""}, []]
        self.api_safe.return_value = {"revision": 2}
        cli._pull_into_dir(CN, "temporary-token", "same-course", self.course_dir)
        self.assertIsNone(json.loads(self.sync.read_text())["profile"])

    def test_temporary_metadata_push_clears_previous_profile_provenance(self):
        manifest = self.bind(profile="previous-account")
        self.api_safe.return_value = {"revision": 2}
        cli._update_course_manifest_after_push(
            CN, "temporary-token", "same-course", self.course_dir, manifest,
        )
        self.assertIsNone(json.loads(self.sync.read_text())["profile"])

    def test_temporary_lesson_push_clears_previous_profile_provenance(self):
        self.bind(profile="previous-account", lessons=[{
            "outline_bid": "lesson", "revision": 1,
        }])
        content = self.root / "lesson.md"
        content.write_text("Updated lesson", encoding="utf-8")
        args = self.args(shifu_bid="same-course", outline_bid="lesson",
                         teaching_prompt_file=str(content),
                         _profile_context=types.SimpleNamespace(name=None))
        with (
            mock.patch.object(cli, "resolve_auth", return_value=(CN, "temporary-token")),
            mock.patch.object(cli, "api_conflict_aware", return_value=("ok", {"new_revision": 2})),
        ):
            cli.cmd_update_lesson(args)
        self.assertIsNone(json.loads(self.sync.read_text())["profile"])


class CourseProfileImageTests(unittest.TestCase):
    def setUp(self):
        self.course_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = self.course_dir / "assets" / "image-manifest.json"
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def entries(self):
        return json.loads(self.path.read_text())["images"]

    def test_same_source_on_two_sites_coexists_and_same_site_replaces(self):
        for source_field in ("local", "source_url"):
            with self.subTest(source_field=source_field):
                for base_url, remote in ((CN, "cn-first"), (COM, "com"),
                                         (CN + "/", "cn-latest")):
                    cli._update_manifest(self.course_dir, {
                        source_field: "source-image", "base_url": base_url,
                        "remote": remote, "profile": "selected",
                    })
                entries = [entry for entry in self.entries()
                           if source_field in entry]
                self.assertEqual(len(entries), 2)
                self.assertEqual({entry["base_url"]: entry["remote"]
                                  for entry in entries},
                                 {CN: "cn-latest", COM: "com"})

    def test_upload_preserves_unknown_legacy_image_provenance(self):
        legacy = {"local": "image.png", "remote": "https://cdn.example/old"}
        cli._write_manifest(self.path, {"images": [legacy]})
        cli._update_manifest(self.course_dir, {
            "local": "image.png", "base_url": CN, "profile": "domestic",
            "remote": "https://cdn.example/new",
        })
        self.assertEqual(self.entries()[0], legacy)
        self.assertEqual(len(self.entries()), 2)

    def test_url_upload_records_resolved_profile_not_cdn_host(self):
        context = types.SimpleNamespace(name="school", base_url=COM)
        args = types.SimpleNamespace(
            course_dir=str(self.course_dir), file=None,
            url="https://source.example/image.png", alt="A diagram",
            _profile_context=context,
        )
        with (
            mock.patch.object(cli, "resolve_auth", return_value=(COM, "fake")),
            mock.patch.object(cli, "api", return_value="https://cdn.example/id"),
        ):
            cli.cmd_upload_image(args)
        entry = self.entries()[0]
        self.assertEqual(entry["profile"], "school")
        self.assertEqual(entry["base_url"], COM)
        self.assertEqual(entry["remote"], "https://cdn.example/id")


if __name__ == "__main__":
    unittest.main()
