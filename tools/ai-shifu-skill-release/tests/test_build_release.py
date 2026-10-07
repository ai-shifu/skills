from __future__ import annotations

import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from support import ReleaseFixture

from ai_shifu_release import artifacts, build, skill_metadata
from ai_shifu_release import verify as verification
from ai_shifu_release.channels import doubao as doubao_channel
from ai_shifu_release.channels import workbuddy

TOOL_ROOT = Path(__file__).resolve().parents[1]


class BuildReleaseTest(ReleaseFixture, unittest.TestCase):
    def test_existing_output_cannot_hide_a_different_source_ref(self) -> None:
        release_dir = self.build(source_ref="main")
        commit = self.git("rev-parse", "main")
        with self.assertRaisesRegex(ValueError, "different source metadata"):
            self.build(source_ref=commit)
        report = json.loads((release_dir / "release.json").read_text())
        self.assertEqual(report["source"]["ref"], "main")

    def test_builds_all_artifacts_from_committed_source(self) -> None:
        release_dir = self.build()
        report = json.loads((release_dir / "release.json").read_text())
        clawhub = release_dir / report["artifacts"]["clawhub"]["directory"]
        skillhub = release_dir / report["artifacts"]["skillhub"]["directory"]

        self.assertEqual(report["schema_version"], 6)
        self.assertEqual(set(report["artifacts"]), set(artifacts.CHANNEL_ORDER))
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

        expected_skillhub = skill_metadata.render_skill_variant(
            self.source_skill_text,
            {
                "slug": "ai-shifu-course-creator",
                "displayName": "ai-shifu-course-creator",
            },
            "fixture",
            top_level_version="1.2.3",
        )
        self.assertEqual((skillhub / "SKILL.md").read_text(), expected_skillhub)
        skillhub_frontmatter, _ = skill_metadata.read_skill_document(
            skillhub / "SKILL.md"
        )
        self.assertIn("\nversion: 1.2.3", skillhub_frontmatter)
        self.assertEqual((skillhub / "references/guide.md").read_text(), "guide\n")

        expected_plugin = skill_metadata.update_skill_frontmatter(
            self.source_skill_text,
            {"version_management": "plugin"},
            "fixture",
        )
        for channel, expected_root in (("workbuddy", "workbuddy-ai-shifu-1.2.3"),):
            archive_path = release_dir / report["artifacts"][channel]["archive"]
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
            self.assertEqual(report["artifacts"][channel]["version"], "1.2.3")

        with zipfile.ZipFile(
            release_dir / report["artifacts"]["workbuddy"]["archive"]
        ) as archive:
            names = set(archive.namelist())
            config_path = "workbuddy-ai-shifu-1.2.3/.codebuddy-plugin/plugin.json"
            self.assertIn(config_path, names)
            self.assertNotIn(
                "workbuddy-ai-shifu-1.2.3/.workbuddy-plugin/plugin.json", names
            )
            plugin = json.loads(archive.read(config_path))
            agent = archive.read("workbuddy-ai-shifu-1.2.3/agents/ai-shifu.md").decode(
                "utf-8"
            )
            avatar = archive.read("workbuddy-ai-shifu-1.2.3/avatars/expert.png")
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
            (
                int.from_bytes(avatar[16:20], "big"),
                int.from_bytes(avatar[20:24], "big"),
            ),
            (512, 512),
        )

        doubao = report["artifacts"]["doubao"]
        doubao_root = release_dir / doubao["directory"]
        profile = doubao_channel.load_profile(
            Path(__file__).resolve().parents[1] / "channels/doubao/profile.json"
        )
        source_frontmatter = self.source_frontmatter(report)
        self.assertEqual(doubao_root.name, "doubao-ai-shifu-1.2.3")
        self.assertEqual(
            (doubao_root / "agent.yml").read_text(encoding="utf-8"),
            doubao_channel.render_agent_yml(profile, source_frontmatter),
        )
        self.assertEqual(
            sorted(path.name for path in (doubao_root / "workspace/skills").iterdir()),
            [
                "ai-shifu-course-creator",
                "ai-shifu-learning-report",
                "course-direction-advisor",
            ],
        )
        self.assertFalse(
            (doubao_root / "workspace/skills/ai-shifu-course-creator/icon.png").exists()
        )
        self.assertFalse(
            (
                doubao_root / "workspace/skills/ai-shifu-learning-report/icon.png"
            ).exists()
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
            self.assertFalse(
                any("__MACOSX" in name or "desktop" in name for name in names)
            )
        embedded = doubao["embedded_skills"]
        self.assertEqual(
            set(embedded),
            {
                "ai-shifu-course-creator",
                "ai-shifu-learning-report",
                "course-direction-advisor",
            },
        )
        creator_text = (
            doubao_root / "workspace/skills/ai-shifu-course-creator/SKILL.md"
        ).read_text(encoding="utf-8")
        creator_frontmatter = doubao_channel.parse_frontmatter(creator_text)
        self.assertEqual(creator_frontmatter["description"], "Test fixture.")
        self.assertEqual(creator_frontmatter["label"], "课程制作管理")
        self.assertEqual(creator_frontmatter["icon"], "")
        self.assertEqual(creator_frontmatter["version_management"], "plugin")
        report_text = (
            doubao_root / "workspace/skills/ai-shifu-learning-report/SKILL.md"
        ).read_text(encoding="utf-8")
        report_frontmatter = doubao_channel.parse_frontmatter(report_text)
        self.assertEqual(
            report_frontmatter["description"],
            "Build one privacy-safe learning report.",
        )
        self.assertEqual(report_frontmatter["label"], "课程学习报告")
        self.assertEqual(report_frontmatter["icon"], "")
        self.assertNotIn("version_management", report_frontmatter)
        report_body = skill_metadata.split_skill_document(
            report_text,
            "report",
        )[1]
        self.assertEqual(
            artifacts.content_hash(report_body.encode("utf-8")),
            embedded["ai-shifu-learning-report"]["body_sha256"],
        )
        advisor_root = doubao_root / "workspace/skills/course-direction-advisor"
        expected_advisor = skill_metadata.update_skill_frontmatter(
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
            advisor_prefix = (
                "doubao-ai-shifu-1.2.3/workspace/skills/course-direction-advisor"
            )
            self.assertEqual(
                archive.read(f"{advisor_prefix}/SKILL.md").decode(), expected_advisor
            )
            self.assertEqual(
                archive.read(f"{advisor_prefix}/references/guide.md"),
                b"advisor guide\n",
            )
        for channel in ("clawhub", "skillhub", "workbuddy"):
            with zipfile.ZipFile(
                release_dir / report["artifacts"][channel]["archive"]
            ) as archive:
                self.assertFalse(
                    any(
                        "course-direction-advisor" in name
                        for name in archive.namelist()
                    )
                )

        verification.verify(release_dir)

    def test_channel_templates_keep_git_file_modes(self) -> None:
        release_dir = self.build()
        report = json.loads((release_dir / "release.json").read_text())
        entries = {
            "workbuddy": "workbuddy-ai-shifu-1.2.3/agents/ai-shifu.md",
            "doubao": "doubao-ai-shifu-1.2.3/workspace/AGENTS.md",
        }
        for channel, entry in entries.items():
            with self.subTest(channel=channel):
                archive = release_dir / report["artifacts"][channel]["archive"]
                with zipfile.ZipFile(archive) as package:
                    self.assertEqual(
                        (package.getinfo(entry).external_attr >> 16) & 0o777, 0o644
                    )

    def test_builds_exact_commit_and_rejects_version_mismatch(self) -> None:
        commit = self.git("rev-parse", "feature/newer-version")
        release_dir = self.build(source_ref=commit, expected_version="8.8.8")
        report = json.loads((release_dir / "release.json").read_text())
        self.assertEqual(report["source"]["commit"], commit)
        self.assertEqual(report["source"]["ref"], commit)
        self.assertEqual(report["skill"]["version"], "8.8.8")
        with self.assertRaisesRegex(ValueError, "does not match expected"):
            self.build(source_ref=commit, expected_version="1.2.3")

    def test_build_uses_committed_channel_templates(self) -> None:
        commit = self.git("rev-parse", "main")
        template = (
            self.source_repo
            / "tools/ai-shifu-skill-release/channels/workbuddy/.codebuddy-plugin/plugin.json"
        )
        template.write_text("tampered working tree", encoding="utf-8")
        self.publisher_config.write_text(
            '[publisher]\nname = "Wrong Author"\nemail = "wrong@example.com"\n',
            encoding="utf-8",
        )
        release_dir = self.build(source_ref=commit)
        report = json.loads((release_dir / "release.json").read_text())
        archive = release_dir / report["artifacts"]["workbuddy"]["archive"]
        with zipfile.ZipFile(archive) as package:
            plugin = json.loads(
                package.read("workbuddy-ai-shifu-1.2.3/.codebuddy-plugin/plugin.json")
            )
        self.assertEqual(plugin["version"], "1.2.3")
        self.assertEqual(
            plugin["author"], {"name": "AI-Shifu", "email": "release@ai-shifu.cn"}
        )

    def test_build_requires_publisher_identity(self) -> None:
        self.publisher_config.write_text(
            '[publisher]\nname = "__PUBLISHER_NAME__"\nemail = "__PUBLISHER_EMAIL__"\n',
            encoding="utf-8",
        )
        self.git("add", "tools/ai-shifu-skill-release/publisher.toml")
        self.git("commit", "-m", "invalid author fixture")
        with self.assertRaisesRegex(
            ValueError, "publisher.toml publisher.name contains a placeholder"
        ):
            self.build()

    def test_build_uses_configured_author_even_with_environment_values(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "AISHIFU_PUBLISHER_NAME": "Wrong Author",
                "AISHIFU_PUBLISHER_EMAIL": "wrong@example.com",
            },
        ):
            root = self.extract_workbuddy(self.build(), "configured-author")
        plugin = json.loads((root / ".codebuddy-plugin/plugin.json").read_text())
        self.assertEqual(
            plugin["author"], {"name": "AI-Shifu", "email": "release@ai-shifu.cn"}
        )

    def test_release_manifest_is_reproducible_for_same_commit(self) -> None:
        commit = self.git("rev-parse", "main")
        first = self.build(source_ref=commit)
        second_output = self.root / "second-dist"
        args = SimpleNamespace(
            source_repo_url=str(self.source_repo),
            source_ref=commit,
            expected_version="1.2.3",
            skill_name="ai-shifu-course-creator",
            output=str(second_output),
        )
        second = build.build(args)
        self.assertEqual(
            (first / "release.json").read_bytes(),
            (second / "release.json").read_bytes(),
        )

    def test_pinned_build_ignores_later_main_changes(self) -> None:
        pinned = self.git("rev-parse", "main")
        self.git("add", "skills/ai-shifu-course-creator/SKILL.md")
        self.git("commit", "-m", "later main version")
        self.assertNotEqual(self.git("rev-parse", "main"), pinned)
        release_dir = self.build(source_ref=pinned, expected_version="1.2.3")
        report = json.loads((release_dir / "release.json").read_text())
        self.assertEqual(report["source"]["commit"], pinned)
        self.assertEqual(report["skill"]["version"], "1.2.3")

    def test_doubao_verification_uses_profile_from_release_source(self) -> None:
        release_dir = self.build()
        report_path = release_dir / "release.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        record = report["artifacts"]["doubao"]
        self.assertEqual(
            hashlib.sha256(record["source_profile_json"].encode("utf-8")).hexdigest(),
            record["source_profile_sha256"],
        )
        with patch.object(
            doubao_channel,
            "load_profile",
            side_effect=AssertionError("local profile used"),
        ):
            verification.verify(release_dir)
        record["source_profile_json"] = record["source_profile_json"].replace(
            "AI师傅教学专家", "Changed profile", 1
        )
        report_path.write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source profile is missing or differs"):
            verification.verify(release_dir)

    def test_workbuddy_rejects_legacy_config_directory(self) -> None:
        root = self.extract_workbuddy(self.build(), "legacy-workbuddy")
        legacy = root / ".workbuddy-plugin"
        (root / ".codebuddy-plugin").rename(legacy)

        with self.assertRaisesRegex(ValueError, "legacy .workbuddy-plugin"):
            workbuddy.validate_workbuddy_package(root, "1.2.3")

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
            workbuddy.validate_workbuddy_package(root, "1.2.3")

    def test_workbuddy_requires_matching_initial_prompt(self) -> None:
        root = self.extract_workbuddy(self.build(), "mismatched-prompt")
        config = root / ".codebuddy-plugin/plugin.json"
        plugin = json.loads(config.read_text(encoding="utf-8"))
        plugin["defaultInitPrompt"]["zh"] = "不一致的提示语"
        config.write_text(json.dumps(plugin, ensure_ascii=False), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "must match quickPrompts"):
            workbuddy.validate_workbuddy_package(root, "1.2.3")

    def test_workbuddy_rejects_invalid_avatar(self) -> None:
        root = self.extract_workbuddy(self.build(), "invalid-avatar")
        (root / "avatars/expert.png").write_bytes(b"not a png")

        with self.assertRaisesRegex(ValueError, "avatar must be a PNG"):
            workbuddy.validate_workbuddy_package(root, "1.2.3")

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
            workbuddy.validate_workbuddy_package(root, "1.2.3")

    def test_artifacts_are_deterministic_and_tampering_is_detected(self) -> None:
        first = self.build()
        first_report = json.loads((first / "release.json").read_text())
        (first / "release-report.json").write_text('{"status": "ready"}\n')
        hashes = {
            "clawhub": first_report["artifacts"]["clawhub"]["archive_sha256"],
            "skillhub": first_report["artifacts"]["skillhub"]["archive_sha256"],
            "workbuddy": first_report["artifacts"]["workbuddy"]["sha256"],
            "doubao": first_report["artifacts"]["doubao"]["archive_sha256"],
        }
        second = self.build()
        self.assertTrue((second / "release-report.json").exists())
        second_report = json.loads((second / "release.json").read_text())
        self.assertEqual(
            hashes["clawhub"], second_report["artifacts"]["clawhub"]["archive_sha256"]
        )
        self.assertEqual(
            hashes["skillhub"], second_report["artifacts"]["skillhub"]["archive_sha256"]
        )
        self.assertEqual(
            hashes["workbuddy"], second_report["artifacts"]["workbuddy"]["sha256"]
        )
        self.assertEqual(
            hashes["doubao"], second_report["artifacts"]["doubao"]["archive_sha256"]
        )

        clawhub = second / second_report["artifacts"]["clawhub"]["directory"]
        (clawhub / "SKILL.md").write_text("tampered\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            verification.verify(second)

    def test_frontmatter_updates_are_scoped_to_yaml(self) -> None:
        updated = skill_metadata.update_skill_frontmatter(
            self.source_skill_text,
            {
                "slug": "ai-shifu-course-creator",
                "displayName": "ai-shifu-course-creator",
            },
            "fixture",
        )

        _, source_body = skill_metadata.split_skill_document(
            self.source_skill_text, "source"
        )
        frontmatter, updated_body = skill_metadata.split_skill_document(
            updated, "updated"
        )
        self.assertEqual(updated_body, source_body)
        self.assertEqual(frontmatter.count("slug: ai-shifu-course-creator"), 1)
        self.assertIn("slug: body-example", updated_body)

    def test_nested_version_updates_preserve_metadata_location(self) -> None:
        updated = skill_metadata.update_skill_frontmatter(
            self.source_skill_text,
            {"version": "1.2.4", "version_management": "plugin"},
            "fixture",
        )
        frontmatter, body = skill_metadata.split_skill_document(updated, "fixture")
        self.assertIn(
            "metadata:\n  version: 1.2.4\n  version_management: plugin", frontmatter
        )
        self.assertNotIn("\nversion: 1.2.4", frontmatter)
        self.assertEqual(
            body,
            skill_metadata.split_skill_document(self.source_skill_text, "source")[1],
        )

    def test_verify_rejects_channel_body_drift_even_with_updated_hashes(self) -> None:
        release_dir = self.build()
        report_path = release_dir / "release.json"
        report = json.loads(report_path.read_text())
        skillhub = report["artifacts"]["skillhub"]
        skillhub_dir = release_dir / skillhub["directory"]
        skill_file = skillhub_dir / "SKILL.md"
        skill_file.write_text(
            skill_file.read_text().replace("# Fixture Skill", "# Changed Body")
        )
        skillhub_zip = release_dir / skillhub["archive"]
        artifacts.write_zip(skillhub_dir, skillhub_zip, skillhub["archive_root"])
        skillhub["tree_sha256"] = artifacts.tree_hash(skillhub_dir)
        skillhub["archive_sha256"] = artifacts.file_hash(skillhub_zip)
        hashes = [
            digest
            for channel in artifacts.CHANNEL_ORDER
            for digest in artifacts.artifact_hashes(report["artifacts"][channel])
        ]
        report["release_sha256"] = artifacts.release_hash(hashes)
        report_path.write_text(json.dumps(report))

        with self.assertRaisesRegex(ValueError, "skillhub directory content mismatch"):
            verification.verify(release_dir)

    def test_verify_requires_channel_specific_schema(self) -> None:
        release_dir = self.build()
        report_path = release_dir / "release.json"
        report = json.loads(report_path.read_text())
        report["schema_version"] = 5
        report_path.write_text(json.dumps(report))

        with self.assertRaisesRegex(ValueError, "rebuild with schema 6"):
            verification.verify(release_dir)

    def test_doubao_profile_tampering_is_rejected(self) -> None:
        release_dir = self.build()
        report = json.loads((release_dir / "release.json").read_text())
        root = release_dir / report["artifacts"]["doubao"]["directory"]
        profile = doubao_channel.load_profile(
            Path(__file__).resolve().parents[1] / "channels/doubao/profile.json"
        )
        source_frontmatter = self.source_frontmatter(report)
        (root / "README.md").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "README.md differs"):
            doubao_channel.validate_package(root, profile, source_frontmatter)

    def test_doubao_rejects_local_paths(self) -> None:
        release_dir = self.build()
        report = json.loads((release_dir / "release.json").read_text())
        root = release_dir / report["artifacts"]["doubao"]["directory"]
        profile = doubao_channel.load_profile(
            Path(__file__).resolve().parents[1] / "channels/doubao/profile.json"
        )
        source_frontmatter = self.source_frontmatter(report)
        identity = root / "workspace/IDENTITY.md"
        identity.write_text(
            identity.read_text(encoding="utf-8")
            + "\n读取 /Users/example/private/file.md\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "local path or private address"):
            doubao_channel.validate_package(root, profile, source_frontmatter)

    def test_verify_rejects_doubao_description_drift_with_updated_hashes(self) -> None:
        release_dir = self.build()
        report = json.loads((release_dir / "release.json").read_text())
        root = release_dir / report["artifacts"]["doubao"]["directory"]
        skill_file = root / "workspace/skills/ai-shifu-course-creator/SKILL.md"
        skill_file.write_text(
            skill_file.read_text().replace(
                "description: Test fixture.", "description: Channel rewrite."
            )
        )
        self.refresh_doubao_hashes(release_dir, report)

        with self.assertRaisesRegex(ValueError, "frontmatter mismatch.*description"):
            verification.verify(release_dir)

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
                    verification.verify(release_dir)


if __name__ == "__main__":
    unittest.main()
