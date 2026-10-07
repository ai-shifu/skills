"""Verified release metadata and durable channel publication reports."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from .artifacts import artifact_path
from .verify import verify


class CommandOutput(Protocol):
    """The output needed to compare a release with the remote source."""

    stdout: str


@dataclass(frozen=True)
class ReleaseContext:
    directory: Path
    metadata: dict

    @classmethod
    def load(cls, directory: Path) -> "ReleaseContext":
        directory = directory.expanduser().resolve()
        verify(directory)
        metadata = json.loads((directory / "release.json").read_text(encoding="utf-8"))
        return cls(directory, metadata)

    def channel_directory(self, target: str) -> Path:
        relative = self.metadata["artifacts"][target]["directory"]
        return artifact_path(self.directory, relative)

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
        match = re.search(
            r"github\.com(?::|/)([^/]+/[^/]+?)(?:\.git)?$", self.source_repository
        )
        if not match:
            raise ValueError(
                f"Unsupported GitHub repository URL: {self.source_repository}"
            )
        return match.group(1)

    def artifact_sha(self, target: str) -> str:
        artifact = self.metadata["artifacts"][target]
        return artifact.get("tree_sha256", artifact.get("sha256", ""))

    def assert_remote_main(self, runner: Callable[[list[str]], CommandOutput]) -> None:
        response = runner(
            ["git", "ls-remote", self.source_repository, "refs/heads/main"]
        )
        remote_commit = response.stdout.split(maxsplit=1)[0] if response.stdout else ""
        if remote_commit != self.source_commit:
            raise ValueError(
                f"GitHub main changed: release={self.source_commit}, remote={remote_commit or 'unavailable'}; rebuild required"
            )


class ReleaseReport:
    def __init__(self, release: ReleaseContext) -> None:
        self.release = release
        self.path = release.directory / "release-report.json"

    def update(self, channel_results: dict) -> None:
        report = self._load()
        report["updated_at"] = datetime.now(timezone.utc).isoformat()
        report["channels"].update(channel_results)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, self.path)

    def _load(self) -> dict:
        if self.path.exists():
            report = json.loads(self.path.read_text(encoding="utf-8"))
            if report.get("release_id") != self.release.metadata["release_id"]:
                raise ValueError("release-report.json belongs to a different release")
            if report.get("release_sha256") != self.release.metadata["release_sha256"]:
                raise ValueError(
                    "release-report.json references different artifact content"
                )
            return report
        return {
            "schema_version": 1,
            "release_id": self.release.metadata["release_id"],
            "release_sha256": self.release.metadata["release_sha256"],
            "channels": {},
        }
