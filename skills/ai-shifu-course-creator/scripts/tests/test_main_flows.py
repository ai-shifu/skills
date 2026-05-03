#!/usr/bin/env python3
"""End-to-end smoke tests for the main flows in shifu-cli.py.

Covers (matching design/adr-001-test-scenarios.md):
  M1–M6  — main flows: import, pull, push (optimize), push (mixed-edit),
                       validate, extract/embed
  E1–E4  — boundary conditions
  R1–R2  — regression guards

Run:
  python3 test_main_flows.py                  # unit-only (no network)
  python3 test_main_flows.py --integration    # also run integration tests (needs SHIFU_TOKEN)
  python3 test_main_flows.py --integration -v # verbose
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

CLI = os.path.join(os.path.dirname(__file__), "..", "shifu-cli.py")
INTEGRATION_TEST_SHIFU_BID = "b51d69868de741fc902caf3934eb2468"  # 极简体验版课程

# When --integration is requested but no token, integration tests are skipped.
RUN_INTEGRATION = False


def run_cli(*cli_args, capture=True, check=False):
    """Invoke shifu-cli.py with the given args and return CompletedProcess."""
    cmd = ["python3", CLI, *cli_args]
    return subprocess.run(cmd, capture_output=capture, text=True, check=check)


def write_course_json(course_dir, course_data):
    """Helper: serialize course_data to <course_dir>/course.json."""
    os.makedirs(course_dir, exist_ok=True)
    path = os.path.join(course_dir, "course.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(course_data, f, ensure_ascii=False, indent=2)
    return path


def read_course_json(course_dir):
    """Helper: read <course_dir>/course.json."""
    with open(os.path.join(course_dir, "course.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def minimal_valid_course(with_placeholders=True):
    """A small valid course.json fixture (1 chapter + 2 lessons)."""
    if with_placeholders:
        cbid, l1, l2 = "new:c01", "new:l01", "new:l02"
    else:
        cbid, l1, l2 = "real-c-bid", "real-l1-bid", "real-l2-bid"
    return {
        "version": "1.0",
        "course": {
            "title": "Smoke Test Course",
            "description": "Auto-generated test fixture.",
            "course_prompt": "你是一位耐心的导师。",
            "language": "zh-CN",
        },
        "structure": [
            {"outline_item_bid": cbid, "children": [
                {"outline_item_bid": l1, "children": []},
                {"outline_item_bid": l2, "children": []},
            ]}
        ],
        "items": {
            cbid: {"type": "chapter", "title": "第一章", "markdownflow_prompt": "## 章节导言\n",
                   "used_variables": [], "depends_on_lessons": [], "source_span_map": []},
            l1: {"type": "lesson", "title": "课节 A", "markdownflow_prompt": "## 课节 A\n讲解 X。\n",
                 "used_variables": [], "depends_on_lessons": [], "source_span_map": []},
            l2: {"type": "lesson", "title": "课节 B", "markdownflow_prompt": "## 课节 B\n讲解 Y。\n",
                 "used_variables": [], "depends_on_lessons": [], "source_span_map": []},
        },
        "global_variables": [],
        "deployment": {},
    }


# ─── Unit tests (no network) ──────────────────────────────────────────────────
class UnitFlows(unittest.TestCase):
    """M5, M6, E1, E2, E4, R2 — local-only flows."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="shifu-cli-unit-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # M5 — validate, both modes
    def test_M5_validate_minimal_course_passes_import_mode(self):
        """A course with placeholder bids passes 'import' mode validation."""
        d = os.path.join(self.tmp, "c1")
        write_course_json(d, minimal_valid_course(with_placeholders=True))
        r = run_cli("validate", "--course-dir", d, "--mode", "import")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("Validation OK", r.stdout)

    def test_M5_validate_real_bids_pass_push_mode(self):
        """A course with all real bids passes 'push' mode validation."""
        d = os.path.join(self.tmp, "c2")
        write_course_json(d, minimal_valid_course(with_placeholders=False))
        r = run_cli("validate", "--course-dir", d, "--mode", "push")
        self.assertEqual(r.returncode, 0, msg=r.stderr)

    # E1 — duplicate bid in structure tree
    def test_E1_duplicate_bid_in_structure_rejected(self):
        d = os.path.join(self.tmp, "dup")
        course = minimal_valid_course()
        # Make new:l01 appear twice in the same children list
        course["structure"][0]["children"].append(
            {"outline_item_bid": "new:l01", "children": []}
        )
        write_course_json(d, course)
        r = run_cli("validate", "--course-dir", d, "--mode", "import")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("duplicate", r.stderr)

    # E2 — orphan reference (in structure but not in items)
    def test_E2_structure_references_unknown_bid_rejected(self):
        d = os.path.join(self.tmp, "orphan")
        course = minimal_valid_course()
        course["structure"][0]["children"].append(
            {"outline_item_bid": "new:l99", "children": []}
        )
        # 'new:l99' is in structure but missing from items
        write_course_json(d, course)
        r = run_cli("validate", "--course-dir", d, "--mode", "import")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("missing from items", r.stderr)

    # M5 (negative path) — placeholders rejected in push mode
    def test_M5_placeholders_rejected_in_push_mode(self):
        d = os.path.join(self.tmp, "ph")
        write_course_json(d, minimal_valid_course(with_placeholders=True))
        r = run_cli("validate", "--course-dir", d, "--mode", "push")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("placeholder bid", r.stderr)

    # M6 + R2 — extract / embed round-trip preserves bytes; field name is lowercase
    def test_M6_extract_then_embed_preserves_bytes(self):
        d = os.path.join(self.tmp, "rt")
        course = minimal_valid_course()
        write_course_json(d, course)
        target_bid = "new:l01"
        original = course["items"][target_bid]["markdownflow_prompt"]

        md_path = os.path.join(self.tmp, "lesson.md")
        r = run_cli("extract", "--course-dir", d, "--outline-bid", target_bid, "-o", md_path)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        with open(md_path, "r", encoding="utf-8") as f:
            extracted = f.read()
        self.assertEqual(extracted, original, "extracted .md must match the field exactly")

        # modify and embed back
        modified = extracted + "\n## 新增小节\n"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(modified)
        r = run_cli("embed", "--course-dir", d, "--outline-bid", target_bid, "--from", md_path)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        course_after = read_course_json(d)
        self.assertEqual(course_after["items"][target_bid]["markdownflow_prompt"], modified)
        # other items untouched
        self.assertEqual(course_after["items"]["new:l02"]["markdownflow_prompt"],
                         course["items"]["new:l02"]["markdownflow_prompt"])

    def test_M6_extract_course_prompt_field_name_is_lowercase(self):
        """R2 regression guard: course.course_prompt is lowercase."""
        d = os.path.join(self.tmp, "cp")
        write_course_json(d, minimal_valid_course())
        md_path = os.path.join(self.tmp, "course-prompt.md")
        r = run_cli("extract", "--course-dir", d, "--course-prompt", "-o", md_path)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        with open(md_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "你是一位耐心的导师。")

    # R3 — variable extraction from MarkdownFlow content
    def test_R3_extract_used_variables_from_markdownflow(self):
        """The CLI auto-derives used_variables from the {{var}} / ?[%{{var}}] patterns."""
        shifu_cli = self._load_shifu_cli()
        cases = [
            ("", []),
            ("plain text", []),
            ("Use {{name}} here.", ["name"]),
            ("Use {{name}} twice: {{name}}.", ["name"]),                       # dedup
            ("?[%{{topic}} A | B | C]", ["topic"]),                           # collection syntax
            ("Hello {{name}}, choose ?[%{{topic}} A | B]", ["name", "topic"]),
            ("Chinese: {{用户名}} 也支持。", ["用户名"]),                      # Unicode word chars
            ("{{ spaced }} works too", ["spaced"]),                           # whitespace inside braces
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(shifu_cli._extract_used_variables(text), expected)

    def test_R3_compute_depends_on_lessons(self):
        """An item that uses a variable collected by another item gets a dependency."""
        shifu_cli = self._load_shifu_cli()
        items = {
            "bidA": {"markdownflow_prompt": "Pick: ?[%{{x}} A | B]", "used_variables": ["x"]},
            "bidB": {"markdownflow_prompt": "Reflect on {{x}}.", "used_variables": ["x"]},
            "bidC": {"markdownflow_prompt": "Plain text.", "used_variables": []},
            "bidD": {"markdownflow_prompt": "?[%{{y}} 1 | 2]", "used_variables": ["y"]},
        }
        shifu_cli._compute_depends_on_lessons(items)
        self.assertEqual(items["bidA"]["depends_on_lessons"], [],
                         "producer should not depend on itself")
        self.assertEqual(items["bidB"]["depends_on_lessons"], ["bidA"],
                         "consumer should depend on producer")
        self.assertEqual(items["bidC"]["depends_on_lessons"], [])
        self.assertEqual(items["bidD"]["depends_on_lessons"], [],
                         "an item that produces but does not consume y has no dep")

    @staticmethod
    def _load_shifu_cli():
        """Import shifu-cli.py despite its dashed filename (not a valid Python module name)."""
        import importlib.util
        cli_path = os.path.join(os.path.dirname(__file__), "..", "shifu-cli.py")
        spec = importlib.util.spec_from_file_location("shifu_cli", cli_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # E4 — extract refuses to overwrite without --force
    def test_E4_extract_refuses_overwrite(self):
        d = os.path.join(self.tmp, "ow")
        write_course_json(d, minimal_valid_course())
        md_path = os.path.join(self.tmp, "x.md")
        # First write
        r = run_cli("extract", "--course-dir", d, "--course-prompt", "-o", md_path)
        self.assertEqual(r.returncode, 0)
        # Second time without --force
        r = run_cli("extract", "--course-dir", d, "--course-prompt", "-o", md_path)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--force", r.stderr)
        # With --force, succeeds
        r = run_cli("extract", "--course-dir", d, "--course-prompt", "-o", md_path, "--force")
        self.assertEqual(r.returncode, 0)


# ─── Integration tests (network required, opt-in via --integration) ───────────
class IntegrationFlows(unittest.TestCase):
    """M1–M4, E3, R1 — flows that require a live SHIFU_TOKEN and network."""

    @classmethod
    def setUpClass(cls):
        if not RUN_INTEGRATION:
            raise unittest.SkipTest("integration tests not enabled (use --integration)")

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="shifu-cli-int-")
        self.created_shifu_bids = []

    def tearDown(self):
        # Archive any test courses we created so they don't pollute the active list
        for bid in self.created_shifu_bids:
            run_cli("archive", bid, capture=True)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # M2 + R2 — pull and verify schema + lowercase field names
    def test_M2_pull_known_course(self):
        d = os.path.join(self.tmp, "pulled")
        r = run_cli("pull", INTEGRATION_TEST_SHIFU_BID, "--to", d)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        c = read_course_json(d)

        # Schema sanity
        self.assertIn("course", c)
        self.assertIn("structure", c)
        self.assertIn("items", c)
        self.assertEqual(c["deployment"]["shifu_bid"], INTEGRATION_TEST_SHIFU_BID)

        # R2 — lowercase field names
        self.assertIn("course_prompt", c["course"])
        self.assertNotIn("Course_prompt", c["course"])
        for item in c["items"].values():
            self.assertIn("markdownflow_prompt", item)
            self.assertNotIn("MarkdownFlow_prompt", item)
            self.assertIn(item["type"], {"chapter", "lesson"})

        # Each item should have a captured revision
        revs = c["deployment"]["draft_pulled_at_revision"]
        self.assertEqual(set(revs.keys()), set(c["items"].keys()))

    # E4 — pull refuses to overwrite without --force-overwrite
    def test_E4_pull_overwrite_protection(self):
        d = os.path.join(self.tmp, "p2")
        # First pull creates the file
        r = run_cli("pull", INTEGRATION_TEST_SHIFU_BID, "--to", d)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # Second pull without force → should fail
        r = run_cli("pull", INTEGRATION_TEST_SHIFU_BID, "--to", d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--force-overwrite", r.stderr)
        # With --force-overwrite, succeeds
        r = run_cli("pull", INTEGRATION_TEST_SHIFU_BID, "--to", d, "--force-overwrite")
        self.assertEqual(r.returncode, 0, msg=r.stderr)

    # R1 — push no-op
    def test_R1_push_no_op_after_pull(self):
        d = os.path.join(self.tmp, "noop")
        run_cli("pull", INTEGRATION_TEST_SHIFU_BID, "--to", d, check=True)
        r = run_cli("push", "--course-dir", d)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("No changes", r.stdout)

    # M1 + R2 — full import flow on a fresh course
    def test_M1_import_new_course_end_to_end(self):
        d = os.path.join(self.tmp, "fresh")
        write_course_json(d, minimal_valid_course(with_placeholders=True))

        r = run_cli("import", "--new", "--course-dir", d)
        self.assertEqual(r.returncode, 0, msg=r.stderr)

        c = read_course_json(d)
        new_bid = c["deployment"]["shifu_bid"]
        self.assertTrue(new_bid)
        self.created_shifu_bids.append(new_bid)

        # All placeholders replaced
        for bid in c["items"].keys():
            self.assertFalse(bid.startswith("new:"), f"placeholder leaked: {bid}")

        # Type distribution preserved (1 chapter + 2 lessons)
        types = [it["type"] for it in c["items"].values()]
        self.assertEqual(types.count("chapter"), 1)
        self.assertEqual(types.count("lesson"), 2)

        # Validate-push must pass after import
        r = run_cli("validate", "--course-dir", d, "--mode", "push")
        self.assertEqual(r.returncode, 0)

    # M3 — modify markdownflow_prompt and push; server revision should advance
    def test_M3_push_content_change(self):
        d = os.path.join(self.tmp, "fresh-m3")
        write_course_json(d, minimal_valid_course(with_placeholders=True))
        r = run_cli("import", "--new", "--course-dir", d, check=True)
        self.assertEqual(r.returncode, 0)
        c = read_course_json(d)
        self.created_shifu_bids.append(c["deployment"]["shifu_bid"])

        # pick a lesson, capture its current revision, modify content
        lesson_bid = next(b for b, it in c["items"].items() if it["type"] == "lesson")
        before_rev = c["deployment"]["draft_pulled_at_revision"][lesson_bid]
        c["items"][lesson_bid]["markdownflow_prompt"] += "\n## extra\n"
        write_course_json(d, c)

        r = run_cli("push", "--course-dir", d)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("update mdflow", r.stdout)

        c_after = read_course_json(d)
        after_rev = c_after["deployment"]["draft_pulled_at_revision"][lesson_bid]
        self.assertGreater(after_rev, before_rev,
                           "server revision should advance after content push")

    # M4 — mixed-edit: add a new lesson via placeholder, push, expect real bid
    def test_M4_push_mixed_edit_adds_lesson(self):
        d = os.path.join(self.tmp, "fresh-m4")
        write_course_json(d, minimal_valid_course(with_placeholders=True))
        r = run_cli("import", "--new", "--course-dir", d, check=True)
        self.assertEqual(r.returncode, 0)
        c = read_course_json(d)
        self.created_shifu_bids.append(c["deployment"]["shifu_bid"])

        chapter_bid = next(b for b, it in c["items"].items() if it["type"] == "chapter")
        # add a new lesson in items + structure with placeholder bid
        c["items"]["new:l_extra"] = {
            "type": "lesson",
            "title": "课节 C (extra)",
            "markdownflow_prompt": "## extra\n",
            "used_variables": [], "depends_on_lessons": [], "source_span_map": [],
        }
        for top in c["structure"]:
            if top["outline_item_bid"] == chapter_bid:
                top["children"].append({"outline_item_bid": "new:l_extra", "children": []})
        write_course_json(d, c)

        r = run_cli("push", "--course-dir", d)
        self.assertEqual(r.returncode, 0, msg=r.stderr)

        c_after = read_course_json(d)
        # placeholder no longer present
        self.assertNotIn("new:l_extra", c_after["items"])
        # but a new lesson with the same title exists
        new_lessons = [b for b, it in c_after["items"].items()
                       if it["type"] == "lesson" and it["title"] == "课节 C (extra)"]
        self.assertEqual(len(new_lessons), 1)


# ─── Entry point ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--integration", action="store_true",
                        help="Run integration tests too (requires SHIFU_TOKEN in .env)")
    parser.add_argument("-v", "--verbose", action="count", default=1)
    args = parser.parse_args()

    global RUN_INTEGRATION
    RUN_INTEGRATION = args.integration

    # Build the loader programmatically so we control which classes run.
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(UnitFlows))
    if RUN_INTEGRATION:
        suite.addTests(loader.loadTestsFromTestCase(IntegrationFlows))

    runner = unittest.TextTestRunner(verbosity=args.verbose)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
