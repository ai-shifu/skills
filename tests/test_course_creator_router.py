from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-shifu-course-creator"


class CourseCreatorCapabilityTests(unittest.TestCase):
    """Protect discovery and package boundaries without prescribing a task plan."""

    @classmethod
    def setUpClass(cls):
        cls.entrypoint = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    def test_public_skill_identity_and_cli_remain_available(self):
        self.assertRegex(self.entrypoint, r"(?m)^name: ai-shifu-course-creator$")
        self.assertTrue((SKILL_ROOT / "scripts" / "shifu-cli.py").is_file())
        ui_metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("$ai-shifu-course-creator", ui_metadata)

    def test_entrypoint_discovers_design_expression_and_cli_capabilities(self):
        for capability in (
            "course-design-intake.md",
            "segmentation-workflow.md",
            "pedagogy.md",
            "markdownflow.md",
            "teaching-prompt.md",
            "course-prompt.md",
            "course-description.md",
            "optimization-workflow.md",
            "image-authoring.md",
            "authentication.md",
            "course-target.md",
            "deployment-workflow.md",
            "course-sync.md",
            "course-management.md",
            "analytics/overview.md",
        ):
            with self.subTest(capability=capability):
                self.assertIn(f"references/{capability}", self.entrypoint)

    def test_entrypoint_does_not_restore_the_fixed_task_pipeline(self):
        for removed_interface in (
            "## Startup Sequence",
            "## Task Router",
            "Required files, in order",
            "authoring-mode.md",
            "orchestration-workflow.md",
            "analytics/workflow.md",
        ):
            with self.subTest(removed_interface=removed_interface):
                self.assertNotIn(removed_interface, self.entrypoint)

    def test_retired_coordinators_are_not_bundled(self):
        for relative_path in (
            "references/authoring-mode.md",
            "references/orchestration-workflow.md",
            "references/analytics/workflow.md",
        ):
            self.assertFalse((SKILL_ROOT / relative_path).exists(), relative_path)

    def test_active_skill_documents_spell_out_markdownflow(self):
        paths = [SKILL_ROOT / "SKILL.md", *sorted((SKILL_ROOT / "references").rglob("*.md"))]
        for path in paths:
            content = path.read_text(encoding="utf-8")
            if path.name == "SKILL.md":
                content = re.sub(
                    r"(?m)^description:.*$",
                    lambda match: match.group().replace("MarkdownFlow (MDF)", "MarkdownFlow", 1),
                    content,
                )
            with self.subTest(path=path.relative_to(SKILL_ROOT)):
                self.assertNotRegex(content, r"\bMDF\b")


if __name__ == "__main__":
    unittest.main()
