"""npm installations must advertise only releases available from npm."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/ai-shifu-course-creator/scripts"))
import skill_update_check as updates


class Response:
    def __init__(self, url, version="2.2.1", status=200):
        self.url, self.status_code, self.headers = url, status, {}
        self.content = json.dumps({"name": "@ai-shifu/cli", "version": version}).encode()

    def iter_content(self, chunk_size):
        yield self.content

    def close(self):
        pass


class NpmUpdateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.skill = self.root / "SKILL.md"
        self.skill.write_text("---\nname: ai-shifu-course-creator\nmetadata:\n  version: 2.2.1\n  version_management: standalone\n---\n")
        self.enterContext(mock.patch.dict(os.environ, {}, clear=True))
        self.marker = self.root / ".ai-shifu-cli.json"
        self.marker.write_text(json.dumps({"schema_version": 1, "distribution": "npm", "version": "2.2.1"}))

    def test_npm_install_does_not_advertise_an_unpublished_github_release(self):
        seen = []
        def get(url, **kwargs):
            seen.append(url)
            return Response(url)
        result = updates.check_for_update(skill_md=self.skill, http_get=get)
        self.assertEqual(result["status"], "latest")
        self.assertEqual(seen, [updates.NPM_MANIFEST_URL])
        self.assertEqual(result["update_url"], updates.NPM_PACKAGE_URL + "/v/2.2.1")

    def test_wrapper_uses_npm_even_without_a_synchronized_marker(self):
        self.marker.unlink()
        with mock.patch.dict(os.environ, {"AI_SHIFU_CLI_DISTRIBUTION": "npm"}):
            result = updates.check_for_update(skill_md=self.skill,
                http_get=lambda url, **kwargs: Response(url, version="2.3.0"))
        self.assertEqual(result["status"], "update_recommended")
        self.assertEqual(result["latest"], "2.3.0")

    def test_npm_lookup_failure_is_skipped_without_falling_back_to_github(self):
        for status in (404, 429, 500):
            with self.subTest(status=status):
                result = updates.check_for_update(skill_md=self.skill,
                    http_get=lambda url, **kwargs: Response(url, status=status))
                self.assertEqual(result["status"], "check_skipped")

    def test_npm_metadata_rejects_another_package_or_unstable_version(self):
        for raw in ({"name": "another", "version": "2.3.0"},
                    {"name": "@ai-shifu/cli", "version": "2.3.0-rc.1"}):
            with self.assertRaises(updates.ManifestError):
                updates.validate_npm_release(raw)

    def test_plugin_managed_installations_still_skip_networking(self):
        self.skill.write_text(self.skill.read_text().replace("standalone", "plugin"))
        get = mock.Mock(side_effect=AssertionError("networking must be skipped"))
        self.assertEqual(updates.check_for_update(skill_md=self.skill, http_get=get),
                         {"status": "check_skipped", "source": "plugin_managed"})

    def test_automatic_checks_accept_npm_links_and_have_separate_source_state(self):
        result = updates.determine_update("2.2.1", updates.validate_npm_release(
            {"name": "@ai-shifu/cli", "version": "2.3.0"}), source="network")
        kwargs = {"skill_md": self.skill, "now": datetime(2026, 11, 1, tzinfo=timezone.utc),
                  "run_check": lambda **_: {"result": result}}
        self.assertEqual(updates.automatic_check_for_update(self.root / "state", **kwargs), result)
        self.assertIsNone(updates.automatic_check_for_update(self.root / "state", **kwargs))
        self.marker.unlink()
        github = dict(result, update_url=updates.GITHUB_RELEASES_URL + "/tag/v2.3.0")
        kwargs["run_check"] = lambda **_: {"result": github}
        self.assertEqual(updates.automatic_check_for_update(self.root / "state", **kwargs), github)
        self.assertEqual(len(list((self.root / "state/update-check").glob("*.json"))), 2)


if __name__ == "__main__":
    unittest.main()
