from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from ai_shifu_release.channels import doubao
from ai_shifu_release.verify import verify
from support import ReleaseFixture


class DoubaoIntegrityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = ReleaseFixture()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.tearDown)
        cls.original = cls.fixture.build(source_ref="main")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.release_dir = self.root / "release"
        shutil.copytree(self.original, self.release_dir)
        self.report = json.loads((self.release_dir / "release.json").read_text())
        self.record = self.report["artifacts"]["doubao"]
        self.package = self.release_dir / self.record["directory"]
        self.profile = json.loads(self.record["source_profile_json"])
        self.source_frontmatter = ReleaseFixture.source_frontmatter(self.report)

    def test_valid_release_and_copied_release_verify(self) -> None:
        verify(self.release_dir)
        copied = self.root / "copied"
        shutil.copytree(self.release_dir, copied)
        verify(copied)

    def test_rejects_icon_symlink_outside_package(self) -> None:
        icon = self.package / doubao.ICON_PATH
        external = self.root / "external.png"
        shutil.copy2(icon, external)
        icon.unlink()
        icon.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "escapes release directory"):
            doubao.validate_package(self.package, self.profile, self.source_frontmatter)

    def test_rejects_invalid_icon_dimensions_and_size(self) -> None:
        icon = self.package / doubao.ICON_PATH
        data = bytearray(icon.read_bytes())
        data[16:20] = (256).to_bytes(4, "big")
        data[20:24] = (256).to_bytes(4, "big")
        icon.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "512x512"):
            doubao.validate_package(self.package, self.profile, self.source_frontmatter)

    def test_rejects_manifest_version_after_rehashing(self) -> None:
        path = self.package / "plugin.json"
        manifest = json.loads(path.read_text())
        manifest["version"] = "9.9.9"
        path.write_text(json.dumps(manifest, ensure_ascii=False))
        ReleaseFixture.refresh_doubao_hashes(self.release_dir, self.report)
        with self.assertRaisesRegex(ValueError, "plugin.json differs"):
            verify(self.release_dir)

    def test_rejects_missing_skill_and_legacy_workspace(self) -> None:
        (self.package / "skills/course-direction-advisor/SKILL.md").unlink()
        with self.assertRaisesRegex(ValueError, "missing SKILL.md"):
            doubao.validate_package(self.package, self.profile, self.source_frontmatter)
        (self.package / "workspace").mkdir()
        with self.assertRaisesRegex(ValueError, "legacy partner"):
            doubao.validate_package(self.package, self.profile, self.source_frontmatter)

    def test_rejects_oversized_file_and_too_many_entries(self) -> None:
        extra = self.package / "large.bin"
        extra.write_bytes(b"x" * (doubao.MAX_FILE_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "exceeds 2 MiB"):
            doubao.validate_package(self.package, self.profile, self.source_frontmatter)
        extra.unlink()
        many = self.package / "extra"
        many.mkdir()
        for number in range(doubao.MAX_ENTRIES):
            (many / str(number)).write_text("x")
        with self.assertRaisesRegex(ValueError, "1024 ZIP entries"):
            doubao.validate_package(self.package, self.profile, self.source_frontmatter)

    def test_rejects_non_whitelisted_skill_change_after_rehashing(self) -> None:
        skill = self.package / "skills/ai-shifu-learning-report/SKILL.md"
        skill.write_text(
            skill.read_text().replace("# Learning Report", "# Changed Report")
        )
        ReleaseFixture.refresh_doubao_hashes(self.release_dir, self.report)
        with self.assertRaisesRegex(ValueError, "body differs"):
            verify(self.release_dir)

    def test_zip_limits_include_directory_entries_and_expanded_sizes(self) -> None:
        archive = self.root / "limits.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("folder/", "")
            bundle.writestr("folder/large.txt", "a" * 2000)
        with patch.object(doubao, "MAX_ENTRIES", 1):
            with self.assertRaisesRegex(ValueError, "1024 ZIP entries"):
                doubao.validate_archive_limits(archive)
        with patch.object(doubao, "MAX_FILE_BYTES", 1000):
            with self.assertRaisesRegex(ValueError, "exceeding 2 MiB"):
                doubao.validate_archive_limits(archive)
        with patch.object(doubao, "MAX_PACKAGE_BYTES", 1000):
            with self.assertRaisesRegex(ValueError, "16 MiB uncompressed"):
                doubao.validate_archive_limits(archive)


class DoubaoLegacyCompatibilityTest(ReleaseFixture, unittest.TestCase):
    def test_build_and_verify_historical_profile(self) -> None:
        profile = (
            self.source_repo
            / "tools/ai-shifu-skill-release/channels/doubao/profile.json"
        )
        legacy = Path(__file__).parent / "fixtures/doubao-legacy-profile.json"
        shutil.copy2(legacy, profile)
        self.git("add", str(profile.relative_to(self.source_repo)))
        self.git("commit", "-m", "historical partner fixture")
        release = self.build()
        report = json.loads((release / "release.json").read_text())
        record = report["artifacts"]["doubao"]
        root = release / record["directory"]
        self.assertTrue((root / "agent.yml").is_file())
        self.assertTrue(
            (root / "workspace/skills/ai-shifu-course-creator/SKILL.md").is_file()
        )
        self.assertEqual(record["archive_root"], "doubao-ai-shifu-1.2.3")
        verify(release)
        self.assertEqual(self.build(), release)


if __name__ == "__main__":
    unittest.main()
