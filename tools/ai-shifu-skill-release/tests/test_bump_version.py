import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_shifu_release import version_bump

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

    def add_cli_package(self, *, version="1.1.1", lock_version="1.1.1") -> Path:
        seed = Path(self.tmp.name) / "seed"
        skill = seed / "skills/ai-shifu-course-creator/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(SKILL_MD, encoding="utf-8")
        package = {"name": "@ai-shifu/cli", "version": version, "bin": {"shifu": "cli/shifu.mjs"}}
        lock = {
            "name": "@ai-shifu/cli", "version": lock_version, "lockfileVersion": 3,
            "packages": {"": {"name": "@ai-shifu/cli", "version": lock_version}},
        }
        (seed / "package.json").write_text(json.dumps(package), encoding="utf-8")
        (seed / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        git("add", "--all", cwd=seed)
        git("commit", "--quiet", "-m", "add CLI", cwd=seed)
        git("push", "--quiet", "origin", "main", cwd=seed)
        return seed

    def test_bump_pushes_branch_without_touching_main(self) -> None:
        args = make_args(skill_version="1.2.0", repo_url=self.repo_url)
        result = version_bump.bump(args)
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
            "chore: bump version to v1.2.0",
        )
        self.assertEqual(
            git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD", cwd=check),
            "skills/demo-skill/SKILL.md",
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

    def test_bump_rejects_non_increasing_version(self) -> None:
        args = make_args(skill_version="1.1.1", repo_url=self.repo_url)
        with self.assertRaises(ValueError):
            version_bump.bump(args)

    def test_primary_skill_bump_updates_cli_and_lockfile_on_the_same_branch(self) -> None:
        self.add_cli_package()
        result = version_bump.bump(make_args(
            skill_name="ai-shifu-course-creator", skill_version="1.2.0", repo_url=self.repo_url,
        ))
        check = Path(self.tmp.name) / "check-cli"
        git("clone", "--quiet", "--branch", result["branch"], self.repo_url, str(check), cwd=check.parent)
        package = json.loads((check / "package.json").read_text())
        lock = json.loads((check / "package-lock.json").read_text())
        self.assertEqual(package["version"], "1.2.0")
        self.assertEqual(package["bin"], {"shifu": "cli/shifu.mjs"})
        self.assertEqual(lock["version"], "1.2.0")
        self.assertEqual(lock["packages"][""]["version"], "1.2.0")
        self.assertEqual(set(git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD", cwd=check).splitlines()), {
            "package.json", "package-lock.json", "skills/ai-shifu-course-creator/SKILL.md",
        })
        self.assertEqual(json.loads(git("show", "origin/main:package.json", cwd=check))["version"], "1.1.1")
        self.assertIn("skill and CLI package", git("log", "-1", "--format=%b", cwd=check))

    def test_primary_bump_rejects_drift_before_changing_package_metadata(self) -> None:
        seed = self.add_cli_package(lock_version="1.0.0")
        before = (seed / "package.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "lockfile version"):
            version_bump.update_cli_version(seed, "ai-shifu-course-creator", "1.1.1", "1.2.0")
        self.assertEqual((seed / "package.json").read_bytes(), before)

    def test_companion_skill_bump_does_not_change_cli_version(self) -> None:
        seed = self.add_cli_package()
        before = (seed / "package.json").read_bytes()
        self.assertFalse(version_bump.update_cli_version(seed, "demo-skill", "1.1.1", "1.2.0"))
        self.assertEqual((seed / "package.json").read_bytes(), before)

    def test_primary_bump_rejects_non_stable_versions_before_writing_metadata(self) -> None:
        seed = self.add_cli_package()
        before = {name: (seed / name).read_bytes() for name in ("package.json", "package-lock.json")}
        for new in ("1.2.0-rc.1", "01.2.0", "1.02.0", "1.2.00", "1.2", "v1.2.0"):
            with self.subTest(new=new):
                with self.assertRaisesRegex(ValueError, "stable X.Y.Z"):
                    version_bump.update_cli_version(seed, "ai-shifu-course-creator", "1.1.1", new)
                for name, content in before.items():
                    self.assertEqual((seed / name).read_bytes(), content)

    def test_primary_prerelease_bump_does_not_push_a_branch(self) -> None:
        self.add_cli_package()
        before = git("ls-remote", "--heads", self.repo_url, cwd=Path(self.tmp.name))
        with self.assertRaisesRegex(ValueError, "stable X.Y.Z"):
            version_bump.bump(make_args(
                skill_name="ai-shifu-course-creator", skill_version="1.2.0-rc.1", repo_url=self.repo_url,
            ))
        self.assertEqual(git("ls-remote", "--heads", self.repo_url, cwd=Path(self.tmp.name)), before)

    def test_companion_prerelease_bump_preserves_existing_support(self) -> None:
        self.add_cli_package()
        result = version_bump.bump(make_args(skill_version="1.2.0-rc.1", repo_url=self.repo_url))
        self.assertEqual(result["new_version"], "1.2.0-rc.1")

    def test_bumped_version_levels(self) -> None:
        self.assertEqual(version_bump.bumped_version("1.1.1", "major"), "2.0.0")
        self.assertEqual(version_bump.bumped_version("1.1.1", "minor"), "1.2.0")
        self.assertEqual(version_bump.bumped_version("1.1.1", "patch"), "1.1.2")


if __name__ == "__main__":
    unittest.main()
