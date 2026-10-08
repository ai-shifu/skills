"""Build and validate the WorkBuddy expert plugin package."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from ai_shifu_release.artifacts import (
    copy_tree,
    directory_contents,
    file_hash,
    scan_tree,
    write_zip,
)
from ai_shifu_release.channels import BuildContext
from ai_shifu_release.config import channel_path
from ai_shifu_release.skill_metadata import (
    SEMVER,
    build_skill_variant,
    channel_frontmatter_overrides,
    parse_frontmatter,
    split_skill_document,
)


def _workbuddy_localized(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"WorkBuddy {field} must contain en and zh")
    localized = value
    for language in ("en", "zh"):
        if (
            not isinstance(localized.get(language), str)
            or not localized[language].strip()
        ):
            raise ValueError(f"WorkBuddy {field}.{language} must be a non-empty string")
    return localized


def _workbuddy_reference(
    contents: dict[str, bytes], reference: object, field: str
) -> str:
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError(f"WorkBuddy {field} must be a non-empty path")
    relative = PurePosixPath(reference.removeprefix("./"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"WorkBuddy {field} must stay inside the package")
    path = relative.as_posix()
    if path not in contents:
        raise ValueError(f"WorkBuddy {field} does not exist: {path}")
    return path


def _workbuddy_agent_localized(frontmatter: str, field: str) -> dict[str, str]:
    lines = frontmatter.splitlines()
    marker = f"{field}:"
    try:
        start = lines.index(marker)
    except ValueError as exc:
        raise ValueError(f"WorkBuddy agent {field} is required") from exc
    localized: dict[str, str] = {}
    for line in lines[start + 1 :]:
        if line and not line[0].isspace():
            break
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key in {"en", "zh"}:
            localized[key] = value.strip().strip("'\"")
    for language in ("en", "zh"):
        if not localized.get(language):
            raise ValueError(
                f"WorkBuddy agent {field}.{language} must be a non-empty string"
            )
    return localized


def validate_workbuddy_package_contents(
    contents: dict[str, bytes], expected_version: str
) -> None:
    config_path = ".codebuddy-plugin/plugin.json"
    if any(path.startswith(".workbuddy-plugin/") for path in contents):
        raise ValueError("WorkBuddy legacy .workbuddy-plugin directory is not allowed")
    if config_path not in contents:
        raise ValueError(f"WorkBuddy config is missing: {config_path}")
    if "README.md" not in contents:
        raise ValueError("WorkBuddy README.md is required")

    try:
        plugin = json.loads(contents[config_path].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("WorkBuddy plugin.json is not valid UTF-8 JSON") from exc
    if not isinstance(plugin, dict):
        raise ValueError("WorkBuddy plugin.json must contain an object")

    required_strings = (
        "name",
        "version",
        "description",
        "expertType",
        "agentName",
        "avatar",
        "categoryId",
        "plugin",
    )
    for field in required_strings:
        if not isinstance(plugin.get(field), str) or not plugin[field].strip():
            raise ValueError(f"WorkBuddy {field} must be a non-empty string")
    if plugin["version"] != expected_version or not SEMVER.fullmatch(plugin["version"]):
        raise ValueError("WorkBuddy version must match the release version")
    if plugin["expertType"] != "agent":
        raise ValueError("WorkBuddy expertType must be agent")
    if plugin["plugin"] != plugin["name"]:
        raise ValueError("WorkBuddy plugin must match name")
    if plugin["categoryId"] != "15-Education":
        raise ValueError("WorkBuddy AI-Shifu categoryId must be 15-Education")

    author = plugin.get("author")
    if not isinstance(author, dict):
        raise ValueError("WorkBuddy author must contain name and email")
    for field in ("name", "email"):
        if not isinstance(author.get(field), str) or not author[field].strip():
            raise ValueError(f"WorkBuddy author.{field} must be a non-empty string")
        if "__PUBLISHER_" in author[field] or author[field] in {
            "your-name",
            "you@example.com",
        }:
            raise ValueError(f"WorkBuddy author.{field} contains a placeholder")

    for field in (
        "displayName",
        "profession",
        "displayDescription",
        "defaultInitPrompt",
    ):
        _workbuddy_localized(plugin.get(field), field)
    description_length = len(plugin["displayDescription"]["zh"])
    if not 40 <= description_length <= 50:
        raise ValueError(
            "WorkBuddy displayDescription.zh must contain 40-50 characters"
        )

    tags = plugin.get("tags")
    if not isinstance(tags, list) or len(tags) != 3:
        raise ValueError("WorkBuddy tags must contain exactly 3 items")
    for index, tag in enumerate(tags):
        _workbuddy_localized(tag, f"tags[{index}]")

    quick_prompts = plugin.get("quickPrompts")
    if not isinstance(quick_prompts, list) or len(quick_prompts) != 3:
        raise ValueError("WorkBuddy quickPrompts must contain exactly 3 items")
    for index, prompt in enumerate(quick_prompts):
        _workbuddy_localized(prompt, f"quickPrompts[{index}]")
    if plugin["defaultInitPrompt"] != quick_prompts[0]:
        raise ValueError("WorkBuddy defaultInitPrompt must match quickPrompts[0]")

    agents = plugin.get("agents")
    if not isinstance(agents, list) or not agents:
        raise ValueError("WorkBuddy agents must contain at least one path")
    agent_paths = [
        _workbuddy_reference(contents, reference, f"agents[{index}]")
        for index, reference in enumerate(agents)
    ]
    primary_agent = f"agents/{plugin['agentName']}.md"
    if primary_agent not in agent_paths:
        raise ValueError("WorkBuddy agentName must match an agents path")

    skills = plugin.get("skills", [])
    if not isinstance(skills, list):
        raise ValueError("WorkBuddy skills must be a path list")
    for index, reference in enumerate(skills):
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError(f"WorkBuddy skills[{index}] must be a non-empty path")
        relative = PurePosixPath(reference.removeprefix("./"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"WorkBuddy skills[{index}] must stay inside the package")
        prefix = f"{relative.as_posix().rstrip('/')}/"
        if not any(path.startswith(prefix) for path in contents):
            raise ValueError(f"WorkBuddy skills[{index}] does not exist: {relative}")

    avatar_path = _workbuddy_reference(contents, plugin["avatar"], "avatar")
    avatar = contents[avatar_path]
    if len(avatar) > 500 * 1024:
        raise ValueError("WorkBuddy avatar must not exceed 500KB")
    if (
        len(avatar) < 24
        or avatar[:8] != b"\x89PNG\r\n\x1a\n"
        or avatar[12:16] != b"IHDR"
    ):
        raise ValueError("WorkBuddy avatar must be a PNG")
    width = int.from_bytes(avatar[16:20], "big")
    height = int.from_bytes(avatar[20:24], "big")
    if (width, height) != (512, 512):
        raise ValueError("WorkBuddy avatar must be 512x512 pixels")

    try:
        agent_text = contents[primary_agent].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("WorkBuddy agent must be UTF-8 Markdown") from exc
    agent_frontmatter, _ = split_skill_document(agent_text, primary_agent)
    agent_fields = parse_frontmatter(agent_frontmatter)
    if agent_fields.get("name") != plugin["agentName"]:
        raise ValueError("WorkBuddy agent name must match agentName")
    if not agent_fields.get("description"):
        raise ValueError("WorkBuddy agent description is required")
    if "tools" in agent_fields:
        raise ValueError("WorkBuddy agent must not declare tools")
    for field in ("displayName", "profession"):
        if _workbuddy_agent_localized(agent_frontmatter, field) != plugin[field]:
            raise ValueError(f"WorkBuddy agent {field} must match plugin.json")


def validate_workbuddy_package(root: Path, expected_version: str) -> None:
    validate_workbuddy_package_contents(directory_contents(root), expected_version)


def build_workbuddy_artifact(channel: str, context: BuildContext) -> dict:
    overrides = channel_frontmatter_overrides(
        channel, context.skill_name, context.display_name
    )
    root_name = f"workbuddy-ai-shifu-{context.version}"
    stage_dir = context.artifacts / channel / root_name
    copy_tree(
        channel_path(context.channels, context.config.workbuddy.template_dir),
        stage_dir,
        ignored={"skills", "build-zip.sh"},
    )
    copy_tree(context.channels / "avatars", stage_dir / "avatars")
    stage_plugin_path = stage_dir / ".codebuddy-plugin/plugin.json"
    stage_plugin = json.loads(stage_plugin_path.read_text(encoding="utf-8"))
    stage_plugin["version"] = context.version
    stage_plugin["author"] = context.publisher
    stage_plugin_path.write_text(
        json.dumps(stage_plugin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    build_skill_variant(
        context.source_skill, stage_dir / "skills" / context.skill_name, overrides
    )
    validate_workbuddy_package(stage_dir, context.version)
    scan_tree(stage_dir)
    archive = context.artifacts / channel / f"{root_name}.zip"
    write_zip(stage_dir, archive, root_name)
    return {
        "archive": context.record_path(archive),
        "sha256": file_hash(archive),
        "version": context.version,
        "embedded_skill_root": f"{root_name}/skills/{context.skill_name}",
        "frontmatter_overrides": overrides,
    }
