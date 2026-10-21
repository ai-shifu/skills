from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
