"""Pinned detect-agent 0.1.8 conformance with synthetic lookup providers only."""

from __future__ import annotations

import json
import locale
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills/ai-shifu-course-creator/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import agent_detection as detector


FIXTURE = Path(__file__).resolve().parent / "fixtures/detect_agent/cases.json"
ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


class LookupProvider:
    """Synthetic provider with explicit name semantics and no enumeration API."""

    def __init__(self, values, *, insensitive=False):
        self.insensitive = insensitive
        self.values = {}
        for key, value in values.items():
            normalized = key.translate(ASCII_LOWER) if insensitive else key
            if normalized in self.values:
                raise AssertionError("Conformance keys must not collide")
            self.values[normalized] = value
        self.lookups = []

    def get(self, key, default=None):
        self.lookups.append(key)
        normalized = key.translate(ASCII_LOWER) if self.insensitive else key
        return self.values.get(normalized, default)

    def __iter__(self):
        raise AssertionError("Detection must not enumerate or copy its provider")

    def __getitem__(self, key):
        raise AssertionError("Detection must use the supplied lookup semantics")


class AgentDetectionConformanceTests(unittest.TestCase):
    def test_all_pinned_portable_cases_without_host_capabilities(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["spec_version"], detector.SPEC_VERSION)
        self.assertEqual(detector.SPEC_COMMIT, "601c270555a4f249959b2bf6c6a591a9e115448f")
        self.assertEqual(len(fixture["cases"]), 200)
        original_locale = locale.setlocale(locale.LC_CTYPE)
        try:
            for target_locale in ("C", "tr_TR.UTF-8", "Turkish_Turkey.1254"):
                try:
                    locale.setlocale(locale.LC_CTYPE, target_locale)
                except locale.Error:
                    continue
                with mock.patch.object(detector.os.path, "exists", side_effect=AssertionError("Native filesystem probe forbidden")):
                    for case in fixture["cases"]:
                        with self.subTest(locale=target_locale, case=case["name"]):
                            provider = LookupProvider(case["env"], insensitive=case.get("env_name_case") == "ascii-insensitive")
                            options = {"path_separator": case.get("path_separator", ":")}
                            if "files" in case:
                                options["filesystem_probe"] = lambda path, files=case["files"]: path in files
                            if "stdout_is_tty" in case:
                                options["stdout_is_tty"] = case["stdout_is_tty"]
                            self.assertEqual(detector.detect_agent(provider, **options), case["expected"])
        finally:
            locale.setlocale(locale.LC_CTYPE, original_locale)

    def test_catalog_declarations_and_aliases(self):
        self.assertEqual(len(detector.AGENT_DISPLAY_NAMES), 36)
        self.assertNotIn("unknown", detector.AGENT_DISPLAY_NAMES)
        for agent_id in detector.AGENT_DISPLAY_NAMES:
            with self.subTest(agent_id=agent_id):
                self.assertEqual(detector.detect_agent({"AI_AGENT": agent_id}), {
                    "agent_id": agent_id, "evidence": "declared",
                })
        for alias, agent_id in {
            "codex_cli": "codex", "claude_code": "claude-code",
            "gemini_cli": "gemini-cli", "open_code": "opencode", "grok": "grok-build",
        }.items():
            self.assertEqual(detector.detect_agent({"AGENT": alias}), {
                "agent_id": agent_id, "evidence": "declared",
            })

    def test_lookup_only_provider_semantics_are_preserved(self):
        sensitive = LookupProvider({"codex_thread_id": "synthetic"})
        insensitive = LookupProvider({"codex_thread_id": "synthetic"}, insensitive=True)
        self.assertEqual(detector.detect_agent(sensitive), {"agent_id": None, "evidence": "none"})
        self.assertEqual(detector.detect_agent(insensitive), {"agent_id": "codex", "evidence": "runtime-marker"})
        self.assertIn("CODEX_THREAD_ID", sensitive.lookups)
        self.assertNotIn("codex_thread_id", sensitive.lookups)

    def test_repeated_calls_evaluate_current_provider(self):
        values = {"CODEX_THREAD_ID": "synthetic"}
        self.assertEqual(detector.detect_agent(values)["agent_id"], "codex")
        values.clear()
        values["SAND_AGENT"] = "0"
        self.assertEqual(detector.detect_agent(values)["agent_id"], "grok-bot")
        values.clear()
        self.assertEqual(detector.detect_agent(values), {"agent_id": None, "evidence": "none"})

    def test_optional_probes_are_not_implicit_and_access_failures_are_skipped(self):
        self.assertEqual(detector.detect_agent({"TERM_PROGRAM": "kiro"})["evidence"], "none")
        self.assertEqual(detector.detect_agent({"TERM_PROGRAM": "kiro"}, stdout_is_tty=False), {
            "agent_id": "kiro", "evidence": "context-hint",
        })
        unavailable = mock.Mock(side_effect=PermissionError("synthetic unavailable probe"))
        self.assertEqual(detector.detect_agent({"ZED_TERM": "1"}, filesystem_probe=unavailable), {
            "agent_id": "zed", "evidence": "context-hint",
        })
        unavailable.assert_called_once_with("/opt/.devin")


if __name__ == "__main__":
    unittest.main()
