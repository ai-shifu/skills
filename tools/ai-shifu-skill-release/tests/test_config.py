from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import tomllib
from ai_shifu_release import TOOL_ROOT, config, release_state
from ai_shifu_release import verify as verification
from support import ReleaseFixture


def toml_document(values: dict) -> str:
    """Render the small public configuration fixtures without another dependency."""
    lines = []

    def table(entries: dict, prefix: str = "") -> None:
        if prefix:
            lines.append(f"[{prefix}]")
        for key, value in entries.items():
            if not isinstance(value, dict):
                lines.append(f"{key} = {json.dumps(value)}")
        lines.append("")
        for key, value in entries.items():
            if isinstance(value, dict):
                table(value, f"{prefix}.{key}" if prefix else key)

    table(values)
    return "\n".join(lines)


class ConfigValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "tool/release.toml"
        self.path.parent.mkdir()
        self.values = tomllib.loads((TOOL_ROOT / "release.toml").read_text())

    def load(self, values: dict):
        self.path.write_text(toml_document(values), encoding="utf-8")
        return config.load(self.path)

    def test_loads_public_identity_and_native_asset_references(self) -> None:
        loaded = self.load(self.values)
        self.assertEqual(loaded.publisher, self.values["publisher"])
        self.assertEqual(
            loaded.clawhub.owner, self.values["channels"]["clawhub"]["owner"]
        )
        self.assertEqual(
            loaded.skillhub.cli_url, self.values["channels"]["skillhub"]["cli_url"]
        )
        self.assertEqual(loaded.workbuddy.template_dir, "channels/workbuddy")
        self.assertEqual(loaded.doubao.profile, "channels/doubao/profile.json")

    def test_missing_channels_and_required_fields_are_rejected(self) -> None:
        for channel in self.values["channels"]:
            with self.subTest(channel=channel):
                candidate = copy.deepcopy(self.values)
                del candidate["channels"][channel]
                with self.assertRaises(ValueError):
                    self.load(candidate)
        sections = [("publisher", self.values["publisher"])] + [
            (channel, fields) for channel, fields in self.values["channels"].items()
        ]
        for section, fields in sections:
            for field in fields:
                with self.subTest(section=section, field=field):
                    candidate = copy.deepcopy(self.values)
                    table = (
                        candidate["publisher"]
                        if section == "publisher"
                        else candidate["channels"][section]
                    )
                    del table[field]
                    with self.assertRaises(ValueError):
                        self.load(candidate)

    def test_unknown_and_secret_fields_are_rejected(self) -> None:
        for section, field in (
            ("publisher", "organization"),
            ("clawhub", "access_token"),
            ("skillhub", "api_key"),
        ):
            with self.subTest(section=section, field=field):
                candidate = copy.deepcopy(self.values)
                table = (
                    candidate["publisher"]
                    if section == "publisher"
                    else candidate["channels"][section]
                )
                table[field] = "fixture-only"
                with self.assertRaises(ValueError):
                    self.load(candidate)

    def test_asset_paths_cannot_escape_the_channels_directory(self) -> None:
        for channel, field in (
            ("workbuddy", "template_dir"),
            ("doubao", "profile"),
            ("doubao", "workspace_dir"),
        ):
            for value in (
                "../channels/asset",
                "/tmp/asset",
                "channels/../../asset",
                "channels\\asset",
            ):
                with self.subTest(channel=channel, field=field, value=value):
                    candidate = copy.deepcopy(self.values)
                    candidate["channels"][channel][field] = value
                    with self.assertRaises(ValueError):
                        self.load(candidate)

    def test_asset_symlinks_cannot_escape_the_channels_directory(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        channels = self.path.parent / "channels"
        channels.mkdir()
        (channels / "escape").symlink_to(outside, target_is_directory=True)
        candidate = copy.deepcopy(self.values)
        candidate["channels"]["workbuddy"]["template_dir"] = "channels/escape"
        with self.assertRaises(ValueError):
            self.load(candidate)

    def test_installer_digest_must_be_a_complete_sha256(self) -> None:
        for digest in ("", "a" * 63, "a" * 65, "g" * 64):
            with self.subTest(digest=digest):
                candidate = copy.deepcopy(self.values)
                candidate["channels"]["skillhub"]["cli_sha256"] = digest
                with self.assertRaises(ValueError):
                    self.load(candidate)

    def test_urls_require_https_and_exclude_embedded_credentials(self) -> None:
        for channel, field in (
            ("clawhub", "endpoint"),
            ("skillhub", "endpoint"),
            ("skillhub", "cli_url"),
        ):
            for url in (
                "http://example.com/cli",
                "https://user:secret@example.com/cli",
                "https://example.com/cli?token=fixture",
                "https://example.com/cli#fragment",
            ):
                with self.subTest(channel=channel, field=field, url=url):
                    candidate = copy.deepcopy(self.values)
                    candidate["channels"][channel][field] = url
                    with self.assertRaises(ValueError):
                        self.load(candidate)

    def test_publisher_placeholders_and_empty_values_are_rejected(self) -> None:
        for field, value in (
            ("name", "__PUBLISHER_NAME__"),
            ("email", "you@example.com"),
            ("name", ""),
            ("email", " "),
        ):
            with self.subTest(field=field, value=value):
                candidate = copy.deepcopy(self.values)
                candidate["publisher"][field] = value
                with self.assertRaises(ValueError):
                    self.load(candidate)


class ConfigSourceTest(ReleaseFixture, unittest.TestCase):
    def test_release_settings_remain_pinned_after_source_main_advances(self) -> None:
        commit = self.git("rev-parse", "main")
        original = config.load_from_source(self.source_repo, commit)
        release = release_state.ReleaseContext.load(self.build(source_ref=commit))
        self.write_publisher("Later Publisher", "later@example.com")
        contents = self.release_config.read_text().replace(
            'owner = "heshaofu2"', 'owner = "later-publisher"'
        )
        self.release_config.write_text(contents)
        self.git("add", "tools/ai-shifu-skill-release/release.toml")
        self.git("commit", "-m", "later release settings")
        later_commit = self.git("rev-parse", "main")
        self.assertNotEqual(later_commit, commit)
        later = config.load_from_source(self.source_repo, later_commit)
        self.assertEqual(later.publisher["name"], "Later Publisher")
        self.assertEqual(later.clawhub.owner, "later-publisher")
        self.release_config.write_text("malformed local checkout [")
        self.assertEqual(config.load_from_source(self.source_repo, commit), original)
        self.assertEqual(config.load_for_release(release), original)

    def test_legacy_source_keeps_original_channel_settings_and_builds(self) -> None:
        legacy = self.release_config.with_name("publisher.toml")
        legacy.write_text(
            '[publisher]\nname = "AI-Shifu"\nemail = "release@ai-shifu.cn"\n'
        )
        self.release_config.unlink()
        self.git(
            "add",
            "tools/ai-shifu-skill-release/release.toml",
            "tools/ai-shifu-skill-release/publisher.toml",
        )
        self.git("commit", "-m", "historical publisher-only fixture")
        commit = self.git("rev-parse", "main")
        loaded = config.load_from_source(self.source_repo, commit)
        self.assertEqual(
            loaded.publisher, {"name": "AI-Shifu", "email": "release@ai-shifu.cn"}
        )
        self.assertEqual(loaded.clawhub.owner, "heshaofu2")
        self.assertEqual(loaded.clawhub.endpoint, "https://clawhub.ai")
        self.assertEqual(loaded.clawhub.package, "clawhub@latest")
        self.assertEqual(loaded.clawhub.node_version, "22")
        self.assertEqual(loaded.skillhub.endpoint, "https://api.skillhub.cn")
        self.assertEqual(loaded.skillhub.cli_version, "2026.8.5")
        self.assertEqual(loaded.workbuddy.template_dir, "channels/workbuddy")
        self.assertEqual(loaded.doubao.profile, "channels/doubao/profile.json")
        verification.verify(self.build(source_ref=commit))

    def test_malformed_source_config_does_not_use_a_legacy_file(self) -> None:
        self.release_config.write_text("malformed configuration [")
        self.release_config.with_name("publisher.toml").write_text(
            '[publisher]\nname = "Legacy Publisher"\nemail = "legacy@example.com"\n'
        )
        self.git("add", "tools/ai-shifu-skill-release")
        self.git("commit", "-m", "invalid modern config with legacy fallback present")
        with self.assertRaises(ValueError):
            config.load_from_source(self.source_repo, self.git("rev-parse", "main"))

    def test_source_config_requires_a_full_commit_sha(self) -> None:
        with self.assertRaises(ValueError):
            config.load_from_source(self.source_repo, "main")


if __name__ == "__main__":
    unittest.main()
