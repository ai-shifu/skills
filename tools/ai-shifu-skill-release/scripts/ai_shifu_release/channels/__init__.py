"""Shared inputs supplied to channel package builders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildContext:
    source_skill: Path
    source_skills: dict[str, Path]
    source_commit: str
    channels: Path
    stage: Path
    skill_name: str
    version: str
    display_name: str
    publisher: dict[str, str]

    @property
    def artifacts(self) -> Path:
        return self.stage / "artifacts"

    def record_path(self, path: Path) -> str:
        return path.relative_to(self.stage).as_posix()
