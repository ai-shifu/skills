from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = (
    REPO_ROOT / "skills" / "ai-shifu-course-creator" / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

import skill_update  # noqa: E402


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
        url: str = skill_update.MANIFEST_URL,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}
        self.url = url

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
            "check_interval_hours": 2,
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
        self.now = datetime(2026, 7, 12, 8, 0, tzinfo=timezone.utc)

    def test_parse_semver_compares_integer_segments(self):
        self.assertGreater(
            skill_update.parse_semver("1.10.0"),
            skill_update.parse_semver("1.9.0"),
        )
        self.assertIsNone(skill_update.parse_semver("v1.0.0"))
        self.assertIsNone(skill_update.parse_semver("1.0"))

    def test_manifest_rejects_impossible_forced_update(self):
        broken = json.loads(json.dumps(self.manifest))
        broken["min_supported"] = "1.11.0"
        with self.assertRaises(skill_update.ManifestError):
            skill_update.validate_manifest(broken)

    def test_update_decision_uses_global_latest(self):
        manifest = skill_update.validate_manifest(self.manifest)
        latest = skill_update.determine_update(
            "1.10.0", manifest, source="network"
        )
        recommended = skill_update.determine_update(
            "1.9.0", manifest, source="network"
        )
        self.assertEqual(latest["status"], "latest")
        self.assertEqual(recommended["status"], "update_recommended")

    def test_update_decision_requires_old_unsupported_version(self):
        manifest = skill_update.validate_manifest(self.manifest)
        result = skill_update.determine_update(
            "0.9.9", manifest, source="network"
        )
        self.assertEqual(result["status"], "update_required")

    def test_stable_github_release_uses_tag_version_and_release_page(self):
        manifest = skill_update.validate_github_release(self.release)
        self.assertEqual(manifest["skill_name"], "ai-shifu-course-creator")
        self.assertEqual(manifest["latest"], "1.10.0")
        self.assertEqual(manifest["min_supported"], "0.0.0")
        self.assertEqual(manifest["notes"], self.release["body"])
        self.assertEqual(manifest["published_at"], self.release["published_at"])
        self.assertEqual(manifest["update_url"], self.release["html_url"])
        self.assertEqual(manifest["check_interval_hours"], 24)
        result = skill_update.determine_update("0.9.9", manifest, source="network")
        self.assertEqual(result["status"], "update_recommended")

    def test_github_release_requires_explicit_stable_public_flags(self):
        for flag in ("draft", "prerelease"):
            for value in (True, None, 0, 1, "false"):
                with self.subTest(flag=flag, value=value):
                    release = dict(self.release, **{flag: value})
                    with self.assertRaises(skill_update.ManifestError):
                        skill_update.validate_github_release(release)
            with self.subTest(flag=flag, missing=True):
                release = dict(self.release)
                del release[flag]
                with self.assertRaises(skill_update.ManifestError):
                    skill_update.validate_github_release(release)

    def test_github_release_rejects_noncanonical_or_preview_tags(self):
        for tag in (
            "1.10.0", "v1.10", "v1.10.0-beta.1", "v01.10.0",
            "preview-v1.10.0-deadbeef", None, 110,
        ):
            with self.subTest(tag=tag):
                release = dict(self.release, tag_name=tag)
                with self.assertRaises(skill_update.ManifestError):
                    skill_update.validate_github_release(release)

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
                with self.assertRaises(skill_update.ManifestError):
                    skill_update.validate_github_release(release)

    def test_github_release_allows_empty_notes_and_bounds_long_notes(self):
        empty = skill_update.validate_github_release(dict(self.release, body=None))
        self.assertEqual(empty["notes"], "")
        long_notes = "Release change\n" * 100
        manifest = skill_update.validate_github_release(
            dict(self.release, body=long_notes)
        )
        self.assertTrue(manifest["notes"].startswith("Release change"))
        self.assertLessEqual(len(manifest["notes"]), skill_update.MAX_NOTES_CHARS)
        skill_update.validate_manifest(manifest)

    def test_github_release_rejects_invalid_timestamp_or_notes(self):
        for change in ({"published_at": None}, {"published_at": "yesterday"}, {"body": {}}):
            with self.subTest(change=change):
                with self.assertRaises(skill_update.ManifestError):
                    skill_update.validate_github_release(dict(self.release, **change))

    def test_network_result_is_cached_and_reused(self):
        body = json.dumps(self.release).encode("utf-8")
        calls: list[dict[str, object]] = []

        def fake_get(_url, **kwargs):
            calls.append(kwargs)
            return FakeResponse(
                status_code=200,
                body=body,
                headers={"ETag": '"manifest-v1"'},
            )

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / ".update-check.json"
            manifest, source = skill_update.fetch_manifest(
                cache_file=cache,
                http_get=fake_get,
                now=self.now,
            )
            self.assertEqual(source, "network")
            self.assertEqual(manifest["latest"], "1.10.0")
            self.assertTrue(cache.is_file())
            self.assertEqual(
                json.loads(cache.read_text(encoding="utf-8"))["source_url"],
                "https://api.github.com/repos/ai-shifu/skills/releases/latest",
            )

            def unexpected_get(*_args, **_kwargs):
                raise AssertionError("fresh cache should avoid the network")

            cached, cached_source = skill_update.fetch_manifest(
                cache_file=cache,
                http_get=unexpected_get,
                now=self.now + timedelta(hours=1),
            )
            self.assertEqual(cached_source, "cache")
            self.assertEqual(cached, manifest)
            self.assertEqual(len(calls), 1)

    def test_force_revalidates_with_etag(self):
        body = json.dumps(self.release).encode("utf-8")
        seen_headers: list[dict[str, str]] = []

        def initial_get(_url, **_kwargs):
            return FakeResponse(
                status_code=200,
                body=body,
                headers={"ETag": '"manifest-v1"'},
            )

        def revalidate_get(_url, **kwargs):
            seen_headers.append(kwargs["headers"])
            return FakeResponse(status_code=304)

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / ".update-check.json"
            skill_update.fetch_manifest(
                cache_file=cache, http_get=initial_get, now=self.now
            )
            _manifest, source = skill_update.fetch_manifest(
                cache_file=cache,
                force=True,
                http_get=revalidate_get,
                now=self.now + timedelta(minutes=1),
            )
            self.assertEqual(source, "revalidated")
            self.assertEqual(seen_headers[0]["If-None-Match"], '"manifest-v1"')

    def test_cache_expires_after_manifest_interval(self):
        body = json.dumps(self.release).encode("utf-8")
        calls = 0

        def fake_get(_url, **_kwargs):
            nonlocal calls
            calls += 1
            return FakeResponse(status_code=200, body=body)

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / ".update-check.json"
            skill_update.fetch_manifest(
                cache_file=cache,
                http_get=fake_get,
                now=self.now,
            )
            _manifest, source = skill_update.fetch_manifest(
                cache_file=cache,
                http_get=fake_get,
                now=self.now + timedelta(hours=24, seconds=1),
            )
            self.assertEqual(source, "network")
            self.assertEqual(calls, 2)

    def test_legacy_and_other_source_caches_do_not_hide_github_release(self):
        for previous_source in (
            None,
            "https://ai-shifu.cn/skill-manifests/ai-shifu-course-creator.json",
            "http://127.0.0.1:8088/skill-manifests/test.json",
        ):
            with self.subTest(previous_source=previous_source):
                calls = []

                def fake_get(url, **kwargs):
                    calls.append((url, kwargs["headers"]))
                    return FakeResponse(
                        status_code=200,
                        body=json.dumps(self.release).encode("utf-8"),
                        headers={"ETag": '"github-release"'},
                    )

                with tempfile.TemporaryDirectory() as tmp:
                    cache = Path(tmp) / ".update-check.json"
                    cached = {
                        "checked_at": self.now.isoformat(),
                        "etag": '"old-website-manifest"',
                        "manifest": dict(self.manifest, latest="9.0.0"),
                    }
                    if previous_source is not None:
                        cached["source_url"] = previous_source
                    cache.write_text(json.dumps(cached), encoding="utf-8")
                    manifest, source = skill_update.fetch_manifest(
                        cache_file=cache,
                        http_get=fake_get,
                        now=self.now + timedelta(minutes=1),
                    )
                    self.assertEqual(source, "network")
                    self.assertEqual(manifest["latest"], "1.10.0")
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(
                        calls[0][0],
                        "https://api.github.com/repos/ai-shifu/skills/releases/latest",
                    )
                    self.assertNotIn("If-None-Match", calls[0][1])

    def test_cache_write_failure_does_not_discard_network_result(self):
        body = json.dumps(self.release).encode("utf-8")

        def fake_get(_url, **_kwargs):
            return FakeResponse(status_code=200, body=body)

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            skill_update, "_write_cache", side_effect=OSError("read-only install")
        ):
            manifest, source = skill_update.fetch_manifest(
                cache_file=Path(tmp) / "cache.json",
                http_get=fake_get,
                now=self.now,
            )
            self.assertEqual(source, "network")
            self.assertEqual(manifest["latest"], "1.10.0")

    def test_untrusted_redirect_is_rejected(self):
        body = json.dumps(self.release).encode("utf-8")

        def fake_get(_url, **_kwargs):
            return FakeResponse(
                status_code=200,
                body=body,
                url="https://attacker.example/manifest.json",
            )

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(skill_update.ManifestError):
                skill_update.fetch_manifest(
                    cache_file=Path(tmp) / "cache.json",
                    http_get=fake_get,
                    now=self.now,
                )

    def test_loopback_manifest_is_allowed_for_explicit_development(self):
        body = json.dumps(self.manifest).encode("utf-8")
        local_url = "http://127.0.0.1:8088/skill-manifests/test.json"
        requested_urls: list[str] = []

        def fake_get(url, **_kwargs):
            requested_urls.append(url)
            return FakeResponse(status_code=200, body=body, url=local_url)

        with tempfile.TemporaryDirectory() as tmp:
            manifest, source = skill_update.fetch_manifest(
                cache_file=Path(tmp) / "cache.json",
                manifest_url=local_url,
                allow_loopback=True,
                http_get=fake_get,
                now=self.now,
            )
            self.assertEqual(source, "network")
            self.assertEqual(manifest["latest"], "1.10.0")
            self.assertEqual(requested_urls, [local_url])

    def test_development_manifest_rejects_remote_hosts(self):
        def unexpected_get(*_args, **_kwargs):
            raise AssertionError("invalid development URL must not be requested")

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(skill_update.ManifestError):
                skill_update.fetch_manifest(
                    cache_file=Path(tmp) / "cache.json",
                    manifest_url="https://attacker.example/manifest.json",
                    allow_loopback=True,
                    http_get=unexpected_get,
                    now=self.now,
                )

    def test_check_is_fail_open_on_network_error(self):
        def failing_get(*_args, **_kwargs):
            raise RuntimeError("offline")

        with tempfile.TemporaryDirectory() as tmp:
            skill_md = Path(tmp) / "SKILL.md"
            skill_md.write_text(
                "---\nname: Test\nversion: 1.0.0\n---\n",
                encoding="utf-8",
            )
            result = skill_update.check_for_update(
                skill_md=skill_md,
                cache_file=Path(tmp) / "cache.json",
                http_get=failing_get,
                now=self.now,
            )
            self.assertEqual(result, {"status": "check_skipped", "source": "none"})

    def test_installed_skill_reads_supported_nested_version_metadata(self):
        skill_md = REPO_ROOT / "skills" / "ai-shifu-course-creator" / "SKILL.md"
        metadata = skill_update.read_skill_metadata(skill_md)
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
            result = skill_update.check_for_update(
                skill_md=skill_md,
                cache_file=Path(tmp) / "cache.json",
                http_get=unexpected_get,
                now=self.now,
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
            result = skill_update.check_for_update(
                skill_md=skill_md,
                cache_file=Path(tmp) / "cache.json",
                http_get=unexpected_get,
                now=self.now,
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
            result = skill_update.check_for_update(
                skill_md=skill_md,
                cache_file=Path(tmp) / "cache.json",
                http_get=unexpected_get,
                now=self.now,
            )
            self.assertEqual(
                result,
                {"status": "check_skipped", "source": "invalid_version_management"},
            )


if __name__ == "__main__":
    unittest.main()
