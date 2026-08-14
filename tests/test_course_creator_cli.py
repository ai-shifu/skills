from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "skills" / "ai-shifu-course-creator" / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "shifu-cli.py"
sys.path.insert(0, str(SCRIPT_DIR))

# The repository test workflow installs requests, while python-dotenv is only a
# runtime dependency of the deployment CLI. Stub its two imported functions so
# these transport-free unit tests stay self-contained.
if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda **_kwargs: None
    dotenv_stub.set_key = lambda *_args, **_kwargs: None
    sys.modules["dotenv"] = dotenv_stub

spec = importlib.util.spec_from_file_location("course_creator_cli", SCRIPT_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT_PATH}")
course_creator_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(course_creator_cli)


class CourseCreatorCliPaginationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.first_page = [
            {
                "bid": "course-1",
                "name": "第一门课",
                "status": "draft",
                "updated_at": "2026-07-13T08:00:00Z",
            },
            {
                "bid": "course-2",
                "name": "第二门课",
                "status": "draft",
                "updated_at": "2026-07-13T07:00:00Z",
            },
        ]
        self.second_page = [
            {
                "bid": "course-3",
                "name": "跟 AI 学 AI 通识",
                "status": "published",
                "updated_at": "2026-07-12T08:00:00Z",
            }
        ]
        self.requested_paths: list[str] = []

    def fake_course_list_api(self, _base_url, _token, method, path, **_kwargs):
        self.assertEqual(method, "get")
        self.requested_paths.append(path)
        if path == "/shifus?page_index=1&page_size=2":
            return {
                "page": 1,
                "page_size": 2,
                "total": 3,
                "page_count": 2,
                "items": self.first_page,
            }
        if path == "/shifus?page_index=2&page_size=2":
            return {
                "page": 2,
                "page_size": 2,
                "total": 3,
                "page_count": 2,
                "items": self.second_page,
            }
        self.fail(f"Unexpected API path: {path}")

    def test_list_includes_courses_from_later_pages(self):
        args = types.SimpleNamespace(token="token")

        with (
            mock.patch.object(
                course_creator_cli, "resolve_auth", return_value=("base", "token")
            ),
            mock.patch.object(
                course_creator_cli, "COURSE_LIST_PAGE_SIZE", 2
            ),
            mock.patch.object(
                course_creator_cli, "api", side_effect=self.fake_course_list_api
            ),
            mock.patch.object(
                course_creator_cli, "_fetch_shifu_title", return_value=None
            ),
            mock.patch.object(course_creator_cli.requests, "Session"),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            course_creator_cli.cmd_list(args)

        output = stdout.getvalue()
        self.assertIn("course-3", output)
        self.assertIn("Total: 3 courses", output)
        self.assertEqual(
            self.requested_paths,
            [
                "/shifus?page_index=1&page_size=2",
                "/shifus?page_index=2&page_size=2",
            ],
        )

    def test_find_title_matches_a_course_from_a_later_page(self):
        args = types.SimpleNamespace(keyword="通识", token="token")

        def fake_title(_base_url, _token, bid, *, table_key, session=None):
            del session
            if bid == "course-3" and table_key == "shifu_published_shifus":
                return "跟 AI 学 AI 通识"
            return None

        with (
            mock.patch.object(
                course_creator_cli, "resolve_auth", return_value=("base", "token")
            ),
            mock.patch.object(
                course_creator_cli, "COURSE_LIST_PAGE_SIZE", 2
            ),
            mock.patch.object(
                course_creator_cli, "api", side_effect=self.fake_course_list_api
            ),
            mock.patch.object(
                course_creator_cli, "_fetch_shifu_title", side_effect=fake_title
            ),
            mock.patch.object(course_creator_cli.requests, "Session"),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            course_creator_cli.cmd_find_title(args)

        output = stdout.getvalue()
        self.assertIn("Published", output)
        self.assertIn("course-3  跟 AI 学 AI 通识", output)
        self.assertEqual(
            self.requested_paths,
            [
                "/shifus?page_index=1&page_size=2",
                "/shifus?page_index=2&page_size=2",
            ],
        )

    def test_course_pagination_stops_at_the_safety_limit(self):
        def full_page_api(_base_url, _token, method, path, **_kwargs):
            self.assertEqual(method, "get")
            self.requested_paths.append(path)
            return {"items": list(self.first_page)}

        with (
            mock.patch.object(course_creator_cli, "COURSE_LIST_PAGE_SIZE", 2),
            mock.patch.object(course_creator_cli, "MAX_COURSE_PAGES", 2),
            mock.patch.object(course_creator_cli, "api", side_effect=full_page_api),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            with self.assertRaises(SystemExit) as raised:
                course_creator_cli._fetch_all_courses("base", "token")

        self.assertEqual(raised.exception.code, 1)
        self.assertIn("maximum page limit", stdout.getvalue())
        self.assertEqual(
            self.requested_paths,
            [
                "/shifus?page_index=1&page_size=2",
                "/shifus?page_index=2&page_size=2",
            ],
        )

    def test_course_pagination_stops_when_total_is_reached_early(self):
        def oversized_page_count_api(
            _base_url, _token, method, path, **_kwargs
        ):
            self.assertEqual(method, "get")
            self.requested_paths.append(path)
            if path != "/shifus?page_index=1&page_size=2":
                self.fail(f"Unexpected redundant API path: {path}")
            return {
                "page": 1,
                "page_size": 2,
                "total": 1,
                "page_count": 2,
                "items": list(self.first_page),
            }

        with (
            mock.patch.object(course_creator_cli, "COURSE_LIST_PAGE_SIZE", 2),
            mock.patch.object(
                course_creator_cli, "api", side_effect=oversized_page_count_api
            ),
        ):
            courses = course_creator_cli._fetch_all_courses("base", "token")

        self.assertEqual(courses, self.first_page)
        self.assertEqual(
            self.requested_paths,
            ["/shifus?page_index=1&page_size=2"],
        )


class FmtTimeTests(unittest.TestCase):
    """Backend timestamps are UTC; fmt_time must render them in local time."""

    @contextlib.contextmanager
    def _local_tz(self, tz: str):
        import os
        import time as time_module

        if not hasattr(time_module, "tzset"):
            self.skipTest("time.tzset is unavailable on this platform")
        original = os.environ.get("TZ")
        os.environ["TZ"] = tz
        time_module.tzset()
        try:
            yield
        finally:
            if original is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = original
            time_module.tzset()

    def test_z_suffixed_utc_converts_to_local(self) -> None:
        with self._local_tz("Asia/Shanghai"):
            self.assertEqual(
                course_creator_cli.fmt_time("2026-05-12T06:23:00Z"),
                "2026-05-12 14:23",
            )

    def test_offsetless_value_is_treated_as_utc(self) -> None:
        with self._local_tz("Asia/Shanghai"):
            self.assertEqual(
                course_creator_cli.fmt_time("2026-05-12T06:23:00"),
                course_creator_cli.fmt_time("2026-05-12T06:23:00Z"),
            )

    def test_explicit_offset_is_respected(self) -> None:
        with self._local_tz("Asia/Shanghai"):
            self.assertEqual(
                course_creator_cli.fmt_time("2026-05-12T06:23:00+08:00"),
                "2026-05-12 06:23",
            )

    def test_missing_and_unparsable_values(self) -> None:
        self.assertEqual(course_creator_cli.fmt_time(""), "")
        self.assertEqual(course_creator_cli.fmt_time(None), "")
        self.assertEqual(
            course_creator_cli.fmt_time("not-a-timestamp-value"),
            "not-a-timestamp-",
        )


class CourseCreatorCliTtsDefaultsTests(unittest.TestCase):
    TENCENT_VOICES = [
        {"value": "101001", "label": "Zhiyu", "resource_id": "premium"},
        {"value": "501001", "label": "Zhilan", "resource_id": "large-model"},
        {"value": "601002", "label": "Aiyue", "resource_id": "large-model"},
    ]

    def _tts_config(self, model_options):
        return {
            "providers": [
                {
                    "name": "tencent_texttovoice",
                    "models": [
                        {"value": "premium"},
                        {"value": "large-model"},
                    ],
                    "voices": self.TENCENT_VOICES,
                    "speed": {"default": 1.0},
                },
                {
                    "name": "minimax",
                    "models": [{"value": "speech-2.8-turbo"}],
                    "voices": [
                        {"value": "voice-a", "label": "Voice A"},
                        {"value": "voice-b", "label": "Voice B"},
                    ],
                    "speed": {"default": 1.0},
                },
            ],
            "model_options": model_options,
        }

    def test_voice_filter_scopes_resource_annotated_voices_to_model(self):
        filtered = course_creator_cli._filter_tts_voices_for_model(
            "tencent_texttovoice", self.TENCENT_VOICES, "large-model"
        )
        self.assertEqual([v["value"] for v in filtered], ["501001", "601002"])

    def test_voice_filter_keeps_unannotated_voices(self):
        plain_voices = [
            {"value": "voice-a", "label": "Voice A"},
            {"value": "voice-b", "label": "Voice B"},
        ]
        filtered = course_creator_cli._filter_tts_voices_for_model(
            "minimax", plain_voices, "speech-2.8-turbo"
        )
        self.assertEqual(filtered, plain_voices)

    def test_defaults_prefer_platform_declared_default_option(self):
        config = self._tts_config(
            [
                {
                    "provider": "tencent_texttovoice",
                    "value": "tencent_texttovoice/premium",
                    "model": "premium",
                    "is_default": False,
                },
                {
                    "provider": "tencent_texttovoice",
                    "value": "tencent_texttovoice/large-model",
                    "model": "large-model",
                    "is_default": True,
                },
            ]
        )
        provider, model, voice_id, speed = (
            course_creator_cli._select_platform_tts_defaults(None, config)
        )
        self.assertEqual(provider, "tencent_texttovoice")
        self.assertEqual(model, "large-model")
        # The default voice must match the default model tier, not the first
        # voice in the provider list (which belongs to the premium tier).
        self.assertEqual(voice_id, "501001")
        self.assertEqual(speed, 1.0)

    def test_defaults_fall_back_to_first_option_without_marker(self):
        config = self._tts_config(
            [
                {
                    "provider": "tencent_texttovoice",
                    "value": "tencent_texttovoice/premium",
                    "model": "premium",
                },
                {
                    "provider": "minimax",
                    "value": "minimax/speech-2.8-turbo",
                    "model": "speech-2.8-turbo",
                },
            ]
        )
        provider, model, voice_id, _speed = (
            course_creator_cli._select_platform_tts_defaults(None, config)
        )
        self.assertEqual(provider, "tencent_texttovoice")
        self.assertEqual(model, "premium")
        self.assertEqual(voice_id, "101001")


class CourseCreatorSetAvatarTests(unittest.TestCase):
    def _image(self, directory: str, name: str = "teacher.jpg") -> Path:
        path = Path(directory) / name
        path.write_bytes(b"source-image-placeholder")
        return path

    def _prepared(self, path: Path):
        return types.SimpleNamespace(
            filename="teacher-processed.jpg",
            data=b"processed-image",
            mime="image/jpeg",
            original_path=path,
            original_bytes=3 * 1024 * 1024,
            original_width=600,
            original_height=900,
        )

    def _image_utils_module(self, path: Path):
        module = types.ModuleType("image_utils")
        module.prepare_image = mock.Mock(return_value=self._prepared(path))
        return module

    def _args(self, path: Path):
        return types.SimpleNamespace(
            shifu_bid="course-bid",
            file=str(path),
            course_dir=None,
            token="token",
        )

    def test_parser_exposes_set_avatar(self):
        args = course_creator_cli.build_parser().parse_args(
            ["set-avatar", "course-bid", "--file", "teacher.png"]
        )
        self.assertEqual(args.command, "set-avatar")
        self.assertEqual(args.shifu_bid, "course-bid")

    def test_non_square_jpg_uploads_binds_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._image(tmp)
            remote = "https://res.ai-shifu.cn/avatar-resource"
            stdout, stderr = io.StringIO(), io.StringIO()
            events = []
            image_utils = self._image_utils_module(source)

            with (
                mock.patch.dict(sys.modules, {"image_utils": image_utils}),
                mock.patch.object(
                    course_creator_cli,
                    "resolve_auth",
                    return_value=("https://app.ai-shifu.cn", "token"),
                ),
                mock.patch.object(
                    course_creator_cli,
                    "_check_course_meta_conflict",
                    side_effect=lambda *a, **k: events.append("conflict"),
                ),
                mock.patch.object(
                    course_creator_cli,
                    "api_upload",
                    side_effect=lambda *a, **k: (
                        events.append(("upload", a[3], a[4])) or remote
                    ),
                ),
                mock.patch.object(
                    course_creator_cli,
                    "api",
                    side_effect=lambda *a, **k: events.append(
                        ("bind", k.get("json"))
                    ),
                ),
                mock.patch.object(
                    course_creator_cli,
                    "api_safe",
                    return_value={"avatar": remote},
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                course_creator_cli.cmd_set_avatar(self._args(source))

            self.assertEqual(events[0], "conflict")
            self.assertEqual(
                events[1],
                (
                    "upload",
                    image_utils.prepare_image.return_value.data,
                    image_utils.prepare_image.return_value.mime,
                ),
            )
            self.assertEqual(events[2], ("bind", {"avatar": remote}))
            self.assertIn("600x900", stderr.getvalue())
            self.assertIn("1:1", stderr.getvalue())
            self.assertIn(remote, stdout.getvalue())
            image_utils.prepare_image.assert_called_once_with(source.resolve())
            self.assertLess(
                len(image_utils.prepare_image.return_value.data),
                image_utils.prepare_image.return_value.original_bytes,
            )

    def test_invalid_extension_stops_before_auth_or_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "teacher.webp"
            source.write_bytes(b"unsupported-image-placeholder")
            with (
                mock.patch.object(course_creator_cli, "resolve_auth") as auth,
                mock.patch.object(course_creator_cli, "api_upload") as upload,
                self.assertRaises(SystemExit) as raised,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                course_creator_cli.cmd_set_avatar(self._args(source))

            self.assertEqual(raised.exception.code, 1)
            auth.assert_not_called()
            upload.assert_not_called()

    def test_known_revision_conflict_stops_before_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._image(tmp)
            args = self._args(source)
            args.course_dir = tmp
            manifest = {"shifu_bid": "course-bid"}
            image_utils = self._image_utils_module(source)
            with (
                mock.patch.dict(sys.modules, {"image_utils": image_utils}),
                mock.patch.object(
                    course_creator_cli,
                    "resolve_auth",
                    return_value=("https://app.ai-shifu.cn", "token"),
                ),
                mock.patch.object(
                    course_creator_cli, "_load_sync", return_value=manifest
                ),
                mock.patch.object(
                    course_creator_cli,
                    "_check_course_meta_conflict",
                    side_effect=SystemExit(course_creator_cli.EXIT_CONFLICT),
                ),
                mock.patch.object(course_creator_cli, "api_upload") as upload,
                self.assertRaises(SystemExit) as raised,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                course_creator_cli.cmd_set_avatar(args)

            self.assertEqual(
                raised.exception.code, course_creator_cli.EXIT_CONFLICT
            )
            upload.assert_not_called()

    def test_readback_mismatch_is_a_hard_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._image(tmp)
            remote = "https://res.ai-shifu.cn/new-avatar"
            image_utils = self._image_utils_module(source)
            with (
                mock.patch.dict(sys.modules, {"image_utils": image_utils}),
                mock.patch.object(
                    course_creator_cli,
                    "resolve_auth",
                    return_value=("https://app.ai-shifu.cn", "token"),
                ),
                mock.patch.object(
                    course_creator_cli, "_check_course_meta_conflict"
                ),
                mock.patch.object(
                    course_creator_cli, "api_upload", return_value=remote
                ),
                mock.patch.object(course_creator_cli, "api"),
                mock.patch.object(
                    course_creator_cli,
                    "api_safe",
                    return_value={"avatar": "https://old.example/avatar"},
                ),
                self.assertRaises(SystemExit) as raised,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                course_creator_cli.cmd_set_avatar(self._args(source))

            self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
