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
    @classmethod
    def setUpClass(cls):
        cls.skill_root = COURSE_CREATOR_REFERENCES.parent
        cls.skill_doc = (cls.skill_root / "SKILL.md").read_text(encoding="utf-8")

        def load(filename: str) -> str:
            return (COURSE_CREATOR_REFERENCES / filename).read_text(
                encoding="utf-8"
            )

        cls.language_policy = load("language-policy.md")
        cls.data_contracts = load("data-contracts.md")
        cls.course_design_intake = load("course-design-intake.md")
        cls.prompt_contracts = load("prompt-contracts.md")
        cls.pedagogy = load("pedagogy.md")
        cls.markdownflow = load("markdownflow.md")
        cls.markdownflow_authoring = load("markdownflow-authoring.md")
        cls.source_preservation = load("source-preservation.md")
        cls.teaching_prompt = load("teaching-prompt.md")
        cls.image_authoring = load("image-authoring.md")
        cls.orchestration_workflow = load("orchestration-workflow.md")
        cls.course_prompt = load("course-prompt.md")
        cls.course_description = load("course-description.md")
        cls.optimization_workflow = load("optimization-workflow.md")
        cls.optimization_checklist = load("optimization-checklist.md")
        cls.deployment_workflow = load("deployment-workflow.md")
        cls.course_sync = load("course-sync.md")
        cls.course_management = load("course-management.md")
        cls.report_template = load("report-template.md")
        cls.course_directory_spec = load("cli/course-directory-spec.md")
        cls.cli_reference = load("cli/cli-reference.md")

    def test_prompt_semantics_are_centralized(self):
        semantics_section = markdown_section(
            self.prompt_contracts, "Prompt Semantics"
        )
        semantics = " ".join(semantics_section.split())

        self.assertIn("Prompts, not Scripts", semantics)
        self.assertIn(
            "The **Teaching Agent** is AI-Shifu's learner-time AI role", semantics
        )
        self.assertIn("gives interaction feedback", semantics)
        self.assertIn("answers learner follow-up questions", semantics)
        self.assertIn("different underlying models", semantics)
        self.assertIn("tell the Teaching Agent how to teach the learner", semantics)
        self.assertIn(
            "turn the resolved lesson design into the actual sequence of "
            "learner-time teaching actions",
            semantics,
        )
        self.assertIn(
            "Depending on its selected personalization level",
            semantics,
        )
        self.assertIn(
            "a transient authoring control, not runtime Prompt content",
            semantics,
        )
        self.assertIn(
            "the level controls how much ordinary title, explanation, "
            "transition, example-detail, and non-deterministic feedback wording "
            "generation writes into the local runtime instructions",
            semantics,
        )
        self.assertIn(
            "a local instruction may include near-final learner-visible wording "
            "or only the message, evidence, boundaries, selection constraints, "
            "and effect needed at that point",
            semantics,
        )
        self.assertIn(
            "Precision chosen for ordinary content expression is separate from "
            "exact output",
            semantics,
        )
        self.assertIn(
            'Directions such as "explain the concept", "add an example", or '
            '"ask a question" are incomplete',
            semantics,
        )
        self.assertIn(
            "Within Prompt instructions, every second-person form in any "
            "language refers only to the Teaching Agent",
            semantics,
        )
        self.assertIn("`you`, `your`, `yours`, and `yourself`", semantics)
        self.assertIn("`你`, `您`, and their possessive forms", semantics)
        self.assertIn('"the learner" or "the student"', semantics)
        self.assertIn(
            "Learner-visible text inside a MarkdownFlow `?[]` interaction or "
            "[standalone deterministic output]"
            "(markdownflow.md#deterministic-blocks) is the exception",
            semantics,
        )
        self.assertIn(
            "Outside `?[]` and standalone deterministic output", semantics
        )
        self.assertIn(
            "Every part of its body serves learner-time delivery", semantics
        )
        self.assertIn(
            "Represent the lesson structure through the order and grouping of "
            "those runtime instructions",
            semantics,
        )
        self.assertIn(
            "remains in the in-memory handoff and owning references", semantics
        )
        self.assertNotIn("internal design notes may appear", self.prompt_contracts)
        self.assertNotIn("HTML comments", self.prompt_contracts)
        self.assertNotIn("## Authority Index", self.prompt_contracts)
        required = markdown_section(
            self.prompt_contracts, "Required References"
        )
        self.assertIn("`markdownflow.md#interactions`", required)
        self.assertIn("`markdownflow.md#deterministic-blocks`", required)

        for path in COURSE_CREATOR_REFERENCES.rglob("*.md"):
            if path.name == "prompt-contracts.md":
                continue
            self.assertNotIn(
                "\n## Prompt Semantics\n",
                path.read_text(encoding="utf-8"),
                f"Prompt semantics must be owned only by prompt-contracts.md: {path}",
            )

    def test_teaching_agent_is_the_canonical_human_facing_term(self):
        self.assertIn(
            "| `Teaching Agent` | Teaching Agent | 授课智能体 |",
            self.language_policy,
        )
        first_mention = " ".join(
            markdown_section(
                self.language_policy, "Teaching Agent First Mention"
            ).split()
        )
        for fragment in (
            "skill's first user-facing mention of the Teaching Agent concept",
            "in a conversation",
            "`AI-Shifu's Teaching Agent`",
            "`AI 师傅的授课智能体`",
            "After that introduction in the same conversation",
            "canonical short form",
            "no conversation context",
            "always use the product-qualified form",
            "do not add an ownership introduction to Teaching Prompt or Course "
            "Prompt content solely to satisfy it",
            "do not change preserved source wording or machine-facing fields",
        ):
            self.assertIn(fragment, first_mention)

        deprecated_terms = {
            "runtime llm",
            "the llm",
            "llm-generated",
            "llm-mediated",
            "ai narration",
            "ai answer",
            "teacher / ai",
            "teacher/ai",
            "model-led",
        }
        paths = list(self.skill_root.rglob("*.md"))
        paths.append(self.skill_root / "scripts" / "shifu-cli.py")
        surfaces = [
            (
                str(path.relative_to(REPO_ROOT)),
                path.read_text(encoding="utf-8"),
            )
            for path in paths
        ]
        evals_path = self.skill_root / "evals" / "evals.json"
        evals_data = json.loads(evals_path.read_text(encoding="utf-8"))
        evals_by_id = {case["id"]: case for case in evals_data["evals"]}
        self.assertIn("AI 旁白", evals_by_id[17]["prompt"])
        self.assertIn("AI 旁白", evals_by_id[20]["prompt"])
        for case_id in (18, 22, 23):
            skill_owned_text = "\n".join(
                [
                    evals_by_id[case_id].get("expected_output", ""),
                    *evals_by_id[case_id].get("expectations", []),
                ]
            )
            self.assertIn("AI 师傅的授课智能体", skill_owned_text)
        for case in evals_data["evals"]:
            skill_owned_text = "\n".join(
                [case.get("expected_output", ""), *case.get("expectations", [])]
            )
            surfaces.append(
                (
                    f"{evals_path.relative_to(REPO_ROOT)}#{case['id']}",
                    skill_owned_text,
                )
            )

        matches = []
        for label, surface in surfaces:
            content = surface.casefold()
            for term in deprecated_terms:
                if term in content:
                    matches.append(f"{label}: {term}")

        self.assertEqual([], matches)
        self.assertIn(
            "stable machine-facing fields for the underlying models and settings "
            "used by the Teaching Agent",
            self.course_directory_spec,
        )
        self.assertIn(
            "human-facing explanations identify AI-Shifu ownership on the first "
            "Teaching Agent mention and use Teaching Agent thereafter",
            self.course_directory_spec,
        )
        cli_script = (
            self.skill_root / "scripts" / "shifu-cli.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'print(f"AI-Shifu\'s Teaching Agent model: {model}")', cli_script
        )
        self.assertIn(
            "(1101 AI-Shifu's Teaching Agent / 1102 TTS)", cli_script
        )

    def test_deprecated_prompt_phrasing_stays_out_of_other_docs(self):
        deprecated_fragments = {
            "## script style",
            "script that guides teaching",
            "model-guiding language",
            "instructional/directive language only",
            "final learner manuscript",
            'address the learner only as "you"',
        }
        matches = []

        for path in self.skill_root.rglob("*.md"):
            if path.name == "prompt-contracts.md":
                continue
            content = path.read_text(encoding="utf-8").casefold()
            for fragment in deprecated_fragments:
                if fragment in content:
                    matches.append(
                        f"{path.relative_to(REPO_ROOT)}: {fragment}"
                    )

        self.assertEqual([], matches)

    def test_markdownflow_contains_observable_runtime_semantics(self):
        preprocessing = markdown_section(self.markdownflow, "Preprocessing")
        variables = markdown_section(self.markdownflow, "Variables")
        interactions = markdown_section(self.markdownflow, "Interactions")
        branching = markdown_section(
            self.markdownflow, "Branching on User Input"
        )
        deterministic = markdown_section(
            self.markdownflow, "Deterministic Blocks"
        )
        images = markdown_section(self.markdownflow, "Images")
        preservation = markdown_section(self.markdownflow, "Preservation")

        self.assertIn("CommonMark fenced code", preprocessing)
        self.assertIn("HTML comments", preprocessing)
        self.assertIn("`UNKNOWN`", variables)
        self.assertIn("`%{{name}}` is an assignment prefix", variables)
        self.assertIn("pauses document progression", interactions)
        self.assertIn("current document context", interactions)
        interaction_forms = re.findall(
            r"^- `(\?\[[^`\n]+\])`:",
            interactions,
            flags=re.MULTILINE,
        )
        self.assertEqual(
            [
                "?[Continue]",
                "?[Option A | Option B]",
                "?[Option A || Option B]",
                "?[...Input hint]",
                "?[Option A | ...Other]",
                "?[Option A || ...Other]",
                "?[%{{name}} Option A | Option B]",
                "?[%{{name}} Option A || Option B]",
                "?[%{{name}} ...Input hint]",
                "?[%{{name}} Option A | ...Other]",
                "?[%{{name}} Option A || ...Other]",
            ],
            interaction_forms,
        )
        self.assertNotIn(r"\|", interactions)
        self.assertIn("no parser-level conditionals", branching)
        self.assertIn(
            "Single-line or inline marker: `===fixed text===`", deterministic
        )
        self.assertIn(
            "```markdown\n!===\n\nParagraph 1\n\nParagraph 2\n\n!===\n```",
            deterministic,
        )
        self.assertIn(
            "without requiring any additional boundary syntax", deterministic
        )
        self.assertIn("without invoking the Teaching Agent", deterministic)
        self.assertIn(
            "When `===...===` appears inline within ordinary prompt content",
            deterministic,
        )
        self.assertIn(
            "surrounding content remains generated by the Teaching Agent",
            deterministic,
        )
        self.assertIn("no image-specific control-flow primitive", images)
        self.assertIn("no dedicated parser semantics", images)
        self.assertIn(
            "inline `===...===` marker remains in content mediated by the "
            "Teaching Agent",
            preservation,
        )
        self.assertIn(
            "Content outside these mechanisms may be paraphrased", preservation
        )

    def test_markdownflow_is_runtime_only(self):
        expected_headings = {
            "markdownflow-spec",
            "required-references",
            "preprocessing",
            "variables",
            "interactions",
            "branching-on-user-input",
            "deterministic-blocks",
            "images",
            "preservation",
        }
        actual_headings = validate_skill_quality.github_heading_slugs(
            COURSE_CREATOR_REFERENCES / "markdownflow.md"
        )
        self.assertEqual(expected_headings, actual_headings)

        forbidden_authoring_fragments = {
            "answer must leave the current lesson",
            "Use single-select for",
            "Use multi-select for",
            "Prompt Placement Rules",
            "Input Marker Rules",
            "Which form to use",
            "upload-image",
            "res.ai-shifu.cn",
            "必须原样保留",
            "不得省略",
            "语义化 alt",
            "保持原始宽高比",
            "Raw SVG, HTML drawings, Mermaid",
            "pedagogy.md",
            "markdownflow-authoring.md",
            "image-authoring.md",
            "data-contracts.md",
        }
        for fragment in forbidden_authoring_fragments:
            self.assertNotIn(fragment, self.markdownflow)

        internal_taxonomy = {
            "processing model",
            "parsed block",
            "content block",
            "generative block",
            "preserved-content block",
            "preserved content block",
            "interaction block",
            "block separator",
        }
        for term in internal_taxonomy:
            self.assertNotIn(term, self.markdownflow.casefold())
        self.assertNotIn("`---`", self.markdownflow)
        self.assertNotRegex(self.markdownflow, r"(?m)^\s*---\s*$")

    def test_language_resolution_and_audit_are_owned_by_language_policy(self):
        resolution = markdown_section(
            self.language_policy, "Language Resolution"
        )
        priority = markdown_section(resolution, "Priority Order")
        priority_items = [
            line
            for line in priority.splitlines()
            if re.match(r"^\d+\.\s+", line)
        ]
        priority_identifiers = [
            line.split("`", 2)[1] for line in priority_items
        ]

        self.assertEqual(
            [
                "context_language_directive",
                "prompt_language_detection",
            ],
            priority_identifiers,
        )
        self.assertIn(
            "any applicable context explicitly specifies", priority
        )
        self.assertIn(
            "otherwise, use the language detected from the", priority
        )
        self.assertIn("follow the normal instruction hierarchy", priority)
        self.assertIn("most recent applicable directive", priority)
        self.assertIn(
            "`resolved_target_language` is a string", resolution
        )
        self.assertIn("## Localization Scope", self.language_policy)
        self.assertIn("## Localization Exclusions", self.language_policy)
        self.assertIn("## Language Audit", self.language_policy)

        for path in COURSE_CREATOR_REFERENCES.rglob("*.md"):
            if path.name == "language-policy.md":
                continue
            self.assertNotIn(
                "\n## Language Resolution\n",
                path.read_text(encoding="utf-8"),
                f"language resolution must be single-sourced: {path}",
            )

        template = (REPO_ROOT / "templates" / "skill.yaml.template").read_text(
            encoding="utf-8"
        )
        template_resolution = template.split(
            "language_resolution:", 1
        )[1].split("inputs:", 1)[0]
        template_priority_identifiers = re.findall(
            r'^\s+-\s+"([^"]+)"$',
            template_resolution,
            re.MULTILINE,
        )
        self.assertEqual(
            priority_identifiers,
            template_priority_identifiers,
        )
        self.assertNotIn("resolved_target_language", self.data_contracts)
        self.assertNotIn("## Language Audit", self.optimization_checklist)

    def test_schema_enums_match_the_validator(self):
        transfer_section = markdown_section(
            self.data_contracts, "Transfer Signals"
        )
        data_contract_keys = markdown_table_first_column(
            transfer_section, "Key"
        )
        self.assertEqual(len(data_contract_keys), len(set(data_contract_keys)))
        self.assertEqual(
            set(data_contract_keys),
            validate_skill_quality.TRANSFER_SIGNAL_KEYS,
        )

        policy_section = markdown_section(
            self.pedagogy, "Interaction Policy Precedence"
        )
        modes = markdown_table_first_column(policy_section, "Mode")
        purposes = markdown_table_first_column(policy_section, "Purpose")
        self.assertEqual(len(modes), len(set(modes)))
        self.assertEqual(len(purposes), len(set(purposes)))
        self.assertEqual(
            set(modes), validate_skill_quality.INTERACTION_POLICY_MODES
        )
        self.assertEqual(
            set(purposes), validate_skill_quality.INTERACTION_PURPOSES
        )
        self.assertNotIn("## Language Resolution", self.data_contracts)
        self.assertNotIn("## Teaching Patterns", self.data_contracts)

    def test_personalization_level_is_a_transient_input_contract(self):
        personalization = markdown_section(
            self.data_contracts, "Teaching Prompt Personalization Level"
        )
        normalized = " ".join(personalization.split())

        self.assertIn("`teaching_prompt_personalization_level`", normalized)
        self.assertIn("top-level scalar", normalized)
        self.assertIn(
            "content-expression control, not a structure control", normalized
        )
        self.assertIn(
            "never changes the internal lesson execution plan, including the "
            "teaching sequence, required actions and effects, slide count and "
            "order, or interaction and feedback placement",
            normalized,
        )
        self.assertRegex(
            self.data_contracts,
            r"`teaching_prompt_personalization_level` \(integer from `1` "
            r"through `5`\):.*transient authoring input",
        )
        self.assertIn("in-memory authoring handoff", normalized)
        self.assertIn(
            "Its only effect on `teaching_prompt` is the amount of ordinary "
            "wording and already-permitted example detail materialized inside "
            "direct local runtime instructions",
            normalized,
        )
        self.assertIn(
            "Keep the control's name, value, and authoring semantics absent "
            "from Prompt bodies",
            normalized,
        )
        for excluded_surface in (
            "lesson_teaching_prompts",
            "course-directory files",
            "CLI inputs or configuration",
            "deployment payloads",
            "platform metadata",
        ):
            self.assertIn(excluded_surface, normalized)
        self.assertIn(
            "Reject booleans, floats, numeric strings, and out-of-range values",
            self.data_contracts,
        )

        output_contract = markdown_section(self.data_contracts, "Output Contract")
        self.assertNotIn(
            "teaching_prompt_personalization_level", output_contract
        )
        self.assertNotIn(
            "teaching_prompt_personalization_level", self.course_directory_spec
        )
        self.assertNotIn(
            "teaching_prompt_personalization_level", self.cli_reference
        )

    def test_authoring_state_materializes_as_direct_runtime_instructions(self):
        semantics = " ".join(
            markdown_section(self.prompt_contracts, "Prompt Semantics").split()
        )
        generation = " ".join(
            markdown_section(self.teaching_prompt, "Generation").split()
        )
        validation = " ".join(
            markdown_section(self.teaching_prompt, "Validation").split()
        )
        gates = " ".join(
            markdown_section(
                self.orchestration_workflow, "Mandatory Gates"
            ).split()
        )
        repair = " ".join(
            markdown_section(
                self.optimization_checklist, "Language and Repair Scope"
            ).split()
        )

        self.assertIn(
            "leaving the rest unwritten is the materialization of that "
            "authoring choice",
            semantics,
        )
        self.assertIn(
            "Materialize the plan as direct local instructions to the Teaching "
            "Agent in learner-time execution order",
            generation,
        )
        self.assertIn(
            "Begin with the first teaching action for the selected delivery mode",
            generation,
        )
        self.assertIn(
            "Insert every selected interaction, deterministic block, required "
            "code or source span, and image instruction directly at its resolved "
            "learner-time position",
            generation,
        )
        self.assertIn(
            "When the level leaves ordinary expression open, write only those "
            "required runtime elements and end the instruction there",
            generation,
        )
        self.assertIn(
            "Recover the execution signature from the Teaching Prompt's actual "
            "ordered instructions",
            validation,
        )
        self.assertIn(
            "open ordinary expression is visible as a shorter local instruction",
            validation,
        )
        self.assertIn(
            "Recover each Teaching Prompt's execution signature from its actual "
            "ordered instructions",
            gates,
        )
        self.assertIn("interaction-control-feedback adjacency", gates)
        self.assertIn(
            "When a Teaching Prompt contains an authoring rationale or a summary "
            "of its internal execution plan",
            repair,
        )
        self.assertIn(
            "Fold lesson-specific behavior into the corresponding local teaching, "
            "slide, interaction, feedback, or close instruction",
            repair,
        )
        self.assertIn(
            "leave course-wide uniform presentation behavior with the Course Prompt",
            repair,
        )
        self.assertIn(
            "The shorter instruction carries that choice without a replacement "
            "explanation about adaptable wording or detail",
            repair,
        )
        self.assertIn(
            "Classify a passage by its function in learner-time execution",
            repair,
        )
        self.assertIn("not by the presence of authoring vocabulary alone", repair)

    def test_runtime_schema_markdownflow_and_variable_contracts_stay_stable(self):
        lesson_schema = markdown_section(self.data_contracts, "Lesson Schema")
        variable_table = markdown_section(self.data_contracts, "Variable Table")
        interactions = markdown_section(self.markdownflow, "Interactions")
        variables = markdown_section(self.markdownflow, "Variables")

        for field in (
            "`lesson_id` (string, required)",
            "`lesson_title` (string, required)",
            "`teaching_prompt` (string, required)",
            "`used_variables` (array of strings, required)",
            "`depends_on_lessons` (array of lesson ids, required)",
        ):
            self.assertIn(field, lesson_schema)
        self.assertNotIn(
            "teaching_prompt_personalization_level", lesson_schema
        )

        for syntax in (
            "`?[Option A | Option B]`",
            "`?[Option A || Option B]`",
            "`?[...Input hint]`",
            "`?[%{{name}} Option A | Option B]`",
        ):
            self.assertIn(syntax, interactions)
        self.assertIn("`UNKNOWN`", variables)
        self.assertIn(
            "Only named variables belong in `global_variable_table`",
            variable_table,
        )
        self.assertIn(
            "no-variable `?[...]` interactions do not create entries",
            variable_table,
        )
        self.assertIn(
            "Every item in `used_variables` has a matching "
            "`global_variable_table` entry",
            lesson_schema,
        )

    def test_generation_evals_grade_runtime_sequence_not_authoring_labels(self):
        evals_data = json.loads(
            (self.skill_root / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        evals_by_id = {case["id"]: case for case in evals_data["evals"]}

        for case_id in (10, 15, 16, 17, 19, 20, 26):
            expectations = " ".join(evals_by_id[case_id]["expectations"])
            self.assertRegex(
                expectations,
                r"(?i)(?:actual|emitted|runtime|learner-time|page directions|"
                r"proceeds directly)",
            )
            self.assertRegex(
                expectations,
                r"(?i)(?:author-facing|global authoring|authoring note)",
            )

        self.assertIn(
            "三份都直接按下面的运行时顺序写",
            evals_by_id[19]["prompt"],
        )
        self.assertIn(
            "The actual runtime directions in all three variants",
            " ".join(evals_by_id[19]["expectations"]),
        )
        self.assertIn(
            "两份都直接按下面顺序创建四页",
            evals_by_id[20]["prompt"],
        )
        self.assertIn(
            "The actual page directions in both variants",
            " ".join(evals_by_id[20]["expectations"]),
        )
        for case_id in (15, 16, 17, 19, 20):
            expectations = " ".join(evals_by_id[case_id]["expectations"])
            self.assertRegex(
                expectations,
                r"(?i)(?:no .*sentence|not through replacement sentences|"
                r"do not add local meta-instructions)",
            )

        regression = evals_by_id[33]
        page_numbers = [
            int(value)
            for value in re.findall(r"第 (\d+) 页：", regression["prompt"])
        ]
        self.assertEqual(list(range(1, 32)), page_numbers)
        self.assertIn(
            "本节采用标准一对一教学。严格按照下列顺序创建 31 张",
            regression["prompt"],
        )
        self.assertIn(
            "下文只有这些精确岛必须原样保留", regression["prompt"]
        )
        self.assertEqual(3, regression["prompt"].count("\n?["))
        regression_expectations = " ".join(regression["expectations"])
        self.assertIn("exactly 31 page directions", regression_expectations)
        self.assertIn(
            "contains no global passage whose only function is to explain the "
            "authoring skeleton",
            regression_expectations,
        )
        self.assertIn(
            "failure depends on whether a passage explains the authoring "
            "process rather than instructing learner-time teaching",
            regression_expectations,
        )
        self.assertIn(
            "`16:9`, visual, and Logo rules from the leaked wrapper are not "
            "copied into or distributed across the 31 local page directions",
            regression_expectations,
        )

    def test_intake_asks_for_personalization_after_usage_and_before_interactions(self):
        scope = markdown_section(self.course_design_intake, "Intake Scope")
        normalized_scope = " ".join(scope.split())

        usage_step = re.search(
            r"(?m)^1\.\s+Ask which usage scenarios the course should support", scope
        )
        personalization_step = re.search(
            r"(?m)^2\.\s+.*(?:personalization|personalisation)", scope
        )
        interaction_step = re.search(r"(?m)^3\.\s+.*interaction", scope)
        self.assertIsNotNone(usage_step)
        self.assertIsNotNone(personalization_step)
        self.assertIsNotNone(interaction_step)
        self.assertLess(usage_step.start(), personalization_step.start())
        self.assertLess(personalization_step.start(), interaction_step.start())

        personalization_block = scope[
            personalization_step.start() : interaction_step.start()
        ]
        choices = re.findall(
            r"`([1-5])`\s+—\s+([^,.;\n]+)", personalization_block
        )
        self.assertEqual(["1", "2", "3", "4", "5"], [n for n, _ in choices])
        self.assertRegex(choices[0][1], r"(?i)certainty|determin")
        self.assertRegex(choices[2][1], r"(?i)balanced")
        self.assertRegex(choices[4][1], r"(?i)personalization|personalisation")
        self.assertRegex(normalized_scope, r"(?i)higher.*intent.*key points")
        self.assertRegex(
            normalized_scope,
            r"(?i)fixing less.*wording.*example identity and detail.*feedback wording",
        )
        self.assertRegex(
            normalized_scope,
            r"(?i)complete teaching sequence.*exact slide count.*slide.*position.*"
            r"teaching purpose.*content slots appear.*where they appear.*"
            r"teaching purpose.*whether an example is "
            r"required.*stay fixed at every level.*only expression inside those "
            r"slots varies",
        )
        self.assertIn("teaching-prompt.md#personalization-levels", personalization_block)
        self.assertIn("`resolved_target_language`", personalization_block)
        self.assertIn("Do not silently skip this question", scope)

        controls = markdown_section(
            self.course_design_intake, "Normalized Design Controls"
        )
        normalized_controls = " ".join(controls.split())
        self.assertIn("`teaching_prompt_personalization_level`", controls)
        self.assertIn("Reuse a value already present in context", controls)
        self.assertRegex(
            normalized_controls,
            r"(?i)(?:fall back|fallback) level `?3`? only when the author "
            r"explicitly skips or asks to continue without answering",
        )
        self.assertIn("absence alone is not a skip", controls)

    def test_intake_explains_the_effect_of_every_design_question(self):
        required = markdown_section(self.course_design_intake, "Required References")
        scope = markdown_section(self.course_design_intake, "Intake Scope")
        validation = markdown_section(self.course_design_intake, "Validation")
        normalized_scope = " ".join(scope.split())

        self.assertIn("data-contracts.md#input-contract", required)
        self.assertIn("pedagogy.md#interaction-policy-precedence", required)
        self.assertIn("pedagogy.md#visual-text-coordination", required)
        for fragment in (
            "Before every applicable question, give a concise effect preview",
            "downstream course decision",
            "learner- or author-visible effect of every option presented",
            "without adding a separate sales pitch or an unsupported outcome",
            "language-policy.md#teaching-agent-first-mention",
            "Never present only bare option labels, numbers, or names",
            "explain the tradeoff dimensions before asking",
        ):
            self.assertIn(fragment, normalized_scope)

        question_effects = {
            1: (
                "controls the learner's delivery experience",
                "lets the Teaching Agent guide one learner directly",
                "projection-ready content paced by a human instructor",
                "both experiences",
            ),
            2: (
                "uses only learner context already available",
                "never authorizes new context collection, interactions, variables, or branches",
                "what the author will see fixed in advance",
                "what the Teaching Agent may adapt for the learner",
            ),
            3: (
                "at an early course or module point",
                "later teaching selected context to use",
                "initial judgment to refine",
                "check or consolidate the lesson's core understanding",
                "worked applications, demonstrations by the Teaching Agent, "
                "or consolidation",
            ),
            4: (
                "adds AI voice with slides",
                "consumes more AI-Shifu credits",
                "leaves the course available without Listen Mode",
                "avoids that additional credit consumption",
            ),
            5: (
                "chapter count controls how lessons are grouped into broader topics",
                "lesson count controls course granularity",
                "fewer lessons concentrate more material into each lesson",
                "more lessons distribute it across more single-question units",
            ),
            6: (
                "AI-Shifu's Teaching Agent",
                "teacher identity during course delivery",
                "leaving it blank does not affect course creation",
                "unanswered question defaults to no named teacher identity",
            ),
        }
        step_starts = {}
        for number in question_effects:
            match = re.search(rf"(?m)^{number}\.\s+", scope)
            self.assertIsNotNone(match, f"Step {number} not found in scope")
            step_starts[number] = match.start()
        for number, fragments in question_effects.items():
            end = step_starts.get(number + 1, len(scope))
            step = " ".join(scope[step_starts[number] : end].split())
            for fragment in fragments:
                self.assertIn(fragment, step, f"missing effect for intake question {number}")

        normalized_validation = " ".join(validation.split())
        self.assertIn("Every asked question includes an effect preview", normalized_validation)
        self.assertIn("rather than showing a bare label", normalized_validation)
        self.assertIn("make no promotional or unsupported promise", normalized_validation)

    def test_slide_only_intake_uses_high_determinism_without_asking(self):
        scope = markdown_section(self.course_design_intake, "Intake Scope")
        normalized_scope = " ".join(scope.split())
        self.assertRegex(
            normalized_scope,
            r"(?i)slide-only delivery with no already-provided level, "
            r"do not ask it and use level `1` \(High determinism\)",
        )
        self.assertIn(
            "Do not silently skip this question for standard or combined delivery",
            normalized_scope,
        )

        controls = markdown_section(
            self.course_design_intake, "Normalized Design Controls"
        )
        normalized_controls = " ".join(controls.split())
        self.assertIn(
            "Reuse a value already present in context instead of asking again, "
            "including for pure-slide delivery",
            normalized_controls,
        )
        self.assertRegex(
            normalized_controls,
            r"(?i)pure-slide delivery has no explicit value, normalize "
            r"directly to level `1` without asking",
        )
        self.assertLess(
            normalized_controls.index("including for pure-slide delivery"),
            normalized_controls.index("pure-slide delivery has no explicit value"),
        )
        self.assertRegex(
            normalized_controls,
            r"(?i)for standard or combined delivery, apply fallback level "
            r"`3` only when the author explicitly skips or asks to continue "
            r"without answering",
        )

    def test_teaching_patterns_are_selected_not_redefined_during_generation(self):
        patterns = markdown_section(self.pedagogy, "Teaching Patterns")
        for pattern in (
            "Pattern A: Evidence Chain",
            "Pattern B: Misconception Repair",
            "Pattern C: Comparison-Driven Learning",
        ):
            self.assertIn(pattern, patterns)
        self.assertIn(
            "do not force every lesson into Evidence Chain",
            self.teaching_prompt,
        )
        self.assertNotRegex(
            self.teaching_prompt,
            r"(?m)^#{2,6} Pattern [ABC]:",
        )
        self.assertNotIn("## Teaching Patterns", self.prompt_contracts)
        self.assertNotIn("## Teaching Patterns", self.course_prompt)

    def test_markdownflow_authoring_owns_encoding(self):
        interaction = markdown_section(
            self.markdownflow_authoring, "Interaction Encoding"
        )
        variables = markdown_section(
            self.markdownflow_authoring, "Variable and Branch Encoding"
        )
        preservation = markdown_section(
            self.markdownflow_authoring, "Preservation Encoding"
        )

        self.assertIn("`?[]` control on its own line", interaction)
        self.assertIn("`|` for single-select", interaction)
        self.assertIn("`||` for multi-select", interaction)
        self.assertIn("literal substituted value `UNKNOWN`", variables)
        self.assertIn("wrap only the position- and formatting-sensitive span", preservation)
        self.assertIn(
            "Inline preservation remains mediated by the Teaching Agent",
            preservation,
        )
        required = markdown_section(
            self.markdownflow_authoring, "Required References"
        )
        conditional = markdown_section(
            self.markdownflow_authoring, "Conditional References"
        )
        self.assertNotIn("source-preservation.md", required)
        self.assertIn("source-preservation.md", conditional)
        self.assertNotIn("## Interaction Encoding", self.pedagogy)
        self.assertNotIn("## Interaction Encoding", self.teaching_prompt)

    def test_pedagogy_resolves_explicit_text_only_delivery(self):
        lesson_loop = markdown_section(self.pedagogy, "Lesson Loop")
        visual_text = markdown_section(
            self.pedagogy, "Visual-Text Coordination"
        )

        self.assertIn("explicit text-only constraint", lesson_loop)
        self.assertIn("Pure classroom slides instead begin", lesson_loop)
        self.assertIn("Explicit text-only constraint", visual_text)
        self.assertIn("Give complete teaching direction", visual_text)
        self.assertIn("selected personalization level", visual_text)
        self.assertIn(
            "keep the teaching and paragraph sequence fixed",
            visual_text,
        )
        self.assertIn(
            "ordinary explanation wording, elaboration, example detail, "
            "transition wording, and feedback wording",
            visual_text,
        )
        self.assertNotIn("`viewpoint_check`", self.pedagogy)

    def test_course_entry_is_a_single_order_derived_lead_in(self):
        required = markdown_section(self.pedagogy, "Required References")
        course_entry = markdown_section(self.pedagogy, "Course Entry")
        lesson_loop = markdown_section(self.pedagogy, "Lesson Loop")
        generation = markdown_section(self.teaching_prompt, "Generation")
        materialization = markdown_section(
            self.teaching_prompt, "Lesson Materialization"
        )
        validation = markdown_section(self.teaching_prompt, "Validation")

        self.assertIn("data-contracts.md#input-contract", required)
        self.assertIn("first lesson of the first chapter", course_entry)
        self.assertIn("approved course order", course_entry)
        self.assertIn("rather than from a lesson-id naming convention", course_entry)
        self.assertIn("single brief direct-teaching lead-in", course_entry)
        self.assertIn("Move immediately", course_entry)
        self.assertIn("relationship-building behavior", lesson_loop)
        self.assertIn("approved course order, not from its lesson id", generation)
        self.assertIn("course-entry behavior", materialization)
        self.assertIn("Course-entry status is derived", validation)

    def test_course_entry_identity_and_delivery_boundaries_are_explicit(self):
        course_entry = markdown_section(self.pedagogy, "Course Entry")
        validation = markdown_section(self.teaching_prompt, "Validation")

        self.assertIn("When `course_author_name` is non-empty", course_entry)
        self.assertIn("never invent a title, affiliation, experience", course_entry)
        self.assertIn("In every later lesson", course_entry)
        self.assertIn("do not repeat the course greeting", course_entry)
        self.assertIn("Pure classroom slides", course_entry)
        self.assertIn("add no Teaching Agent greeting or self-introduction", validation)

        self.assertIn("do not impose a word-count or sentence-count quota", course_entry)

    def test_teaching_prompt_owns_five_personalization_levels(self):
        lesson_loop = markdown_section(self.pedagogy, "Lesson Loop")
        visual_text = markdown_section(
            self.pedagogy, "Visual-Text Coordination"
        )
        generation = markdown_section(self.teaching_prompt, "Generation")
        levels = markdown_section(
            self.teaching_prompt, "Personalization Levels"
        )
        validation = markdown_section(self.teaching_prompt, "Validation")
        checklist = markdown_section(
            self.optimization_checklist, "Teaching Prompt Behavior"
        )

        for path in COURSE_CREATOR_REFERENCES.rglob("*.md"):
            self.assertNotIn(
                "instructional role",
                path.read_text(encoding="utf-8").lower(),
                f"use teaching purpose instead of the ambiguous role label: {path}",
            )
        self.assertIn("teaching purpose", visual_text)
        self.assertIn("classroom-ready deck", visual_text)
        self.assertIn("must-cover evidence and boundaries", generation)
        self.assertIn("`teaching_prompt_personalization_level`", generation)
        self.assertLess(
            generation.index("Select the teaching pattern"),
            generation.index("`teaching_prompt_personalization_level`"),
        )
        self.assertLess(
            generation.index("Build one internal lesson execution plan"),
            generation.index("`teaching_prompt_personalization_level`"),
        )
        self.assertLess(
            generation.index("`teaching_prompt_personalization_level`"),
            generation.index(
                "Materialize the plan as direct local instructions"
            ),
        )
        self.assertLess(
            generation.index("Materialize the plan as direct local instructions"),
            generation.index("`markdownflow-authoring.md`"),
        )
        self.assertIn(
            "Begin with the first teaching action for the selected delivery mode",
            generation,
        )
        self.assertIn(
            "the resulting sequence and adjacency carry the lesson structure",
            generation,
        )

        self.assertEqual(
            ["1", "2", "3", "4", "5"],
            markdown_table_first_column(levels, "Level"),
        )
        normalized_levels = " ".join(levels.split())
        for structural_fragment in (
            "internal lesson execution plan",
            "required presence, position, and teaching effect of titles, ordinary "
            "explanations, examples, transitions, interactions, images, feedback "
            "states, and the close",
            "teaching sequence",
            "exact slide count",
            "each slide's ordinal position and teaching function",
            "content groups",
            "visual hierarchy",
            "semantic layout",
            "Apply the level only while writing the local runtime instructions",
            "Every level materializes the same teaching actions, slide order and "
            "grouping, interactions, images, feedback states, and close",
            "The level itself and this authoring rationale remain in the in-memory "
            "handoff",
        ):
            self.assertIn(structural_fragment, normalized_levels)
        self.assertIn(
            "The level changes only content-expression specificity",
            normalized_levels,
        )
        self.assertIn(
            "The actual ordered runtime instructions at every level implement "
            "the same structural decisions",
            normalized_levels,
        )
        level_rows = {}
        for line in levels.splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [
                cell.strip().replace(r"\|", "|")
                for cell in split_markdown_table_row(line)
            ]
            if cells and cells[0].strip("`") in {"1", "2", "3", "4", "5"}:
                level_rows[cells[0].strip("`")] = " ".join(cells[1:])

        for level, row in level_rows.items():
            self.assertIn("Write", row, level)

        level_1 = " ".join(level_rows["1"].split())
        for fragment in (
            "exact or near-final title wording",
            "selected example details",
            "ordinary explanations",
            "transitions",
            "feedback wording",
        ):
            self.assertIn(fragment, level_1)

        level_5 = " ".join(level_rows["5"].split())
        for fragment in (
            "concrete message and outcome for every teaching action",
            "critical facts and boundaries",
            "each required example's material requirements and intended "
            "takeaway",
            "feedback completion conditions and effects",
            "Omit all other ordinary wording and example identity or detail",
        ):
            self.assertIn(fragment, level_5)
        self.assertIn("an empty outline", levels)

        common_constraints = normalized_levels
        for fragment in (
            "complete learner-facing interaction question",
            "`?[]`",
            "variable lifecycle",
            "deterministic output",
            "regulated wording",
            "fixed numeric",
            "selected image URLs",
            "caption",
            "ordering",
            "wording or layout the author explicitly requires",
        ):
            self.assertIn(fragment, common_constraints)
        self.assertRegex(
            common_constraints,
            r"(?i)factual or source fidelity.*selected teaching pattern and "
            r"loop, interaction policy",
        )
        self.assertIn(
            "The level adds no learner-context collection, interactions, "
            "variables, or branches",
            common_constraints,
        )
        self.assertIn(
            "Insert material selected for exact preservation directly at its "
            "resolved runtime position",
            common_constraints,
        )

        self.assertIn("normalized personalization level", validation)
        self.assertIn("`teaching_prompt_personalization_level`", checklist)
        self.assertIn("ordinary title and explanation wording", checklist)
        self.assertIn("overly specific", checklist)
        self.assertIn("overly abstract", checklist)
        self.assertIn("At levels `1` and `2`", checklist)
        self.assertIn("At levels `4` and `5`", checklist)
        self.assertIn(
            "At every level, recover the execution signature from the actual "
            "ordered runtime instructions",
            checklist,
        )
        self.assertIn(
            "Treat a level-driven difference in that signature as a defect",
            checklist,
        )
        self.assertIn(
            "compare the actual instruction sequences explicitly", checklist
        )
        self.assertIn(
            "record cross-level structural consistency as `not-assessed`",
            checklist,
        )
        self.assertIn("`not-assessed`", checklist)
        self.assertRegex(checklist, r"(?i)do not infer")

        for path in COURSE_CREATOR_REFERENCES.rglob("*.md"):
            if path.name == "teaching-prompt.md":
                continue
            self.assertNotIn(
                "\n## Personalization Levels\n",
                path.read_text(encoding="utf-8"),
                f"five-level behavior table belongs only in teaching-prompt.md: {path}",
            )

    def test_personalization_does_not_absorb_course_prompt_or_runtime_contracts(self):
        field = "teaching_prompt_personalization_level"
        self.assertNotIn(field, self.course_prompt)

        for owner_section in (
            markdown_section(self.pedagogy, "Interaction Design"),
            markdown_section(self.pedagogy, "Variable Strategy"),
            markdown_section(self.markdownflow, "Interactions"),
            markdown_section(self.markdownflow, "Variables"),
            markdown_section(self.markdownflow_authoring, "Interaction Encoding"),
            markdown_section(
                self.markdownflow_authoring, "Variable and Branch Encoding"
            ),
        ):
            self.assertNotIn(field, owner_section)
            self.assertNotIn("Personalization Levels", owner_section)

    def test_standard_teaching_uses_brief_text_visual_text_cadence(self):
        lesson_loop = " ".join(
            markdown_section(self.pedagogy, "Lesson Loop").split()
        )
        visual_text = " ".join(
            markdown_section(self.pedagogy, "Visual-Text Coordination").split()
        )
        materialization = " ".join(
            markdown_section(self.teaching_prompt, "Lesson Materialization").split()
        )
        validation = " ".join(
            markdown_section(self.teaching_prompt, "Validation").split()
        )
        interaction_encoding = " ".join(
            markdown_section(
                self.markdownflow_authoring, "Interaction Encoding"
            ).split()
        )
        authoring_validation = " ".join(
            markdown_section(self.markdownflow_authoring, "Validation").split()
        )
        checklist = " ".join(
            markdown_section(
                self.optimization_checklist, "Teaching Prompt Behavior"
            ).split()
        )

        self.assertIn("brief text lead-in", lesson_loop)
        self.assertIn("standard teaching branch of combined delivery", lesson_loop)
        self.assertIn("first learner-visible block", validation)
        self.assertIn("slide, or image as the opening", lesson_loop)
        self.assertIn("word-count or sentence-count quota", lesson_loop)

        self.assertIn(
            "brief text lead-in → substantive visual unit → concise but complete "
            "text explanation",
            visual_text,
        )
        self.assertIn(
            "Every lesson in this mode contains at least one substantive visual unit",
            visual_text,
        )
        self.assertIn(
            "A visual unit is one slide or one standalone image",
            visual_text,
        )
        self.assertIn("slide containing an image still counts as one", visual_text)
        self.assertIn("Do not place two visual units back to back", visual_text)
        self.assertIn(
            "defer several visuals' explanations to one later block",
            visual_text,
        )
        self.assertIn(
            "reject any visual unit whose sole purpose is to pad the lesson's "
            "length or pacing",
            visual_text,
        )
        self.assertIn("already present in an audited artifact", visual_text)
        self.assertIn(
            "defined framing, orientation, transition, atmosphere, or teaching "
            "purpose",
            visual_text,
        )
        self.assertIn(
            "does not fail this padding rule merely because it is non-substantive",
            visual_text,
        )
        self.assertIn(
            "context, relationship, reasoning, inference, or application",
            visual_text,
        )
        self.assertIn("rather than merely restating it", visual_text)
        self.assertIn(
            "final pair's explanation also performs the selected summary, "
            "decision checkpoint, or action close",
            visual_text,
        )
        self.assertIn(
            "question-only slide, place the unchanged `?[]` control immediately "
            "after it, then provide the immediate feedback or explanatory effect",
            visual_text,
        )
        self.assertIn("`?[Continue]`", visual_text)

        self.assertIn("one brief learner-visible text lead-in", materialization)
        self.assertIn("at least one substantive visual-and-explanation pair", materialization)
        self.assertIn("make the final explanation perform the close", materialization)
        self.assertIn("no consecutive visual units", validation)
        self.assertIn(
            "one concise but complete explanation after every visual and before "
            "the next",
            validation,
        )
        self.assertIn("final explanation that also performs the close", validation)
        self.assertIn("question-only visual", validation)
        self.assertIn("unchanged `?[]` control", validation)

        self.assertIn("question-only visual instruction", interaction_encoding)
        self.assertIn("without option labels", interaction_encoding)
        self.assertIn("unchanged `?[]` control", interaction_encoding)
        self.assertIn("`?[Continue]`", interaction_encoding)
        self.assertIn("do not invent a learner question", interaction_encoding)
        self.assertIn("only in the interaction control", interaction_encoding)
        self.assertIn(
            "do not duplicate those labels on the question-only visual",
            interaction_encoding,
        )
        self.assertIn(
            "After the learner responds, acknowledge the goal and explain",
            interaction_encoding,
        )
        self.assertIn(
            "What course-wide goal should later lessons use?",
            interaction_encoding,
        )
        self.assertNotIn("Course Prompt", interaction_encoding)
        self.assertIn("question-only visual instructions", authoring_validation)
        self.assertIn("feedback or explanatory effects", authoring_validation)

        for defect in (
            "visual opening",
            "consecutive visual units",
            "several visuals followed by one delayed explanation",
            "unpaired learner-visible text turn after the lead-in",
        ):
            self.assertIn(defect, checklist)
        self.assertIn(
            "flag any visual unit whose sole purpose is to pad the lesson's length "
            "or pacing",
            checklist,
        )
        self.assertIn("newly proposed or already present", checklist)
        self.assertIn(
            "defined framing, orientation, transition, atmosphere, or teaching "
            "purpose",
            checklist,
        )
        self.assertIn(
            "as padding merely because it is non-substantive",
            checklist,
        )
        self.assertIn(
            "Pure classroom slides do not use Teaching Agent narration or paired "
            "explanatory text",
            checklist,
        )
        self.assertIn("explicit text-only delivery uses no visual units", checklist)

        non_owners = {
            "Course Prompt": self.course_prompt,
            "Prompt Contracts": self.prompt_contracts,
            "Orchestration": self.orchestration_workflow,
            "MarkdownFlow runtime": self.markdownflow,
            "Image authoring": self.image_authoring,
        }
        for lesson_level_contract in (
            "brief text lead-in",
            "substantive visual unit",
            "question-only visual",
            "visual-and-explanation pair",
        ):
            for label, content in non_owners.items():
                self.assertNotIn(
                    lesson_level_contract,
                    content.casefold(),
                    f"{label} must not own the lesson cadence contract",
                )

    def test_author_images_keep_complete_explanation_except_in_pure_slides(self):
        visual_text = markdown_section(
            self.pedagogy, "Visual-Text Coordination"
        )
        image_row = next(
            line
            for line in visual_text.splitlines()
            if line.startswith("| Author-provided image file |")
        )
        pure_slides_row = next(
            line
            for line in visual_text.splitlines()
            if line.startswith("| Pure slides |")
        )

        self.assertIn("Under the standard visual-text scope", image_row)
        self.assertNotIn("Listen Mode", image_row)
        self.assertIn(
            "give it the required following explanation before any later visual",
            image_row,
        )
        self.assertRegex(image_row, r"(?i)pure-slide.*overrides")
        self.assertIn("explicit text-only constraint overrides image use", image_row)
        self.assertIn("Do not instruct the Teaching Agent to narrate", pure_slides_row)
        self.assertIn("omit long spoken paragraphs", pure_slides_row)

        deprecated_surface_rules = {
            "slide-style visual cover",
            "every core concept paired with a slide",
            "2–4 short bullets",
            "overrides the default slide pairing",
        }
        for fragment in deprecated_surface_rules:
            self.assertNotIn(fragment, self.pedagogy)

    def test_source_preservation_owns_selection_and_scope(self):
        decisions = markdown_section(
            self.source_preservation, "Preservation Decisions"
        )
        self.assertIn("Never preserve an entire lesson", decisions)
        self.assertIn("Preserve author-selected immutable content", decisions)
        self.assertNotIn("`!===`", decisions)
        self.assertNotIn("deterministic markers", decisions)
        self.assertNotIn(
            "## Preservation Decisions", self.optimization_workflow
        )
        self.assertNotIn(
            "## Preservation Decisions", self.optimization_checklist
        )

    def test_image_authoring_owns_asset_composition_and_validation(self):
        composition = markdown_section(
            self.image_authoring, "Image Composition"
        )
        validation = markdown_section(
            self.image_authoring, "Image Output Validation"
        )
        required = markdown_section(
            self.image_authoring, "Required References"
        )
        conditional = markdown_section(
            self.image_authoring, "Conditional References"
        )
        self.assertIn("Raw SVG, HTML drawings, Mermaid", composition)
        self.assertIn("res.ai-shifu.cn", self.image_authoring)
        self.assertIn("HTML-view", composition)
        self.assertIn("assets/image-manifest.json", validation)
        self.assertIn("`remote`", validation)
        self.assertIn("`alt`", validation)
        for required_field in (
            "selected form",
            "caption",
            "position",
            "layout constraints",
            "ordering",
        ):
            self.assertIn(required_field, validation)
        self.assertIn("Stop before generation", validation)
        self.assertIn("Regenerate only", validation)
        self.assertIn("Do not finalize or hand off", validation)
        self.assertNotIn("source-preservation.md", required)
        self.assertIn("source-preservation.md", conditional)

        owner_only_fragments = {
            "不得省略",
            "语义化 alt",
            "保持原始宽高比",
        }
        for path in self.skill_root.rglob("*.md"):
            if path.name == "image-authoring.md":
                continue
            content = path.read_text(encoding="utf-8")
            for fragment in owner_only_fragments:
                self.assertNotIn(
                    fragment,
                    content,
                    f"image authoring rule {fragment!r} belongs only in "
                    "image-authoring.md",
                )

    def test_course_prompt_keeps_six_sections_and_five_placeholders(self):
        template = markdown_section(self.course_prompt, "Fillable Template")
        headings = re.findall(
            r"^# (Role|Task|Teaching Techniques|Writing Style|Format|Slides)$",
            template,
            flags=re.MULTILINE,
        )
        self.assertEqual(
            [
                "Role",
                "Task",
                "Teaching Techniques",
                "Writing Style",
                "Format",
                "Slides",
            ],
            headings,
        )
        self.assertEqual(5, template.count("XXX"))

        sources = markdown_section(
            self.course_prompt, "Placeholder Sources and Context"
        )
        placeholders = markdown_table_first_column(sources, "Placeholder")
        self.assertEqual(5, len(placeholders))
        self.assertEqual(len(placeholders), len(set(placeholders)))
        self.assertIn("`course_author_name` from Course Design Intake", sources)
        self.assertIn(
            "omit the corresponding list item in the Fillable Template",
            sources,
        )
        self.assertNotIn("If unknown, ask the author", sources)
        self.assertIn("they do not add placeholders to the template", sources)

    def test_course_prompt_owns_delivery_mode_not_lesson_pedagogy(self):
        responsibilities = markdown_section(
            self.prompt_contracts, "Artifact Responsibilities"
        )
        purpose = markdown_section(self.course_prompt, "Purpose")
        template = markdown_section(self.course_prompt, "Fillable Template")
        required = markdown_section(
            self.course_prompt, "Required References"
        )

        self.assertIn(
            "follows each Teaching Prompt and does not own lesson pedagogy",
            responsibilities,
        )
        self.assertIn(
            "does not redefine shared Prompt semantics, lesson pedagogy, or "
            "MarkdownFlow runtime behavior",
            purpose,
        )
        self.assertIn("standard one-on-one", self.course_prompt.casefold())
        self.assertIn("pure classroom slides", self.course_prompt.casefold())
        self.assertNotIn(
            "build interest → lower the barrier → understand the structure",
            template,
        )
        self.assertIn("current user message", template)
        self.assertNotIn("the user message", template)
        self.assertNotIn("Teaching Prompt", template)
        self.assertNotRegex(
            self.course_prompt,
            r"(?m)^#{2,6} Pattern [ABC]:",
        )
        self.assertIn("prompt-contracts.md#prompt-semantics", required)
        self.assertIn("prompt-contracts.md#artifact-responsibilities", required)

    def test_course_prompt_layers_learner_context_within_author_boundaries(self):
        template = markdown_section(self.course_prompt, "Fillable Template")
        checks = markdown_section(self.course_prompt, "Materialization Checks")
        semantics = markdown_section(self.prompt_contracts, "Prompt Semantics")
        responsibilities = markdown_section(
            self.prompt_contracts, "Artifact Responsibilities"
        )
        generation = markdown_section(self.teaching_prompt, "Generation")
        checklist = markdown_section(self.optimization_checklist, "Course Prompt")

        for required_behavior in (
            "In every delivery mode, actively use relevant learner context",
            "only where the current user message leaves those details open",
            "objectives, facts and boundaries, teaching method, content sequence, "
            "pacing, required examples, interactions, exact material, slide count "
            "and order, and close unchanged",
            "empty, `UNKNOWN`, irrelevant, or unavailable",
            "without quoting, summarizing, or mentioning the learner background",
        ):
            self.assertIn(required_behavior, template)

        for adaptable_surface in (
            "ordinary examples",
            "terminology",
            "prerequisite scaffolding",
            "emphasis",
            "explanation depth",
            "language style",
            "non-deterministic feedback",
        ):
            self.assertIn(adaptable_surface, template)

        self.assertIn("`course_profile`, topic-scope", checks)
        self.assertIn("platform learner-background tags", checks)
        self.assertIn("intended audience and course constraints are hard boundaries", semantics)
        self.assertIn("Platform-supplied learner context is additive", semantics)
        self.assertIn("platform supplies runtime learner context separately", responsibilities)
        self.assertIn("bounded cross-lesson personalization", generation)
        self.assertIn("Pure classroom slides", checklist)
        self.assertIn("neutral course-appropriate defaults", checklist)

        for leaked_runtime_name in (
            "sys_user_background",
            "sys_user_nickname",
            "{{learner_background}}",
            "<learner_background>",
        ):
            self.assertNotIn(leaked_runtime_name, template)
            self.assertNotIn(leaked_runtime_name, self.data_contracts)

        self.assertNotIn("runtime learner background", self.data_contracts.casefold())

        evals_data = json.loads(
            (self.skill_root / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        evals_by_id = {case["id"]: case for case in evals_data["evals"]}
        self.assertIn(37, evals_by_id)
        self.assertIn(38, evals_by_id)
        eval_37 = " ".join(evals_by_id[37]["expectations"])
        eval_38 = " ".join(evals_by_id[38]["expectations"])
        self.assertIn("experienced emergency physicians", eval_37)
        self.assertIn("workplace training organizers", eval_37)
        self.assertIn("every delivery mode", eval_37)
        self.assertIn("does not change or retarget", eval_38)
        self.assertIn("internal learner-background variable", eval_38)

        for source in (template, checks, semantics, responsibilities, eval_37, eval_38):
            self.assertNotRegex(source.casefold(), r"learner[- ]profile")

    def test_course_prompt_owns_general_slide_rules_without_cover_handling(self):
        responsibilities = markdown_section(
            self.prompt_contracts, "Artifact Responsibilities"
        )
        purpose = markdown_section(self.course_prompt, "Purpose")
        template = markdown_section(self.course_prompt, "Fillable Template")
        checks = markdown_section(self.course_prompt, "Materialization Checks")
        materialization = markdown_section(
            self.teaching_prompt, "Lesson Materialization"
        )
        validation = markdown_section(self.teaching_prompt, "Validation")

        self.assertIn(
            "general presentation requirements applied uniformly to every slide",
            responsibilities,
        )
        self.assertIn(
            "special handling for an individual slide position or purpose",
            responsibilities,
        )
        self.assertIn("single runtime owner", purpose)
        self.assertIn("uniformly to every slide", purpose)
        self.assertNotIn("cover", template.casefold())
        self.assertNotIn("slide 1", template.casefold())
        self.assertIn("does not special-case a cover", checks)

        self.assertIn("slide 1 a clear cover-page visual treatment", materialization)
        self.assertIn("with lesson title and author information", materialization)
        self.assertIn("clear cover-page visual treatment", validation)
        self.assertIn("with lesson title and author information", validation)
        self.assertNotIn("rather than adding a cover", self.pedagogy)
        self.assertNotIn("rather than serve as a cover", self.pedagogy)
        self.assertNotIn("cover-only", self.optimization_checklist)
        for removed_page_rule in (
            "decorative page",
            "decorative pages",
            "objective-only page",
            "objective-only pages",
        ):
            self.assertNotIn(removed_page_rule, self.pedagogy)
            self.assertNotIn(removed_page_rule, self.optimization_checklist)
        self.assertIn(
            "without restating the general presentation requirements",
            validation,
        )
        self.assertIn(
            "without special handling for a cover",
            self.optimization_checklist,
        )

        evals_data = json.loads(
            (self.skill_root / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        evals_by_id = {case["id"]: case for case in evals_data["evals"]}
        eval_26_prompt = evals_by_id[26]["prompt"]
        self.assertNotRegex(
            eval_26_prompt,
            r"(?:不要增加|不得增加|禁止增加)[^。\n]*(?:装饰页|目标空页)",
        )
        self.assertIn("不要增加封面或其他填充页", eval_26_prompt)
        self.assertIn(
            "does not mention, create, or style a cover page or slide 1 specially",
            " ".join(evals_by_id[12]["expectations"]),
        )
        for eval_id in (19, 20):
            expectations = " ".join(evals_by_id[eval_id]["expectations"])
            self.assertIn(
                "cover-page visual treatment",
                expectations,
            )
            self.assertIn("with lesson title and author information", expectations)

    def test_optimization_audits_existing_artifacts_without_absorbing_creation(self):
        self.assertIn("## Entry Conditions", self.optimization_workflow)
        self.assertIn("## Optimization Method", self.optimization_workflow)
        self.assertIn("## Issue Taxonomy", self.optimization_workflow)
        self.assertIn(
            "does not perform first-time course authoring",
            self.optimization_workflow,
        )
        self.assertNotIn(
            "## Preservation Decisions", self.optimization_workflow
        )
        self.assertNotIn(
            "Course Description and Review Outputs", self.optimization_workflow
        )
        self.assertNotIn(
            "## Language Audit", self.optimization_checklist
        )

    def test_content_only_optimization_does_not_claim_source_fidelity(self):
        workflow_required = markdown_section(
            self.optimization_workflow, "Required References"
        )
        workflow_conditional = markdown_section(
            self.optimization_workflow, "Conditional References"
        )
        checklist_required = markdown_section(
            self.optimization_checklist, "Required References"
        )
        checklist_conditional = markdown_section(
            self.optimization_checklist, "Conditional References"
        )
        coverage = markdown_section(
            self.optimization_checklist, "Coverage and Fidelity"
        )

        self.assertNotIn("source-preservation.md", workflow_required)
        self.assertNotIn("source-preservation.md", checklist_required)
        self.assertIn("source-preservation.md", workflow_conditional)
        self.assertIn("source-preservation.md", checklist_conditional)
        self.assertIn("does not claim coverage of or fidelity", coverage)
        self.assertNotIn("`allow_headings`", self.optimization_checklist)

    def test_optional_course_author_uses_standard_intake_fallback(self):
        input_contract = markdown_section(self.data_contracts, "Input Contract")
        intake_scope = markdown_section(self.course_design_intake, "Intake Scope")
        normalized_controls = markdown_section(
            self.course_design_intake, "Normalized Design Controls"
        )
        conditional = markdown_section(
            self.course_prompt, "Conditional References"
        )
        checks = markdown_section(self.course_prompt, "Materialization Checks")

        self.assertIn("`course_author_name` (string)", input_contract)
        self.assertIn("blank or unanswered value", input_contract)
        self.assertRegex(intake_scope, r"(?m)^6\. When a Course Prompt is in scope")
        self.assertIn("leaving it blank does not affect course creation", intake_scope)
        self.assertIn("**Course author name**", normalized_controls)
        self.assertIn(
            "supplied value is blank, or the question is skipped or unanswered, "
            "use an empty string",
            normalized_controls,
        )
        self.assertIn("`course-design-intake.md`", conditional)
        self.assertIn(
            "optional named Role identity item is either absent or contains a "
            "non-empty name",
            checks,
        )
        self.assertIn(
            "completed artifact contains no unresolved `XXX` placeholder",
            checks,
        )

        evals_data = json.loads(
            (self.skill_root / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        author_name_eval = next(
            case for case in evals_data["evals"] if case["id"] == 27
        )
        self.assertEqual(3, len(author_name_eval["expectations"]))
        self.assertIn("normal Course Design Intake", author_name_eval["expected_output"])

    def test_phase_workflows_directly_load_their_fallback_schemas(self):
        expected = {
            "segmentation-fallback-fields": (
                COURSE_CREATOR_REFERENCES / "segmentation-workflow.md"
            ),
            "orchestration-fallback-fields": (
                COURSE_CREATOR_REFERENCES / "orchestration-workflow.md"
            ),
            "generation-fallback-fields": (
                COURSE_CREATOR_REFERENCES / "teaching-prompt.md"
            ),
            "optimization-fallback-fields": (
                COURSE_CREATOR_REFERENCES / "optimization-workflow.md"
            ),
        }

        for anchor, path in expected.items():
            with self.subTest(path=path.name):
                required = markdown_section(
                    path.read_text(encoding="utf-8"), "Required References"
                )
                self.assertIn(f"data-contracts.md#{anchor}", required)

    def test_platform_workflows_have_disjoint_mutation_responsibilities(self):
        self.assertIn("import --new", self.deployment_workflow)
        self.assertIn("build", self.deployment_workflow)
        self.assertIn("publish", self.deployment_workflow)
        self.assertNotIn("Version Sync Workflow", self.deployment_workflow)
        self.assertNotIn("Conflict Convergence", self.deployment_workflow)
        self.assertNotIn("## Operations", self.deployment_workflow)

        self.assertIn("Pull Before Editing", self.course_sync)
        self.assertIn("Conflict Convergence", self.course_sync)
        self.assertNotIn("import --new", self.course_sync)

        self.assertIn("## Operations", self.course_management)
        self.assertIn("archive", self.course_management)
        self.assertIn("reorder", self.course_management)
        self.assertIn(
            "pass that same directory through `--course-dir`",
            self.course_management,
        )
        self.assertIn("three consecutive exit-`2`", self.course_sync)
        self.assertIn("explicit user confirmation", self.course_sync)
        self.assertIn(
            "Immediately after each successful `add-chapter`, `add-lesson`, "
            "`rename-lesson`, or `delete-lesson`",
            self.course_sync,
        )
        self.assertIn(
            "run `pull <shifu_bid> --course-dir <dir>`",
            self.course_sync,
        )
        self.assertIn(
            "never continue from the pre-mutation sync baseline",
            self.course_sync,
        )
        self.assertNotIn("import --new", self.course_management)

    def test_direct_query_consumers_declare_query_command_dependency(self):
        analytics = (
            COURSE_CREATOR_REFERENCES / "analytics" / "workflow.md"
        ).read_text(encoding="utf-8")
        analytics_required = markdown_section(analytics, "Required References")
        deployment_required = markdown_section(
            self.deployment_workflow, "Required References"
        )

        self.assertIn(
            "../cli/cli-reference.md#query-commands", analytics_required
        )
        self.assertIn("cli/cli-reference.md#query-commands", deployment_required)

    def test_orchestration_rebuilds_derived_outputs_after_phase_reruns(self):
        workflow = markdown_section(self.orchestration_workflow, "Workflow")
        reruns = markdown_section(self.orchestration_workflow, "Rerun Rules")

        self.assertIn("Rerun the phase that owns each failed output", workflow)
        self.assertIn("rebuild both `course_index`", workflow)
        self.assertIn("rerun Segmentation", reruns)
        self.assertIn("never hand off a stale `course_index`", reruns)

    def test_find_title_contract_matches_cli_keyword_validation(self):
        query_commands = markdown_section(self.cli_reference, "Query Commands")

        self.assertIn("at least two non-whitespace characters", query_commands)

    def test_new_deployment_keeps_authoring_and_selected_attributes_explicit(self):
        conditional = markdown_section(
            self.deployment_workflow, "Conditional References"
        )
        deploy = markdown_section(
            self.deployment_workflow, "Deploy and Publish"
        )

        self.assertIn("standalone course directory lacks a Course Prompt", conditional)
        self.assertIn("`course-prompt.md`", conditional)
        self.assertIn("`course-description.md`", conditional)
        self.assertIn("`course-management.md#operations`", conditional)
        self.assertLess(
            deploy.index("Before first publication"),
            deploy.index("Run `publish <shifu_bid>`"),
        )
        self.assertIn("enabling Listen Mode", deploy)

    def test_version_aware_avatar_management_keeps_directory_state_current(self):
        deploy = markdown_section(
            self.deployment_workflow, "Deploy and Publish"
        )
        directory_layout = markdown_section(
            self.course_directory_spec, "Directory Layout"
        )

        for command in ("`update-meta`", "`set-tts`", "`set-avatar`"):
            self.assertIn(command, self.course_management)
        self.assertIn(
            "every version-aware course-level management write",
            self.course_management,
        )
        self.assertIn("must be the pulled directory", self.course_management)
        self.assertIn("`pull <shifu_bid> --course-dir <dir>`", deploy)
        self.assertIn(
            "`set-avatar <shifu_bid> --file <course_author_avatar_source> "
            "--course-dir <dir>`",
            deploy,
        )
        self.assertIn("set-avatar --course-dir", directory_layout)

    def test_optimization_report_names_each_prompt_type(self):
        report = markdown_section(self.report_template, "Optimization Report")
        self.assertIn("- Target Teaching Prompt(s):", report)
        self.assertIn("- Target Course Prompt:", report)
        self.assertIn("- Target course description:", report)
        self.assertIn(
            "- Artifact envelope/schema check: `pass|fail|not-assessed`",
            report,
        )
        self.assertNotIn("- Target Prompt(s):", report)

    def test_orchestration_handoffs_do_not_expand_directory_contract(self):
        self.assertIn("structured phase-handoff data", self.orchestration_workflow)
        self.assertIn("closed artifact set owned by", self.orchestration_workflow)
        self.assertNotIn("authoring-manifest.json", self.orchestration_workflow)
        self.assertIn("authoring-manifest.json", self.course_directory_spec)
        self.assertIn(
            "complete set of recognized and managed", self.course_directory_spec
        )
        self.assertIn("must not synthesize CLI-managed outputs", self.course_directory_spec)
        self.assertIn("should write only that", self.course_directory_spec)
        self.assertIn("title heading", self.course_directory_spec)
        self.assertIn("do not duplicate the author", self.course_directory_spec)

    def test_import_omission_semantics_distinguish_new_and_existing_courses(self):
        self.assertIn(
            "Existing-course import leaves omitted", self.cli_reference
        )
        self.assertIn(
            "new-course import uses platform defaults", self.cli_reference
        )
        self.assertNotIn(
            "Both forms send content fields while leaving omitted",
            self.cli_reference,
        )

    def test_removed_authoring_controls_do_not_reappear(self):
        scan_roots = [
            self.skill_root,
            REPO_ROOT / "scripts",
            REPO_ROOT / "templates",
        ]
        removed_terms = {
            "require_" + "branching_feedback",
            "interaction_" + "density",
            "interaction " + "density",
            "interaction-" + "density",
            "互动" + "密度",
            "交互" + "密度",
            "source_material_" + "dominant_language",
            "default_fallback_" + "language",
            "target_language_" + "parameter",
            "session_" + "language_preference",
            "explicit_output_language_" + "request",
            "prior_context_language_" + "directive",
            "allow_any_" + "language",
            "bcp" + "47",
            "bcp-" + "47",
            "pre-deploy-language-" + "audit",
            "## User-Visible " + "Language",
            "## Output " + "Language",
        }
        removed_input_identifier = "target_" + "language"
        removed_input_pattern = re.compile(
            rf"(?<![A-Za-z0-9_]){re.escape(removed_input_identifier)}"
            r"(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        matches = []

        for root in scan_roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {
                    ".json",
                    ".md",
                    ".py",
                    ".yaml",
                    ".yml",
                }:
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
                for term in removed_terms:
                    if term.casefold() in content.casefold():
                        matches.append(
                            (str(path.relative_to(REPO_ROOT)), term)
                        )
                if removed_input_pattern.search(content):
                    matches.append(
                        (
                            str(path.relative_to(REPO_ROOT)),
                            removed_input_identifier,
                        )
                    )

        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
