"""Read and render skill metadata without changing document bodies."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def channel_frontmatter_overrides(
    channel: str, skill_name: str, display_name: str
) -> dict[str, str]:
    if channel == "clawhub":
        return {}
    if channel == "skillhub":
        return {"slug": skill_name, "displayName": display_name}
    if channel == "workbuddy":
        return {"version_management": "plugin"}
    raise ValueError(f"Unsupported channel: {channel}")


def split_skill_document(text: str, source: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError(f"Missing YAML frontmatter: {source}")
    delimiter = "\n---\n"
    end = text.find(delimiter, 4)
    if end < 0:
        raise ValueError(f"Unclosed YAML frontmatter: {source}")
    return text[4:end], text[end + len(delimiter) :]


def parse_frontmatter(frontmatter: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    in_metadata = False
    for line in frontmatter.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            key = key.strip()
            in_metadata = key == "metadata"
            fields[key] = value.strip().strip("'\"")
        elif (
            in_metadata
            and line.startswith("  ")
            and not line.startswith("   ")
            and ":" in line
        ):
            key, value = line.strip().split(":", 1)
            if key in {"version", "version_management"}:
                fields.setdefault(key, value.strip().strip("'\""))
    return fields


def read_skill_document(skill_file: Path) -> tuple[str, str]:
    text = skill_file.read_bytes().decode("utf-8")
    return split_skill_document(text, str(skill_file))


def read_frontmatter(skill_file: Path) -> dict[str, str]:
    frontmatter, _ = read_skill_document(skill_file)
    fields = parse_frontmatter(frontmatter)
    version = fields.get("version", "")
    if not SEMVER.fullmatch(version):
        raise ValueError(f"Invalid SemVer in {skill_file}: {version!r}")
    if fields.get("version_management") not in {"standalone", "plugin"}:
        raise ValueError(f"Invalid version_management in {skill_file}")
    return fields


def format_frontmatter_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]*", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def update_skill_frontmatter(text: str, updates: dict[str, str], source: str) -> str:
    frontmatter, body = split_skill_document(text, source)
    lines = frontmatter.split("\n")
    for key, value in updates.items():
        pattern = re.compile(rf"^{re.escape(key)}:\s*.*$")
        indexes = [index for index, line in enumerate(lines) if pattern.fullmatch(line)]
        nested_indexes = []
        metadata_index = None
        if key in {"version", "version_management"}:
            in_metadata = False
            for index, line in enumerate(lines):
                if line and not line[0].isspace():
                    in_metadata = line == "metadata:"
                    if in_metadata:
                        metadata_index = index
                elif (
                    in_metadata and line.startswith("  ") and not line.startswith("   ")
                ):
                    if pattern.fullmatch(line[2:]):
                        nested_indexes.append(index)
        if len(indexes) + len(nested_indexes) > 1:
            raise ValueError(f"Duplicate {key} in YAML frontmatter: {source}")
        replacement = f"{key}: {format_frontmatter_value(value)}"
        if indexes:
            lines[indexes[0]] = replacement
        elif nested_indexes:
            lines[nested_indexes[0]] = f"  {replacement}"
        elif metadata_index is not None:
            lines.insert(metadata_index + 1, f"  {replacement}")
        else:
            lines.append(replacement)
    updated_frontmatter = "\n".join(lines)
    updated = f"---\n{updated_frontmatter}\n---\n{body}"
    _, updated_body = split_skill_document(updated, source)
    if updated_body != body:
        raise ValueError(f"SKILL.md body changed while updating frontmatter: {source}")
    return updated


def render_skill_variant(
    text: str, updates: dict[str, str], source: str, *, top_level_version: str = ""
) -> str:
    updated = update_skill_frontmatter(text, updates, source)
    if not top_level_version:
        return updated
    frontmatter, body = split_skill_document(updated, source)
    lines = frontmatter.split("\n")
    indexes = [
        index
        for index, line in enumerate(lines)
        if re.fullmatch(r"version:\s*.*", line)
    ]
    if len(indexes) > 1:
        raise ValueError(f"Duplicate top-level version: {source}")
    replacement = f"version: {format_frontmatter_value(top_level_version)}"
    if indexes:
        lines[indexes[0]] = replacement
    else:
        lines.append(replacement)
    joined = "\n".join(lines)
    return f"---\n{joined}\n---\n{body}"


def build_skill_variant(
    source: Path,
    destination: Path,
    updates: dict[str, str],
    *,
    top_level_version: str = "",
) -> None:
    shutil.copytree(source, destination)
    if not updates and not top_level_version:
        return
    skill_file = destination / "SKILL.md"
    text = skill_file.read_bytes().decode("utf-8")
    updated = render_skill_variant(
        text, updates, str(skill_file), top_level_version=top_level_version
    )
    skill_file.write_bytes(updated.encode("utf-8"))
