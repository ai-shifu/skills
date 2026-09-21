from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import publish_release


class FakeRunner:
    def __init__(
        self,
        failing_publish: str | None = None,
        failing_auth: str | None = None,
        remote_commit: str = "abc123456789",
    ) -> None:
        self.commands: list[list[str]] = []
        self.failing_publish = failing_publish
        self.failing_auth = failing_auth
        self.remote_commit = remote_commit

    def __call__(self, command: list[str]) -> publish_release.CommandResult:
        self.commands.append(command)
        if command[:2] == ["git", "ls-remote"]:
            return publish_release.CommandResult(f"{self.remote_commit}\trefs/heads/main")
        if "whoami" in command and self.failing_auth and self.failing_auth in command[0]:
            raise publish_release.CommandFailure(command, "not authenticated")
        is_publish = "publish" in command and "--dry-run" not in command
        if is_publish and self.failing_publish and self.failing_publish in command[0]:
            raise publish_release.CommandFailure(command, "publish failed")
        return publish_release.CommandResult('{"ok": true}')


class PublishReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.release_dir = Path(self.temporary.name)
        clawhub = self.release_dir / "artifacts/clawhub/ai-shifu-course-creator"
        skillhub = self.release_dir / "artifacts/skillhub/ai-shifu-course-creator"
        clawhub.mkdir(parents=True)
        skillhub.mkdir(parents=True)
        (clawhub / "SKILL.md").write_text("fixture\n")
        (skillhub / "SKILL.md").write_text("fixture\n")
        workbuddy = self.release_dir / "artifacts/workbuddy/workbuddy-ai-shifu-1.1.0.zip"
        qclaw = self.release_dir / "artifacts/qclaw/qclaw-ai-shifu-1.0.0.zip"
        doubao = self.release_dir / "artifacts/doubao/doubao-ai-shifu-1.2.3.zip"
        workbuddy.parent.mkdir(parents=True)
        qclaw.parent.mkdir(parents=True)
        doubao.parent.mkdir(parents=True)
        workbuddy.write_bytes(b"workbuddy")
        qclaw.write_bytes(b"qclaw")
        doubao.write_bytes(b"doubao")
        self.metadata = {
            "schema_version": 4,
            "release_id": "fixture-1.2.3-abc1234-def5678",
            "release_sha256": "def5678",
            "source": {
                "repository": "git@github.com:ai-shifu/skills.git",
                "commit": "abc123456789",
            },
            "skill": {
                "name": "ai-shifu-course-creator",
                "display_name": "AI-Shifu Course Creator",
                "version": "1.2.3",
            },
            "artifacts": {
                "clawhub": {
                    "directory": "artifacts/clawhub/ai-shifu-course-creator",
                    "tree_sha256": "clawhub-tree-sha",
                },
                "skillhub": {
                    "directory": "artifacts/skillhub/ai-shifu-course-creator",
                    "tree_sha256": "skillhub-tree-sha",
                },
                "workbuddy": {
                    "archive": "artifacts/workbuddy/workbuddy-ai-shifu-1.1.0.zip",
                    "sha256": "workbuddy-sha",
                    "version": "1.1.0",
                },
                "qclaw": {
                    "archive": "artifacts/qclaw/qclaw-ai-shifu-1.0.0.zip",
                    "sha256": "qclaw-sha",
                    "version": "1.0.0",
                },
                "doubao": {
                    "archive": "artifacts/doubao/doubao-ai-shifu-1.2.3.zip",
                    "archive_sha256": "doubao-sha",
                    "tree_sha256": "doubao-tree-sha",
                    "version": "1.2.3",
                    "embedded_skills": {
                        "ai-shifu-course-creator": {},
                        "ai-shifu-learning-report": {},
                        "course-direction-advisor": {},
                    },
                },
            },
        }
        (self.release_dir / "release.json").write_text(json.dumps(self.metadata))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def publisher(self, runner: FakeRunner) -> publish_release.AutomatedPublisher:
        with patch.object(publish_release.build_release, "verify"):
            context = publish_release.ReleaseContext.load(self.release_dir)
        return publish_release.AutomatedPublisher(
            context,
            runner=runner,
            clawhub_command=("/node22/node", "/node22/npx-cli.js"),
            skillhub_cli=Path("/bin/skillhub"),
        )

    def test_check_uses_authentication_and_dry_run_only(self) -> None:
        runner = FakeRunner()
        results = self.publisher(runner).check(("clawhub", "skillhub"))

        self.assertEqual({target: result["status"] for target, result in results.items()}, {
            "clawhub": "ready",
            "skillhub": "ready",
        })
        publish_commands = [command for command in runner.commands if "publish" in command]
        self.assertEqual(len(publish_commands), 2)
        self.assertTrue(all("--dry-run" in command for command in publish_commands))
        clawhub_command = next(command for command in publish_commands if "clawhub@latest" in command)
        skillhub_command = next(command for command in publish_commands if command[0] == "/bin/skillhub")
        self.assertIn(
            str((self.release_dir / "artifacts/clawhub/ai-shifu-course-creator").resolve()),
            clawhub_command,
        )
        self.assertIn(
            str((self.release_dir / "artifacts/skillhub/ai-shifu-course-creator").resolve()),
            skillhub_command,
        )
        self.assertEqual(clawhub_command[clawhub_command.index("--name") + 1], "AI-Shifu Course Creator")
        report = json.loads((self.release_dir / "release-report.json").read_text())
        self.assertEqual(report["channels"]["clawhub"]["status"], "ready")
        self.assertEqual(results["clawhub"]["artifact_sha256"], "clawhub-tree-sha")
        self.assertEqual(results["skillhub"]["artifact_sha256"], "skillhub-tree-sha")

    def test_publish_records_partial_failure_without_rebuilding(self) -> None:
        runner = FakeRunner(failing_publish="skillhub")
        results = self.publisher(runner).publish(("clawhub", "skillhub"))

        self.assertEqual(results["clawhub"]["status"], "published")
        self.assertEqual(results["skillhub"]["status"], "failed")
        self.assertEqual(results["skillhub"]["response"], "publish failed")
        report = json.loads((self.release_dir / "release-report.json").read_text())
        self.assertEqual(report["channels"]["clawhub"]["status"], "published")
        self.assertEqual(report["channels"]["skillhub"]["status"], "failed")

    def test_failed_preflight_blocks_every_real_publish(self) -> None:
        runner = FakeRunner(failing_auth="skillhub")
        results = self.publisher(runner).publish(("clawhub", "skillhub"))

        self.assertEqual(results["clawhub"]["status"], "ready")
        self.assertEqual(results["skillhub"]["status"], "failed")
        real_publish_commands = [
            command for command in runner.commands
            if "publish" in command and "--dry-run" not in command
        ]
        self.assertEqual(real_publish_commands, [])

    def test_remote_main_change_requires_rebuild(self) -> None:
        runner = FakeRunner(remote_commit="different-commit")
        results = self.publisher(runner).check(("clawhub", "skillhub"))

        self.assertEqual(results["clawhub"]["status"], "failed")
        self.assertIn("rebuild required", results["skillhub"]["response"])
        self.assertEqual(len(runner.commands), 1)

    def test_manual_channels_use_built_archives_and_require_evidence(self) -> None:
        with patch.object(publish_release.build_release, "verify"):
            context = publish_release.ReleaseContext.load(self.release_dir)
        publisher = publish_release.ManualPublisher(context, runner=FakeRunner())

        plan = publisher.plan(("workbuddy", "qclaw", "doubao"))
        self.assertEqual(plan["workbuddy"]["status"], "pending_manual")
        self.assertEqual(plan["qclaw"]["embedded_skill_version"], "1.2.3")
        self.assertEqual(
            plan["doubao"]["embedded_skills"],
            ["ai-shifu-course-creator", "ai-shifu-learning-report", "course-direction-advisor"],
        )
        self.assertEqual(len(plan["doubao"]["runtime_tests"]["recommended_instructions"]), 3)
        self.assertIn(
            "all_embedded_skills_triggered",
            plan["doubao"]["runtime_tests"]["required_checks"],
        )
        with self.assertRaisesRegex(ValueError, "requires --url"):
            publisher.record("workbuddy", "verified")
        result = publisher.record(
            "workbuddy",
            "verified",
            url="https://workbuddy.example/releases/1.1.0",
        )
        self.assertEqual(result["status"], "verified")
        report = json.loads((self.release_dir / "release-report.json").read_text())
        self.assertEqual(report["channels"]["workbuddy"]["status"], "verified")
        with self.assertRaisesRegex(ValueError, "requires --url"):
            publisher.record("doubao", "submitted")
        doubao_result = publisher.record(
            "doubao",
            "submitted",
            url="https://doubao.example/submissions/123",
        )
        self.assertEqual(doubao_result["artifact_sha256"], "doubao-sha")


if __name__ == "__main__":
    unittest.main()
