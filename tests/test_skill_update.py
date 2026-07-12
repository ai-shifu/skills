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

    def test_network_result_is_cached_and_reused(self):
        body = json.dumps(self.manifest).encode("utf-8")
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
        body = json.dumps(self.manifest).encode("utf-8")
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
        body = json.dumps(self.manifest).encode("utf-8")
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
                now=self.now + timedelta(hours=2, seconds=1),
            )
            self.assertEqual(source, "network")
            self.assertEqual(calls, 2)

    def test_cache_write_failure_does_not_discard_network_result(self):
        body = json.dumps(self.manifest).encode("utf-8")

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
        body = json.dumps(self.manifest).encode("utf-8")

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


if __name__ == "__main__":
    unittest.main()
