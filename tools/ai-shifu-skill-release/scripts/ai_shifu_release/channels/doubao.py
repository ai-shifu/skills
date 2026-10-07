"""Build, render, and validate the Doubao Work partner package."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import struct
import unicodedata
from pathlib import Path, PurePosixPath

from ai_shifu_release.artifacts import (
    artifact_path,
    assert_contents_equal,
    content_hash,
    copy_tree,
    directory_contents,
    directory_manifest,
    expected_variant_contents,
    file_hash,
    manifest_tree_hash,
    scan_tree,
    tree_hash,
    verify_zip,
    write_zip,
    zip_subtree_contents,
)
from ai_shifu_release.channels import BuildContext
from ai_shifu_release.config import channel_path
from ai_shifu_release.skill_metadata import (
    build_skill_variant,
    read_skill_document,
    split_skill_document,
    update_skill_frontmatter,
)
from ai_shifu_release.skill_metadata import parse_frontmatter as parse_skill_frontmatter

# Localized platform values and package copy must retain their Chinese wording.
ALLOWED_TAGS = {
    "内容创作",
    "办公提效",
    "产品研发",
    "金融与理财",
    "电商运营",
    "短剧与短视频",
    "数据分析",
    "学习教育",
    "求职与人事",
    "市场营销",
    "销售与客户",
    "经营管理",
    "商业研究",
}


ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


SKILL_NAME_PATTERN = ID_PATTERN


FORBIDDEN_WORDS = (
    "保证",
    "必过",
    "稳赚",
    "某公司",
    "XX 行业",
    "一站式",
    "全面赋能",
    "一键",
    "TODO",
    "FIXME",
    "待替换",
    "占位符",
)


TEMPLATE_RESIDUE = ("TODO", "FIXME", "待替换", "占位符")


EXTERNAL_INPUT_PATTERN = re.compile(r"上传|附件|提供材料|把.*发给我|这份文件")


AI_SHIFU_SPACING_PATTERN = re.compile(r"AI\s+师傅")


LEAK_PATTERNS = (
    re.compile(r"/Users/[^/\s]+/"),
    re.compile(r"/home/[^/\s]+/"),
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"localhost:\d+", re.IGNORECASE),
    re.compile(r"\b10(?:\.\d{1,3}){3}\b"),
    re.compile(r"\b192\.168(?:\.\d{1,3}){2}\b"),
)


REQUIRED_WORKSPACE_FILES = ("IDENTITY.md", "USER.md", "SOUL.md", "AGENTS.md")


SKILL_PROFILE_FIELDS = {"name", "display_name"}


def load_profile(path: Path) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    validate_profile(profile)
    return profile


def text_length(value: str) -> int:
    units = 0
    for character in value:
        if character.isspace():
            continue
        units += 2 if unicodedata.east_asian_width(character) in {"W", "F", "A"} else 1
    return math.ceil(units / 2)


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def welcome_message(profile: dict) -> str:
    lines = [profile["welcome_intro"], "", "你可以直接使用以下指令："]
    for instruction in profile["recommended_instructions"]:
        lines.append(f"- {instruction}")
    lines.extend(
        [
            "",
            "信息不足时，我会说明尚未验证的部分，并交付可继续补充的结构或检查清单。",
        ]
    )
    return "\n".join(lines)


def render_agent_yml(
    profile: dict, source_frontmatter: dict[str, dict[str, str]]
) -> str:
    expected_names = {skill["name"] for skill in profile["skills"]}
    if set(source_frontmatter) != expected_names:
        raise ValueError("Doubao source frontmatter skill set mismatch")
    lines = [
        f"id: {quote(profile['id'])}",
        f"name: {quote(profile['name'])}",
        f"avatar: {quote(profile['avatar'])}",
        "tags:",
        *[f"  - {quote(tag)}" for tag in profile["tags"]],
        f"description: {quote(profile['description'])}",
        "core_scenarios:",
        *[f"  - {quote(item)}" for item in profile["core_scenarios"]],
        "recommended_instructions:",
        *[f"  - {quote(item)}" for item in profile["recommended_instructions"]],
        "welcome_message:",
        "  zh-CN: |-",
        *[
            f"    {line}" if line else ""
            for line in welcome_message(profile).splitlines()
        ],
        "recommended_question:",
        f"  zh-CN: {quote(profile['recommended_instructions'][0])}",
        f"  en-US: {quote(profile['recommended_question_en'])}",
        "ai_tags:",
        *[f"  - {quote(item)}" for item in profile["ai_tags"]],
        "skills:",
    ]
    for skill in profile["skills"]:
        metadata = source_frontmatter[skill["name"]]
        lines.extend(
            [
                f"  - icon: {quote('')}",
                f"    name: {quote(metadata['name'])}",
                f"    display_name: {quote(skill['display_name'])}",
                f"    description: {quote(metadata['description'])}",
            ]
        )
    rendered = "\n".join(lines) + "\n"
    if AI_SHIFU_SPACING_PATTERN.search(rendered):
        raise ValueError(
            "Doubao agent.yml must not contain spaces inside the AI-Shifu brand name"
        )
    return rendered


def render_readme(profile: dict) -> str:
    lines = ["## 核心场景", "", profile["readme_intro"], ""]
    for scenario in profile["readme_scenarios"]:
        lines.append(f"- **{scenario['name']}**：{scenario['description']}")
    lines.extend(["", "## 推荐指令", ""])
    lines.extend(
        f"- {instruction}" for instruction in profile["recommended_instructions"]
    )
    return "\n".join(lines) + "\n"


def skill_overrides(skill: dict, source: dict[str, str]) -> dict[str, str]:
    name = skill["name"]
    if source.get("name") != name:
        raise ValueError(f"Doubao skill name mismatch: {name}")
    if not source.get("description"):
        raise ValueError(f"Doubao source skill is missing description: {name}")

    expected_label = skill["display_name"]
    source_label = source.get("label")
    if source_label and source_label != expected_label:
        raise ValueError(f"Doubao source skill label conflicts with profile: {name}")

    source_icon = source.get("icon")
    if source_icon:
        raise ValueError(f"Doubao source skill icon must be empty: {name}")

    overrides: dict[str, str] = {}
    if source_label != expected_label:
        overrides["label"] = expected_label
    if "icon" not in source:
        overrides["icon"] = ""

    version_management = source.get("version_management")
    if version_management == "standalone":
        overrides["version_management"] = "plugin"
    elif version_management not in {None, "", "plugin"}:
        raise ValueError(f"Doubao source skill has invalid version_management: {name}")
    return overrides


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("Doubao skill has invalid YAML frontmatter")
    raw = text[4:].split("\n---\n", 1)[0]
    fields = {}
    in_metadata = False
    for line in raw.splitlines():
        if ":" not in line:
            continue
        if not line[0].isspace():
            key, value = line.split(":", 1)
            key = key.strip()
            in_metadata = key == "metadata"
        elif in_metadata and line.startswith("  ") and not line.startswith("   "):
            key, value = line.strip().split(":", 1)
            if key not in {"version", "version_management"} or key in fields:
                continue
        else:
            continue
        value = value.strip()
        try:
            fields[key] = json.loads(value)
        except json.JSONDecodeError:
            fields[key] = value.strip("'\"")
    return fields


def _require_count(profile: dict, field: str, expected: int) -> list:
    values = profile.get(field)
    if not isinstance(values, list) or len(values) != expected:
        raise ValueError(
            f"Doubao profile {field} must contain exactly {expected} items"
        )
    return values


def _reject_forbidden(value: str, field: str) -> None:
    match = next((word for word in FORBIDDEN_WORDS if word in value), "")
    if match:
        raise ValueError(f"Doubao profile {field} contains forbidden wording: {match}")


def validate_profile(profile: dict) -> None:
    avatar = profile.get("avatar")
    if not isinstance(avatar, str) or not avatar.strip():
        raise ValueError("Doubao avatar must be a nonempty relative package path")
    avatar_path = PurePosixPath(avatar)
    if (
        not avatar_path.parts
        or avatar_path.is_absolute()
        or ".." in avatar_path.parts
        or "\\" in avatar
        or re.match(r"^[A-Za-z]:", avatar)
        or any(unicodedata.category(character) == "Cc" for character in avatar)
    ):
        raise ValueError("Doubao avatar must be a safe relative package path")
    if not ID_PATTERN.fullmatch(str(profile.get("id", ""))):
        raise ValueError("Doubao profile id must use kebab-case")
    if profile.get("primary_skill") != "ai-shifu-course-creator":
        raise ValueError("Doubao profile primary_skill must be ai-shifu-course-creator")
    if profile.get("persona_name") != "AI师傅教学专家":
        raise ValueError(
            "Doubao profile persona_name must match the required localized teaching expert name"
        )
    if not 1 <= text_length(str(profile.get("name", ""))) <= 8:
        raise ValueError("Doubao profile name must be 1 to 8 characters")
    if text_length(str(profile.get("description", ""))) > 50:
        raise ValueError("Doubao profile description exceeds 50 characters")
    tags = _require_count(profile, "tags", 1)
    if tags[0] not in ALLOWED_TAGS:
        raise ValueError(f"Unsupported Doubao tag: {tags[0]}")
    _require_count(profile, "core_scenarios", 3)
    instructions = _require_count(profile, "recommended_instructions", 3)
    for index, instruction in enumerate(instructions):
        length = text_length(instruction)
        if not 15 <= length <= 50:
            raise ValueError(
                f"Doubao recommended instruction length must be 15 to 50: {instruction}"
            )
        if index != 2 and EXTERNAL_INPUT_PATTERN.search(instruction):
            raise ValueError(
                f"Doubao recommended instruction is not zero-input: {instruction}"
            )
    ai_tags = _require_count(profile, "ai_tags", 3)
    if len(set(ai_tags)) != 3 or any(not 2 <= text_length(tag) <= 6 for tag in ai_tags):
        raise ValueError("Doubao ai_tags must be unique and 2 to 6 characters")
    scenarios = _require_count(profile, "readme_scenarios", 3)
    if any(not item.get("name") or not item.get("description") for item in scenarios):
        raise ValueError("Doubao README scenarios require name and description")
    skills = profile.get("skills")
    if not isinstance(skills, list) or len(skills) < 2:
        raise ValueError("Doubao profile requires at least two skills")
    names = [skill.get("name", "") for skill in skills]
    if len(set(names)) != len(names) or any(
        not SKILL_NAME_PATTERN.fullmatch(name) for name in names
    ):
        raise ValueError("Doubao skill names must be unique kebab-case values")
    if profile["primary_skill"] not in names:
        raise ValueError("Doubao primary skill is not declared in skills")
    for index, skill in enumerate(skills):
        extra_fields = set(skill) - SKILL_PROFILE_FIELDS
        if extra_fields:
            raise ValueError(
                f"Doubao skill {names[index]} has unsupported profile fields: "
                f"{sorted(extra_fields)}"
            )
        for field in ("display_name",):
            if not skill.get(field):
                raise ValueError(f"Doubao skill {names[index]} is missing {field}")
    for field in (
        "name",
        "description",
        "welcome_intro",
        "readme_intro",
        "recommended_question_en",
    ):
        _reject_forbidden(str(profile.get(field, "")), field)
    for field in ("core_scenarios", "recommended_instructions", "ai_tags"):
        for value in profile[field]:
            _reject_forbidden(value, field)


def png_dimensions(path: Path) -> tuple[int, int]:
    content = path.read_bytes()
    if (
        len(content) < 24
        or content[:8] != b"\x89PNG\r\n\x1a\n"
        or content[12:16] != b"IHDR"
    ):
        raise ValueError(f"Doubao image is not a valid PNG: {path}")
    return struct.unpack(">II", content[16:24])


def validate_image(path: Path, *, max_bytes: int | None = None) -> str:
    if not path.is_file():
        raise ValueError(f"Doubao image is missing: {path}")
    if max_bytes is not None and path.stat().st_size > max_bytes:
        raise ValueError(f"Doubao image exceeds size limit: {path}")
    width, height = png_dimensions(path)
    if width != height or min(width, height) < 128:
        raise ValueError(f"Doubao image must be square and at least 128px: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_package(
    root: Path,
    profile: dict,
    source_frontmatter: dict[str, dict[str, str]],
) -> None:
    validate_profile(profile)
    root = root.resolve()
    avatar = artifact_path(root, profile["avatar"])
    required = [root / "agent.yml", root / "README.md", avatar]
    required.extend(root / "workspace" / name for name in REQUIRED_WORKSPACE_FILES)
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing:
        raise ValueError(f"Doubao package is missing required files: {missing}")
    if (root / "agent.yml").read_text(encoding="utf-8") != render_agent_yml(
        profile, source_frontmatter
    ):
        raise ValueError("Doubao agent.yml differs from the channel profile")
    if (root / "README.md").read_text(encoding="utf-8") != render_readme(profile):
        raise ValueError("Doubao README.md differs from the channel profile")
    validate_image(avatar, max_bytes=2 * 1024 * 1024)
    skills_root = root / "workspace" / "skills"
    actual_names = sorted(path.name for path in skills_root.iterdir() if path.is_dir())
    expected_names = sorted(skill["name"] for skill in profile["skills"])
    if actual_names != expected_names:
        raise ValueError(
            f"Doubao skill directories mismatch: {actual_names} != {expected_names}"
        )
    for skill in profile["skills"]:
        skill_root = skills_root / skill["name"]
        skill_file = skill_root / "SKILL.md"
        if not skill_file.is_file():
            raise ValueError(f"Doubao skill is missing SKILL.md: {skill['name']}")
        frontmatter = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        source = source_frontmatter[skill["name"]]
        expected = {
            "name": source["name"],
            "label": skill["display_name"],
            "icon": "",
            "description": source["description"],
        }
        for field, value in expected.items():
            if frontmatter.get(field) != value:
                raise ValueError(
                    f"Doubao skill frontmatter mismatch: {skill['name']} {field}"
                )
    agents = (root / "workspace" / "AGENTS.md").read_text(encoding="utf-8")
    if len(agents) < 800:
        raise ValueError("Doubao AGENTS.md must contain at least 800 characters")
    for skill in profile["skills"]:
        path = f"workspace/skills/{skill['name']}/SKILL.md"
        if path not in agents:
            raise ValueError(f"Doubao AGENTS.md does not reference {path}")
    for relative in (
        "workspace/IDENTITY.md",
        "workspace/SOUL.md",
        "workspace/AGENTS.md",
    ):
        if profile["persona_name"] not in (root / relative).read_text(encoding="utf-8"):
            raise ValueError(f"Doubao persona identity mismatch: {relative}")
    if profile["persona_name"] not in profile["welcome_intro"]:
        raise ValueError(
            "Doubao welcome intro does not use the configured persona identity"
        )
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() == ".png":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in LEAK_PATTERNS:
            if pattern.search(text):
                raise ValueError(
                    f"Doubao package contains a local path or private address: {path.relative_to(root)}"
                )
        if any(word in text for word in TEMPLATE_RESIDUE):
            raise ValueError(
                f"Doubao package contains template residue: {path.relative_to(root)}"
            )


def build_doubao_artifact(channel: str, context: BuildContext) -> dict:
    profile_path = channel_path(context.channels, context.config.doubao.profile)
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    validate_profile(profile)
    if context.skill_name != profile["primary_skill"]:
        raise ValueError(
            f"Doubao profile supports {profile['primary_skill']}, not {context.skill_name}"
        )
    root_name = f"doubao-ai-shifu-{context.version}"
    stage_dir = context.artifacts / channel / root_name
    workspace = stage_dir / "workspace"
    stage_dir.mkdir(parents=True)
    avatar_relative = PurePosixPath(profile["avatar"])
    avatar = profile_path.parent / avatar_relative
    channels_root = context.channels.resolve()
    if not avatar.resolve().is_relative_to(channels_root):
        raise ValueError("Doubao avatar must stay inside channels/")
    target_avatar = stage_dir / avatar_relative
    target_avatar.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(avatar, target_avatar)
    copy_tree(
        channel_path(context.channels, context.config.doubao.workspace_dir), workspace
    )

    source_documents: dict[str, tuple[str, str]] = {}
    source_frontmatter: dict[str, dict[str, str]] = {}
    for skill in profile["skills"]:
        name = skill["name"]
        frontmatter, body = read_skill_document(
            context.source_skills[name] / "SKILL.md"
        )
        metadata = parse_skill_frontmatter(frontmatter)
        skill_overrides(skill, metadata)
        source_documents[name] = (frontmatter, body)
        source_frontmatter[name] = metadata

    (stage_dir / "agent.yml").write_text(
        render_agent_yml(profile, source_frontmatter), encoding="utf-8"
    )
    (stage_dir / "README.md").write_text(render_readme(profile), encoding="utf-8")

    embedded_skills = {}
    for skill in profile["skills"]:
        name = skill["name"]
        source = context.source_skills[name]
        destination = workspace / "skills" / name
        frontmatter, source_body = source_documents[name]
        metadata = source_frontmatter[name]
        overrides = skill_overrides(skill, metadata)
        source_skill_bytes = (source / "SKILL.md").read_bytes()
        build_skill_variant(source, destination, overrides)
        assert_contents_equal(
            directory_contents(destination),
            expected_variant_contents(
                directory_contents(source), overrides, f"Doubao {name}/SKILL.md"
            ),
            f"doubao {name} directory",
        )
        embedded_skills[name] = {
            "root": f"{root_name}/workspace/skills/{name}",
            "source_commit": context.source_commit,
            "source_tree_sha256": tree_hash(source),
            "source_files": directory_manifest(source),
            "source_skill_sha256": content_hash(source_skill_bytes),
            "source_frontmatter": frontmatter,
            "body_sha256": content_hash(source_body.encode("utf-8")),
            "tree_sha256": tree_hash(destination),
            "frontmatter_overrides": overrides,
        }

    scan_tree(stage_dir)
    validate_package(stage_dir, profile, source_frontmatter)
    archive = context.artifacts / channel / f"{root_name}.zip"
    write_zip(stage_dir, archive, root_name)
    return {
        "directory": context.record_path(stage_dir),
        "tree_sha256": tree_hash(stage_dir),
        "archive": context.record_path(archive),
        "archive_sha256": file_hash(archive),
        "archive_root": root_name,
        "version": context.version,
        "source_profile_json": profile_bytes.decode("utf-8"),
        "source_profile_sha256": content_hash(profile_bytes),
        "embedded_skills": embedded_skills,
    }


def verify_embedded_source_variant(
    skill_root: Path,
    record: dict,
    overrides: dict[str, str],
    name: str,
) -> None:
    source_files = record.get("source_files")
    if not isinstance(source_files, dict) or "SKILL.md" not in source_files:
        raise ValueError(f"doubao {name} source file manifest is missing")
    if manifest_tree_hash(source_files) != record.get("source_tree_sha256"):
        raise ValueError(f"doubao {name} source tree manifest mismatch")

    actual_manifest = directory_manifest(skill_root)
    if actual_manifest.keys() != source_files.keys():
        missing = sorted(source_files.keys() - actual_manifest.keys())
        extra = sorted(actual_manifest.keys() - source_files.keys())
        raise ValueError(
            f"doubao {name} source file set mismatch: missing={missing}, extra={extra}"
        )
    for relative, expected in source_files.items():
        if relative == "SKILL.md":
            if actual_manifest[relative]["mode"] != expected["mode"]:
                raise ValueError(
                    f"doubao {name} SKILL.md mode differs from GitHub source"
                )
            continue
        if actual_manifest[relative] != expected:
            raise ValueError(
                f"doubao {name} source file differs from GitHub source: {relative}"
            )

    actual_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    _, body = split_skill_document(actual_text, f"doubao {name}/SKILL.md")
    if content_hash(body.encode("utf-8")) != record.get("body_sha256"):
        raise ValueError(f"doubao {name} body differs from GitHub source")

    source_frontmatter = record.get("source_frontmatter")
    if not isinstance(source_frontmatter, str):
        raise ValueError(f"doubao {name} source frontmatter is missing")
    source_text = f"---\n{source_frontmatter}\n---\n{body}"
    if content_hash(source_text.encode("utf-8")) != record.get("source_skill_sha256"):
        raise ValueError(f"doubao {name} source SKILL.md proof mismatch")
    if content_hash(source_text.encode("utf-8")) != source_files["SKILL.md"]["sha256"]:
        raise ValueError(f"doubao {name} source SKILL.md manifest mismatch")

    expected_text = update_skill_frontmatter(
        source_text, overrides, f"doubao {name}/SKILL.md"
    )
    if actual_text != expected_text:
        raise ValueError(f"doubao {name} SKILL.md contains non-whitelisted changes")


def verify_doubao_artifact(
    artifact: dict,
    release_dir: Path,
    skill: dict,
    source_commit: str,
    canonical: dict[str, bytes],
) -> list[str]:
    profile_json = artifact.get("source_profile_json")
    if not isinstance(profile_json, str):
        raise ValueError(
            "Doubao source profile is missing or differs from its recorded hash"
        )
    if content_hash(profile_json.encode("utf-8")) != artifact.get(
        "source_profile_sha256"
    ):
        raise ValueError(
            "Doubao source profile is missing or differs from its recorded hash"
        )
    profile = json.loads(profile_json)
    validate_profile(profile)
    if skill["name"] != profile["primary_skill"]:
        raise ValueError("Doubao primary skill does not match release.json")
    directory = artifact_path(release_dir, artifact["directory"])
    expected_root = f"doubao-ai-shifu-{skill['version']}"
    if directory.name != artifact["archive_root"] or directory.name != expected_root:
        raise ValueError("Doubao archive root mismatch")
    if tree_hash(directory) != artifact["tree_sha256"]:
        raise ValueError("doubao directory hash mismatch")
    scan_tree(directory)

    profile_skills = {item["name"]: item for item in profile["skills"]}
    embedded = artifact.get("embedded_skills", {})
    if set(embedded) != set(profile_skills):
        raise ValueError("doubao embedded skill records mismatch")
    source_frontmatter: dict[str, dict[str, str]] = {}
    for name, record in embedded.items():
        if record.get("source_commit") != source_commit:
            raise ValueError(f"doubao {name} source commit mismatch")
        raw_frontmatter = record.get("source_frontmatter")
        if not isinstance(raw_frontmatter, str):
            raise ValueError(f"doubao {name} source frontmatter is missing")
        source_frontmatter[name] = parse_skill_frontmatter(raw_frontmatter)
    validate_package(directory, profile, source_frontmatter)

    for name, record in embedded.items():
        item = profile_skills[name]
        metadata = source_frontmatter[name]
        expected_overrides = skill_overrides(item, metadata)
        if record.get("frontmatter_overrides") != expected_overrides:
            raise ValueError(f"doubao {name} frontmatter override policy mismatch")
        skill_root = directory / "workspace" / "skills" / name
        if tree_hash(skill_root) != record.get("tree_sha256"):
            raise ValueError(f"doubao {name} tree hash mismatch")
        verify_embedded_source_variant(skill_root, record, expected_overrides, name)
        if name == skill["name"]:
            expected = expected_variant_contents(
                canonical, expected_overrides, f"doubao {name}/SKILL.md"
            )
            assert_contents_equal(
                directory_contents(skill_root), expected, f"doubao {name} directory"
            )

    archive = artifact_path(release_dir, artifact["archive"])
    if file_hash(archive) != artifact["archive_sha256"]:
        raise ValueError("doubao archive hash mismatch")
    verify_zip(archive)
    assert_contents_equal(
        zip_subtree_contents(archive, artifact["archive_root"]),
        directory_contents(directory),
        "doubao archive",
    )
    return [artifact["tree_sha256"], artifact["archive_sha256"]]
