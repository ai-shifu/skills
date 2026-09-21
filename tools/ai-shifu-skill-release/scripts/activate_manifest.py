#!/usr/bin/env python3
"""Open a website-manifest PR to activate a released skill version.

The last release stage: after the channels are published, update the public
manifest (zh/skill-manifests/<skill_name>.json in ai-shifu/ai-shifu-website)
so installed skills see the new version. This command only edits the file and
opens a PR — merging the PR and rebuilding/deploying the site Docker image
stay manual, so going live always requires a human.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_release import SEMVER, SOURCE_REPOSITORY, parse_frontmatter, run, split_skill_document
from scripts.bump_version import semver_key
from scripts.publish_release import (
    MANIFEST_REQUIRED_AUTOMATED_TARGETS,
    MANIFEST_REQUIRED_MANUAL_TARGETS,
)

WEBSITE_REPOSITORY = "git@github.com:ai-shifu/ai-shifu-website.git"
MANIFEST_BASE_URL = "https://ai-shifu.cn/skill-manifests"
AUTOMATED_OK = {"published", "verified"}
MANUAL_OK = {"submitted", "verified"}


def load_release(release_dir: Path) -> tuple[str, str, str]:
    metadata = json.loads((release_dir / "release.json").read_text(encoding="utf-8"))
    skill = metadata["skill"]
    return skill["name"], skill["version"], metadata.get("source", {}).get("commit", "")


def collect_changes(
    repo_url: str, skill_name: str, previous_version: str, upper_commit: str, workdir: Path
) -> list[str]:
    """Commit subjects (squash-merged PR titles) that touched this skill between
    the commit where SKILL.md last became previous_version and upper_commit."""
    clone = workdir / "skills-history"
    run("git", "clone", "--quiet", "--single-branch", repo_url, str(clone), cwd=workdir)
    skill_md = f"skills/{skill_name}/SKILL.md"
    boundary = ""
    seen_previous = False
    for sha in run("git", "log", "--format=%H", "--", skill_md, cwd=clone).split():
        frontmatter, _ = split_skill_document(run("git", "show", f"{sha}:{skill_md}", cwd=clone), sha)
        version = parse_frontmatter(frontmatter).get("version", "")
        if version == previous_version:
            seen_previous = True
            boundary = sha
        elif seen_previous:
            break
    if not boundary:
        raise ValueError(f"Cannot locate the commit where {skill_name} became {previous_version}")
    subjects = run(
        "git", "log", "--format=%s", f"{boundary}..{upper_commit or 'HEAD'}",
        "--", f"skills/{skill_name}/", cwd=clone,
    )
    bump_noise = re.compile(rf"bump {re.escape(skill_name)} to ")
    return [line for line in subjects.splitlines() if line.strip() and not bump_noise.search(line)]


def compose_notes(version: str, changes: list[str]) -> str:
    if not changes:
        return f"Release {version}"
    cleaned = [re.sub(r"^\w+(\(.*?\))?!?:\s*", "", change) for change in changes]
    notes = f"Release {version}: " + "; ".join(cleaned)
    return notes[:497] + "..." if len(notes) > 500 else notes


def assert_channels_ready(release_dir: Path, allow_pending: tuple[str, ...] = ()) -> None:
    report_path = release_dir / "release-report.json"
    if not report_path.exists():
        raise ValueError("release-report.json not found; run check/publish and record-manual first")
    channels = json.loads(report_path.read_text(encoding="utf-8")).get("channels", {})
    problems = []
    for target in MANIFEST_REQUIRED_AUTOMATED_TARGETS:
        status = channels.get(target, {}).get("status", "missing")
        if status not in AUTOMATED_OK:
            problems.append(f"{target}={status}")
    for target in MANIFEST_REQUIRED_MANUAL_TARGETS:
        if target in allow_pending:
            continue  # explicitly waived by the release owner; recorded in the PR
        status = channels.get(target, {}).get("status", "missing")
        if status not in MANUAL_OK:
            problems.append(f"{target}={status}")
    if problems:
        raise ValueError(
            "Channels are not ready for manifest activation: " + ", ".join(problems)
            + ". Publish the automated channels and record the manual uploads first."
        )


def update_manifest(manifest_path: Path, version: str, notes: str) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["latest"] = version
    manifest["notes"] = notes
    manifest["published_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not SEMVER.fullmatch(manifest.get("latest", "")):
        raise ValueError(f"Invalid latest version: {manifest.get('latest')!r}")
    if not SEMVER.fullmatch(manifest.get("min_supported", "")):
        raise ValueError(f"Invalid min_supported version: {manifest.get('min_supported')!r}")
    if semver_key(manifest["min_supported"]) > semver_key(manifest["latest"]):
        raise ValueError("min_supported must not exceed latest")
    if not str(manifest.get("update_url", "")).startswith("https://"):
        raise ValueError("update_url must be HTTPS")
    if "schema_version" not in manifest:
        raise ValueError("manifest is missing schema_version")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def check_online(skill_name: str, version: str) -> dict:
    cache_buster = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    url = f"{MANIFEST_BASE_URL}/{skill_name}.json?t={cache_buster}"
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=10) as response:
        manifest = json.loads(response.read().decode("utf-8"))
    online = manifest.get("latest", "")
    return {
        "url": url,
        "online_latest": online,
        "expected": version,
        "active": online == version,
        "note": "" if online == version else "Edge caches hold entries up to ~5 minutes; retry after deploying.",
    }


def activate(args) -> dict:
    release_dir = Path(args.release_dir).expanduser().resolve()
    skill_name, version, source_commit = load_release(release_dir)
    if args.check_online:
        return check_online(skill_name, version)
    if args.notes and args.auto_notes:
        raise ValueError("Use either --notes or --auto-notes, not both")
    waived = tuple(args.allow_pending)
    assert_channels_ready(release_dir, waived)

    with tempfile.TemporaryDirectory(prefix="ai-shifu-manifest-") as tmp:
        workdir = Path(tmp)
        clone = workdir / "website"
        run("git", "clone", "--quiet", "--depth=1", args.repo_url, str(clone), cwd=workdir)
        manifest_path = clone / "zh/skill-manifests" / f"{skill_name}.json"
        if not manifest_path.exists():
            raise ValueError(f"Manifest not found in website repository: {manifest_path.name}")
        notes = args.notes
        changes: list[str] = []
        if args.auto_notes:
            previous_latest = json.loads(manifest_path.read_text(encoding="utf-8")).get("latest", "")
            changes = collect_changes(SOURCE_REPOSITORY, skill_name, previous_latest, source_commit, workdir)
            notes = compose_notes(version, changes)
        notes = notes or f"Release {version}"
        manifest = update_manifest(manifest_path, version, notes)

        branch = f"codex/bump-{skill_name}-manifest-v{version}"
        title = f"chore: bump {skill_name} manifest to {version}"
        run("git", "checkout", "--quiet", "-b", branch, cwd=clone)
        run("git", "add", "--all", cwd=clone)
        run("git", "commit", "--quiet", "-m", title, cwd=clone)
        run("git", "push", "--quiet", "-u", "origin", branch, cwd=clone)

        result = {
            "skill_name": skill_name,
            "version": version,
            "branch": branch,
            "manifest": manifest,
            "changes": changes,
            "waived_channels": list(waived),
            "pr_url": "",
            "next_step": "",
        }
        manual_tail = (
            "After merging, rebuild and deploy the zh site Docker image, then run "
            "activate-manifest --check-online to confirm the live manifest."
        )
        pr_body = f"Sets latest to {version}. {manual_tail}"
        if waived:
            pr_body += f" Waived channels (handled offline by the release owner): {', '.join(waived)}."
        if args.no_pr:
            result["next_step"] = f"Open a PR for branch {branch} manually. {manual_tail}"
        else:
            command = [
                "gh", "pr", "create", "--head", branch, "--base", "main",
                "--title", title, "--body", pr_body,
            ]
            if args.draft:
                command.append("--draft")
            try:
                result["pr_url"] = run(*command, cwd=clone)
                result["next_step"] = f"Review and merge the PR manually. {manual_tail}"
            except (subprocess.CalledProcessError, FileNotFoundError) as error:
                detail = (getattr(error, "stderr", "") or "").strip() or str(error)
                result["next_step"] = (
                    f"Branch {branch} was pushed, but `gh pr create` failed ({detail}); open the PR manually. {manual_tail}"
                )
    return result
