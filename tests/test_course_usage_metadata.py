"""Caller attribution and fail-open metadata on existing business transports."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
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
import skill_update_check as update_checks

EXPECTED_METADATA = {
    "X-AI-Shifu-Skill": "ai-shifu-course-creator",
    "X-AI-Shifu-Skill-Version": "2.0.0",
    "X-AI-Shifu-Caller-Agent": "codex",
    "X-AI-Shifu-Caller-Agent-Name": "Codex",
}


class CallerDetectionTests(unittest.TestCase):
    def test_cli_generates_every_fixed_display_name_with_the_bundled_version(self):
        names = {
            "codex": "Codex",
            "crush": "Crush",
            "hermes-agent": "Hermes Agent",
            "kilo-code": "Kilo Code",
            "trae": "TRAE",
            "vtcode": "VT Code",
            "claude-code": "Claude Code",
            "cursor-cli": "Cursor CLI",
            "cursor": "Cursor",
            "openclaw": "OpenClaw",
            "workbuddy": "WorkBuddy",
            "qwenwork": "QwenWork",
            "grok-bot": "Grok Bot",
            "cue": "Cue",
            "muse": "Muse",
            "manus": "Manus",
            "doubao-work": "Doubao Work",
            "kimi": "Kimi Code",
            "grok-build": "Grok Build",
            "gemini-cli": "Gemini CLI",
            "cline": "Cline",
            "antigravity": "Antigravity",
            "augment-cli": "Augment CLI",
            "opencode": "opencode",
            "goose": "Goose",
            "junie": "Junie",
            "pi": "Pi",
            "cowork": "Claude Cowork",
            "kiro": "Kiro",
            "github-copilot": "GitHub Copilot",
            "replit": "Replit",
            "devin": "Devin",
            "zed": "Zed",
            "hi": "hi",
            "sandbase-harness": "SandBase Harness",
            "unknown": "Unknown Agent",
        }
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(cli, "_client_version", return_value="3.12.45"):
            for family, name in names.items():
                with self.subTest(family=family):
                    self.assertEqual(cli._skill_usage_metadata(family), {
                        "X-AI-Shifu-Skill": "ai-shifu-course-creator",
                        "X-AI-Shifu-Skill-Version": "3.12.45",
                        "X-AI-Shifu-Caller-Agent": family,
                        "X-AI-Shifu-Caller-Agent-Name": name,
                    })
            self.assertEqual(cli._skill_usage_metadata("unverified-agent"), {})

    def test_cli_accepts_only_declared_or_runtime_evidence(self):
        for agent_id in cli.AGENT_DISPLAY_NAMES:
            self.assertEqual(cli._detect_caller_agent({"AI_AGENT": agent_id}), agent_id)
        for env in (
            {}, {"AI_AGENT": "unregistered", "CODEX_THREAD_ID": "1"},
            {"GOOSE_PROVIDER": "synthetic-provider"}, {"CURSOR_TRACE_ID": "synthetic"},
            {"COPILOT_GITHUB_TOKEN": "synthetic-secret"}, {"PATH": "/opt/.pi/agent/bin"},
        ):
            self.assertEqual(cli._detect_caller_agent(env), "unknown")
        self.assertEqual(cli._detect_caller_agent({"AI_AGENT": " CLAUDE_CODE "}), "claude-code")

    def test_nonempty_runtime_policy_and_removed_hints_replace_presence_only(self):
        self.assertEqual(cli._detect_caller_agent({"CODEX_THREAD_ID": ""}), "unknown")
        for value in ("0", "false", " ", "sensitive-session-secret"):
            self.assertEqual(cli._detect_caller_agent({"CODEX_THREAD_ID": value}), "codex")
        self.assertEqual(cli._detect_caller_agent(dict.fromkeys((
            "CODEX_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION", "WORKBUDDY_CONFIG_DIR",
            "QODERWORK_IS_CN", "QODERWORK_SOURCE_CHAT_ID", "MUSE_AGENT", "DOUBAO_AGENT",
        ), "synthetic")), "unknown")

    def test_ordered_runtime_matches_replace_independent_conflict_fallback(self):
        self.assertEqual(cli._detect_caller_agent({"CODEX_THREAD_ID": "1", "CLAUDECODE": "1"}), "codex")
        self.assertEqual(cli._detect_caller_agent({"SAND_AGENT": "1", "CURSOR_AGENT": "1"}), "grok-bot")
        self.assertEqual(cli._detect_caller_agent({
            "SAND_AGENT": "1", "CURSOR_AGENT": "1", "HERMES_SESSION_ID": "1",
        }), "hermes-agent")


class AutomaticUpdateMetadataTests(unittest.TestCase):
    def test_update_worker_excludes_business_authentication_and_usage_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_md = root / "SKILL.md"
            skill_md.write_text(
                "---\nname: ai-shifu-course-creator\nversion: 1.0.0\n---\n",
                encoding="utf-8",
            )
            release = {
                "tag_name": "v9.0.0", "draft": False, "prerelease": False,
                "body": "Update notes", "published_at": "2026-10-21T00:00:00Z",
                "html_url": "https://github.com/ai-shifu/skills/releases/tag/v9.0.0",
            }
            update_response = types.SimpleNamespace(
                status_code=200, url=update_checks.MANIFEST_URL, headers={},
                iter_content=lambda **_kwargs: iter([json.dumps(release).encode("utf-8")]),
                close=mock.Mock(),
            )
            business_response = mock.Mock(ok=True)
            business_response.json.return_value = {"code": 0, "data": {"value": 7}}
            requests = []

            def get(url, **kwargs):
                requests.append((url, kwargs["headers"]))
                return update_response if url == update_checks.MANIFEST_URL else business_response

            # Run the real worker and scheduler in-process so every outgoing
            # request is intercepted; worker timeout behavior has separate tests.
            automatic = cli.automatic_check_for_update

            def lookup(directory):
                return automatic(
                    directory, skill_md=skill_md, run_check=update_checks._automatic_check_worker,
                )

            def business(_args):
                result = cli.api("https://platform.example", "business-token", "get", "/shifus")
                print(json.dumps(result))

            with (
                mock.patch.dict(os.environ, {
                    "AI_SHIFU_CONFIG_DIR": str(root / "configuration"),
                    "CODEX_THREAD_ID": "private-session", "SHIFU_TOKEN": "private-env-token",
                }, clear=True),
                mock.patch.object(cli, "automatic_check_for_update", side_effect=lookup),
                mock.patch.object(update_checks.requests, "get", side_effect=get),
                mock.patch.object(cli, "load_env"),
                mock.patch.object(cli, "profile_store"),
                mock.patch.object(cli, "resolve_context", return_value=types.SimpleNamespace(
                    base_url="https://platform.example", name="saved",
                )),
                mock.patch.object(cli, "_client_version", return_value="2.0.0"),
                mock.patch.object(cli, "_USAGE_METADATA_HEADERS", {"stale-header": "old"}),
                mock.patch.object(cli, "cmd_list", side_effect=business),
                mock.patch.object(sys, "argv", ["shifu-cli.py", "list"]),
                contextlib.redirect_stdout(io.StringIO()) as output,
                contextlib.redirect_stderr(io.StringIO()) as errors,
            ):
                cli.main()
            self.assertEqual(json.loads(output.getvalue()), {"value": 7})
            self.assertIn(release["html_url"], errors.getvalue())
            self.assertEqual(len(requests), 2)
            self.assertEqual(requests[0], (
                update_checks.MANIFEST_URL, {"Accept": "application/vnd.github+json"},
            ))
            business_headers = requests[1][1]
            self.assertEqual(business_headers["Cookie"], "token=business-token")
            self.assertEqual({
                key: value for key, value in business_headers.items()
                if key.startswith("X-AI-Shifu-")
            }, EXPECTED_METADATA)
            self.assertNotIn("stale-header", business_headers)
            update_response.close.assert_called_once()


class UsageTransportTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "private-session"}, clear=True))
        self.enterContext(mock.patch.object(cli, "load_env"))
        self.enterContext(mock.patch.object(cli, "_maybe_check_for_updates"))
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
            self.assertNotIn("User-Agent", headers)
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

    def test_display_names_follow_ordered_detection_on_all_business_transports(self):
        cases = (
            ({"CODEX_THREAD_ID": "1", "CODEX_CI": "1"}, "codex", "Codex"),
            ({"CLAUDECODE": "1", "CLAUDE_CODE": "1"}, "claude-code", "Claude Code"),
            ({"CURSOR_AGENT": "1"}, "cursor-cli", "Cursor CLI"),
            ({"HERMES_AGENT": "1"}, "hermes-agent", "Hermes Agent"),
            ({"OPENCLAW_SHELL": "1"}, "openclaw", "OpenClaw"),
            ({"WORKBUDDY_APPLICATION_NAME": "arbitrary"}, "workbuddy", "WorkBuddy"),
            ({"QODER_WORK_INTEGRATION_PRODUCT": "arbitrary"}, "qwenwork", "QwenWork"),
            ({"SAND_AGENT": "0", "CURSOR_AGENT": "1"}, "grok-bot", "Grok Bot"),
            ({}, "unknown", "Unknown Agent"),
            ({"CODEX_THREAD_ID": "1", "CLAUDECODE": "1"}, "codex", "Codex"),
            ({"SAND_AGENT": "1", "CURSOR_AGENT": "1", "HERMES_AGENT": "1"}, "hermes-agent", "Hermes Agent"),
            ({"AI_AGENT": "unknown-declaration", "CODEX_THREAD_ID": "1"}, "unknown", "Unknown Agent"),
            ({"COPILOT_MODEL": "synthetic-model"}, "unknown", "Unknown Agent"),
            ({"AI_AGENT": " GITHUB-COPILOT "}, "github-copilot", "GitHub Copilot"),
            ({"CODEX_THREAD_ID": ""}, "unknown", "Unknown Agent"),
            ({"VTCODE": "0"}, "vtcode", "VT Code"),
            ({"MANUS_LONG_DESKTOP_WORKER": "false"}, "cue", "Cue"),
        )
        for environment, family, name in cases:
            with self.subTest(family=family, name=name):
                os.environ.clear()
                os.environ.update(environment)
                self.get.reset_mock()
                self.post.reset_mock()
                with mock.patch.object(cli, "cmd_list", side_effect=self.all_business_transports):
                    self.run_cli("list")
                self.assert_usage_headers({
                    **EXPECTED_METADATA,
                    "X-AI-Shifu-Caller-Agent": family,
                    "X-AI-Shifu-Caller-Agent-Name": name,
                })
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
        self.assert_usage_headers({
            **EXPECTED_METADATA,
            "X-AI-Shifu-Caller-Agent": "unknown",
            "X-AI-Shifu-Caller-Agent-Name": "Unknown Agent",
        })

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
            headers = self.get.call_args.kwargs["headers"]
            observed.append((headers["X-AI-Shifu-Caller-Agent"], headers["X-AI-Shifu-Caller-Agent-Name"]))

        with mock.patch.object(cli, "cmd_list", side_effect=request):
            self.run_cli("list")
            os.environ.clear()
            os.environ["SAND_AGENT"] = "1"
            os.environ["CURSOR_AGENT"] = "1"
            self.run_cli("list")
            os.environ.clear()
            self.run_cli("list")
        self.assertEqual(observed, [("codex", "Codex"), ("grok-bot", "Grok Bot"), ("unknown", "Unknown Agent")])
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
        update.assert_called_once_with()
        self.version.assert_not_called()


if __name__ == "__main__":
    unittest.main()
