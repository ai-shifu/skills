from __future__ import annotations

import ast
import json
import re
import subprocess
import unittest
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_RELATIVE_ROOT = Path("skills/ai-shifu-course-creator")
SKILL_ROOT = REPO_ROOT / SKILL_RELATIVE_ROOT

MARKDOWN_LINK = re.compile(
    r"!?\[[^\]\n]*\]\((?P<target><[^>\n]+>|[^\s)\n]+)"
)
INLINE_CODE = re.compile(r"(?<!`)`(?P<code>[^`\n]+)`(?!`)")
CODE_PATH = re.compile(
    r"(?:\{skillDir\}/|\.\.?/|(?:references|examples|scripts|evals)/)?"
    r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.{}<>*-]+)*"
    r"(?:\.md|\.py|\.json|\.txt)"
    r"(?:#[A-Za-z0-9_.-]+)?"
)

# These names commonly describe generated course-directory artifacts rather than
# files in the skill. A Markdown link is still authoritative; only ambiguous bare
# code spans are ignored.
GENERATED_ARTIFACT_NAMES = frozenset(
    {
        "README.md",
        "course-description.md",
        "course-prompt.md",
        "lesson-*.md",
        "structure.json",
        "course-config.json",
        "image-manifest.json",
        "shifu-import.json",
    }
)

AUTHORING_RANKS = {
    Path("references/session-controls.md"): 0,
    Path("references/markdownflow.md"): 0,
    Path("references/course-prompt.md"): 1,
    Path("references/data-contracts.md"): 2,
    Path("references/pedagogy.md"): 3,
    Path("references/delivery-modes.md"): 4,
    Path("references/prompt-contracts.md"): 5,
    Path("references/authoring-intake.md"): 5,
    Path("references/image-assets.md"): 5,
    Path("references/review-checklist.md"): 6,
    Path("references/generation-workflow.md"): 7,
    Path("references/optimization-workflow.md"): 7,
    Path("references/segmentation-orchestration.md"): 8,
    Path("references/authoring-controls.md"): 9,
    Path("examples/fallback-mode.md"): 10,
    Path("examples/pipeline-full.md"): 10,
    Path("examples/deploy-only.md"): 11,
    Path("examples/generation-only.md"): 11,
    Path("examples/optimization-only.md"): 11,
    Path("examples/segmentation-only.md"): 11,
    Path("SKILL.md"): 12,
}

ANALYTICS_RANKS = {
    Path("references/analytics/tables.md"): 0,
    Path("references/analytics/dsl.md"): 1,
    Path("references/analytics/privacy-and-presentation.md"): 2,
    Path("references/analytics/recipes.md"): 3,
    Path("references/analytics/overview.md"): 4,
    Path("references/analytics/workflow.md"): 5,
    Path("SKILL.md"): 6,
}

PLATFORM_RANKS = {
    Path("references/cli/course-directory-spec.md"): 0,
    Path("references/cli/cli-reference.md"): 1,
    Path("references/authentication.md"): 2,
    Path("references/course-target.md"): 3,
    Path("references/image-assets.md"): 3,
    Path("references/deployment-workflow.md"): 4,
    Path("examples/deploy-only.md"): 5,
    Path("SKILL.md"): 6,
}

# Presentation-only output formatting is intentionally independent from the
# authoring, platform, and analytics authority stacks. Keep this exception
# explicit so a newly added reference cannot silently escape classification.
ARCHITECTURE_NEUTRAL_REFERENCES = {
    Path("references/report-template.md"),
}

REQUIRED_EDGES = {
    Path("examples/optimization-only.md"): {
        Path("examples/pipeline-full.md"),
    },
    Path("references/data-contracts.md"): {
        Path("references/course-prompt.md"),
        Path("references/markdownflow.md"),
        Path("references/session-controls.md"),
    },
    Path("references/pedagogy.md"): {
        Path("references/course-prompt.md"),
        Path("references/data-contracts.md"),
        Path("references/markdownflow.md"),
    },
    Path("references/delivery-modes.md"): {
        Path("references/course-prompt.md"),
        Path("references/data-contracts.md"),
        Path("references/markdownflow.md"),
        Path("references/pedagogy.md"),
    },
    Path("references/prompt-contracts.md"): {
        Path("references/course-prompt.md"),
        Path("references/data-contracts.md"),
        Path("references/delivery-modes.md"),
        Path("references/markdownflow.md"),
        Path("references/pedagogy.md"),
        Path("references/session-controls.md"),
    },
    Path("references/authoring-intake.md"): {
        Path("references/course-target.md"),
        Path("references/data-contracts.md"),
        Path("references/delivery-modes.md"),
        Path("references/pedagogy.md"),
    },
    Path("references/review-checklist.md"): {
        Path("references/course-prompt.md"),
        Path("references/data-contracts.md"),
        Path("references/delivery-modes.md"),
        Path("references/image-assets.md"),
        Path("references/markdownflow.md"),
        Path("references/pedagogy.md"),
        Path("references/prompt-contracts.md"),
        Path("references/session-controls.md"),
    },
    Path("references/generation-workflow.md"): {
        Path("references/data-contracts.md"),
        Path("references/delivery-modes.md"),
        Path("references/image-assets.md"),
        Path("references/pedagogy.md"),
        Path("references/prompt-contracts.md"),
        Path("references/review-checklist.md"),
    },
    Path("references/optimization-workflow.md"): {
        Path("references/course-prompt.md"),
        Path("references/data-contracts.md"),
        Path("references/delivery-modes.md"),
        Path("references/markdownflow.md"),
        Path("references/pedagogy.md"),
        Path("references/prompt-contracts.md"),
        Path("references/review-checklist.md"),
        Path("references/session-controls.md"),
    },
    Path("references/segmentation-orchestration.md"): {
        Path("references/data-contracts.md"),
        Path("references/generation-workflow.md"),
        Path("references/markdownflow.md"),
        Path("references/pedagogy.md"),
        Path("references/review-checklist.md"),
    },
    Path("references/authoring-controls.md"): {
        Path("references/course-prompt.md"),
        Path("references/data-contracts.md"),
        Path("references/delivery-modes.md"),
        Path("references/image-assets.md"),
        Path("references/markdownflow.md"),
        Path("references/pedagogy.md"),
        Path("references/prompt-contracts.md"),
        Path("references/review-checklist.md"),
        Path("references/session-controls.md"),
    },
    Path("references/analytics/dsl.md"): {
        Path("references/analytics/tables.md"),
    },
    Path("references/analytics/privacy-and-presentation.md"): {
        Path("references/analytics/dsl.md"),
        Path("references/analytics/tables.md"),
    },
    Path("references/analytics/recipes.md"): {
        Path("references/analytics/dsl.md"),
        Path("references/analytics/privacy-and-presentation.md"),
        Path("references/analytics/tables.md"),
        Path("references/cli/cli-reference.md"),
    },
    Path("references/analytics/overview.md"): {
        Path("references/analytics/recipes.md"),
    },
    Path("references/analytics/workflow.md"): {
        Path("references/analytics/overview.md"),
        Path("references/authentication.md"),
        Path("references/cli/cli-reference.md"),
    },
    Path("references/cli/cli-reference.md"): {
        Path("references/analytics/dsl.md"),
        Path("references/cli/course-directory-spec.md"),
    },
    Path("references/authentication.md"): {
        Path("references/cli/cli-reference.md"),
    },
    Path("references/image-assets.md"): {
        Path("references/authentication.md"),
        Path("references/cli/cli-reference.md"),
        Path("references/delivery-modes.md"),
        Path("references/markdownflow.md"),
        Path("references/pedagogy.md"),
    },
    Path("references/deployment-workflow.md"): {
        Path("references/authentication.md"),
        Path("references/cli/cli-reference.md"),
        Path("references/cli/course-directory-spec.md"),
        Path("references/course-prompt.md"),
        Path("references/course-target.md"),
        Path("references/delivery-modes.md"),
        Path("references/image-assets.md"),
        Path("references/report-template.md"),
        Path("references/review-checklist.md"),
    },
}

