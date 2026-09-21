from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

from scripts import build_release, doubao_package


class BuildReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source_repo = self.root / "skills"
        self.output = self.root / "dist"
        self.skill = self.source_repo / "skills/ai-shifu-course-creator"
        self.skill.mkdir(parents=True)
        self.source_skill_text = (
            "---\n"
            "name: ai-shifu-course-creator\n"
            "description: Test fixture.\n"
            "version: 1.2.3\n"
            "version_management: standalone\n"
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
        self.env_example = (
            "SHIFU_BASE_URL=https://app.ai-shifu.cn\n"
            "SHIFU_TOKEN=\n"
        )
        (self.skill / ".env.example").write_text(
            self.env_example, encoding="utf-8"
        )
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
            self.advisor_skill_text.replace("source evidence boundary", "feature branch")
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

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.source_repo, check=True, capture_output=True)

    def build(self) -> Path:
        args = SimpleNamespace(
            source_repo_url=str(self.source_repo),
            skill_name="ai-shifu-course-creator",
            output=str(self.output),
        )
        return build_release.build(args)

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
            name: build_release.parse_frontmatter(record["source_frontmatter"])
            for name, record in report["artifacts"]["doubao"][
                "embedded_skills"
            ].items()
        }

    @staticmethod
    def refresh_doubao_hashes(release_dir: Path, report: dict) -> None:
        doubao = report["artifacts"]["doubao"]
        root = release_dir / doubao["directory"]
        for name, record in doubao["embedded_skills"].items():
            record["tree_sha256"] = build_release.tree_hash(
                root / "workspace" / "skills" / name
            )
        archive = release_dir / doubao["archive"]
        build_release.write_zip(root, archive, doubao["archive_root"])
        doubao["tree_sha256"] = build_release.tree_hash(root)
        doubao["archive_sha256"] = build_release.file_hash(archive)
        hashes = [
            digest
            for channel in build_release.CHANNEL_ORDER
            for digest in build_release.artifact_hashes(report["artifacts"][channel])
        ]
        report["release_sha256"] = hashlib.sha256(
            "\0".join(hashes).encode()
        ).hexdigest()
        (release_dir / "release.json").write_text(json.dumps(report))

    def test_builds_all_artifacts_from_committed_source(self) -> None:
        release_dir = self.build()
        report = json.loads((release_dir / "release.json").read_text())
        clawhub = release_dir / report["artifacts"]["clawhub"]["directory"]
        skillhub = release_dir / report["artifacts"]["skillhub"]["directory"]

        self.assertEqual(report["schema_version"], 4)
        self.assertEqual(report["skill"]["version"], "1.2.3")
        self.assertFalse((clawhub / ".env").exists())
        self.assertEqual(
            (clawhub / ".env.example").read_text(encoding="utf-8"),
            self.env_example,
        )
        self.assertFalse((clawhub / ".update-check.json").exists())
        self.assertFalse((clawhub / "design").exists())
        self.assertFalse((clawhub / "evals").exists())
        self.assertEqual((clawhub / "SKILL.md").read_text(), self.source_skill_text)

        expected_skillhub = build_release.update_skill_frontmatter(
            self.source_skill_text,
            {
                "slug": "ai-shifu-course-creator",
                "displayName": "ai-shifu-course-creator",
            },
            "fixture",
        )
        self.assertEqual((skillhub / "SKILL.md").read_text(), expected_skillhub)
        self.assertEqual((skillhub / "references/guide.md").read_text(), "guide\n")

        expected_plugin = build_release.update_skill_frontmatter(
            self.source_skill_text,
            {"version_management": "plugin"},
            "fixture",
        )
        for platform, expected_root in (
            ("workbuddy", "workbuddy-ai-shifu-1.2.3"),
            ("qclaw", f"qclaw-ai-shifu-{report['artifacts']['qclaw']['version']}"),
        ):
            archive_path = release_dir / report["artifacts"][platform]["archive"]
            with zipfile.ZipFile(archive_path) as archive:
                skill_file = archive.read(
                    f"{expected_root}/skills/ai-shifu-course-creator/SKILL.md"
                ).decode()
                env_example = archive.read(
                    f"{expected_root}/skills/ai-shifu-course-creator/.env.example"
                ).decode()
            self.assertEqual(skill_file, expected_plugin)
            self.assertEqual(env_example, self.env_example)
            # Plugin versions follow SKILL.md; the repository stores no version of its own.
            self.assertEqual(report["artifacts"][platform]["version"], "1.2.3")

        with zipfile.ZipFile(release_dir / report["artifacts"]["workbuddy"]["archive"]) as archive:
            names = set(archive.namelist())
            config_path = "workbuddy-ai-shifu-1.2.3/.codebuddy-plugin/plugin.json"
            self.assertIn(config_path, names)
            self.assertNotIn(
                "workbuddy-ai-shifu-1.2.3/.workbuddy-plugin/plugin.json", names
            )
            plugin = json.loads(
                archive.read(config_path)
            )
            agent = archive.read(
                "workbuddy-ai-shifu-1.2.3/agents/ai-shifu.md"
            ).decode("utf-8")
            avatar = archive.read(
                "workbuddy-ai-shifu-1.2.3/avatars/expert.png"
            )
        self.assertEqual(plugin["version"], "1.2.3")
        self.assertEqual(len(plugin["displayDescription"]["zh"]), 47)
        self.assertEqual(len(plugin["tags"]), 3)
        self.assertEqual(len(plugin["quickPrompts"]), 3)
        self.assertEqual(plugin["defaultInitPrompt"], plugin["quickPrompts"][0])
        self.assertIn("displayName:\n  en: AI-Shifu\n  zh: AI师傅\n", agent)
        self.assertIn(
            "profession:\n  en: AI-Shifu Course Production Expert\n"
            "  zh: AI师傅课程制作专家\n",
            agent,
        )
        self.assertNotIn("\ntools:", agent)
        self.assertLessEqual(len(avatar), 500 * 1024)
        self.assertEqual(avatar[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(
            (int.from_bytes(avatar[16:20], "big"), int.from_bytes(avatar[20:24], "big")),
            (512, 512),
        )

        doubao = report["artifacts"]["doubao"]
        doubao_root = release_dir / doubao["directory"]
        profile = doubao_package.load_profile(
            Path(__file__).resolve().parents[1] / "channels/doubao/profile.json"
        )
        source_frontmatter = self.source_frontmatter(report)
        self.assertEqual(doubao_root.name, "doubao-ai-shifu-1.2.3")
        self.assertEqual(
            (doubao_root / "agent.yml").read_text(encoding="utf-8"),
            doubao_package.render_agent_yml(profile, source_frontmatter),
        )
        self.assertEqual(
            sorted(path.name for path in (doubao_root / "workspace/skills").iterdir()),
            ["ai-shifu-course-creator", "ai-shifu-learning-report", "course-direction-advisor"],
        )
        self.assertFalse(
            (doubao_root / "workspace/skills/ai-shifu-course-creator/icon.png").exists()
        )
        self.assertFalse(
            (doubao_root / "workspace/skills/ai-shifu-learning-report/icon.png").exists()
        )
        self.assertFalse(
            (doubao_root / "workspace/skills/ai-shifu-course-creator/.env").exists()
        )
        with zipfile.ZipFile(release_dir / doubao["archive"]) as archive:
            names = archive.namelist()
            self.assertTrue(names)
            self.assertTrue(
                all(name.startswith("doubao-ai-shifu-1.2.3/") for name in names)
            )
            self.assertFalse(any("__MACOSX" in name or "desktop" in name for name in names))
        embedded = doubao["embedded_skills"]
        self.assertEqual(
            set(embedded),
            {"ai-shifu-course-creator", "ai-shifu-learning-report", "course-direction-advisor"},
        )
        creator_text = (
            doubao_root / "workspace/skills/ai-shifu-course-creator/SKILL.md"
        ).read_text(encoding="utf-8")
        creator_frontmatter = doubao_package.parse_frontmatter(creator_text)
        self.assertEqual(creator_frontmatter["description"], "Test fixture.")
        self.assertEqual(creator_frontmatter["label"], "课程制作管理")
        self.assertEqual(creator_frontmatter["icon"], "")
        self.assertEqual(creator_frontmatter["version_management"], "plugin")
        report_text = (
            doubao_root / "workspace/skills/ai-shifu-learning-report/SKILL.md"
        ).read_text(encoding="utf-8")
        report_frontmatter = doubao_package.parse_frontmatter(report_text)
        self.assertEqual(
            report_frontmatter["description"],
            "Build one privacy-safe learning report.",
        )
        self.assertEqual(report_frontmatter["label"], "课程学习报告")
        self.assertEqual(report_frontmatter["icon"], "")
        self.assertNotIn("version_management", report_frontmatter)
        report_body = build_release.split_skill_document(
            report_text,
            "report",
        )[1]
        self.assertEqual(
            build_release.content_hash(report_body.encode("utf-8")),
            embedded["ai-shifu-learning-report"]["body_sha256"],
        )
        advisor_root = doubao_root / "workspace/skills/course-direction-advisor"
        expected_advisor = build_release.update_skill_frontmatter(
            self.advisor_skill_text,
            {"label": "做课方向建议", "icon": ""},
            "advisor",
        )
        self.assertEqual((advisor_root / "SKILL.md").read_text(), expected_advisor)
        self.assertEqual(
            (advisor_root / "references/guide.md").read_text(), "advisor guide\n"
        )
        self.assertEqual(
            embedded["course-direction-advisor"]["source_commit"],
            report["source"]["commit"],
        )
        self.assertEqual(
            set(embedded["course-direction-advisor"]["source_files"]),
            {"SKILL.md", "references/guide.md"},
        )
        with zipfile.ZipFile(release_dir / doubao["archive"]) as archive:
            advisor_prefix = "doubao-ai-shifu-1.2.3/workspace/skills/course-direction-advisor"
            self.assertEqual(
                archive.read(f"{advisor_prefix}/SKILL.md").decode(), expected_advisor
            )
            self.assertEqual(
                archive.read(f"{advisor_prefix}/references/guide.md"), b"advisor guide\n"
            )
        for channel in ("clawhub", "skillhub", "workbuddy", "qclaw"):
            with zipfile.ZipFile(release_dir / report["artifacts"][channel]["archive"]) as archive:
                self.assertFalse(
                    any("course-direction-advisor" in name for name in archive.namelist())
                )

        build_release.verify(release_dir)

    def test_workbuddy_rejects_legacy_config_directory(self) -> None:
        root = self.extract_workbuddy(self.build(), "legacy-workbuddy")
        legacy = root / ".workbuddy-plugin"
        (root / ".codebuddy-plugin").rename(legacy)

        with self.assertRaisesRegex(ValueError, "legacy .workbuddy-plugin"):
            build_release.validate_workbuddy_package(root, "1.2.3")

    def test_workbuddy_requires_bilingual_agent_metadata(self) -> None:
        root = self.extract_workbuddy(self.build(), "missing-agent-metadata")
        agent = root / "agents/ai-shifu.md"
        agent.write_text(
            agent.read_text(encoding="utf-8").replace(
                "displayName:\n  en: AI-Shifu\n  zh: AI师傅\n",
                "displayName:\n  en: AI-Shifu\n",
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "agent displayName.zh"):
            build_release.validate_workbuddy_package(root, "1.2.3")

    def test_workbuddy_requires_matching_initial_prompt(self) -> None:
        root = self.extract_workbuddy(self.build(), "mismatched-prompt")
        config = root / ".codebuddy-plugin/plugin.json"
        plugin = json.loads(config.read_text(encoding="utf-8"))
        plugin["defaultInitPrompt"]["zh"] = "不一致的提示语"
        config.write_text(json.dumps(plugin, ensure_ascii=False), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "must match quickPrompts"):
            build_release.validate_workbuddy_package(root, "1.2.3")

    def test_workbuddy_rejects_invalid_avatar(self) -> None:
        root = self.extract_workbuddy(self.build(), "invalid-avatar")
        (root / "avatars/expert.png").write_bytes(b"not a png")

        with self.assertRaisesRegex(ValueError, "avatar must be a PNG"):
            build_release.validate_workbuddy_package(root, "1.2.3")

    def test_workbuddy_rejects_agent_tools(self) -> None:
        root = self.extract_workbuddy(self.build(), "agent-tools")
        agent = root / "agents/ai-shifu.md"
        agent.write_text(
            agent.read_text(encoding="utf-8").replace(
                "maxTurns: 80\n", "tools: [Read, Write]\nmaxTurns: 80\n"
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "must not declare tools"):
            build_release.validate_workbuddy_package(root, "1.2.3")

    def test_artifacts_are_deterministic_and_tampering_is_detected(self) -> None:
        first = self.build()
        first_report = json.loads((first / "release.json").read_text())
        (first / "release-report.json").write_text('{"status": "ready"}\n')
        hashes = {
            "clawhub": first_report["artifacts"]["clawhub"]["archive_sha256"],
            "skillhub": first_report["artifacts"]["skillhub"]["archive_sha256"],
            "workbuddy": first_report["artifacts"]["workbuddy"]["sha256"],
            "qclaw": first_report["artifacts"]["qclaw"]["sha256"],
            "doubao": first_report["artifacts"]["doubao"]["archive_sha256"],
        }
        second = self.build()
        self.assertTrue((second / "release-report.json").exists())
        second_report = json.loads((second / "release.json").read_text())
        self.assertEqual(hashes["clawhub"], second_report["artifacts"]["clawhub"]["archive_sha256"])
        self.assertEqual(hashes["skillhub"], second_report["artifacts"]["skillhub"]["archive_sha256"])
        self.assertEqual(hashes["workbuddy"], second_report["artifacts"]["workbuddy"]["sha256"])
        self.assertEqual(hashes["qclaw"], second_report["artifacts"]["qclaw"]["sha256"])
        self.assertEqual(
            hashes["doubao"], second_report["artifacts"]["doubao"]["archive_sha256"]
        )

        clawhub = second / second_report["artifacts"]["clawhub"]["directory"]
        (clawhub / "SKILL.md").write_text("tampered\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            build_release.verify(second)

    def test_frontmatter_updates_are_scoped_to_yaml(self) -> None:
        updated = build_release.update_skill_frontmatter(
            self.source_skill_text,
            {
                "slug": "ai-shifu-course-creator",
                "displayName": "ai-shifu-course-creator",
            },
            "fixture",
        )

        _, source_body = build_release.split_skill_document(self.source_skill_text, "source")
        frontmatter, updated_body = build_release.split_skill_document(updated, "updated")
        self.assertEqual(updated_body, source_body)
        self.assertEqual(frontmatter.count("slug: ai-shifu-course-creator"), 1)
        self.assertIn("slug: body-example", updated_body)

    def test_verify_rejects_channel_body_drift_even_with_updated_hashes(self) -> None:
        release_dir = self.build()
        report_path = release_dir / "release.json"
        report = json.loads(report_path.read_text())
        skillhub = report["artifacts"]["skillhub"]
        skillhub_dir = release_dir / skillhub["directory"]
        skill_file = skillhub_dir / "SKILL.md"
        skill_file.write_text(skill_file.read_text().replace("# Fixture Skill", "# Changed Body"))
        skillhub_zip = release_dir / skillhub["archive"]
        build_release.write_zip(skillhub_dir, skillhub_zip, skillhub["archive_root"])
        skillhub["tree_sha256"] = build_release.tree_hash(skillhub_dir)
        skillhub["archive_sha256"] = build_release.file_hash(skillhub_zip)
        hashes = [
            digest
            for channel in build_release.CHANNEL_ORDER
            for digest in build_release.artifact_hashes(report["artifacts"][channel])
        ]
        report["release_sha256"] = hashlib.sha256("\0".join(hashes).encode()).hexdigest()
        report_path.write_text(json.dumps(report))

        with self.assertRaisesRegex(ValueError, "skillhub directory content mismatch"):
            build_release.verify(release_dir)

    def test_verify_requires_channel_specific_schema(self) -> None:
        release_dir = self.build()
        report_path = release_dir / "release.json"
        report = json.loads(report_path.read_text())
        report["schema_version"] = 1
        report_path.write_text(json.dumps(report))

        with self.assertRaisesRegex(ValueError, "rebuild with schema 4"):
            build_release.verify(release_dir)

    def test_doubao_profile_tampering_is_rejected(self) -> None:
        release_dir = self.build()
        report = json.loads((release_dir / "release.json").read_text())
        root = release_dir / report["artifacts"]["doubao"]["directory"]
        profile = doubao_package.load_profile(
            Path(__file__).resolve().parents[1] / "channels/doubao/profile.json"
        )
        source_frontmatter = self.source_frontmatter(report)
        (root / "README.md").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "README.md differs"):
            doubao_package.validate_package(root, profile, source_frontmatter)

    def test_doubao_rejects_local_paths(self) -> None:
        release_dir = self.build()
        report = json.loads((release_dir / "release.json").read_text())
        root = release_dir / report["artifacts"]["doubao"]["directory"]
        profile = doubao_package.load_profile(
            Path(__file__).resolve().parents[1] / "channels/doubao/profile.json"
        )
        source_frontmatter = self.source_frontmatter(report)
        identity = root / "workspace/IDENTITY.md"
        identity.write_text(
            identity.read_text(encoding="utf-8") + "\n读取 /Users/example/private/file.md\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "local path or private address"):
            doubao_package.validate_package(root, profile, source_frontmatter)

    def test_verify_rejects_doubao_description_drift_with_updated_hashes(self) -> None:
        release_dir = self.build()
        report = json.loads((release_dir / "release.json").read_text())
        root = release_dir / report["artifacts"]["doubao"]["directory"]
        skill_file = (
            root / "workspace/skills/ai-shifu-course-creator/SKILL.md"
        )
        skill_file.write_text(
            skill_file.read_text().replace(
                "description: Test fixture.", "description: Channel rewrite."
            )
        )
        self.refresh_doubao_hashes(release_dir, report)

        with self.assertRaisesRegex(ValueError, "frontmatter mismatch.*description"):
            build_release.verify(release_dir)

    def test_verify_rejects_doubao_source_file_drift_with_updated_hashes(self) -> None:
        for mutation in ("change", "extra"):
            with self.subTest(mutation=mutation):
                self.output = self.root / f"dist-{mutation}"
                release_dir = self.build()
                report = json.loads((release_dir / "release.json").read_text())
                root = release_dir / report["artifacts"]["doubao"]["directory"]
                report_root = root / "workspace/skills/ai-shifu-learning-report"
                if mutation == "change":
                    (report_root / "references/guide.md").write_text("changed\n")
                else:
                    (report_root / "references/extra.md").write_text("extra\n")
                self.refresh_doubao_hashes(release_dir, report)

                with self.assertRaisesRegex(
                    ValueError, "source file (set )?mismatch|source file differs"
                ):
                    build_release.verify(release_dir)

if __name__ == "__main__":
    unittest.main()
