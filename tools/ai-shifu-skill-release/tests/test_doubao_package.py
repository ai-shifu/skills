from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts import doubao_package


class DoubaoPackageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = doubao_package.load_profile(
            Path(__file__).resolve().parents[1] / "channels/doubao/profile.json"
        )
        self.source_frontmatter = {
            "ai-shifu-course-creator": {
                "name": "ai-shifu-course-creator",
                "description": "Create and manage AI-Shifu courses.",
                "version": "1.2.7",
                "version_management": "standalone",
            },
            "ai-shifu-learning-report": {
                "name": "ai-shifu-learning-report",
                "description": "Create a privacy-safe AI-Shifu learning report.",
            },
            "course-direction-advisor": {
                "name": "course-direction-advisor",
                "description": "Select course topics from source materials and market evidence.",
            },
        }

    def test_generated_surfaces_share_recommended_instructions(self) -> None:
        agent = doubao_package.render_agent_yml(
            self.profile, self.source_frontmatter
        )
        readme = doubao_package.render_readme(self.profile)
        for instruction in self.profile["recommended_instructions"]:
            self.assertIn(instruction, agent)
            self.assertIn(instruction, readme)
        first = self.profile["recommended_instructions"][0]
        self.assertIn(f'zh-CN: {doubao_package.quote(first)}', agent)
        self.assertIn('id: "ai-shifu"', agent)
        self.assertIn('name: "AI师傅教学专家"', agent)
        self.assertIn("AI师傅教学专家", agent)
        self.assertNotRegex(agent, doubao_package.AI_SHIFU_SPACING_PATTERN)
        self.assertIn('icon: ""', agent)
        self.assertIn(
            'description: "Create and manage AI-Shifu courses."', agent
        )
        self.assertIn('name: "course-direction-advisor"', agent)
        self.assertIn('display_name: "做课方向建议"', agent)
        self.assertIn(
            'description: "Select course topics from source materials and market evidence."',
            agent,
        )
        self.assertEqual(
            first,
            "以“为什么要学习AI”为主题，创建一门AI师傅课程",
        )
        self.assertEqual(
            self.profile["recommended_instructions"][1],
            "我想做一门跟 AI 相关的课，帮我找找具体什么方向比较好？",
        )
        self.assertEqual(
            self.profile["recommended_instructions"][2],
            "帮我把这份上传的素材转成AI师傅课程",
        )
        self.assertIn("从0开始建课", self.profile["core_scenarios"][0])
        self.assertIn("做课方向建议", self.profile["core_scenarios"][1])
        self.assertIn("上传自己的PPT", self.profile["core_scenarios"][2])
        for scenario, readme_scenario in zip(
            self.profile["core_scenarios"], self.profile["readme_scenarios"]
        ):
            self.assertEqual(
                scenario, f"{readme_scenario['name']}：{readme_scenario['description']}"
            )

    def test_rejects_spacing_inside_ai_shifu_brand_in_agent_yml(self) -> None:
        source_frontmatter = copy.deepcopy(self.source_frontmatter)
        source_frontmatter["ai-shifu-learning-report"]["description"] = (
            "Create an AI 师傅 learning report."
        )
        with self.assertRaisesRegex(ValueError, "spaces inside the AI-Shifu brand name"):
            doubao_package.render_agent_yml(self.profile, source_frontmatter)

    def test_skill_overrides_are_limited_to_doubao_required_fields(self) -> None:
        skills = {skill["name"]: skill for skill in self.profile["skills"]}
        creator = doubao_package.skill_overrides(
            skills["ai-shifu-course-creator"],
            self.source_frontmatter["ai-shifu-course-creator"],
        )
        report = doubao_package.skill_overrides(
            skills["ai-shifu-learning-report"],
            self.source_frontmatter["ai-shifu-learning-report"],
        )
        advisor = doubao_package.skill_overrides(
            skills["course-direction-advisor"],
            self.source_frontmatter["course-direction-advisor"],
        )

        self.assertEqual(
            creator,
            {
                "label": "课程制作管理",
                "icon": "",
                "version_management": "plugin",
            },
        )
        self.assertEqual(report, {"label": "课程学习报告", "icon": ""})
        self.assertEqual(advisor, {"label": "做课方向建议", "icon": ""})
        self.assertNotIn("description", creator)
        self.assertNotIn("name", creator)

    def test_rejects_conflicting_source_label_or_custom_icon(self) -> None:
        skill = self.profile["skills"][0]
        conflicting_label = dict(self.source_frontmatter[skill["name"]])
        conflicting_label["label"] = "另一个标签"
        with self.assertRaisesRegex(ValueError, "label conflicts"):
            doubao_package.skill_overrides(skill, conflicting_label)

        custom_icon = dict(self.source_frontmatter[skill["name"]])
        custom_icon["icon"] = "custom.png"
        with self.assertRaisesRegex(ValueError, "icon must be empty"):
            doubao_package.skill_overrides(skill, custom_icon)

    def test_allows_uploaded_material_only_in_third_instruction(self) -> None:
        self.assertRegex(
            self.profile["recommended_instructions"][2],
            doubao_package.EXTERNAL_INPUT_PATTERN,
        )
        doubao_package.validate_profile(self.profile)

        for index in (0, 1):
            with self.subTest(index=index):
                profile = copy.deepcopy(self.profile)
                profile["recommended_instructions"][index] = (
                    "请上传一份课程附件，我会根据附件内容生成完整的课程教学脚本。"
                )
                with self.assertRaisesRegex(ValueError, "not zero-input"):
                    doubao_package.validate_profile(profile)

    def test_rejects_duplicate_or_insufficient_skills(self) -> None:
        profile = copy.deepcopy(self.profile)
        profile["skills"] = profile["skills"][:1]
        with self.assertRaisesRegex(ValueError, "at least two skills"):
            doubao_package.validate_profile(profile)

    def test_rejects_duplicate_channel_metadata_for_skills(self) -> None:
        profile = copy.deepcopy(self.profile)
        profile["skills"][0]["description"] = "Channel-owned description."
        with self.assertRaisesRegex(ValueError, "unsupported profile fields"):
            doubao_package.validate_profile(profile)


if __name__ == "__main__":
    unittest.main()
