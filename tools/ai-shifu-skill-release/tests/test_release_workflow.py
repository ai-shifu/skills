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
            not isinstance(node.func, ast.Name) or node.func.id != "startsWith"
        ):
            raise ValueError("Unexpected workflow expression function")
    return eval(  # noqa: S307 - AST and execution context are explicitly restricted.
        compile(tree, str(WORKFLOW), "eval"),
        {"__builtins__": {}},
        {
            **context,
            "true": True,
            "false": False,
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
) -> dict[str, object]:
    return {
        "github": SimpleNamespace(
            event_name=event,
            ref_name="main" if event == "workflow_dispatch" else tag,
            event=SimpleNamespace(
                action=action,
                release=SimpleNamespace(
                    tag_name=tag, draft=draft, prerelease=prerelease
                ),
            ),
        ),
        "inputs": SimpleNamespace(preview_type=preview, expected_version="1.2.3"),
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
        if needs:
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

    def test_platforms_wait_for_published_formal_release(self) -> None:
        cases = (
            ({"event": "push"}, set()),
            ({"event": "workflow_dispatch", "preview": "artifact"}, set()),
            ({"event": "workflow_dispatch", "preview": "draft"}, set()),
            ({"event": "release"}, {"clawhub", "skillhub"}),
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

    def test_platforms_use_published_tag_even_when_workflow_ref_differs(self) -> None:
        context = event_context("release", tag="v1.2.3")
        context["github"].ref_name = "main"
        for target, (name, block) in self.channels.items():
            with self.subTest(target=target):
                self.assertTrue(self.eligible(name, context))
                self.assertEqual(evaluate(scalar(block, "tag", 6), context), "v1.2.3")

    def test_draft_and_artifact_events_never_start_platform_jobs(self) -> None:
        draft_jobs = [
            name for name, block in self.jobs.items() if "--draft-only" in block
        ]
        self.assertTrue(draft_jobs, "Formal draft creation must keep the release private")
        for event, preview, expected in (
            ("push", "artifact", True),
            ("workflow_dispatch", "draft", True),
            ("workflow_dispatch", "artifact", False),
            ("release", "artifact", False),
        ):
            with self.subTest(event=event, preview=preview):
                context = event_context(event, preview=preview)
                self.assertEqual(
                    any(self.eligible(name, context) for name in draft_jobs), expected
                )

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
                    env={**os.environ, "GITHUB_SHA": commit, "RELEASE_TAG": tag},
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
            # The remote tag must still select GITHUB_SHA, never checkout HEAD.
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


if __name__ == "__main__":
    unittest.main()
