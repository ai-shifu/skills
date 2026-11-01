"""Execute the manual npm publication source gate against real Git histories."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/cli-publish.yml"


def release_gate() -> str:
    document = WORKFLOW.read_text(encoding="utf-8")
    steps = re.split(r"^      - name: ", document, flags=re.MULTILINE)[1:]
    step = next(item for item in steps if item.splitlines()[0] == "Verify the published release is on main")
    return textwrap.dedent(step.split("        run: |\n", 1)[1])


class CliPublicationGateTest(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory(prefix="cli-publish-gate-"))
        self.root = Path(directory)
        self.git("init", "--quiet", "--initial-branch=main")
        self.git("config", "user.name", "CLI publication test")
        self.git("config", "user.email", "cli-test@example.com")
        self.git("commit", "--quiet", "--allow-empty", "-m", "release on main")
        self.git("tag", "v2.2.1")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.release = {
            "tag_name": "v2.2.1", "draft": False, "prerelease": False,
            "published_at": "2026-11-01T00:00:00Z",
        }
        self.bin = self.root / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text('#!/bin/sh\ncat "$CLI_RELEASE_FIXTURE"\n', encoding="utf-8")
        gh.chmod(0o755)

    def git(self, *arguments):
        return subprocess.run(["git", *arguments], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def run_gate(self, tag="v2.2.1", ref="refs/heads/main"):
        fixture = self.root / "release-fixture.json"
        fixture.write_text(json.dumps(self.release), encoding="utf-8")
        environment = {
            **os.environ,
            "PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
            "CLI_RELEASE_FIXTURE": str(fixture), "RUNNER_TEMP": str(self.root),
            "CLI_TAG": tag, "GITHUB_REF": ref, "GITHUB_REPOSITORY": "ai-shifu/skills",
        }
        return subprocess.run(["bash", "-c", release_gate()], cwd=self.root, env=environment, capture_output=True, text=True)

    def test_selects_the_exact_released_commit_on_main(self):
        self.git("commit", "--quiet", "--allow-empty", "-m", "later main change")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.git("rev-parse", "v2.2.1^{commit}"))

    def test_rejects_unmerged_release_tags(self):
        self.git("checkout", "--quiet", "-b", "unmerged")
        self.git("commit", "--quiet", "--allow-empty", "-m", "unmerged release")
        self.git("tag", "v2.2.2")
        self.release["tag_name"] = "v2.2.2"
        self.assertNotEqual(self.run_gate("v2.2.2").returncode, 0)

    def test_requires_a_published_stable_release(self):
        for change in ({"draft": True}, {"prerelease": True}, {"published_at": None}, {"tag_name": "v2.2.0"}):
            with self.subTest(change=change):
                original = dict(self.release)
                self.release.update(change)
                result = self.run_gate()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("published stable", result.stderr)
                self.release = original

    def test_rejects_workflow_dispatch_from_other_branches(self):
        self.assertNotEqual(self.run_gate(ref="refs/heads/feature").returncode, 0)

    def test_rejects_malformed_or_shell_tag_input(self):
        for tag in ("v2.2.1; touch injected", "v2.2.1-beta.1", "--help", "v02.2.1"):
            with self.subTest(tag=tag):
                self.assertNotEqual(self.run_gate(tag).returncode, 0)
        self.assertFalse((self.root / "injected").exists())
