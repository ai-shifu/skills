#!/usr/bin/env python3
"""Validate skill quality per the official Claude Skill Guide.

Only uses Python standard library — no pyyaml dependency required.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

RE_KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RE_HUMAN_READABLE_NAME = re.compile(r"^\S[^\r\n<>]*$")
RE_XML_TAG = re.compile(r"[<>]")
RE_REF_PATH = re.compile(r"references/[A-Za-z0-9_./-]+\.md")
RE_MD_ANCHOR_REF = re.compile(
    r"(?<![\w/.])"
    r"(?P<path>(?:\.\./)*(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.md)"
    r"#(?P<anchor>[A-Za-z0-9][A-Za-z0-9-]*)"
)
RE_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
RE_SLUG_STRIP = re.compile(r"[^\w\- ]")
RE_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
RE_JSON_FENCE = re.compile(
    r"^```json[ \t]*\n(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
RE_COURSE_PROMPT_ARTIFACT = re.compile(
    r"^### Course Prompt Artifact[ \t]*$.*?"
    r"^```markdown[ \t]*\n(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
FORBIDDEN_WORDS = {"claude", "anthropic"}

# Doc surface scanned for cross-file anchor links. Local-only dirs
# (design/, evals/, scripts/) are intentionally excluded.
ANCHOR_SCAN_GLOBS = ("SKILL.md", "references/**/*.md", "examples/**/*.md")

MAX_DESCRIPTION_LEN = 1024
MIN_DESCRIPTION_LEN_RECOMMENDED = 50
MAX_COMPATIBILITY_LEN = 500
TRANSFER_SIGNAL_KEYS = {
    "learner_hook",
    "evidence_type",
    "visual_cue",
    "concept_conflict",
    "boundary_cue",
    "action_cue",
    "density_cue",
    "quote_cue",
    "visual_text_pair_cue",
    "interaction_intent_cue",
    "compare_cue",
}


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
        if name == slug:
            issues.add_error(
                f"{skill_md}: frontmatter 'name' must be a human-readable "
                f"display name, but it matches the folder slug '{name}'"
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

    version = front.get("version", "").strip()
    update_checker = skill_dir / "scripts" / "skill_update.py"
    if update_checker.is_file():
        if not version:
            issues.add_error(f"{skill_md}: frontmatter 'version' field is required")
        elif not RE_SEMVER.fullmatch(version):
            issues.add_error(
                f"{skill_md}: version must use MAJOR.MINOR.PATCH, got '{version}'"
            )
    else:
        if version and not RE_SEMVER.fullmatch(version):
            issues.add_error(
                f"{skill_md}: version must use MAJOR.MINOR.PATCH, got '{version}'"
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

    validate_anchors(skill_dir, issues)
    validate_example_contracts(skill_dir, issues)


def github_heading_slugs(md_file: Path) -> set[str]:
    """Collect the GitHub anchor slugs of every heading in a markdown file.

    GitHub's algorithm: lowercase, drop punctuation, convert each space to
    one hyphen (no collapsing — "A & B" yields "a--b"), and suffix -1/-2/…
    on duplicate headings. Headings inside fenced code blocks are ignored.
    """
    slug_counts: dict[str, int] = {}
    slugs: set[str] = set()
    in_fence = False
    fence_marker = ""
    for line in md_file.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence = False
            continue
        if in_fence:
            continue
        m = RE_HEADING.match(line)
        if not m:
            continue
        title = m.group(2).lower()
        base = RE_SLUG_STRIP.sub("", title).replace(" ", "-")
        n = slug_counts.get(base, 0)
        slug_counts[base] = n + 1
        slugs.add(base if n == 0 else f"{base}-{n}")
    return slugs


def validate_anchors(skill_dir: Path, issues: IssueBag) -> None:
    """Every `<path>.md#<anchor>` reference in the skill's doc surface must
    resolve to a real heading in the target file (broken anchors are silent
    at runtime: the pointed-to rule text becomes unreachable)."""
    slug_cache: dict[Path, set[str]] = {}
    for pattern in ANCHOR_SCAN_GLOBS:
        for md_file in sorted(skill_dir.glob(pattern)):
            content = md_file.read_text(encoding="utf-8")
            seen: set[tuple[str, str]] = set()
            for m in RE_MD_ANCHOR_REF.finditer(content):
                ref = (m.group("path"), m.group("anchor"))
                if ref in seen:
                    continue
                seen.add(ref)
                target = (md_file.parent / ref[0]).resolve()
                if not target.is_file():
                    # Missing files are reported by the RE_REF_PATH check.
                    continue
                if target not in slug_cache:
                    slug_cache[target] = github_heading_slugs(target)
                if ref[1] not in slug_cache[target]:
                    issues.add_error(
                        f"{md_file}: broken anchor -> {ref[0]}#{ref[1]} "
                        f"(no matching heading in {target.name})"
                    )


def walk_json(value: object):
    """Yield every nested JSON value, including the root."""
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def validate_segment_example(
    segment: dict[str, object], md_file: Path, issues: IssueBag
) -> None:
    required = {
        "segment_id",
        "segment_type",
        "core_point",
        "preserve_block",
        "source_span",
        "transfer_signals",
    }
    missing = sorted(required - segment.keys())
    if missing:
        issues.add_error(
            f"{md_file}: segment example {segment.get('segment_id')} "
            f"is missing required fields: {', '.join(missing)}"
        )
        return

    source_span = segment["source_span"]
    if not isinstance(source_span, dict):
        issues.add_error(
            f"{md_file}: segment example {segment['segment_id']} source_span "
            "must be an object"
        )
    else:
        source_id = source_span.get("source_id")
        start = source_span.get("start")
        end = source_span.get("end")
        valid_offsets = (
            isinstance(source_id, str)
            and bool(source_id)
            and isinstance(start, int)
            and not isinstance(start, bool)
            and start >= 0
            and isinstance(end, int)
            and not isinstance(end, bool)
            and end > start
        )
        if not valid_offsets:
            issues.add_error(
                f"{md_file}: segment example {segment['segment_id']} source_span "
                "must contain source_id and valid start/end offsets"
            )

    transfer_signals = segment["transfer_signals"]
    if not isinstance(transfer_signals, dict) or not transfer_signals:
        issues.add_error(
            f"{md_file}: segment example {segment['segment_id']} "
            "transfer_signals must be a non-empty object"
        )
    else:
        unknown_keys = sorted(transfer_signals.keys() - TRANSFER_SIGNAL_KEYS)
        if unknown_keys:
            issues.add_error(
                f"{md_file}: segment example {segment['segment_id']} uses "
                f"unknown transfer signal keys: {', '.join(unknown_keys)}"
            )
        if any(
            not isinstance(value, str) or not value.strip()
            for value in transfer_signals.values()
        ):
            issues.add_error(
                f"{md_file}: segment example {segment['segment_id']} transfer "
                "signal values must be non-empty strings"
            )


def course_prompt_template_lines(skill_dir: Path) -> list[str]:
    template_file = skill_dir / "references" / "course-prompt.md"
    if not template_file.is_file():
        return []
    content = template_file.read_text(encoding="utf-8")
    marker = "## Fillable Template"
    if marker not in content:
        return []
    template_section = content.split(marker, 1)[1]
    match = re.search(
        r"^```markdown[ \t]*\n(?P<body>.*?)^```[ \t]*$",
        template_section,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []
    return [
        line.strip()
        for line in match.group("body").splitlines()
        if line.strip() and "XXX" not in line
    ]


def validate_example_contracts(skill_dir: Path, issues: IssueBag) -> None:
    """Keep executable examples aligned with their documented contracts."""
    examples_dir = skill_dir / "examples"
    if not examples_dir.is_dir():
        return

    prompt_template_lines = course_prompt_template_lines(skill_dir)
    for md_file in sorted(examples_dir.glob("**/*.md")):
        content = md_file.read_text(encoding="utf-8")
        for match in RE_JSON_FENCE.finditer(content):
            try:
                payload = json.loads(match.group("body"))
            except json.JSONDecodeError as exc:
                issues.add_error(
                    f"{md_file}: invalid JSON example near line "
                    f"{content.count(chr(10), 0, match.start('body')) + exc.lineno}: "
                    f"{exc.msg}"
                )
                continue

            for value in walk_json(payload):
                if not isinstance(value, dict):
                    continue
                if "segment_id" in value and (
                    "segment_type" in value or "core_point" in value
                ):
                    validate_segment_example(value, md_file, issues)
                if "effect_scope" in value and value["effect_scope"] != "cross_lesson":
                    issues.add_error(
                        f"{md_file}: global variable examples must use "
                        "effect_scope 'cross_lesson'"
                    )

        for match in RE_COURSE_PROMPT_ARTIFACT.finditer(content):
            prompt = match.group("body")
            if "XXX" in prompt:
                issues.add_error(
                    f"{md_file}: Course Prompt example contains unresolved XXX"
                )
            for required_prefix in (
                "- You are ",
                "- You specialize in ",
                "- The current course is ",
            ):
                if required_prefix not in prompt:
                    issues.add_error(
                        f"{md_file}: Course Prompt example is missing filled "
                        f"placeholder line beginning with: {required_prefix}"
                    )
            for required_line in prompt_template_lines:
                if required_line not in prompt:
                    issues.add_error(
                        f"{md_file}: Course Prompt example is missing template "
                        f"instruction: {required_line}"
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
