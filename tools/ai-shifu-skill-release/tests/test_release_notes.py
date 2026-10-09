"""Source-pinned, complete release-note collection without external services."""

from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai_shifu_release import release_notes


class ReleaseNotesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="release-notes-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        self.git("init", "--quiet", "--initial-branch=main")
        self.git("config", "user.name", "Fixture Author")
        self.git("config", "user.email", "fixture@example.invalid")
        self.counter = 0
        self.base = self.commit("chore: start repository")
        self.git("tag", "v1.0.0")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, title: str, path: str = "skills/demo/SKILL.md") -> str:
        self.counter += 1
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"change {self.counter}\n", encoding="utf-8")
        self.git("add", "--all")
        self.git("commit", "--quiet", "-m", title)
        return self.git("rev-parse", "HEAD")

    def pr(self, number: int, sha: str, title: str, **overrides) -> dict:
        result = {
            "number": number,
            "title": title,
            "html_url": f"https://github.com/example/skills/pull/{number}",
            "user": {"login": "author"},
            "merged": True,
            "merged_at": "2026-10-09T04:00:00Z",
            "merge_commit_sha": sha,
            "base": {"ref": "main", "repo": {"full_name": "example/skills"}},
            "changed_files": 1,
        }
        result.update(overrides)
        return result

    def api(
        self,
        associations: dict[str, list[int]],
        prs: dict[int, dict],
        *,
        releases=None,
        files=None,
    ):
        def fetch(endpoint: str, *, paginate: bool = False):
            if endpoint == "repos/example/skills":
                return {"full_name": "example/skills", "default_branch": "main"}
            if endpoint == "repos/example/skills/releases?per_page=100":
                self.assertTrue(paginate)
                return releases or []
            if "/commits/" in endpoint:
                self.assertTrue(paginate)
                sha = endpoint.split("/commits/", 1)[1].split("/", 1)[0]
                return [{"number": number} for number in associations.get(sha, [])]
            if endpoint.endswith("/files?per_page=100"):
                self.assertTrue(paginate)
                number = int(endpoint.split("/pulls/", 1)[1].split("/", 1)[0])
                return (files or {}).get(number, [{"filename": "skills/demo/SKILL.md"}])
            number = int(endpoint.rsplit("/", 1)[1])
            return prs[number]

        return fetch

    def collect_github(self, head: str, **kwargs) -> dict:
        return release_notes.collect_changes(
            str(self.repo),
            head,
            base_ref="v1.0.0",
            github_repository="example/skills",
            **kwargs,
        )

    def test_types_include_alias_scope_breaking_and_unknown(self) -> None:
        for title, change_type, body in (
            ("FEAT: Create courses", "feat", "Create courses"),
            ("feature(author): New workflow", "feat", "New workflow"),
            ("fix!: Change login", "fix", "! Change login"),
            ("perf(cli)!: Speed up import", "perf", "! Speed up import"),
            (
                "style: Small visual adjustment",
                "other",
                "style: Small visual adjustment",
            ),
            ("A change without prefix", "other", "A change without prefix"),
            (
                "feat(scope)(extra): Invalid prefix",
                "other",
                "feat(scope)(extra): Invalid prefix",
            ),
        ):
            with self.subTest(title=title):
                self.assertEqual(release_notes.parse_change_type(title), change_type)
                self.assertEqual(release_notes.title_body(title), body)

    def test_all_types_and_ties_have_stable_order(self) -> None:
        changes = [
            {
                "number": number,
                "title": f"{kind}: change",
                "commit": f"{number:040x}",
                "merged_at": "2026-10-09T04:00:00Z",
            }
            for number, kind in enumerate(reversed(release_notes.TYPE_ORDER), start=1)
        ]
        changes += [
            {
                "number": 100,
                "title": "feat: tie",
                "commit": "a" * 40,
                "merged_at": "2026-10-09T04:00:00Z",
            }
        ]
        ordered = release_notes.sort_changes(changes)
        self.assertEqual(ordered[0]["number"], 100)
        self.assertEqual(
            [release_notes.parse_change_type(item["title"]) for item in ordered[1:]],
            list(release_notes.TYPE_ORDER),
        )
        newer = dict(changes[-1], number=1, merged_at="2026-10-09T05:00:00+00:00")
        self.assertEqual(release_notes.sort_changes([changes[-1], newer])[0], newer)

    def test_offline_collection_keeps_more_than_thirty_prs_and_fixed_head(self) -> None:
        for number in range(1, 37):
            self.commit(
                f"{'fix' if number % 2 else 'feat'}: Change {number} (#{number})"
            )
        head = self.git("rev-parse", "HEAD")
        self.commit("feat: Later change (#999)")
        with patch.object(
            release_notes,
            "_github_json",
            side_effect=AssertionError("unexpected network"),
        ):
            snapshot = release_notes.collect_changes(
                str(self.repo), head, base_ref="v1.0.0"
            )
        self.assertEqual(snapshot["pr_count"], 36)
        self.assertEqual(
            {item["number"] for item in snapshot["changes"]}, set(range(1, 37))
        )
        self.assertFalse(snapshot["pr_metadata_verified"])
        self.assertEqual(snapshot["head_sha"], head)
        text = release_notes.render_changelog(snapshot)
        self.assertEqual(text.count(" by Fixture Author"), 36)
        self.assertLess(text.index("### Features"), text.index("### Bug Fixes"))

    def test_offline_normal_merge_omits_internal_commits(self) -> None:
        self.git("checkout", "--quiet", "-b", "development")
        self.commit("fix: Internal fix (#10)")
        self.commit("test: Internal test")
        self.git("checkout", "--quiet", "main")
        self.git(
            "merge",
            "--quiet",
            "--no-ff",
            "development",
            "-m",
            "Merge pull request #20 from development\n\nfeat: Create an authoring workflow",
        )
        head = self.git("rev-parse", "HEAD")
        snapshot = release_notes.collect_changes(
            str(self.repo), head, base_ref="v1.0.0"
        )
        self.assertEqual(len(snapshot["changes"]), 1)
        self.assertEqual(snapshot["changes"][0]["number"], 20)
        self.assertEqual(
            snapshot["changes"][0]["title"], "feat: Create an authoring workflow"
        )

    def test_github_merge_squash_and_rebase_are_verified_and_deduplicated(self) -> None:
        first = self.commit("feat: First rebased commit")
        last = self.commit("feat: Second rebased commit")
        squash = self.commit("fix: Squashed change (#200)")
        self.git("checkout", "--quiet", "-b", "development")
        internal = self.commit("test: Branch internals (#999)")
        self.git("checkout", "--quiet", "main")
        self.git(
            "merge",
            "--quiet",
            "--no-ff",
            "development",
            "-m",
            "Merge pull request #300 from development\n\nperf: Faster imports",
        )
        head = self.git("rev-parse", "HEAD")
        prs = {
            100: self.pr(100, last, "feat: Multi-commit rebase"),
            200: self.pr(200, squash, "fix: Successful course publishing", user=None),
            300: self.pr(300, head, "perf: Faster imports"),
            999: self.pr(
                999,
                internal,
                "test: Nested branch",
                base={"ref": "development", "repo": {"full_name": "example/skills"}},
            ),
        }
        associations = {first: [100], last: [100], squash: [200], head: [300, 999]}
        with patch.object(
            release_notes, "_github_json", side_effect=self.api(associations, prs)
        ):
            snapshot = self.collect_github(head)
        self.assertEqual(
            [item["number"] for item in snapshot["changes"]], [100, 200, 300]
        )
        text = release_notes.render_changelog(snapshot)
        for number in (100, 200, 300):
            self.assertEqual(text.count(f"[#{number}]"), 1)
            self.assertIn(f"https://github.com/example/skills/pull/{number}", text)
        self.assertIn(" by @author", text)
        self.assertNotIn("#999", text)

    def test_missing_association_checks_explicit_pr_hint_instead_of_hiding_it(
        self,
    ) -> None:
        head = self.commit("feat: Course creation (#12)")
        prs = {12: self.pr(12, head, "feat: Course creation")}
        with patch.object(release_notes, "_github_json", side_effect=self.api({}, prs)):
            snapshot = self.collect_github(head)
        self.assertEqual(snapshot["pr_count"], 1)
        self.assertEqual(snapshot["changes"][0]["number"], 12)
        for overrides, expected in (
            ({"merged": False}, "not merged into"),
            ({"merge_commit_sha": self.base}, "outside the release range"),
            (
                {
                    "base": {
                        "ref": "development",
                        "repo": {"full_name": "example/skills"},
                    }
                },
                "not merged into",
            ),
        ):
            with self.subTest(overrides=overrides):
                prs = {12: self.pr(12, head, "feat: Course creation", **overrides)}
                with (
                    patch.object(
                        release_notes, "_github_json", side_effect=self.api({}, prs)
                    ),
                    self.assertRaisesRegex(ValueError, expected),
                ):
                    self.collect_github(head)

    def test_github_default_branch_overrides_local_checked_out_feature_branch(
        self,
    ) -> None:
        head = self.commit("feat: Merged course authoring (#12)")
        self.git("checkout", "--quiet", "-b", "feature-work")
        self.commit("fix: Pending local work (#13)")
        prs = {12: self.pr(12, head, "feat: Merged course authoring")}
        with patch.object(
            release_notes, "_github_json", side_effect=self.api({head: [12]}, prs)
        ):
            snapshot = self.collect_github(head)
        self.assertEqual(snapshot["target_branch"], "main")
        self.assertEqual([item["number"] for item in snapshot["changes"]], [12])

    def test_detached_checkout_keeps_its_source_remote_tracking_branch(self) -> None:
        head = self.commit("feat: Prepared course authoring (#12)")
        self.git("update-ref", "refs/remotes/origin/main", head)
        self.git("checkout", "--quiet", "--detach", head)
        self.git("update-ref", "-d", "refs/heads/main")
        snapshot = release_notes.collect_changes(
            str(self.repo), head, base_ref="v1.0.0", preview=True
        )
        self.assertEqual(snapshot["target_branch"], "main")
        self.assertEqual(snapshot["pr_count"], 1)
        prs = {12: self.pr(12, head, "feat: Prepared course authoring")}
        with patch.object(
            release_notes, "_github_json", side_effect=self.api({head: [12]}, prs)
        ):
            snapshot = self.collect_github(head, preview=True)
        self.assertEqual(snapshot["target_branch"], "main")
        self.assertEqual(snapshot["pr_count"], 1)

    def test_direct_and_unmerged_changes_are_separate(self) -> None:
        direct = self.commit("ci: Update validation")
        self.git("checkout", "--quiet", "-b", "preview-work")
        head = self.commit("feat: Work awaiting merge (#123)")
        self.git("checkout", "--quiet", "main")
        with patch.object(release_notes, "_github_json", side_effect=self.api({}, {})):
            snapshot = self.collect_github(head, preview=True)
        self.assertEqual(
            {item["kind"] for item in snapshot["changes"]}, {"commit", "preview"}
        )
        text = release_notes.render_changelog(snapshot)
        self.assertIn("### Additional commits", text)
        self.assertIn("### Unmerged preview changes", text)
        self.assertIn(f"https://github.com/example/skills/commit/{direct}", text)
        self.assertEqual(snapshot["pr_count"], 0)
        with (
            patch.object(release_notes, "_github_json", side_effect=self.api({}, {})),
            self.assertRaisesRegex(ValueError, "use preview"),
        ):
            self.collect_github(head)

    def test_path_filter_reads_every_file_and_includes_previous_rename_path(
        self,
    ) -> None:
        head = self.commit("fix: Rename the course file (#7)")
        files = [{"filename": f"other/file-{index}.md"} for index in range(101)]
        files += [
            {
                "filename": "other/renamed.md",
                "previous_filename": "skills/demo/SKILL.md",
            }
        ]
        prs = {
            7: self.pr(
                7, head, "fix: Keep course files available", changed_files=len(files)
            )
        }
        with patch.object(
            release_notes,
            "_github_json",
            side_effect=self.api({head: [7]}, prs, files={7: files}),
        ):
            snapshot = self.collect_github(head, paths=("skills/demo/",))
        self.assertEqual(snapshot["pr_count"], 1)
        with patch.object(
            release_notes,
            "_github_json",
            side_effect=self.api({head: [7]}, prs, files={7: files[:-1]}),
        ), self.assertRaisesRegex(ValueError, "Incomplete file list"):
            self.collect_github(head, paths=("skills/demo/",))

    def test_pagination_uses_every_page_and_rejects_invalid_responses(self) -> None:
        response = SimpleNamespace(
            returncode=0,
            stdout=json.dumps([[{"number": 1}], [{"number": 2}]]),
            stderr="",
        )
        with patch.object(
            release_notes.subprocess, "run", return_value=response
        ) as run:
            result = release_notes._github_json(
                "repos/example/skills/releases?per_page=100", paginate=True
            )
        self.assertEqual(result, [{"number": 1}, {"number": 2}])
        self.assertIn("--paginate", run.call_args.args[0])
        self.assertIn("--slurp", run.call_args.args[0])
        response.stdout = "{}"
        with (
            patch.object(release_notes.subprocess, "run", return_value=response),
            self.assertRaisesRegex(ValueError, "Incomplete paginated"),
        ):
            release_notes._github_json("endpoint", paginate=True)
        response.returncode = 1
        response.stderr = "page 2 could not be fetched"
        with (
            patch.object(release_notes.subprocess, "run", return_value=response),
            self.assertRaisesRegex(ValueError, "page 2"),
        ):
            release_notes._github_json("endpoint", paginate=True)

    def test_transient_github_errors_retry_but_permanent_failures_do_not(self) -> None:
        success = SimpleNamespace(returncode=0, stdout='{"ok":true}', stderr="")
        transient = SimpleNamespace(
            returncode=1, stdout="", stderr="read: connection reset by peer"
        )
        with (
            patch.object(
                release_notes.subprocess,
                "run",
                side_effect=[transient, transient, success],
            ) as run,
            patch.object(release_notes.time, "sleep") as sleep,
        ):
            self.assertEqual(release_notes._github_json("endpoint"), {"ok": True})
        self.assertEqual(run.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.25, 0.5])
        for message in ("gh: Not Found (HTTP 404)", "gh: Forbidden (HTTP 403)"):
            failure = SimpleNamespace(returncode=1, stdout="", stderr=message)
            with (
                self.subTest(message=message),
                patch.object(
                    release_notes.subprocess, "run", return_value=failure
                ) as run,
                patch.object(release_notes.time, "sleep") as sleep,
                self.assertRaisesRegex(ValueError, "metadata lookup failed"),
            ):
                release_notes._github_json("endpoint")
            self.assertEqual(run.call_count, 1)
            sleep.assert_not_called()
        malformed = SimpleNamespace(returncode=0, stdout="not json", stderr="")
        with (
            patch.object(
                release_notes.subprocess, "run", return_value=malformed
            ) as run,
            patch.object(release_notes.time, "sleep") as sleep,
            self.assertRaisesRegex(ValueError, "Invalid GitHub metadata"),
        ):
            release_notes._github_json("endpoint")
        self.assertEqual(run.call_count, 1)
        sleep.assert_not_called()
        with (
            patch.object(
                release_notes.subprocess, "run", return_value=transient
            ) as run,
            patch.object(release_notes.time, "sleep"),
            self.assertRaisesRegex(ValueError, "connection reset"),
        ):
            release_notes._github_json("endpoint")
        self.assertEqual(run.call_count, 3)

    def test_default_base_uses_nearest_published_lower_ancestor(self) -> None:
        self.git("tag", "v1.8.0")
        later = self.commit("chore: Previous version")
        self.git("tag", "-a", "v1.2.0", "-m", "annotated previous release")
        head = self.commit("feat: New release")
        for tag in ("v1.8.1", "v1.8.2", "v1.9.0", "v2.0.0"):
            self.git("tag", tag)
        self.git("checkout", "--quiet", "-b", "unrelated", self.base)
        self.commit("fix: Unreleased branch")
        self.git("tag", "v1.7.0")
        self.git("checkout", "--quiet", "main")
        releases = [
            {"tag_name": tag, "draft": tag == "v1.8.1", "prerelease": tag == "v1.8.2"}
            for tag in (
                "v1.0.0",
                "v1.8.0",
                "v1.2.0",
                "v1.7.0",
                "v1.8.1",
                "v1.8.2",
                "v1.9.0",
                "v2.0.0",
                "preview-v1.9.0-test",
            )
        ]
        with patch.object(
            release_notes,
            "_github_json",
            side_effect=self.api({}, {}, releases=releases),
        ):
            snapshot = release_notes.generate_notes(
                str(self.repo), head, "1.9.0", github_repository="example/skills"
            )
        self.assertEqual(snapshot["base_ref"], "v1.2.0")
        self.assertEqual(snapshot["base_sha"], later)
        self.assertEqual(len(snapshot["changes"]), 1)
        self.assertFalse(snapshot["initial_release"])

    def test_first_release_is_explicit_and_full_history_is_preserved(self) -> None:
        head = self.commit("feat: First public capability")
        with patch.object(release_notes, "_github_json", side_effect=self.api({}, {})):
            snapshot = release_notes.generate_notes(
                str(self.repo), head, "1.1.0", github_repository="example/skills"
            )
        self.assertTrue(snapshot["initial_release"])
        self.assertEqual(len(snapshot["changes"]), 2)
        self.assertIn("Initial release", release_notes.render_notes(snapshot))

    def test_incomplete_authoritative_pr_data_never_silently_succeeds(self) -> None:
        head = self.commit("feat: A course workflow (#3)")
        for overrides, expected in (
            ({"merged_at": None}, "timestamp"),
            ({"html_url": None}, "title or URL"),
            ({"merged": None}, "merge status"),
            (
                {"base": {"ref": "main", "repo": {"full_name": "wrong/repository"}}},
                "different repository",
            ),
        ):
            with self.subTest(overrides=overrides):
                prs = {3: self.pr(3, head, "feat: A course workflow", **overrides)}
                with patch.object(
                    release_notes,
                    "_github_json",
                    side_effect=self.api({head: [3]}, prs),
                ), self.assertRaisesRegex(ValueError, expected):
                    self.collect_github(head)
        with patch.object(
            release_notes, "_github_json", side_effect=ValueError("GitHub unavailable")
        ), self.assertRaisesRegex(ValueError, "GitHub unavailable"):
            self.collect_github(head)

    def test_concurrent_metadata_keeps_order_and_propagates_worker_failures(
        self,
    ) -> None:
        shas = [self.commit(f"feat: Capability {number}") for number in range(1, 9)]
        associations = {sha: [number] for number, sha in enumerate(shas, start=1)}
        prs = {
            number: self.pr(number, sha, f"feat: Capability {number}")
            for number, sha in enumerate(shas, start=1)
        }
        api = self.api(associations, prs)
        lock = threading.Lock()
        active = 0
        maximum = 0

        def delayed_api(endpoint, *, paginate=False):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            try:
                time.sleep(0.005 if endpoint.endswith("/1") else 0.01)
                return api(endpoint, paginate=paginate)
            finally:
                with lock:
                    active -= 1

        with patch.object(release_notes, "_github_json", side_effect=delayed_api):
            snapshot = self.collect_github(shas[-1])
            repeated = self.collect_github(shas[-1])
        self.assertEqual(snapshot, repeated)
        self.assertEqual(
            [item["number"] for item in snapshot["changes"]], list(range(8, 0, -1))
        )
        self.assertGreater(maximum, 1)
        self.assertLessEqual(maximum, 4)

        def failed_api(endpoint, *, paginate=False):
            if endpoint.endswith("/pulls/3"):
                raise ValueError("PR detail worker failed")
            return api(endpoint, paginate=paginate)

        with (
            patch.object(release_notes, "_github_json", side_effect=failed_api),
            self.assertRaisesRegex(ValueError, "PR detail worker failed"),
        ):
            self.collect_github(shas[-1])

    def test_invalid_or_unrelated_references_are_rejected(self) -> None:
        head = self.commit("fix: Mainline repair")
        self.git("checkout", "--quiet", "-b", "unrelated", self.base)
        unrelated = self.commit("fix: A different branch")
        self.git("checkout", "--quiet", "main")
        with self.assertRaisesRegex(ValueError, "not an ancestor"):
            release_notes.collect_changes(str(self.repo), head, base_ref=unrelated)
        with self.assertRaisesRegex(ValueError, "full source commit"):
            release_notes.collect_changes(str(self.repo), "main")
        with self.assertRaisesRegex(ValueError, "differs from the source"):
            release_notes.collect_changes(
                "https://github.com/example/skills.git",
                head,
                github_repository="another/skills",
            )

    def test_snapshot_and_markdown_are_stable_and_written_together(self) -> None:
        head = self.commit("feat!: Updated publishing workflow (#3)")
        snapshot = release_notes.generate_notes(str(self.repo), head, "1.1.0")
        repeated = release_notes.generate_notes(str(self.repo), head, "1.1.0")
        self.assertEqual(snapshot, repeated)
        paths = release_notes.write_notes(snapshot, self.root / "notes")
        self.assertEqual(json.loads(paths[0].read_text()), snapshot)
        self.assertEqual(paths[1].read_text(), release_notes.render_notes(snapshot))
        self.assertIn(
            "Publication to each channel is tracked separately", paths[1].read_text()
        )
        self.assertIn("! Updated publishing workflow", paths[1].read_text())
        self.assertEqual(snapshot["fingerprint"], snapshot["facts_sha256"])

    def test_preview_labels_counts_and_final_snapshot_fingerprint(self) -> None:
        head = self.commit("feat: Preview improvement (#1)")
        snapshot = release_notes.generate_notes(
            str(self.repo), head, "1.1.0", preview=True
        )
        previous_hash = snapshot["facts_sha256"]
        self.assertIn("PREVIEW ONLY", release_notes.render_notes(snapshot))
        self.assertIn(
            "Collection status: complete. Pull requests: 1.",
            release_notes.render_notes(snapshot),
        )
        snapshot["draft_preview"] = True
        _, markdown = release_notes.write_notes(snapshot, self.root / "draft-notes")
        self.assertIn("TEST DRAFT ONLY", markdown.read_text())
        self.assertNotEqual(snapshot["facts_sha256"], previous_hash)

    def test_renderer_rejects_invalid_change_identity_and_kind(self) -> None:
        head = self.commit("fix: Complete learner flow (#1)")
        snapshot = release_notes.collect_changes(
            str(self.repo), head, base_ref="v1.0.0"
        )
        for invalid in (None, True, 0, "1"):
            with self.subTest(number=invalid):
                snapshot["changes"][0]["number"] = invalid
                with self.assertRaisesRegex(ValueError, "invalid PR identity"):
                    release_notes.render_changelog(snapshot)
        snapshot["changes"][0]["number"] = 1
        snapshot["changes"][0]["kind"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown change kind"):
            release_notes.render_changelog(snapshot)

    def test_renderer_rejects_duplicate_prs_and_preserves_unknown_types(self) -> None:
        head = self.commit("style: Clearer prompts (#4)")
        snapshot = release_notes.collect_changes(
            str(self.repo), head, base_ref="v1.0.0"
        )
        text = release_notes.render_changelog(snapshot)
        self.assertIn("### Other Changes", text)
        self.assertIn("style: Clearer prompts", text)
        snapshot["changes"].append(dict(snapshot["changes"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate PR"):
            release_notes.render_changelog(snapshot)


if __name__ == "__main__":
    unittest.main()
