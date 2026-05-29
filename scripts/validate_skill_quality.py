#!/usr/bin/env python3
"""Validate skill quality per the official Claude Skill Guide.

Only uses Python standard library — no pyyaml dependency required.
"""

from __future__ import annotations

import re
import sys
import json
from dataclasses import dataclass, field
from pathlib import Path

RE_KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RE_XML_TAG = re.compile(r"[<>]")
RE_REF_PATH = re.compile(r"references/[A-Za-z0-9_./-]+\.md")
RE_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
FORBIDDEN_WORDS = {"claude", "anthropic"}

MAX_DESCRIPTION_LEN = 1024
MIN_DESCRIPTION_LEN_RECOMMENDED = 50
MAX_COMPATIBILITY_LEN = 500
CODEX_PLUGIN_PATH_FIELDS = ("skills", "mcpServers", "apps", "hooks")


@dataclass
class IssueBag:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def parse_frontmatter(skill_md: Path, issues: IssueBag) -> dict[str, str] | None:
    """Parse YAML frontmatter using only the standard library.

    Handles simple key: value pairs which is sufficient for SKILL.md
    frontmatter (name, description, compatibility).
    """
    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        issues.add_error(f"{skill_md}: missing YAML frontmatter")
        return None

    end_index = content.find("---", 3)
    if end_index == -1:
        issues.add_error(f"{skill_md}: malformed YAML frontmatter (no closing ---)")
        return None

    raw = content[3:end_index].strip()
    if not raw:
        issues.add_error(f"{skill_md}: YAML frontmatter is empty")
        return None

    result: dict[str, str] = {}
    current_key: str | None = None
    current_value_lines: list[str] = []

    for line in raw.splitlines():
        colon_pos = line.find(":")
        if colon_pos > 0 and not line[0].isspace():
            if current_key is not None:
                result[current_key] = " ".join(current_value_lines).strip()
            current_key = line[:colon_pos].strip()
            current_value_lines = [line[colon_pos + 1 :].strip()]
        elif current_key is not None:
            current_value_lines.append(line.strip())

    if current_key is not None:
        result[current_key] = " ".join(current_value_lines).strip()

    return result


def validate_skill(skill_dir: Path, issues: IssueBag) -> None:
    slug = skill_dir.name

    if not RE_KEBAB_CASE.match(slug):
        issues.add_error(
            f"{skill_dir}: folder name '{slug}' is not kebab-case "
            "(lowercase letters, digits, hyphens only)"
        )

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        variants = [p for p in skill_dir.iterdir() if p.name.lower() == "skill.md"]
        if variants:
            issues.add_error(
                f"{skill_dir}: found '{variants[0].name}' but the file must be "
                "named exactly 'SKILL.md' (case-sensitive)"
            )
        else:
            issues.add_error(f"{skill_dir}: required file SKILL.md is missing")
        return

    front = parse_frontmatter(skill_md, issues)
    if front is None:
        return

    name = front.get("name", "").strip()
    if not name:
        issues.add_error(f"{skill_md}: frontmatter 'name' field is required")
    else:
        if not RE_KEBAB_CASE.match(name):
            issues.add_error(
                f"{skill_md}: frontmatter 'name' must be kebab-case, got '{name}'"
            )
        if name != slug:
            issues.add_error(
                f"{skill_md}: frontmatter 'name' ({name}) must match "
                f"folder name ({slug})"
            )
        name_lower = name.lower()
        for word in FORBIDDEN_WORDS:
            if word in name_lower:
                issues.add_error(
                    f"{skill_md}: frontmatter 'name' must not contain '{word}'"
                )

    description = front.get("description", "").strip()
    if not description:
        issues.add_error(f"{skill_md}: frontmatter 'description' field is required")
    else:
        if len(description) > MAX_DESCRIPTION_LEN:
            issues.add_error(
                f"{skill_md}: description exceeds {MAX_DESCRIPTION_LEN} chars "
                f"({len(description)})"
            )
        if RE_XML_TAG.search(description):
            issues.add_error(
                f"{skill_md}: description must not contain XML tags (< or >)"
            )
        if len(description) < MIN_DESCRIPTION_LEN_RECOMMENDED:
            issues.add_warning(
                f"{skill_md}: description is only {len(description)} chars; "
                f"consider >= {MIN_DESCRIPTION_LEN_RECOMMENDED} to include both "
                "what the skill does and when it should trigger"
            )

    compatibility = front.get("compatibility", "").strip()
    if compatibility and len(compatibility) > MAX_COMPATIBILITY_LEN:
        issues.add_warning(
            f"{skill_md}: compatibility field exceeds {MAX_COMPATIBILITY_LEN} chars "
            f"({len(compatibility)})"
        )

    readme = skill_dir / "README.md"
    if readme.exists():
        issues.add_warning(
            f"{skill_dir}: README.md found inside skill folder; "
            "consider moving content into SKILL.md"
        )

    content = skill_md.read_text(encoding="utf-8")
    ref_paths = sorted(set(RE_REF_PATH.findall(content)))
    for ref in ref_paths:
        ref_file = skill_dir / ref
        if not ref_file.exists():
            issues.add_warning(
                f"{skill_md}: referenced file not found -> {ref}"
            )


