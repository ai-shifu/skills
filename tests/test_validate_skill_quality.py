from __future__ import annotations

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


def markdown_table_first_column(section: str, header: str) -> list[str]:
    """Read canonical values from a Markdown table identified by its header."""
    lines = section.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [
            cell.strip().replace(r"\|", "|")
            for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))
        ]
        if not cells or cells[0].strip("`").casefold() != header.casefold():
            continue

        values: list[str] = []
        for row in lines[index + 2 :]:
            if not row.lstrip().startswith("|"):
                break
            first_cell = re.split(
                r"(?<!\\)\|", row.strip().strip("|"), maxsplit=1
            )[0].strip()
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


class AnchorValidationTests(unittest.TestCase):
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


class PedagogyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_doc = (
            COURSE_CREATOR_REFERENCES.parent / "SKILL.md"
        ).read_text(encoding="utf-8")
        cls.pedagogy_path = COURSE_CREATOR_REFERENCES / "pedagogy.md"
        cls.pedagogy = cls.pedagogy_path.read_text(encoding="utf-8")
        cls.course_prompt_path = COURSE_CREATOR_REFERENCES / "course-prompt.md"
        cls.course_prompt = cls.course_prompt_path.read_text(encoding="utf-8")
        cls.generation_workflow_path = (
            COURSE_CREATOR_REFERENCES / "generation-workflow.md"
        )
        cls.generation_workflow = cls.generation_workflow_path.read_text(
            encoding="utf-8"
        )
        cls.optimization_workflow_path = (
            COURSE_CREATOR_REFERENCES / "optimization-workflow.md"
        )
        cls.optimization_workflow = cls.optimization_workflow_path.read_text(
            encoding="utf-8"
        )
        cls.segmentation_workflow_path = (
            COURSE_CREATOR_REFERENCES / "segmentation-orchestration.md"
        )
        cls.segmentation_workflow = cls.segmentation_workflow_path.read_text(
            encoding="utf-8"
        )
        cls.markdownflow_path = COURSE_CREATOR_REFERENCES / "markdownflow.md"
        cls.markdownflow = cls.markdownflow_path.read_text(encoding="utf-8")
        cls.prompt_contracts_path = (
            COURSE_CREATOR_REFERENCES / "prompt-contracts.md"
        )
        cls.prompt_contracts = cls.prompt_contracts_path.read_text(
            encoding="utf-8"
        )
        cls.review_checklist = (
            COURSE_CREATOR_REFERENCES / "review-checklist.md"
        ).read_text(encoding="utf-8")
        cls.report_template = (
            COURSE_CREATOR_REFERENCES / "report-template.md"
        ).read_text(encoding="utf-8")
        cls.pipeline_example = (
            COURSE_CREATOR_REFERENCES.parent / "examples" / "pipeline-full.md"
        ).read_text(encoding="utf-8")
        cls.optimization_example = (
            COURSE_CREATOR_REFERENCES.parent
            / "examples"
            / "optimization-only.md"
        ).read_text(encoding="utf-8")
        cls.data_contracts_path = COURSE_CREATOR_REFERENCES / "data-contracts.md"
        cls.data_contracts = cls.data_contracts_path.read_text(encoding="utf-8")
        cls.deployment_workflow = (
            COURSE_CREATOR_REFERENCES / "deployment-workflow.md"
        ).read_text(encoding="utf-8")
        cls.reference_anchors_by_path = {
            path: validate_skill_quality.github_heading_slugs(path)
            for path in sorted(COURSE_CREATOR_REFERENCES.rglob("*.md"))
            if all(
                not part.startswith(".")
                for part in path.relative_to(COURSE_CREATOR_REFERENCES).parts
            )
        }

    def test_reference_anchors_match_authority_boundaries(self):
        expected_anchors_by_path = {
            self.pedagogy_path: {
                "pedagogy",
                "interaction-policy-precedence",
                "lesson-loop",
                "teaching-patterns",
                "pattern-a-evidence-chain",
                "pattern-b-misconception-repair",
                "pattern-c-comparison-driven-learning",
                "cognitive-techniques",
                "interaction-design",
                "variable-strategy",
                "visual-text-coordination",
            },
            self.segmentation_workflow_path: {
                "segmentation-methodology",
                "objective",
                "core-rules",
                "failure-handling",
            },
            self.data_contracts_path: {
                "segment-types",
                "transfer-signals",
            },
            self.markdownflow_path: {
                "markdownflow-spec",
                "processing-model",
                "preprocessing",
                "variables",
                "interactions",
                "branching-on-user-input",
                "deterministic-blocks",
                "images",
                "preservation",
            },
            self.generation_workflow_path: {
                "markdownflow-authoring",
                "interaction-encoding",
                "variable-and-branch-encoding",
                "preservation-encoding",
                "image-authoring",
                "working-with-author-provided-images",
            },
            self.optimization_workflow_path: {
                "optimization-methodology",
                "principles",
                "content-fidelity-and-controlled-rewriting",
                "preservation-decisions",
                "issue-taxonomy",
                "execution-sequence",
            },
        }

        for path, expected_anchors in expected_anchors_by_path.items():
            actual_anchors = self.reference_anchors_by_path[path]
            self.assertTrue(
                expected_anchors.issubset(actual_anchors),
                f"missing authority anchors in {path}: "
                f"{sorted(expected_anchors - actual_anchors)}",
            )

        self.assertEqual(
            expected_anchors_by_path[self.markdownflow_path],
            self.reference_anchors_by_path[self.markdownflow_path],
            "MarkdownFlow may contain only its runtime-specification headings",
        )

        exclusive_anchors_by_path = {
            self.pedagogy_path: {
                "pedagogy",
                "interaction-policy-precedence",
                "teaching-patterns",
                "pattern-a-evidence-chain",
                "pattern-b-misconception-repair",
                "pattern-c-comparison-driven-learning",
                "cognitive-techniques",
                "interaction-design",
                "variable-strategy",
            },
            self.segmentation_workflow_path: {"segmentation-methodology"},
            self.data_contracts_path: {"segment-types", "transfer-signals"},
            self.markdownflow_path: {
                "markdownflow-spec",
                "processing-model",
                "preprocessing",
                "variables",
                "interactions",
                "branching-on-user-input",
                "deterministic-blocks",
                "images",
                "preservation",
            },
            self.generation_workflow_path: {
                "markdownflow-authoring",
                "interaction-encoding",
                "variable-and-branch-encoding",
                "preservation-encoding",
                "image-authoring",
            },
            self.optimization_workflow_path: {
                "optimization-methodology",
                "content-fidelity-and-controlled-rewriting",
                "preservation-decisions",
                "issue-taxonomy",
                "execution-sequence",
            },
        }

        for owner_path, exclusive_anchors in exclusive_anchors_by_path.items():
            for path, actual_anchors in self.reference_anchors_by_path.items():
                if path == owner_path:
                    continue
                duplicated_anchors = exclusive_anchors.intersection(actual_anchors)
                self.assertFalse(
                    duplicated_anchors,
                    f"authority anchors owned by {owner_path} also appear in "
                    f"{path}: {sorted(duplicated_anchors)}",
                )

    def test_prompt_semantics_are_centralized(self):
        semantics_section = markdown_section(
            self.prompt_contracts, "Prompt Semantics"
        )
        semantics = " ".join(semantics_section.split())
        review_semantics = markdown_section(
            self.review_checklist, "Prompt Semantics"
        )

        self.assertIn("Prompts, not Scripts", semantics)
        self.assertIn("runtime LLM", semantics)
        self.assertIn("tell the LLM how to teach the learner", semantics)
        self.assertIn(
            "Within Prompt instructions, every occurrence of `you`, `your`, "
            "`yours`, or `yourself`, "
            "in any capitalization, refers only to the runtime LLM",
            semantics,
        )
        self.assertIn('"the learner" or "the student"', semantics)
        self.assertIn(
            "Learner-visible text inside a MarkdownFlow `?[]` interaction or "
            "[deterministic block](markdownflow.md#deterministic-blocks) is "
            "the exception",
            semantics,
        )
        self.assertIn(
            "Outside `?[]` and deterministic blocks", semantics
        )
        self.assertNotIn("Within Course Prompt content", semantics)
        for block in semantics_section.strip().split("\n\n"):
            block = block.strip()
            if not block:
                continue
            lines = block.splitlines()
            if lines[0].startswith("- "):
                self.assertTrue(all(line.startswith("- ") for line in lines))
            else:
                self.assertEqual(1, len(lines))
        self.assertNotIn("## Script " + "Style", self.pedagogy)
        self.assertIn(
            "prompt-semantics",
            validate_skill_quality.github_heading_slugs(
                self.prompt_contracts_path
            ),
        )
        self.assertIn(
            "(prompt-contracts.md#prompt-semantics)", review_semantics
        )

    def test_deprecated_script_style_phrasing_stays_out_of_other_docs(self):
        deprecated_fragments = {
            "## script style",
            "script that guides teaching",
            "model-guiding language",
            "instructional/directive language only",
            "final learner manuscript",
            'address the learner only as "you"',
        }
        matches = []

        for path in COURSE_CREATOR_REFERENCES.parent.rglob("*.md"):
            if path == self.prompt_contracts_path:
                continue
            content = path.read_text(encoding="utf-8").casefold()
            for fragment in deprecated_fragments:
                if fragment in content:
                    matches.append(
                        f"{path.relative_to(REPO_ROOT)}: {fragment}"
                    )

        self.assertEqual([], matches)

    def test_markdownflow_contains_runtime_mechanics_not_authoring_policy(self):
        processing = markdown_section(self.markdownflow, "Processing Model")
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

        self.assertIn("`---` separates adjacent content blocks", processing)
        self.assertIn("pauses progression", processing)
        self.assertIn("current document context", processing)
        self.assertIn("fenced code blocks", preprocessing)
        self.assertIn("HTML comments", preprocessing)
        self.assertIn("`UNKNOWN`", variables)
        self.assertIn("`%{{name}}` is an assignment prefix", variables)
        interaction_forms = markdown_table_first_column(
            interactions, "Form"
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
        self.assertIn("no parser-level conditionals", branching)
        self.assertIn("without an LLM call", deterministic)
        self.assertIn("no image-specific control-flow primitive", images)
        self.assertIn("no dedicated parser semantics", images)
        self.assertIn("Content outside these mechanisms remains generative", preservation)

    def test_reviewed_author_side_course_prompt_terms_stay_explicit(self):
        responsibilities = markdown_section(
            self.prompt_contracts, "Artifact Responsibilities"
        )
        materialization = markdown_section(
            self.course_prompt, "Materialization Checks"
        )
        review = markdown_section(self.review_checklist, "Course Prompt")

        self.assertIn("follows each Teaching Prompt", responsibilities)
        self.assertIn("does not own lesson pedagogy", responsibilities)
        self.assertIn(
            "contains no MarkdownFlow `?[]` interaction controls",
            responsibilities,
        )
        self.assertIn(
            "Every non-placeholder template instruction", materialization
        )
        self.assertIn("current Teaching Prompt", review)
        self.assertIn("without introducing competing lesson pedagogy", review)
        self.assertNotIn("current user message", review)
        self.assertIn("multiple script versions", self.optimization_workflow)
        self.assertIn(
            "source-to-Prompt coverage matrix", self.optimization_workflow
        )
        self.assertIn(
            "prompt-contracts.md#artifact-responsibilities",
            self.optimization_workflow,
        )

    def test_preservation_and_language_gates_run_before_content_shipping(self):
        self.assertIn(
            "[Pre-Deploy Language Audit]"
            "(data-contracts.md#pre-deploy-language-audit)",
            self.deployment_workflow,
        )
        self.assertIn(
            "During Segmentation, apply "
            "`optimization-workflow.md#preservation-decisions`",
            self.segmentation_workflow,
        )
        self.assertIn("before any Generation step", self.segmentation_workflow)

        route_order_checks = {
            "| Create a full course,": "references/segmentation-orchestration.md",
            "| Plan course structure": "references/segmentation-orchestration.md",
            "| Segment supplied material only": (
                "references/segmentation-orchestration.md"
            ),
            "| Generate Teaching Prompts": "references/generation-workflow.md",
        }
        for row_prefix, downstream_path in route_order_checks.items():
            row = next(
                line
                for line in self.skill_doc.splitlines()
                if line.startswith(row_prefix)
            )
            self.assertLess(
                row.index("references/optimization-workflow.md#preservation-decisions"),
                row.index(downstream_path),
                f"preservation decisions must load before {downstream_path}",
            )

    def test_optimization_report_names_each_prompt_type(self):
        report = markdown_section(self.report_template, "Optimization Report")

        self.assertIn("- Target Teaching Prompt(s):", report)
        self.assertIn("- Target Course Prompt:", report)
        self.assertNotIn("- Target Prompt(s):", report)

    def test_reviewed_prompt_prose_has_no_soft_line_wraps(self):
        slide_override = markdown_section(
            self.generation_workflow, "Slide-Only Generation Override"
        )
        narration_rule = (
            "- Do not instruct the runtime LLM to narrate or verbally explain "
            "the slides. Omit long spoken paragraphs and instructions such as "
            '"explain to the learner", "walk through", "向学习者说明", "讲解", '
            '"用文字解释", or "讲清".'
        )

        self.assertIn(narration_rule, slide_override.splitlines())

    def test_transfer_signal_keys_match_data_contract_and_validator(self):
        transfer_section = markdown_section(
            self.data_contracts, "Transfer Signals"
        )
        data_contract_keys = markdown_table_first_column(
            transfer_section, "Key"
        )

        validator_keys = validate_skill_quality.TRANSFER_SIGNAL_KEYS
        self.assertEqual(len(data_contract_keys), len(set(data_contract_keys)))
        self.assertEqual(set(data_contract_keys), validator_keys)
        self.assertIn(
            "(data-contracts.md#transfer-signals)",
            self.segmentation_workflow,
        )

    def test_interaction_matrix_has_only_canonical_modes_and_purposes(self):
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

    def test_authority_links_cover_prompt_and_delivery_boundaries(self):
        authority = markdown_section(self.prompt_contracts, "Authority Index")
        interaction = markdown_section(self.pedagogy, "Interaction Design")
        variables = markdown_section(self.pedagogy, "Variable Strategy")
        visuals = markdown_section(self.pedagogy, "Visual-Text Coordination")
        interaction_encoding = markdown_section(
            self.generation_workflow, "Interaction Encoding"
        )
        image_authoring = markdown_section(
            self.generation_workflow, "Image Authoring"
        )
        preservation_encoding = markdown_section(
            self.generation_workflow, "Preservation Encoding"
        )

        for link in (
            "(pedagogy.md)",
            "(markdownflow.md)",
            "(course-prompt.md)",
            "(data-contracts.md)",
        ):
            self.assertIn(link, authority)
        self.assertIn("(markdownflow.md#interactions)", interaction)
        self.assertIn("(markdownflow.md#branching-on-user-input)", interaction)
        self.assertIn("(markdownflow.md#variables)", variables)
        self.assertIn("(data-contracts.md#variable-table)", variables)
        self.assertIn(
            "(generation-workflow.md#markdownflow-authoring)", authority
        )
        self.assertIn("(generation-workflow.md#generation)", authority)
        self.assertIn(
            "(generation-workflow.md#image-authoring)", authority
        )
        self.assertIn(
            "(optimization-workflow.md#optimization)", authority
        )
        self.assertIn(
            "(optimization-workflow.md#preservation-decisions)", authority
        )
        self.assertIn(
            "(generation-workflow.md#image-authoring)", visuals
        )
        self.assertIn("pedagogy.md#interaction-design", interaction_encoding)
        self.assertIn("pedagogy.md#variable-strategy", interaction_encoding)
        self.assertIn(
            "optimization-workflow.md#preservation-decisions",
            preservation_encoding,
        )
        self.assertIn(
            "markdownflow.md#deterministic-blocks", preservation_encoding
        )
        self.assertIn("markdownflow.md#images", image_authoring)
        self.assertIn(
            "(generation-workflow.md#slide-only-generation-override)",
            visuals,
        )

    def test_course_prompt_template_uses_runtime_user_message_context(self):
        responsibilities = markdown_section(
            self.prompt_contracts, "Artifact Responsibilities"
        )
        purpose = markdown_section(self.course_prompt, "Purpose")
        template = markdown_section(self.course_prompt, "Fillable Template")

        self.assertIn(
            "follows each Teaching Prompt and does not own lesson pedagogy",
            responsibilities,
        )
        self.assertIn(
            "does not redefine shared Prompt semantics, lesson pedagogy, or "
            "MarkdownFlow runtime behavior",
            purpose,
        )
        self.assertIn(
            "Course Prompt's teaching contribution to the presentation layer",
            template,
        )
        self.assertNotIn(
            "build interest → lower the barrier → understand the structure",
            template,
        )
        self.assertIn(
            "proactively guide the learner to the next step at the end",
            template,
        )
        self.assertIn("Teach one-on-one", template)
        self.assertIn(
            "address the learner directly in the second person", template
        )
        self.assertNotIn('address the learner only as "you"', template)
        self.assertIn("Do not greet the learner", template)
        self.assertNotIn("You may use analogies", template)
        self.assertNotIn("Teaching Prompt", template)
        self.assertIn("current user message", template)
        self.assertNotIn("the user message", template)
        self.assertIn(
            "Follow the current user message's delivery mode and "
            "slide-text relationship",
            template,
        )
        self.assertIn(
            "When the current user message requests text alongside a slide",
            template,
        )
        self.assertIn("follow it with a complete text explanation", template)
        for example in (self.pipeline_example, self.optimization_example):
            artifact = markdown_section(example, "Course Prompt Artifact")
            self.assertNotIn("Teaching Prompt", artifact)
            self.assertIn("current user message", artifact)
            self.assertNotIn("the user message", artifact)
        self.assertIn(
            "do not rely on the Course Prompt to supply, repair, or override",
            self.generation_workflow,
        )
        self.assertIn(
            "follows each Teaching Prompt and does not own lesson pedagogy",
            responsibilities,
        )

    def test_reference_files_keep_single_responsibilities(self):
        authority = markdown_section(self.prompt_contracts, "Authority Index")

        retired_anchors = {
            "scope-and-authority-boundaries",
            "pipeline-methodologies",
            "prompt-placement-rules",
            "input-marker-rules",
            "input-marker-examples",
            "no-program-syntax-around-var",
            "31-fixed-image-standard-markdown--deterministic",
            "32-html-view-image-instruction-style-not-fixed-output",
            "33-which-form-to-use",
        }
        moved_anchor_owners = {
            "segmentation-methodology": self.segmentation_workflow_path,
            "segment-types": self.data_contracts_path,
            "transfer-signals": self.data_contracts_path,
            "optimization-methodology": self.optimization_workflow_path,
        }

        for path, actual_anchors in self.reference_anchors_by_path.items():
            self.assertTrue(
                retired_anchors.isdisjoint(actual_anchors),
                f"retired responsibility headings reappeared in {path}: "
                f"{sorted(retired_anchors.intersection(actual_anchors))}",
            )

        retired_references = []
        doc_paths = [COURSE_CREATOR_REFERENCES.parent / "SKILL.md"]
        doc_paths.extend(COURSE_CREATOR_REFERENCES.rglob("*.md"))
        doc_paths.extend(
            (COURSE_CREATOR_REFERENCES.parent / "examples").rglob("*.md")
        )
        for path in doc_paths:
            content = path.read_text(encoding="utf-8").casefold()
            for anchor in retired_anchors:
                if f"#{anchor}" in content:
                    retired_references.append(
                        f"{path.relative_to(REPO_ROOT)}#{anchor}"
                    )
        self.assertEqual([], retired_references)

        for anchor, owner_path in moved_anchor_owners.items():
            unexpected_paths = [
                path
                for path, actual_anchors in self.reference_anchors_by_path.items()
                if path != owner_path and anchor in actual_anchors
            ]
            self.assertEqual(
                [],
                unexpected_paths,
                f"authority anchor {anchor!r} belongs only in {owner_path}",
            )

        self.assertNotIn(
            "Teaching Prompt and Course Prompt Authoring Hard Rules",
            self.prompt_contracts,
        )
        self.assertNotIn("?[%{{var}}", self.prompt_contracts)
        self.assertNotIn("single-select", self.prompt_contracts)
        self.assertNotIn("multi-select", self.prompt_contracts)
        self.assertNotIn("UNKNOWN", self.prompt_contracts)
        self.assertIn("(pedagogy.md)", authority)
        self.assertIn("(markdownflow.md)", authority)

        forbidden_markdownflow_fragments = {
            "answer must leave the current lesson",
            "Use single-select for",
            "Use multi-select for",
            "Prompt Placement Rules",
            "Input Marker Rules",
            "Input Marker Examples",
            "Correct:",
            "Incorrect:",
            "Which form to use",
            "Default to 3.1",
            "upload-image",
            "res.ai-shifu.cn",
            "必须原样保留",
            "不得省略",
            "语义化 alt",
            "保持原始宽高比",
            "Do not lock an entire lesson",
            "Raw SVG, HTML drawings, Mermaid",
            "pedagogy.md",
            "generation-workflow.md",
            "optimization-workflow.md",
            "data-contracts.md",
        }
        for fragment in forbidden_markdownflow_fragments:
            self.assertNotIn(fragment, self.markdownflow)

        interaction_encoding = markdown_section(
            self.generation_workflow, "Interaction Encoding"
        )
        image_authoring = markdown_section(
            self.generation_workflow, "Image Authoring"
        )
        preservation_encoding = markdown_section(
            self.generation_workflow, "Preservation Encoding"
        )
        preservation_decisions = markdown_section(
            self.optimization_workflow, "Preservation Decisions"
        )
        self.assertIn("`?[]` control on its own line", interaction_encoding)
        self.assertIn("Raw SVG, HTML drawings, Mermaid", image_authoring)
        self.assertIn("res.ai-shifu.cn", image_authoring)
        self.assertIn("HTML-view", image_authoring)
        self.assertIn("不得省略", image_authoring)
        self.assertIn("语义化 alt", image_authoring)
        self.assertIn("保持原始宽高比", image_authoring)

        image_authoring_only_fragments = {
            "不得省略",
            "语义化 alt",
            "保持原始宽高比",
        }
        for path in doc_paths:
            if path == COURSE_CREATOR_REFERENCES / "generation-workflow.md":
                continue
            content = path.read_text(encoding="utf-8")
            for fragment in image_authoring_only_fragments:
                self.assertNotIn(
                    fragment,
                    content,
                    f"image authoring rule {fragment!r} belongs only in "
                    "generation-workflow.md",
                )
        self.assertNotIn("entire lesson", preservation_encoding)
        self.assertIn(
            "An entire lesson is not a valid preservation scope",
            preservation_decisions,
        )
        self.assertNotIn("entire lesson", self.review_checklist)
        self.assertNotIn("`!===", preservation_decisions)
        self.assertNotIn("deterministic markers", preservation_decisions)

        self.assertIn(
            "do not duplicate them in the Teaching Prompt body",
            self.data_contracts,
        )
        self.assertIn(
            "filler removal, sentence smoothing", self.optimization_workflow
        )
        self.assertIn("silent factual change", self.optimization_workflow)

        self.assertNotIn("## Boundaries", self.course_prompt)
        self.assertNotIn("## Validation", self.course_prompt)
        self.assertIn("## Materialization Checks", self.course_prompt)

    def test_course_prompt_placeholder_map_matches_template(self):
        template = markdown_section(self.course_prompt, "Fillable Template")
        sources = markdown_section(
            self.course_prompt, "Placeholder Sources and Context"
        )
        placeholders = markdown_table_first_column(sources, "Placeholder")

        self.assertEqual(5, template.count("XXX"))
        self.assertEqual(5, len(placeholders))
        self.assertEqual(len(placeholders), len(set(placeholders)))
        self.assertIn("they do not add placeholders to the template", sources)

    def test_removed_authoring_controls_do_not_reappear(self):
        scan_roots = [
            COURSE_CREATOR_REFERENCES.parent,
            REPO_ROOT / "scripts",
            REPO_ROOT / "tests",
        ]
        removed_terms = {
            "interaction_" + "density",
            "interaction " + "density",
            "interaction-" + "density",
            "互动" + "密度",
            "交互" + "密度",
        }
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

        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
