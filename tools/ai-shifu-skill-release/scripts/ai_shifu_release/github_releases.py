"""Prepare, publish, download, and verify immutable GitHub Release packages."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

from . import build
from .artifacts import CHANNEL_ORDER, artifact_path, verify_zip
from .artifacts import file_hash as sha256
from .release_state import ReleaseContext
from .source import SOURCE_SKILL_NAME
from .verify import verify

TAG_PATTERN = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PREVIEW_TAG_PATTERN = re.compile(
    r"preview-v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)-([0-9a-f]{40})-([1-9]\d*)-([1-9]\d*)$"
)


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *args], check=check, capture_output=True, text=True)


def change_notes(tag: str, commit: str) -> str:
    try:
        tags = subprocess.run(
            [
                "git",
                "for-each-ref",
                "--sort=-version:refname",
                "--format=%(refname:short)",
                "refs/tags/v*",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        previous = next(
            (
                candidate
                for candidate in tags
                if TAG_PATTERN.fullmatch(candidate)
                and candidate != tag
                and subprocess.run(
                    ["git", "merge-base", "--is-ancestor", candidate, commit],
                    capture_output=True,
                ).returncode
                == 0
            ),
            None,
        )
        span = f"{previous}..{commit}" if previous else commit
        subjects = subprocess.run(
            ["git", "log", "--format=%s", span],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        return (
            "\n".join(f"- {subject}" for subject in subjects[:30])
            or "- Initial release"
        )
    except (OSError, subprocess.CalledProcessError):
        return f"- Source commit {commit}"


def prepare_assets(
    release_dir: Path, tag: str, commit: str, destination: Path
) -> tuple[list[Path], str]:
    """Copy the four-channel attachment set from an exact tagged source build."""
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError("Tag must use vX.Y.Z")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full source commit SHA is required")
    verify(release_dir)
    report = json.loads((release_dir / "release.json").read_text(encoding="utf-8"))
    version = ".".join(match.groups())
    if report["skill"]["version"] != version or report["source"]["commit"] != commit:
        raise ValueError("Tag, source commit and package version differ")
    if report["source"]["ref"] != commit:
        raise ValueError("Release packages were not built from the exact tagged commit")
    if set(report["artifacts"]) != set(CHANNEL_ORDER):
        raise ValueError("Release must contain exactly four channel packages")

    destination.mkdir(parents=True, exist_ok=True)
    assets = []
    for channel in CHANNEL_ORDER:
        source = artifact_path(release_dir, report["artifacts"][channel]["archive"])
        name = asset_name(channel, source.name)
        target = destination / name
        target.write_bytes(source.read_bytes())
        assets.append(target)
    manifest = destination / "release.json"
    manifest.write_bytes((release_dir / "release.json").read_bytes())
    assets.append(manifest)
    checksums = destination / "SHA256SUMS"
    checksums.write_text(
        "".join(f"{sha256(asset)}  {asset.name}\n" for asset in assets),
        encoding="utf-8",
    )
    assets.append(checksums)
    notes = (
        f"AI-Shifu Skills {version}\n\n"
        f"Source commit: {commit}\n\n"
        "Packages: ClawHub and SkillHub standalone skills; WorkBuddy expert plugin; "
        "Doubao Work partner package. These are downloadable installation packages. "
        "Publication to each channel is tracked separately.\n\n"
        f"Changes:\n{change_notes(tag, commit)}\n"
    )
    return assets, notes


def publish(
    tag: str,
    commit: str,
    assets: list[Path],
    notes: str,
    *,
    draft_preview: bool = False,
    version_tag: str | None = None,
) -> str:
    if draft_preview:
        match = PREVIEW_TAG_PATTERN.fullmatch(tag)
        if (
            not match
            or version_tag != f"v{'.'.join(match.groups()[:3])}"
            or match.group(4) != commit
        ):
            raise ValueError(
                "Preview tag must contain the package version and exact source commit"
            )
        notes = "TEST DRAFT ONLY — do not publish this Release.\n\n" + notes
    elif not TAG_PATTERN.fullmatch(tag):
        raise ValueError("Published Release tag must use vX.Y.Z")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("GITHUB_REPOSITORY is required")
    existing = gh(
        "release",
        "view",
        tag,
        "--repo",
        repository,
        "--json",
        "isDraft,assets",
        check=False,
    )
    if existing.returncode:
        with tempfile.TemporaryDirectory() as temporary:
            notes_file = Path(temporary) / "notes.md"
            notes_file.write_text(notes, encoding="utf-8")
            command = [
                "release",
                "create",
                tag,
                "--repo",
                repository,
                "--draft",
                "--target",
                commit,
                "--title",
                tag,
                "--notes-file",
                str(notes_file),
            ]
            if not draft_preview:
                command.append("--verify-tag")
            gh(*command)
        existing = gh(
            "release", "view", tag, "--repo", repository, "--json", "isDraft,assets"
        )
    release = json.loads(existing.stdout)
    if draft_preview and not release["isDraft"]:
        raise ValueError("Preview Release is already public; refusing to change it")
    remote_assets = {asset["name"] for asset in release["assets"]}
    expected_assets = {asset.name for asset in assets}
    if remote_assets - expected_assets:
        raise ValueError(
            f"Unexpected existing Release assets: {sorted(remote_assets - expected_assets)}"
        )
    for asset in assets:
        if asset.name in remote_assets:
            continue
        if release["isDraft"]:
            gh("release", "upload", tag, str(asset), "--repo", repository)
        else:
            raise ValueError(
                f"Published Release is missing {asset.name}; use a new version"
            )
    final = json.loads(
        gh(
            "release", "view", tag, "--repo", repository, "--json", "isDraft,assets,url"
        ).stdout
    )
    if {item["name"] for item in final["assets"]} != expected_assets:
        raise ValueError("Release asset set is incomplete")
    with tempfile.TemporaryDirectory() as temporary:
        for asset in assets:
            gh(
                "release",
                "download",
                tag,
                "--repo",
                repository,
                "--pattern",
                asset.name,
                "--dir",
                temporary,
            )
            if sha256(Path(temporary) / asset.name) != sha256(asset):
                raise ValueError(
                    f"Published asset has different content: {asset.name}; use a new version"
                )
    if final["isDraft"] and not draft_preview:
        gh("release", "edit", tag, "--repo", repository, "--draft=false")
        final = json.loads(
            gh("release", "view", tag, "--repo", repository, "--json", "url").stdout
        )
    return final["url"]


def asset_name(channel: str, archive: str) -> str:
    """Name a GitHub attachment without collisions between registry packages."""
    name = Path(archive).name
    return f"{channel}-{name}" if channel in {"clawhub", "skillhub"} else name


def extract_archive(archive: Path, destination: Path, archive_root: str) -> None:
    """Restore regular files from a verified archive while rejecting unsafe paths."""
    verify_zip(archive)
    prefix = f"{archive_root}/"
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            if item.is_dir():
                continue
            relative = PurePosixPath(item.filename)
            if (
                not item.filename.startswith(prefix)
                or relative.is_absolute()
                or ".." in relative.parts
            ):
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
    """Reconstruct and verify a published release for internal channel submission."""
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("Tag must use vX.Y.Z")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Repository must be owner/name")
    release = json.loads(
        gh(
            "release",
            "view",
            tag,
            "--repo",
            repository,
            "--json",
            "isDraft,assets,tagName",
        ).stdout
    )
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
        gh(
            "release",
            "download",
            tag,
            "--repo",
            repository,
            "--pattern",
            name,
            "--dir",
            str(output),
        )
    manifest = output / "release.json"
    report = json.loads(manifest.read_text(encoding="utf-8"))
    archives = {
        channel: asset_name(channel, report["artifacts"][channel]["archive"])
        for channel in CHANNEL_ORDER
    }
    expected = set(archives.values()) | {"release.json", "SHA256SUMS"}
    if names != expected or {path.name for path in output.iterdir()} != expected:
        raise ValueError(
            "Release attachment set differs from the four-package contract"
        )
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
        if sha256(output / name) != digest:
            raise ValueError(f"Release attachment checksum differs: {name}")
    commit = gh(
        "api", f"repos/{repository}/commits/{tag}", "--jq", ".sha"
    ).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("The Release tag must resolve to a full source commit SHA")
    if report["source"]["commit"] != commit or report["source"]["ref"] != commit:
        raise ValueError("Release source commit differs from its tag")
    if tag != f"v{report['skill']['version']}":
        raise ValueError("Release tag differs from package version")
    release_id = report["release_id"]
    if not isinstance(release_id, str) or not release_id:
        raise ValueError("Release ID must be a nonempty string")
    release_dir = artifact_path(output, release_id)
    release_dir.mkdir()
    (release_dir / "release.json").write_bytes(manifest.read_bytes())
    for channel, name in archives.items():
        record = report["artifacts"][channel]
        archived = output / name
        target_archive = artifact_path(release_dir, record["archive"])
        target_archive.parent.mkdir(parents=True, exist_ok=True)
        target_archive.write_bytes(archived.read_bytes())
        if "directory" in record:
            target_directory = artifact_path(release_dir, record["directory"])
            extract_archive(archived, target_directory, record["archive_root"])
    verify(release_dir)
    verify_tagged_source(release_dir, repository, commit, tag[1:])
    return release_dir


def verify_tagged_source(
    release_dir: Path, repository: str, commit: str, version: str
) -> None:
    """Anchor downloaded packages to the requested repository's exact tag tree."""
    report = json.loads((release_dir / "release.json").read_text(encoding="utf-8"))
    release = ReleaseContext(release_dir, report)
    if release.source_repo.casefold() != repository.casefold():
        raise ValueError("Release source repository differs from requested repository")
    with tempfile.TemporaryDirectory(prefix="ai-shifu-source-check-") as temporary:
        expected_dir = build.build(
            SimpleNamespace(
                source_repo_url=f"https://github.com/{repository}.git",
                source_ref=commit,
                expected_version=version,
                skill_name=SOURCE_SKILL_NAME,
                output=temporary,
            )
        )
        expected = json.loads(
            (expected_dir / "release.json").read_text(encoding="utf-8")
        )
        for channel in CHANNEL_ORDER:
            actual_archive = artifact_path(
                release_dir, report["artifacts"][channel]["archive"]
            )
            expected_archive = artifact_path(
                expected_dir, expected["artifacts"][channel]["archive"]
            )
            if sha256(actual_archive) != sha256(expected_archive):
                raise ValueError(f"{channel} archive differs from tagged source")
        for field in (
            "schema_version",
            "release_id",
            "release_sha256",
            "source_committed_at",
            "skill",
            "artifacts",
        ):
            if report.get(field) != expected[field]:
                raise ValueError(f"Release {field} differs from tagged source")
