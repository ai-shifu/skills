"""Publish a verified release to Standalone Skill registries."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import config as release_config
from .artifacts import artifact_path
from .release_state import ReleaseContext, ReleaseReport

AUTOMATED_TARGETS = ("clawhub", "skillhub")
MANUAL_TARGETS = ("workbuddy", "doubao")
MANUAL_STATUSES = ("submitted", "verified", "failed")


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str = ""


class CommandFailure(RuntimeError):
    def __init__(self, command: list[str], output: str):
        super().__init__(output)
        self.command = command
        self.output = output


def run_command(command: list[str]) -> CommandResult:
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        output = (error.stderr or error.stdout or str(error)).strip()
        raise CommandFailure(command, output) from error
    return CommandResult(result.stdout.strip(), result.stderr.strip())


def resolve_clawhub_command(node_version: str) -> tuple[str, ...]:
    # Portable resolution order: explicit override, then a plain `npx` on PATH,
    # then the nvm-based fallback for machines that only expose Node via nvm.
    # PATH must expose the Node runtime selected by release.toml.
    override = os.environ.get("CLAWHUB_NPX")
    if override:
        return (str(Path(override).expanduser().resolve()),)
    npx = shutil.which("npx")
    if npx:
        return (npx,)
    return _resolve_clawhub_via_nvm(node_version)


def _resolve_clawhub_via_nvm(node_version: str) -> tuple[str, ...]:
    result = run_command(
        [
            "zsh",
            "-lc",
            'source ~/.nvm/nvm.sh && nvm which "$1"',
            "release-node",
            node_version,
        ]
    )
    node = Path(result.stdout)
    npx_cli = node.parent.parent / "lib/node_modules/npm/bin/npx-cli.js"
    if not node.is_file() or not npx_cli.is_file():
        raise ValueError(
            "Cannot locate a Node runtime for clawhub. Set CLAWHUB_NPX to an npx "
            f"binary, put `npx` (Node {node_version}) on PATH, or install Node {node_version} via nvm."
        )
    path = f"{node.parent}:{os.environ.get('PATH', '')}"
    return ("/usr/bin/env", f"PATH={path}", str(node), str(npx_cli))


def resolve_skillhub_cli() -> Path:
    override = os.environ.get("SKILLHUB_CLI")
    command = override or shutil.which("skillhub")
    if not command:
        raise ValueError(
            "skillhub CLI is not installed; see https://skillhub.cn/install/skillhub.md"
        )
    return Path(command).expanduser().resolve()


class AutomatedPublisher:
    def __init__(
        self,
        release: ReleaseContext,
        *,
        runner: Callable[[list[str]], CommandResult] = run_command,
        clawhub_command: tuple[str, ...] | None = None,
        clawhub_owner: str = "",
        skillhub_cli: Path | None = None,
        require_current_main: bool = True,
        config: release_config.ReleaseConfig | None = None,
    ) -> None:
        self.release = release
        self.runner = runner
        self.clawhub_command = clawhub_command
        self._clawhub_owner = clawhub_owner
        self._config = config
        self.skillhub_cli = skillhub_cli
        self.require_current_main = require_current_main
        self.report = ReleaseReport(release)

    @property
    def config(self) -> release_config.ReleaseConfig:
        """Load channel settings from this release's exact source commit once."""
        if self._config is None:
            self._config = release_config.load_for_release(self.release)
        return self._config

    @property
    def clawhub_owner(self) -> str:
        """Resolve the same publisher owner for local and downloaded releases."""
        owner = (
            self._clawhub_owner.strip()
            or os.environ.get("CLAWHUB_OWNER", "").strip()
            or self.config.clawhub.owner
        ).lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", owner):
            raise ValueError("ClawHub publisher owner is not configured")
        return owner

    def _clawhub_invocation(self) -> list[str]:
        return [
            *self._clawhub_command(),
            "--yes",
            self.config.clawhub.package,
            "--registry",
            self.config.clawhub.endpoint,
        ]

    def existing_clawhub_version(self) -> bool:
        """Return whether the configured owner's exact version already exists."""
        identity = f"@{self.clawhub_owner}/{self.release.skill_name}"
        command = [
            *self._clawhub_invocation(),
            "inspect",
            identity,
            "--version",
            self.release.version,
            "--json",
        ]
        try:
            self.runner(command)
            return True
        except CommandFailure as error:
            if re.search(
                r"\b(not found|404|no such version)\b", error.output, re.IGNORECASE
            ):
                return False
            raise

    def existing_skillhub_version(self) -> bool:
        """Verify an existing version against this release's SkillHub archive."""
        archive = self.release.metadata["artifacts"]["skillhub"]["archive"]
        command = [
            str(self._skillhub_cli()),
            "verify",
            f"{self.release.skill_name}@{self.release.version}",
            "--zip",
            str(artifact_path(self.release.directory, archive)),
            "--host",
            self.config.skillhub.endpoint,
        ]
        try:
            response = self.runner(command)
            if not re.search(
                r"签名与内容校验通过|signature and content verified|verification passed",
                response.stdout,
                re.IGNORECASE,
            ):
                raise ValueError(
                    "SkillHub version exists but its content could not be verified"
                )
            return True
        except CommandFailure as error:
            if re.search(
                r"找不到该版本|version not found|404", error.output, re.IGNORECASE
            ):
                return False
            raise

    def check(self, targets: tuple[str, ...]) -> dict:
        results = {}
        if self.require_current_main:
            try:
                self.release.assert_remote_main(self.runner)
            except (CommandFailure, ValueError) as error:
                results = {
                    target: self._result(target, "failed", str(error))
                    for target in targets
                }
                self.report.update(results)
                return results
        for target in targets:
            try:
                self._authenticate(target)
                response = self.runner(self._publish_command(target, dry_run=True))
                results[target] = self._result(target, "ready", response.stdout)
            except (CommandFailure, ValueError) as error:
                results[target] = self._result(target, "failed", str(error))
        self.report.update(results)
        return results

    def publish(self, targets: tuple[str, ...]) -> dict:
        checks = self.check(targets)
        if any(result["status"] != "ready" for result in checks.values()):
            return checks
        results = dict(checks)
        for target in targets:
            if checks[target]["status"] != "ready":
                continue
            try:
                response = self.runner(self._publish_command(target, dry_run=False))
                results[target] = self._result(target, "published", response.stdout)
            except (CommandFailure, ValueError) as error:
                results[target] = self._result(target, "failed", str(error))
            self.report.update(results)
        return results

    def _authenticate(self, target: str) -> None:
        if target == "clawhub":
            self.runner([*self._clawhub_invocation(), "whoami"])
        elif target == "skillhub":
            self.runner(
                [
                    str(self._skillhub_cli()),
                    "auth",
                    "whoami",
                    "--host",
                    self.config.skillhub.endpoint,
                ]
            )
        else:
            raise ValueError(f"Unsupported target: {target}")

    def _publish_command(self, target: str, *, dry_run: bool) -> list[str]:
        common = [
            str(self.release.channel_directory(target)),
            "--version",
            self.release.version,
        ]
        changelog = f"Release {self.release.version} from source commit {self.release.source_commit}"
        if target == "clawhub":
            command = [
                *self._clawhub_invocation(),
                "skill",
                "publish",
                common[0],
                "--slug",
                self.release.skill_name,
                "--name",
                self.release.display_name,
                "--owner",
                self.clawhub_owner,
                *common[1:],
                "--source-repo",
                self.release.source_repo,
                "--source-commit",
                self.release.source_commit,
                "--source-path",
                f"skills/{self.release.skill_name}",
                "--changelog",
                changelog,
                "--json",
            ]
        elif target == "skillhub":
            command = [
                str(self._skillhub_cli()),
                "publish",
                *common,
                "--changelog",
                changelog,
                "--host",
                self.config.skillhub.endpoint,
            ]
        else:
            raise ValueError(f"Unsupported target: {target}")
        if dry_run:
            command.append("--dry-run")
        return command

    def _clawhub_command(self) -> tuple[str, ...]:
        if self.clawhub_command is None:
            self.clawhub_command = resolve_clawhub_command(
                self.config.clawhub.node_version
            )
        return self.clawhub_command

    def _skillhub_cli(self) -> Path:
        if self.skillhub_cli is None:
            self.skillhub_cli = resolve_skillhub_cli()
        return self.skillhub_cli

    def _result(self, target: str, status: str, output: str) -> dict:
        try:
            response = json.loads(output) if output else None
        except json.JSONDecodeError:
            response = output
        return {
            "status": status,
            "version": self.release.version,
            "source_commit": self.release.source_commit,
            "artifact_sha256": self.release.artifact_sha(target),
            "response": response,
        }


