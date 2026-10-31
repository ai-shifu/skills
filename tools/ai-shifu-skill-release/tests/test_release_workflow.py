"""Exercise release event routing without a runner or third-party YAML parser."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace


WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/release.yml"


def scalar(block: str, key: str, indent: int) -> str:
    """Read a scalar from the workflow's indentation-based mapping."""
    lines = block.splitlines()
    prefix = " " * indent + key + ":"
    for index, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if value in ("|", "|-", ">", ">-"):
            continuation = []
            for following in lines[index + 1 :]:
                if (
                    following.strip()
                    and len(following) - len(following.lstrip()) <= indent
                ):
                    break
                continuation.append(following.strip())
            return " ".join(continuation)
        return value
    return ""


def job_blocks(document: str) -> dict[str, str]:
    jobs = document.split("\njobs:\n", 1)[1]
    entries = list(re.finditer(r"^  ([a-zA-Z0-9_-]+):\s*$", jobs, re.MULTILINE))
    return {
        match.group(1): jobs[match.start() : entries[index + 1].start()]
        if index + 1 < len(entries)
        else jobs[match.start() :]
        for index, match in enumerate(entries)
    }


def list_values(block: str, key: str, indent: int) -> list[str]:
    value = scalar(block, key, indent)
    if value:
        return [item.strip().strip("\"'") for item in value.strip("[]").split(",")]
    following = block.split(" " * indent + key + ":\n", 1)[1]
    values = []
    for line in following.splitlines():
        if line.strip() and not line.startswith(" " * (indent + 2)):
            break
        if line.strip().startswith("- "):
            values.append(line.strip()[2:].strip("\"'"))
    return values


def step_script(block: str, name: str) -> str:
    steps = re.split(r"^      - name: ", block, flags=re.MULTILINE)[1:]
    step = next(step for step in steps if step.splitlines()[0] == name)
    return textwrap.dedent(step.split("        run: |\n", 1)[1])


