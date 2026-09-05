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
    dotenv_stub.dotenv_values = lambda *_args, **_kwargs: {}
    sys.modules["dotenv"] = dotenv_stub

spec = importlib.util.spec_from_file_location("course_creator_cli", SCRIPT_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT_PATH}")
course_creator_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(course_creator_cli)


class CourseCreatorSiteTests(unittest.TestCase):
    def setUp(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(tmp)
        self.enterContext(mock.patch.dict(
            course_creator_cli.os.environ,
            {"AI_SHIFU_CONFIG_DIR": tmp}, clear=True,
        ))
        self.enterContext(mock.patch.object(course_creator_cli, "load_env"))
        self.track = self.enterContext(mock.patch.object(course_creator_cli, "track"))
        self.get = self.enterContext(mock.patch.object(course_creator_cli.requests, "get"))
        self.post = self.enterContext(mock.patch.object(course_creator_cli.requests, "post"))

    def run_cli(self, *arguments):
        with (
            mock.patch.object(sys, "argv", ["shifu-cli.py", *arguments]),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            course_creator_cli.main()
        return output.getvalue()

    def test_first_run_requires_choice_without_network_or_credentials(self):
        result = json.loads(self.run_cli("site"))
        self.assertEqual(result, {
            "status": "selection_required", "base_url": None, "contact_url": None,
        })
        self.assertFalse((self.root / "settings.json").exists())
        self.get.assert_not_called()
        self.post.assert_not_called()
        self.track.assert_not_called()

    def test_official_choices_persist_and_drive_platform_and_contact_urls(self):
        for site in ("cn", "com"):
            with self.subTest(site=site):
                result = json.loads(self.run_cli("site", "--set", site))
                self.assertEqual(result["base_url"], f"https://app.ai-shifu.{site}")
                self.assertEqual(result["contact_url"], f"https://ai-shifu.{site}/contact.html")
                self.assertEqual(json.loads(self.run_cli("site")), result)
                with (
                    mock.patch.object(course_creator_cli, "cmd_verify") as verify,
                    mock.patch.object(course_creator_cli, "cmd_login") as login,
                ):
                    self.run_cli("verify")
                    verify.assert_called_once()
                    login.assert_not_called()
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    course_creator_cli._print_verification_urls(
                        course_creator_cli.resolve_base_url(), "course", True,
                    )
                self.assertIn(f"https://app.ai-shifu.{site}/c/course", output.getvalue())
        self.assertEqual((self.root / "settings.json").stat().st_mode & 0o777, 0o600)
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_custom_url_is_normalized_and_uses_official_contact(self):
        result = json.loads(self.run_cli("site", "--url", " https://school.example:8443/ "))
        self.assertEqual(result["base_url"], "https://school.example:8443")
        self.assertEqual(result["contact_url"], "https://ai-shifu.com/contact.html")
        self.assertEqual(course_creator_cli.resolve_base_url(), result["base_url"])

    def test_explicit_configuration_is_reused_and_cannot_be_silently_overridden(self):
        self.run_cli("site", "--set", "com")
        original = (self.root / "settings.json").read_bytes()
        with mock.patch.dict(course_creator_cli.os.environ, {"SHIFU_BASE_URL": "https://app.ai-shifu.cn/"}):
            self.assertEqual(json.loads(self.run_cli("site"))["base_url"], course_creator_cli.SITE_URLS["cn"])
            with self.assertRaises(SystemExit) as error:
                self.run_cli("site", "--set", "com")
            self.assertEqual(error.exception.code, 1)
        self.assertEqual((self.root / "settings.json").read_bytes(), original)

    def test_blank_override_uses_remembered_site(self):
        self.run_cli("site", "--set", "com")
        for value in ("", "   ", "///"):
            with mock.patch.dict(course_creator_cli.os.environ, {"SHIFU_BASE_URL": value}):
                self.assertEqual(course_creator_cli.configured_base_url(), course_creator_cli.SITE_URLS["com"])

    def test_invalid_custom_addresses_are_rejected_without_saving(self):
        for url in ("", "school.example", "https://", "http://school.example", "https://user:secret@school.example", "https://school.example?q=1", "https://school.example#x", "https://school.example:bad", "https://school.example?", "https://school.example#", "https://school.example:0", "https://school example"):
            with self.subTest(url=url), self.assertRaises(SystemExit) as error:
                self.run_cli("site", "--url", url)
            self.assertEqual(error.exception.code, 1)
            self.assertFalse((self.root / "settings.json").exists())
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_loopback_development_address_is_allowed(self):
        result = json.loads(self.run_cli("site", "--url", "http://127.0.0.1:5000/"))
        self.assertEqual(result["base_url"], "http://127.0.0.1:5000")

    def test_all_platform_commands_stop_before_dispatch_without_site(self):
        for command in ("verify", "login", "list", "publish"):
            arguments = (command, "course") if command == "publish" else (command,)
            with self.subTest(command=command), self.assertRaises(SystemExit) as error:
                self.run_cli(*arguments)
            self.assertEqual(error.exception.code, 4)
        self.get.assert_not_called()
        self.post.assert_not_called()
        self.track.assert_not_called()

    def test_local_build_and_update_check_do_not_require_selection(self):
        with (
            mock.patch.object(course_creator_cli, "cmd_build") as build,
            mock.patch.object(course_creator_cli, "cmd_check_update") as update,
        ):
            self.run_cli("build", "--course-dir", str(self.root))
            self.run_cli("check-update")
        build.assert_called_once()
        update.assert_called_once()
        self.assertFalse((self.root / "settings.json").exists())

    def test_existing_unbound_credentials_are_not_sent_to_new_site(self):
        course_creator_cli.save_token("test-token")
        with self.assertRaises(SystemExit) as error:
            self.run_cli("site", "--set", "com")
        self.assertEqual(error.exception.code, 1)
        self.assertFalse((self.root / "settings.json").exists())
        self.assertEqual(course_creator_cli.load_saved_token(), "test-token")
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_same_site_setup_preserves_existing_credentials_and_settings(self):
        self.run_cli("site", "--set", "cn")
        course_creator_cli.save_token("test-token")
        self.run_cli("site", "--set", "cn")
        with self.assertRaises(SystemExit):
            self.run_cli("site", "--set", "com")
        self.assertEqual(course_creator_cli.configured_base_url(), course_creator_cli.SITE_URLS["cn"])
        self.assertEqual(course_creator_cli.load_saved_token(), "test-token")


class CourseCreatorCliBaseUrlTests(unittest.TestCase):
    def test_env_example_documents_base_url_and_token(self):
        env_example = SCRIPT_DIR.parent / ".env.example"
        content = env_example.read_text(encoding="utf-8")

        self.assertIn("\nSHIFU_BASE_URL=\n", content)
        self.assertIn("SHIFU_TOKEN=", content)

    def test_load_env_copies_the_template_when_env_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_file = root / ".env"
            env_example = root / ".env.example"
            template = (
                "SHIFU_BASE_URL=https://app.ai-shifu.cn\n"
                "SHIFU_TOKEN=\n"
            )
            env_example.write_text(template, encoding="utf-8")

            with (
                mock.patch.object(course_creator_cli, "ENV_FILE", env_file),
                mock.patch.object(
                    course_creator_cli, "ENV_EXAMPLE_FILE", env_example
                ),
                mock.patch.object(course_creator_cli, "load_dotenv") as load_dotenv,
            ):
                course_creator_cli.load_env()

            self.assertEqual(env_file.read_text(encoding="utf-8"), template)
            self.assertEqual(env_file.stat().st_mode & 0o777, 0o600)
            load_dotenv.assert_called_once_with(
                dotenv_path=env_file, override=False
            )

    def test_load_env_never_replaces_an_existing_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_file = root / ".env"
            env_example = root / ".env.example"
            existing = (
                "SHIFU_BASE_URL=https://custom.example\n"
                "SHIFU_TOKEN=existing-token\n"
            )
            env_file.write_text(existing, encoding="utf-8")
            env_example.write_text(
                "SHIFU_BASE_URL=https://app.ai-shifu.cn\nSHIFU_TOKEN=\n",
                encoding="utf-8",
            )

            with (
                mock.patch.object(course_creator_cli, "ENV_FILE", env_file),
                mock.patch.object(
                    course_creator_cli, "ENV_EXAMPLE_FILE", env_example
                ),
                mock.patch.object(course_creator_cli, "load_dotenv") as load_dotenv,
            ):
                course_creator_cli.load_env()

            self.assertEqual(env_file.read_text(encoding="utf-8"), existing)
            load_dotenv.assert_called_once_with(
                dotenv_path=env_file, override=False
            )

    def test_load_env_fails_clearly_when_the_template_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_file = root / ".env"
            env_example = root / ".env.example"

            with (
                mock.patch.object(course_creator_cli, "ENV_FILE", env_file),
                mock.patch.object(
                    course_creator_cli, "ENV_EXAMPLE_FILE", env_example
                ),
                self.assertRaises(SystemExit) as raised,
                contextlib.redirect_stderr(io.StringIO()) as stderr,
            ):
                course_creator_cli.load_env()

            self.assertEqual(raised.exception.code, 1)
            self.assertIn("missing environment template", stderr.getvalue())

    def test_login_starts_device_authorization_on_custom_base_url(self):
        args = types.SimpleNamespace(wait=False, timeout=120)
        with (
            mock.patch.dict(
                course_creator_cli.os.environ,
                {"SHIFU_BASE_URL": "https://example.test/"},
                clear=True,
            ),
            mock.patch.object(
                course_creator_cli,
                "_login_post",
                return_value={
                    "code": 0,
                    "data": {
                        "device_code": "secret-device-code",
                        "user_code": "AC4-7HK",
                        "verification_uri_complete": "https://example.test/login/device?code=AC4-7HK",
                        "interval": 5,
                        "expires_in": 600,
                    },
                },
            ) as login_post,
            mock.patch.object(course_creator_cli, "_write_private_json") as write_json,
            mock.patch.object(course_creator_cli.webbrowser, "open", return_value=False),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            course_creator_cli.cmd_login(args)

        called_base_url, called_path, payload, _ = login_post.call_args[0]
        self.assertEqual(called_base_url, "https://example.test")
        self.assertEqual(called_path, "/api/user/device/authorize")
        self.assertIn("device_name", payload)

        printed = stdout.getvalue()
        self.assertIn("AC4-7HK", printed)
        # The device code can be exchanged for a token, so it must stay on disk
        # and out of the calling agent's transcript.
        self.assertNotIn("secret-device-code", printed)
        stored = write_json.call_args[0][1]
        self.assertEqual(stored["device_code"], "secret-device-code")

    def test_login_wait_saves_the_token_once_approved(self):
        args = types.SimpleNamespace(wait=True, timeout=30)
        with (
            mock.patch.dict(
                course_creator_cli.os.environ,
                {"SHIFU_BASE_URL": "https://example.test/"},
                clear=True,
            ),
            mock.patch.object(
                course_creator_cli,
                "_read_json_file",
                return_value={
                    "device_code": "secret-device-code",
                    "user_code": "AC4-7HK",
                    "interval": 1,
                    "expires_at": course_creator_cli.time.time() + 600,
                },
            ),
            mock.patch.object(
                course_creator_cli,
                "_poll_device_authorization",
                return_value=("approved", "new-token"),
            ) as poll,
            mock.patch.object(course_creator_cli, "save_token") as save_token,
            mock.patch.object(course_creator_cli.Path, "unlink"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            course_creator_cli.cmd_login(args)

        poll.assert_called_once_with("https://example.test", "secret-device-code")
        save_token.assert_called_once_with("new-token")

    def test_login_wait_reports_a_denied_request(self):
        args = types.SimpleNamespace(wait=True, timeout=30)
        with (
            mock.patch.object(
                course_creator_cli,
                "_read_json_file",
                return_value={"device_code": "secret", "interval": 1},
            ),
            mock.patch.object(
                course_creator_cli,
                "_poll_device_authorization",
                return_value=("denied", ""),
            ),
            mock.patch.object(course_creator_cli, "save_token") as save_token,
            mock.patch.object(course_creator_cli.Path, "unlink"),
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as exit_ctx,
        ):
            course_creator_cli.cmd_login(args)

        self.assertEqual(exit_ctx.exception.code, 1)
        save_token.assert_not_called()

    def test_login_wait_without_a_pending_request_fails_clearly(self):
        args = types.SimpleNamespace(wait=True, timeout=30)
        with (
            mock.patch.object(course_creator_cli, "_read_json_file", return_value=None),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
            self.assertRaises(SystemExit) as exit_ctx,
        ):
            course_creator_cli.cmd_login(args)

        self.assertEqual(exit_ctx.exception.code, 1)
        self.assertIn("login", stdout.getvalue())

    def test_plaintext_base_url_is_refused(self):
        """Authorization carries credentials, so it must not go over http."""
        with self.assertRaises(SystemExit) as exit_ctx, contextlib.redirect_stdout(
            io.StringIO()
        ) as stdout:
            course_creator_cli.require_secure_base_url("http://example.test")
        self.assertEqual(exit_ctx.exception.code, 1)
        self.assertIn("https", stdout.getvalue())

    def test_loopback_may_stay_plaintext_for_local_development(self):
        for url in ("http://localhost:5800", "http://127.0.0.1:5800"):
            self.assertEqual(course_creator_cli.require_secure_base_url(url), url)

    def test_https_base_url_is_accepted(self):
        url = "https://app.ai-shifu.cn"
        self.assertEqual(course_creator_cli.require_secure_base_url(url), url)

    def test_wait_refuses_a_device_code_issued_by_another_host(self):
        """The device code belongs to the host that issued it."""
        args = types.SimpleNamespace(wait=True, timeout=30)
        with (
            mock.patch.dict(
                course_creator_cli.os.environ,
                {"SHIFU_BASE_URL": "https://other.example"},
                clear=True,
            ),
            mock.patch.object(
                course_creator_cli,
                "_read_json_file",
                return_value={
                    "device_code": "secret",
                    "base_url": "https://original.example",
                    "interval": 1,
                },
            ),
            mock.patch.object(
                course_creator_cli, "_poll_device_authorization"
            ) as poll,
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as exit_ctx,
        ):
            course_creator_cli.cmd_login(args)

        self.assertEqual(exit_ctx.exception.code, 1)
        poll.assert_not_called()

    def test_credentials_end_up_owner_only(self):
        """The credential file is owner-only, however permissive the umask."""
        original_umask = course_creator_cli.os.umask(0o000)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "credentials.json"
                course_creator_cli._write_private_json(target, {"token": "secret"})
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)
                # Rewriting an existing file must not leave it wider either.
                course_creator_cli._write_private_json(target, {"token": "second"})
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        finally:
            course_creator_cli.os.umask(original_umask)

    def test_credentials_are_moved_into_place_rather_than_written_in_situ(self):
        """The mode is only safe if the file is private before it holds data.

        Checking the final mode cannot show that: writing in place and then
        chmod-ing also ends at 0600, while leaving the secret readable in
        between. This asserts the implementation instead.
        """
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "credentials.json"
            real_replace = course_creator_cli.os.replace
            with mock.patch.object(
                course_creator_cli.os, "replace", wraps=real_replace
            ) as replace:
                course_creator_cli._write_private_json(target, {"token": "secret"})

            replace.assert_called_once()
            source = replace.call_args[0][0]
            self.assertNotEqual(str(source), str(target))
            self.assertEqual(json.loads(target.read_text())["token"], "secret")

    def test_macos_is_named_the_way_its_owner_would(self):
        """The approval page must not show the Darwin kernel version."""
        with (
            mock.patch.object(course_creator_cli.platform, "system", return_value="Darwin"),
            mock.patch.object(course_creator_cli.platform, "release", return_value="25.5.0"),
            mock.patch.object(
                course_creator_cli.platform, "mac_ver", return_value=("15.5", "", "")
            ),
        ):
            self.assertEqual(course_creator_cli._friendly_os_name(), "macOS 15.5")

    def test_linux_prefers_the_distribution_name(self):
        with (
            mock.patch.object(course_creator_cli.platform, "system", return_value="Linux"),
            mock.patch.object(
                course_creator_cli.platform,
                "freedesktop_os_release",
                return_value={"PRETTY_NAME": "Ubuntu 24.04.1 LTS"},
            ),
        ):
            self.assertEqual(
                course_creator_cli._friendly_os_name(), "Ubuntu 24.04.1 LTS"
            )

    def test_os_name_falls_back_without_failing_login(self):
        with (
            mock.patch.object(course_creator_cli.platform, "system", return_value="Linux"),
            mock.patch.object(
                course_creator_cli.platform,
                "freedesktop_os_release",
                side_effect=OSError("no os-release"),
            ),
            mock.patch.object(course_creator_cli.platform, "release", return_value="6.8.0"),
        ):
            self.assertEqual(course_creator_cli._friendly_os_name(), "Linux 6.8.0")

    def test_credentials_live_outside_the_skill_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                course_creator_cli.os.environ,
                {"AI_SHIFU_CONFIG_DIR": tmp},
                clear=True,
            ):
                course_creator_cli.save_token("stored-token")
                self.assertEqual(course_creator_cli.load_saved_token(), "stored-token")
                path = course_creator_cli.credentials_path()

            self.assertTrue(str(path).startswith(tmp))
            # Owner-only permissions: the file holds a live credential.
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_legacy_token_is_migrated_out_of_the_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("SHIFU_TOKEN=legacy-token\n", encoding="utf-8")
            config_dir = Path(tmp) / "config"

            with (
                mock.patch.dict(
                    course_creator_cli.os.environ,
                    {"AI_SHIFU_CONFIG_DIR": str(config_dir)},
                    clear=True,
                ),
                mock.patch.object(course_creator_cli, "ENV_FILE", env_file),
                mock.patch.object(
                    course_creator_cli,
                    "dotenv_values",
                    return_value={"SHIFU_TOKEN": "legacy-token"},
                ),
                mock.patch.object(course_creator_cli, "set_key") as set_key,
            ):
                course_creator_cli.migrate_legacy_token()
                self.assertEqual(course_creator_cli.load_saved_token(), "legacy-token")

            set_key.assert_called_once_with(str(env_file), "SHIFU_TOKEN", "")

    def test_migration_never_rewrites_an_exported_token(self):
        """A SHIFU_TOKEN the user exported is theirs; only the .env is migrated."""
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "config"
            missing_env = Path(tmp) / "absent.env"

            with (
                mock.patch.dict(
                    course_creator_cli.os.environ,
                    {
                        "AI_SHIFU_CONFIG_DIR": str(config_dir),
                        "SHIFU_TOKEN": "exported-token",
                    },
                    clear=True,
                ),
                mock.patch.object(course_creator_cli, "ENV_FILE", missing_env),
            ):
                course_creator_cli.migrate_legacy_token()
                self.assertEqual(course_creator_cli.load_saved_token(), "")


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
