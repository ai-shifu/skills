from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
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


if __name__ == "__main__":
    unittest.main()
