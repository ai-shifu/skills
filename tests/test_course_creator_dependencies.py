from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_skill_quality  # noqa: E402


SKILL_ROOT = REPO_ROOT / "skills" / "ai-shifu-course-creator"
REFERENCES = SKILL_ROOT / "references"
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
REFERENCE_PATH = re.compile(r"`(references/[A-Za-z0-9_./-]+\.md(?:#[A-Za-z0-9-]+)?)`")


def local_markdown_targets(path: Path) -> list[str]:
    text = validate_skill_quality.markdown_without_fenced_code_or_html_comments(
        path.read_text(encoding="utf-8")
    )
    return [
        target
        for target in MARKDOWN_LINK.findall(text)
        if ".md" in target and "://" not in target
    ]


class CourseCreatorReferenceTests(unittest.TestCase):
    """Capabilities may cross-reference each other without an execution DAG."""

    def assert_target_exists(self, source: Path, value: str):
        relative_path, _, anchor = value.partition("#")
        target = (source.parent / relative_path).resolve()
        self.assertTrue(target.is_file(), f"{source}: missing target {value}")
        if anchor:
            self.assertIn(
                anchor,
                validate_skill_quality.github_heading_slugs(target),
                f"{source}: missing anchor {value}",
            )

    def test_capability_links_and_anchors_resolve(self):
        for path in [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.rglob("*.md"))]:
            for target in local_markdown_targets(path):
                with self.subTest(source=path.relative_to(SKILL_ROOT), target=target):
                    self.assert_target_exists(path, target)

    def test_backticked_entrypoint_references_resolve(self):
        entrypoint = SKILL_ROOT / "SKILL.md"
        for value in REFERENCE_PATH.findall(entrypoint.read_text(encoding="utf-8")):
            with self.subTest(value=value):
                self.assert_target_exists(entrypoint, value)

    def test_reference_owners_are_in_the_maintenance_map(self):
        ownership = (SKILL_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for path in REFERENCES.rglob("*.md"):
            relative = path.relative_to(SKILL_ROOT).as_posix()
            with self.subTest(reference=relative):
                self.assertIn(f"`{relative}`", ownership)

    def test_learning_report_uses_the_current_analytics_capability(self):
        report_reference = (
            REPO_ROOT / "skills" / "ai-shifu-learning-report" / "references"
            / "data-collection-and-privacy.md"
        )
        content = report_reference.read_text(encoding="utf-8")
        self.assertIn("ai-shifu-course-creator/references/analytics/overview.md", content)
        self.assertNotIn("ai-shifu-course-creator/references/analytics/workflow.md", content)
        for target in re.findall(r"`([^`]+\.md(?:#[^`]+)?)`", content):
            if "ai-shifu-course-creator/" in target:
                self.assert_target_exists(report_reference, target)

    def test_removed_coordinators_have_no_active_reference_links(self):
        removed_paths = (
            "authoring-mode.md",
            "orchestration-workflow.md",
            "analytics/workflow.md",
        )
        for path in [SKILL_ROOT / "SKILL.md", SKILL_ROOT / "AGENTS.md", *REFERENCES.rglob("*.md")]:
            content = path.read_text(encoding="utf-8")
            for removed in removed_paths:
                with self.subTest(source=path.relative_to(SKILL_ROOT), removed=removed):
                    self.assertNotIn(removed, content)


if __name__ == "__main__":
    unittest.main()
