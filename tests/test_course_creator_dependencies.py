from __future__ import annotations

import re
import sys
import unittest
from collections.abc import Iterable
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_skill_quality  # noqa: E402


SKILL_ROOT = REPO_ROOT / "skills" / "ai-shifu-course-creator"
REFERENCES = SKILL_ROOT / "references"
SKILL_MD = SKILL_ROOT / "SKILL.md"
DEPENDENCY_ITEM = re.compile(r"^- `([^`]+\.md(?:#[^`]+)?)`$")


def markdown_h2_section(markdown: str, title: str) -> str | None:
    lines = markdown.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line == f"## {title}":
            start = index + 1
            break
    if start is None:
        return None

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def declared_paths(markdown: str, section: str) -> list[str]:
    body = markdown_h2_section(markdown, section)
    if body is None:
        return []
    if body == "None.":
        return []

    dependencies = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if section == "Required References":
            match = DEPENDENCY_ITEM.fullmatch(line)
            values = [match.group(1)] if match else []
        else:
            values = re.findall(r"`([^`]+\.md(?:#[^`]+)?)`", line)
            if not line.startswith("- "):
                values = []
        if len(values) != 1:
            raise AssertionError(
                f"{section} accepts only bullets containing exactly one "
                f"backticked Markdown path; got {line!r}"
            )
        dependencies.append(values[0])
    return dependencies


def route_line(markdown: str, intent_prefix: str) -> str:
    for line in markdown_h2_section(markdown, "Task Router").splitlines():
        if line.startswith(f"| {intent_prefix}"):
            return line
    raise AssertionError(f"missing route for {intent_prefix!r}")


def route_paths(markdown: str, intent_prefix: str) -> list[str]:
    return [
        value
        for value in re.findall(r"`([^`]+\.md(?:#[^`]+)?)`", route_line(markdown, intent_prefix))
        if value.startswith("references/")
    ]


def split_reference(value: str) -> tuple[str, str | None]:
    path, separator, anchor = value.partition("#")
    return path, anchor if separator else None


def resolve_reference(source: Path, value: str) -> tuple[Path, str | None]:
    path_value, anchor = split_reference(value)
    if path_value.startswith("references/"):
        path_value = path_value.removeprefix("references/")

    raw_path = Path(path_value)
    candidates = [source.parent / raw_path, REFERENCES / raw_path]
    resolved_candidates = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file() and resolved not in resolved_candidates:
            resolved_candidates.append(resolved)

    if not resolved_candidates:
        raise AssertionError(f"{source} declares missing reference {value!r}")
    if len(resolved_candidates) > 1:
        raise AssertionError(f"{source} declares ambiguous reference {value!r}")
    target = resolved_candidates[0]
    if REFERENCES.resolve() not in target.parents:
        raise AssertionError(f"{source} declares out-of-tree reference {value!r}")
    return target, anchor


def dependency_graph() -> dict[Path, list[Path]]:
    graph = {}
    for path in sorted(REFERENCES.rglob("*.md")):
        markdown = path.read_text(encoding="utf-8")
        dependencies = []
        for value in declared_paths(markdown, "Required References"):
            target, anchor = resolve_reference(path, value)
            if anchor is not None:
                anchors = validate_skill_quality.github_heading_slugs(target)
                if anchor not in anchors:
                    raise AssertionError(
                        f"{path} declares missing anchor {value!r}"
                    )
            dependencies.append(target)
        graph[path.resolve()] = dependencies
    return graph


def transitive_closure(
    roots: Iterable[Path], graph: dict[Path, list[Path]]
) -> set[Path]:
    closure: set[Path] = set()
    pending = [path.resolve() for path in roots]
    while pending:
        path = pending.pop()
        if path in closure:
            continue
        closure.add(path)
        pending.extend(graph[path])
    return closure


class CourseCreatorDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = SKILL_MD.read_text(encoding="utf-8")

    def route_roots(self, intent_prefix: str) -> list[Path]:
        roots = []
        for value in route_paths(self.router, intent_prefix):
            target, anchor = resolve_reference(SKILL_MD, value)
            if anchor is not None:
                anchors = validate_skill_quality.github_heading_slugs(target)
                self.assertIn(anchor, anchors, f"missing route anchor: {value}")
            roots.append(target)
        return roots

    def test_every_reference_starts_with_required_references_contract(self):
        for path in sorted(REFERENCES.rglob("*.md")):
            markdown = path.read_text(encoding="utf-8")
            h2_headings = re.findall(r"^## (.+)$", markdown, re.MULTILINE)
            with self.subTest(path=path.relative_to(REFERENCES)):
                self.assertTrue(h2_headings, "reference must have an H2 heading")
                self.assertEqual("Required References", h2_headings[0])
                declared_paths(markdown, "Required References")
                declared_paths(markdown, "Conditional References")

    def test_required_reference_targets_and_anchors_exist(self):
        graph = dependency_graph()
        self.assertEqual(
            len(list(REFERENCES.rglob("*.md"))),
            len(graph),
        )
        for source in graph:
            markdown = source.read_text(encoding="utf-8")
            for value in declared_paths(markdown, "Conditional References"):
                target, anchor = resolve_reference(source, value)
                if anchor is not None:
                    self.assertIn(
                        anchor,
                        validate_skill_quality.github_heading_slugs(target),
                        f"missing conditional-reference anchor: {value}",
                    )

    def test_required_reference_graph_is_a_dag(self):
        graph = dependency_graph()
        active: list[Path] = []
        complete: set[Path] = set()

        def visit(path: Path) -> None:
            if path in complete:
                return
            if path in active:
                cycle = active[active.index(path) :] + [path]
                names = " -> ".join(
                    str(item.relative_to(REFERENCES)) for item in cycle
                )
                self.fail(f"required-reference cycle: {names}")
            active.append(path)
            for dependency in graph[path]:
                visit(dependency)
            active.pop()
            complete.add(path)

        for path in graph:
            visit(path)

    def test_router_paths_resolve_without_loading_plain_markdown_links(self):
        for line in markdown_h2_section(self.router, "Task Router").splitlines():
            if not line.startswith("| ") or "Required files" in line:
                continue
            for value in re.findall(r"`([^`]+\.md(?:#[^`]+)?)`", line):
                if value.startswith("references/"):
                    resolve_reference(SKILL_MD, value)

        sample = (
            "# Example\n\n"
            "## Required References\n\n"
            "  - `prompt-contracts.md`  \n\n"
            "## Notes\n\n"
            "See [ordinary navigation](pedagogy.md).\n\n"
            "## Conditional References\n\n"
            "  - When images are present: `image-authoring.md`  \n"
        )
        self.assertEqual(
            ["prompt-contracts.md"],
            declared_paths(sample, "Required References"),
        )
        self.assertEqual(
            ["image-authoring.md"],
            declared_paths(sample, "Conditional References"),
        )

    def test_full_course_closure_excludes_unrelated_routes_and_images(self):
        graph = dependency_graph()
        closure = transitive_closure(
            self.route_roots("Create a full course"), graph
        )
        relative_paths = {
            str(path.relative_to(REFERENCES)) for path in closure
        }

        self.assertFalse(
            any(path.startswith("analytics/") for path in relative_paths)
        )
        self.assertTrue(
            {
                "segmentation-workflow.md",
                "orchestration-workflow.md",
                "teaching-prompt.md",
                "course-prompt.md",
                "course-description.md",
                "optimization-workflow.md",
                "deployment-workflow.md",
            }.issubset(relative_paths)
        )
        self.assertTrue(
            {
                "course-sync.md",
                "course-management.md",
                "image-authoring.md",
            }.isdisjoint(relative_paths)
        )

    def test_offline_prompt_audit_closure_excludes_platform_access(self):
        graph = dependency_graph()
        roots = self.route_roots("Review or audit pasted")
        checklist = (REFERENCES / "optimization-checklist.md").resolve()
        teaching_prompt = None
        for value in declared_paths(
            checklist.read_text(encoding="utf-8"),
            "Conditional References",
        ):
            target, _ = resolve_reference(checklist, value)
            if target.name == "teaching-prompt.md":
                teaching_prompt = target
                break
        self.assertIsNotNone(
            teaching_prompt,
            "offline Teaching Prompt audit needs a declared conditional owner",
        )

        closure = transitive_closure([*roots, teaching_prompt], graph)
        relative_paths = {
            str(path.relative_to(REFERENCES)) for path in closure
        }
        self.assertTrue(
            {
                "optimization-workflow.md",
                "teaching-prompt.md",
                "prompt-contracts.md",
                "pedagogy.md",
                "markdownflow-authoring.md",
                "markdownflow.md",
            }.issubset(relative_paths)
        )
        self.assertTrue(
            {
                "authentication.md",
                "course-target.md",
                "deployment-workflow.md",
                "course-sync.md",
                "course-management.md",
                "course-prompt.md",
                "course-description.md",
                "image-authoring.md",
                "source-preservation.md",
            }.isdisjoint(relative_paths)
        )
        self.assertFalse(
            any(path.startswith("analytics/") for path in relative_paths)
        )

    def test_local_course_prompt_closure_excludes_platform_access(self):
        graph = dependency_graph()
        closure = transitive_closure(
            self.route_roots("Create or revise a Course Prompt"), graph
        )
        relative_paths = {
            str(path.relative_to(REFERENCES)) for path in closure
        }
        self.assertIn("course-prompt.md", relative_paths)
        self.assertIn("course-design-intake.md", relative_paths)
        self.assertTrue(
            {
                "authentication.md",
                "course-target.md",
                "course-sync.md",
                "course-management.md",
                "deployment-workflow.md",
                "pedagogy.md",
            }.isdisjoint(relative_paths)
        )

    def test_raw_local_teaching_prompt_closure_stays_authoring_only(self):
        graph = dependency_graph()
        closure = transitive_closure(
            self.route_roots(
                "Produce local Teaching Prompts from raw supplied material"
            ),
            graph,
        )
        relative_paths = {
            str(path.relative_to(REFERENCES)) for path in closure
        }
        self.assertTrue(
            {
                "segmentation-workflow.md",
                "teaching-prompt.md",
                "pedagogy.md",
                "markdownflow-authoring.md",
            }.issubset(relative_paths)
        )
        self.assertTrue(
            {
                "authentication.md",
                "course-target.md",
                "orchestration-workflow.md",
                "course-prompt.md",
                "course-description.md",
                "deployment-workflow.md",
            }.isdisjoint(relative_paths)
        )

    def test_local_full_course_closure_excludes_platform_access(self):
        graph = dependency_graph()
        closure = transitive_closure(
            self.route_roots("Produce a complete course locally"), graph
        )
        relative_paths = {
            str(path.relative_to(REFERENCES)) for path in closure
        }
        self.assertTrue(
            {
                "segmentation-workflow.md",
                "orchestration-workflow.md",
                "teaching-prompt.md",
                "course-prompt.md",
                "course-description.md",
                "optimization-workflow.md",
                "cli/course-directory-spec.md",
            }.issubset(relative_paths)
        )
        self.assertTrue(
            {
                "authentication.md",
                "course-target.md",
                "deployment-workflow.md",
                "course-sync.md",
                "course-management.md",
            }.isdisjoint(relative_paths)
        )

    def test_existing_structural_edit_uses_sync_not_new_deployment(self):
        graph = dependency_graph()
        closure = transitive_closure(
            self.route_roots("Restructure an existing platform course"),
            graph,
        )
        relative_paths = {
            str(path.relative_to(REFERENCES)) for path in closure
        }
        self.assertIn("course-sync.md", relative_paths)
        self.assertIn("course-management.md", relative_paths)
        self.assertNotIn("deployment-workflow.md", relative_paths)

    def test_structure_planning_route_loads_orchestration_finalizer(self):
        route = route_line(self.router, "Plan course structure")
        self.assertIn("segmentation-workflow.md", route)
        self.assertIn(
            "orchestration-workflow.md#lesson-structure-finalization",
            route,
        )

    def test_existing_course_prompt_update_uses_management_not_content_push(self):
        route = route_line(
            self.router,
            "Create or revise a Course Prompt in an existing",
        )
        self.assertIn("course-sync.md#pull-before-editing", route)
        self.assertNotIn("course-sync.md#push-existing-course-content", route)
        graph = dependency_graph()
        closure = transitive_closure(
            self.route_roots("Create or revise a Course Prompt in an existing"),
            graph,
        )
        relative_paths = {
            str(path.relative_to(REFERENCES)) for path in closure
        }
        self.assertIn("course-design-intake.md", relative_paths)
        self.assertIn("course-management.md", relative_paths)
        self.assertNotIn("deployment-workflow.md", relative_paths)

    def test_image_authoring_is_conditional_not_a_strong_dependency(self):
        graph = dependency_graph()
        image_authoring = (REFERENCES / "image-authoring.md").resolve()
        strong_consumers = {
            source for source, dependencies in graph.items() if image_authoring in dependencies
        }
        conditional_consumers = set()
        for source in graph:
            markdown = source.read_text(encoding="utf-8")
            for value in declared_paths(markdown, "Conditional References"):
                target, _ = resolve_reference(source, value)
                if target == image_authoring:
                    conditional_consumers.add(source)

        self.assertEqual(set(), strong_consumers)
        self.assertTrue(
            conditional_consumers,
            "at least one authoring guide must conditionally load image-authoring.md",
        )

    def test_optimization_artifact_owners_are_scope_conditional(self):
        graph = dependency_graph()
        checklist = (REFERENCES / "optimization-checklist.md").resolve()
        required_names = {
            path.name for path in graph[checklist]
        }
        self.assertTrue(
            {
                "teaching-prompt.md",
                "course-prompt.md",
                "course-description.md",
                "pedagogy.md",
                "markdownflow-authoring.md",
            }.isdisjoint(required_names)
        )
        conditional_names = set()
        markdown = checklist.read_text(encoding="utf-8")
        for value in declared_paths(markdown, "Conditional References"):
            target, _ = resolve_reference(checklist, value)
            conditional_names.add(target.name)
        self.assertTrue(
            {
                "teaching-prompt.md",
                "course-prompt.md",
                "course-description.md",
                "image-authoring.md",
            }.issubset(conditional_names)
        )


if __name__ == "__main__":
    unittest.main()
