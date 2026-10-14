from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_skill_quality  # noqa: E402


COURSE_CREATOR_REFERENCES = (
    REPO_ROOT / "skills" / "ai-shifu-course-creator" / "references"
)
PERSONALIZATION_DIRECTIONS = (
    "examples",
    "analogies",
    "language_style",
    "value_relevance",
)


def markdown_section(markdown: str, title: str) -> str:
    """Return one Markdown section, including any lower-level subsections."""
    heading_pattern = re.compile(
        rf"^(?P<marks>#{{1,6}})[ \t]+{re.escape(title)}[ \t]*$"
    )
    heading_end = None
    heading_level = None
    in_fence = False
    fence_marker = ""
    offset = 0

    for line in markdown.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence = False
            offset += len(line)
            continue
        if not in_fence:
            heading = heading_pattern.match(line.rstrip("\r\n"))
            if heading:
                heading_end = offset + len(line.rstrip("\r\n"))
                heading_level = len(heading.group("marks"))
                break
        offset += len(line)

    if heading_end is None or heading_level is None:
        raise AssertionError(f"missing Markdown section: {title}")

    section_end = heading_end
    in_fence = False
    fence_marker = ""
    for line in markdown[heading_end:].splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence = False
            section_end += len(line)
            continue
        if not in_fence:
            next_heading = re.match(r"^(#{1,6})[ \t]+", line)
            if next_heading and len(next_heading.group(1)) <= heading_level:
                return markdown[heading_end:section_end]
        section_end += len(line)
    return markdown[heading_end:]


def markdown_table_row_body(line: str) -> str:
    """Remove at most one actual outer pipe from each side of a table row."""
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        preceding_backslashes = 0
        for character in reversed(row[:-1]):
            if character != "\\":
                break
            preceding_backslashes += 1
        if preceding_backslashes % 2 == 0:
            row = row[:-1]
    return row


def split_markdown_table_row(line: str) -> list[str]:
    """Split a table row on pipes preceded by an even backslash count."""
    cells: list[str] = []
    current: list[str] = []
    preceding_backslashes = 0

    for character in markdown_table_row_body(line):
        if character == "\\":
            current.append(character)
            preceding_backslashes += 1
            continue
        if character == "|" and preceding_backslashes % 2 == 0:
            cells.append("".join(current))
            current = []
        else:
            current.append(character)
        preceding_backslashes = 0

    cells.append("".join(current))
    return cells


def markdown_table_first_column(section: str, header: str) -> list[str]:
    """Read canonical values from a Markdown table identified by its header."""
    lines = section.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [
            cell.strip().replace(r"\|", "|")
            for cell in split_markdown_table_row(line)
        ]
        if not cells or cells[0].strip("`").casefold() != header.casefold():
            continue

        values: list[str] = []
        for row in lines[index + 2 :]:
            if not row.lstrip().startswith("|"):
                break
            first_cell = split_markdown_table_row(row)[0].strip()
            values.append(first_cell.strip("`").replace(r"\|", "|"))
        return values

    raise AssertionError(f"missing Markdown table with first header: {header}")


class MarkdownSectionHelperTests(unittest.TestCase):
    def test_ignores_fenced_headings_for_target_and_boundary(self):
        markdown = (
            "```markdown\n"
            "## Target\n"
            "```\n"
            "## Target\n"
            "Body before the fence.\n"
            "```python\n"
            "# Not a boundary\n"
            "```\n"
            "Body after the fence.\n"
            "## Next\n"
            "Outside the target section.\n"
        )

        section = markdown_section(markdown, "Target")

        self.assertIn("Body before the fence.", section)
        self.assertIn("# Not a boundary", section)
        self.assertIn("Body after the fence.", section)
        self.assertNotIn("Outside the target section.", section)

    def test_table_first_column_preserves_trailing_escaped_pipes(self):
        markdown = "| Header\\||\n|---|\n| value\\||\n"

        values = markdown_table_first_column(markdown, "Header|")

        self.assertEqual(["value|"], values)

    def test_table_row_split_uses_backslash_parity(self):
        cases = (
            ("| left | right |", [" left ", " right "]),
            (r"| left\|right |", [r" left\|right "]),
            (r"| left\\| right |", [r" left\\", " right "]),
            (r"| left\\\|right |", [r" left\\\|right "]),
        )

        for row, expected in cases:
            with self.subTest(row=row):
                self.assertEqual(expected, split_markdown_table_row(row))

    def test_table_row_preserves_escaped_pipe_with_optional_outer_boundary(self):
        expected = [r" value\|"]

        self.assertEqual(expected, split_markdown_table_row(r"| value\||"))
        self.assertEqual(expected, split_markdown_table_row(r"| value\|"))


