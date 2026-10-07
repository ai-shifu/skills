from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import test_build_release
from scripts import platform_publish, publish_release


class PlatformPublishTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = test_build_release.BuildReleaseTest()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.tearDown)
        cls.commit = cls.fixture.git("rev-parse", "main")
        cls.release_dir = cls.fixture.build(source_ref=cls.commit)

    def test_clawhub_requires_existing_publisher_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, \
             patch.dict(os.environ, {"CLAWHUB_OWNER": ""}), \
             patch.object(platform_publish.download_release, "download", return_value=self.release_dir), \
             patch.object(platform_publish.publish_release, "AutomatedPublisher") as publisher:
            result = platform_publish.publish(
                "v1.2.3", "ai-shifu/skills", "clawhub", Path(temporary), execute=True
            )
        self.assertEqual(result["status"], "failed")
        self.assertIn("owner", result["reason"])
        publisher.assert_not_called()

    def test_skillhub_submits_without_approval_switch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, \
             patch.dict(os.environ, {}, clear=True), \
             patch.object(platform_publish.download_release, "download", return_value=self.release_dir), \
             patch.object(platform_publish.publish_release, "AutomatedPublisher") as publisher, \
             patch.object(platform_publish, "existing_skillhub_version", return_value=False):
            instance = MagicMock()
            instance.publish.return_value = {"skillhub": {
                "status": "published", "response": "Published: skillId=123 status=pending_review"
            }}
            publisher.return_value = instance
            result = platform_publish.publish(
                "v1.2.3", "ai-shifu/skills", "skillhub", Path(temporary), execute=True
            )
        self.assertEqual(result["status"], "pending_review")
        self.assertEqual(result["archive_sha256"], self._archive_hash("skillhub"))
        self.assertEqual(publisher.call_args.kwargs["require_current_main"], False)
        instance.publish.assert_called_once_with(("skillhub",))

    def test_clawhub_submits_with_owner_without_mit0_switch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, \
             patch.dict(os.environ, {"CLAWHUB_OWNER": "heshaofu2"}, clear=True), \
             patch.object(platform_publish.download_release, "download", return_value=self.release_dir), \
             patch.object(platform_publish.publish_release, "AutomatedPublisher") as publisher, \
             patch.object(platform_publish, "existing_clawhub_version", return_value=False):
            instance = MagicMock()
            instance.publish.return_value = {"clawhub": {
                "status": "published", "response": "version accepted"
            }}
            publisher.return_value = instance
            result = platform_publish.publish(
                "v1.2.3", "ai-shifu/skills", "clawhub", Path(temporary), execute=True
            )
        self.assertEqual(result["status"], "submitted")
        self.assertEqual(publisher.call_args.kwargs["clawhub_owner"], "heshaofu2")
        instance.publish.assert_called_once_with(("clawhub",))

    def test_existing_clawhub_version_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, \
             patch.dict(os.environ, {"CLAWHUB_OWNER": "heshaofu2"}), \
             patch.object(platform_publish.download_release, "download", return_value=self.release_dir), \
             patch.object(platform_publish.publish_release, "AutomatedPublisher") as publisher, \
             patch.object(platform_publish, "existing_clawhub_version", return_value=True):
            result = platform_publish.publish(
                "v1.2.3", "ai-shifu/skills", "clawhub", Path(temporary), execute=True
            )
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(publisher.call_args.kwargs["clawhub_owner"], "heshaofu2")
        publisher.return_value.publish.assert_not_called()

    def test_existing_skillhub_version_is_not_resubmitted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, \
             patch.dict(os.environ, {}, clear=True), \
             patch.object(platform_publish.download_release, "download", return_value=self.release_dir), \
             patch.object(platform_publish.publish_release, "AutomatedPublisher") as publisher, \
             patch.object(platform_publish, "existing_skillhub_version", return_value=True):
            result = platform_publish.publish(
                "v1.2.3", "ai-shifu/skills", "skillhub", Path(temporary), execute=True
            )
        self.assertEqual(result["status"], "already_verified")
        publisher.return_value.publish.assert_not_called()

    def test_skillhub_version_lookup_proceeds_only_on_not_found(self) -> None:
        release = publish_release.ReleaseContext.load(self.release_dir)
        def missing(command):
            raise publish_release.CommandFailure(command, "找不到该版本")
        publisher = publish_release.AutomatedPublisher(
            release, runner=missing, skillhub_cli=Path("/bin/skillhub"),
            require_current_main=False,
        )
        self.assertFalse(platform_publish.existing_skillhub_version(publisher))
        def uncertain(command):
            raise publish_release.CommandFailure(command, "authentication failed")
        publisher.runner = uncertain
        with self.assertRaises(publish_release.CommandFailure):
            platform_publish.existing_skillhub_version(publisher)

    def test_uncertain_registry_lookup_never_submits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, \
             patch.dict(os.environ, {}, clear=True), \
             patch.object(platform_publish.download_release, "download", return_value=self.release_dir), \
             patch.object(platform_publish.publish_release, "AutomatedPublisher") as publisher, \
             patch.object(platform_publish, "existing_skillhub_version", side_effect=ValueError("unknown state")):
            result = platform_publish.publish(
                "v1.2.3", "ai-shifu/skills", "skillhub", Path(temporary), execute=True
            )
        self.assertEqual(result["status"], "needs_review")
        publisher.return_value.publish.assert_not_called()

    def _archive_hash(self, target: str) -> str:
        import json
        return json.loads((self.release_dir / "release.json").read_text())["artifacts"][target]["archive_sha256"]


if __name__ == "__main__":
    unittest.main()
