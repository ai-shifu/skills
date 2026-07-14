from __future__ import annotations

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
            "authoring-intake.md",
            "delivery-modes.md",
            "image-assets.md",
            "prompt-contracts.md",
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
        ):
            route = self.route_line(prefix)
            self.assertIn("references/authentication.md", route)
            self.assertIn("references/delivery-modes.md", route)
            self.assertIn("references/prompt-contracts.md", route)

    def test_deploy_route_preserves_platform_mode_and_routes_images_conditionally(self):
        route = self.route_line("Deploy a new course")

        self.assertIn("references/authentication.md", route)
        self.assertIn("references/prompt-contracts.md", route)
        self.assertIn("references/image-assets.md", route)
        self.assertIn("local images", route)
        self.assertIn("invalid platform resource URLs", route)
        self.assertIn("references/deployment-workflow.md", route)
        self.assertNotIn("references/delivery-modes.md", route)

    def test_platform_and_analytics_routes_require_authentication(self):
        for prefix in (
            "Publish, preview",
            "Query observed data",
        ):
            route = self.route_line(prefix)
            self.assertIn("references/authentication.md", route)

    def test_listen_mode_route_loads_only_its_required_boundaries(self):
        route = self.route_line("Enable, disable, or inspect Listen Mode")
        required = (
            "references/authentication.md",
            "references/deployment-workflow.md#listen-mode-management",
        )

        for earlier, later in zip(required, required[1:]):
            self.assertLess(route.index(earlier), route.index(later))
        self.assertEqual(route.count("references/"), len(required))
        self.assertNotIn("authoring-intake.md", route)
        self.assertNotIn("prompt-contracts.md", route)

    def test_listen_mode_handoff_preserves_authoring_decisions(self):
        deployment = (
            SKILL_ROOT / "references" / "deployment-workflow.md"
        ).read_text(encoding="utf-8")
        delivery_modes = (
            SKILL_ROOT / "references" / "delivery-modes.md"
        ).read_text(encoding="utf-8")
        handoff = deployment.split("### Delivery Mode Handoff", 1)[1].split(
            "\n### ", 1
        )[0]
        resolution = delivery_modes.split("## Resolution and Handoff", 1)[1].split(
            "\n## ", 1
        )[0]

        self.assertIn("produced earlier in the same request", handoff)
        self.assertIn("do not reinterpret", handoff)
        self.assertIn("do not infer or confirm a delivery mode", handoff)

        self.assertIn("authoring_run_controls", resolution)
        self.assertIn("delivery_mode", resolution)
        self.assertIn("listen_mode_enabled", resolution)
        self.assertIn("data-contracts.md#final-authoring-output", resolution)
        self.assertIn("without reinterpreting", resolution)
        self.assertIn("Independent deployment", resolution)
        self.assertIn("does not resolve, infer, or ask for `delivery_mode`", resolution)
        self.assertIn("outside this authoring contract", resolution)
        self.assertIn("ask the user to choose", resolution)
        self.assertIn("focused audit or narrow existing-course prompt edit", resolution)
        self.assertIn("preserves the supplied artifact's existing mode-dependent structure", resolution)
        self.assertIn("selected platform workflow owns their attribute behavior", resolution)
        self.assertNotIn("preserve the current platform Listen Mode", resolution)

        standard = delivery_modes.split("## Standard", 1)[1].split(
            "\n## ", 1
        )[0]
        pure_slides = delivery_modes.split("## Pure Slides", 1)[1]
        self.assertIn("listen_mode_enabled", standard)
        self.assertIn("unchanged", standard)
        self.assertIn("Normalize `listen_mode_enabled` to `false`", pure_slides)

        listen_management = deployment.split("### Listen Mode Management", 1)[1].split(
            "\n### ", 1
        )[0]
        self.assertIn("inspection request", listen_management)
        self.assertIn("without calling `set-tts`", listen_management)
        self.assertIn("user-requested value", listen_management)
        self.assertIn("non-blocking warning", listen_management)

    def test_generation_runs_design_intake_before_prompt_contracts(self):
        route = self.route_line("Generate Teaching Prompts")
        self.assertLess(
            route.index("references/authoring-intake.md"),
            route.index("references/delivery-modes.md"),
        )
        self.assertLess(
            route.index("references/delivery-modes.md"),
            route.index("references/prompt-contracts.md"),
        )

    def test_full_course_optimization_requires_design_intake(self):
        route = self.route_line("Optimize content in an existing platform course")

        self.assertIn("performing full-course finalization", route)
        self.assertIn("creates or replaces the Course Prompt", route)
        self.assertIn("insert `references/authoring-intake.md`", route)

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
        self.assertIn("## Output Language", session)
        self.assertIn("before the first user-visible response", self.router)
        self.assertIn("## Reporting", self.router)
        self.assertIn("#deployment-report", self.router)
        self.assertIn("references/report-template.md", self.router)
        report_template = (
            SKILL_ROOT / "references" / "report-template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Input normalization notes:", report_template)
        self.assertIn("ignored legacy input path and value", report_template)
        self.assertIn(
            "When fallback mode applies, also read",
            self.router,
        )

    def test_safe_deployment_branches_new_and_existing_targets(self):
        route = self.route_line("Deploy a new course")
        deployment = (
            SKILL_ROOT / "references" / "deployment-workflow.md"
        ).read_text(encoding="utf-8")
        self.assertIn("review-checklist.md#pre-deploy-language-audit", route)
        self.assertIn("Pre-Deploy Language Audit", deployment)
        self.assertIn("Deploy a new target", deployment)
        self.assertIn("do not run this command", deployment)
        self.assertIn("Existing target: use the Version Sync Workflow", deployment)
        self.assertIn("do not change Listen Mode", deployment)

    def test_standalone_deploy_and_narrow_updates_preserve_tts(self):
        deployment = (
            SKILL_ROOT / "references" / "deployment-workflow.md"
        ).read_text(encoding="utf-8")
        delivery_modes = (
            SKILL_ROOT / "references" / "delivery-modes.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Standalone deployment and narrow existing-course content updates", deployment)
        self.assertIn("preserve lesson access, visibility, Listen Mode", deployment)
        self.assertIn("Do not infer or ask for a delivery mode", deployment)
        self.assertIn("do not change Listen Mode", deployment)
        self.assertIn("same request that also asks for deployment", deployment)
        self.assertIn("Authoring without deployment", delivery_modes)
        self.assertIn("does not authorize a platform change", delivery_modes)
        self.assertIn("stop standalone deployment", deployment)
        self.assertIn("do not silently assume the standard profile", deployment)

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
