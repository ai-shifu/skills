from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

from ai_shifu_release import (
    TOOL_ROOT,
    channel_submission,
    config,
    github_releases,
    publishing,
    release_state,
)
from support import ReleaseFixture


class ChannelSubmissionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = config.load(TOOL_ROOT / "release.toml")
        cls.fixture = ReleaseFixture()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.tearDown)
        cls.commit = cls.fixture.git("rev-parse", "main")
        cls.release_dir = cls.fixture.build(source_ref=cls.commit)

    def test_clawhub_owner_defaults_to_release_configuration(self) -> None:
        commands = []

        def runner(command):
            commands.append(command)
            if "inspect" in command:
                raise publishing.CommandFailure(command, "not found")
            return publishing.CommandResult("version accepted")

        publisher_class = publishing.AutomatedPublisher

        def create_publisher(release, **options):
            return publisher_class(
                release, runner=runner, clawhub_command=("/bin/npx",), **options
            )

        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {"CLAWHUB_OWNER": ""}, clear=True),
            patch.object(
                release_state.ReleaseContext,
                "source_repo",
                new_callable=PropertyMock,
                return_value="ai-shifu/skills",
            ),
            patch.object(
                channel_submission.github_releases,
                "download",
                return_value=self.release_dir,
            ),
            patch.object(
                channel_submission.publishing,
                "AutomatedPublisher",
                side_effect=create_publisher,
            ),
        ):
            result = channel_submission.publish(
                "v1.2.3",
                "ai-shifu/skills",
                "clawhub",
                Path(temporary),
                execute=True,
                config=self.config,
            )
        self.assertEqual(result["status"], "submitted")
        lookup = next(command for command in commands if "inspect" in command)
        self.assertIn(f"@{self.config.clawhub.owner}/ai-shifu-course-creator", lookup)
        for command in commands:
            self.assertEqual(
                command[command.index("--registry") + 1], self.config.clawhub.endpoint
            )
            if "publish" in command:
                self.assertEqual(
                    command[command.index("--owner") + 1], self.config.clawhub.owner
                )

    def test_skillhub_submits_without_approval_switch(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {}, clear=True),
            patch.object(
                channel_submission.github_releases,
                "download",
                return_value=self.release_dir,
            ),
            patch.object(
                channel_submission.publishing, "AutomatedPublisher"
            ) as publisher,
        ):
            instance = MagicMock()
            instance.existing_skillhub_version.return_value = False
            instance.publish.return_value = {
                "skillhub": {
                    "status": "published",
                    "response": "Published: skillId=123 status=pending_review",
                }
            }
            publisher.return_value = instance
            result = channel_submission.publish(
                "v1.2.3",
                "ai-shifu/skills",
                "skillhub",
                Path(temporary),
                execute=True,
                config=self.config,
            )
        self.assertEqual(result["status"], "pending_review")
        self.assertEqual(result["archive_sha256"], self._archive_hash("skillhub"))
        self.assertEqual(publisher.call_args.kwargs["require_current_main"], False)
        instance.publish.assert_called_once_with(("skillhub",))

    def test_skillhub_rerun_requires_new_confirmation(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {"GITHUB_RUN_ATTEMPT": "2"}),
            patch.object(channel_submission.github_releases, "download") as download,
        ):
            with self.assertRaisesRegex(ValueError, "start a new manual run"):
                channel_submission.publish(
                    "v1.2.3",
                    "ai-shifu/skills",
                    "skillhub",
                    Path(temporary),
                    execute=True,
                    config=self.config,
                )
            download.assert_not_called()

    def test_clawhub_submits_with_owner_without_mit0_switch(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {"CLAWHUB_OWNER": "heshaofu2"}, clear=True),
            patch.object(
                channel_submission.github_releases,
                "download",
                return_value=self.release_dir,
            ),
            patch.object(
                channel_submission.publishing, "AutomatedPublisher"
            ) as publisher,
        ):
            instance = MagicMock()
            instance.existing_clawhub_version.return_value = False
            instance.publish.return_value = {
                "clawhub": {"status": "published", "response": "version accepted"}
            }
            publisher.return_value = instance
            result = channel_submission.publish(
                "v1.2.3",
                "ai-shifu/skills",
                "clawhub",
                Path(temporary),
                execute=True,
                config=self.config,
            )
        self.assertEqual(result["status"], "submitted")
        self.assertIs(publisher.call_args.kwargs["config"], self.config)
        instance.publish.assert_called_once_with(("clawhub",))

    def test_existing_clawhub_version_requires_review(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {"CLAWHUB_OWNER": "heshaofu2"}),
            patch.object(
                channel_submission.github_releases,
                "download",
                return_value=self.release_dir,
            ),
            patch.object(
                channel_submission.publishing, "AutomatedPublisher"
            ) as publisher,
        ):
            publisher.return_value.existing_clawhub_version.return_value = True
            result = channel_submission.publish(
                "v1.2.3",
                "ai-shifu/skills",
                "clawhub",
                Path(temporary),
                execute=True,
                config=self.config,
            )
        self.assertEqual(result["status"], "needs_review")
        self.assertIs(publisher.call_args.kwargs["config"], self.config)
        publisher.return_value.publish.assert_not_called()

    def test_existing_skillhub_version_is_not_resubmitted(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {}, clear=True),
            patch.object(
                channel_submission.github_releases,
                "download",
                return_value=self.release_dir,
            ),
            patch.object(
                channel_submission.publishing, "AutomatedPublisher"
            ) as publisher,
        ):
            publisher.return_value.existing_skillhub_version.return_value = True
            result = channel_submission.publish(
                "v1.2.3",
                "ai-shifu/skills",
                "skillhub",
                Path(temporary),
                execute=True,
                config=self.config,
            )
        self.assertEqual(result["status"], "already_verified")
        publisher.return_value.publish.assert_not_called()

    def test_skillhub_version_lookup_proceeds_only_on_not_found(self) -> None:
        release = release_state.ReleaseContext.load(self.release_dir)

        def missing(command):
            raise publishing.CommandFailure(command, "找不到该版本")

        publisher = publishing.AutomatedPublisher(
            release,
            runner=missing,
            skillhub_cli=Path("/bin/skillhub"),
            require_current_main=False,
            config=self.config,
        )
        self.assertFalse(publisher.existing_skillhub_version())

        def uncertain(command):
            raise publishing.CommandFailure(command, "authentication failed")

        publisher.runner = uncertain
        with self.assertRaises(publishing.CommandFailure):
            publisher.existing_skillhub_version()

    def test_uncertain_registry_lookup_never_submits(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {}, clear=True),
            patch.object(
                channel_submission.github_releases,
                "download",
                return_value=self.release_dir,
            ),
            patch.object(
                channel_submission.publishing, "AutomatedPublisher"
            ) as publisher,
        ):
            publisher.return_value.existing_skillhub_version.side_effect = ValueError(
                "unknown state"
            )
            result = channel_submission.publish(
                "v1.2.3",
                "ai-shifu/skills",
                "skillhub",
                Path(temporary),
                execute=True,
                config=self.config,
            )
        self.assertEqual(result["status"], "needs_review")
        publisher.return_value.publish.assert_not_called()

    def test_unverified_release_never_reaches_a_publisher(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate"
            shutil.copytree(self.release_dir, candidate)
            metadata = json.loads((candidate / "release.json").read_text())
            archive = candidate / metadata["artifacts"]["skillhub"]["archive"]
            archive.write_bytes(b"tampered release package")
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(
                    channel_submission.github_releases,
                    "download",
                    return_value=candidate,
                ),
                patch.object(
                    channel_submission.publishing, "AutomatedPublisher"
                ) as publisher,
            ):
                with self.assertRaises(ValueError):
                    channel_submission.publish(
                        "v1.2.3",
                        "ai-shifu/skills",
                        "skillhub",
                        root / "output",
                        execute=True,
                        config=self.config,
                    )
                publisher.assert_not_called()

    def test_configuration_commit_must_match_downloaded_release_before_publication(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {"RELEASE_SOURCE_COMMIT": "f" * 40}, clear=True),
            patch.object(
                channel_submission.github_releases,
                "download",
                return_value=self.release_dir,
            ),
            patch.object(
                channel_submission.publishing, "AutomatedPublisher"
            ) as publisher,
        ):
            with self.assertRaisesRegex(ValueError, "configuration source commit"):
                channel_submission.publish(
                    "v1.2.3",
                    "ai-shifu/skills",
                    "clawhub",
                    Path(temporary),
                    execute=True,
                    config=self.config,
                )
            publisher.assert_not_called()

    def test_new_runtime_submits_old_release_after_source_main_advances(self) -> None:
        fixture = ReleaseFixture()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        old_commit = fixture.git("rev-parse", "main")
        candidate = fixture.build(source_ref=old_commit)
        old_metadata = json.loads((candidate / "release.json").read_text())
        skill_file = fixture.skill / "SKILL.md"
        skill_file.write_text(fixture.source_skill_text.replace("1.2.3", "2.0.0"))
        fixture.git("add", "skills/ai-shifu-course-creator/SKILL.md")
        fixture.git("commit", "-m", "advance source after release")
        new_commit = fixture.git("rev-parse", "main")
        self.assertNotEqual(new_commit, old_commit)
        assets, _ = github_releases.prepare_assets(
            candidate, "v1.2.3", old_commit, fixture.root / "attachments"
        )
        attachment_paths = {path.name: path for path in assets}
        github_calls = []
        registry_commands = []

        def fake_gh(*arguments, **options):
            github_calls.append(arguments)
            if arguments[:2] == ("release", "view"):
                return SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "isDraft": False,
                            "tagName": "v1.2.3",
                            "assets": [{"name": name} for name in attachment_paths],
                        }
                    )
                )
            if arguments[:2] == ("release", "download"):
                name = arguments[arguments.index("--pattern") + 1]
                destination = Path(arguments[arguments.index("--dir") + 1])
                shutil.copy2(attachment_paths[name], destination / name)
                return SimpleNamespace(stdout="")
            if arguments[:2] == ("api", "repos/ai-shifu/skills/commits/v1.2.3"):
                return SimpleNamespace(stdout=old_commit)
            raise AssertionError(arguments)

        def registry_runner(command):
            registry_commands.append(command)
            if command[:2] == ["git", "ls-remote"]:
                return publishing.CommandResult(f"{new_commit}\trefs/heads/main")
            if command[1] == "verify":
                raise publishing.CommandFailure(command, "找不到该版本")
            if command[1:3] == ["auth", "whoami"]:
                return publishing.CommandResult('{"authenticated": true}')
            if command[1] == "publish":
                return publishing.CommandResult("Published: status=pending_review")
            raise AssertionError(command)

        publisher_class = publishing.AutomatedPublisher

        def create_publisher(release, **options):
            return publisher_class(
                release,
                runner=registry_runner,
                skillhub_cli=Path("/bin/skillhub"),
                **options,
            )

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(github_releases, "gh", side_effect=fake_gh),
            patch.object(
                publishing, "AutomatedPublisher", side_effect=create_publisher
            ) as publisher,
        ):
            result = channel_submission.publish(
                "v1.2.3",
                "ai-shifu/skills",
                "skillhub",
                fixture.root / "download",
                execute=True,
                config=self.config,
            )

        self.assertEqual(result["status"], "pending_review")
        self.assertEqual(result["source_commit"], old_commit)
        self.assertEqual(result["version"], "1.2.3")
        self.assertEqual(
            result["archive_sha256"],
            old_metadata["artifacts"]["skillhub"]["archive_sha256"],
        )
        self.assertFalse(publisher.call_args.kwargs["require_current_main"])
        self.assertFalse(
            any(command[:2] == ["git", "ls-remote"] for command in registry_commands)
        )
        archive_check = next(
            command for command in registry_commands if command[1] == "verify"
        )
        checked_archive = Path(archive_check[archive_check.index("--zip") + 1])
        self.assertEqual(
            checked_archive.read_bytes(),
            (candidate / old_metadata["artifacts"]["skillhub"]["archive"]).read_bytes(),
        )
        publication = next(
            command
            for command in registry_commands
            if command[1] == "publish" and "--dry-run" not in command
        )
        self.assertEqual(publication[publication.index("--version") + 1], "1.2.3")
        self.assertEqual(
            (Path(publication[2]) / "SKILL.md").read_text().split("# Fixture Skill")[1],
            fixture.source_skill_text.split("# Fixture Skill")[1],
        )
        self.assertTrue(
            all(
                arguments[2] == "v1.2.3"
                for arguments in github_calls
                if arguments[0] == "release"
            )
        )

    def _archive_hash(self, target: str) -> str:
        return json.loads((self.release_dir / "release.json").read_text())["artifacts"][
            target
        ]["archive_sha256"]


if __name__ == "__main__":
    unittest.main()