EXAMPLE_AUTHORITIES = {
    Path("examples/deploy-only.md"): {
        Path("references/deployment-workflow.md"),
        Path("references/image-assets.md"),
    },
    Path("examples/fallback-mode.md"): {
        Path("references/authoring-controls.md"),
        Path("references/data-contracts.md"),
        Path("references/review-checklist.md"),
    },
    Path("examples/generation-only.md"): {
        Path("references/generation-workflow.md"),
    },
    Path("examples/optimization-only.md"): {
        Path("references/optimization-workflow.md"),
    },
    Path("examples/pipeline-full.md"): {
        Path("references/course-prompt.md"),
        Path("references/segmentation-orchestration.md"),
    },
    Path("examples/segmentation-only.md"): {
        Path("references/segmentation-orchestration.md"),
    },
}


def skill_files() -> set[Path]:
    """Return tracked and untracked non-ignored files relative to the skill root."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            str(SKILL_RELATIVE_ROOT),
        ],
        check=True,
        capture_output=True,
    )
    paths = set()
    for raw_path in result.stdout.decode("utf-8").split("\0"):
        if not raw_path:
            continue
        repo_path = Path(raw_path)
        skill_path = repo_path.relative_to(SKILL_RELATIVE_ROOT)
        if (SKILL_ROOT / skill_path).is_file():
            paths.add(skill_path)
    return paths


def without_fenced_code(markdown: str) -> str:
    """Remove fenced blocks while preserving line boundaries for inline parsing."""
    visible_lines: list[str] = []
    fence_character = ""
    fence_length = 0

    for line in markdown.splitlines(keepends=True):
        fence = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})", line)
        if fence:
            marker = fence.group(1)
            if not fence_character:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = ""
                fence_length = 0
            visible_lines.append("\n" if line.endswith("\n") else "")
            continue

        if fence_character:
            visible_lines.append("\n" if line.endswith("\n") else "")
        else:
            visible_lines.append(line)

    return "".join(visible_lines)


def code_span_targets(markdown: str) -> Iterable[str]:
    for match in INLINE_CODE.finditer(markdown):
        for path_match in CODE_PATH.finditer(match.group("code")):
            target = path_match.group(0)
            path_without_anchor = target.split("#", 1)[0]
            if (
                "/" not in path_without_anchor
                and "#" not in target
                and Path(path_without_anchor).name in GENERATED_ARTIFACT_NAMES
            ):
                continue
            if "<" in target or ">" in target or "*" in target:
                continue
            yield target


def is_explicit_skill_local_code_target(raw_target: str) -> bool:
    """Return whether a code span explicitly claims a skill-local file path."""
    target = unquote(raw_target.strip()).split("#", 1)[0].split("?", 1)[0]
    return target in {"SKILL.md", "CHANGELOG.md"} or target.startswith(
        (
            "{skillDir}/",
            "./",
            "../",
            "references/",
            "examples/",
            "scripts/",
            "evals/",
        )
    )


def resolve_skill_target(
    source: Path, raw_target: str, known_files: set[Path]
) -> Path | None:
    """Resolve one reference only when it names a real skill source file."""
    target = unquote(raw_target.strip())
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if not target or target.startswith(("#", "/", "mailto:")):
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
        return None

    target = target.split("#", 1)[0].split("?", 1)[0]
    if target.startswith("{skillDir}/"):
        candidate = SKILL_ROOT / target.removeprefix("{skillDir}/")
    elif target.startswith(("references/", "examples/", "scripts/", "evals/")):
        candidate = SKILL_ROOT / target
    elif target in {"SKILL.md", "CHANGELOG.md"}:
        candidate = SKILL_ROOT / target
    else:
        candidate = SKILL_ROOT / source.parent / target

    try:
        relative_target = candidate.resolve().relative_to(SKILL_ROOT.resolve())
    except ValueError:
        return None
    if relative_target not in known_files or not candidate.is_file():
        return None
    return relative_target


def behavioral_dependency_graph() -> dict[Path, set[Path]]:
    """Build the behavioral graph from real links, excluding runtime imports."""
    known_files = skill_files()
    graph = {path: set() for path in known_files}

    for source in known_files:
        if source.suffix != ".md":
            continue
        markdown = without_fenced_code(
            (SKILL_ROOT / source).read_text(encoding="utf-8")
        )
        raw_targets = [
            match.group("target") for match in MARKDOWN_LINK.finditer(markdown)
        ]
        raw_targets.extend(code_span_targets(markdown))
        for raw_target in raw_targets:
            target = resolve_skill_target(source, raw_target, known_files)
            if target is None or target == source:
                continue
            graph[source].add(target)

    return graph


def python_import_graph() -> dict[Path, set[Path]]:
    """Build the local Python import graph independently of documentation links."""
    python_files = {path for path in skill_files() if path.suffix == ".py"}
    modules = {path.stem: path for path in python_files}
    graph = {path: set() for path in python_files}

    for source in python_files:
        tree = ast.parse((SKILL_ROOT / source).read_text(encoding="utf-8"))
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module.split(".", 1)[0])
        for module in imported_modules:
            if module in modules and modules[module] != source:
                graph[source].add(modules[module])

    return graph


def python_file_reference_graph() -> dict[Path, set[Path]]:
    """Resolve simple literal references from Python sources to skill files."""
    known_files = skill_files()
    python_files = {path for path in known_files if path.suffix == ".py"}
    files_by_name: dict[str, set[Path]] = {}
    for path in known_files:
        files_by_name.setdefault(path.name, set()).add(path)

    graph = {path: set() for path in python_files}
    for source in python_files:
        tree = ast.parse((SKILL_ROOT / source).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if node.value in GENERATED_ARTIFACT_NAMES:
                continue
            candidates = files_by_name.get(node.value, set())
            if len(candidates) == 1:
                target = next(iter(candidates))
                if target != source:
                    graph[source].add(target)
    return graph


def complete_dependency_graph() -> dict[Path, set[Path]]:
    """Combine documentation, local imports, and literal source-file reads."""
    graph = behavioral_dependency_graph()
    for partial in (python_import_graph(), python_file_reference_graph()):
        for source, targets in partial.items():
            graph[source].update(targets)
    return graph


def rank_violations(
    graph: dict[Path, set[Path]], ranks: dict[Path, int]
) -> list[str]:
    violations = []
    for source, source_rank in ranks.items():
        for target in graph.get(source, set()):
            if target in ranks and source_rank <= ranks[target]:
                violations.append(
                    f"{source} (rank {source_rank}) -> "
                    f"{target} (rank {ranks[target]})"
                )
    return sorted(violations)


def strongly_connected_components(
    graph: dict[Path, set[Path]],
) -> list[set[Path]]:
    """Return Tarjan strongly connected components for the dependency graph."""
    next_index = 0
    indices: dict[Path, int] = {}
    lowlinks: dict[Path, int] = {}
    stack: list[Path] = []
    on_stack: set[Path] = set()
    components: list[set[Path]] = []

    def visit(node: Path) -> None:
        nonlocal next_index
        indices[node] = next_index
        lowlinks[node] = next_index
        next_index += 1
        stack.append(node)
        on_stack.add(node)

        for target in sorted(graph[node], key=str):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] != indices[node]:
            return
        component: set[Path] = set()
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.add(member)
            if member == node:
                break
        components.append(component)

    for node in sorted(graph, key=str):
        if node not in indices:
            visit(node)
    return components


def format_cycles(
    graph: dict[Path, set[Path]], components: Iterable[set[Path]]
) -> str:
    descriptions = []
    for component in sorted(
        components, key=lambda members: tuple(sorted(map(str, members)))
    ):
        members = ", ".join(sorted(map(str, component)))
        internal_edges = [
            f"{source} -> {target}"
            for source in sorted(component, key=str)
            for target in sorted(graph[source], key=str)
            if target in component
        ]
        descriptions.append(
            f"SCC [{members}]\n  edges: " + "; ".join(internal_edges)
        )
    return "\n".join(descriptions)


def read_skill_file(path: str) -> str:
    return (SKILL_ROOT / path).read_text(encoding="utf-8")


def markdown_heading_section(markdown: str, heading: str) -> str:
    """Return one heading body without depending on the quality-test helpers."""
    heading_match = re.search(
        rf"^(?P<marks>#+)\s+{re.escape(heading)}\s*$",
        markdown,
        flags=re.MULTILINE,
    )
    if heading_match is None:
        raise AssertionError(f"missing Markdown heading: {heading}")
    level = len(heading_match.group("marks"))
    following_heading = re.compile(
        rf"^#{{1,{level}}}\s+.+$", flags=re.MULTILINE
    )
    end_match = following_heading.search(markdown, heading_match.end())
    end = end_match.start() if end_match else len(markdown)
    return markdown[heading_match.end() : end]


def first_json_code_block(markdown: str) -> object:
    match = re.search(
        r"(?ms)^```json[ \t]*\n(?P<body>.*?)^```[ \t]*$", markdown
    )
    if match is None:
        raise AssertionError("missing fenced JSON block")
    return json.loads(match.group("body"))


class CourseCreatorDependencyTests(unittest.TestCase):
    def test_scanner_ignores_fences_and_generated_artifact_basenames(self):
        markdown = """Outside `references/data-contracts.md#output-contract`.