def _require_non_empty_str(
    obj: dict[str, object],
    field: str,
    issues: IssueBag,
    label: str,
) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        issues.add_error(f"{label}: field '{field}' must be a non-empty string")
        return ""
    return value.strip()


def _validate_plugin_relative_path(
    repo_root: Path,
    value: object,
    issues: IssueBag,
    label: str,
) -> None:
    if not isinstance(value, str) or not value.strip():
        issues.add_error(f"{label} must be a non-empty string path")
        return
    if not value.startswith("./"):
        issues.add_error(f"{label} must start with ./")
        return

    rel = value[2:]
    if not rel:
        issues.add_error(f"{label} must not be empty")
        return

    parts = rel.split("/")
    for index, part in enumerate(parts):
        is_trailing_slash = part == "" and index == len(parts) - 1
        if is_trailing_slash:
            continue
        if part in {"", ".", ".."}:
            issues.add_error(f"{label} must stay inside the plugin root")
            return

    normalized = rel[:-1] if rel.endswith("/") else rel
    target = (repo_root / normalized).resolve()
    try:
        target.relative_to(repo_root.resolve())
    except ValueError:
        issues.add_error(f"{label} must stay inside the plugin root")
        return

    if not target.exists():
        issues.add_error(f"{label} points to a missing path: {value}")


def validate_codex_plugin_manifest(repo_root: Path, issues: IssueBag) -> None:
    manifest_path = repo_root / ".codex-plugin" / "plugin.json"
    if not manifest_path.exists():
        issues.add_error(".codex-plugin/plugin.json is required for Codex plugin installs")
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.add_error(f"{manifest_path}: invalid JSON: {exc}")
        return

    if not isinstance(manifest, dict):
        issues.add_error(f"{manifest_path}: root value must be an object")
        return

    name = _require_non_empty_str(manifest, "name", issues, str(manifest_path))
    if name and not RE_KEBAB_CASE.match(name):
        issues.add_error(f"{manifest_path}: field 'name' must be kebab-case")

    version = _require_non_empty_str(manifest, "version", issues, str(manifest_path))
    if version and not RE_SEMVER.match(version):
        issues.add_error(f"{manifest_path}: field 'version' must be strict semver")

    for field in ("description", "homepage", "repository", "license"):
        _require_non_empty_str(manifest, field, issues, str(manifest_path))

    author = manifest.get("author")
    if not isinstance(author, dict):
        issues.add_error(f"{manifest_path}: field 'author' must be an object")
    else:
        _require_non_empty_str(author, "name", issues, f"{manifest_path}: author")

    keywords = manifest.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        issues.add_error(f"{manifest_path}: field 'keywords' must be a non-empty array")
    elif not all(isinstance(item, str) and item.strip() for item in keywords):
        issues.add_error(f"{manifest_path}: field 'keywords' must contain only non-empty strings")

    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        issues.add_error(f"{manifest_path}: field 'interface' must be an object")
    else:
        for field in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
        ):
            _require_non_empty_str(interface, field, issues, f"{manifest_path}: interface")

        capabilities = interface.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            issues.add_error(
                f"{manifest_path}: interface.capabilities must be a non-empty array"
            )
        elif not all(isinstance(item, str) and item.strip() for item in capabilities):
            issues.add_error(
                f"{manifest_path}: interface.capabilities must contain only non-empty strings"
            )

    has_component = False
    for field in CODEX_PLUGIN_PATH_FIELDS:
        if field not in manifest:
            continue
        has_component = True
        value = manifest[field]
        if isinstance(value, list):
            for index, item in enumerate(value):
                _validate_plugin_relative_path(
                    repo_root,
                    item,
                    issues,
                    f"{manifest_path}: {field}[{index}]",
                )
        else:
            _validate_plugin_relative_path(
                repo_root,
                value,
                issues,
                f"{manifest_path}: {field}",
            )

    if not has_component:
        issues.add_error(
            f"{manifest_path}: at least one component path is required "
            "(skills, mcpServers, apps, or hooks)"
        )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    skills_root = repo_root / "skills"
    skill_dirs = sorted(
        p for p in skills_root.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )

    if not skill_dirs:
        print("No skill directories found under skills/", file=sys.stderr)
        return 1

    issues = IssueBag()
    validate_codex_plugin_manifest(repo_root, issues)
    for skill_dir in skill_dirs:
        validate_skill(skill_dir, issues)

    if issues.warnings:
        print("Warnings:")
        for warning in issues.warnings:
            print(f"  warning: {warning}")
        print()

    if issues.errors:
        print("Validation FAILED:", file=sys.stderr)
        for err in issues.errors:
            print(f"  error: {err}", file=sys.stderr)
        return 1

    print(f"Validated {len(skill_dirs)} skills -- all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