def evaluate(expression: str, context: dict[str, object]) -> object:
    """Evaluate only the small documented expression subset used by job routing."""
    expression = expression.strip()
    if expression.startswith("${{") and expression.endswith("}}"):
        expression = expression[3:-2].strip()
    expression = expression.replace("&&", " and ").replace("||", " or ")
    expression = re.sub(r"!(?!=)", "not ", expression).strip()
    tree = ast.parse(expression, mode="eval")
    allowed = (
        ast.Expression,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Attribute,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Call,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError(f"Unsupported workflow expression: {type(node).__name__}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError("Private attributes are not workflow context")
        if isinstance(node, ast.Call) and (
            not isinstance(node.func, ast.Name)
            or node.func.id not in ("startsWith", "cancelled")
        ):
            raise ValueError("Unexpected workflow expression function")
    return eval(  # noqa: S307 - AST and execution context are explicitly restricted.
        compile(tree, str(WORKFLOW), "eval"),
        {"__builtins__": {}},
        {
            **context,
            "true": True,
            "false": False,
            "cancelled": lambda: context.get("cancelled", False),
            "startsWith": lambda value, prefix: str(value).casefold().startswith(
                str(prefix).casefold()
            ),
        },
    )


def event_context(
    event: str,
    *,
    preview: str = "artifact",
    action: str = "published",
    tag: str = "v1.2.3",
    draft: bool = False,
    prerelease: bool = False,
    create_draft: str = "true",
    ref_type: str = "branch",
    attempt: int = 1,
    release_result: str | None = None,
    published: str | None = None,
    cancelled: bool = False,
) -> dict[str, object]:
    automatic = event == "push" and ref_type == "branch" and create_draft == "true"
    return {
        "cancelled": cancelled,
        "github": SimpleNamespace(
            event_name=event,
            ref_name="main" if ref_type == "branch" else tag,
            ref_type=ref_type,
            run_attempt=attempt,
            event=SimpleNamespace(
                action=action,
                release=SimpleNamespace(
                    tag_name=tag, draft=draft, prerelease=prerelease
                ),
            ),
        ),
        "inputs": SimpleNamespace(preview_type=preview, expected_version="1.2.3"),
        "needs": SimpleNamespace(
            release_source=SimpleNamespace(
                outputs=SimpleNamespace(create_draft=create_draft)
            ),
            draft=SimpleNamespace(
                result=release_result or ("success" if automatic else "skipped"),
                outputs=SimpleNamespace(
                    published=published if published is not None else str(automatic).lower(),
                    tag=tag if automatic else "",
                ),
            ),
        ),
    }


class ReleaseWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.document = WORKFLOW.read_text(encoding="utf-8")
        self.jobs = job_blocks(self.document)
        self.channels = {
            scalar(block, "target", 6): (name, block)
            for name, block in self.jobs.items()
            if scalar(block, "uses", 4) == "./.github/workflows/platform-publish.yml"
        }
        self.assertEqual(set(self.channels), {"clawhub", "skillhub"})

    def eligible(self, name: str, context: dict[str, object]) -> bool:
        block = self.jobs[name]
        condition = scalar(block, "if", 4)
        if condition and not evaluate(condition, context):
            return False
        needs = scalar(block, "needs", 4)
        # A status function overrides Actions' implicit success() requirement.
        # Legacy release events intentionally run even though draft was skipped.
        if needs and not re.search(r"\b(?:cancelled|always|failure|success)\(", condition):
            for dependency in needs.strip("[]").split(","):
                if not self.eligible(dependency.strip(), context):
                    return False
        return True

    def launched_channels(self, **event: object) -> set[str]:
        context = event_context(**event)
        return {
            target
            for target, (name, _) in self.channels.items()
            if self.eligible(name, context)
        }

    def test_platforms_start_after_automatic_or_human_publication(self) -> None:
        cases = (
            ({"event": "push"}, {"clawhub", "skillhub"}),
            ({"event": "push", "ref_type": "tag"}, set()),
            ({"event": "push", "create_draft": "false"}, set()),
            ({"event": "push", "release_result": "failure"}, set()),
            ({"event": "push", "release_result": "skipped"}, set()),
            ({"event": "push", "published": "false"}, set()),
            ({"event": "push", "attempt": 2}, set()),
            ({"event": "push", "cancelled": True}, set()),
            ({"event": "workflow_dispatch", "preview": "artifact"}, set()),
            ({"event": "workflow_dispatch", "preview": "draft"}, set()),
            ({"event": "workflow_dispatch", "preview": "publish", "published": "true", "release_result": "success"}, set()),
            ({"event": "release"}, {"clawhub", "skillhub"}),
            ({"event": "release", "cancelled": True}, set()),
            ({"event": "release", "draft": True}, set()),
            ({"event": "release", "prerelease": True}, set()),
            ({"event": "release", "tag": "preview-v1.2.3-abc"}, set()),
        )
        for event, expected in cases:
            with self.subTest(event=event):
                self.assertEqual(self.launched_channels(**event), expected)

    def test_release_subscription_ignores_draft_creation_and_edits(self) -> None:
        events = self.document.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        release = re.search(
            r"^  release:\s*\n((?:^    .*\n|^\s*\n)*)", events, re.MULTILINE
        )
        self.assertIsNotNone(release, "Human publication must trigger the workflow")
        activities = scalar(release.group(1), "types", 4)
        self.assertEqual(
            activities.strip("[]").replace(" ", "").split(","), ["published"]
        )

    def test_main_pushes_and_formal_tag_pushes_reach_the_release_workflow(self) -> None:
        events = self.document.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        push = re.search(r"^  push:\s*\n((?:^    .*\n|^\s*\n)*)", events, re.MULTILINE)
        self.assertIsNotNone(push)
        self.assertEqual(list_values(push.group(1), "branches", 4), ["main"])
        self.assertEqual(list_values(push.group(1), "tags", 4), ["v*"])

    def test_platforms_use_published_tag_even_when_workflow_ref_differs(self) -> None:
        context = event_context("release", tag="v1.2.3")
        context["github"].ref_name = "main"
        for target, (name, block) in self.channels.items():
            with self.subTest(target=target):
                self.assertTrue(self.eligible(name, context))
                self.assertEqual(evaluate(scalar(block, "tag", 6), context), "v1.2.3")

    def test_automatic_platforms_use_the_verified_release_tag(self) -> None:
        context = event_context("push", tag="v1.2.4")
        context["github"].event.release.tag_name = ""
        for target, (name, block) in self.channels.items():
            with self.subTest(target=target):
                self.assertTrue(self.eligible(name, context))
                self.assertEqual(evaluate(scalar(block, "tag", 6), context), "v1.2.4")

    def test_preparation_runs_only_for_release_sources(self) -> None:
        draft_jobs = [
            name for name, block in self.jobs.items() if "--draft-only" in block
        ]
        self.assertTrue(draft_jobs, "Optional draft preparation must remain available")
        for event, preview, expected in (
            ("push", "artifact", True),
            ("workflow_dispatch", "draft", True),
            ("workflow_dispatch", "publish", True),
            ("workflow_dispatch", "artifact", False),
            ("release", "artifact", False),
        ):
            with self.subTest(event=event, preview=preview):
                context = event_context(event, preview=preview)
                self.assertEqual(
                    any(self.eligible(name, context) for name in draft_jobs), expected
                )

    def test_main_version_detector_controls_preparation_and_publication(self) -> None:
        for create_draft in ("false", "true"):
            with self.subTest(create_draft=create_draft):
                context = event_context("push", create_draft=create_draft)
                context["github"].ref_name = "main"
                self.assertEqual(
                    self.eligible("draft", context), create_draft == "true"
                )
                for name, _ in self.channels.values():
                    self.assertEqual(self.eligible(name, context), create_draft == "true")

    def test_manual_draft_requires_the_main_branch(self) -> None:
        script = step_script(
            self.jobs["draft"], "Require main after the version PR is merged"
        )
        for ref_type, ref_name, accepted in (
            ("branch", "main", True),
            ("branch", "feature/version", False),
            ("tag", "main", False),
            ("tag", "v1.2.3", False),
        ):
            with self.subTest(ref_type=ref_type, ref_name=ref_name):
                result = subprocess.run(
                    [
                        "bash", "--noprofile", "--norc", "-e", "-o", "pipefail",
                        "-c", script,
                    ],
                    env={
                        **os.environ,
                        "GITHUB_REF_TYPE": ref_type,
                        "GITHUB_REF_NAME": ref_name,
                    },
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode == 0, accepted, result.stderr)

    def test_main_ancestry_and_formal_tag_pin_use_the_exact_verified_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            remote = root / "remote.git"
            source = root / "source"
            source.mkdir()
            subprocess.run(
                ["git", "init", "--bare", "--quiet", str(remote)], check=True
            )

            def git(*arguments: str) -> str:
                return subprocess.run(
                    ["git", *arguments], cwd=source, check=True,
                    capture_output=True, text=True,
                ).stdout.strip()

            git("init", "--quiet", "-b", "main")
            git("config", "user.name", "Workflow Test")
            git("config", "user.email", "workflow@example.com")
            git("remote", "add", "origin", str(remote))
            (source / "version").write_text("old\n")
            git("add", ".")
            git("commit", "--quiet", "-m", "old release")
            previous = git("rev-parse", "HEAD")
            (source / "version").write_text("verified\n")
            git("commit", "--quiet", "-a", "-m", "verified version")
            verified = git("rev-parse", "HEAD")
            git("push", "--quiet", "origin", "main")
            git("checkout", "--quiet", "-b", "unmerged")
            (source / "unmerged").write_text("must not be released\n")
            git("add", ".")
            git("commit", "--quiet", "-m", "unmerged changes")
            unmerged = git("rev-parse", "HEAD")

            def run(
                script: str, commit: str, tag: str = "v1.2.3"
            ) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        "bash", "--noprofile", "--norc", "-e", "-o", "pipefail",
                        "-c", script,
                    ],
                    cwd=source, capture_output=True, text=True,
                    env={**os.environ, "GITHUB_SHA": unmerged,
                         "RELEASE_COMMIT": commit, "RELEASE_TAG": tag},
                )

            ancestry = step_script(
                self.jobs["draft"], "Ensure Draft Release source is on main"
            )
            self.assertEqual(run(ancestry, verified).returncode, 0)
            self.assertNotEqual(run(ancestry, unmerged).returncode, 0)

            pin = step_script(
                self.jobs["draft"], "Pin the formal version tag to the verified source"
            )
            # Checkout deliberately remains on the newer, unmerged commit.
            # Recovery must select RELEASE_COMMIT, never GITHUB_SHA or checkout HEAD.
            for attempt in range(2):
                with self.subTest(attempt=attempt):
                    result = run(pin, verified)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        git("ls-remote", "--refs", "origin", "refs/tags/v1.2.3").split()[0],
                        verified,
                    )

            git("tag", "v1.2.4", previous)
            git("push", "--quiet", "origin", "refs/tags/v1.2.4")
            self.assertNotEqual(run(pin, verified, "v1.2.4").returncode, 0)
            self.assertEqual(
                git("ls-remote", "--refs", "origin", "refs/tags/v1.2.4").split()[0],
                previous,
            )

            git("tag", "-a", "v1.2.5", verified, "-m", "annotated version")
            git("push", "--quiet", "origin", "refs/tags/v1.2.5")
            result = run(pin, verified, "v1.2.5")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_publication_mode_and_failure_propagation(self) -> None:
        step = next(
            step for step in re.split(r"^      - name: ", self.jobs["draft"], flags=re.MULTILINE)[1:]
            if step.splitlines()[0] == "Upload, verify and publish the formal Release"
        )
        self.assertEqual(scalar(step, "shell", 8), "bash")
        script = step_script(self.jobs["draft"], "Upload, verify and publish the formal Release")
        for publish, exit_code in (("true", 0), ("false", 0), ("true", 23)):
            with self.subTest(publish=publish, exit_code=exit_code), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "dist/candidate").mkdir(parents=True)
                executable = root / "bin/python3"
                executable.parent.mkdir()
                executable.write_text(
                    '#!/bin/sh\n'
                    'printf "%s\\n" "$@" > "$ARGUMENTS_FILE"\n'
                    'mkdir -p release-notes\n'
                    'printf "%s\\n" "Release notes" > release-notes/release-notes.md\n'
                    'printf "%s\\n" "https://github.com/example/skills/releases/tag/v1.2.3"\n'
                    'exit "$PUBLICATION_EXIT_CODE"\n'
                )
                executable.chmod(0o755)
                output = root / "github-output"
                output.touch()
                result = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                    cwd=root, capture_output=True, text=True,
                    env={
                        **os.environ,
                        "PATH": str(executable.parent) + os.pathsep + os.environ["PATH"],
                        "ARGUMENTS_FILE": str(root / "arguments"),
                        "PUBLICATION_EXIT_CODE": str(exit_code),
                        "RELEASE_COMMIT": "a" * 40,
                        "GITHUB_SHA": "b" * 40,
                        "RELEASE_TAG": "v1.2.3",
                        "PUBLISH_RELEASE": publish,
                        "GITHUB_OUTPUT": str(output),
                        "GITHUB_STEP_SUMMARY": str(root / "summary"),
                    },
                )
                arguments = (root / "arguments").read_text().splitlines()
                self.assertEqual(arguments[arguments.index("--commit") + 1], "a" * 40)
                self.assertEqual("--draft-only" in arguments, publish == "false")
                if exit_code:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(output.read_text(), "")
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(output.read_text(), f"published={publish}\n")

    def test_release_notes_artifact_keeps_retry_attempts_separate(self) -> None:
        step = next(
            step for step in re.split(r"^      - name: ", self.jobs["draft"], flags=re.MULTILINE)[1:]
            if step.splitlines()[0] == "Save Release notes"
        )
        name = scalar(step, "name", 10)
        self.assertIn("needs.release_source.outputs.commit", name)
        self.assertIn("github.run_attempt", name)


class ReleaseSourceDetectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.jobs = job_blocks(WORKFLOW.read_text(encoding="utf-8"))
        source = self.jobs["release_source"]
        steps = re.split(r"^      - name: ", source, flags=re.MULTILINE)[1:]
        scripts = [
            textwrap.dedent(step.split("        run: |\n", 1)[1])
            for step in steps
            if "PUSH_BEFORE" in step and "        run: |\n" in step
        ]
        self.assertEqual(len(scripts), 1, "Expected one main version-change detector")
        self.script = scripts[0]
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        self.skill = self.repo / "skills/ai-shifu-course-creator/SKILL.md"
        self.skill.parent.mkdir(parents=True)
        self.git("init", "--quiet", "-b", "main")
        self.git("config", "user.name", "Workflow Test")
        self.git("config", "user.email", "workflow@example.com")
        self.before = self.commit_skill("1.2.3")

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments], cwd=self.repo, check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def commit_skill(self, version: str, body: str = "Release fixture") -> str:
        self.skill.write_text(
            "---\nname: ai-shifu-course-creator\ndescription: Test fixture\n"
            f"metadata:\n  version: {version}\n  version_management: standalone\n"
            f"---\n\n# Fixture\n\n{body}\nversion: 99.0.0\n",
            encoding="utf-8",
        )
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "update fixture")
        return self.git("rev-parse", "HEAD")

    def detect(
        self, head: str, *, before: str | None = None,
        event: str = "push", ref_type: str = "branch", ref_name: str = "main",
        expected_version: str = "1.2.3",
        preview: str = "draft", source_commit: str = "",
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
        output = self.root / "github-output"
        output.write_text("")
        result = subprocess.run(
            [
                "bash", "--noprofile", "--norc", "-e", "-o", "pipefail",
                "-c", self.script,
            ],
            cwd=self.repo, capture_output=True, text=True,
            env={
                **os.environ,
                "GITHUB_EVENT_NAME": event,
                "GITHUB_REF_TYPE": ref_type,
                "GITHUB_REF_NAME": ref_name,
                "GITHUB_SHA": head,
                "PUSH_BEFORE": self.before if before is None else before,
                "EXPECTED_VERSION": expected_version,
                "PREVIEW_TYPE": preview,
                "SOURCE_COMMIT": source_commit,
                "GITHUB_OUTPUT": str(output),
                "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "scripts"),
            },
        )
        outputs = dict(
            line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
        )
        return result, outputs

    def test_version_increase_publishes_from_the_exact_merge_commit(self) -> None:
        verified = self.commit_skill("1.2.4")
        self.commit_skill("9.9.9", "Unrelated later checkout changes")
        result, outputs = self.detect(verified)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            outputs,
            {"create_draft": "true", "publish_release": "true", "version": "1.2.4", "tag": "v1.2.4", "commit": verified},
        )

    def test_body_change_with_the_same_version_does_not_prepare_a_draft(self) -> None:
        head = self.commit_skill("1.2.3", "A corrected authoring instruction")
        result, outputs = self.detect(head)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs.get("create_draft"), "false")
        self.assertEqual(outputs.get("publish_release"), "false")

    def test_ordinary_main_commit_does_not_prepare_a_draft(self) -> None:
        (self.repo / "README.md").write_text("An ordinary repository change\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "ordinary change")
        result, outputs = self.detect(self.git("rev-parse", "HEAD"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs.get("create_draft"), "false")
        self.assertEqual(outputs.get("publish_release"), "false")

    def test_initial_main_push_does_not_create_a_release_without_a_baseline(self) -> None:
        result, outputs = self.detect(self.before, before="0" * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs.get("create_draft"), "false")
        self.assertEqual(outputs.get("publish_release"), "false")

    def test_missing_baseline_fails_before_preparing_a_draft(self) -> None:
        head = self.commit_skill("1.2.4")
        result, outputs = self.detect(head, before="1" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(outputs.get("create_draft"), "true")

    def test_version_decrease_fails_before_preparing_a_draft(self) -> None:
        head = self.commit_skill("1.2.2")
        result, outputs = self.detect(head)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(outputs.get("create_draft"), "true")

    def test_version_comparison_uses_numeric_components(self) -> None:
        baseline = self.commit_skill("1.2.9")
        head = self.commit_skill("1.2.10")
        result, outputs = self.detect(head, before=baseline)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs.get("create_draft"), "true")
        self.assertEqual(outputs.get("tag"), "v1.2.10")

    def test_tag_push_and_manual_draft_keep_their_version_selection(self) -> None:
        for event, ref_type, ref_name in (
            ("push", "tag", "v1.2.3"),
            ("workflow_dispatch", "branch", "main"),
        ):
            with self.subTest(event=event):
                result, outputs = self.detect(
                    self.before, event=event, ref_type=ref_type, ref_name=ref_name
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(outputs.get("create_draft"), "true")
                self.assertEqual(outputs.get("publish_release"), "false")
                self.assertEqual(outputs.get("version"), "1.2.3")
                self.assertEqual(outputs.get("tag"), "v1.2.3")
                self.assertEqual(outputs.get("commit"), self.before)

    def test_manual_publish_recovers_original_commit_after_main_advances(self) -> None:
        merged = self.commit_skill("1.2.4")
        latest = self.commit_skill("1.2.5", "A later release")
        result, outputs = self.detect(
            latest, event="workflow_dispatch", preview="publish",
            source_commit=merged, expected_version="1.2.4",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs.get("commit"), merged)
        self.assertEqual(outputs.get("version"), "1.2.4")
        self.assertEqual(outputs.get("publish_release"), "true")

    def test_manual_publish_rejects_missing_non_sha_and_mismatched_source(self) -> None:
        for source_commit, expected_version in (
            ("", "1.2.3"),
            ("main", "1.2.3"),
            (self.before[:7], "1.2.3"),
            ("1" * 40, "1.2.3"),
            (self.before, "1.2.4"),
        ):
            with self.subTest(source_commit=source_commit, expected_version=expected_version):
                result, outputs = self.detect(
                    self.before, event="workflow_dispatch", preview="publish",
                    source_commit=source_commit, expected_version=expected_version,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotEqual(outputs.get("publish_release"), "true")

    def test_manual_publish_requires_main_and_artifact_mode_has_no_publication(self) -> None:
        for preview, ref_type, ref_name in (
            ("publish", "branch", "feature/version"),
            ("publish", "tag", "v1.2.3"),
            ("artifact", "branch", "main"),
        ):
            with self.subTest(preview=preview, ref_type=ref_type, ref_name=ref_name):
                result, outputs = self.detect(
                    self.before, event="workflow_dispatch", preview=preview,
                    source_commit=self.before, ref_type=ref_type, ref_name=ref_name,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotEqual(outputs.get("publish_release"), "true")


if __name__ == "__main__":
    unittest.main()
