from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from ai_shifu_release import artifacts
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

    def rewrite_avatar(self, avatar: str) -> None:
        self.profile["avatar"] = avatar
        profile_json = json.dumps(self.profile, ensure_ascii=False) + "\n"
        self.record["source_profile_json"] = profile_json
        self.record["source_profile_sha256"] = artifacts.content_hash(
            profile_json.encode("utf-8")
        )
        (self.package / "agent.yml").write_text(
            doubao.render_agent_yml(self.profile, self.source_frontmatter),
            encoding="utf-8",
        )
        (self.package / "README.md").write_text(
            doubao.render_readme(self.profile), encoding="utf-8"
        )
        ReleaseFixture.refresh_doubao_hashes(self.release_dir, self.report)

    def assert_ledger_matches(self) -> None:
        self.assertEqual(
            self.record["source_profile_sha256"],
            artifacts.content_hash(self.record["source_profile_json"].encode("utf-8")),
        )
        self.assertEqual(self.record["tree_sha256"], artifacts.tree_hash(self.package))
        self.assertEqual(
            self.record["archive_sha256"],
            artifacts.file_hash(self.release_dir / self.record["archive"]),
        )
        self.assertEqual(
            self.report["release_sha256"],
            artifacts.release_hash(
                digest
                for channel in artifacts.CHANNEL_ORDER
                for digest in artifacts.artifact_hashes(
                    self.report["artifacts"][channel]
                )
            ),
        )

    def test_valid_main_source_release_still_verifies(self) -> None:
        self.assertEqual(
            self.report["source"]["commit"], self.fixture.git("rev-parse", "main")
        )
        verify(self.release_dir)

    def assert_external_avatar_rejected(self, *, relative: bool) -> None:
        original_avatar = self.package / self.profile["avatar"]
        external_avatar = self.root / "outside-avatar.png"
        shutil.copy2(original_avatar, external_avatar)
        original_avatar.unlink()
        avatar = (
            os.path.relpath(external_avatar, self.package)
            if relative
            else str(external_avatar)
        )
        self.rewrite_avatar(avatar)
        self.assert_ledger_matches()
        self.assertTrue(external_avatar.is_file())
        with self.assertRaisesRegex(ValueError, "Doubao avatar"):
            verify(self.release_dir)

    def test_rejects_absolute_external_avatar_after_rehashing_every_ledger(
        self,
    ) -> None:
        self.assert_external_avatar_rejected(relative=False)

    def test_rejects_parent_external_avatar_after_rehashing_every_ledger(self) -> None:
        self.assert_external_avatar_rejected(relative=True)

    def test_package_validator_rejects_avatar_symlink_outside_package(self) -> None:
        avatar = self.package / self.profile["avatar"]
        external_avatar = self.root / "outside-avatar.png"
        shutil.copy2(avatar, external_avatar)
        avatar.unlink()
        avatar.symlink_to(external_avatar)
        with self.assertRaisesRegex(ValueError, "escapes release directory"):
            doubao.validate_package(self.package, self.profile, self.source_frontmatter)

    def test_nested_avatar_package_verifies_after_copying(self) -> None:
        original_avatar = self.package / self.profile["avatar"]
        nested_avatar = self.package / "images/avatar.png"
        nested_avatar.parent.mkdir()
        original_avatar.rename(nested_avatar)
        self.rewrite_avatar("images/avatar.png")
        self.assert_ledger_matches()
        verify(self.release_dir)
        copied_release = self.root / "copied-release"
        shutil.copytree(self.release_dir, copied_release)
        verify(copied_release)
