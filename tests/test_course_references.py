from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_skill_quality  # noqa: E402


SKILL_ROOT = REPO_ROOT / "skills" / "ai-shifu-course-creator"
REFERENCES = SKILL_ROOT / "references"
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
REFERENCE_PATH = re.compile(r"`(references/[A-Za-z0-9_./-]+\.md(?:#[A-Za-z0-9-]+)?)`")
BACKTICKED_NAVIGATION_PATH = re.compile(
    r"`((?:\.\.?/)*(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.md"
    r"(?:#[A-Za-z0-9-]+)?)`"
)
NAVIGATION_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
INLINE_CODE = re.compile(r"(?<!`)(`+).*?\1(?!`)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def markdown_link_targets(content: str) -> list[str]:
    return [
        target
        for target in MARKDOWN_LINK.findall(INLINE_CODE.sub("", content))
        if ".md" in target and "://" not in target
    ]


def local_markdown_targets(path: Path) -> list[str]:
    text = validate_skill_quality.markdown_without_fenced_code_or_html_comments(
        path.read_text(encoding="utf-8")
    )
    return markdown_link_targets(text)


def active_reference_targets(content: str) -> list[str]:
    text = validate_skill_quality.markdown_without_fenced_code_or_html_comments(content)
    targets = markdown_link_targets(text)
    for line in text.splitlines():
        if NAVIGATION_ITEM.match(line):
            targets.extend(BACKTICKED_NAVIGATION_PATH.findall(line))
    return targets


def related_guidance_targets(content: str) -> list[str]:
    text = validate_skill_quality.markdown_without_fenced_code_or_html_comments(content)
    guidance_lines: list[str] = []
    section_level: int | None = None
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            if section_level is not None and level <= section_level:
                section_level = None
            if heading.group(2) == "Related Guidance":
                section_level = level
        if section_level is not None:
            guidance_lines.append(line)
    return active_reference_targets("\n".join(guidance_lines))


class ReferenceTargetParsingTests(unittest.TestCase):
    def test_links_and_relative_navigation_paths_are_active(self):
        content = """[Guidance](references/guide.md#inputs)
- `../authentication.md` establishes access.
* When needed: `analytics/guide.md#queries`
1. `./local.md`
2) `nested/example.md` and `other.md#output`
"""
        self.assertEqual(
            active_reference_targets(content),
            [
                "references/guide.md#inputs",
                "../authentication.md",
                "analytics/guide.md#queries",
                "./local.md",
                "nested/example.md",
                "other.md#output",
            ],
        )

    def test_examples_comments_and_prose_are_not_navigation(self):
        content = """Historical guidance mentioned `old-guide.md` and analytics/old.md.
An inline example is `[Example](inline-example.md)`.
``[Another example](double-backtick-example.md)``
[External](https://example.org/external.md)
```markdown
- `fenced-navigation.md`
[Example](fenced-link.md)
```
~~~markdown
- `tilde-fenced.md`
~~~
<!--
- `commented-navigation.md`
[Comment](commented-link.md)
-->
- `active.md` <!-- [Comment](inline-comment.md) -->
Ordinary prose can still contain an active [link](active-link.md).
"""
        self.assertEqual(
            active_reference_targets(content), ["active-link.md", "active.md"]
        )

    def test_related_guidance_excludes_artifact_lists_in_other_sections(self):
        content = """# Capability
## Related Guidance
- `../guide.md#inputs`
### Additional references
- `analytics/guide.md`
## Output
- `lesson.md` is an authored artifact.
```markdown
## Related Guidance
- `example.md`
```
"""
        self.assertEqual(
            related_guidance_targets(content),
            ["../guide.md#inputs", "analytics/guide.md"],
        )


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

    def test_related_guidance_links_and_anchors_resolve(self):
        for path in sorted(REFERENCES.rglob("*.md")):
            for target in related_guidance_targets(path.read_text(encoding="utf-8")):
                with self.subTest(source=path.relative_to(SKILL_ROOT), target=target):
                    self.assert_target_exists(path, target)

    def test_navigation_validation_rejects_missing_files_and_anchors(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "capability.md"
            (source.parent / "guide.md").write_text("# Inputs\n", encoding="utf-8")
            cases = [
                ("missing.md#inputs", "missing target"),
                ("guide.md#missing", "missing anchor"),
            ]
            for target, error in cases:
                source.write_text(
                    f"# Capability\n\n## Related Guidance\n\n- `{target}`\n",
                    encoding="utf-8",
                )
                with self.subTest(target=target):
                    targets = related_guidance_targets(source.read_text(encoding="utf-8"))
                    self.assertEqual(targets, [target])
                    with self.assertRaisesRegex(AssertionError, error):
                        self.assert_target_exists(source, targets[0])

    def test_reference_owners_are_in_the_maintenance_map(self):
        ownership = (SKILL_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for path in REFERENCES.rglob("*.md"):
            relative = path.relative_to(SKILL_ROOT).as_posix()
            with self.subTest(reference=relative):
                self.assertIn(f"`{relative}`", ownership)

    def test_learning_report_uses_the_current_analytics_capability(self):
        report_reference = (
            REPO_ROOT / "skills" / "ai-shifu-learning-report" / "references"
            / "data-collection.md"
        )
        content = report_reference.read_text(encoding="utf-8")
        self.assertIn("ai-shifu-course-creator/references/analytics/guide.md", content)
        self.assertNotIn("ai-shifu-course-creator/references/analytics/workflow.md", content)
        for target in re.findall(r"`([^`]+\.md(?:#[^`]+)?)`", content):
            if "ai-shifu-course-creator/" in target:
                self.assert_target_exists(report_reference, target)

    def assert_no_removed_coordinator_targets(self, source: Path, content: str):
        removed_paths = {
            (REFERENCES / relative).resolve()
            for relative in (
                "authoring-mode.md",
                "orchestration-workflow.md",
                "analytics/workflow.md",
            )
        }
        for value in active_reference_targets(content):
            target = (source.parent / value.partition("#")[0]).resolve()
            self.assertNotIn(
                target,
                removed_paths,
                f"{source}: active reference to removed coordinator {value}",
            )

    def test_removed_coordinator_validation_resolves_relative_navigation(self):
        source = REFERENCES / "analytics" / "capability.md"
        targets = (
            "workflow.md",
            "./workflow.md#queries",
            "../analytics/workflow.md",
            "../analytics/../analytics/workflow.md",
            "../authoring-mode.md",
            "../../references/orchestration-workflow.md",
        )
        for target in targets:
            content = f"# Capability\n\n## More capabilities\n\n- `{target}`\n"
            with self.subTest(target=target):
                with self.assertRaisesRegex(AssertionError, "removed coordinator"):
                    self.assert_no_removed_coordinator_targets(source, content)

    def test_removed_coordinator_validation_allows_different_target_paths(self):
        source = REFERENCES / "analytics" / "capability.md"
        content = """# Capability
## More capabilities
- `examples/analytics/workflow.md`
- `examples/authoring-mode.md`
"""
        self.assert_no_removed_coordinator_targets(source, content)

    def test_removed_coordinators_have_no_active_reference_links(self):
        for path in [SKILL_ROOT / "SKILL.md", SKILL_ROOT / "AGENTS.md", *REFERENCES.rglob("*.md")]:
            with self.subTest(source=path.relative_to(SKILL_ROOT)):
                self.assert_no_removed_coordinator_targets(path, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
