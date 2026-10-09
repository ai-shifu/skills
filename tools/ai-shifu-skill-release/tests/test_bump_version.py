import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai_shifu_release import version

SKILL_MD = """---
name: Demo Skill
metadata:
  version: 1.1.1
  version_management: standalone
---

# Demo

Body stays byte-identical.
"""


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def make_args(**overrides) -> SimpleNamespace:
    defaults = {
        "skill_name": "demo-skill",
        "skill_version": "",
        "level": "",
        "changelog": "",
        "draft": False,
        "no_pr": True,
        "repo_url": "",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class BumpVersionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="bump-test-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
            os.environ[key] = "bump-test"
            self.addCleanup(os.environ.pop, key, None)
        for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
            os.environ[key] = "bump-test@example.com"
            self.addCleanup(os.environ.pop, key, None)

        self.origin = root / "origin.git"
        git(
            "init",
            "--bare",
            "--quiet",
            "--initial-branch=main",
            str(self.origin),
            cwd=root,
        )
        seed = root / "seed"
        git("clone", "--quiet", f"file://{self.origin}", str(seed), cwd=root)
        skill_dir = seed / "skills/demo-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
        git("add", "--all", cwd=seed)
        git("commit", "--quiet", "-m", "seed", cwd=seed)
        git("push", "--quiet", "origin", "main", cwd=seed)

        self.repo_url = f"file://{self.origin}"

    def test_bump_pushes_branch_without_touching_main(self) -> None:
        args = make_args(skill_version="1.2.0", repo_url=self.repo_url)
        result = version.bump(args)
        self.assertEqual(result["previous_version"], "1.1.1")
        self.assertEqual(result["new_version"], "1.2.0")
        self.assertEqual(result["branch"], "bump/demo-skill-v1.2.0")

        check = Path(self.tmp.name) / "check"
        git(
            "clone",
            "--quiet",
            "--branch",
            result["branch"],
            self.repo_url,
            str(check),
            cwd=Path(self.tmp.name),
        )
        self.assertEqual(
            git("log", "-1", "--format=%s", cwd=check),
            "fix: bump demo-skill to 1.2.0",
        )
        text = (check / "skills/demo-skill/SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "metadata:\n  version: 1.2.0\n  version_management: standalone", text
        )
        self.assertNotIn("\nversion: 1.2.0", text)
        self.assertEqual(
            text.split("---\n", 2)[2], SKILL_MD.split("---\n", 2)[2]
        )  # body unchanged
        # main itself must not move: the merge is a human gate
        self.assertIn(
            "version: 1.1.1",
            git("show", "origin/main:skills/demo-skill/SKILL.md", cwd=check),
        )

    def test_bump_opens_release_pr_with_a_separate_commit_subject(self) -> None:
        args = make_args(
            skill_version="1.2.0", repo_url=self.repo_url, no_pr=False
        )
        run = version.run
        pr_url = "https://github.com/ai-shifu/skills/pull/123"

        def run_with_mocked_github(*command: str, cwd: Path) -> str:
            if command[:3] == ("gh", "pr", "create"):
                self.assertEqual(
                    command[command.index("--title") + 1],
                    "chore: flow version to v1.2.0",
                )
                self.assertEqual(
                    git("log", "-1", "--format=%s", cwd=cwd),
                    "fix: bump demo-skill to 1.2.0",
                )
                return pr_url
            return run(*command, cwd=cwd)

        with patch.object(version, "run", side_effect=run_with_mocked_github):
            result = version.bump(args)
        self.assertEqual(result["pr_url"], pr_url)

    def test_bump_rejects_non_increasing_version(self) -> None:
        args = make_args(skill_version="1.1.1", repo_url=self.repo_url)
        with self.assertRaises(ValueError):
            version.bump(args)

    def test_bumped_version_levels(self) -> None:
        self.assertEqual(version.bumped_version("1.1.1", "major"), "2.0.0")
        self.assertEqual(version.bumped_version("1.1.1", "minor"), "1.2.0")
        self.assertEqual(version.bumped_version("1.1.1", "patch"), "1.1.2")


if __name__ == "__main__":
    unittest.main()
