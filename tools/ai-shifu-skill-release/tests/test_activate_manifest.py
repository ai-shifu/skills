import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai_shifu_release import manifest as manifest_workflow

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
}


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
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
    def test_collect_changes_requires_a_fixed_source_sha(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(manifest_workflow, "run") as git,
        ):
            for upper in ("", "HEAD", "main"):
                with (
                    self.subTest(upper=upper),
                    self.assertRaisesRegex(ValueError, "full source commit SHA"),
                ):
                    manifest_workflow.collect_changes(
                        "unused",
                        "ai-shifu-course-creator",
                        "1.0.0",
                        upper,
                        Path(temporary),
                    )
            git.assert_not_called()

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
        manifest_dir = seed / "zh/skill-manifests"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "demo-skill.json").write_text(
            json.dumps(MANIFEST, indent=2) + "\n", encoding="utf-8"
        )
        git("add", "--all", cwd=seed)
        git("commit", "--quiet", "-m", "seed", cwd=seed)
        git("push", "--quiet", "origin", "main", cwd=seed)
        self.repo_url = f"file://{self.origin}"

        self.release_dir = root / "release"
        self.release_dir.mkdir()
        (self.release_dir / "release.json").write_text(
            json.dumps({"skill": {"name": "demo-skill", "version": "1.2.0"}}),
            encoding="utf-8",
        )
        self.write_report(GOOD_CHANNELS)

    def write_report(self, channels: dict) -> None:
        (self.release_dir / "release-report.json").write_text(
            json.dumps({"channels": channels}), encoding="utf-8"
        )

    def test_activate_pushes_manifest_branch(self) -> None:
        args = make_args(self.release_dir, self.repo_url)
        with patch.object(manifest_workflow, "collect_changes") as collect:
            result = manifest_workflow.activate(args)
        collect.assert_not_called()
        self.assertEqual(result["branch"], "codex/bump-demo-skill-manifest-v1.2.0")
        self.assertEqual(result["manifest"]["latest"], "1.2.0")
        self.assertEqual(result["manifest"]["notes"], "Release 1.2.0")

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
        manifest = json.loads(
            (check / "zh/skill-manifests/demo-skill.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["latest"], "1.2.0")
        self.assertEqual(manifest["update_url"], MANIFEST["update_url"])
        old = json.loads(
            git("show", "origin/main:zh/skill-manifests/demo-skill.json", cwd=check)
        )
        self.assertEqual(
            old["latest"], "1.1.1"
        )  # main untouched: merge is a human gate

    def test_activate_blocks_when_channel_not_ready(self) -> None:
        channels = dict(GOOD_CHANNELS)
        channels["skillhub"] = {"status": "failed"}
        self.write_report(channels)
        with self.assertRaises(ValueError) as ctx:
            manifest_workflow.activate(make_args(self.release_dir, self.repo_url))
        self.assertIn("skillhub=failed", str(ctx.exception))

    def test_activate_blocks_when_manual_channel_missing(self) -> None:
        channels = {
            key: value for key, value in GOOD_CHANNELS.items() if key != "workbuddy"
        }
        self.write_report(channels)
        with self.assertRaises(ValueError) as ctx:
            manifest_workflow.activate(make_args(self.release_dir, self.repo_url))
        self.assertIn("workbuddy=missing", str(ctx.exception))

    def test_activate_allows_waived_manual_channel(self) -> None:
        channels = {
            key: value for key, value in GOOD_CHANNELS.items() if key != "workbuddy"
        }
        self.write_report(channels)
        args = make_args(self.release_dir, self.repo_url, allow_pending=["workbuddy"])
        result = manifest_workflow.activate(args)
        self.assertEqual(result["manifest"]["latest"], "1.2.0")
        self.assertEqual(result["waived_channels"], ["workbuddy"])

    def test_activate_does_not_require_doubao(self) -> None:
        self.assertNotIn("doubao", GOOD_CHANNELS)
        result = manifest_workflow.activate(make_args(self.release_dir, self.repo_url))
        self.assertEqual(result["manifest"]["latest"], "1.2.0")

    def test_activate_preserves_manual_notes(self) -> None:
        notes = "请按原计划升级，保留手写说明。"
        with patch.object(manifest_workflow, "collect_changes") as collect:
            result = manifest_workflow.activate(
                make_args(self.release_dir, self.repo_url, notes=notes)
            )
        collect.assert_not_called()
        self.assertEqual(result["manifest"]["notes"], notes)

    def test_activate_rejects_manual_and_automatic_notes_together(self) -> None:
        with self.assertRaisesRegex(ValueError, "either --notes or --auto-notes"):
            manifest_workflow.activate(
                make_args(
                    self.release_dir, self.repo_url, notes="manual", auto_notes=True
                )
            )

    def test_collect_changes_between_versions(self) -> None:
        root = Path(self.tmp.name)
        skills_origin = root / "skills.git"
        git(
            "init",
            "--bare",
            "--quiet",
            "--initial-branch=main",
            str(skills_origin),
            cwd=root,
        )
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
        other_skill = seed / "skills/other-skill"
        other_skill.mkdir()
        (other_skill / "SKILL.md").write_text("Other skill.\n", encoding="utf-8")
        git("add", "--all", cwd=seed)
        git("commit", "--quiet", "-m", "feat!: replace another skill (#115)", cwd=seed)
        head = git("rev-parse", "HEAD", cwd=seed)
        commit("feat: add later guidance (#120)", "1.1.1", extra="later\n")
        git("push", "--quiet", "origin", "main", cwd=seed)

        workdir = root / "collect-work"
        workdir.mkdir()
        changes = manifest_workflow.collect_changes(
            f"file://{skills_origin}", "demo-skill", "1.1.1", head, workdir
        )
        # Use the previous version's introduction at the frozen source commit;
        # exclude bumps, other skills, and changes made after that source.
        self.assertEqual(
            changes,
            [
                "feat: add analytics guidance (#110)",
                "fix: improve lesson pacing (#103)",
            ],
        )
        notes = manifest_workflow.compose_notes("1.2.0", changes)
        self.assertEqual(
            notes,
            "Release 1.2.0: add analytics guidance (#110); improve lesson pacing (#103)",
        )

    def test_collect_changes_keeps_more_than_thirty_prs(self) -> None:
        root = Path(self.tmp.name)
        source = root / "large-source"
        git("init", "--quiet", "--initial-branch=main", str(source), cwd=root)
        skill_dir = source / "skills/demo-skill"
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: Demo\nversion: 1.1.1\nversion_management: standalone\n---\n\nBody.\n",
            encoding="utf-8",
        )
        git("add", "--all", cwd=source)
        git("commit", "--quiet", "-m", "chore: bump demo-skill to 1.1.1", cwd=source)
        titles = []
        for number in range(100, 135):
            (skill_dir / "guide.md").write_text(f"Change {number}.\n", encoding="utf-8")
            title = f"fix: correct lesson {number} (#{number})"
            titles.append(title)
            git("add", "--all", cwd=source)
            git("commit", "--quiet", "-m", title, cwd=source)
        head = git("rev-parse", "HEAD", cwd=source)
        workdir = root / "large-collect"
        workdir.mkdir()
        changes = manifest_workflow.collect_changes(
            f"file://{source}", "demo-skill", "1.1.1", head, workdir
        )
        self.assertEqual(changes, list(reversed(titles)))

    def test_collect_changes_uses_structured_pr_titles(self) -> None:
        root = Path(self.tmp.name)
        source = root / "structured-source"
        git("init", "--quiet", "--initial-branch=main", str(source), cwd=root)
        skill_dir = source / "skills/demo-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: Demo\nversion: 1.1.1\nversion_management: standalone\n---\n\nBody.\n",
            encoding="utf-8",
        )
        git("add", "--all", cwd=source)
        git("commit", "--quiet", "-m", "chore: bump demo-skill to 1.1.1", cwd=source)
        boundary = git("rev-parse", "HEAD", cwd=source)
        workdir = root / "structured-collect"
        workdir.mkdir()
        with patch.object(
            manifest_workflow.release_notes,
            "collect_changes",
            return_value={
                "changes": [
                    {"number": 120, "title": "feat!: require a new course format"},
                    {"number": 110, "title": "feat: add analytics guidance"},
                    {"number": 103, "title": "fix: improve lesson pacing (#103)"},
                    {"number": 130, "title": "chore: bump demo-skill to 1.2.0"},
                ]
            },
        ) as collect:
            changes = manifest_workflow.collect_changes(
                f"file://{source}", "demo-skill", "1.1.1", boundary, workdir
            )
        collect.assert_called_once_with(
            workdir / "skills-history",
            boundary,
            base_ref=boundary,
            github_repository="",
            paths=("skills/demo-skill/",),
        )
        self.assertEqual(
            changes,
            [
                "feat!: require a new course format (#120)",
                "feat: add analytics guidance (#110)",
                "fix: improve lesson pacing (#103)",
            ],
        )
        self.assertIn(
            "! require a new course format (#120)",
            manifest_workflow.compose_notes("1.2.0", changes),
        )

    def test_compose_notes_omits_whole_changes_at_schema_limit(self) -> None:
        changes = [f"fix: change {i} " + "x" * 40 + f" (#{i + 100})" for i in range(20)]
        notes = manifest_workflow.compose_notes("1.2.0", changes)
        self.assertLessEqual(len(notes), 500)
        parts = notes.removeprefix("Release 1.2.0: ").split("; ")
        remaining = int(parts[-1].split()[1])
        self.assertEqual(
            parts[:-1],
            [change.removeprefix("fix: ") for change in changes[: len(parts) - 1]],
        )
        self.assertEqual(remaining + len(parts) - 1, len(changes))

    def test_compose_notes_handles_an_oversized_first_change(self) -> None:
        notes = manifest_workflow.compose_notes(
            "1.2.0", ["feat: " + "x" * 600 + " (#123)", "fix: improve pacing (#124)"]
        )
        self.assertEqual(notes, "Release 1.2.0: 2 changes; see the release changelog")

    def test_compose_notes_preserves_a_change_at_the_exact_limit(self) -> None:
        title = "x" * (500 - len("Release 1.2.0: "))
        notes = manifest_workflow.compose_notes("1.2.0", [f"fix: {title}"])
        self.assertEqual(notes, f"Release 1.2.0: {title}")

    def test_update_manifest_rejects_min_supported_above_latest(self) -> None:
        manifest_path = Path(self.tmp.name) / "manifest.json"
        bad = dict(MANIFEST, min_supported="9.9.9")
        manifest_path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(ValueError):
            manifest_workflow.update_manifest(manifest_path, "1.2.0", "note")


if __name__ == "__main__":
    unittest.main()
