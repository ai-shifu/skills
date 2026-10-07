"""Verify the release manifest and every recorded channel artifact."""

from __future__ import annotations

import json
from pathlib import Path

from ai_shifu_release.artifacts import (
    CHANNEL_ORDER,
    RELEASE_SCHEMA_VERSION,
    artifact_path,
    assert_contents_equal,
    content_hash,
    directory_contents,
    expected_variant_contents,
    file_hash,
    release_hash,
    scan_tree,
    tree_hash,
    verify_zip,
    zip_subtree_contents,
)
from ai_shifu_release.channels.doubao import verify_doubao_artifact
from ai_shifu_release.channels.workbuddy import validate_workbuddy_package_contents
from ai_shifu_release.skill_metadata import (
    channel_frontmatter_overrides,
    parse_frontmatter,
    split_skill_document,
)


def verify_canonical_skill(
    release_dir: Path, artifact: dict, skill: dict
) -> dict[str, bytes]:
    directory = artifact_path(release_dir, artifact["directory"])
    if tree_hash(directory) != artifact["tree_sha256"]:
        raise ValueError("clawhub directory hash mismatch")
    canonical = directory_contents(directory)
    canonical_skill = canonical["SKILL.md"]
    if content_hash(canonical_skill) != skill["source_skill_sha256"]:
        raise ValueError("clawhub SKILL.md differs from GitHub source")
    frontmatter, body = split_skill_document(
        canonical_skill.decode("utf-8"), "clawhub SKILL.md"
    )
    fields = parse_frontmatter(frontmatter)
    if (
        fields.get("version") != skill["version"]
        or fields.get("version_management") != "standalone"
    ):
        raise ValueError("clawhub metadata does not match release.json")
    if content_hash(body.encode("utf-8")) != skill["body_sha256"]:
        raise ValueError("clawhub SKILL.md body differs from GitHub source")
    return canonical


def verify_channel_artifact(
    channel: str,
    artifact: dict,
    release_dir: Path,
    skill: dict,
    canonical: dict[str, bytes],
) -> list[str]:
    expected_overrides = channel_frontmatter_overrides(
        channel, skill["name"], skill["display_name"]
    )
    if (artifact.get("frontmatter_overrides") or {}) != expected_overrides:
        raise ValueError(f"{channel} frontmatter override policy mismatch")
    expected = expected_variant_contents(
        canonical,
        expected_overrides,
        f"{channel} SKILL.md",
        top_level_version=skill["version"] if channel == "skillhub" else "",
    )
    hashes: list[str] = []
    if "directory" in artifact:
        directory = artifact_path(release_dir, artifact["directory"])
        if tree_hash(directory) != artifact["tree_sha256"]:
            raise ValueError(f"{channel} directory hash mismatch")
        scan_tree(directory)
        assert_contents_equal(
            directory_contents(directory), expected, f"{channel} directory"
        )
        hashes.append(artifact["tree_sha256"])
        archive_sha = artifact["archive_sha256"]
        archive_root = artifact["archive_root"]
    else:
        archive_sha = artifact["sha256"]
        archive_root = artifact["embedded_skill_root"]
    archive = artifact_path(release_dir, artifact["archive"])
    if file_hash(archive) != archive_sha:
        raise ValueError(f"{channel} archive hash mismatch")
    verify_zip(archive)
    if channel == "workbuddy":
        marker = "/skills/"
        embedded_root = artifact["embedded_skill_root"]
        if marker not in embedded_root:
            raise ValueError("workbuddy embedded skill root is invalid")
        package_root = embedded_root.split(marker, 1)[0]
        expected_root = f"workbuddy-ai-shifu-{skill['version']}"
        if package_root != expected_root:
            raise ValueError("workbuddy archive root mismatch")
        validate_workbuddy_package_contents(
            zip_subtree_contents(archive, package_root), skill["version"]
        )
    assert_contents_equal(
        zip_subtree_contents(archive, archive_root), expected, f"{channel} archive"
    )
    hashes.append(archive_sha)
    return hashes


def verify(release_dir: Path) -> None:
    report = json.loads((release_dir / "release.json").read_text())
    schema_version = report.get("schema_version")
    if schema_version != RELEASE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported release schema {schema_version!r}; rebuild with schema {RELEASE_SCHEMA_VERSION}"
        )

    skill = report["skill"]
    artifacts = report["artifacts"]
    canonical = verify_canonical_skill(release_dir, artifacts["clawhub"], skill)
    hashes: list[str] = []
    for channel in CHANNEL_ORDER:
        if channel == "doubao":
            hashes.extend(
                verify_doubao_artifact(
                    artifacts[channel],
                    release_dir,
                    skill,
                    report["source"]["commit"],
                    canonical,
                )
            )
        else:
            hashes.extend(
                verify_channel_artifact(
                    channel, artifacts[channel], release_dir, skill, canonical
                )
            )
    expected_release_sha = release_hash(hashes)
    if report.get("release_sha256") != expected_release_sha:
        raise ValueError("Release hash mismatch")
