#!/usr/bin/env python3
"""Open a version-bump PR against the ai-shifu/skills source repository.

The bump never merges anything: it clones the source repository, changes only
the SKILL.md version field (the body must stay byte-identical), pushes a
branch, and opens a PR. Merging is a deliberate human gate; the release build
always packs from the remote main branch.
"""

from __future__ import annotations

import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_release import SEMVER, read_frontmatter, run, update_skill_frontmatter

PUSH_REPOSITORY = "git@github.com:ai-shifu/skills.git"
BUMP_LEVELS = ("major", "minor", "patch")


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


def append_changelog(path: Path, version: str, note: str) -> None:
    date = datetime.now(timezone.utc).date().isoformat()
    section = f"## {version} - {date}\n\n- {note}\n"
    if not path.exists():
        path.write_text(f"# Changelog\n\n{section}", encoding="utf-8")
        return
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith("# "):
            insert_at = index + 1
            break
    lines.insert(insert_at, f"\n{section}")
    path.write_text("".join(lines), encoding="utf-8")


def bump(args) -> dict:
    if bool(args.skill_version) == bool(args.level):
        raise ValueError("Provide exactly one of --skill-version or --level")
    with tempfile.TemporaryDirectory(prefix="ai-shifu-bump-") as tmp:
        workdir = Path(tmp)
        clone = workdir / "skills"
        run("git", "clone", "--quiet", "--depth=1", args.repo_url, str(clone), cwd=workdir)
        skill_file = clone / "skills" / args.skill_name / "SKILL.md"
        current = read_frontmatter(skill_file)["version"]
        new_version = args.skill_version or bumped_version(current, args.level)
        if semver_key(new_version) <= semver_key(current):
            raise ValueError(f"New version {new_version} must be greater than current {current}")
        text = skill_file.read_bytes().decode("utf-8")
        updated = update_skill_frontmatter(text, {"version": new_version}, str(skill_file))
        skill_file.write_bytes(updated.encode("utf-8"))
        if args.changelog:
            append_changelog(skill_file.parent / "CHANGELOG.md", new_version, args.changelog)

        branch = f"bump/{args.skill_name}-v{new_version}"
        title = f"chore: bump {args.skill_name} to {new_version}"
        body = (
            f"Changed:\nRaised the {args.skill_name} skill version from {current} to {new_version}.\n\n"
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
            result["next_step"] = f"Open a PR for branch {branch} manually and merge it before building."
        else:
            command = ["gh", "pr", "create", "--head", branch, "--base", "main", "--title", title, "--body", body]
            if args.draft:
                command.append("--draft")
            try:
                result["pr_url"] = run(*command, cwd=clone)
                result["next_step"] = "Review and merge the PR manually, then run build."
            except (subprocess.CalledProcessError, FileNotFoundError) as error:
                detail = (getattr(error, "stderr", "") or "").strip() or str(error)
                result["next_step"] = (
                    f"Branch {branch} was pushed, but `gh pr create` failed ({detail}); open the PR manually."
                )
    return result
