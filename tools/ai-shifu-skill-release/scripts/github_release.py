#!/usr/bin/env python3
"""Publish a verified, immutable GitHub Release from a tagged build."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_release


CHANNELS = build_release.CHANNEL_ORDER
TAG_PATTERN = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PREVIEW_TAG_PATTERN = re.compile(
    r"preview-v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)-([0-9a-f]{40})-([1-9]\d*)-([1-9]\d*)$"
)


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *args], check=check, capture_output=True, text=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def change_notes(tag: str, commit: str) -> str:
    try:
        tags = subprocess.run(
            ["git", "for-each-ref", "--sort=-version:refname", "--format=%(refname:short)",
             "refs/tags/v*"], capture_output=True, text=True, check=True
        ).stdout.splitlines()
        previous = next((candidate for candidate in tags if TAG_PATTERN.fullmatch(candidate) and
                         candidate != tag and
                         subprocess.run(["git", "merge-base", "--is-ancestor", candidate, commit],
                                        capture_output=True).returncode == 0), None)
        span = f"{previous}..{commit}" if previous else commit
        subjects = subprocess.run(["git", "log", "--format=%s", span],
                                  capture_output=True, text=True, check=True).stdout.splitlines()
        return "\n".join(f"- {subject}" for subject in subjects[:30]) or "- Initial release"
    except (OSError, subprocess.CalledProcessError):
        return f"- Source commit {commit}"


def prepare_assets(release_dir: Path, tag: str, commit: str, destination: Path) -> tuple[list[Path], str]:
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError("Tag must use vX.Y.Z")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full source commit SHA is required")
    build_release.verify(release_dir)
    report = json.loads((release_dir / "release.json").read_text(encoding="utf-8"))
    version = ".".join(match.groups())
    if report["skill"]["version"] != version or report["source"]["commit"] != commit:
        raise ValueError("Tag, source commit and package version differ")
    if report["source"]["ref"] != commit:
        raise ValueError("Release packages were not built from the exact tagged commit")
    if set(report["artifacts"]) != set(CHANNELS):
        raise ValueError("Release must contain exactly four channel packages")

    destination.mkdir(parents=True, exist_ok=True)
    assets = []
    for channel in CHANNELS:
        source = build_release.artifact_path(release_dir, report["artifacts"][channel]["archive"])
        name = f"{channel}-{source.name}" if channel in {"clawhub", "skillhub"} else source.name
        target = destination / name
        target.write_bytes(source.read_bytes())
        assets.append(target)
    manifest = destination / "release.json"
    manifest.write_bytes((release_dir / "release.json").read_bytes())
    assets.append(manifest)
    checksums = destination / "SHA256SUMS"
    checksums.write_text("".join(f"{sha256(asset)}  {asset.name}\n" for asset in assets), encoding="utf-8")
    assets.append(checksums)
    notes = (
        f"AI-Shifu Skills {version}\n\n"
        f"Source commit: {commit}\n\n"
        "Packages: ClawHub and SkillHub standalone skills; WorkBuddy expert plugin; "
        "Doubao Work partner package. These are downloadable installation packages. "
        "Publication to each platform is tracked separately.\n\n"
        f"Changes:\n{change_notes(tag, commit)}\n"
    )
    return assets, notes


def publish(tag: str, commit: str, assets: list[Path], notes: str,
            *, draft_preview: bool = False, version_tag: str | None = None) -> None:
    if draft_preview:
        match = PREVIEW_TAG_PATTERN.fullmatch(tag)
        if not match or version_tag != f"v{'.'.join(match.groups()[:3])}" or match.group(4) != commit:
            raise ValueError("Preview tag must contain the package version and exact source commit")
        notes = "TEST DRAFT ONLY — do not publish this Release.\n\n" + notes
    elif not TAG_PATTERN.fullmatch(tag):
        raise ValueError("Published Release tag must use vX.Y.Z")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("GITHUB_REPOSITORY is required")
    existing = gh("release", "view", tag, "--repo", repository, "--json", "isDraft,assets", check=False)
    if existing.returncode:
        with tempfile.TemporaryDirectory() as temporary:
            notes_file = Path(temporary) / "notes.md"
            notes_file.write_text(notes, encoding="utf-8")
            command = ["release", "create", tag, "--repo", repository, "--draft",
                       "--target", commit, "--title", tag, "--notes-file", str(notes_file)]
            if not draft_preview:
                command.append("--verify-tag")
            gh(*command)
        existing = gh("release", "view", tag, "--repo", repository, "--json", "isDraft,assets")
    release = json.loads(existing.stdout)
    if draft_preview and not release["isDraft"]:
        raise ValueError("Preview Release is already public; refusing to change it")
    remote_assets = {asset["name"] for asset in release["assets"]}
    expected_assets = {asset.name for asset in assets}
    if remote_assets - expected_assets:
        raise ValueError(f"Unexpected existing Release assets: {sorted(remote_assets - expected_assets)}")
    for asset in assets:
        if asset.name in remote_assets:
            continue
        if release["isDraft"]:
            gh("release", "upload", tag, str(asset), "--repo", repository)
        else:
            raise ValueError(f"Published Release is missing {asset.name}; use a new version")
    final = json.loads(gh("release", "view", tag, "--repo", repository,
                          "--json", "isDraft,assets,url").stdout)
    if {item["name"] for item in final["assets"]} != expected_assets:
        raise ValueError("Release asset set is incomplete")
    with tempfile.TemporaryDirectory() as temporary:
        for asset in assets:
            gh("release", "download", tag, "--repo", repository, "--pattern", asset.name,
               "--dir", temporary)
            if sha256(Path(temporary) / asset.name) != sha256(asset):
                raise ValueError(f"Published asset has different content: {asset.name}; use a new version")
    if final["isDraft"] and not draft_preview:
        gh("release", "edit", tag, "--repo", repository, "--draft=false")
    print(final["url"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--prepare-only", action="store_true", help="Prepare assets without creating a Release")
    parser.add_argument("--draft-preview-tag", help="Create and verify a branch-only test Draft Release")
    parser.add_argument("--output", type=Path, help="Required output directory for --prepare-only")
    args = parser.parse_args()
    if args.prepare_only and args.draft_preview_tag:
        parser.error("--prepare-only and --draft-preview-tag cannot be combined")
    if args.prepare_only:
        if args.output is None:
            parser.error("--prepare-only requires --output")
        assets, _ = prepare_assets(args.release_dir.resolve(), args.tag, args.commit,
                                   args.output.resolve())
        print("\n".join(str(asset) for asset in assets))
        return
    with tempfile.TemporaryDirectory() as temporary:
        assets, notes = prepare_assets(args.release_dir.resolve(), args.tag, args.commit,
                                       Path(temporary))
        publish(args.draft_preview_tag or args.tag, args.commit, assets, notes,
                draft_preview=bool(args.draft_preview_tag), version_tag=args.tag)


if __name__ == "__main__":
    main()
