from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = (
    REPO_ROOT / "skills" / "ai-shifu-course-creator" / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

import usage_tracker  # noqa: E402


def fake_jwt(payload: dict) -> str:
    body = (
        base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"header.{body}.signature"


class DetectAgentTests(unittest.TestCase):
    def test_generic_ai_agent_wins(self) -> None:
        env = {"AI_AGENT": "claude-code_2-1-215_agent", "CLAUDECODE": "1"}
        with mock.patch.dict(usage_tracker.os.environ, env, clear=True):
            self.assertEqual(
                usage_tracker.detect_agent(), "claude-code_2-1-215_agent"
            )

    def test_claude_code_marker_with_entrypoint(self) -> None:
        env = {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli"}
        with mock.patch.dict(usage_tracker.os.environ, env, clear=True):
            self.assertEqual(usage_tracker.detect_agent(), "claude-code/cli")

    def test_opencode_marker(self) -> None:
        env = {"OPENCODE": "1"}
        with mock.patch.dict(usage_tracker.os.environ, env, clear=True):
            self.assertEqual(usage_tracker.detect_agent(), "opencode")

    def test_process_walk_fallback(self) -> None:
        with mock.patch.dict(usage_tracker.os.environ, {}, clear=True), \
                mock.patch.object(
                    usage_tracker,
                    "_walk_parent_process_names",
                    return_value=iter(["zsh", "workbuddy-helper"]),
                ):
            self.assertEqual(usage_tracker.detect_agent(), "proc:workbuddy")

    def test_unknown_when_no_signal(self) -> None:
        with mock.patch.dict(usage_tracker.os.environ, {}, clear=True), \
                mock.patch.object(
                    usage_tracker,
                    "_walk_parent_process_names",
                    return_value=iter(["zsh", "launchd"]),
                ):
            self.assertEqual(usage_tracker.detect_agent(), "unknown")


class DistinctIdTests(unittest.TestCase):
    def test_prefers_platform_user_id_from_env_token(self) -> None:
        token = fake_jwt({"user_id": "user-123", "time_stamp": 1})
        with mock.patch.dict(
            usage_tracker.os.environ, {"SHIFU_TOKEN": token}, clear=True
        ):
            self.assertEqual(usage_tracker.distinct_id(), "u:user-123")

    def test_truncates_to_umami_limit(self) -> None:
        token = fake_jwt({"user_id": "x" * 80, "time_stamp": 1})
        with mock.patch.dict(
            usage_tracker.os.environ, {"SHIFU_TOKEN": token}, clear=True
        ):
            self.assertEqual(len(usage_tracker.distinct_id()), 50)

    def test_anonymous_fallback_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            id_file = Path(tmp) / "analytics-id"
            with mock.patch.dict(
                usage_tracker.os.environ, {}, clear=True
            ), mock.patch.object(
                usage_tracker, "ANALYTICS_ID_FILE", id_file
            ), mock.patch.object(
                usage_tracker, "ENV_FILE", Path(tmp) / "missing.env"
            ):
                first = usage_tracker.distinct_id()
                second = usage_tracker.distinct_id()
        self.assertTrue(first.startswith("a:"))
        self.assertEqual(first, second)

    def test_malformed_token_falls_back_to_anonymous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            id_file = Path(tmp) / "analytics-id"
            with mock.patch.dict(
                usage_tracker.os.environ,
                {"SHIFU_TOKEN": "not-a-jwt"},
                clear=True,
            ), mock.patch.object(
                usage_tracker, "ANALYTICS_ID_FILE", id_file
            ):
                self.assertTrue(
                    usage_tracker.distinct_id().startswith("a:")
                )


class UserAgentTests(unittest.TestCase):
    def test_shape_passes_isbot_conventions(self) -> None:
        ua = usage_tracker._user_agent("claude-code")
        self.assertTrue(ua.startswith("Mozilla/5.0 ("))
        self.assertIn("AIShifuSkill/", ua)
        self.assertIn("claude-code", ua)
        for marker in ("python-requests", "curl", "bot"):
            self.assertNotIn(marker, ua.lower())


class TrackTests(unittest.TestCase):
    def _env(self, **extra: str) -> dict[str, str]:
        env = {"AISHIFU_UMAMI_WEBSITE_ID": "site-1"}
        env.update(extra)
        return env

    def test_sends_event_with_custom_user_agent(self) -> None:
        with mock.patch.dict(
            usage_tracker.os.environ, self._env(AI_AGENT="opencode"),
            clear=True,
        ), mock.patch.object(
            usage_tracker, "distinct_id", return_value="u:user-123"
        ), mock.patch.object(
            usage_tracker.requests, "post"
        ) as post:
            usage_tracker.track("cli_publish", {"extra": "1"})

        self.assertEqual(post.call_count, 1)
        args, kwargs = post.call_args
        self.assertEqual(args[0], usage_tracker.UMAMI_URL)
        body = kwargs["json"]
        self.assertEqual(body["type"], "event")
        payload = body["payload"]
        self.assertEqual(payload["website"], "site-1")
        self.assertEqual(payload["name"], "cli_publish")
        self.assertEqual(payload["id"], "u:user-123")
        self.assertEqual(payload["tag"], "opencode")
        self.assertEqual(payload["data"]["agent"], "opencode")
        self.assertEqual(payload["data"]["extra"], "1")
        self.assertTrue(
            kwargs["headers"]["User-Agent"].startswith("Mozilla/5.0 (")
        )
        self.assertEqual(kwargs["timeout"], usage_tracker.REQUEST_TIMEOUT)

    def test_no_request_without_website_id(self) -> None:
        with mock.patch.dict(
            usage_tracker.os.environ, {}, clear=True
        ), mock.patch.object(usage_tracker.requests, "post") as post:
            usage_tracker.track("cli_list")
        post.assert_not_called()

    def test_opt_out_disables_tracking(self) -> None:
        with mock.patch.dict(
            usage_tracker.os.environ,
            self._env(AISHIFU_ANALYTICS="off"),
            clear=True,
        ), mock.patch.object(usage_tracker.requests, "post") as post:
            usage_tracker.track("cli_list")
        post.assert_not_called()

    def test_network_failure_is_swallowed(self) -> None:
        with mock.patch.dict(
            usage_tracker.os.environ, self._env(), clear=True
        ), mock.patch.object(
            usage_tracker, "distinct_id", return_value="a:x"
        ), mock.patch.object(
            usage_tracker.requests,
            "post",
            side_effect=OSError("network down"),
        ):
            usage_tracker.track("cli_list")  # must not raise


if __name__ == "__main__":
    unittest.main()
