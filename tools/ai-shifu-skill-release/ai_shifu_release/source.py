"""Fetch and export the selected Git source and publisher identity."""

from __future__ import annotations

import io
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

import tomllib

from ai_shifu_release.artifacts import is_excluded

SOURCE_REPOSITORY = "https://github.com/ai-shifu/skills.git"


SOURCE_REF = "main"


def run(*args: str, cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def git_metadata(project: Path) -> tuple[str | None, str | None, bool | None]:
    """Best-effort builder provenance. Degrades to None outside a git work tree
    so the skill can build when copied into a plain (non-git) directory. These
    fields are provenance-only and never feed release_sha256."""
    try:
        commit = run("git", "rev-parse", "HEAD^{commit}", cwd=project)
        remote = run("git", "remote", "get-url", "origin", cwd=project)
        dirty = bool(run("git", "status", "--porcelain", cwd=project))
        return commit, remote, dirty
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None, None, None


def load_publisher(source_repo: Path, commit: str) -> dict[str, str]:
    """Read the publisher identity committed with the selected source revision."""
    path = "tools/ai-shifu-skill-release/publisher.toml"
    try:
        contents = run("git", "show", f"{commit}:{path}", cwd=source_repo)
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"Missing publisher configuration at {path}") from exc
    config = tomllib.loads(contents)
    publisher = config.get("publisher")
    if not isinstance(publisher, dict):
        raise ValueError("publisher.toml must contain a [publisher] section")
    for field in ("name", "email"):
        value = publisher.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"publisher.toml publisher.{field} must be non-empty")
        if "__PUBLISHER_" in value or value in {"your-name", "you@example.com"}:
            raise ValueError(f"publisher.toml publisher.{field} contains a placeholder")
    return {"name": publisher["name"], "email": publisher["email"]}


def export_tree(
    repo: Path,
    commit: str,
    source_path: str,
    destination: Path,
    *,
    normalize_git_modes: bool = False,
) -> None:
    archive = subprocess.run(
        ["git", "archive", "--format=tar", f"{commit}:{source_path}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        for member in tar.getmembers():
            relative = PurePosixPath(member.name)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or is_excluded(relative)
            ):
                continue
            target = destination.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tar.extractfile(member)
                if source is None:
                    raise ValueError(f"Cannot extract {member.name}")
                target.write_bytes(source.read())
                # Git tracks regular files as 100644 or 100755. Archive tar headers
                # may add group write bits that a checkout would not have.
                mode = (
                    (0o755 if member.mode & 0o111 else 0o644)
                    if normalize_git_modes
                    else member.mode
                )
                target.chmod(mode)
            elif member.issym():
                continue
            else:
                raise ValueError(f"Unsupported archive member: {member.name}")


def export_skill(repo: Path, commit: str, skill_name: str, destination: Path) -> None:
    export_tree(repo, commit, f"skills/{skill_name}", destination)


def fetch_source(
    repository: str, destination: Path, source_ref: str = SOURCE_REF
) -> tuple[str, str]:
    if not re.fullmatch(r"[0-9a-fA-F]{40}|main", source_ref):
        raise ValueError("Source ref must be main or a full commit SHA")
    destination.mkdir(parents=True)
    run("git", "init", "--quiet", cwd=destination)
    run("git", "remote", "add", "origin", repository, cwd=destination)
    fetch_ref = "refs/heads/main" if source_ref == "main" else source_ref
    run("git", "fetch", "--quiet", "--depth=1", "origin", fetch_ref, cwd=destination)
    commit = run("git", "rev-parse", "FETCH_HEAD^{commit}", cwd=destination)
    if source_ref != "main" and commit.lower() != source_ref.lower():
        raise ValueError("Fetched source commit does not match requested commit")
    remote = run("git", "remote", "get-url", "origin", cwd=destination)
    return commit, remote
