from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-shifu-course-creator"
sys.path.insert(0, str(REPO_ROOT / "tools" / "ai-shifu-skill-release" / "scripts"))

from ai_shifu_release.artifacts import is_excluded


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
            "course-design-choices.md",
            "course-structure.md",
            "teaching-design.md",
            "markdownflow-syntax.md",
            "teaching-prompt.md",
            "course-prompt.md",
            "course-description.md",
            "course-review.md",
            "image-authoring.md",
            "authentication.md",
            "course-lookup.md",
            "build-and-import.md",
            "course-sync.md",
            "course-management.md",
            "analytics/guide.md",
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

    def assert_retired_contract_absent(self, skill_root: Path):
        retired_contract = re.compile(
            r"%\{\{[^{}]*\}\}|"
            r"\b(?:global_variable_table|used_variables|collected_in|"
            r"effect_scope|var_variable_values|variable_bid)\b|"
            r"markdownflow-syntax\.md#(?:variables|pre-collection-references)\b|"
            r"authoring-contracts\.md#variable-table\b|"
            r"teaching-design\.md#variable-strategy\b",
            re.IGNORECASE,
        )
        runtime_references = re.compile(
            r"\{\{[^{}\n]*\}\}|^#{1,6}[ \t]+Variables?[ \t]*$",
            re.IGNORECASE | re.MULTILINE,
        )
        for path in sorted(skill_root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            relative = PurePosixPath(path.relative_to(skill_root).as_posix())
            # Evals are maintained source even though release archives omit them.
            release_path = (
                PurePosixPath(*relative.parts[1:])
                if relative.parts[0] == "evals"
                else relative
            )
            if is_excluded(release_path):
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            match = retired_contract.search(content)
            if not match and relative.as_posix() == "references/markdownflow-syntax.md":
                match = runtime_references.search(content)
            if match:
                self.fail(
                    f"Retired learner-state contract in {relative}: {match.group(0)!r}"
                )

    def test_package_retires_the_named_learner_state_contract(self):
        self.assert_retired_contract_absent(SKILL_ROOT)

    def test_contract_scan_allows_other_domains_and_skips_runtime_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_root = Path(tmp)
            sources = {
                ".env": "SENSITIVE_TOKEN=canary global_variable_table",
                ".update-check.json": '{"used_variables": []}',
                "evals/.env": "%{{private_key}}",
                ".env.example": "# Configure environment variables here.",
                "references/other-template.md": (
                    "An environment variable is configuration.\n"
                    "Jekyll 使用模板变量 {{ site.title }}。\n"
                ),
                "evals/other-template.json": '{"query": "Render {{ page.title }}"}',
            }
            for name, content in sources.items():
                path = skill_root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            self.assert_retired_contract_absent(skill_root)

    def test_contract_scan_rejects_retired_source_with_short_errors(self):
        cases = (
            ("evals/case.json", '{"used_variables": []}'),
            ("references/lesson.md", "?[%{{learner_goal}} ...Goal]"),
            ("references/analytics/tables.md", "var_variable_values"),
            ("references/markdownflow-syntax.md", "Read {{learner_goal}}."),
            ("references/consumer.md", "markdownflow-syntax.md#variables"),
        )
        for name, content in cases:
            with self.subTest(source=name), tempfile.TemporaryDirectory() as tmp:
                skill_root = Path(tmp)
                path = skill_root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("source_secret_canary\n" + content, encoding="utf-8")

                with self.assertRaises(AssertionError) as error:
                    self.assert_retired_contract_absent(skill_root)
                self.assertIn(name, str(error.exception))
                self.assertNotIn("source_secret_canary", str(error.exception))


if __name__ == "__main__":
    unittest.main()
