from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-shifu-course-creator"
SKILL_MD = SKILL_ROOT / "SKILL.md"


class CourseCreatorRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = SKILL_MD.read_text(encoding="utf-8")

    def route_line(self, intent_prefix: str) -> str:
        for line in self.router.splitlines():
            if line.startswith(f"| {intent_prefix}"):
                return line
        self.fail(f"Intent prefix {intent_prefix!r} not found in router table")

    def test_main_file_is_a_small_router(self):
        self.assertLess(len(self.router.splitlines()), 150)
        self.assertIn("## Task Router", self.router)
        self.assertFalse(
            (SKILL_ROOT / "references" / "authoring-workflow.md").exists()
        )
        routed_guides = (
            "session-controls.md",
            "authentication.md",
            "course-target.md",
            "authoring-controls.md",
            "prompt-contracts.md",
            "authoring-intake.md",
            "segmentation-orchestration.md",
            "generation-workflow.md",
            "optimization-workflow.md",
            "deployment-workflow.md",
            "analytics/workflow.md",
        )
        for relative_path in routed_guides:
            path = SKILL_ROOT / "references" / relative_path
            self.assertLess(
                len(path.read_text(encoding="utf-8").splitlines()),
                300,
                f"{path} should be split before it becomes a second monolith",
            )

    def test_large_reference_files_have_contents_navigation(self):
        for path in (SKILL_ROOT / "references").rglob("*.md"):
            content = path.read_text(encoding="utf-8")
            if len(content.splitlines()) > 300:
                self.assertIn(
                    "## Contents",
                    content,
                    f"{path} needs navigation for progressive disclosure",
                )

    def test_authoring_routes_declare_shared_dependencies(self):
        for prefix in (
            "Create a full course",
            "Generate Teaching Prompts",
            "Optimize content in an existing platform course",
            "Deploy a new course",
        ):
            route = self.route_line(prefix)
            self.assertIn("references/authentication.md", route)
            self.assertIn("references/prompt-contracts.md", route)

    def test_platform_and_analytics_routes_require_authentication(self):
        for prefix in (
            "Publish, preview",
            "Query observed data",
        ):
            route = self.route_line(prefix)
            self.assertIn("references/authentication.md", route)

    def test_generation_runs_design_intake_before_prompt_contracts(self):
        route = self.route_line("Generate Teaching Prompts")
        self.assertLess(
            route.index("references/authoring-intake.md"),
            route.index("references/prompt-contracts.md"),
        )

    def test_pure_analytics_does_not_load_authoring_guides(self):
        route = self.route_line("Query observed data")
        self.assertNotIn("authoring-intake.md", route)
        self.assertNotIn("generation-workflow.md", route)
        self.assertNotIn("optimization-workflow.md", route)

    def test_offline_prompt_audit_does_not_require_platform_access(self):
        route = self.route_line("Review or audit pasted")
        self.assertNotIn("authentication.md", route)
        self.assertNotIn("course-target.md", route)
        self.assertIn("prompt-contracts.md", route)
        self.assertIn("optimization-workflow.md", route)

    def test_structure_planning_has_an_explicit_route(self):
        route = self.route_line("Plan course structure")
        self.assertIn("authoring-intake.md", route)
        self.assertIn("segmentation-orchestration.md#segmentation", route)

    def test_design_count_is_not_analytics(self):
        self.assertIn(
            "how many lessons should this material become?",
            self.router,
        )
        self.assertIn("remain authoring tasks", self.router)
        self.assertNotIn("any question asking for a number", self.router)

    def test_global_language_and_reporting_contracts_are_loaded(self):
        session = (
            SKILL_ROOT / "references" / "session-controls.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("## Output " + "Language", session)
        self.assertIn("## Progress, Errors, and Handoffs", session)
        self.assertIn("references/data-contracts.md#language-resolution", self.router)
        self.assertIn("resolve `resolved_target_language`", self.router)
        self.assertIn("before the first user-visible response", self.router)
        self.assertIn("## Reporting", self.router)
        self.assertIn("#deployment-report", self.router)
        self.assertIn("references/report-template.md", self.router)
        self.assertIn(
            "When fallback mode applies, also read",
            self.router,
        )

    def test_resolved_language_identifiers_are_single_sourced(self):
        data_contracts = (
            SKILL_ROOT / "references" / "data-contracts.md"
        ).read_text(encoding="utf-8")
        session_controls = (
            SKILL_ROOT / "references" / "session-controls.md"
        ).read_text(encoding="utf-8")
        language_resolution = data_contracts.split(
            "## Language Resolution", 1
        )[1].split("## Fallback Output Extensions", 1)[0]
        priority = language_resolution.split("### Priority Order", 1)[1]
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
            "any applicable context explicitly specifies a language",
            priority,
        )
        self.assertIn(
            "otherwise, the language detected from the current user prompt",
            priority,
        )
        self.assertIn("follow the normal instruction hierarchy", priority)
        self.assertIn("most recent applicable directive", priority)
        self.assertIn(
            "`resolved_target_language` is a string",
            data_contracts,
        )
        self.assertIn("`resolved_target_language`", data_contracts)
        self.assertIn("`resolved_target_language`", session_controls)
        self.assertNotIn("### Rules", language_resolution)
        self.assertNotIn("Pre-Deploy Language Audit", language_resolution)
        for identifier in priority_identifiers:
            self.assertNotIn(f"`{identifier}`", session_controls)

        skill_content = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_ROOT.rglob("*.md")
        ).casefold()
        deprecated_aliases = (
            "resolved " + "output language",
            "resolved " + "target language",
            "resolved " + "language",
            "actual " + "output language",
            "in the user's " + "language",
            "reply in the user's " + "language",
        )
        for alias in deprecated_aliases:
            self.assertNotIn(alias, skill_content)

        template = (REPO_ROOT / "templates" / "skill.yaml.template").read_text(
            encoding="utf-8"
        )
        template_language_resolution = template.split(
            "language_resolution:", 1
        )[1].split("inputs:", 1)[0]
        template_priority_identifiers = re.findall(
            r'^\s+-\s+"([^"]+)"$',
            template_language_resolution,
            re.MULTILINE,
        )
        self.assertEqual(
            priority_identifiers,
            template_priority_identifiers,
        )
        language_contract_surfaces = "\n".join(
            (data_contracts, session_controls, template)
        )
        self.assertIsNone(
            re.search(
                r"\bbcp(?:[-_ ]?47)\b",
                language_contract_surfaces,
                re.IGNORECASE,
            )
        )
        legacy_table_headers = (
            "en-" + "US",
            "zh-" + "CN",
            "fr-" + "FR",
        )
        for header in legacy_table_headers:
            self.assertNotIn(header, session_controls)

    def test_language_constraints_are_owned_by_concrete_scenarios(self):
        references = SKILL_ROOT / "references"
        scenario_expectations = {
            "session-controls.md": (
                "Support & Contact",
                "Version Check",
                "Progress, Errors, and Handoffs",
                "resolved_target_language",
            ),
            "authentication.md": (
                "SMS-code prompts",
                "resolved_target_language",
            ),
            "course-target.md": (
                "new-versus-existing choice questions",
                "resolved_target_language",
            ),
            "authoring-intake.md": (
                "Course Design Intake",
                "resolved_target_language",
            ),
            "segmentation-orchestration.md": (
                "core_point",
                "transfer_signals",
                "rerun_plan",
                "resolved_target_language",
            ),
            "generation-workflow.md": (
                "lesson_teaching_prompts[].teaching_prompt",
                "assumptions[]",
                "newly authored alt text",
                "resolved_target_language",
            ),
            "optimization-workflow.md": (
                "Course Description and Review Outputs",
                "change_list[].change",
                "resolved_target_language",
            ),
            "report-template.md": (
                "Report language",
                "purpose label in resolved_target_language",
            ),
            "analytics/privacy-and-presentation.md": (
                "Answer Structure",
                "drill-down offers",
                "resolved_target_language",
            ),
            "cli/course-directory-spec.md": (
                "README.md",
                "chapters[].title",
                "resolved_target_language",
            ),
        }
        for relative_path, expected_phrases in scenario_expectations.items():
            content = (references / relative_path).read_text(encoding="utf-8")
            for phrase in expected_phrases:
                with self.subTest(path=relative_path, phrase=phrase):
                    self.assertIn(phrase, content)

        report = (references / "report-template.md").read_text(encoding="utf-8")
        verification_templates = report.split("Verification URLs:", 1)[1]
        self.assertIn("illustrative templates only", verification_templates)
        self.assertIn(
            "ordinary Markdown without the surrounding fence",
            verification_templates,
        )
        self.assertIn(
            "translate every non-placeholder instruction",
            (references / "optimization-workflow.md").read_text(encoding="utf-8"),
        )

        review = (references / "review-checklist.md").read_text(
            encoding="utf-8"
        )
        language_audit = review.split("## Language Audit", 1)[1].split(
            "## Structure Separation", 1
        )[0]
        checked_outputs = (
            "segments[].core_point",
            "course_index[].lesson_title",
            "course_index[].core_question",
            "lesson_teaching_prompts[].lesson_title",
            "lesson_teaching_prompts[].teaching_prompt",
            "global_variable_table[].name",
            "course_prompt",
            "course_description",
            "README.md",
            "course-description.md",
            "structure.json.chapters[].title",
            "course-prompt.md",
            "lessons/lesson-*.md",
            "shifu.title",
            "shifu.description",
            "shifu.course_prompt",
            "outline_items[].title",
            "outline_items[].content",
        )
        for output in checked_outputs:
            with self.subTest(output=output):
                self.assertIn(output, language_audit)
        self.assertNotIn(
            "Generated course artifacts and learner-facing passages",
            language_audit,
        )

    def test_safe_deployment_branches_new_and_existing_targets(self):
        deployment = (
            SKILL_ROOT / "references" / "deployment-workflow.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Deploy a new target", deployment)
        self.assertIn("do not run this command", deployment)
        self.assertIn("Existing target: use the Version Sync Workflow", deployment)

    def test_removed_section_references_do_not_return(self):
        stale_phrases = (
            "Data & Statistics Routing",
            "Workflow, references, and validation: `## Analytics` below",
            "SKILL.md `## Execution Modes`",
        )
        content = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_ROOT.rglob("*.md")
        )
        for phrase in stale_phrases:
            self.assertNotIn(phrase, content)


if __name__ == "__main__":
    unittest.main()
