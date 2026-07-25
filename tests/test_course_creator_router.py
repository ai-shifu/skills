from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-shifu-course-creator"
REFERENCES = SKILL_ROOT / "references"
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
        self.assertNotIn("## Reference Map", self.router)

    def test_router_does_not_duplicate_downstream_operating_rules(self):
        analytics_workflow = (
            REFERENCES / "analytics" / "workflow.md"
        ).read_text(encoding="utf-8")
        course_sync = (REFERENCES / "course-sync.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("All analytics traffic goes through", analytics_workflow)
        self.assertIn("Never write raw HTTP", analytics_workflow)
        self.assertNotIn("Do not guess analytics endpoints", self.router)
        self.assertIn("## Pull Before Editing", course_sync)
        self.assertNotIn("always author from the freshly pulled", self.router)

    def test_single_purpose_reference_set_replaces_combined_guides(self):
        expected_files = {
            "language-policy.md",
            "authoring-mode.md",
            "course-design-intake.md",
            "source-preservation.md",
            "segmentation-workflow.md",
            "orchestration-workflow.md",
            "teaching-prompt.md",
            "markdownflow-authoring.md",
            "image-authoring.md",
            "course-description.md",
            "optimization-checklist.md",
            "course-sync.md",
            "course-management.md",
        }
        retired_files = {
            "authoring-controls.md",
            "authoring-intake.md",
            "segmentation-orchestration.md",
            "generation-workflow.md",
            "review-checklist.md",
            "authoring-workflow.md",
        }

        for filename in expected_files:
            with self.subTest(filename=filename):
                self.assertTrue((REFERENCES / filename).is_file())

        for filename in retired_files:
            with self.subTest(filename=filename):
                self.assertFalse((REFERENCES / filename).exists())
                self.assertNotIn(filename, self.router)

    def test_routed_guides_remain_focused(self):
        routed_guides = {
            path.removeprefix("references/").split("#", 1)[0]
            for line in self.router.splitlines()
            if line.startswith("| ")
            for path in _backticked_paths(line)
            if path.startswith("references/")
        }
        for relative_path in routed_guides:
            path = REFERENCES / relative_path
            with self.subTest(path=relative_path):
                self.assertTrue(path.is_file())
                self.assertLess(
                    len(path.read_text(encoding="utf-8").splitlines()),
                    300,
                    f"{path} should be split before it becomes a second monolith",
                )

    def test_course_creator_has_no_bundled_examples(self):
        self.assertFalse((SKILL_ROOT / "examples").exists())
        self.assertNotIn("examples/", self.router)
        paths_to_check = list(REFERENCES.rglob("*.md"))
        paths_to_check.extend(
            [REPO_ROOT / "README.md", REPO_ROOT / "README.zh-CN.md"]
        )
        for path in paths_to_check:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "examples/",
                content,
                f"Stale examples reference found in {path}",
            )

    def test_large_reference_files_have_contents_navigation(self):
        for path in REFERENCES.rglob("*.md"):
            content = path.read_text(encoding="utf-8")
            if len(content.splitlines()) > 300:
                self.assertIn(
                    "## Contents",
                    content,
                    f"{path} needs navigation for progressive disclosure",
                )

    def test_full_course_deploys_after_authoring_and_optimization_by_default(self):
        route = self.route_line("Create a full course")
        ordered_files = (
            "references/course-design-intake.md",
            "references/orchestration-workflow.md",
            "references/course-prompt.md",
            "references/course-description.md",
            "references/optimization-workflow.md",
            "references/deployment-workflow.md",
        )

        positions = []
        for path in ordered_files:
            self.assertIn(path, route)
            positions.append(route.index(path))
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(route.endswith("`references/deployment-workflow.md` |"))
        self.assertNotIn(
            "only when deployment or publication is requested",
            self.router,
        )

    def test_platform_routes_require_authentication(self):
        for prefix in (
            "Create a full course",
            "Optimize Teaching Prompt content in an existing platform course",
            "Deploy a new course",
            "Publish, preview",
            "Query observed data",
        ):
            with self.subTest(prefix=prefix):
                self.assertIn(
                    "references/authentication.md", self.route_line(prefix)
                )

    def test_generation_runs_design_intake_before_teaching_prompt(self):
        route = self.route_line("Generate Teaching Prompts")
        self.assertLess(
            route.index("references/course-design-intake.md"),
            route.index("references/teaching-prompt.md"),
        )

    def test_local_teaching_prompt_route_omits_platform_setup(self):
        route = self.route_line(
            "Produce local Teaching Prompts from existing segments"
        )
        self.assertIn("references/teaching-prompt.md", route)
        self.assertNotIn("authentication.md", route)
        self.assertNotIn("course-target.md", route)

    def test_raw_local_teaching_prompt_route_segments_without_platform_setup(self):
        route = self.route_line(
            "Produce local Teaching Prompts from raw supplied material"
        )
        self.assertLess(
            route.index("references/segmentation-workflow.md"),
            route.index("references/teaching-prompt.md"),
        )
        self.assertNotIn("authentication.md", route)
        self.assertNotIn("course-target.md", route)
        self.assertNotIn("orchestration-workflow.md", route)

    def test_target_kind_change_requires_router_reclassification(self):
        target_contract = (REFERENCES / "course-target.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("resolved target kind", self.router)
        self.assertIn("reclassify the remaining work", self.router)
        self.assertIn("new-only or existing-only", self.router)
        self.assertIn("Create intent with one or more matches", target_contract)
        self.assertIn("Edit intent with no match", target_contract)
        self.assertIn("explicitly confirms creation", target_contract)
        self.assertIn("explicit Shifu BID", target_contract)
        self.assertIn("run `show <shifu_bid>`", target_contract)

    def test_course_prompt_only_route_stays_local_and_focused(self):
        route = self.route_line("Create or revise a Course Prompt")
        self.assertIn("references/course-prompt.md", route)
        for filename in (
            "authentication.md",
            "course-target.md",
            "orchestration-workflow.md",
            "teaching-prompt.md",
            "deployment-workflow.md",
        ):
            self.assertNotIn(filename, route)

    def test_structure_planning_runs_segmentation_then_structure_finalization(self):
        route = self.route_line("Plan course structure")
        self.assertIn("course-design-intake.md", route)
        segmentation = "references/segmentation-workflow.md"
        finalizer = (
            "references/orchestration-workflow.md#lesson-structure-finalization"
        )
        self.assertIn(segmentation, route)
        self.assertIn(finalizer, route)
        self.assertLess(route.index(segmentation), route.index(finalizer))

    def test_offline_prompt_audit_does_not_require_platform_access(self):
        route = self.route_line("Review or audit pasted")
        self.assertNotIn("authentication.md", route)
        self.assertNotIn("course-target.md", route)
        self.assertIn("optimization-workflow.md", route)

        session_controls = (
            REFERENCES / "session-controls.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "explicitly requires offline or no-network execution",
            session_controls,
        )
        self.assertIn("skip this automatic check", session_controls)

    def test_explicit_local_only_authoring_skips_platform_setup(self):
        route = self.route_line("Produce a complete course locally")
        self.assertIn("references/orchestration-workflow.md", route)
        for filename in (
            "authentication.md",
            "course-target.md",
            "deployment-workflow.md",
            "course-sync.md",
            "course-management.md",
        ):
            self.assertNotIn(filename, route)

    def test_pure_analytics_does_not_load_authoring_guides(self):
        route = self.route_line("Query observed data")
        for filename in (
            "course-design-intake.md",
            "segmentation-workflow.md",
            "orchestration-workflow.md",
            "teaching-prompt.md",
            "optimization-workflow.md",
        ):
            self.assertNotIn(filename, route)

    def test_sync_and_management_are_separate_platform_routes(self):
        sync_route = self.route_line("Sync edited lesson content")
        management_route = self.route_line("Publish, preview")
        self.assertIn("course-sync.md", sync_route)
        self.assertNotIn("course-management.md", sync_route)
        self.assertIn("course-management.md", management_route)
        self.assertNotIn("course-sync.md", management_route)
        self.assertNotIn("teaching-prompt.md", management_route)

    def test_listing_courses_does_not_require_target_resolution(self):
        route = self.route_line("List platform courses")
        self.assertIn("authentication.md", route)
        self.assertIn("course-management.md", route)
        self.assertNotIn("course-target.md", route)

    def test_existing_structural_edit_syncs_content_before_metadata(self):
        route = self.route_line("Restructure an existing platform course")
        self.assertLess(
            route.index("references/course-sync.md#pull-before-editing"),
            route.index("references/orchestration-workflow.md"),
        )
        self.assertLess(
            route.index("references/optimization-workflow.md"),
            route.index("references/course-sync.md#push-existing-course-content"),
        )
        self.assertLess(
            route.index("references/course-sync.md#push-existing-course-content"),
            route.index("references/course-management.md"),
        )
        self.assertNotIn("references/deployment-workflow.md", route)

    def test_existing_content_push_routes_load_conflict_convergence(self):
        for prefix in (
            "Restructure an existing platform course",
            "Revise lesson-level teaching design",
            "Replace an existing lesson Teaching Prompt",
            "Optimize Teaching Prompt content in an existing platform course",
        ):
            with self.subTest(prefix=prefix):
                route = self.route_line(prefix)
                push = "references/course-sync.md#push-existing-course-content"
                convergence = "references/course-sync.md#conflict-convergence"
                self.assertIn(push, route)
                self.assertIn(convergence, route)
                self.assertLess(route.index(push), route.index(convergence))

    def test_existing_lesson_design_edit_omits_course_wide_artifacts(self):
        route = self.route_line("Revise lesson-level teaching design")
        self.assertIn("references/course-design-intake.md", route)
        self.assertIn("references/teaching-prompt.md", route)
        self.assertIn("references/optimization-workflow.md", route)
        for filename in (
            "orchestration-workflow.md",
            "course-prompt.md",
            "course-description.md",
            "course-management.md",
            "deployment-workflow.md",
        ):
            self.assertNotIn(filename, route)

    def test_provided_teaching_prompt_is_audited_between_pull_and_push(self):
        route = self.route_line("Replace an existing lesson Teaching Prompt")
        self.assertLess(
            route.index("references/course-sync.md#pull-before-editing"),
            route.index("references/optimization-workflow.md"),
        )
        self.assertLess(
            route.index("references/optimization-workflow.md"),
            route.index("references/course-sync.md#push-existing-course-content"),
        )
        self.assertNotIn("references/course-management.md", route)
        self.assertNotIn("references/deployment-workflow.md", route)

    def test_existing_course_level_artifacts_use_metadata_management(self):
        for prefix, owner in (
            ("Create or revise a Course Prompt in an existing", "course-prompt.md"),
            (
                "Create or revise a course description in an existing",
                "course-description.md",
            ),
        ):
            with self.subTest(prefix=prefix):
                route = self.route_line(prefix)
                self.assertIn(f"references/{owner}", route)
                self.assertIn("references/optimization-workflow.md", route)
                self.assertIn("references/course-management.md", route)
                self.assertNotIn(
                    "references/course-sync.md#push-existing-course-content",
                    route,
                )

    def test_design_count_is_not_analytics(self):
        self.assertIn(
            "how many lessons should this material become?",
            self.router,
        )
        self.assertIn("remain authoring tasks", self.router)
        self.assertNotIn("any question asking for a number", self.router)

    def test_language_and_reporting_contracts_are_loaded_once(self):
        startup = self.router.split("## Task Router", 1)[0]
        self.assertIn("references/language-policy.md", startup)
        self.assertIn("references/session-controls.md", startup)
        self.assertIn("resolve `resolved_target_language`", startup)
        self.assertIn("before the first user-visible response", startup)
        self.assertIn("## Reporting", self.router)
        self.assertIn("#deployment-report", self.router)
        self.assertIn("references/report-template.md", self.router)

    def test_contact_mentions_are_contextual_bounded_and_conversation_only(self):
        session_controls = (
            REFERENCES / "session-controls.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Conditional opening turn", session_controls)
        self.assertIn("First invocation alone is never a trigger", session_controls)
        self.assertIn("Substantive milestone", session_controls)
        self.assertIn("Product or human-help intent", session_controls)
        self.assertIn("Persistent platform block", session_controls)
        self.assertIn(
            "Never include contact mentions in adjacent user-visible responses",
            session_controls,
        )
        self.assertIn(
            "suppress it for the same intent and journey stage",
            session_controls,
        )
        self.assertIn(
            "can qualify again after intervening work",
            session_controls,
        )
        self.assertIn("a first recoverable error alone is not enough", session_controls)
        self.assertIn("a lightweight opening-turn task", session_controls)
        self.assertIn("Keep the contact link in the operational conversation only", session_controls)
        self.assertIn("Never put it in", session_controls)
        self.assertNotIn(
            "include a brief contact mention in the first user-visible response",
            session_controls,
        )
        self.assertNotIn("Contact page:", self.router)

    def test_verification_url_templates_survive_markdown_formatting(self):
        report = (REFERENCES / "report-template.md").read_text(encoding="utf-8")
        verification_templates = report.split("Verification URLs:", 1)[1]

        for purpose_label in (
            "localized admin-console label",
            "localized course-preview label",
            "localized published-course label",
        ):
            with self.subTest(purpose_label=purpose_label):
                self.assertIn(
                    f"  - [<course name> - <{purpose_label}>]"
                    "(<URL from script>)\n"
                    "    <URL from script>\n"
                    '    <Chinese hint copied verbatim from the script output, '
                    'without "#">',
                    verification_templates,
                )

    def test_removed_identifiers_and_section_references_do_not_return(self):
        stale_phrases = (
            "require_branching_feedback",
            "allow_headings",
            "viewpoint_check",
            "Data & Statistics Routing",
            "Workflow, references, and validation: `## Analytics` below",
            "SKILL.md `## Execution Modes`",
        )
        content = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_ROOT.rglob("*")
            if path.is_file() and path.suffix in {".md", ".json", ".py"}
        )
        for phrase in stale_phrases:
            self.assertNotIn(phrase, content)


def _backticked_paths(markdown: str) -> list[str]:
    paths = []
    for piece in markdown.split("`")[1::2]:
        if ".md" in piece:
            paths.append(piece)
    return paths


if __name__ == "__main__":
    unittest.main()
