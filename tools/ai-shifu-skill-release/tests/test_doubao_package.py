from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ai_shifu_release.channels import doubao
from ai_shifu_release.skill_metadata import update_skill_frontmatter


class DoubaoPackageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = doubao.load_profile(
            Path(__file__).resolve().parents[1] / "channels/doubao/profile.json"
        )
        self.source = {
            "name": "ai-shifu-course-creator",
            "description": "Create and manage AI-Shifu courses.",
            "version_management": "standalone",
        }

    def test_manifest_uses_official_plugin_fields(self) -> None:
        manifest = doubao.render_plugin(self.profile, "1.2.3")
        self.assertEqual(manifest["name"], "ai-shifu")
        self.assertEqual(manifest["version"], "1.2.3")
        self.assertEqual(
            manifest["extensions"]["com.doubao"]["displayName"],
            {"zh": "AI师傅教学专家"},
        )
        self.assertEqual(
            manifest["extensions"]["com.doubao"]["icon"],
            "./com.doubao/assets/plugin-icon.png",
        )
        self.assertEqual(
            set(manifest), {"name", "version", "description", "extensions"}
        )

    def test_source_description_and_metadata_are_preserved(self) -> None:
        updates = doubao.skill_overrides(self.profile["skills"][0], self.source)
        self.assertEqual(
            updates,
            {
                "metadata.display_name": "课程制作管理",
                "metadata.display_description": self.source["description"],
                "version_management": "plugin",
            },
        )
        source = (
            "---\nname: ai-shifu-course-creator\n"
            "description: Create and manage AI-Shifu courses.\n"
            "metadata:\n  version: 1.2.3\n  version_management: standalone\n"
            "  short-description: Example\n---\n# Body\n"
        )
        result = update_skill_frontmatter(source, updates, "test")
        self.assertIn("  version_management: plugin\n", result)
        self.assertIn("  short-description: Example\n", result)
        self.assertIn('  display_name: "课程制作管理"\n', result)
        self.assertIn(
            '  display_description: "Create and manage AI-Shifu courses."\n', result
        )
        self.assertTrue(result.endswith("---\n# Body\n"))
        self.assertNotIn("\nlabel:", result)
        self.assertNotIn("\nicon:", result)

    def test_display_description_omits_search_only_abbreviation(self) -> None:
        source = dict(self.source, description="Create with MarkdownFlow (MDF).")
        overrides = doubao.skill_overrides(self.profile["skills"][0], source)
        self.assertEqual(
            overrides["metadata.display_description"], "Create with MarkdownFlow."
        )
        self.assertNotIn("description", overrides)
        self.assertEqual(source["description"], "Create with MarkdownFlow (MDF).")

    def test_adds_metadata_when_missing(self) -> None:
        text = "---\nname: report\ndescription: Report\n---\nBody\n"
        result = update_skill_frontmatter(
            text,
            {"metadata.display_name": "报告", "metadata.display_description": "Report"},
            "test",
        )
        self.assertIn(
            'metadata:\n  display_name: "报告"\n  display_description: "Report"', result
        )

    def test_rejects_invalid_or_duplicate_metadata(self) -> None:
        for metadata in (
            "metadata: {version: 1}\n",
            "metadata:\n  version: 1\n",
            "metadata:\n  one: a\n  one: b\n",
            "metadata:\n  nested:\n    item: value\n",
            "metadata:\n  a: x\nmetadata:\n  b: y\n",
        ):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                update_skill_frontmatter(
                    "---\nname: x\n" + metadata + "---\nbody\n",
                    {"metadata.display_name": "x"},
                    "test",
                )

    def test_rejects_bad_source_and_profile(self) -> None:
        for description in ("", " ", "x" * 1025):
            source = dict(self.source, description=description)
            with (
                self.subTest(description=description[:8]),
                self.assertRaisesRegex(ValueError, "description"),
            ):
                doubao.skill_overrides(self.profile["skills"][0], source)
        profile = copy.deepcopy(self.profile)
        profile["package_format"] = "unknown"
        with self.assertRaisesRegex(ValueError, "Unsupported Doubao package format"):
            doubao.validate_profile(profile)
        profile = copy.deepcopy(self.profile)
        profile["skills"][0]["name"] = "x" * 65
        with self.assertRaises(ValueError):
            doubao.validate_profile(profile)

    def test_legacy_profile_is_still_recognized(self) -> None:
        path = Path(__file__).parent / "fixtures/doubao-legacy-profile.json"
        legacy = json.loads(path.read_text())
        doubao.validate_profile(legacy)
        self.assertNotIn("package_format", legacy)


if __name__ == "__main__":
    unittest.main()
