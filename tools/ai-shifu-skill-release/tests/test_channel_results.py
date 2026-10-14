from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_shifu_release import TOOL_ROOT, channel_results
from ai_shifu_release.release_state import ReleaseContext, ReleaseReport
from support import ReleaseFixture


class ChannelResultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = ReleaseFixture()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.tearDown)
        cls.original = cls.fixture.build(
            source_ref=cls.fixture.git("rev-parse", "main")
        )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.release_dir = self.root / "release"
        shutil.copytree(self.original, self.release_dir)
        self.release = ReleaseContext.load(self.release_dir)

    def receipt(self, channel: str, submission_status: str, **overrides) -> Path:
        result = {
            "target": channel,
            "tag": f"v{self.release.version}",
            "source_commit": self.release.source_commit,
            "version": self.release.version,
            "archive_sha256": self.release.metadata["artifacts"][channel][
                "archive_sha256"
            ],
            "status": submission_status,
        }
        result.update(overrides)
        path = self.root / f"{channel}-result.json"
        path.write_text(json.dumps(result), encoding="utf-8")
        return path

    def test_actions_receipts_update_report_and_preserve_manual_results(self) -> None:
        manual = {
            "workbuddy": {
                "status": "submitted",
                "url": "https://example.com/workbuddy",
                "note": "Awaiting platform review",
            },
            "doubao": {
                "status": "verified",
                "url": "https://example.com/doubao",
                "note": "Runtime checks passed",
            },
        }
        ReleaseReport(self.release).update(manual)
        imported = channel_results.import_results(
            self.release_dir,
            [
                self.receipt("clawhub", "pending_review"),
                self.receipt("skillhub", "already_verified"),
            ],
        )
        self.assertEqual(imported["clawhub"]["status"], "published")
        self.assertEqual(imported["clawhub"]["submission_status"], "pending_review")
        self.assertEqual(imported["skillhub"]["status"], "verified")
        self.assertEqual(imported["skillhub"]["submission_status"], "already_verified")
        report = json.loads((self.release_dir / "release-report.json").read_text())
        self.assertEqual(report["channels"], {**manual, **imported})

    def test_failed_or_uncertain_receipts_replace_previous_success(self) -> None:
        retained = {
            "skillhub": {"status": "verified", "submission_status": "already_verified"},
            "workbuddy": {"status": "submitted", "url": "https://example.com/workbuddy"},
            "doubao": {"status": "verified", "url": "https://example.com/doubao"},
        }
        for status in ("failed", "needs_review"):
            with self.subTest(status=status):
                ReleaseReport(self.release).update(
                    {**retained, "clawhub": {"status": "published"}}
                )
                reason = f"Channel submission {status}"
                imported = channel_results.import_results(
                    self.release_dir, [self.receipt("clawhub", status, reason=reason)]
                )
                self.assertEqual(imported["clawhub"]["status"], status)
                self.assertEqual(imported["clawhub"]["submission_status"], status)
                self.assertEqual(imported["clawhub"]["response"], reason)
                report = json.loads((self.release_dir / "release-report.json").read_text())
                self.assertEqual(report["channels"], {**retained, **imported})

    def test_mismatched_receipt_does_not_partially_update_report(self) -> None:
        ReleaseReport(self.release).update({"workbuddy": {"status": "submitted"}})
        report_path = self.release_dir / "release-report.json"
        original = report_path.read_bytes()
        for field, value in (
            ("source_commit", "0" * 40),
            ("version", "9.9.9"),
            ("tag", "v9.9.9"),
            ("archive_sha256", "0" * 64),
            ("status", "listed"),
            ("target", "workbuddy"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    channel_results.import_results(
                        self.release_dir,
                        [
                            self.receipt("clawhub", "submitted"),
                            self.receipt("skillhub", "submitted", **{field: value}),
                        ],
                    )
                self.assertEqual(report_path.read_bytes(), original)

    def test_rejects_duplicate_channel_receipts(self) -> None:
        receipt = self.receipt("clawhub", "submitted")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            channel_results.import_results(self.release_dir, [receipt, receipt])
        self.assertFalse((self.release_dir / "release-report.json").exists())

    def test_rejects_tampered_release_before_recording_receipts(self) -> None:
        receipt = self.receipt("skillhub", "submitted")
        archive = (
            self.release_dir / self.release.metadata["artifacts"]["skillhub"]["archive"]
        )
        archive.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            channel_results.import_results(self.release_dir, [receipt])
        self.assertFalse((self.release_dir / "release-report.json").exists())

    def test_command_imports_receipt_from_caller_relative_path(self) -> None:
        receipt = self.receipt("clawhub", "submitted")
        result = subprocess.run(
            [
                sys.executable,
                str(TOOL_ROOT / "scripts/release.py"),
                "record-channel",
                str(self.release_dir),
                "--result",
                receipt.name,
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        )
        imported = json.loads(result.stdout)
        self.assertEqual(imported["clawhub"]["status"], "published")
        self.assertEqual(imported["clawhub"]["submission_status"], "submitted")
        report = json.loads((self.release_dir / "release-report.json").read_text())
        self.assertEqual(report["channels"], imported)
