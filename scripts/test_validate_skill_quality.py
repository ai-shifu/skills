#!/usr/bin/env python3
"""Tests for repository-level validation helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_skill_quality import IssueBag, validate_codex_plugin_manifest


class CodexPluginManifestValidationTest(unittest.TestCase):
    def test_missing_codex_plugin_manifest_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            issues = IssueBag()

            validate_codex_plugin_manifest(repo_root, issues)

            self.assertIn(
                ".codex-plugin/plugin.json is required for Codex plugin installs",
                issues.errors,
            )

    def test_valid_codex_plugin_manifest_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "skills").mkdir()
            manifest_dir = repo_root / ".codex-plugin"
            manifest_dir.mkdir()
            (manifest_dir / "plugin.json").write_text(
                """{
  "name": "ai-shifu-skills",
  "version": "0.1.0",
  "description": "Reusable AI-Shifu skills for course production.",
  "author": {
    "name": "AI-Shifu"
  },
  "homepage": "https://github.com/ai-shifu/skills",
  "repository": "https://github.com/ai-shifu/skills",
  "license": "MIT",
  "keywords": ["ai-shifu", "skills", "course-authoring"],
  "skills": "./skills/",
  "interface": {
    "displayName": "AI-Shifu Skills",
    "shortDescription": "Course production skills for AI-Shifu.",
    "longDescription": "Reusable AI-Shifu skills for course topic advising, course script generation, and course deployment workflows.",
    "developerName": "AI-Shifu",
    "category": "Education",
    "capabilities": ["Interactive", "Read", "Write"]
  }
}
""",
                encoding="utf-8",
            )
            issues = IssueBag()

            validate_codex_plugin_manifest(repo_root, issues)

            self.assertEqual([], issues.errors)


if __name__ == "__main__":
    unittest.main()
