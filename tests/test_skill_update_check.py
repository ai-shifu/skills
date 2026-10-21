from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = (
    REPO_ROOT / "skills" / "ai-shifu-course-creator" / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

import skill_update_check  # noqa: E402


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
        url: str = skill_update_check.MANIFEST_URL,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}
        self.url = url
        self.closed = False

    def close(self):
        self.closed = True

    def iter_content(self, chunk_size: int):
        for start in range(0, len(self.body), chunk_size):
            yield self.body[start : start + chunk_size]


class SkillUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = {
            "schema_version": 1,
            "skill_name": "ai-shifu-course-creator",
            "latest": "1.10.0",
            "min_supported": "1.0.0",
            "notes": "A safe update note",
            "published_at": "2026-07-12T00:00:00Z",
            "update_url": "https://github.com/ai-shifu/skills",
        }
        self.release = {
            "tag_name": "v1.10.0",
            "draft": False,
            "prerelease": False,
            "body": "A safe update note",
            "published_at": "2026-07-12T00:00:00Z",
            "html_url": "https://github.com/ai-shifu/skills/releases/tag/v1.10.0",
        }

    def test_parse_semver_compares_integer_segments(self):
        self.assertGreater(
            skill_update_check.parse_semver("1.10.0"),
            skill_update_check.parse_semver("1.9.0"),
        )
        self.assertIsNone(skill_update_check.parse_semver("v1.0.0"))
        self.assertIsNone(skill_update_check.parse_semver("1.0"))

    def test_manifest_rejects_impossible_required_update(self):
        broken = json.loads(json.dumps(self.manifest))
        broken["min_supported"] = "1.11.0"
        with self.assertRaises(skill_update_check.ManifestError):
            skill_update_check.validate_manifest(broken)

    def test_development_manifest_accepts_old_optional_fields(self):
        self.assertEqual(skill_update_check.validate_manifest(self.manifest), self.manifest)
        legacy = dict(self.manifest, check_interval_hours=2)
        self.assertEqual(skill_update_check.validate_manifest(legacy), legacy)

    def test_update_decision_uses_global_latest(self):
        manifest = skill_update_check.validate_manifest(self.manifest)
        latest = skill_update_check.determine_update(
            "1.10.0", manifest, source="network"
        )
        recommended = skill_update_check.determine_update(
            "1.9.0", manifest, source="network"
        )
        self.assertEqual(latest["status"], "latest")
        self.assertEqual(recommended["status"], "update_recommended")

    def test_update_decision_requires_old_unsupported_version(self):
        manifest = skill_update_check.validate_manifest(self.manifest)
        result = skill_update_check.determine_update(
            "0.9.9", manifest, source="network"
        )
        self.assertEqual(result["status"], "update_required")

    def test_stable_github_release_uses_tag_version_and_release_page(self):
        manifest = skill_update_check.validate_github_release(self.release)
        self.assertEqual(manifest["skill_name"], "ai-shifu-course-creator")
        self.assertEqual(manifest["latest"], "1.10.0")
        self.assertEqual(manifest["min_supported"], "0.0.0")
        self.assertEqual(manifest["notes"], self.release["body"])
        self.assertEqual(manifest["published_at"], self.release["published_at"])
        self.assertEqual(manifest["update_url"], self.release["html_url"])
        result = skill_update_check.determine_update("0.9.9", manifest, source="network")
        self.assertEqual(result["status"], "update_recommended")

    def test_github_release_requires_explicit_stable_public_flags(self):
        for flag in ("draft", "prerelease"):
            for value in (True, None, 0, 1, "false"):
                with self.subTest(flag=flag, value=value):
                    release = dict(self.release, **{flag: value})
                    with self.assertRaises(skill_update_check.ManifestError):
                        skill_update_check.validate_github_release(release)
            with self.subTest(flag=flag, missing=True):
                release = dict(self.release)
                del release[flag]
                with self.assertRaises(skill_update_check.ManifestError):
                    skill_update_check.validate_github_release(release)

    def test_github_release_rejects_noncanonical_or_preview_tags(self):
        for tag in (
            "1.10.0", "v1.10", "v1.10.0-beta.1", "v01.10.0",
            "preview-v1.10.0-deadbeef", None, 110,
        ):
            with self.subTest(tag=tag):
                release = dict(self.release, tag_name=tag)
                with self.assertRaises(skill_update_check.ManifestError):
                    skill_update_check.validate_github_release(release)

    def test_github_release_requires_matching_official_release_page(self):
        for url in (
            "http://github.com/ai-shifu/skills/releases/tag/v1.10.0",
            "https://attacker.example/ai-shifu/skills/releases/tag/v1.10.0",
            "https://github.com/another/skills/releases/tag/v1.10.0",
            "https://github.com/ai-shifu/skills/releases/tag/v1.9.0",
            "https://github.com/ai-shifu/skills/releases/tag/v1.10.0?download=1",
            "https://github.com/ai-shifu/skills/releases/tag/v1.10.0#changes",
            None,
        ):
            with self.subTest(url=url):
                release = dict(self.release, html_url=url)
                with self.assertRaises(skill_update_check.ManifestError):
                    skill_update_check.validate_github_release(release)

    def test_github_release_allows_empty_notes_and_bounds_long_notes(self):
        empty = skill_update_check.validate_github_release(dict(self.release, body=None))
        self.assertEqual(empty["notes"], "")
        long_notes = "Release change\n" * 100
        manifest = skill_update_check.validate_github_release(
            dict(self.release, body=long_notes)
        )
        self.assertTrue(manifest["notes"].startswith("Release change"))
        self.assertLessEqual(len(manifest["notes"]), skill_update_check.MAX_NOTES_CHARS)
        skill_update_check.validate_manifest(manifest)

    def test_github_release_rejects_invalid_timestamp_or_notes(self):
        for change in ({"published_at": None}, {"published_at": "yesterday"}, {"body": {}}):
            with self.subTest(change=change):
                with self.assertRaises(skill_update_check.ManifestError):
                    skill_update_check.validate_github_release(dict(self.release, **change))

    def changing_responses(self, *, allow_loopback):
        manifest_url = (
            "http://127.0.0.1:8088/skill-manifests/test.json"
            if allow_loopback else skill_update_check.MANIFEST_URL
        )
        responses = []
        for version in ("1.10.0", "1.11.0"):
            payload = (
                dict(self.manifest, latest=version)
                if allow_loopback else dict(
                    self.release,
                    tag_name=f"v{version}",
                    html_url=f"https://github.com/ai-shifu/skills/releases/tag/v{version}",
                )
            )
            responses.append(FakeResponse(
                status_code=200,
                body=json.dumps(payload).encode("utf-8"),
                headers={"ETag": f'"v{version}"'},
                url=manifest_url,
            ))
        return manifest_url, responses

    def test_each_fetch_reads_current_remote_version_without_disk_access(self):
        for allow_loopback in (False, True):
            with self.subTest(allow_loopback=allow_loopback):
                manifest_url, responses = self.changing_responses(allow_loopback=allow_loopback)
                get = mock.Mock(side_effect=responses)
                with mock.patch.object(
                    Path, "open", side_effect=AssertionError("fetch must not read or write files"),
                ) as opened:
                    results = [
                        skill_update_check.fetch_manifest(
                            manifest_url=manifest_url,
                            allow_loopback=allow_loopback,
                            http_get=get,
                        )
                        for _ in range(2)
                    ]
                self.assertEqual(
                    [(manifest["latest"], source) for manifest, source in results],
                    [("1.10.0", "network"), ("1.11.0", "network")],
                )
                self.assertEqual(get.call_count, 2)
                for call in get.call_args_list:
                    self.assertEqual(call.args, (manifest_url,))
                    self.assertEqual(call.kwargs["headers"], {
                        "Accept": "application/json" if allow_loopback else "application/vnd.github+json",
                    })
                self.assertTrue(all(response.closed for response in responses))
                opened.assert_not_called()

    def test_check_reads_only_skill_metadata_in_read_only_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_md = Path(tmp) / "SKILL.md"
            skill_md.write_text(
                "---\nname: ai-shifu-course-creator\nversion: 1.10.0\n---\n",
                encoding="utf-8",
            )
            old_files = [Path(tmp) / name for name in (".update-check.json", ".update-check.dev.json")]
            for old_file in old_files:
                old_file.write_text('{"latest":"9.0.0","etag":"old"}', encoding="utf-8")
            original_open = Path.open

            def read_skill_only(path, mode="r", *args, **kwargs):
                self.assertEqual(path, skill_md, "only installed Skill metadata may be read")
                if mode != "r":
                    raise PermissionError("read-only installation")
                return original_open(path, mode, *args, **kwargs)

            for allow_loopback in (False, True):
                with self.subTest(allow_loopback=allow_loopback):
                    manifest_url, responses = self.changing_responses(allow_loopback=allow_loopback)
                    get = mock.Mock(side_effect=responses)
                    with (
                        mock.patch.object(Path, "open", autospec=True, side_effect=read_skill_only) as opened,
                        mock.patch.object(Path, "write_text", side_effect=PermissionError("read-only")) as written,
                        mock.patch.object(Path, "mkdir", side_effect=PermissionError("read-only")) as mkdir,
                    ):
                        results = [
                            skill_update_check.check_for_update(
                                skill_md=skill_md,
                                manifest_url=manifest_url,
                                allow_loopback=allow_loopback,
                                http_get=get,
                            )
                            for _ in range(2)
                        ]
                    self.assertEqual(
                        [(result["status"], result["latest"], result["source"]) for result in results],
                        [("latest", "1.10.0", "network"), ("update_recommended", "1.11.0", "network")],
                    )
                    self.assertEqual(get.call_count, 2)
                    self.assertEqual(opened.call_count, 2)
                    written.assert_not_called()
                    mkdir.assert_not_called()
                    self.assertTrue(all(response.closed for response in responses))
            self.assertEqual(set(Path(tmp).iterdir()), {skill_md, *old_files})
            for old_file in old_files:
                self.assertEqual(old_file.read_text(encoding="utf-8"), '{"latest":"9.0.0","etag":"old"}')

    def test_non_200_responses_are_rejected_without_reading_body_and_closed(self):
        for status in (304, 404, 429, 500):
            with self.subTest(status=status):
                response = FakeResponse(status_code=status)
                response.iter_content = mock.Mock(side_effect=AssertionError("do not read failed response"))
                with self.assertRaises(skill_update_check.ManifestError):
                    skill_update_check.fetch_manifest(http_get=mock.Mock(return_value=response))
                response.iter_content.assert_not_called()
                self.assertTrue(response.closed)

    def test_untrusted_redirect_is_rejected_and_closed(self):
        for allow_loopback in (False, True):
            with self.subTest(allow_loopback=allow_loopback):
                manifest_url, responses = self.changing_responses(allow_loopback=allow_loopback)
                response = responses[0]
                response.url = "https://attacker.example/manifest.json"
                with self.assertRaises(skill_update_check.ManifestError):
                    skill_update_check.fetch_manifest(
                        manifest_url=manifest_url,
                        allow_loopback=allow_loopback,
                        http_get=mock.Mock(return_value=response),
                    )
                self.assertTrue(response.closed)

    def test_untrusted_sources_are_rejected_before_network_access(self):
        for manifest_url, allow_loopback in (
            ("https://attacker.example/manifest.json", False),
            ("http://api.github.com/repos/ai-shifu/skills/releases/latest", False),
            ("http://127.0.0.1:8088/manifest.json", False),
            ("https://attacker.example/manifest.json", True),
            ("http://user:secret@127.0.0.1/manifest.json", True),
            ("file://localhost/manifest.json", True),
        ):
            with self.subTest(manifest_url=manifest_url, allow_loopback=allow_loopback):
                get = mock.Mock(side_effect=AssertionError("untrusted source must not be requested"))
                with self.assertRaises(skill_update_check.ManifestError):
                    skill_update_check.fetch_manifest(
                        manifest_url=manifest_url, allow_loopback=allow_loopback, http_get=get,
                    )
                get.assert_not_called()

    def test_oversized_or_invalid_response_is_rejected_and_closed(self):
        valid_body = json.dumps(self.release).encode("utf-8")
        for body, headers in (
            (valid_body, {"Content-Length": str(skill_update_check.MAX_MANIFEST_BYTES + 1)}),
            (valid_body, {"Content-Length": "invalid"}),
            (b"x" * (skill_update_check.MAX_MANIFEST_BYTES + 1), {}),
            (b"\xff", {}),
            (b"{", {}),
        ):
            with self.subTest(body_size=len(body), headers=headers):
                response = FakeResponse(status_code=200, body=body, headers=headers)
                with self.assertRaises(skill_update_check.ManifestError):
                    skill_update_check.fetch_manifest(http_get=mock.Mock(return_value=response))
                self.assertTrue(response.closed)

    def test_check_is_fail_open_on_network_error_or_rejected_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_md = Path(tmp) / "SKILL.md"
            skill_md.write_text("---\nname: Test\nversion: 1.0.0\n---\n", encoding="utf-8")
            not_modified = FakeResponse(status_code=304)
            for get in (
                mock.Mock(side_effect=RuntimeError("offline")),
                mock.Mock(return_value=not_modified),
            ):
                with self.subTest(get=get):
                    result = skill_update_check.check_for_update(skill_md=skill_md, http_get=get)
                    self.assertEqual(result, {"status": "check_skipped", "source": "none"})
                    get.assert_called_once()
            self.assertTrue(not_modified.closed)

    def test_installed_skill_reads_supported_nested_version_metadata(self):
        skill_md = REPO_ROOT / "skills" / "ai-shifu-course-creator" / "SKILL.md"
        metadata = skill_update_check.read_skill_metadata(skill_md)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["name"], "ai-shifu-course-creator")
        self.assertRegex(
            metadata["version"],
            r"\A(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z",
        )
        self.assertEqual(metadata["version_management"], "standalone")

    def test_nested_plugin_managed_skill_skips_without_network(self):
        def unexpected_get(*_args, **_kwargs):
            raise AssertionError("plugin-managed skill must not request manifest")

        with tempfile.TemporaryDirectory() as tmp:
            skill_md = Path(tmp) / "SKILL.md"
            skill_md.write_text(
                "---\nname: Test\nmetadata:\n"
                "  version: 1.0.0\n  version_management: plugin\n---\n",
                encoding="utf-8",
            )
            result = skill_update_check.check_for_update(
                skill_md=skill_md,
                http_get=unexpected_get,
            )
            self.assertEqual(
                result,
                {"status": "check_skipped", "source": "plugin_managed"},
            )

    def test_plugin_managed_skill_skips_without_network(self):
        def unexpected_get(*_args, **_kwargs):
            raise AssertionError("plugin-managed skill must not request manifest")

        with tempfile.TemporaryDirectory() as tmp:
            skill_md = Path(tmp) / "SKILL.md"
            skill_md.write_text(
                (
                    "---\n"
                    "name: Test\n"
                    "version: 1.0.0\n"
                    "version_management: plugin\n"
                    "---\n"
                ),
                encoding="utf-8",
            )
            result = skill_update_check.check_for_update(
                skill_md=skill_md,
                http_get=unexpected_get,
            )
            self.assertEqual(
                result,
                {"status": "check_skipped", "source": "plugin_managed"},
            )

    def test_invalid_version_management_skips_without_network(self):
        def unexpected_get(*_args, **_kwargs):
            raise AssertionError("invalid version management must not request manifest")

        with tempfile.TemporaryDirectory() as tmp:
            skill_md = Path(tmp) / "SKILL.md"
            skill_md.write_text(
                (
                    "---\n"
                    "name: Test\n"
                    "version: 1.0.0\n"
                    "version_management: mystery\n"
                    "---\n"
                ),
                encoding="utf-8",
            )
            result = skill_update_check.check_for_update(
                skill_md=skill_md,
                http_get=unexpected_get,
            )
            self.assertEqual(
                result,
                {"status": "check_skipped", "source": "invalid_version_management"},
            )


class AutomaticUpdateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.skill_md = self.root / "SKILL.md"
        self.skill_md.write_text(
            "---\nname: ai-shifu-course-creator\nversion: 1.0.0\n---\n", encoding="utf-8",
        )
        self.state_dir = self.root / "user-state"
        self.now = datetime(2026, 10, 21, tzinfo=timezone.utc)
        self.check = mock.Mock(return_value=self.result())

    def result(self, latest="1.1.0", local="1.0.0"):
        manifest = skill_update_check.validate_github_release({
            "tag_name": f"v{latest}", "draft": False, "prerelease": False,
            "body": "A new release", "published_at": "2026-10-20T00:00:00Z",
            "html_url": f"https://github.com/ai-shifu/skills/releases/tag/v{latest}",
        })
        return skill_update_check.determine_update(local, manifest, source="network")

    def call(self, seconds=0, **kwargs):
        return skill_update_check.automatic_check_for_update(
            self.state_dir, skill_md=self.skill_md,
            now=self.now + timedelta(seconds=seconds), run_check=self.check, **kwargs,
        )

    def state_path(self):
        paths = list((self.state_dir / "update-check").glob("*.json"))
        self.assertEqual(len(paths), 1)
        return paths[0]

    def state(self):
        return json.loads(self.state_path().read_text(encoding="utf-8"))

    def test_success_throttles_at_24_hour_boundary_and_notifies_each_version_once(self):
        self.assertEqual(self.call(), self.result())
        self.assertIsNone(self.call(86399))
        self.check.assert_called_once_with(skill_md=self.skill_md)
        self.assertIsNone(self.call(86400))
        self.assertEqual(self.check.call_count, 2)
        self.check.return_value = self.result("1.2.0")
        self.assertEqual(self.call(172800), self.result("1.2.0"))
        self.check.return_value = self.result("1.1.0")
        self.assertIsNone(self.call(259200))
        self.assertEqual(self.state()["notified_versions"], ["1.1.0", "1.2.0"])

    def test_latest_result_also_throttles_without_suppressing_later_update(self):
        self.check.return_value = self.result("1.0.0")
        self.assertIsNone(self.call())
        self.assertIsNone(self.call(86399))
        self.check.assert_called_once()
        self.check.return_value = self.result()
        self.assertEqual(self.call(86400), self.result())
        self.assertEqual(self.check.call_count, 2)

    def test_installed_versions_have_independent_schedules_and_reminders(self):
        self.check.return_value = self.result("1.2.0")
        self.assertEqual(self.call(), self.result("1.2.0"))
        self.skill_md.write_text(
            "---\nname: ai-shifu-course-creator\nversion: 1.1.0\n---\n", encoding="utf-8",
        )
        self.check.return_value = self.result("1.2.0", local="1.1.0")
        self.assertEqual(self.call(1), self.result("1.2.0", local="1.1.0"))
        self.assertEqual(len(list((self.state_dir / "update-check").glob("*.json"))), 2)
        self.assertEqual(self.check.call_count, 2)
        self.skill_md.write_text(
            "---\nname: ai-shifu-course-creator\nversion: 1.0.0\n---\n", encoding="utf-8",
        )
        self.assertIsNone(self.call(2))
        self.assertEqual(self.check.call_count, 2)

    def test_plugin_or_invalid_metadata_never_creates_state_or_requests_network(self):
        for contents in (
            "---\nname: ai-shifu-course-creator\nversion: 1.0.0\nversion_management: plugin\n---\n",
            "---\nname: ai-shifu-course-creator\nmetadata:\n  version: 1.0.0\n  version_management: plugin\n---\n",
            "---\nname: ai-shifu-course-creator\nversion: broken\n---\n",
            "---\nname: other\nversion: 1.0.0\n---\n",
            "not frontmatter",
        ):
            with self.subTest(contents=contents):
                self.skill_md.write_text(contents, encoding="utf-8")
                self.assertIsNone(self.call())
                self.assertFalse(self.state_dir.exists())
                self.check.assert_not_called()

    def test_failure_retries_after_five_minutes_without_recording_success(self):
        self.check.return_value = {"status": "check_skipped", "source": "none"}
        self.assertIsNone(self.call())
        self.assertEqual(self.state()["last_success_at"], 0)
        self.assertEqual(self.state()["notified_versions"], [])
        self.assertIsNone(self.call(299))
        self.check.assert_called_once()
        self.check.return_value = self.result()
        self.assertEqual(self.call(300), self.result())
        self.assertEqual(self.check.call_count, 2)

    def test_server_wait_is_never_shortened_to_local_failure_delay(self):
        self.check.return_value = {
            "result": {"status": "check_skipped", "source": "none"},
            "retry_after_seconds": 900,
        }
        self.assertIsNone(self.call())
        self.assertIsNone(self.call(899))
        self.check.assert_called_once()
        self.check.return_value = self.result()
        self.assertEqual(self.call(900), self.result())

    def test_rate_limit_headers_stay_internal_and_preserve_server_wait(self):
        for status, headers, expected in (
            (429, {"Retry-After": "900"}, 900),
            (403, {"Retry-After": format_datetime(self.now + timedelta(seconds=900), usegmt=True)}, 900),
            (403, {"X-RateLimit-Reset": str(self.now.timestamp() + 1200)}, 1200),
            (429, {"Retry-After": "invalid"}, 0),
        ):
            with self.subTest(status=status, headers=headers):
                response = FakeResponse(status_code=status, headers=headers)
                with (
                    mock.patch.object(skill_update_check.requests, "get", return_value=response),
                    mock.patch.object(skill_update_check, "datetime", wraps=datetime) as clock,
                ):
                    clock.now.return_value = self.now
                    outcome = skill_update_check._automatic_check_worker(self.skill_md)
                self.assertEqual(outcome["result"], {"status": "check_skipped", "source": "none"})
                self.assertEqual(outcome["retry_after_seconds"], expected)
                self.assertTrue(response.closed)

    def test_corrupt_identity_and_future_timestamps_recover(self):
        self.call()
        state_path = self.state_path()
        original = self.state()
        self.check.return_value = self.result("1.2.0")
        corrupt = (
            "broken JSON", "[]",
            json.dumps(dict(original, source="https://other.example")),
            json.dumps(dict(original, schema_version=True)),
            json.dumps(dict(original, last_success_at=self.now.timestamp() + 1000)),
            json.dumps(dict(original, last_attempt_at=self.now.timestamp() + 1000)),
            json.dumps(dict(original, retry_after_seconds=float("nan"))),
            json.dumps(dict(original, last_attempt_at=10 ** 1000)),
        )
        for contents in corrupt:
            with self.subTest(contents=contents[:100]):
                state_path.write_text(contents, encoding="utf-8")
                self.assertEqual(self.call(1), self.result("1.2.0"))
                self.assertEqual(self.state()["source"], skill_update_check.MANIFEST_URL)

    def test_future_times_recover_schedule_without_repeating_a_seen_version(self):
        self.call()
        state = self.state()
        state["last_attempt_at"] = state["last_success_at"] = self.now.timestamp() + 1000
        self.state_path().write_text(json.dumps(state), encoding="utf-8")
        self.assertIsNone(self.call(1))
        self.assertEqual(self.check.call_count, 2)
        self.assertEqual(self.state()["notified_versions"], ["1.1.0"])
        self.assertEqual(self.state()["last_success_at"], self.now.timestamp() + 1)

    def test_untrusted_redirect_cannot_set_server_retry_delay(self):
        response = FakeResponse(
            status_code=403, headers={"Retry-After": "999999"},
            url="https://attacker.example/manifest.json",
        )
        with mock.patch.object(skill_update_check.requests, "get", return_value=response):
            outcome = skill_update_check._automatic_check_worker(self.skill_md)
        self.assertEqual(outcome, {
            "result": {"status": "check_skipped", "source": "none"}, "retry_after_seconds": 0,
        })
        self.assertTrue(response.closed)

    def test_invalid_worker_results_do_not_suppress_a_later_valid_check(self):
        for index, change in enumerate((
            {"local_version": "9.0.0"}, {"skill_name": "other"}, {"source": "cache"},
            {"latest": "invalid"}, {"status": "latest"}, {"update_url": "https://attacker.example"},
            {"min_supported": "9.0.0"},
        )):
            with self.subTest(change=change):
                directory = self.state_dir / str(index)
                check = mock.Mock(return_value=dict(self.result(), **change))
                self.assertIsNone(skill_update_check.automatic_check_for_update(
                    directory, skill_md=self.skill_md, now=self.now, run_check=check,
                ))
                check.return_value = self.result()
                self.assertEqual(skill_update_check.automatic_check_for_update(
                    directory, skill_md=self.skill_md, now=self.now + timedelta(seconds=300), run_check=check,
                ), self.result())

    def test_write_failure_skips_network_or_notification_and_preserves_short_backoff(self):
        with mock.patch.object(skill_update_check.os, "replace", side_effect=PermissionError("read-only")):
            self.assertIsNone(self.call())
        self.check.assert_not_called()
        self.assertEqual({path.suffix for path in (self.state_dir / "update-check").iterdir()}, {".lock"})
        write = skill_update_check._write_automatic_state
        writes = 0

        def fail_final_write(path, state):
            nonlocal writes
            writes += 1
            if writes == 2:
                raise PermissionError("disk unavailable")
            return write(path, state)

        with mock.patch.object(skill_update_check, "_write_automatic_state", side_effect=fail_final_write):
            self.assertIsNone(self.call())
        self.check.assert_called_once()
        self.assertEqual(self.state()["last_success_at"], 0)
        self.assertIsNone(self.call(1))
        self.check.assert_called_once()

    def test_state_is_private_atomic_and_does_not_change_the_installation(self):
        self.assertEqual(self.call(), self.result())
        self.assertEqual(set(self.root.iterdir()), {self.skill_md, self.state_dir})
        directory = self.state_dir / "update-check"
        self.assertEqual({path.suffix for path in directory.iterdir()}, {".json", ".lock"})
        if os.name != "nt":
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            for path in directory.iterdir():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(set(self.state()), {
            "schema_version", "source", "local_version", "last_attempt_at", "last_success_at",
            "retry_after_seconds", "notified_versions",
        })

    def test_production_lookup_timeout_is_captured_and_releases_lock_for_retry(self):
        with mock.patch.object(
            skill_update_check.subprocess, "run", side_effect=subprocess.TimeoutExpired("worker", 2),
        ) as run:
            self.assertIsNone(skill_update_check.automatic_check_for_update(
                self.state_dir, skill_md=self.skill_md, now=self.now,
            ))
            self.assertEqual(run.call_args.kwargs["timeout"], 2)
            self.assertTrue(run.call_args.kwargs["capture_output"])
            self.assertIn("-B", run.call_args.args[0])
            self.assertIsNone(self.call(299))
            self.check.assert_not_called()
        self.assertEqual(self.call(300), self.result())

    def test_worker_output_is_parsed_without_reaching_parent_stdout(self):
        outcome = {"result": self.result(), "retry_after_seconds": 0}
        with mock.patch.object(skill_update_check.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 0, stdout=json.dumps(outcome), stderr="private diagnostics",
        )):
            self.assertEqual(skill_update_check._run_automatic_check(skill_md=self.skill_md), outcome)

    def test_real_subprocess_timeout_finishes_without_waiting_for_slow_worker(self):
        worker = self.root / "slow-worker.py"
        worker.write_text("import time\ntime.sleep(10)\n", encoding="utf-8")
        popen = subprocess.Popen
        processes = []

        def start(*args, **kwargs):
            process = popen(*args, **kwargs)
            processes.append(process)
            return process

        started = time.monotonic()
        with (
            mock.patch.object(skill_update_check, "__file__", str(worker)),
            mock.patch.object(skill_update_check, "AUTOMATIC_LOOKUP_TIMEOUT_SECONDS", 0.2),
            mock.patch.object(skill_update_check.subprocess, "Popen", side_effect=start),
        ):
            self.assertIsNone(skill_update_check.automatic_check_for_update(
                self.state_dir, skill_md=self.skill_md, now=self.now,
            ))
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll(), "timed-out worker must be terminated")
        self.assertEqual(self.state()["last_success_at"], 0)
        self.assertEqual(self.call(300), self.result())

    def test_concurrent_processes_do_not_duplicate_lookup_or_reminder(self):
        worker = r'''
import json, sys, time
from datetime import datetime
from pathlib import Path
import skill_update_check as updates
root, label, result = Path(sys.argv[1]), sys.argv[2], json.loads(sys.argv[3])
def check(**kwargs):
    (root / (label + '-checked')).touch()
    if label == 'owner':
        deadline = time.monotonic() + 15
        while not (root / 'release').exists():
            if time.monotonic() > deadline:
                raise RuntimeError('test gate timed out')
            time.sleep(0.01)
    return result
print(json.dumps(updates.automatic_check_for_update(
    root / 'user-state', skill_md=root / 'SKILL.md',
    now=datetime.fromisoformat('2026-10-21T00:00:00+00:00'), run_check=check,
)))
'''
        command = [sys.executable, "-B", "-c", worker, str(self.root)]
        env = {**os.environ, "PYTHONPATH": str(SCRIPT_DIR)}
        owner = subprocess.Popen(
            [*command, "owner", json.dumps(self.result())], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            deadline = time.monotonic() + 8
            while not (self.root / "owner-checked").exists():
                if time.monotonic() > deadline:
                    self.fail("automatic check owner did not acquire the lock")
                time.sleep(0.01)
            competitor = subprocess.run(
                [*command, "competitor", json.dumps(self.result())], env=env,
                capture_output=True, text=True, timeout=8, check=True,
            )
            self.assertIsNone(json.loads(competitor.stdout))
            self.assertFalse((self.root / "competitor-checked").exists())
            (self.root / "release").touch()
            stdout, stderr = owner.communicate(timeout=8)
            self.assertEqual(owner.returncode, 0, stderr)
            self.assertEqual(json.loads(stdout), self.result())
            self.assertIsNone(self.call(1))
            self.check.assert_not_called()
        finally:
            if owner.poll() is None:
                owner.kill()
                owner.communicate(timeout=8)


if __name__ == "__main__":
    unittest.main()
