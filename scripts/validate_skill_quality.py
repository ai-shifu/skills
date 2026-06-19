#!/usr/bin/env python3
"""Validate skill quality per the official Claude Skill Guide.

Only uses Python standard library — no pyyaml dependency required.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

RE_KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RE_HUMAN_READABLE_NAME = re.compile(r"^\S[^\r\n<>]*$")
RE_XML_TAG = re.compile(r"[<>]")
RE_REF_PATH = re.compile(r"references/[A-Za-z0-9_./-]+\.md")
FORBIDDEN_WORDS = {"claude", "anthropic"}

MAX_DESCRIPTION_LEN = 1024
MIN_DESCRIPTION_LEN_RECOMMENDED = 50
MAX_COMPATIBILITY_LEN = 500


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
        if RE_KEBAB_CASE.match(name):
            issues.add_error(
                f"{skill_md}: frontmatter 'name' must be human-readable, "
                f"got slug-like value '{name}'"
            )
        elif not RE_HUMAN_READABLE_NAME.match(name):
            issues.add_error(
                f"{skill_md}: frontmatter 'name' contains unsupported display "
                f"name characters, got '{name}'"
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
