"""Shared local source repository and release fixtures for offline tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

from ai_shifu_release import TOOL_ROOT, artifacts, build, skill_metadata


class ReleaseFixture:
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source_repo = self.root / "skills"
        shutil.copytree(
            TOOL_ROOT / "channels",
            self.source_repo / "tools/ai-shifu-skill-release/channels",
            symlinks=True,
        )
        self.workbuddy_config = (
            self.source_repo
            / "tools/ai-shifu-skill-release/channels/workbuddy/.codebuddy-plugin/plugin.json"
        )
        self.release_config = (
            self.source_repo / "tools/ai-shifu-skill-release/release.toml"
        )
        shutil.copy2(TOOL_ROOT / "release.toml", self.release_config)
        self.write_publisher("AI-Shifu", "release@ai-shifu.cn")
        self.output = self.root / "dist"
        self.skill = self.source_repo / "skills/ai-shifu-course-creator"
        self.skill.mkdir(parents=True)
        self.source_skill_text = (
            "---\n"
            "name: ai-shifu-course-creator\n"
            "description: Test fixture.\n"
            "metadata:\n"
            "  version: 1.2.3\n"
            "  version_management: standalone\n"
            "---\n\n"
            "# Fixture Skill\n\n"
            "slug: body-example\n"
            "displayName: body example\n"
            "version_management: body-example\n"
        )
        (self.skill / "SKILL.md").write_text(self.source_skill_text, encoding="utf-8")
        (self.skill / "references").mkdir()
        (self.skill / "references/guide.md").write_text("guide\n")
        (self.skill / "design").mkdir()
        (self.skill / "design/internal.md").write_text("internal\n")
        (self.skill / "evals").mkdir()
        (self.skill / "evals/cases.json").write_text("{}\n")
        self.env_example = "SHIFU_BASE_URL=https://app.ai-shifu.cn\nSHIFU_TOKEN=\n"
        (self.skill / ".env.example").write_text(self.env_example, encoding="utf-8")
        self.report_skill = self.source_repo / "skills/ai-shifu-learning-report"
        self.report_skill.mkdir(parents=True)
        self.report_skill_text = (
            "---\n"
            "name: ai-shifu-learning-report\n"
            "description: Build one privacy-safe learning report.\n"
            "---\n\n"
            "# Learning Report\n\n"
            "Use supplied or explicitly synthetic aggregate data.\n"
        )
        (self.report_skill / "SKILL.md").write_text(
            self.report_skill_text, encoding="utf-8"
        )
        (self.report_skill / "references").mkdir()
        (self.report_skill / "references/guide.md").write_text(
            "report guide\n", encoding="utf-8"
        )
        self.advisor_skill = self.source_repo / "skills/course-direction-advisor"
        self.advisor_skill.mkdir(parents=True)
        self.advisor_skill_text = (
            "---\n"
            "name: course-direction-advisor\n"
            "description: Select course topics from source materials and market evidence.\n"
            "metadata:\n"
            "  short-description: Validate course directions\n"
            "---\n\n"
            "# Course Topic Selection\n\n"
            "Keep recommendations within the source evidence boundary.\n"
        )
        (self.advisor_skill / "SKILL.md").write_text(
            self.advisor_skill_text, encoding="utf-8"
        )
        (self.advisor_skill / "references").mkdir()
        (self.advisor_skill / "references/guide.md").write_text(
            "advisor guide\n", encoding="utf-8"
        )
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Build Test")
        self.git("config", "user.email", "build@example.com")
        self.git("remote", "add", "origin", "git@example.com:ai-shifu/skills.git")
        self.git("add", ".")
        self.git("commit", "-m", "fixture")

        self.git("checkout", "-b", "feature/newer-version")
        (self.skill / "SKILL.md").write_text(
            (self.skill / "SKILL.md").read_text().replace("1.2.3", "8.8.8")
        )
        (self.report_skill / "SKILL.md").write_text(
            (self.report_skill / "SKILL.md")
            .read_text()
            .replace("Build one privacy-safe", "Feature branch")
        )
        (self.advisor_skill / "SKILL.md").write_text(
            self.advisor_skill_text.replace(
                "source evidence boundary", "feature branch"
            )
        )
        self.git("add", "skills/ai-shifu-course-creator/SKILL.md")
        self.git("add", "skills/ai-shifu-learning-report/SKILL.md")
        self.git("add", "skills/course-direction-advisor/SKILL.md")
        self.git("commit", "-m", "feature version")
        self.git("checkout", "main")

        # Neither another branch nor working-tree changes may enter the main build.
        (self.skill / ".env").write_text("TOKEN=private\n")
        (self.skill / ".update-check.json").write_text("{}\n")
        (self.skill / "SKILL.md").write_text(
            (self.skill / "SKILL.md").read_text().replace("1.2.3", "9.9.9")
        )
        (self.report_skill / "SKILL.md").write_text(
            (self.report_skill / "SKILL.md")
            .read_text()
            .replace("Build one privacy-safe", "Working tree")
        )
        (self.advisor_skill / "SKILL.md").write_text(
            self.advisor_skill_text.replace("source evidence boundary", "working tree")
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_publisher(self, name: str, email: str) -> None:
        document = self.release_config.read_text(encoding="utf-8")
        prefix, publisher = document.split("[publisher]\n", 1)
        _, channels = publisher.split("\n[", 1)
        self.release_config.write_text(
            f"{prefix}[publisher]\nname = {json.dumps(name)}\nemail = {json.dumps(email)}\n\n[{channels}",
            encoding="utf-8",
        )

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.source_repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def build(self, *, source_ref: str = "main", expected_version: str = "") -> Path:
        args = SimpleNamespace(
            source_repo_url=str(self.source_repo),
            source_ref=source_ref,
            expected_version=expected_version,
            skill_name="ai-shifu-course-creator",
            output=str(self.output),
        )
        return build.build(args)

    def extract_workbuddy(self, release_dir: Path, destination: str) -> Path:
        report = json.loads((release_dir / "release.json").read_text())
        artifact = report["artifacts"]["workbuddy"]
        target = self.root / destination
        with zipfile.ZipFile(release_dir / artifact["archive"]) as archive:
            archive.extractall(target)
        return target / f"workbuddy-ai-shifu-{report['skill']['version']}"

    @staticmethod
    def source_frontmatter(report: dict) -> dict[str, dict[str, str]]:
        return {
            name: skill_metadata.parse_frontmatter(record["source_frontmatter"])
            for name, record in report["artifacts"]["doubao"]["embedded_skills"].items()
        }

    @staticmethod
    def refresh_doubao_hashes(release_dir: Path, report: dict) -> None:
        doubao = report["artifacts"]["doubao"]
        root = release_dir / doubao["directory"]
        for name, record in doubao["embedded_skills"].items():
            record["tree_sha256"] = artifacts.tree_hash(
                root / "workspace" / "skills" / name
            )
        archive = release_dir / doubao["archive"]
        artifacts.write_zip(root, archive, doubao["archive_root"])
        doubao["tree_sha256"] = artifacts.tree_hash(root)
        doubao["archive_sha256"] = artifacts.file_hash(archive)
        hashes = [
            digest
            for channel in artifacts.CHANNEL_ORDER
            for digest in artifacts.artifact_hashes(report["artifacts"][channel])
        ]
        report["release_sha256"] = artifacts.release_hash(hashes)
        (release_dir / "release.json").write_text(json.dumps(report))
