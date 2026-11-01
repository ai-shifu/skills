"""Open a version-bump PR against the ai-shifu/skills source repository.

The bump never merges anything: it clones the source repository, updates
version metadata while preserving the skill body, pushes a branch, and opens
a PR. The primary skill and CLI share one release version. Merging is a
deliberate human gate; the release build packs from the remote main branch.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from .skill_metadata import SEMVER, read_frontmatter, update_skill_frontmatter
from .source import run

PUSH_REPOSITORY = "git@github.com:ai-shifu/skills.git"
BUMP_LEVELS = ("major", "minor", "patch")
PRIMARY_SKILL = "ai-shifu-course-creator"
CLI_PACKAGE = "@ai-shifu/cli"


def update_cli_version(clone: Path, skill_name: str, current: str, new: str) -> bool:
    """Keep CLI version metadata aligned when bumping the primary skill."""
    if skill_name != PRIMARY_SKILL:
        return False
    package_file = clone / "package.json"
    if not package_file.is_file():
        return False  # Older skill-only source revisions remain supported.
    package = json.loads(package_file.read_text(encoding="utf-8"))
    if package.get("name") != CLI_PACKAGE or package.get("version") != current:
        raise ValueError("CLI package version must match the primary skill before a bump")
    package["version"] = new
    lock_file = clone / "package-lock.json"
    lock = None
    if lock_file.is_file():
        lock = json.loads(lock_file.read_text(encoding="utf-8"))
        if lock.get("name") != CLI_PACKAGE or lock.get("version") != current:
            raise ValueError("CLI lockfile version must match the primary skill before a bump")
        root_package = lock.get("packages", {}).get("")
        if not isinstance(root_package, dict) or root_package.get("version") != current:
            raise ValueError("CLI lockfile root package must match the primary skill before a bump")
        lock["version"] = new
        root_package["version"] = new
    package_file.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if lock is not None:
        lock_file.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


class BumpOptions(Protocol):
    """Inputs consumed by the version-bump workflow."""

    skill_name: str
    skill_version: str
    level: str
    draft: bool
    no_pr: bool
    repo_url: str


def semver_key(version: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(version)
    if not match:
        raise ValueError(f"Invalid SemVer: {version!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bumped_version(current: str, level: str) -> str:
    major, minor, patch = semver_key(current)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unknown bump level: {level!r}")


def bump(args: BumpOptions) -> dict:
    if bool(args.skill_version) == bool(args.level):
        raise ValueError("Provide exactly one of --skill-version or --level")
    with tempfile.TemporaryDirectory(prefix="ai-shifu-bump-") as tmp:
        workdir = Path(tmp)
        clone = workdir / "skills"
        run(
            "git",
            "clone",
            "--quiet",
            "--depth=1",
            args.repo_url,
            str(clone),
            cwd=workdir,
        )
        skill_file = clone / "skills" / args.skill_name / "SKILL.md"
        current = read_frontmatter(skill_file)["version"]
        new_version = args.skill_version or bumped_version(current, args.level)
        if semver_key(new_version) <= semver_key(current):
            raise ValueError(
                f"New version {new_version} must be greater than current {current}"
            )
        text = skill_file.read_bytes().decode("utf-8")
        updated = update_skill_frontmatter(
            text, {"version": new_version}, str(skill_file)
        )
        skill_file.write_bytes(updated.encode("utf-8"))
        cli_updated = update_cli_version(clone, args.skill_name, current, new_version)

        branch = f"bump/{args.skill_name}-v{new_version}"
        title = f"chore: bump version to v{new_version}"
        body = (
            f"Changed:\nRaised the {args.skill_name} skill"
            f"{' and CLI package' if cli_updated else ''} version from {current} to {new_version}.\n\n"
            f"Benefit:\nChannels and users can identify and receive the {new_version} release."
        )
        run("git", "checkout", "--quiet", "-b", branch, cwd=clone)
        run("git", "add", "--all", cwd=clone)
        run("git", "commit", "--quiet", "-m", title, "-m", body, cwd=clone)
        run("git", "push", "--quiet", "-u", "origin", branch, cwd=clone)

        result = {
            "skill_name": args.skill_name,
            "previous_version": current,
            "new_version": new_version,
            "branch": branch,
            "pr_url": "",
        }
        if args.no_pr:
            result["next_step"] = (
                f"Open a PR for branch {branch} manually and merge it before building."
            )
        else:
            command = [
                "gh",
                "pr",
                "create",
                "--head",
                branch,
                "--base",
                "main",
                "--title",
                title,
                "--body",
                body,
            ]
            if args.draft:
                command.append("--draft")
            try:
                result["pr_url"] = run(*command, cwd=clone)
                result["next_step"] = (
                    "Review and merge the PR manually, then run build."
                )
            except (subprocess.CalledProcessError, FileNotFoundError) as error:
                detail = (getattr(error, "stderr", "") or "").strip() or str(error)
                result["next_step"] = (
                    f"Branch {branch} was pushed, but `gh pr create` failed ({detail}); open the PR manually."
                )
    return result
