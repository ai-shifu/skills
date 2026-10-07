#!/usr/bin/env python3
"""Download and verify the immutable packages of a published GitHub Release."""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_release, github_release


def asset_name(channel: str, archive: str) -> str:
    name = Path(archive).name
    return f"{channel}-{name}" if channel in {"clawhub", "skillhub"} else name


def extract_archive(archive: Path, destination: Path, archive_root: str) -> None:
    build_release.verify_zip(archive)
    prefix = f"{archive_root}/"
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            if item.is_dir():
                continue
            relative = PurePosixPath(item.filename)
            if not item.filename.startswith(prefix) or relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unexpected ZIP path: {item.filename}")
            mode = item.external_attr >> 16
            if not stat.S_ISREG(mode):
                raise ValueError(f"Non-file ZIP entry: {item.filename}")
            target = destination.joinpath(*relative.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ValueError(f"Duplicate ZIP entry: {item.filename}")
            target.write_bytes(bundle.read(item))
            target.chmod(stat.S_IMODE(mode))


def download(tag: str, repository: str, output: Path) -> Path:
    if not github_release.TAG_PATTERN.fullmatch(tag):
        raise ValueError("Tag must use skills-vX.Y.Z")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Repository must be owner/name")
    release = json.loads(github_release.gh(
        "release", "view", tag, "--repo", repository, "--json", "isDraft,assets,tagName"
    ).stdout)
    if release["isDraft"] or release["tagName"] != tag:
        raise ValueError("A published Release with the requested tag is required")
    names = {item["name"] for item in release["assets"]}
    if len(names) != len(release["assets"]):
        raise ValueError("Duplicate Release attachment names")
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", name) for name in names):
        raise ValueError("Release attachment name is unsafe")
    output = output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    for name in sorted(names):
        github_release.gh("release", "download", tag, "--repo", repository,
                          "--pattern", name, "--dir", str(output))
    manifest = output / "release.json"
    report = json.loads(manifest.read_text(encoding="utf-8"))
    archives = {channel: asset_name(channel, report["artifacts"][channel]["archive"])
                for channel in build_release.CHANNEL_ORDER}
    expected = set(archives.values()) | {"release.json", "SHA256SUMS"}
    if names != expected or {path.name for path in output.iterdir()} != expected:
        raise ValueError("Release attachment set differs from the four-package contract")
    lines = (output / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    checksums = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if not match or match.group(2) in checksums:
            raise ValueError("Invalid or duplicate SHA256SUMS entry")
        checksums[match.group(2)] = match.group(1)
    if set(checksums) != expected - {"SHA256SUMS"}:
        raise ValueError("SHA256SUMS does not cover every Release attachment")
    for name, digest in checksums.items():
        if github_release.sha256(output / name) != digest:
            raise ValueError(f"Release attachment checksum differs: {name}")
    commit = github_release.gh("api", f"repos/{repository}/commits/{tag}",
                               "--jq", ".sha").stdout.strip()
    if report["source"]["commit"] != commit or report["source"]["ref"] != commit:
        raise ValueError("Release source commit differs from its tag")
    if tag != f"skills-v{report['skill']['version']}":
        raise ValueError("Release tag differs from package version")
    release_dir = output / report["release_id"]
    release_dir.mkdir()
    (release_dir / "release.json").write_bytes(manifest.read_bytes())
    for channel, name in archives.items():
        record = report["artifacts"][channel]
        archived = output / name
        target_archive = build_release.artifact_path(release_dir, record["archive"])
        target_archive.parent.mkdir(parents=True, exist_ok=True)
        target_archive.write_bytes(archived.read_bytes())
        if "directory" in record:
            target_directory = build_release.artifact_path(release_dir, record["directory"])
            extract_archive(archived, target_directory, record["archive_root"])
    build_release.verify(release_dir)
    return release_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(download(args.tag, args.repo, args.output))


if __name__ == "__main__":
    main()
