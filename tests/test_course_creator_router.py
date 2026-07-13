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
        return next(
            line
            for line in self.router.splitlines()
            if line.startswith(f"| {intent_prefix}")
        )

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
        self.assertIn("## Output Language", session)
        self.assertIn("before the first user-visible response", self.router)
        self.assertIn("## Reporting", self.router)
        self.assertIn("#deployment-report", self.router)

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
