#!/usr/bin/env python3
"""Publish a verified release to Standalone Skill registries."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from scripts import build_release, doubao_package


AUTOMATED_TARGETS = ("clawhub", "skillhub")
MANUAL_TARGETS = ("workbuddy", "qclaw", "doubao")
MANIFEST_REQUIRED_AUTOMATED_TARGETS = AUTOMATED_TARGETS
MANIFEST_REQUIRED_MANUAL_TARGETS = ("workbuddy", "qclaw")
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


@dataclass(frozen=True)
class ReleaseContext:
    directory: Path
    metadata: dict

    @classmethod
    def load(cls, directory: Path) -> "ReleaseContext":
        directory = directory.expanduser().resolve()
        build_release.verify(directory)
        metadata = json.loads((directory / "release.json").read_text(encoding="utf-8"))
        return cls(directory, metadata)

    def channel_directory(self, target: str) -> Path:
        relative = self.metadata["artifacts"][target]["directory"]
        return build_release.artifact_path(self.directory, relative)

    @property
    def skill_name(self) -> str:
        return self.metadata["skill"]["name"]

    @property
    def version(self) -> str:
        return self.metadata["skill"]["version"]

    @property
    def display_name(self) -> str:
        return self.metadata["skill"]["display_name"]

    @property
    def source_commit(self) -> str:
        return self.metadata["source"]["commit"]

    @property
    def source_repository(self) -> str:
        return self.metadata["source"]["repository"]

    @property
    def source_repo(self) -> str:
        match = re.search(r"github\.com(?::|/)([^/]+/[^/]+?)(?:\.git)?$", self.source_repository)
        if not match:
            raise ValueError(f"Unsupported GitHub repository URL: {self.source_repository}")
        return match.group(1)

    def artifact_sha(self, target: str) -> str:
        artifact = self.metadata["artifacts"][target]
        return artifact.get("tree_sha256", artifact.get("sha256", ""))

    def assert_remote_main(self, runner: Callable[[list[str]], CommandResult]) -> None:
        response = runner(["git", "ls-remote", self.source_repository, "refs/heads/main"])
        remote_commit = response.stdout.split(maxsplit=1)[0] if response.stdout else ""
        if remote_commit != self.source_commit:
            raise ValueError(
                f"GitHub main changed: release={self.source_commit}, remote={remote_commit or 'unavailable'}; rebuild required"
            )


def resolve_clawhub_command() -> tuple[str, ...]:
    # Portable resolution order: explicit override, then a plain `npx` on PATH,
    # then the nvm-based fallback for machines that only expose Node via nvm.
    # ClawHub still requires Node 22; when relying on PATH make sure `npx`
    # resolves to a Node 22 runtime (see references/publishing.md).
    override = os.environ.get("CLAWHUB_NPX")
    if override:
        return (str(Path(override).expanduser().resolve()),)
    npx = shutil.which("npx")
    if npx:
        return (npx,)
    return _resolve_clawhub_via_nvm()


def _resolve_clawhub_via_nvm() -> tuple[str, ...]:
    result = run_command(["zsh", "-lc", "source ~/.nvm/nvm.sh && nvm which 22"])
    node = Path(result.stdout)
    npx_cli = node.parent.parent / "lib/node_modules/npm/bin/npx-cli.js"
    if not node.is_file() or not npx_cli.is_file():
        raise ValueError(
            "Cannot locate a Node runtime for clawhub. Set CLAWHUB_NPX to an npx "
            "binary, put `npx` (Node 22) on PATH, or install Node 22 via nvm."
        )
    path = f"{node.parent}:{os.environ.get('PATH', '')}"
    return ("/usr/bin/env", f"PATH={path}", str(node), str(npx_cli))


def resolve_skillhub_cli() -> Path:
    override = os.environ.get("SKILLHUB_CLI")
    command = override or shutil.which("skillhub")
    if not command:
        raise ValueError("skillhub CLI is not installed; see https://skillhub.cn/install/skillhub.md")
    return Path(command).expanduser().resolve()


class ReleaseReport:
    def __init__(self, release: ReleaseContext) -> None:
        self.release = release
        self.path = release.directory / "release-report.json"

    def update(self, channel_results: dict) -> None:
        report = self._load()
        report["updated_at"] = datetime.now(timezone.utc).isoformat()
        report["channels"].update(channel_results)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    def _load(self) -> dict:
        if self.path.exists():
            report = json.loads(self.path.read_text(encoding="utf-8"))
            if report.get("release_id") != self.release.metadata["release_id"]:
                raise ValueError("release-report.json belongs to a different release")
            if report.get("release_sha256") != self.release.metadata["release_sha256"]:
                raise ValueError("release-report.json references different artifact content")
            return report
        return {
            "schema_version": 1,
            "release_id": self.release.metadata["release_id"],
            "release_sha256": self.release.metadata["release_sha256"],
            "channels": {},
        }


class AutomatedPublisher:
    def __init__(
        self,
        release: ReleaseContext,
        *,
        runner: Callable[[list[str]], CommandResult] = run_command,
        clawhub_command: tuple[str, ...] | None = None,
        skillhub_cli: Path | None = None,
    ) -> None:
        self.release = release
        self.runner = runner
        self.clawhub_command = clawhub_command
        self.skillhub_cli = skillhub_cli
        self.report = ReleaseReport(release)

    def check(self, targets: tuple[str, ...]) -> dict:
        results = {}
        try:
            self.release.assert_remote_main(self.runner)
        except (CommandFailure, ValueError) as error:
            results = {target: self._result(target, "failed", str(error)) for target in targets}
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
            self.runner([*self._clawhub_command(), "--yes", "clawhub@latest", "whoami"])
        elif target == "skillhub":
            self.runner([str(self._skillhub_cli()), "auth", "whoami"])
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
                *self._clawhub_command(),
                "--yes",
                "clawhub@latest",
                "publish",
                common[0],
                "--slug",
                self.release.skill_name,
                "--name",
                self.release.display_name,
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
                "--json",
            ]
        else:
            raise ValueError(f"Unsupported target: {target}")
        if dry_run:
            command.append("--dry-run")
        return command

    def _clawhub_command(self) -> tuple[str, ...]:
        if self.clawhub_command is None:
            self.clawhub_command = resolve_clawhub_command()
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
        results = {target: self._base_result(target, "pending_manual") for target in targets}
        self.report.update(results)
        return results

    def record(self, target: str, status: str, *, url: str = "", note: str = "") -> dict:
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
        archive = build_release.artifact_path(self.release.directory, artifact["archive"])
        result = {
            "status": status,
            "version": artifact["version"],
            "embedded_skill_version": self.release.version,
            "artifact": artifact["archive"],
            "upload_path": str(archive),
            "artifact_sha256": artifact.get("archive_sha256", artifact.get("sha256", "")),
        }
        if artifact.get("embedded_skills"):
            result["embedded_skills"] = sorted(artifact["embedded_skills"])
        if target == "doubao":
            profile = doubao_package.load_profile(
                Path(__file__).resolve().parents[1] / "channels/doubao/profile.json"
            )
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
