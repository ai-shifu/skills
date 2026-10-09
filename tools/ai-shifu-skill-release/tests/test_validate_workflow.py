"""Exercise PR preview packaging with Actions' detached synthetic merge."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from ai_shifu_release import github_releases, release_notes
from support import ReleaseFixture


class PullRequestPreviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = ReleaseFixture()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        # Discard the fixture's deliberate uncommitted changes before making
        # the divergent main / PR histories used by an Actions test merge.
        self.fixture.git("checkout", "--", ".")
        self.fixture.git("tag", "v1.2.2")
        self.fixture.git("checkout", "-b", "proposed-release")
        self.branch_commits = []
        for title, filename in (
            ("feat: Preview the proposed authoring flow", "authoring.md"),
            ("fix: Keep the learner continuation", "continuation.md"),
        ):
            (self.fixture.skill / "references" / filename).write_text(title + "\n")
            self.fixture.git("add", ".")
            self.fixture.git("commit", "--quiet", "-m", title)
            self.branch_commits.append(self.fixture.git("rev-parse", "HEAD"))
        self.fixture.git("checkout", "main")
        (self.fixture.source_repo / "main-only.md").write_text("main changes\n")
        self.fixture.git("add", "main-only.md")
        self.fixture.git("commit", "--quiet", "-m", "docs: Update main guidance")
        self.main_commit = self.fixture.git("rev-parse", "HEAD")
        self.fixture.git("checkout", "--detach", "main")
        self.fixture.git(
            "merge",
            "--no-ff",
            "proposed-release",
            "-m",
            f"Merge {self.branch_commits[-1]} into {self.main_commit}",
        )
        self.merge_commit = self.fixture.git("rev-parse", "HEAD")
        # actions/checkout leaves the test merge detached and main available
        # only as a remote-tracking ref. No named PR head is needed to collect
        # the commits reachable through the merge's second parent.
        self.fixture.git("update-ref", "refs/remotes/origin/main", self.main_commit)
        self.fixture.git("branch", "-D", "main", "proposed-release")

    def test_trial_packages_and_notes_keep_merge_pin_and_branch_changes(self) -> None:
        release_dir = self.fixture.build(source_ref=self.merge_commit)
        requested_commits = []

        def github_json(endpoint: str, *, paginate: bool = False):
            if endpoint == "repos/example/skills":
                return {"default_branch": "main"}
            if endpoint == "repos/example/skills/releases?per_page=100":
                self.assertTrue(paginate)
                return [{"tag_name": "v1.2.2", "draft": False, "prerelease": False}]
            if "/commits/" in endpoint:
                self.assertTrue(paginate)
                requested_commits.append(
                    endpoint.split("/commits/", 1)[1].split("/", 1)[0]
                )
                return []
            self.fail(f"Unexpected GitHub request: {endpoint}")

        output = self.fixture.root / "preview-assets"
        with patch.object(release_notes, "_github_json", side_effect=github_json):
            assets, markdown = github_releases.prepare_assets(
                release_dir,
                "v1.2.3",
                self.merge_commit,
                output,
                github_repository="example/skills",
                preview=True,
            )

        self.assertEqual(len(assets), 6)
        packaged_report = json.loads((output / "release.json").read_text())
        snapshot = json.loads((output / "notes/release-notes.json").read_text())
        self.assertEqual(packaged_report["source"]["commit"], self.merge_commit)
        self.assertEqual(snapshot["head_sha"], self.merge_commit)
        self.assertEqual(snapshot["collection_status"], "complete")
        self.assertTrue(snapshot["pr_metadata_verified"])
        changes = {change["commit"]: change for change in snapshot["changes"]}
        self.assertEqual(len(changes), len(snapshot["changes"]))
        self.assertEqual(
            set(changes),
            {self.main_commit, self.merge_commit, *self.branch_commits},
        )
        self.assertEqual(changes[self.main_commit]["kind"], "commit")
        for sha in (self.merge_commit, *self.branch_commits):
            self.assertEqual(changes[sha]["kind"], "preview")
        self.assertEqual(requested_commits, [self.main_commit])
        self.assertIn("### Unmerged preview changes", markdown)
        self.assertIn("Preview the proposed authoring flow", markdown)
        self.assertIn("Keep the learner continuation", markdown)

    def test_formal_notes_keep_one_first_parent_pr_after_the_merge(self) -> None:
        self.fixture.git("update-ref", "refs/remotes/origin/main", self.merge_commit)

        def github_json(endpoint: str, *, paginate: bool = False):
            if endpoint == "repos/example/skills":
                return {"default_branch": "main"}
            if "/commits/" in endpoint:
                sha = endpoint.split("/commits/", 1)[1].split("/", 1)[0]
                return [{"number": 77}] if sha == self.merge_commit else []
            if endpoint == "repos/example/skills/pulls/77":
                return {
                    "number": 77,
                    "title": "feat: Improve course authoring and continuation",
                    "html_url": "https://github.com/example/skills/pull/77",
                    "user": {"login": "author"},
                    "merged": True,
                    "merged_at": "2026-10-09T04:00:00Z",
                    "merge_commit_sha": self.merge_commit,
                    "base": {
                        "ref": "main",
                        "repo": {"full_name": "example/skills"},
                    },
                }
            self.fail(f"Unexpected GitHub request: {endpoint}")

        with patch.object(release_notes, "_github_json", side_effect=github_json):
            snapshot = release_notes.collect_changes(
                str(self.fixture.source_repo),
                self.merge_commit,
                base_ref="v1.2.2",
                github_repository="example/skills",
            )
        self.assertEqual(len(snapshot["changes"]), 2)
        self.assertEqual(snapshot["pr_count"], 1)
        changes = {change["commit"]: change for change in snapshot["changes"]}
        self.assertEqual(set(changes), {self.main_commit, self.merge_commit})
        self.assertEqual(changes[self.merge_commit]["kind"], "pr")
        self.assertEqual(changes[self.merge_commit]["number"], 77)


if __name__ == "__main__":
    unittest.main()