class FrontmatterValidationTests(unittest.TestCase):
    def test_course_creator_version_in_supported_metadata(self):
        skill_md = REPO_ROOT / "skills" / "ai-shifu-course-creator" / "SKILL.md"
        issues = validate_skill_quality.IssueBag()
        fields = validate_skill_quality.parse_frontmatter(skill_md, issues)
        self.assertEqual(issues.errors, [])
        self.assertIsNotNone(fields)
        self.assertRegex(
            fields["version"],
            r"\A(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z",
        )
        self.assertEqual(fields["version_management"], "standalone")


class AnchorValidationTests(unittest.TestCase):
    def test_heading_scan_recognizes_only_zero_to_three_space_fences(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            markdown_file = Path(tmpdir) / "headings.md"
            real_fences = "".join(
                f"{' ' * indentation}```markdown\n"
                f"# Hidden at {indentation} spaces\n"
                f"{' ' * indentation}```\n"
                for indentation in range(4)
            )
            markdown_file.write_text(
                real_fences
                + "    ```markdown\n"
                + "# Visible after four-space pseudo-fence\n"
                + "    ```\n",
                encoding="utf-8",
            )

            slugs = validate_skill_quality.github_heading_slugs(markdown_file)

            for indentation in range(4):
                self.assertNotIn(f"hidden-at-{indentation}-spaces", slugs)
            self.assertIn("visible-after-four-space-pseudo-fence", slugs)

    def test_heading_scan_requires_a_matching_fence_character_and_length(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            markdown_file = Path(tmpdir) / "headings.md"
            markdown_file.write_text(
                "````markdown\n"
                "# Hidden before shorter fence\n"
                "````python\n"
                "# Hidden after info-string fence\n"
                "```\n"
                "# Hidden after shorter fence\n"
                "~~~~\n"
                "# Hidden after different fence\n"
                "````\n"
                "# Visible after matching fence\n",
                encoding="utf-8",
            )

            slugs = validate_skill_quality.github_heading_slugs(markdown_file)

            self.assertEqual({"visible-after-matching-fence"}, slugs)

    def test_anchor_scan_does_not_close_on_a_fence_with_an_info_string(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "SKILL.md").write_text(
                "```markdown\n"
                "references/hidden-before.md#target\n"
                "```python\n"
                "references/hidden-after.md#target\n"
                "```\n"
                "references/visible.md#target\n",
                encoding="utf-8",
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_anchors(skill_dir, issues)

            self.assertEqual(1, len(issues.errors))
            self.assertIn("visible.md#target", issues.errors[0])

    def test_anchor_scan_recognizes_only_zero_to_three_space_fences(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            real_fences = "".join(
                f"{' ' * indentation}```markdown\n"
                f"references/hidden-{indentation}.md#target\n"
                f"{' ' * indentation}```\n"
                for indentation in range(4)
            )
            (skill_dir / "SKILL.md").write_text(
                real_fences
                + "    ```markdown\n"
                + "references/visible.md#target\n"
                + "    ```\n",
                encoding="utf-8",
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_anchors(skill_dir, issues)

            self.assertEqual(1, len(issues.errors))
            self.assertIn("visible.md#target", issues.errors[0])

    def test_ignores_anchor_references_in_fences_and_html_comments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            references = skill_dir / "references"
            references.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "```markdown\n"
                "references/missing-fenced.md#target\n"
                "```\n"
                "~~~text\n"
                "references/missing-tilde.md#target\n"
                "~~~\n"
                "<!--\n"
                "references/missing-commented.md#target\n"
                "-->\n"
                "See [target](references/existing.md#target).\n",
                encoding="utf-8",
            )
            (references / "existing.md").write_text(
                "# Target\n", encoding="utf-8"
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_anchors(skill_dir, issues)

            self.assertEqual([], issues.errors)

    def test_unclosed_html_comment_marker_does_not_hide_later_anchors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "SKILL.md").write_text(
                "Show the literal inline-code marker `<!--` here.\n"
                "Read `references/missing.md#target`.\n",
                encoding="utf-8",
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_anchors(skill_dir, issues)

            self.assertEqual(1, len(issues.errors))
            self.assertIn("missing.md#target", issues.errors[0])

    def test_still_validates_anchor_reference_in_inline_code(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "SKILL.md").write_text(
                "Read `references/missing.md#target`.\n", encoding="utf-8"
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_anchors(skill_dir, issues)

            self.assertEqual(1, len(issues.errors))
            self.assertIn("target file not found", issues.errors[0])

    def test_missing_anchor_target_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            references = skill_dir / "references"
            references.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "See [missing](references/missing.md#target).\n",
                encoding="utf-8",
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_anchors(skill_dir, issues)

            self.assertEqual(1, len(issues.errors))
            self.assertIn("target file not found", issues.errors[0])


class CoursePromptExampleValidationTests(unittest.TestCase):
    def test_noncanonical_headings_cannot_bypass_template_validation(self):
        prompt = "\n\n".join(
            f"# 非规范标题 {index}\n内容 {index}" for index in range(1, 7)
        )
        template_lines = [
            "# Role",
            "# Task",
            "# Teaching Techniques",
            "# Writing Style",
            "# Format",
            "# Slides",
        ]
        issues = validate_skill_quality.IssueBag()

        validate_skill_quality.validate_course_prompt_example(
            prompt,
            template_lines,
            Path("example.md"),
            issues,
        )

        self.assertTrue(
            any(
                "headings do not match the template" in error
                for error in issues.errors
            )
        )


class InteractionPolicyValidationTests(unittest.TestCase):
    def test_enabled_policy_requires_a_canonical_purpose(self):
        issues = validate_skill_quality.IssueBag()

        validate_skill_quality.validate_interaction_policy_example(
            {"mode": "enabled", "purposes": []},
            Path("example.md"),
            issues,
        )

        self.assertEqual(len(issues.errors), 1)
        self.assertIn("requires at least one purpose", issues.errors[0])

    def test_disabled_policy_rejects_interactive_lesson_content(self):
        issues = validate_skill_quality.IssueBag()
        lessons = [
            {
                "teaching_prompt": (
                    "Ask the learner to choose a path.\n"
                    "?[A | B]\n"
                    "Use {{learner_goal}} in the explanation.\n"
                    "After the learner answers, branch to the matching example."
                ),
                "used_variables": ["learner_goal"],
            }
        ]

        validate_skill_quality.validate_disabled_lesson_examples(
            lessons,
            Path("example.md"),
            issues,
        )

        self.assertEqual(len(issues.errors), 5)
        self.assertTrue(
            any("interaction syntax" in error for error in issues.errors)
        )
        self.assertTrue(
            any("solicit a learner response" in error for error in issues.errors)
        )
        self.assertTrue(
            any("branch on a learner response" in error for error in issues.errors)
        )

    def test_disabled_policy_rejects_localized_response_request(self):
        issues = validate_skill_quality.IssueBag()
        lessons = [
            {
                "teaching_prompt": "请学习者选择一个答案，然后按答案继续。",
                "used_variables": [],
            }
        ]

        validate_skill_quality.validate_disabled_lesson_examples(
            lessons,
            Path("example.md"),
            issues,
        )

        self.assertTrue(
            any("solicit a learner response" in error for error in issues.errors)
        )
        self.assertTrue(
            any("branch on a learner response" in error for error in issues.errors)
        )

    def test_disabled_policy_rejects_plural_learner_directives(self):
        prompts = [
            "Ask learners to choose an option.",
            "Have students write a short answer.",
        ]

        for teaching_prompt in prompts:
            with self.subTest(teaching_prompt=teaching_prompt):
                issues = validate_skill_quality.IssueBag()
                validate_skill_quality.validate_disabled_lesson_examples(
                    [
                        {
                            "teaching_prompt": teaching_prompt,
                            "used_variables": [],
                        }
                    ],
                    Path("example.md"),
                    issues,
                )

                self.assertTrue(
                    any(
                        "solicit a learner response" in error
                        for error in issues.errors
                    )
                )

    def test_disabled_policy_rejects_ask_for_directives(self):
        prompts = [
            "Ask the learner for a goal.",
            "Prompt students for an answer.",
        ]

        for teaching_prompt in prompts:
            with self.subTest(teaching_prompt=teaching_prompt):
                issues = validate_skill_quality.IssueBag()
                validate_skill_quality.validate_disabled_lesson_examples(
                    [
                        {
                            "teaching_prompt": teaching_prompt,
                            "used_variables": [],
                        }
                    ],
                    Path("example.md"),
                    issues,
                )

                self.assertTrue(
                    any(
                        "solicit a learner response" in error
                        for error in issues.errors
                    )
                )

    def test_disabled_policy_rejects_colon_directives(self):
        issues = validate_skill_quality.IssueBag()

        validate_skill_quality.validate_disabled_lesson_examples(
            [
                {
                    "teaching_prompt": "Ask the learner: Which option fits best?",
                    "used_variables": [],
                }
            ],
            Path("example.md"),
            issues,
        )

        self.assertTrue(
            any("solicit a learner response" in error for error in issues.errors)
        )

    def test_disabled_policy_rejects_conditional_response_branches(self):
        prompts = [
            "If the learner chooses A, show the matching explanation.",
            "如果学习者选择 A，展示对应解释。",
            "Si l’apprenant choisit A, affichez l’explication correspondante.",
        ]

        for teaching_prompt in prompts:
            with self.subTest(teaching_prompt=teaching_prompt):
                issues = validate_skill_quality.IssueBag()
                validate_skill_quality.validate_disabled_lesson_examples(
                    [
                        {
                            "teaching_prompt": teaching_prompt,
                            "used_variables": [],
                        }
                    ],
                    Path("example.md"),
                    issues,
                )

                self.assertTrue(
                    any(
                        "branch on a learner response" in error
                        for error in issues.errors
                    )
                )

    def test_disabled_policy_rejects_plural_response_branches(self):
        prompts = [
            "After learners answer, show feedback.",
            "If students select A, continue.",
        ]

        for teaching_prompt in prompts:
            with self.subTest(teaching_prompt=teaching_prompt):
                issues = validate_skill_quality.IssueBag()
                validate_skill_quality.validate_disabled_lesson_examples(
                    [
                        {
                            "teaching_prompt": teaching_prompt,
                            "used_variables": [],
                        }
                    ],
                    Path("example.md"),
                    issues,
                )

                self.assertTrue(
                    any(
                        "branch on a learner response" in error
                        for error in issues.errors
                    )
                )

    def test_disabled_policy_accepts_worked_application(self):
        issues = validate_skill_quality.IssueBag()
        lessons = [
            {
                "teaching_prompt": (
                    "Explain the mechanism, then show a worked decision and "
                    "close with a reusable rule."
                ),
                "used_variables": [],
            }
        ]

        validate_skill_quality.validate_disabled_lesson_examples(
            lessons,
            Path("example.md"),
            issues,
        )

        self.assertEqual(issues.errors, [])

    def test_disabled_policy_carries_across_example_json_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "ai-shifu-course-creator"
            examples_dir = skill_dir / "examples"
            references_dir = skill_dir / "references"
            examples_dir.mkdir(parents=True)
            references_dir.mkdir()
            (references_dir / "course-prompt.md").write_text(
                "## Fillable Template\n\n```markdown\n# Role\nFilled\n```\n",
                encoding="utf-8",
            )
            (examples_dir / "split-policy.md").write_text(
                """# Split Policy Example

```json
{"interaction_policy":{"mode":"disabled","purposes":[]}}
```

```json
{"lesson_teaching_prompts":[{"teaching_prompt":"?[A | B]","used_variables":[]}]}
```
""",
                encoding="utf-8",
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_example_contracts(skill_dir, issues)

            self.assertTrue(
                any("interaction syntax" in error for error in issues.errors)
            )

    def test_disabled_policy_validates_single_lesson_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "ai-shifu-course-creator"
            examples_dir = skill_dir / "examples"
            references_dir = skill_dir / "references"
            examples_dir.mkdir(parents=True)
            references_dir.mkdir()
            (references_dir / "course-prompt.md").write_text(
                "## Fillable Template\n\n```markdown\n# Role\nFilled\n```\n",
                encoding="utf-8",
            )
            (examples_dir / "single-lesson.md").write_text(
                """# Single Lesson Example

```json
{"interaction_policy":{"mode":"disabled","purposes":[]}}
```

```json
{"lesson_id":"L01","teaching_prompt":"?[A | B]","used_variables":[]}
```
""",
                encoding="utf-8",
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_example_contracts(skill_dir, issues)

            self.assertTrue(
                any("interaction syntax" in error for error in issues.errors)
            )

    def test_disabled_policy_validates_markdown_teaching_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "ai-shifu-course-creator"
            examples_dir = skill_dir / "examples"
            references_dir = skill_dir / "references"
            examples_dir.mkdir(parents=True)
            references_dir.mkdir()
            (references_dir / "course-prompt.md").write_text(
                "## Fillable Template\n\n```markdown\n# Role\nFilled\n```\n",
                encoding="utf-8",
            )
            example_file = examples_dir / "markdown-prompt.md"
            example_content = """# Markdown Teaching Prompt Example

```json
{"interaction_policy":{"mode":"disabled","purposes":[]}}
```

```markdown
Ask the learner to choose a path.
?[A | B]
```
"""
            example_file.write_text(
                example_content,
                encoding="utf-8",
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_example_contracts(skill_dir, issues)

            self.assertTrue(
                any("interaction syntax" in error for error in issues.errors)
            )
            self.assertTrue(
                any(
                    "solicit a learner response" in error
                    for error in issues.errors
                )
            )

            example_file.write_text(
                example_content.replace("```markdown", "```md"),
                encoding="utf-8",
            )
            alias_issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_example_contracts(
                skill_dir, alias_issues
            )

            self.assertTrue(
                any(
                    "interaction syntax" in error
                    for error in alias_issues.errors
                )
            )
            self.assertTrue(
                any(
                    "solicit a learner response" in error
                    for error in alias_issues.errors
                )
            )

    def test_disabled_policy_rejects_global_variable_table(self):
        issues = validate_skill_quality.IssueBag()

        validate_skill_quality.validate_disabled_global_variable_table_example(
            [
                {
                    "name": "learner_goal",
                    "collected_in": "L01",
                    "used_in": ["L02"],
                    "effect_scope": "cross_lesson",
                }
            ],
            Path("example.md"),
            issues,
        )

        self.assertEqual(len(issues.errors), 1)
        self.assertIn("empty global_variable_table", issues.errors[0])

    def test_disabled_policy_rejects_course_prompt_variables(self):
        issues = validate_skill_quality.IssueBag()

        validate_skill_quality.validate_disabled_course_prompt_example(
            "The learner goal is {{learner_goal}}.",
            Path("example.md"),
            issues,
        )

        self.assertEqual(len(issues.errors), 1)
        self.assertIn("course_prompt", issues.errors[0])
        self.assertIn("learner-answer variables", issues.errors[0])

    def test_disabled_policy_rejects_course_prompt_interactions(self):
        issues = validate_skill_quality.IssueBag()

        validate_skill_quality.validate_disabled_course_prompt_example(
            (
                "Ask the learner to choose a path.\n"
                "?[A | B]\n"
                "After the learner answers, branch to the matching guidance."
            ),
            Path("example.md"),
            issues,
        )

        self.assertEqual(len(issues.errors), 3)
        self.assertTrue(
            any("interaction syntax" in error for error in issues.errors)
        )
        self.assertTrue(
            any("solicit a learner response" in error for error in issues.errors)
        )
        self.assertTrue(
            any("branch on a learner response" in error for error in issues.errors)
        )

    def test_disabled_policy_rejects_course_prompt_artifact_variables(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "ai-shifu-course-creator"
            examples_dir = skill_dir / "examples"
            references_dir = skill_dir / "references"
            examples_dir.mkdir(parents=True)
            references_dir.mkdir()
            (references_dir / "course-prompt.md").write_text(
                "## Fillable Template\n\n```markdown\n# Role\nFilled\n```\n",
                encoding="utf-8",
            )
            (examples_dir / "course-prompt-artifact.md").write_text(
                """# Course Prompt Artifact Example

```json
{"interaction_policy":{"mode":"disabled","purposes":[]}}
```

### Course Prompt Artifact

```markdown
# Role
Use {{learner_goal}} to personalize the course.
Ask the learner to choose a path.
?[A | B]
After the learner answers, branch to the matching guidance.
```
""",
                encoding="utf-8",
            )
            issues = validate_skill_quality.IssueBag()

            validate_skill_quality.validate_example_contracts(skill_dir, issues)

            self.assertTrue(
                any(
                    "course_prompt" in error
                    and "learner-answer variables" in error
                    for error in issues.errors
                )
            )
            self.assertTrue(
                any(
                    "course_prompt" in error and "interaction syntax" in error
                    for error in issues.errors
                )
            )
            self.assertTrue(
                any(
                    "course_prompt" in error
                    and "solicit a learner response" in error
                    for error in issues.errors
                )
            )
            self.assertTrue(
                any(
                    "course_prompt" in error
                    and "branch on a learner response" in error
                    for error in issues.errors
                )
            )


class CourseCreatorContractTests(unittest.TestCase):
    """Stable artifact contracts and behavioral evaluation coverage.

    The evals judge observable results. These package checks deliberately do not
    prescribe the agent's question order, internal plan, or capability sequence.
    """

    @classmethod
    def setUpClass(cls):
        cls.skill_root = COURSE_CREATOR_REFERENCES.parent
        cls.evals = json.loads(
            (cls.skill_root / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        cls.by_id = {case["id"]: case for case in cls.evals["evals"]}

    def test_optional_personalization_control_keeps_supported_values(self):
        controls = (COURSE_CREATOR_REFERENCES / "authoring-contracts.md").read_text(
            encoding="utf-8"
        )
        values = markdown_table_first_column(
            markdown_section(controls, "Personalization Directions"), "Value"
        )
        self.assertCountEqual(PERSONALIZATION_DIRECTIONS, values)

    def test_documented_markdownflow_controls_keep_the_runtime_syntax(self):
        runtime = (COURSE_CREATOR_REFERENCES / "markdownflow-syntax.md").read_text(
            encoding="utf-8"
        )
        for syntax in (
            "?[Option A | Option B]",
            "?[Option A || Option B]",
            "?[...Input hint]",
            "?[%{{name}} Option A | Option B]",
            "?[%{{name}} ...Input hint]",
            "UNKNOWN",
            "===...===",
        ):
            with self.subTest(syntax=syntax):
                self.assertIn(syntax, runtime)

        examples = [
            match.group("body").splitlines()
            for match in validate_skill_quality.RE_MARKDOWN_FENCE.finditer(runtime)
            if match.group("body").startswith("!===\n")
        ]
        self.assertTrue(examples, "document a complete multi-line preservation fence")
        for lines in examples:
            self.assertEqual("!===", lines[-1])
            self.assertTrue(any(line.strip() for line in lines[1:-1]))

    def test_course_prompt_retains_its_six_section_artifact_interface(self):
        issues = validate_skill_quality.IssueBag()
        lines = validate_skill_quality.course_prompt_template_lines(
            self.skill_root, issues
        )
        self.assertEqual([], issues.errors)
        self.assertEqual(
            ["# Role", "# Task", "# Teaching Techniques", "# Writing Style", "# Format", "# Slides"],
            [line for line in lines if line.startswith("# ")],
        )

    def test_teaching_prompt_examples_keep_runtime_content_outside_comments(self):
        document = (COURSE_CREATOR_REFERENCES / "teaching-prompt.md").read_text(
            encoding="utf-8"
        )
        examples = list(validate_skill_quality.RE_MARKDOWN_FENCE.finditer(document))
        self.assertGreaterEqual(len(examples), 3)
        layouts = set()
        for example in examples:
            body = example.group("body")
            comments = re.findall(r"<!--(.*?)-->", body, re.DOTALL)
            runtime = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL).strip()
            self.assertTrue(comments)
            self.assertTrue(runtime)
            for comment in comments:
                self.assertNotIn("<!--", comment)
                self.assertNotIn("-->", comment)
                self.assertNotRegex(comment, r"\?\[|\{\{|https?://|!===|===")
            for control in re.findall(r"(?m)^\?\[[^\n]+\]$", body):
                self.assertIn(control, runtime)
            layouts.add("list" if re.search(r"(?m)^- ", runtime) else "paragraph")
        self.assertEqual({"list", "paragraph"}, layouts)

    def test_behavioral_evaluation_manifest_is_usable(self):
        self.assertEqual("AI-Shifu Course Creator", self.evals["skill_name"])
        cases = self.evals["evals"]
        self.assertEqual(len(cases), len(self.by_id), "evaluation IDs must be unique")
        for case in cases:
            with self.subTest(case_id=case["id"]):
                self.assertIsInstance(case["id"], int)
                self.assertTrue(case["prompt"].strip())
                self.assertTrue(case["expected_output"].strip())
                self.assertIsInstance(case["files"], list)
                self.assertGreaterEqual(len(case["expectations"]), 2)
                self.assertTrue(all(value.strip() for value in case["expectations"]))

    def assert_eval_family(self, case_ids: tuple[int, ...], concepts: tuple[str, ...]):
        for case_id in case_ids:
            self.assertIn(case_id, self.by_id)
        criteria = " ".join(
            criterion
            for case_id in case_ids
            for criterion in self.by_id[case_id]["expectations"]
        ).casefold()
        for concept in concepts:
            with self.subTest(concept=concept, case_ids=case_ids):
                self.assertIn(concept.casefold(), criteria)

    def test_evals_preserve_runtime_source_and_variable_regressions(self):
        self.assert_eval_family(
            (8, 9, 15, 16, 17, 33, 51, 52),
            ("UNKNOWN", "deterministic", "exact", "feedback", "named variable"),
        )

    def test_evals_preserve_selected_and_empty_personalization(self):
        self.assert_eval_family(
            (19, 20, 37, 38, 71, 72, 85, 86, 87, 88, 89, 90, 91),
            ("unselected", "empty selection", "fallback", "not-assessed", "source"),
        )

    def test_evals_preserve_new_course_approval_publication_and_truthful_handoff(self):
        self.assert_eval_family(
            (54, 55, 56, 61, 63, 64, 65, 66, 67, 70, 104),
            ("approval", "publish", "preview", "draft", "verified", "effective", "same JSON file"),
        )

    def test_evals_preserve_existing_course_sync_and_conflict_boundaries(self):
        self.assert_eval_family(
            (5, 57, 58, 59, 61, 68, 69, 78, 105),
            ("existing", "version", "conflict", "no-match", "access", "unpushed", "standalone explicit rename", "local-only audit"),
        )

    def test_evals_preserve_contact_browser_and_analytics_boundaries(self):
        self.assert_eval_family(
            (2, 28, 29, 30, 31, 32, 46, 47, 48, 49, 100, 101),
            ("contact", "browser", "Markdown link", "raw IDs", "verification", "privacy", "masked", "UTC"),
        )

    def test_evals_cover_standalone_capabilities_without_intermediate_artifacts(self):
        self.assert_eval_family(
            (74, 75, 92, 93, 94, 98),
            ("directly", "description", "one runnable", "JSON", "without"),
        )

    def test_evals_cover_custom_design_and_multiple_readable_layouts(self):
        self.assert_eval_family(
            (95, 96, 99),
            ("custom", "paragraph", "unordered", "slide", "HTML", "standalone"),
        )

    def test_evals_cover_audit_and_limited_repair_without_forced_reformatting(self):
        self.assert_eval_family(
            (33, 91, 97),
            ("audit", "not-assessed", "navigation comments", "without rewriting"),
        )

    def test_evals_cover_design_only_and_faithful_runtime_expression(self):
        self.assert_eval_family(
            (102, 103),
            ("teaching design", "source", "unchanged", "feedback", "MarkdownFlow", "CLI", "intermediate"),
        )

    def test_discovery_evals_include_isolated_capabilities_and_other_platforms(self):
        cases = json.loads(
            (self.skill_root / "evals" / "trigger_eval.json").read_text(encoding="utf-8")
        )
        self.assertTrue(any(case["should_trigger"] for case in cases))
        self.assertTrue(any(not case["should_trigger"] for case in cases))
        for case in cases:
            self.assertTrue(case["query"].strip())
            self.assertIsInstance(case["should_trigger"], bool)


if __name__ == "__main__":
    unittest.main()
