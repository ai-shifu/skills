from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_skill_quality  # noqa: E402


class InteractionPolicyValidationTests(unittest.TestCase):
    def test_enabled_policy_requires_a_canonical_purpose(self):
        issues = validate_skill_quality.IssueBag()

        validate_skill_quality.validate_interaction_policy_example(
            {"mode": "enabled", "purposes": []},
            Path("example.md"),
            issues,
        )

        self.assertEqual(len(issues.errors), 1)
        self.assertIn("requires at least one purpose", issues.errors[0])

    def test_disabled_policy_rejects_interactive_lesson_content(self):
        issues = validate_skill_quality.IssueBag()
        lessons = [
            {
                "teaching_prompt": (
                    "Ask the learner to choose a path.\n"
                    "?[A | B]\n"
                    "Use {{learner_goal}} in the explanation.\n"
                    "After the learner answers, branch to the matching example."
                ),
                "used_variables": ["learner_goal"],
            }
        ]

        validate_skill_quality.validate_disabled_lesson_examples(
            lessons,
            Path("example.md"),
            issues,
        )

        self.assertEqual(len(issues.errors), 5)
        self.assertTrue(
            any("interaction syntax" in error for error in issues.errors)
        )
        self.assertTrue(
            any("solicit a learner response" in error for error in issues.errors)
        )
        self.assertTrue(
            any("branch on a learner response" in error for error in issues.errors)
        )

    def test_disabled_policy_rejects_localized_response_request(self):
        issues = validate_skill_quality.IssueBag()
        lessons = [
            {
                "teaching_prompt": "请学习者选择一个答案，然后按答案继续。",
                "used_variables": [],
            }
        ]

        validate_skill_quality.validate_disabled_lesson_examples(
            lessons,
            Path("example.md"),
            issues,
        )

        self.assertTrue(
            any("solicit a learner response" in error for error in issues.errors)
        )
        self.assertTrue(
            any("branch on a learner response" in error for error in issues.errors)
        )

    def test_disabled_policy_rejects_conditional_response_branches(self):
        prompts = [
            "If the learner chooses A, show the matching explanation.",
            "如果学习者选择 A，展示对应解释。",
            "Si l’apprenant choisit A, affichez l’explication correspondante.",
        ]

        for teaching_prompt in prompts:
            with self.subTest(teaching_prompt=teaching_prompt):
                issues = validate_skill_quality.IssueBag()
                validate_skill_quality.validate_disabled_lesson_examples(
                    [
                        {
                            "teaching_prompt": teaching_prompt,
                            "used_variables": [],
                        }
                    ],
                    Path("example.md"),
                    issues,
                )

                self.assertTrue(
                    any(
                        "branch on a learner response" in error
                        for error in issues.errors
                    )
                )

    def test_disabled_policy_accepts_worked_application(self):
        issues = validate_skill_quality.IssueBag()
        lessons = [
            {
                "teaching_prompt": (
                    "Explain the mechanism, then show a worked decision and "
                    "close with a reusable rule."
                ),
                "used_variables": [],
            }
        ]

        validate_skill_quality.validate_disabled_lesson_examples(
            lessons,
            Path("example.md"),
            issues,
        )

        self.assertEqual(issues.errors, [])


if __name__ == "__main__":
    unittest.main()
