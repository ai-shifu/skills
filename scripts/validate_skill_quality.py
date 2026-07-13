#!/usr/bin/env python3
"""Validate skill quality per the official Claude Skill Guide.

Only uses Python standard library — no pyyaml dependency required.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Generator
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
RE_LEARNER_RESPONSE_DIRECTIVE = re.compile(
    r"(?:"
    r"\b(?:ask|have|prompt|invite)\s+(?:the\s+)?"
    r"(?:learner|learners|student|students)\s+"
    r"(?:(?:to\s+)?(?:answer|choose|select|respond|enter|write|name|describe|share|"
    r"identify|decide|rank|reflect|recall|consider)|"
    r"(?:where|what|which|how|why|whether)\b|"
    r"for\s+(?:an?\s+|the\s+)?"
    r"(?:answer|response|choice|goal|input|example|description|reflection|"
    r"decision|ranking|name)\b)"
    r"|(?:请|让|要求)(?:学习者|学员|学生).{0,24}"
    r"(?:回答|选择|输入|填写|作答|决定|排序|描述|分享|回忆|思考)"
    r"|(?:demandez|invitez).{0,24}(?:apprenant|élève).{0,32}"
    r"(?:répondre|choisir|sélectionner|saisir|écrire|décrire)"
    r")",
    re.IGNORECASE,
)
RE_ANSWER_DEPENDENT_BRANCH = re.compile(
    r"(?:"
    r"\b(?:after|when|once)\s+(?:the\s+)?"
    r"(?:learner|learners|student|students)\s+"
    r"(?:answers?|responds?|chooses?|selects?|decides?|enters?|writes?|names?|"
    r"describes?|shares?|identif(?:y|ies))\b"
    r"|\bif\s+(?:the\s+)?(?:learner|learners|student|students)\s+"
    r"(?:answers?|responds?|chooses?|selects?|decides?|enters?|writes?|names?|"
    r"describes?|shares?|identif(?:y|ies))\b"
    r"|\bbased on (?:the )?"
    r"(?:learner's|learners'|student's|students'|learner|learners|student|students) "
    r"(?:answer|response|choice|input)\b"
    r"|(?:学习者|学员|学生).{0,16}(?:回答|选择|输入|填写|作答|决定)后"
    r"|如果.{0,8}(?:学习者|学员|学生).{0,16}"
    r"(?:回答|选择|输入|填写|作答|决定)"
    r"|(?:按|根据).{0,16}(?:回答|答案|选择|输入).{0,16}"
    r"(?:分支|继续|调整|展示|解释|反馈)"
    r"|après.{0,32}(?:réponse|choix|saisie).{0,32}"
    r"(?:branche|adapter|continuer)"
    r"|\bsi\s+(?:l['’])?(?:apprenant|élève).{0,24}"
    r"(?:répond|choisit|sélectionne|saisit|écrit)\b"
    r")",
    re.IGNORECASE,
)
FORBIDDEN_WORDS = {"claude", "anthropic"}

# Doc surface scanned for cross-file anchor links. Local-only dirs
# (design/, evals/, scripts/) are intentionally excluded.
ANCHOR_SCAN_GLOBS = ("SKILL.md", "references/**/*.md", "examples/**/*.md")

MAX_DESCRIPTION_LEN = 1024
MIN_DESCRIPTION_LEN_RECOMMENDED = 50
MAX_COMPATIBILITY_LEN = 500
SEGMENT_TYPES = {"concept", "example", "code", "image", "exercise", "transition"}
SEGMENT_REQUIRED_KEYS = {
    "segment_id",
    "segment_type",
    "core_point",
    "preserve_block",
    "source_span",
    "transfer_signals",
}
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
SOURCE_TEXT_KEYS = {"course_material"}
INTERACTION_POLICY_MODES = {"enabled", "disabled", "unspecified"}
INTERACTION_PURPOSES = {
    "learner_context",
    "pre_content_thinking",
    "lesson_end_self_check",
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


def walk_json(value: object) -> Generator[object, None, None]:
    """Yield every nested JSON value, including the root."""
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def source_texts_for_payload(
    payload_index: int,
    source_candidates: dict[str, list[tuple[int, str]]],
) -> dict[str, str]:
    """Select the closest source value for one example output payload."""
    source_texts: dict[str, str] = {}
    for source_id, candidates in source_candidates.items():
        preceding = [item for item in candidates if item[0] <= payload_index]
        if preceding:
            source_texts[source_id] = max(preceding, key=lambda item: item[0])[1]
        else:
            source_texts[source_id] = min(candidates, key=lambda item: item[0])[1]
    return source_texts


def validate_source_span_example(
    source_span: object,
    owner: str,
    source_texts: dict[str, str],
    md_file: Path,
    issues: IssueBag,
) -> None:
    if not isinstance(source_span, dict):
        issues.add_error(f"{md_file}: {owner} must be an object")
        return

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
            f"{md_file}: {owner} must contain source_id and valid "
            "start/end offsets"
        )
        return

    source_text = source_texts.get(source_id)
    if source_text is None:
        issues.add_error(
            f"{md_file}: {owner} references unknown string source {source_id!r}"
        )
    elif end > len(source_text):
        issues.add_error(
            f"{md_file}: {owner} end {end} exceeds {source_id!r} length "
            f"{len(source_text)}"
        )


def validate_segment_example(
    segment: dict[str, object],
    source_texts: dict[str, str],
    md_file: Path,
    issues: IssueBag,
) -> None:
    missing = sorted(SEGMENT_REQUIRED_KEYS - segment.keys())
    if missing:
        issues.add_error(
            f"{md_file}: segment example {segment.get('segment_id')} "
            f"is missing required fields: {', '.join(missing)}"
        )
        return

    segment_id = segment["segment_id"]
    if not isinstance(segment_id, str) or not segment_id.strip():
        issues.add_error(
            f"{md_file}: segment example segment_id must be a non-empty string"
        )

    segment_type = segment["segment_type"]
    if not isinstance(segment_type, str) or segment_type not in SEGMENT_TYPES:
        issues.add_error(
            f"{md_file}: segment example {segment_id} has invalid segment_type "
            f"{segment_type!r}; expected one of {', '.join(sorted(SEGMENT_TYPES))}"
        )

    core_point = segment["core_point"]
    if not isinstance(core_point, str) or not core_point.strip():
        issues.add_error(
            f"{md_file}: segment example {segment_id} core_point must be a "
            "non-empty string"
        )

    if not isinstance(segment["preserve_block"], bool):
        issues.add_error(
            f"{md_file}: segment example {segment_id} preserve_block must be "
            "a boolean"
        )

    validate_source_span_example(
        segment["source_span"],
        f"segment example {segment_id} source_span",
        source_texts,
        md_file,
        issues,
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


def validate_global_variable_example(
    variable: dict[str, object], md_file: Path, issues: IssueBag
) -> None:
    required = {"name", "collected_in", "used_in", "effect_scope"}
    missing = sorted(required - variable.keys())
    if missing:
        issues.add_error(
            f"{md_file}: global variable example {variable.get('name')} "
            f"is missing required fields: {', '.join(missing)}"
        )
        return

    variable_name = variable["name"]
    if not isinstance(variable_name, str) or not re.fullmatch(
        r"\w+", variable_name
    ):
        issues.add_error(
            f"{md_file}: global variable example name must contain only "
            "letters, numbers, and underscores"
        )
    if (
        not isinstance(variable["collected_in"], str)
        or not variable["collected_in"].strip()
    ):
        issues.add_error(
            f"{md_file}: global variable example collected_in must be a "
            "non-empty string"
        )
    used_in = variable["used_in"]
    if not isinstance(used_in, list) or any(
        not isinstance(item, str) or not item.strip() for item in used_in
    ):
        issues.add_error(
            f"{md_file}: global variable example used_in must be an array "
            "of non-empty strings"
        )
    if variable["effect_scope"] != "cross_lesson":
        issues.add_error(
            f"{md_file}: global variable examples must use "
            "effect_scope 'cross_lesson'"
        )


def validate_interaction_policy_example(
    policy: object, md_file: Path, issues: IssueBag
) -> str | None:
    if not isinstance(policy, dict):
        issues.add_error(f"{md_file}: interaction_policy must be an object")
        return None

    missing = sorted({"mode", "purposes"} - policy.keys())
    if missing:
        issues.add_error(
            f"{md_file}: interaction_policy is missing required fields: "
            f"{', '.join(missing)}"
        )
        return None

    mode = policy["mode"]
    if not isinstance(mode, str) or mode not in INTERACTION_POLICY_MODES:
        issues.add_error(
            f"{md_file}: interaction_policy mode must be one of "
            f"{', '.join(sorted(INTERACTION_POLICY_MODES))}"
        )
        return None

    purposes = policy["purposes"]
    if not isinstance(purposes, list):
        issues.add_error(
            f"{md_file}: interaction_policy purposes must be an array"
        )
        return mode

    if any(
        not isinstance(purpose, str) or purpose not in INTERACTION_PURPOSES
        for purpose in purposes
    ):
        issues.add_error(
            f"{md_file}: interaction_policy purposes must use only "
            f"{', '.join(sorted(INTERACTION_PURPOSES))}"
        )
    elif len(set(purposes)) != len(purposes):
        issues.add_error(
            f"{md_file}: interaction_policy purposes must not contain duplicates"
        )

    if mode == "enabled" and not purposes:
        issues.add_error(
            f"{md_file}: enabled interaction_policy requires at least one purpose"
        )
    elif mode != "enabled" and purposes:
        issues.add_error(
            f"{md_file}: {mode} interaction_policy requires an empty purposes array"
        )
    return mode


def validate_disabled_lesson_examples(
    lessons: object,
    md_file: Path,
    issues: IssueBag,
) -> None:
    if not isinstance(lessons, list):
        issues.add_error(f"{md_file}: lesson_teaching_prompts must be an array")
        return

    for lesson_index, lesson in enumerate(lessons):
        owner = f"disabled lesson_teaching_prompts[{lesson_index}]"
        if not isinstance(lesson, dict):
            issues.add_error(f"{md_file}: {owner} must be an object")
            continue

        teaching_prompt = lesson.get("teaching_prompt")
        if not isinstance(teaching_prompt, str) or not teaching_prompt.strip():
            issues.add_error(
                f"{md_file}: {owner} teaching_prompt must be a non-empty string"
            )
        else:
            if "?[" in teaching_prompt:
                issues.add_error(
                    f"{md_file}: {owner} must not contain interaction syntax"
                )
            if "{{" in teaching_prompt:
                issues.add_error(
                    f"{md_file}: {owner} must not reference learner-answer variables"
                )
            if RE_LEARNER_RESPONSE_DIRECTIVE.search(teaching_prompt):
                issues.add_error(
                    f"{md_file}: {owner} must not solicit a learner response"
                )
            if RE_ANSWER_DEPENDENT_BRANCH.search(teaching_prompt):
                issues.add_error(
                    f"{md_file}: {owner} must not branch on a learner response"
                )

        used_variables = lesson.get("used_variables")
        if used_variables != []:
            issues.add_error(
                f"{md_file}: {owner} used_variables must be an empty array"
            )


def validate_disabled_global_variable_table_example(
    variables: object, md_file: Path, issues: IssueBag
) -> None:
    if variables != []:
        issues.add_error(
            f"{md_file}: disabled interaction_policy requires an empty "
            "global_variable_table"
        )


def course_prompt_template_lines(
    skill_dir: Path, issues: IssueBag
) -> list[str]:
    template_file = skill_dir / "references" / "course-prompt.md"
    if not template_file.is_file():
        issues.add_error(
            f"{skill_dir}: Course Prompt examples require "
            "references/course-prompt.md"
        )
        return []
    content = template_file.read_text(encoding="utf-8")
    marker = "## Fillable Template"
    if marker not in content:
        issues.add_error(
            f"{template_file}: missing required section '{marker}'"
        )
        return []
    template_section = content.split(marker, 1)[1]
    match = re.search(
        r"^```markdown[ \t]*\n(?P<body>.*?)^```[ \t]*$",
        template_section,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        issues.add_error(
            f"{template_file}: missing markdown code block under '{marker}'"
        )
        return []
    return [
        line.strip()
        for line in match.group("body").splitlines()
        if line.strip()
    ]


def validate_course_prompt_example(
    prompt: str,
    prompt_template_lines: list[str],
    md_file: Path,
    issues: IssueBag,
    is_localized: bool = False,
) -> None:
    if "XXX" in prompt:
        issues.add_error(
            f"{md_file}: Course Prompt example contains unresolved XXX"
        )

    heading_matches = list(re.finditer(r"^# [^#\n].*$", prompt, re.MULTILINE))
    if len(heading_matches) != 6:
        issues.add_error(
            f"{md_file}: Course Prompt example must contain exactly six "
            f"top-level sections, found {len(heading_matches)}"
        )
        return

    for index, heading in enumerate(heading_matches):
        body_start = heading.end()
        body_end = (
            heading_matches[index + 1].start()
            if index + 1 < len(heading_matches)
            else len(prompt)
        )
        if not prompt[body_start:body_end].strip():
            issues.add_error(
                f"{md_file}: Course Prompt example section "
                f"{heading.group(0)} must not be empty"
            )

    headings = [match.group(0).strip() for match in heading_matches]
    english_headings = [
        line for line in prompt_template_lines if line.startswith("# ")
    ]
    if headings != english_headings:
        heading_set = set(headings)
        english_heading_set = set(english_headings)
        if heading_set == english_heading_set:
            issues.add_error(
                f"{md_file}: Course Prompt example headings are out of order; "
                f"expected: {', '.join(english_headings)}"
            )
        elif english_headings and not is_localized:
            missing_headings = sorted(english_heading_set - heading_set)
            unexpected_headings = sorted(heading_set - english_heading_set)
            issues.add_error(
                f"{md_file}: Course Prompt example headings do not match "
                f"the template; missing: {', '.join(missing_headings) or 'none'}; "
                f"unexpected: {', '.join(unexpected_headings) or 'none'}"
            )
        # Localized examples cannot be compared to English instructions by exact
        # text. Their six-section shape and resolved placeholders are still
        # validated above; semantic localization remains a human review concern.
        return

    for required_line in prompt_template_lines:
        if "XXX" in required_line:
            filled_line_pattern = (
                r"^[ \t]*"
                + re.escape(required_line).replace("XXX", r"[^\n]+")
                + r"[ \t]*$"
            )
            if not re.search(filled_line_pattern, prompt, re.MULTILINE):
                issues.add_error(
                    f"{md_file}: Course Prompt example is missing filled "
                    f"placeholder line matching template: {required_line}"
                )
        elif required_line not in prompt:
            issues.add_error(
                f"{md_file}: Course Prompt example is missing template "
                f"instruction: {required_line}"
            )


def validate_example_contracts(skill_dir: Path, issues: IssueBag) -> None:
    """Keep executable examples aligned with their documented contracts."""
    if skill_dir.name != "ai-shifu-course-creator":
        return

    examples_dir = skill_dir / "examples"
    if not examples_dir.is_dir():
        return

    example_contents = [
        (md_file, md_file.read_text(encoding="utf-8"))
        for md_file in sorted(examples_dir.glob("**/*.md"))
    ]
    prompt_template_lines = course_prompt_template_lines(skill_dir, issues)
    for md_file, content in example_contents:
        parsed_payloads: list[object] = []
        for match in RE_JSON_FENCE.finditer(content):
            try:
                payload = json.loads(match.group("body"))
            except json.JSONDecodeError as exc:
                error_line = (
                    content.count("\n", 0, match.start("body")) + exc.lineno
                )
                issues.add_error(
                    f"{md_file}: invalid JSON example near line "
                    f"{error_line}: "
                    f"{exc.msg}"
                )
                continue
            parsed_payloads.append(payload)

        source_candidates: dict[str, list[tuple[int, str]]] = {}
        target_language_candidates: list[tuple[int, str]] = []
        interaction_mode_candidates: list[tuple[int, str | None]] = []
        for payload_index, payload in enumerate(parsed_payloads):
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if key in SOURCE_TEXT_KEYS and isinstance(value, str):
                        source_candidates.setdefault(key, []).append(
                            (payload_index, value)
                        )
                    if key == "target_language" and isinstance(value, str):
                        target_language_candidates.append((payload_index, value))
                    if key == "interaction_policy":
                        interaction_mode_candidates.append(
                            (
                                payload_index,
                                validate_interaction_policy_example(
                                    value, md_file, issues
                                ),
                            )
                        )

        for payload_index, payload in enumerate(parsed_payloads):
            source_texts = source_texts_for_payload(
                payload_index, source_candidates
            )
            target_language = source_texts_for_payload(
                payload_index,
                (
                    {"target_language": target_language_candidates}
                    if target_language_candidates
                    else {}
                ),
            ).get("target_language")
            is_localized = bool(target_language) and not (
                target_language.lower().startswith("en")
            )
            preceding_interaction_modes = [
                candidate
                for candidate in interaction_mode_candidates
                if candidate[0] <= payload_index
            ]
            interaction_mode = (
                max(
                    preceding_interaction_modes,
                    key=lambda candidate: candidate[0],
                )[1]
                if preceding_interaction_modes
                else None
            )
            if (
                interaction_mode == "disabled"
                and isinstance(payload, dict)
                and {"lesson_id", "teaching_prompt", "used_variables"}
                <= payload.keys()
            ):
                validate_disabled_lesson_examples(
                    [payload],
                    md_file,
                    issues,
                )
            for value in walk_json(payload):
                if not isinstance(value, dict):
                    continue
                if (
                    interaction_mode == "disabled"
                    and "lesson_teaching_prompts" in value
                ):
                    validate_disabled_lesson_examples(
                        value["lesson_teaching_prompts"],
                        md_file,
                        issues,
                    )
                if (
                    interaction_mode == "disabled"
                    and "global_variable_table" in value
                ):
                    validate_disabled_global_variable_table_example(
                        value["global_variable_table"], md_file, issues
                    )
                if "structured_segments_json" in value:
                    segments = value["structured_segments_json"]
                    if not isinstance(segments, list):
                        issues.add_error(
                            f"{md_file}: structured_segments_json must be an array"
                        )
                    else:
                        for segment_index, segment in enumerate(segments):
                            if not isinstance(segment, dict):
                                issues.add_error(
                                    f"{md_file}: structured_segments_json"
                                    f"[{segment_index}] must be an object"
                                )
                                continue
                            validate_segment_example(
                                segment, source_texts, md_file, issues
                            )
                if "course_index" in value:
                    course_index = value["course_index"]
                    if not isinstance(course_index, list):
                        issues.add_error(
                            f"{md_file}: course_index must be an array"
                        )
                        course_index = []
                    for lesson_index, lesson in enumerate(course_index):
                        if not isinstance(lesson, dict):
                            issues.add_error(
                                f"{md_file}: course_index[{lesson_index}] "
                                "must be an object"
                            )
                            continue
                        span_map = lesson.get("source_span_map")
                        if not isinstance(span_map, list):
                            issues.add_error(
                                f"{md_file}: course_index lesson "
                                f"{lesson.get('lesson_id')!r} source_span_map "
                                "must be an array"
                            )
                            continue
                        lesson_id = lesson.get("lesson_id")
                        for map_index, source_span in enumerate(span_map):
                            validate_source_span_example(
                                source_span,
                                f"course_index lesson {lesson_id!r} "
                                f"source_span_map[{map_index}]",
                                source_texts,
                                md_file,
                                issues,
                            )
                if "global_variable_table" in value:
                    variables = value["global_variable_table"]
                    if not isinstance(variables, list):
                        issues.add_error(
                            f"{md_file}: global_variable_table must be an array"
                        )
                    else:
                        for variable_index, variable in enumerate(variables):
                            if not isinstance(variable, dict):
                                issues.add_error(
                                    f"{md_file}: global_variable_table"
                                    f"[{variable_index}] must be an object"
                                )
                                continue
                            validate_global_variable_example(
                                variable, md_file, issues
                            )
                if "course_prompt" in value:
                    course_prompt = value["course_prompt"]
                    if isinstance(course_prompt, str):
                        validate_course_prompt_example(
                            course_prompt,
                            prompt_template_lines,
                            md_file,
                            issues,
                            is_localized=is_localized,
                        )
                    else:
                        issues.add_error(
                            f"{md_file}: course_prompt example must be a string"
                        )

        artifact_is_localized = bool(target_language_candidates) and all(
            not language.lower().startswith("en")
            for _, language in target_language_candidates
        )
        for match in RE_COURSE_PROMPT_ARTIFACT.finditer(content):
            validate_course_prompt_example(
                match.group("body"),
                prompt_template_lines,
                md_file,
                issues,
                is_localized=artifact_is_localized,
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
