from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from ai_shifu_release import TOOL_ROOT, config, publishing, release_state


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

    def __call__(self, command: list[str]) -> publishing.CommandResult:
        self.commands.append(command)
        if command[:2] == ["git", "ls-remote"]:
            return publishing.CommandResult(f"{self.remote_commit}\trefs/heads/main")
        if (
            "whoami" in command
            and self.failing_auth
            and self.failing_auth in command[0]
        ):
            raise publishing.CommandFailure(command, "not authenticated")
        is_publish = "publish" in command and "--dry-run" not in command
        if is_publish and self.failing_publish and self.failing_publish in command[0]:
            raise publishing.CommandFailure(command, "publish failed")
        return publishing.CommandResult('{"ok": true}')


class PublishReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.release_dir = Path(self.temporary.name)
        self.config = config.load(TOOL_ROOT / "release.toml")
        clawhub = self.release_dir / "artifacts/clawhub/ai-shifu-course-creator"
        skillhub = self.release_dir / "artifacts/skillhub/ai-shifu-course-creator"
        clawhub.mkdir(parents=True)
        skillhub.mkdir(parents=True)
        (clawhub / "SKILL.md").write_text("fixture\n")
        (skillhub / "SKILL.md").write_text("fixture\n")
        workbuddy = (
            self.release_dir / "artifacts/workbuddy/workbuddy-ai-shifu-1.1.0.zip"
        )
        doubao = self.release_dir / "artifacts/doubao/doubao-ai-shifu-1.2.3.zip"
        workbuddy.parent.mkdir(parents=True)
        doubao.parent.mkdir(parents=True)
        workbuddy.write_bytes(b"workbuddy")
        doubao.write_bytes(b"doubao")
        self.metadata = {
            "schema_version": 6,
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
                "doubao": {
                    "archive": "artifacts/doubao/doubao-ai-shifu-1.2.3.zip",
                    "archive_sha256": "doubao-sha",
                    "tree_sha256": "doubao-tree-sha",
                    "version": "1.2.3",
                    "source_profile_json": json.dumps(
                        {
                            "recommended_instructions": [
                                "Released instruction one",
                                "Released instruction two",
                                "Released instruction three",
                            ]
                        }
                    ),
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

    def publisher(self, runner: FakeRunner) -> publishing.AutomatedPublisher:
        with patch.object(release_state, "verify"):
            context = release_state.ReleaseContext.load(self.release_dir)
        return publishing.AutomatedPublisher(
            context,
            runner=runner,
            clawhub_command=("/node22/node", "/node22/npx-cli.js"),
            skillhub_cli=Path("/bin/skillhub"),
            config=self.config,
        )

    def test_check_uses_authentication_and_dry_run_only(self) -> None:
        runner = FakeRunner()
        results = self.publisher(runner).check(("clawhub", "skillhub"))

        self.assertEqual(
            {target: result["status"] for target, result in results.items()},
            {
                "clawhub": "ready",
                "skillhub": "ready",
            },
        )
        publish_commands = [
            command for command in runner.commands if "publish" in command
        ]
        self.assertEqual(len(publish_commands), 2)
        self.assertTrue(all("--dry-run" in command for command in publish_commands))
        clawhub_command = next(
            command for command in publish_commands if "clawhub@latest" in command
        )
        skillhub_command = next(
            command for command in publish_commands if command[0] == "/bin/skillhub"
        )
        self.assertIn(
            str(
                (
                    self.release_dir / "artifacts/clawhub/ai-shifu-course-creator"
                ).resolve()
            ),
            clawhub_command,
        )
        self.assertIn(
            str(
                (
                    self.release_dir / "artifacts/skillhub/ai-shifu-course-creator"
                ).resolve()
            ),
            skillhub_command,
        )
        self.assertNotIn("--json", skillhub_command)
        self.assertIn("https://api.skillhub.cn", skillhub_command)
        self.assertIn(
            ["skill", "publish"],
            [clawhub_command[i : i + 2] for i in range(len(clawhub_command) - 1)],
        )
        self.assertEqual(
            clawhub_command[clawhub_command.index("--name") + 1],
            "AI-Shifu Course Creator",
        )
        report = json.loads((self.release_dir / "release-report.json").read_text())
        self.assertEqual(report["channels"]["clawhub"]["status"], "ready")
        self.assertEqual(results["clawhub"]["artifact_sha256"], "clawhub-tree-sha")
        self.assertEqual(results["skillhub"]["artifact_sha256"], "skillhub-tree-sha")

    def test_channel_config_controls_every_authentication_and_publish_command(
        self,
    ) -> None:
        runner = FakeRunner()
        publisher = self.publisher(runner)
        publisher._config = replace(
            self.config,
            clawhub=replace(
                self.config.clawhub,
                owner="configured-owner",
                endpoint="https://clawhub.example",
                package="clawhub@1.2.3",
            ),
            skillhub=replace(self.config.skillhub, endpoint="https://skillhub.example"),
        )
        with patch.dict(os.environ, {"CLAWHUB_OWNER": ""}):
            result = publisher.check(("clawhub", "skillhub"))
        self.assertTrue(all(item["status"] == "ready" for item in result.values()))
        clawhub_commands = [
            command for command in runner.commands if "clawhub@1.2.3" in command
        ]
        self.assertEqual(len(clawhub_commands), 2)
        for command in clawhub_commands:
            self.assertEqual(
                command[command.index("--registry") + 1], "https://clawhub.example"
            )
        publication = next(
            command for command in clawhub_commands if "publish" in command
        )
        self.assertEqual(
            publication[publication.index("--owner") + 1], "configured-owner"
        )
        for command in runner.commands:
            if command[0] == "/bin/skillhub":
                self.assertEqual(
                    command[command.index("--host") + 1], "https://skillhub.example"
                )

    def test_nonempty_owner_override_and_empty_environment_fallback(self) -> None:
        publisher = self.publisher(FakeRunner())
        with patch.dict(os.environ, {"CLAWHUB_OWNER": "@local-owner"}):
            self.assertEqual(publisher.clawhub_owner, "local-owner")
        with patch.dict(os.environ, {"CLAWHUB_OWNER": ""}):
            self.assertEqual(publisher.clawhub_owner, self.config.clawhub.owner)

    def test_configured_node_version_is_used_when_resolving_clawhub(self) -> None:
        publisher = self.publisher(FakeRunner())
        publisher.clawhub_command = None
        publisher._config = replace(
            self.config, clawhub=replace(self.config.clawhub, node_version="24")
        )
        with patch.object(
            publishing, "resolve_clawhub_command", return_value=("/node24/npx",)
        ) as resolve:
            publisher.check(("clawhub",))
            resolve.assert_called_once_with("24")

    def test_release_configuration_is_loaded_lazily_once_from_release(self) -> None:
        with patch.object(release_state, "verify"):
            context = release_state.ReleaseContext.load(self.release_dir)
        with patch.object(
            publishing.release_config, "load_for_release", return_value=self.config
        ) as load:
            publisher = publishing.AutomatedPublisher(
                context,
                runner=FakeRunner(),
                clawhub_command=("/bin/npx",),
                skillhub_cli=Path("/bin/skillhub"),
            )
            load.assert_not_called()
            publisher.check(("clawhub", "skillhub"))
            load.assert_called_once_with(context)

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
            command
            for command in runner.commands
            if "publish" in command and "--dry-run" not in command
        ]
        self.assertEqual(real_publish_commands, [])

    def test_remote_main_change_requires_rebuild(self) -> None:
        runner = FakeRunner(remote_commit="different-commit")
        results = self.publisher(runner).check(("clawhub", "skillhub"))

        self.assertEqual(results["clawhub"]["status"], "failed")
        self.assertIn("rebuild required", results["skillhub"]["response"])
        self.assertEqual(len(runner.commands), 1)

    def test_verified_release_can_publish_after_main_advances(self) -> None:
        runner = FakeRunner(remote_commit="different-commit")
        with patch.object(release_state, "verify"):
            context = release_state.ReleaseContext.load(self.release_dir)
        publisher = publishing.AutomatedPublisher(
            context,
            runner=runner,
            require_current_main=False,
            skillhub_cli=Path("/bin/skillhub"),
            config=self.config,
        )
        results = publisher.publish(("skillhub",))
        self.assertEqual(results["skillhub"]["status"], "published")
        self.assertFalse(
            any(command[:2] == ["git", "ls-remote"] for command in runner.commands)
        )

    def test_manual_channels_use_built_archives_and_require_evidence(self) -> None:
        with patch.object(release_state, "verify"):
            context = release_state.ReleaseContext.load(self.release_dir)
        publisher = publishing.ManualPublisher(context, runner=FakeRunner())

        plan = publisher.plan(("workbuddy", "doubao"))
        self.assertEqual(plan["workbuddy"]["status"], "pending_manual")
        self.assertEqual(
            plan["doubao"]["embedded_skills"],
            [
                "ai-shifu-course-creator",
                "ai-shifu-learning-report",
                "course-direction-advisor",
            ],
        )
        self.assertEqual(
            plan["doubao"]["runtime_tests"]["recommended_instructions"],
            [
                "Released instruction one",
                "Released instruction two",
                "Released instruction three",
            ],
        )
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
