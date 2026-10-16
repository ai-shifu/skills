"""Caller attribution and fail-open metadata on existing business transports."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
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
spec = importlib.util.spec_from_file_location("course_usage_cli", SCRIPT_DIR / "shifu-cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

EXPECTED_METADATA = {
    "X-AI-Shifu-Skill": "ai-shifu-course-creator",
    "X-AI-Shifu-Skill-Version": "2.0.0",
    "X-AI-Shifu-Caller-Agent": "codex",
}


class PresenceOnlyEnvironment:
    """Any access beyond checking fixed names fails the regression test."""

    def __init__(self, keys):
        self.keys = set(keys)

    def __contains__(self, key):
        return key in self.keys

    def __getitem__(self, _key):
        raise AssertionError("Agent detection must not read environment values")

    def get(self, *_args):
        raise AssertionError("Agent detection must not read environment values")

    def __iter__(self):
        raise AssertionError("Agent detection must not scan environment names")


class CallerDetectionTests(unittest.TestCase):
    def test_each_allowlisted_hint_requires_presence_only(self):
        cases = {
            "codex": ("CODEX_THREAD_ID", "CODEX_SESSION_ID"),
            "claude_code": ("CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION"),
            "cursor": ("CURSOR_AGENT",),
            "hermes": ("HERMES_AGENT", "HERMES_SESSION_ID"),
            "openclaw": ("OPENCLAW_SHELL",),
            "workbuddy": ("WORKBUDDY_CONFIG_DIR",),
            "qoderwork": ("QODERWORK_IS_CN", "QODERWORK_SOURCE_CHAT_ID"),
            "grok_bot": ("SAND_AGENT",),
        }
        for expected, keys in cases.items():
            for key in keys:
                with self.subTest(key=key):
                    self.assertEqual(cli._detect_caller_agent(PresenceOnlyEnvironment([key])), expected)
            self.assertEqual(cli._detect_caller_agent(PresenceOnlyEnvironment(keys)), expected)

    def test_values_cannot_change_identity_and_unverified_names_are_ignored(self):
        for value in ("", "0", "false", "sensitive-session-secret"):
            self.assertEqual(cli._detect_caller_agent({"CODEX_THREAD_ID": value}), "codex")
        self.assertEqual(cli._detect_caller_agent(PresenceOnlyEnvironment([
            "MANUS_OPERATOR_PLATFORM", "MANUS_OPERATOR_WORKSPACE_NAMESPACE",
            "MUSE_AGENT", "DOUBAO_AGENT", "CUA_PACK_DIR", "OPENAI_MODEL",
        ])), "unknown")
        self.assertEqual(cli._detect_caller_agent(PresenceOnlyEnvironment([])), "unknown")

    def test_independent_conflicts_are_unknown_with_specific_grok_exception(self):
        for keys in (
            ["CODEX_THREAD_ID", "CLAUDECODE"],
            ["WORKBUDDY_CONFIG_DIR", "QODERWORK_SOURCE_CHAT_ID"],
            ["SAND_AGENT", "CURSOR_AGENT", "HERMES_SESSION_ID"],
        ):
            self.assertEqual(cli._detect_caller_agent(PresenceOnlyEnvironment(keys)), "unknown")
        self.assertEqual(cli._detect_caller_agent(PresenceOnlyEnvironment([
            "SAND_AGENT", "CURSOR_AGENT",
        ])), "grok_bot")


class UsageTransportTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "private-session"}, clear=True))
        self.enterContext(mock.patch.object(cli, "load_env"))
        self.enterContext(mock.patch.object(cli, "profile_store", return_value=mock.Mock()))
        self.context = types.SimpleNamespace(base_url="https://service.example", name="saved")
        self.enterContext(mock.patch.object(cli, "resolve_context", return_value=self.context))
        self.enterContext(mock.patch.object(cli, "validate_course_binding"))
        self.enterContext(mock.patch.object(cli, "resolve_auth", return_value=(self.context.base_url, "auth-token")))
        self.version = self.enterContext(mock.patch.object(cli, "_client_version", return_value="2.0.0"))
        self.response = mock.Mock(ok=True, status_code=200, content=b"{}", text="{}")
        self.response.json.return_value = {"code": 0, "data": {"items": [], "total": 0}}
        self.get = self.enterContext(mock.patch.object(cli.requests, "get", return_value=self.response))
        self.post = self.enterContext(mock.patch.object(cli.requests, "post", return_value=self.response))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def run_cli(self, *arguments):
        with mock.patch.object(sys, "argv", ["shifu-cli.py", *arguments]):
            cli.main()

    def all_business_transports(self, _args):
        origin, token = self.context.base_url, "auth-token"
        expected_data = self.response.json.return_value["data"]
        self.assertEqual(cli.api(origin, token, "get", "/shifus"), expected_data)
        self.assertEqual(cli.api_safe(origin, token, "get", "/shifus"), expected_data)
        self.assertEqual(cli.api_conflict_aware(origin, token, "post", "/lesson/mdflow"), ("ok", expected_data))
        self.assertEqual(cli.api_upload(origin, token, "image.png", b"image", "image/png"), expected_data)
        self.assertEqual(cli.api_analytics(origin, token, {"table": "orders"}), (True, self.response.json.return_value))
        self.assertEqual(cli.api_credit_detail(origin, token, {"shifu_bid": "course"}), (True, self.response.json.return_value))
        cli.cmd_export(types.SimpleNamespace(shifu_bid="course", output=None))
        session = mock.Mock()
        session.get.return_value = self.response
        session.post.return_value = self.response
        cli.api_safe(origin, token, "get", "/shifus", session=session)
        cli.api_analytics(origin, token, {"table": "orders"}, session=session)
        self.session_calls = session.mock_calls

    def captured_requests(self):
        calls = self.get.call_args_list + self.post.call_args_list
        calls += [call for call in getattr(self, "session_calls", []) if "headers" in call.kwargs]
        return calls

    def assert_usage_headers(self, expected):
        calls = self.captured_requests()
        self.assertEqual(len(calls), 9)
        for call in calls:
            headers = call.kwargs["headers"]
            metadata = {key: value for key, value in headers.items() if key.startswith("X-AI-Shifu-")}
            self.assertEqual(metadata, expected)
            self.assertNotIn("private-session", headers.values())
            if "/creator-analytics/" in call.args[0]:
                self.assertEqual(headers["Authorization"], "Bearer auth-token")
                self.assertEqual(headers["Token"], "auth-token")
            else:
                self.assertEqual(headers["Cookie"], "token=auth-token")
            if "/upfile" in call.args[0] or "/export" in call.args[0]:
                self.assertNotIn("Content-Type", headers)
            else:
                self.assertEqual(headers["Content-Type"], "application/json")

    def test_all_business_transports_preserve_auth_and_add_same_metadata(self):
        with mock.patch.object(cli, "cmd_list", side_effect=self.all_business_transports):
            self.run_cli("list")
        self.assert_usage_headers(EXPECTED_METADATA)
        self.assertEqual(cli._USAGE_METADATA_HEADERS, {})

    def test_dotenv_cannot_forge_caller_and_detection_runs_once(self):
        os.environ.clear()
        cli.load_env.side_effect = lambda: os.environ.update({"CODEX_THREAD_ID": "forged", "SAND_AGENT": "forged"})
        with (
            mock.patch.object(cli, "_detect_caller_agent", wraps=cli._detect_caller_agent) as detect,
            mock.patch.object(cli, "cmd_list", side_effect=self.all_business_transports),
        ):
            self.run_cli("list")
        self.assertEqual(detect.call_count, 1)
        self.assert_usage_headers({**EXPECTED_METADATA, "X-AI-Shifu-Caller-Agent": "unknown"})

    def test_optout_from_export_or_dotenv_omits_all_metadata_on_every_transport(self):
        for source in ("process", "dotenv"):
            with self.subTest(source=source):
                self.get.reset_mock()
                self.post.reset_mock()
                os.environ.pop("SHIFU_DISABLE_ANALYTICS", None)
                cli.load_env.side_effect = None
                if source == "process":
                    os.environ["SHIFU_DISABLE_ANALYTICS"] = "1"
                else:
                    cli.load_env.side_effect = lambda: os.environ.setdefault("SHIFU_DISABLE_ANALYTICS", "1")
                with mock.patch.object(cli, "cmd_list", side_effect=self.all_business_transports):
                    self.run_cli("list")
                self.assert_usage_headers({})
        self.version.assert_not_called()

    def test_invalid_version_or_metadata_failure_does_not_change_business_results(self):
        for bad_version in ("2.0.0\r\nPrivate: value", "dev-branch", "", "1.2.3-rc.1"):
            self.get.reset_mock()
            self.post.reset_mock()
            self.version.return_value = bad_version
            with mock.patch.object(cli, "cmd_list", side_effect=self.all_business_transports):
                self.run_cli("list")
            self.assert_usage_headers({})
        self.get.reset_mock()
        self.post.reset_mock()
        self.version.side_effect = RuntimeError("optional metadata failed")
        with mock.patch.object(cli, "cmd_list", side_effect=self.all_business_transports):
            self.run_cli("list")
        self.assert_usage_headers({})

    def test_detection_failure_is_fail_open(self):
        with (
            mock.patch.object(cli, "_detect_caller_agent", side_effect=RuntimeError("unavailable")),
            mock.patch.object(cli, "cmd_list", side_effect=self.all_business_transports),
        ):
            self.run_cli("list")
        self.assert_usage_headers({})

    def test_repeated_invocations_do_not_reuse_caller_or_leak_after_failure(self):
        observed = []

        def request(_args):
            cli.api(self.context.base_url, "auth-token", "get", "/shifus")
            observed.append(self.get.call_args.kwargs["headers"]["X-AI-Shifu-Caller-Agent"])

        with mock.patch.object(cli, "cmd_list", side_effect=request):
            self.run_cli("list")
            os.environ.clear()
            os.environ["SAND_AGENT"] = ""
            os.environ["CURSOR_AGENT"] = ""
            self.run_cli("list")
            os.environ.clear()
            self.run_cli("list")
        self.assertEqual(observed, ["codex", "grok_bot", "unknown"])
        with mock.patch.object(cli, "cmd_list", side_effect=SystemExit(1)), self.assertRaises(SystemExit):
            self.run_cli("list")
        self.assertEqual(cli._USAGE_METADATA_HEADERS, {})

    def test_authentication_and_update_requests_have_no_usage_metadata(self):
        with self.assertRaises(SystemExit) as result:
            self.run_cli("verify")
        self.assertEqual(result.exception.code, 0)
        self.assertEqual(self.get.call_args.kwargs["headers"], {
            "Cookie": "token=auth-token", "Content-Type": "application/json",
        })

        def authorization(_args):
            cli._login_post(self.context.base_url, "/api/user/device/authorize", {}, "failed")
            cli._poll_device_authorization(self.context.base_url, "private-device-code")

        with mock.patch.object(cli, "cmd_login", side_effect=authorization):
            self.run_cli("login")
        for call in self.post.call_args_list:
            self.assertEqual(call.kwargs["headers"], {"Content-Type": "application/json"})
        with mock.patch.object(cli, "check_for_update", return_value={}) as update:
            self.run_cli("check-update")
        update.assert_called_once_with(force=False)
        self.version.assert_not_called()


if __name__ == "__main__":
    unittest.main()
