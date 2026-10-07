import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import activate_manifest

MANIFEST = {
    "schema_version": 1,
    "skill_name": "demo-skill",
    "latest": "1.1.1",
    "min_supported": "0.0.0",
    "notes": "old",
    "check_interval_hours": 2,
    "published_at": "2026-07-16T00:00:00Z",
    "update_url": "https://github.com/ai-shifu/skills/tree/main/skills/demo-skill",
}

GOOD_CHANNELS = {
    "clawhub": {"status": "published"},
    "skillhub": {"status": "published"},
    "workbuddy": {"status": "submitted"},
    "qclaw": {"status": "verified"},
}


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def make_args(release_dir: Path, repo_url: str, **overrides) -> SimpleNamespace:
    defaults = {
        "release_dir": str(release_dir),
        "notes": "",
        "draft": False,
        "no_pr": True,
        "check_online": False,
        "allow_pending": [],
        "auto_notes": False,
        "repo_url": repo_url,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class ActivateManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="manifest-test-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
            os.environ[key] = "manifest-test"
            self.addCleanup(os.environ.pop, key, None)
        for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
            os.environ[key] = "manifest-test@example.com"
            self.addCleanup(os.environ.pop, key, None)

        self.origin = root / "website.git"
        git("init", "--bare", "--quiet", "--initial-branch=main", str(self.origin), cwd=root)
        seed = root / "seed"
        git("clone", "--quiet", f"file://{self.origin}", str(seed), cwd=root)
        manifest_dir = seed / "zh/skill-manifests"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "demo-skill.json").write_text(json.dumps(MANIFEST, indent=2) + "\n", encoding="utf-8")
        git("add", "--all", cwd=seed)
        git("commit", "--quiet", "-m", "seed", cwd=seed)
        git("push", "--quiet", "origin", "main", cwd=seed)
        self.repo_url = f"file://{self.origin}"

        self.release_dir = root / "release"
        self.release_dir.mkdir()
        (self.release_dir / "release.json").write_text(
            json.dumps({"skill": {"name": "demo-skill", "version": "1.2.0"}}), encoding="utf-8"
        )
        self.write_report(GOOD_CHANNELS)

    def write_report(self, channels: dict) -> None:
        (self.release_dir / "release-report.json").write_text(
            json.dumps({"channels": channels}), encoding="utf-8"
        )

    def test_activate_pushes_manifest_branch(self) -> None:
        args = make_args(self.release_dir, self.repo_url)
        result = activate_manifest.activate(args)
        self.assertEqual(result["branch"], "codex/bump-demo-skill-manifest-v1.2.0")
        self.assertEqual(result["manifest"]["latest"], "1.2.0")
        self.assertEqual(result["manifest"]["notes"], "Release 1.2.0")

        check = Path(self.tmp.name) / "check"
        git("clone", "--quiet", "--branch", result["branch"], self.repo_url, str(check), cwd=Path(self.tmp.name))
        manifest = json.loads((check / "zh/skill-manifests/demo-skill.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["latest"], "1.2.0")
        self.assertEqual(manifest["update_url"], MANIFEST["update_url"])
        old = json.loads(git("show", "origin/main:zh/skill-manifests/demo-skill.json", cwd=check))
        self.assertEqual(old["latest"], "1.1.1")  # main untouched: merge is a human gate

    def test_activate_blocks_when_channel_not_ready(self) -> None:
        channels = dict(GOOD_CHANNELS)
        channels["skillhub"] = {"status": "failed"}
        self.write_report(channels)
        with self.assertRaises(ValueError) as ctx:
            activate_manifest.activate(make_args(self.release_dir, self.repo_url))
        self.assertIn("skillhub=failed", str(ctx.exception))

    def test_activate_blocks_when_manual_channel_missing(self) -> None:
        channels = {key: value for key, value in GOOD_CHANNELS.items() if key != "workbuddy"}
        self.write_report(channels)
        with self.assertRaises(ValueError) as ctx:
            activate_manifest.activate(make_args(self.release_dir, self.repo_url))
        self.assertIn("workbuddy=missing", str(ctx.exception))

    def test_activate_allows_waived_manual_channel(self) -> None:
        channels = {key: value for key, value in GOOD_CHANNELS.items() if key != "workbuddy"}
        self.write_report(channels)
        args = make_args(self.release_dir, self.repo_url, allow_pending=["workbuddy"])
        result = activate_manifest.activate(args)
        self.assertEqual(result["manifest"]["latest"], "1.2.0")
        self.assertEqual(result["waived_channels"], ["workbuddy"])

    def test_activate_does_not_require_doubao(self) -> None:
        self.assertNotIn("doubao", GOOD_CHANNELS)
        result = activate_manifest.activate(make_args(self.release_dir, self.repo_url))
        self.assertEqual(result["manifest"]["latest"], "1.2.0")

    def test_collect_changes_between_versions(self) -> None:
        root = Path(self.tmp.name)
        skills_origin = root / "skills.git"
        git("init", "--bare", "--quiet", "--initial-branch=main", str(skills_origin), cwd=root)
        seed = root / "skills-seed"
        git("clone", "--quiet", f"file://{skills_origin}", str(seed), cwd=root)
        skill_dir = seed / "skills/demo-skill"
        skill_dir.mkdir(parents=True)

        def commit(subject: str, version: str, extra: str = "") -> None:
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: Demo\nversion: {version}\nversion_management: standalone\n---\n\nBody.\n{extra}",
                encoding="utf-8",
            )
            git("add", "--all", cwd=seed)
            git("commit", "--quiet", "-m", subject, cwd=seed)

        commit("chore: bump demo-skill to 1.1.0", "1.1.0")
        commit("chore: bump demo-skill to 1.1.1", "1.1.1")
        commit("fix: improve lesson pacing (#103)", "1.1.1", extra="pacing\n")
        commit("feat: add analytics guidance (#110)", "1.1.1", extra="analytics\n")
        commit("chore: bump demo-skill to 1.2.0", "1.2.0", extra="analytics\n")
        git("push", "--quiet", "origin", "main", cwd=seed)
        head = git("rev-parse", "HEAD", cwd=seed)

        workdir = root / "collect-work"
        workdir.mkdir()
        changes = activate_manifest.collect_changes(
            f"file://{skills_origin}", "demo-skill", "1.1.1", head, workdir
        )
        # Exclude the upper-bound bump commit; keep content changes newest first.
        self.assertEqual(
            changes, ["feat: add analytics guidance (#110)", "fix: improve lesson pacing (#103)"]
        )
        notes = activate_manifest.compose_notes("1.2.0", changes)
        self.assertEqual(notes, "Release 1.2.0: add analytics guidance (#110); improve lesson pacing (#103)")

    def test_compose_notes_truncates_to_schema_limit(self) -> None:
        notes = activate_manifest.compose_notes("1.2.0", [f"fix: change {i} " + "x" * 40 for i in range(20)])
        self.assertLessEqual(len(notes), 500)
        self.assertTrue(notes.endswith("..."))

    def test_update_manifest_rejects_min_supported_above_latest(self) -> None:
        manifest_path = Path(self.tmp.name) / "manifest.json"
        bad = dict(MANIFEST, min_supported="9.9.9")
        manifest_path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(ValueError):
            activate_manifest.update_manifest(manifest_path, "1.2.0", "note")


if __name__ == "__main__":
    unittest.main()