class ManualPublisher:
    def __init__(
        self,
        release: ReleaseContext,
        *,
        runner: Callable[[list[str]], CommandResult] = run_command,
    ) -> None:
        self.release = release
        self.runner = runner
        self.report = ReleaseReport(release)

    def plan(self, targets: tuple[str, ...]) -> dict:
        self.release.assert_remote_main(self.runner)
        results = {
            target: self._base_result(target, "pending_manual") for target in targets
        }
        self.report.update(results)
        return results

    def record(
        self, target: str, status: str, *, url: str = "", note: str = ""
    ) -> dict:
        if target not in MANUAL_TARGETS:
            raise ValueError(f"Unsupported manual target: {target}")
        if status not in MANUAL_STATUSES:
            raise ValueError(f"Unsupported manual status: {status}")
        if status in {"submitted", "verified"} and not url:
            raise ValueError(f"{status} requires --url as publication evidence")
        result = self._base_result(target, status)
        if url:
            result["url"] = url
        if note:
            result["note"] = note
        self.report.update({target: result})
        return result

    def _base_result(self, target: str, status: str) -> dict:
        artifact = self.release.metadata["artifacts"][target]
        archive = artifact_path(self.release.directory, artifact["archive"])
        result = {
            "status": status,
            "version": artifact["version"],
            "embedded_skill_version": self.release.version,
            "artifact": artifact["archive"],
            "upload_path": str(archive),
            "artifact_sha256": artifact.get(
                "archive_sha256", artifact.get("sha256", "")
            ),
        }
        if artifact.get("embedded_skills"):
            result["embedded_skills"] = sorted(artifact["embedded_skills"])
        if target == "doubao":
            profile = json.loads(artifact["source_profile_json"])
            result["runtime_tests"] = {
                "recommended_instructions": profile["recommended_instructions"],
                "required_checks": [
                    "three_complete_outputs",
                    "all_embedded_skills_triggered",
                    "missing_information_not_invented",
                    "privacy_boundary_preserved",
                ],
            }
        return result


def expand_automated_targets(target: str) -> tuple[str, ...]:
    return AUTOMATED_TARGETS if target == "all" else (target,)


def expand_manual_targets(target: str) -> tuple[str, ...]:
    return MANUAL_TARGETS if target == "all" else (target,)
