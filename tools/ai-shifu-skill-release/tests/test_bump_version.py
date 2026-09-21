import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import bump_version

SKILL_MD = """---
name: Demo Skill
version: 1.1.1
version_management: standalone
---

# Demo

Body stays byte-identical.
"""

def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
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
        git("init", "--bare", "--quiet", "--initial-branch=main", str(self.origin), cwd=root)
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
        result = bump_version.bump(args)
        self.assertEqual(result["previous_version"], "1.1.1")
        self.assertEqual(result["new_version"], "1.2.0")
        self.assertEqual(result["branch"], "bump/demo-skill-v1.2.0")

        check = Path(self.tmp.name) / "check"
        git("clone", "--quiet", "--branch", result["branch"], self.repo_url, str(check), cwd=Path(self.tmp.name))
        text = (check / "skills/demo-skill/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("version: 1.2.0", text)
        self.assertEqual(text.split("---\n", 2)[2], SKILL_MD.split("---\n", 2)[2])  # body unchanged
        # main itself must not move: the merge is a human gate
        self.assertIn("version: 1.1.1", git("show", "origin/main:skills/demo-skill/SKILL.md", cwd=check))

    def test_bump_rejects_non_increasing_version(self) -> None:
        args = make_args(skill_version="1.1.1", repo_url=self.repo_url)
        with self.assertRaises(ValueError):
            bump_version.bump(args)

    def test_bumped_version_levels(self) -> None:
        self.assertEqual(bump_version.bumped_version("1.1.1", "major"), "2.0.0")
        self.assertEqual(bump_version.bumped_version("1.1.1", "minor"), "1.2.0")
        self.assertEqual(bump_version.bumped_version("1.1.1", "patch"), "1.1.2")


if __name__ == "__main__":
    unittest.main()
