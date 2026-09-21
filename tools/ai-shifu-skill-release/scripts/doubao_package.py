#!/usr/bin/env python3
"""Render and validate the Doubao Work partner package shell."""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import unicodedata
from pathlib import Path


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


def render_agent_yml(profile: dict, source_frontmatter: dict[str, dict[str, str]]) -> str:
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
        *[f"    {line}" if line else "" for line in welcome_message(profile).splitlines()],
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
        raise ValueError("Doubao agent.yml must not contain spaces inside the AI-Shifu brand name")
    return rendered


def render_readme(profile: dict) -> str:
    lines = ["## 核心场景", "", profile["readme_intro"], ""]
    for scenario in profile["readme_scenarios"]:
        lines.append(f"- **{scenario['name']}**：{scenario['description']}")
    lines.extend(["", "## 推荐指令", ""])
    lines.extend(f"- {instruction}" for instruction in profile["recommended_instructions"])
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
        raise ValueError(
            f"Doubao source skill has invalid version_management: {name}"
        )
    return overrides


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("Doubao skill has invalid YAML frontmatter")
    raw = text[4:].split("\n---\n", 1)[0]
    fields = {}
    for line in raw.splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        try:
            fields[key.strip()] = json.loads(value)
        except json.JSONDecodeError:
            fields[key.strip()] = value.strip("'\"")
    return fields


def _require_count(profile: dict, field: str, expected: int) -> list:
    values = profile.get(field)
    if not isinstance(values, list) or len(values) != expected:
        raise ValueError(f"Doubao profile {field} must contain exactly {expected} items")
    return values


def _reject_forbidden(value: str, field: str) -> None:
    match = next((word for word in FORBIDDEN_WORDS if word in value), "")
    if match:
        raise ValueError(f"Doubao profile {field} contains forbidden wording: {match}")


def validate_profile(profile: dict) -> None:
    if not ID_PATTERN.fullmatch(str(profile.get("id", ""))):
        raise ValueError("Doubao profile id must use kebab-case")
    if profile.get("primary_skill") != "ai-shifu-course-creator":
        raise ValueError("Doubao profile primary_skill must be ai-shifu-course-creator")
    if profile.get("persona_name") != "AI师傅教学专家":
        raise ValueError("Doubao profile persona_name must match the required localized teaching expert name")
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
            raise ValueError(f"Doubao recommended instruction length must be 15 to 50: {instruction}")
        if index != 2 and EXTERNAL_INPUT_PATTERN.search(instruction):
            raise ValueError(f"Doubao recommended instruction is not zero-input: {instruction}")
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
    if len(set(names)) != len(names) or any(not SKILL_NAME_PATTERN.fullmatch(name) for name in names):
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
    if len(content) < 24 or content[:8] != b"\x89PNG\r\n\x1a\n" or content[12:16] != b"IHDR":
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
    required = [root / "agent.yml", root / "README.md", root / profile["avatar"]]
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
    validate_image(root / profile["avatar"], max_bytes=2 * 1024 * 1024)
    skills_root = root / "workspace" / "skills"
    actual_names = sorted(path.name for path in skills_root.iterdir() if path.is_dir())
    expected_names = sorted(skill["name"] for skill in profile["skills"])
    if actual_names != expected_names:
        raise ValueError(f"Doubao skill directories mismatch: {actual_names} != {expected_names}")
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
    for relative in ("workspace/IDENTITY.md", "workspace/SOUL.md", "workspace/AGENTS.md"):
        if profile["persona_name"] not in (root / relative).read_text(encoding="utf-8"):
            raise ValueError(f"Doubao persona identity mismatch: {relative}")
    if profile["persona_name"] not in profile["welcome_intro"]:
        raise ValueError("Doubao welcome intro does not use the configured persona identity")
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
            raise ValueError(f"Doubao package contains template residue: {path.relative_to(root)}")