`README.md` and `course-prompt.md` are generated artifacts here.

```markdown
`references/pedagogy.md`
[Not a dependency](references/markdownflow.md)
```
"""

        visible_markdown = without_fenced_code(markdown)
        targets = set(code_span_targets(visible_markdown))

        self.assertEqual(
            targets, {"references/data-contracts.md#output-contract"}
        )
        self.assertNotIn("references/pedagogy.md", visible_markdown)
        self.assertNotIn("references/markdownflow.md", visible_markdown)

    def test_behavioral_dependencies_are_acyclic(self):
        graph = behavioral_dependency_graph()
        cycles = [
            component
            for component in strongly_connected_components(graph)
            if len(component) > 1
        ]

        self.assertEqual(
            cycles,
            [],
            "behavioral dependency cycles detected:\n" + format_cycles(graph, cycles),
        )

    def test_runtime_imports_are_acyclic(self):
        graph = python_import_graph()
        cycles = [
            component
            for component in strongly_connected_components(graph)
            if len(component) > 1
        ]

        self.assertEqual(
            cycles,
            [],
            "runtime import cycles detected:\n" + format_cycles(graph, cycles),
        )

    def test_complete_source_dependencies_are_acyclic(self):
        graph = complete_dependency_graph()
        cycles = [
            component
            for component in strongly_connected_components(graph)
            if len(component) > 1
        ]

        self.assertEqual(
            cycles,
            [],
            "complete source dependency cycles detected:\n"
            + format_cycles(graph, cycles),
        )

    def test_version_metadata_is_a_leaf_authority_and_matches_frontmatter(self):
        graph = complete_dependency_graph()
        shifu_cli = Path("scripts/shifu-cli.py")
        skill_update = Path("scripts/skill_update.py")
        version_metadata = Path("version-metadata.json")
        updater_source = (SKILL_ROOT / skill_update).read_text(encoding="utf-8")
        metadata = json.loads(
            (SKILL_ROOT / version_metadata).read_text(encoding="utf-8")
        )
        skill_source = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = skill_source.split("---", 2)[1]

        self.assertIn(skill_update, graph[shifu_cli])
        self.assertIn(version_metadata, graph[skill_update])
        self.assertEqual(graph[version_metadata], set())
        self.assertIn('SKILL_ROOT / "version-metadata.json"', updater_source)
        self.assertNotIn('SKILL_ROOT / "SKILL.md"', updater_source)
        self.assertRegex(frontmatter, rf"(?m)^version: {re.escape(metadata['version'])}$")
        self.assertRegex(
            frontmatter,
            rf"(?m)^version_management: {re.escape(metadata['version_management'])}$",
        )

    def test_documentation_dependencies_follow_declared_layers(self):
        graph = behavioral_dependency_graph()
        for name, ranks in (
            ("authoring", AUTHORING_RANKS),
            ("analytics", ANALYTICS_RANKS),
            ("platform", PLATFORM_RANKS),
        ):
            with self.subTest(domain=name):
                missing_files = sorted(set(ranks) - set(graph), key=str)
                violations = rank_violations(graph, ranks)
                self.assertEqual(missing_files, [], f"unscanned {name} files")
                self.assertEqual(
                    violations,
                    [],
                    f"{name} dependencies must point to a lower layer:\n"
                    + "\n".join(violations),
                )

    def test_every_reference_has_an_architecture_classification(self):
        references = {
            path
            for path in skill_files()
            if path.suffix == ".md" and path.parts[0] == "references"
        }
        classified = {
            path
            for ranks in (AUTHORING_RANKS, ANALYTICS_RANKS, PLATFORM_RANKS)
            for path in ranks
            if path.parts[0] == "references"
        }
        classified.update(ARCHITECTURE_NEUTRAL_REFERENCES)

        self.assertEqual(
            references - classified,
            set(),
            "reference files must join an authority layer or be explicitly neutral",
        )
        self.assertEqual(
            classified - references,
            set(),
            "architecture classifications must name real reference files",
        )

        graph = behavioral_dependency_graph()
        for neutral in ARCHITECTURE_NEUTRAL_REFERENCES:
            with self.subTest(neutral=str(neutral)):
                self.assertEqual(
                    graph[neutral],
                    set(),
                    "neutral references must remain dependency leaves",
                )

    def test_required_authority_edges_cannot_be_deleted(self):
        graph = behavioral_dependency_graph()
        missing = []
        for source, targets in REQUIRED_EDGES.items():
            for target in targets:
                if target not in graph.get(source, set()):
                    missing.append(f"{source} -> {target}")

        self.assertEqual(
            missing,
            [],
            "required authority links are missing:\n" + "\n".join(missing),
        )

    def test_reference_files_do_not_depend_on_examples(self):
        graph = behavioral_dependency_graph()
        reverse_edges = [
            f"{source} -> {target}"
            for source in sorted(graph, key=str)
            if source.parts[0] == "references"
            for target in sorted(graph[source], key=str)
            if target.parts[0] == "examples"
        ]

        self.assertEqual(
            reverse_edges,
            [],
            "reference files must not use examples as authorities:\n"
            + "\n".join(reverse_edges),
        )

    def test_examples_link_to_their_authorities(self):
        graph = behavioral_dependency_graph()
        language_authority = Path("references/session-controls.md")
        for example, authorities in sorted(
            EXAMPLE_AUTHORITIES.items(), key=lambda item: str(item[0])
        ):
            with self.subTest(example=str(example)):
                self.assertIn(language_authority, graph[example])
                self.assertTrue(
                    authorities.issubset(graph[example]),
                    f"{example} must link its authorities: "
                    f"{sorted(authorities - graph[example], key=str)}",
                )

        fallback_example = Path("examples/fallback-mode.md")
        for phase_example in (
            Path("examples/generation-only.md"),
            Path("examples/optimization-only.md"),
            Path("examples/segmentation-only.md"),
        ):
            with self.subTest(example=str(phase_example)):
                self.assertIn(fallback_example, graph[phase_example])

    def test_explicit_local_markdown_links_resolve(self):
        known_files = skill_files()
        unresolved = []
        for source in sorted(known_files, key=str):
            if source.suffix != ".md":
                continue
            markdown = without_fenced_code(
                (SKILL_ROOT / source).read_text(encoding="utf-8")
            )
            for match in MARKDOWN_LINK.finditer(markdown):
                raw_target = match.group("target")
                target_without_anchor = raw_target.strip("<>").split("#", 1)[0]
                if not target_without_anchor.lower().endswith(".md"):
                    continue
                if resolve_skill_target(source, raw_target, known_files) is None:
                    unresolved.append(f"{source} -> {raw_target}")

        self.assertEqual(
            unresolved,
            [],
            "local Markdown links do not resolve:\n" + "\n".join(unresolved),
        )

    def test_explicit_skill_local_code_span_references_resolve(self):
        known_files = skill_files()
        unresolved = []
        for source in sorted(known_files, key=str):
            if source.suffix != ".md":
                continue
            markdown = without_fenced_code(
                (SKILL_ROOT / source).read_text(encoding="utf-8")
            )
            for raw_target in code_span_targets(markdown):
                if not is_explicit_skill_local_code_target(raw_target):
                    continue
                if resolve_skill_target(source, raw_target, known_files) is None:
                    unresolved.append(f"{source} -> {raw_target}")

        self.assertEqual(
            unresolved,
            [],
            "skill-local code-span file references do not resolve:\n"
            + "\n".join(unresolved),
        )


class AuthoringResponsibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.references = {
            path: (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in skill_files()
            if path.suffix == ".md" and path.parts[0] == "references"
        }
        cls.session_controls = cls.references[
            Path("references/session-controls.md")
        ]
        cls.data_contracts = cls.references[
            Path("references/data-contracts.md")
        ]
        cls.pedagogy = cls.references[Path("references/pedagogy.md")]
        cls.delivery_modes = cls.references[
            Path("references/delivery-modes.md")
        ]
        cls.course_prompt = cls.references[
            Path("references/course-prompt.md")
        ]
        cls.generation = cls.references[
            Path("references/generation-workflow.md")
        ]
        cls.image_assets = cls.references[Path("references/image-assets.md")]
        cls.review = cls.references[
            Path("references/review-checklist.md")
        ]
        cls.authentication = cls.references[
            Path("references/authentication.md")
        ]
        cls.cli = cls.references[Path("references/cli/cli-reference.md")]
        cls.examples = {
            path: (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in skill_files()
            if path.suffix == ".md" and path.parts[0] == "examples"
        }

    def files_containing(self, pattern: str) -> list[Path]:
        regex = re.compile(pattern, flags=re.MULTILINE)
        return sorted(
            (path for path, text in self.references.items() if regex.search(text)),
            key=str,
        )

    def test_language_policy_and_term_table_have_one_owner(self):
        self.assertEqual(
            self.files_containing(r"^## Output Language$"),
            [Path("references/session-controls.md")],
        )
        self.assertEqual(
            self.files_containing(r"^\| Canonical term \|"),
            [Path("references/session-controls.md")],
        )
        self.assertNotRegex(
            self.data_contracts,
            r"(?m)^#{1,6} (?:Language Resolution|"
            r"Canonical Term Translation Table)$",
        )

    def test_delivery_modes_own_cross_artifact_overrides(self):
        pure_slides = markdown_heading_section(
            self.delivery_modes, "Pure Slides"
        )
        generation_redirect = markdown_heading_section(
            self.generation, "Slide-Only Generation Override"
        )

        self.assertEqual(
            self.files_containing(r"^## Pure Slides$"),
            [Path("references/delivery-modes.md")],
        )
        self.assertIn("### Teaching Prompt Override", pure_slides)
        self.assertIn("### Course Prompt Override", pure_slides)
        self.assertIn("### Listen Mode Override", pure_slides)
        self.assertNotRegex(self.pedagogy, r"(?m)^#{1,6} Pure Slides$")
        self.assertNotIn("Compatibility anchor", self.pedagogy)
        self.assertIn("delivery-modes.md#pure-slides", generation_redirect)
        self.assertLess(len(generation_redirect.split()), 25)

    def test_course_prompt_base_template_has_one_owner(self):
        expected_sections = (
            "Role",
            "Task",
            "Teaching Techniques",
            "Writing Style",
            "Format",
            "Slides",
        )
        template_match = re.search(
            r"(?ms)^## Fillable Template\s*$.*?^```markdown\s*$"
            r"(?P<template>.*?)^```\s*$",
            self.course_prompt,
        )
        self.assertIsNotNone(template_match)
        template = template_match.group("template")

        for section in expected_sections:
            with self.subTest(section=section):
                self.assertIn(f"# {section}", template)
                self.assertEqual(
                    self.files_containing(rf"^# {re.escape(section)}$"),
                    [Path("references/course-prompt.md")],
                )

        complete_examples = []
        for path, text in self.examples.items():
            headings = {
                match.group("title")
                for match in re.finditer(
                    r"(?m)^# (?P<title>Role|Task|Teaching Techniques|"
                    r"Writing Style|Format|Slides)[ \t]*$",
                    text,
                )
            }
            if headings == set(expected_sections):
                complete_examples.append(path)

        self.assertEqual(
            complete_examples,
            [],
            "examples must bind to the canonical Course Prompt template instead of copying it",
        )
        pipeline = self.examples[Path("examples/pipeline-full.md")]
        self.assertIn(
            "../references/course-prompt.md#fillable-template", pipeline
        )
        self.assertIn("Placeholder source", pipeline)

    def test_control_normalization_preserves_non_control_context(self):
        intake = self.references[Path("references/authoring-intake.md")]
        optimization = self.references[
            Path("references/optimization-workflow.md")
        ]

        self.assertIn("replace only those six raw fields", self.data_contracts)
        self.assertIn(
            "control normalization must not discard that remaining context",
            self.data_contracts,
        )
        self.assertIn("remaining normalized `course_profile` members", self.data_contracts)
        for context_field in (
            "course_material",
            "course_author_name",
            "course_profile",
            "delivery_constraints",
            "target_language",
        ):
            with self.subTest(context_field=context_field):
                self.assertIn(context_field, self.data_contracts)

        self.assertIn("Keep the remaining authoring context", intake)
        self.assertIn(
            "unchanged authoring context carried alongside the phase results",
            optimization,
        )

    def test_phase_handoffs_have_distinct_schemas(self):
        expected_fields = {
            "Segmentation Output": {
                "structured_segments_json",
                "preserve_block_index",
                "lesson_cut_candidates",
            },
            "Generation Output": {"lesson_teaching_prompts"},
            "Orchestration Output": {
                "authoring_run_controls",
                "lesson_teaching_prompts",
                "course_index",
                "global_variable_table",
            },
            "Optimization Output": {
                "risk_and_issue_report",
                "change_list",
                "lesson_teaching_prompts",
            },
            "Final Authoring Output": {
                "authoring_run_controls",
                "lesson_teaching_prompts",
                "course_index",
                "global_variable_table",
                "course_prompt",
                "course_description",
            },
        }

        for heading, fields in expected_fields.items():
            with self.subTest(heading=heading):
                section = markdown_heading_section(self.data_contracts, heading)
                documented = set(re.findall(r"`([a-z][a-z0-9_]*)`", section))
                self.assertTrue(
                    fields.issubset(documented),
                    f"{heading} is missing fields: {sorted(fields - documented)}",
                )

    def test_authentication_owns_agent_login_decisions(self):
        self.assertEqual(
            self.files_containing(r"^## Agent Login Flow$"),
            [Path("references/authentication.md")],
        )
        authentication_section = markdown_heading_section(
            self.authentication, "Agent Login Flow"
        )
        cli_authentication = markdown_heading_section(
            self.cli, "Authentication"
        )

        self.assertIn("third consecutive wrong code", authentication_section)
        self.assertIn("five SMS codes per day", authentication_section)
        self.assertIn("Conversation sequencing", cli_authentication)
        self.assertIn("outside this command contract", cli_authentication)
        self.assertNotIn("third consecutive wrong code", cli_authentication)
        self.assertNotIn("five SMS codes per day", cli_authentication)

    def test_sms_rate_limit_waits_for_existing_code_without_resending(self):
        authentication_section = markdown_heading_section(
            self.authentication, "Agent Login Flow"
        )

        self.assertIn("smsSendTooFrequent", authentication_section)
        self.assertIn("Wait up to 60 seconds for the original code", authentication_section)
        self.assertIn("end the current login attempt without resending", authentication_section)
        self.assertIn("tell the user to retry later", authentication_section)
        self.assertIn("only permitted automatic resend", authentication_section)
        self.assertIn("Third consecutive code error", authentication_section)

    def test_legacy_authoring_keys_have_one_normalization_owner(self):
        legacy_keys = {
            "chapter_hint",
            "generation_constraints",
            "teaching_constraints",
            "optimization_constraints",
        }
        for key in legacy_keys:
            with self.subTest(key=key):
                self.assertEqual(
                    self.files_containing(rf"\b{re.escape(key)}\b"),
                    [Path("references/data-contracts.md")],
                )

        examples = "\n".join(self.examples.values())
        outputs = self.data_contracts.split("## Output Contract", 1)[1]
        for key in legacy_keys:
            self.assertNotRegex(examples, rf"\b{re.escape(key)}\b")
            self.assertNotRegex(outputs, rf"\b{re.escape(key)}\b")

        compatibility = markdown_heading_section(
            self.data_contracts, "Input Compatibility Normalization"
        )
        for canonical_field in (
            "lesson_count_target",
            "lesson_granularity",
            "teaching_persona",
            "max_interactions",
            "require_visual_text_pair",
            "must_use_viewpoint_check",
            "allow_cross_lesson_dependency",
            "require_branching_feedback",
            "minimize_optimization_scope",
            "execution_mode",
        ):
            with self.subTest(canonical_field=canonical_field):
                self.assertIn(canonical_field, compatibility)
        self.assertIn("course_profile.lesson_count_target", compatibility)
        self.assertIn("keep the canonical field", compatibility)
        self.assertIn("record every ignored legacy path and value", compatibility)
        self.assertIn("never choose an alias by incidental input order", compatibility)
        self.assertIn("unrecognized member", compatibility)
        authoring_controls = self.references[
            Path("references/authoring-controls.md")
        ]
        self.assertIn("Consume the normalization result", authoring_controls)
        self.assertNotIn("keep the canonical field", authoring_controls)
        self.assertNotIn("unrecognized member", authoring_controls)

    def test_authoring_constraints_preserve_canonical_limits_and_output_shape(self):
        constraints = markdown_heading_section(
            self.data_contracts, "Authoring Constraints"
        )
        generation_output = markdown_heading_section(
            self.data_contracts, "Generation Output"
        )
        interaction_policy = markdown_heading_section(
            self.pedagogy, "Interaction Policy Precedence"
        )

        self.assertIn("integer from `0` through `5`", constraints)
        self.assertIn("per-lesson maximum remains `5`", constraints)
        self.assertIn("`disabled`", interaction_policy)
        self.assertIn("Emit no MarkdownFlow interaction blocks", interaction_policy)
        self.assertIn("disabled` forces zero interactions", self.pedagogy)
        self.assertIn("pure_slides` overrides `require_visual_text_pair`", self.pedagogy)
        self.assertIn("lesson_teaching_prompts` (array, required)", generation_output)
        self.assertIn("exactly one lesson", self.generation)

    def test_focused_optimization_does_not_synthesize_course_artifacts(self):
        optimization = self.references[
            Path("references/optimization-workflow.md")
        ]
        course_prompt = markdown_heading_section(optimization, "Course Prompt")
        course_description = markdown_heading_section(
            optimization, "Course Description"
        )

        self.assertIn("focused audit", course_prompt)
        self.assertIn("does not synthesize a new course-level artifact", course_prompt)
        self.assertIn("lesson-only source material", course_prompt)
        self.assertIn("focused prompt audit does not create", course_description)

    def test_image_assets_owns_inspect_upload_embed_workflow(self):
        generation_pointer = markdown_heading_section(
            self.generation, "Working with Author-Provided Images"
        )
        deployment = self.references[Path("references/deployment-workflow.md")]

        for heading in ("Inspect", "Upload", "Embed", "Validate", "Handoff"):
            with self.subTest(heading=heading):
                self.assertEqual(
                    self.files_containing(rf"^## {heading}$"),
                    [Path("references/image-assets.md")],
                )
        self.assertIn("Understand each image", self.image_assets)
        self.assertIn("upload-image", self.image_assets)
        self.assertIn("markdownflow.md#images", self.image_assets)
        self.assertIn("image-assets.md", generation_pointer)
        self.assertLess(len(generation_pointer.split()), 40)
        self.assertIn("image-assets.md", deployment)
        self.assertIn("local image", deployment)
        self.assertIn("external image URL", deployment)
        self.assertIn("invalid platform resource URL", deployment)
        self.assertIn("already-valid platform resource", deployment)
        self.assertIn("needs no upload or new manifest entry", self.image_assets)
        self.assertIn("whether the resource was preserved or uploaded", self.image_assets)
        self.assertIn("preserves an already-valid platform resource", self.generation)

    def test_review_checklist_owns_observable_validation(self):
        for heading in (
            "Segmentation Validation",
            "Orchestration Validation",
            "Generation Validation",
            "Optimization Validation",
            "Pre-Deploy Language Audit",
        ):
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}", self.review)

        self.assertNotIn("## Validation", self.course_prompt)
        self.assertIn(
            "review-checklist.md#generation-validation", self.generation
        )
        self.assertIn("image-assets.md#validate", self.review)
        self.assertNotIn("res.ai-shifu.cn", self.review)
        self.assertNotIn("image-manifest.json", self.review)
        self.assertIn(
            "does not exceed the normalized `authoring_constraints.max_interactions`",
            self.review,
        )


class AnalyticsAndPlatformResponsibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = read_skill_file("references/analytics/tables.md")
        cls.dsl = read_skill_file("references/analytics/dsl.md")
        cls.privacy = read_skill_file(
            "references/analytics/privacy-and-presentation.md"
        )
        cls.recipes = read_skill_file("references/analytics/recipes.md")
        cls.cli = read_skill_file("references/cli/cli-reference.md")
        cls.directory_spec = read_skill_file(
            "references/cli/course-directory-spec.md"
        )

    def test_schema_documents_are_dependency_leaves(self):
        graph = behavioral_dependency_graph()

        self.assertEqual(graph[Path("references/analytics/tables.md")], set())
        self.assertEqual(
            graph[Path("references/cli/course-directory-spec.md")], set()
        )

    def test_identifier_relationships_and_translation_have_distinct_owners(self):
        self.assertIn("## Identifier Relationships", self.tables)
        self.assertNotIn("## ID Field Translation Rules", self.tables)
        self.assertIn("## ID Field Translation Rules", self.privacy)
        self.assertIn("tables.md#identifier-relationships", self.privacy)

    def test_generated_content_protocol_has_one_owner(self):
        allowlist = "[301, 311, 312, 321, 322]"

        self.assertIn(allowlist, self.dsl)
        self.assertNotIn(allowlist, self.tables)
        self.assertNotIn(allowlist, self.privacy)
        self.assertIn("generated-content rules in `dsl.md`", self.privacy)

    def test_privacy_policy_does_not_copy_executable_queries(self):
        self.assertNotIn("analytics-query", self.privacy)
        self.assertIn("## Refusals", self.privacy)
        self.assertIn("## Translation Gate", self.privacy)
        self.assertIn("## Answer Structure", self.privacy)

    def test_query_recipes_not_cli_reference_own_business_scenarios(self):
        self.assertIn("## Course Overview", self.recipes)
        self.assertIn("## Follow-up Q&A", self.recipes)
        self.assertNotIn("## Course Overview", self.cli)
        self.assertNotIn("## Follow-up Q&A", self.cli)

    def test_tables_own_rating_and_follow_up_relationship_facts(self):
        feedback_relationship = markdown_heading_section(
            self.tables, "Feedback-to-Lesson Relationship"
        )
        follow_up_relationship = markdown_heading_section(
            self.tables, "Follow-up Q&A Relationship"
        )
        rating_recipe = markdown_heading_section(
            self.recipes, "Recipe 7 — Lowest-rated lessons and mode comparison"
        )
        follow_up_recipe = markdown_heading_section(
            self.recipes,
            "Recipe 22 — Latest follow-ups with asker identity (3-step combo)",
        )

        self.assertIn("progress_record_bid", feedback_relationship)
        self.assertIn("outline_item_bid", feedback_relationship)
        self.assertIn("tables.md#feedback-to-lesson-relationship", rating_recipe)
        self.assertIn('"table":"learn_lesson_feedbacks"', rating_recipe)
        self.assertIn('"table":"learn_progress_records"', rating_recipe)
        self.assertIn("client-side join", rating_recipe)

        self.assertIn("normally have the same position", follow_up_relationship)
        self.assertIn(
            "Never require `answer.position > question.position`",
            follow_up_relationship,
        )
        self.assertIn("tables.md#follow-up-qa-relationship", follow_up_recipe)
        self.assertNotIn("smallest `position >", follow_up_recipe)

    def test_cli_owns_credit_envelope_and_recipes_consume_it(self):
        credit_contract = markdown_heading_section(self.cli, "credit-detail")
        credit_recipe = markdown_heading_section(
            self.recipes, "Recipe 13 — Reading the response"
        )

        self.assertIn("data.summary.total_credits", credit_contract)
        self.assertIn("data.summary.unique_wallets", credit_contract)
        self.assertIn("data.rows[].wallet_creator_bid", credit_contract)
        self.assertIn("cli-reference.md#credit-detail", credit_recipe)
        self.assertIn("client-side", credit_recipe)
        self.assertIn("wallet_creator_bid", credit_recipe)

    def test_dsl_owns_null_aggregate_and_user_dimension_rules(self):
        operators = markdown_heading_section(
            self.dsl, "Operators (`where[].op`)"
        )
        aggregates = markdown_heading_section(
            self.dsl, "Aggregate Functions (`aggregate[].fn`)"
        )
        learner_dimension = markdown_heading_section(
            self.dsl, "Per-Learner (`user_bid`) Dimension"
        )

        self.assertRegex(
            operators,
            r"(?s)`is_null`, `is_not_null`.*Omit `value`.*JSON `null`"
            r".*non-null value is rejected",
        )
        self.assertRegex(
            aggregates,
            r"(?s)`min`, `max`.*Numeric or timestamp aggregate",
        )
        self.assertRegex(
            aggregates,
            r"(?s)`alias` is optional.*server derives.*unique safe identifier",
        )
        self.assertIn(
            "## Constraints (enforced server-side; see "
            "[Validation Error Codes](#validation-error-codes))",
            self.dsl,
        )

        self.assertIn("exactly these ways", learner_dimension)
        for required_signal in (
            "count_distinct(user_bid)",
            "`select` and `group_by` together",
            "`generated_content` is also selected",
            "restricted `user_users` lookup",
        ):
            with self.subTest(required_signal=required_signal):
                self.assertIn(required_signal, learner_dimension)

    def test_order_recipes_keep_metric_grains_distinct(self):
        ordering_users = markdown_heading_section(
            self.recipes, "Recipe 3 — Ordering users (下单人数)"
        )
        successful_users = markdown_heading_section(
            self.recipes, "Recipe 4 — Successful ordering users (成功下单)"
        )
        paid_users = markdown_heading_section(
            self.recipes, "Recipe 5 — Paid users (付费人数) and revenue"
        )
        order_count = markdown_heading_section(
            self.recipes, "Recipe 6 — Successful order count (订单数) and revenue"
        )
        refunds = markdown_heading_section(
            self.recipes,
            "Recipe 6a — Refunded users (退款人数) and refunded order count",
        )
        funnel = markdown_heading_section(
            self.recipes, "Recipe 6c — Order status distribution (funnel view)"
        )

        self.assertIn('"op":"in","value":[501,502,504]', ordering_users)
        self.assertIn('"fn":"count_distinct","field":"user_bid"', ordering_users)
        self.assertIn('"value":502', successful_users)
        self.assertIn('"fn":"count_distinct","field":"user_bid"', successful_users)
        self.assertIn('"field":"paid_price","op":">","value":0', paid_users)
        self.assertIn('"field":"status","op":"=","value":502', paid_users)
        self.assertIn('"fn":"count_distinct","field":"user_bid"', paid_users)
        self.assertIn('"value":502', order_count)
        self.assertIn('{"fn":"count","alias":"orders"}', order_count)
        self.assertIn('"value":503', refunds)
        self.assertIn(
            '"fn":"count_distinct","field":"user_bid","alias":"refunded_users"',
            refunds,
        )
        self.assertNotIn('"where"', funnel)
        self.assertIn('"group_by":["status"]', funnel)

    def test_title_resolution_rejects_unsupported_history(self):
        metadata = markdown_heading_section(
            self.recipes, "Course Metadata (resolve `shifu_bid ↔ current title`)"
        )
        title_visibility = markdown_heading_section(
            self.tables, "Current Title Visibility"
        )

        self.assertIn("find-title <keyword>", metadata)
        self.assertIn("only when the `shifu_bid` is already known", metadata)
        self.assertIn("Historical title lookup is unsupported", metadata)
        self.assertIn("not exposed", title_visibility)
        self.assertNotIn('"op":"replace"', metadata)

    def test_identity_lookup_and_follow_up_presentation_have_one_safe_path(self):
        identity = markdown_heading_section(self.recipes, "Identity Lookup")
        follow_ups = markdown_heading_section(self.recipes, "Follow-up Q&A")
        restricted_access = markdown_heading_section(
            self.privacy, "`user_users` — Restricted Access"
        )

        self.assertEqual(self.recipes.count('"table":"user_users"'), 2)
        self.assertIn("Recipe 24A", identity)
        self.assertIn("already obtained", identity)
        self.assertIn("Recipe 24B", identity)
        self.assertIn("exact phone number or email", identity)
        self.assertIn("Never filter by nickname", identity)
        self.assertIn("Learner A (安全昵称 · 脱敏身份)", restricted_access)
        self.assertIn("ordinal labels", restricted_access)
        self.assertIn("aggregate questions", follow_ups)
        self.assertIn("do not execute an identity lookup", follow_ups)
        self.assertIn("omit the identity lookup", follow_ups)
        self.assertIn(
            "Never expose a raw `user_bid` in user-facing output",
            restricted_access,
        )
        self.assertIn("Never expose a raw `user_bid`; other raw", self.privacy)

    def test_import_payload_schema_has_one_owner(self):
        cli_pointer = markdown_heading_section(self.cli, "Import JSON Schema")
        directory_schema = markdown_heading_section(
            self.directory_spec, "shifu-import.json"
        )

        self.assertIn(
            "course-directory-spec.md#shifu-importjson", cli_pointer
        )
        self.assertNotIn('"outline_items"', cli_pointer)
        self.assertIn('"outline_items"', directory_schema)

    def test_import_payload_schema_matches_the_builder_contract(self):
        directory_schema = markdown_heading_section(
            self.directory_spec, "shifu-import.json"
        )
        payload = first_json_code_block(directory_schema)

        self.assertIsInstance(payload, dict)
        self.assertEqual(
            set(payload),
            {"version", "exported_at", "shifu", "outline_items", "structure"},
        )
        self.assertRegex(payload["exported_at"], r"^\d{4}-\d{2}-\d{2}T")

        shifu = payload["shifu"]
        self.assertTrue(
            {
                "shifu_bid",
                "title",
                "description",
                "course_prompt",
                "ask_enabled_status",
            }.issubset(shifu)
        )
        self.assertNotIn("price", shifu)

        self.assertGreaterEqual(len(payload["outline_items"]), 2)
        chapter, lesson = payload["outline_items"][:2]
        self.assertTrue(
            {
                "outline_item_bid",
                "title",
                "parent_bid",
                "course_prompt",
                "ask_enabled_status",
                "content",
            }.issubset(chapter)
        )
        self.assertEqual(chapter["parent_bid"], "")
        self.assertEqual(chapter["course_prompt"], "")
        self.assertEqual(chapter["content"], "")
        self.assertEqual(lesson["parent_bid"], chapter["outline_item_bid"])
        self.assertNotEqual(lesson["course_prompt"], "")
        self.assertNotEqual(lesson["content"], "")
        self.assertEqual(payload["structure"]["type"], "shifu")
        self.assertIn("children", payload["structure"])
        self.assertRegex(
            directory_schema,
            r"(?s)current importer sends course `title`, `description`, and "
            r"`course_prompt`.*does not submit.*Ask.*as platform attributes",
        )


if __name__ == "__main__":
    unittest.main()
