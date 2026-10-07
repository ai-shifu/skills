from __future__ import annotations

import json
import shutil
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from ai_shifu_release import artifacts
from ai_shifu_release import verify as verification
from ai_shifu_release.artifacts import zip_subtree_contents
from support import ReleaseFixture


def write_member(bundle: zipfile.ZipFile, name: str, content: str) -> None:
    info = zipfile.ZipInfo(name)
    info.external_attr = (
        (stat.S_IFDIR | 0o755) if name.endswith("/") else (stat.S_IFREG | 0o644)
    ) << 16
    bundle.writestr(info, content)


class ArchiveIntegrityTest(unittest.TestCase):
    def test_rejects_unverified_sibling_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "package.zip"
            for extra in ("extra.txt", "sibling/file.txt", "sibling/"):
                with self.subTest(extra=extra):
                    with zipfile.ZipFile(archive, "w") as bundle:
                        write_member(bundle, "skill/SKILL.md", "expected")
                        write_member(bundle, extra, "unverified")
                    with self.assertRaisesRegex(ValueError, "outside"):
                        zip_subtree_contents(archive, "skill")

    def test_rejects_duplicate_members_even_when_contents_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "package.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(archive, "w") as bundle:
                    write_member(bundle, "skill/SKILL.md", "expected")
                    write_member(bundle, "skill/SKILL.md", "expected")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                zip_subtree_contents(archive, "skill")

    def test_reads_valid_root_and_skips_its_directory_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "package.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                write_member(bundle, "skill/", "")
                write_member(bundle, "skill/references/", "")
                write_member(bundle, "skill/SKILL.md", "expected")
                write_member(bundle, "skill/references/guide.md", "guide")
            self.assertEqual(
                zip_subtree_contents(archive, "skill"),
                {"SKILL.md": b"expected", "references/guide.md": b"guide"},
            )


class ReleaseZipTypeTest(unittest.TestCase):
    def test_symlink_metadata_is_rejected_even_with_matching_release_hashes(
        self,
    ) -> None:
        fixture = ReleaseFixture()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        original = fixture.build(source_ref=fixture.git("rev-parse", "main"))
        candidate = fixture.root / "candidate"
        shutil.copytree(original, candidate)
        report = json.loads((candidate / "release.json").read_text())
        record = report["artifacts"]["skillhub"]
        archive = candidate / record["archive"]
        changed = fixture.root / "changed.zip"
        with (
            zipfile.ZipFile(archive) as source,
            zipfile.ZipFile(changed, "w") as target,
        ):
            for info in source.infolist():
                if info.filename.endswith("/SKILL.md"):
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                target.writestr(info, source.read(info))
        changed.replace(archive)
        record["archive_sha256"] = artifacts.file_hash(archive)
        report["release_sha256"] = artifacts.release_hash(
            digest
            for channel in artifacts.CHANNEL_ORDER
            for digest in artifacts.artifact_hashes(report["artifacts"][channel])
        )
        (candidate / "release.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "Non-file ZIP entry"):
            verification.verify(candidate)
