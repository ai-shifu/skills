"""Build standalone packages for ClawHub and SkillHub."""

from __future__ import annotations

from ai_shifu_release.artifacts import file_hash, scan_tree, tree_hash, write_zip
from ai_shifu_release.channels import BuildContext
from ai_shifu_release.skill_metadata import (
    build_skill_variant,
    channel_frontmatter_overrides,
)


def build_clawhub_skillhub_artifact(channel: str, context: BuildContext) -> dict:
    overrides = channel_frontmatter_overrides(
        channel, context.skill_name, context.display_name
    )
    directory = context.artifacts / channel / context.skill_name
    build_skill_variant(
        context.source_skill,
        directory,
        overrides,
        top_level_version=context.version if channel == "skillhub" else "",
    )
    scan_tree(directory)
    archive = (
        context.artifacts / channel / f"{context.skill_name}-{context.version}.zip"
    )
    write_zip(directory, archive, context.skill_name)
    record = {
        "directory": context.record_path(directory),
        "tree_sha256": tree_hash(directory),
        "archive": context.record_path(archive),
        "archive_sha256": file_hash(archive),
        "archive_root": context.skill_name,
        "version_management": "standalone",
    }
    if overrides:
        record["frontmatter_overrides"] = overrides
    return record
