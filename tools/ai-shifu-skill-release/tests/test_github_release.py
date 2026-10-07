from __future__ import annotations

import json
import io
import os
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

import test_build_release
from scripts import github_release


class GitHubReleaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = test_build_release.BuildReleaseTest()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.tearDown)
        cls.commit = cls.fixture.git("rev-parse", "main")
        cls.release_dir = cls.fixture.build(source_ref=cls.commit, expected_version="1.2.3")

    def test_prepares_four_distinct_packages_and_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets, notes = github_release.prepare_assets(
                self.release_dir, "v1.2.3", self.commit, Path(temporary)
            )
            self.assertEqual(len(assets), 6)
            self.assertEqual(len({asset.name for asset in assets}), 6)
            self.assertEqual(len([asset for asset in assets if asset.suffix == ".zip"]), 4)
            self.assertIn(self.commit, notes)
            self.assertIn("clawhub-", assets[0].name)
            checksums = assets[-1].read_text(encoding="utf-8")
            for asset in assets[:-1]:
                self.assertIn(f"{github_release.sha256(asset)}  {asset.name}", checksums)

    def test_rejects_wrong_tag_or_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            with self.assertRaisesRegex(ValueError, "Tag must use vX.Y.Z"):
                github_release.prepare_assets(self.release_dir, "skills-v1.2.3", self.commit, destination)
            with self.assertRaisesRegex(ValueError, "version differ"):
                github_release.prepare_assets(self.release_dir, "v1.2.4", self.commit, destination)
            with self.assertRaisesRegex(ValueError, "version differ"):
                github_release.prepare_assets(self.release_dir, "v1.2.3", "a" * 40, destination)

    def test_existing_published_release_cannot_gain_missing_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets, notes = github_release.prepare_assets(
                self.release_dir, "v1.2.3", self.commit, Path(temporary)
            )
            response = type("Response", (), {"returncode": 0,
                "stdout": json.dumps({"isDraft": False, "assets": []})})()
            with patch.dict(os.environ, {"GITHUB_REPOSITORY": "ai-shifu/skills"}), \
                 patch.object(github_release, "gh", return_value=response):
                with self.assertRaisesRegex(ValueError, "missing"):
                    github_release.publish("v1.2.3", self.commit, assets, notes)

    def test_new_release_stays_draft_until_every_asset_is_uploaded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets, notes = github_release.prepare_assets(
                self.release_dir, "v1.2.3", self.commit, Path(temporary)
            )
            calls = []
            remote = {}
            created = False
            published = False

            def fake_gh(*args, check=True):
                nonlocal created, published
                action = args[1]
                calls.append(action)
                if action == "view":
                    if not created:
                        return type("Response", (), {"returncode": 1, "stdout": ""})()
                    payload = {"isDraft": not published, "assets": [{"name": name} for name in remote],
                               "url": "https://github.com/ai-shifu/skills/releases/tag/v1.2.3"}
                    return type("Response", (), {"returncode": 0, "stdout": json.dumps(payload)})()
                if action == "create":
                    self.assertIn("--draft", args)
                    self.assertIn("--verify-tag", args)
                    created = True
                elif action == "upload":
                    self.assertFalse(published)
                    asset = Path(args[3])
                    remote[asset.name] = asset.read_bytes()
                elif action == "download":
                    name = args[args.index("--pattern") + 1]
                    directory = Path(args[args.index("--dir") + 1])
                    (directory / name).write_bytes(remote[name])
                elif action == "edit":
                    self.assertEqual(set(remote), {asset.name for asset in assets})
                    published = True
                return type("Response", (), {"returncode": 0, "stdout": ""})()

            with patch.dict(os.environ, {"GITHUB_REPOSITORY": "ai-shifu/skills"}), \
                 patch.object(github_release, "gh", side_effect=fake_gh), \
                 redirect_stdout(io.StringIO()):
                github_release.publish("v1.2.3", self.commit, assets, notes)
            self.assertTrue(published)
            self.assertEqual(calls.count("create"), 1)
            self.assertEqual(calls.count("upload"), len(assets))
            self.assertEqual(calls[-1], "edit")

    def test_branch_preview_uploads_and_verifies_without_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets, notes = github_release.prepare_assets(
                self.release_dir, "v1.2.3", self.commit, Path(temporary)
            )
            preview_tag = f"preview-v1.2.3-{self.commit}-123-1"
            remote = {}
            created = False
            calls = []

            def fake_gh(*args, check=True):
                nonlocal created
                action = args[1]
                calls.append(action)
                if action == "view":
                    if not created:
                        return type("Response", (), {"returncode": 1, "stdout": ""})()
                    payload = {"isDraft": True, "assets": [{"name": name} for name in remote],
                               "url": f"https://github.com/ai-shifu/skills/releases/tag/{preview_tag}"}
                    return type("Response", (), {"returncode": 0, "stdout": json.dumps(payload)})()
                if action == "create":
                    self.assertIn("--draft", args)
                    self.assertNotIn("--verify-tag", args)
                    self.assertEqual(args[args.index("--target") + 1], self.commit)
                    notes_path = Path(args[args.index("--notes-file") + 1])
                    self.assertIn("TEST DRAFT ONLY", notes_path.read_text(encoding="utf-8"))
                    created = True
                elif action == "upload":
                    asset = Path(args[3])
                    remote[asset.name] = asset.read_bytes()
                elif action == "download":
                    name = args[args.index("--pattern") + 1]
                    directory = Path(args[args.index("--dir") + 1])
                    (directory / name).write_bytes(remote[name])
                elif action == "edit":
                    self.fail("A branch preview must never publish the Draft Release")
                return type("Response", (), {"returncode": 0, "stdout": ""})()

            with patch.dict(os.environ, {"GITHUB_REPOSITORY": "ai-shifu/skills"}), \
                 patch.object(github_release, "gh", side_effect=fake_gh), \
                 redirect_stdout(io.StringIO()):
                github_release.publish(preview_tag, self.commit, assets, notes,
                                       draft_preview=True, version_tag="v1.2.3")
            self.assertEqual(set(remote), {asset.name for asset in assets})
            self.assertEqual(calls.count("download"), len(assets))
            self.assertNotIn("edit", calls)

    def test_branch_preview_rejects_wrong_identity_or_public_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets, notes = github_release.prepare_assets(
                self.release_dir, "v1.2.3", self.commit, Path(temporary)
            )
            preview_tag = f"preview-v1.2.3-{self.commit}-123-1"
            with self.assertRaisesRegex(ValueError, "version and exact source commit"):
                github_release.publish(preview_tag, self.commit, assets, notes,
                                       draft_preview=True, version_tag="v1.2.4")
            with self.assertRaisesRegex(ValueError, "version and exact source commit"):
                github_release.publish(preview_tag, "a" * 40, assets, notes,
                                       draft_preview=True, version_tag="v1.2.3")
            response = type("Response", (), {"returncode": 0,
                "stdout": json.dumps({"isDraft": False, "assets": []})})()
            with patch.dict(os.environ, {"GITHUB_REPOSITORY": "ai-shifu/skills"}), \
                 patch.object(github_release, "gh", return_value=response):
                with self.assertRaisesRegex(ValueError, "already public"):
                    github_release.publish(preview_tag, self.commit, assets, notes,
                                           draft_preview=True, version_tag="v1.2.3")

    def test_interrupted_draft_upload_can_resume_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets, notes = github_release.prepare_assets(
                self.release_dir, "v1.2.3", self.commit, Path(temporary)
            )
            remote = {}
            published = False
            uploads = 0
            interrupt = True

            def fake_gh(*args, check=True):
                nonlocal published, uploads, interrupt
                action = args[1]
                if action == "view":
                    payload = {"isDraft": not published, "assets": [{"name": name} for name in remote],
                               "url": "https://github.com/ai-shifu/skills/releases/tag/v1.2.3"}
                    return type("Response", (), {"returncode": 0, "stdout": json.dumps(payload)})()
                if action == "upload":
                    uploads += 1
                    if interrupt and uploads == 3:
                        raise RuntimeError("upload interrupted")
                    path = Path(args[3])
                    remote[path.name] = path.read_bytes()
                elif action == "download":
                    name = args[args.index("--pattern") + 1]
                    directory = Path(args[args.index("--dir") + 1])
                    (directory / name).write_bytes(remote[name])
                elif action == "edit":
                    published = True
                return type("Response", (), {"returncode": 0, "stdout": ""})()

            with patch.dict(os.environ, {"GITHUB_REPOSITORY": "ai-shifu/skills"}), \
                 patch.object(github_release, "gh", side_effect=fake_gh):
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    github_release.publish("v1.2.3", self.commit, assets, notes)
                self.assertFalse(published)
                interrupt = False
                first_name = assets[0].name
                correct_bytes = remote[first_name]
                remote[first_name] = b"corrupt draft attachment"
                with self.assertRaisesRegex(ValueError, "different content"):
                    github_release.publish("v1.2.3", self.commit, assets, notes)
                self.assertFalse(published)
                remote[first_name] = correct_bytes
                with redirect_stdout(io.StringIO()):
                    github_release.publish("v1.2.3", self.commit, assets, notes)
                upload_count = uploads
                with redirect_stdout(io.StringIO()):
                    github_release.publish("v1.2.3", self.commit, assets, notes)
                self.assertEqual(uploads, upload_count)
                remote[assets[0].name] = b"different published content"
                with self.assertRaisesRegex(ValueError, "different content"):
                    github_release.publish("v1.2.3", self.commit, assets, notes)
            self.assertTrue(published)
            self.assertEqual(set(remote), {asset.name for asset in assets})
