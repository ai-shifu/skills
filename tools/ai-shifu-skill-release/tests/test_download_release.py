from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai_shifu_release import (
    artifacts,
    build,
    channel_submission,
    github_releases,
    publishing,
    release_notes,
    skill_metadata,
    source,
)
from ai_shifu_release import verify as verification
from ai_shifu_release.channels import doubao
from support import ReleaseFixture


class DownloadReleaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = ReleaseFixture()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.tearDown)
        cls.commit = cls.fixture.git("rev-parse", "main")
        cls.original = cls.fixture.build(source_ref=cls.commit)
        cls.notes = release_notes.generate_notes(
            str(cls.fixture.source_repo), cls.commit, "1.2.3"
        )
        cls.original_report = json.loads((cls.original / "release.json").read_text())
        cls.original_report["source"]["repository"] = source.SOURCE_REPOSITORY
        (cls.original / "release.json").write_text(json.dumps(cls.original_report))

    def setUp(self) -> None:
        self.last_transport = None
        # These tests exercise package transport and the independent source build.
        # Keep unrelated PR metadata collection on the local fixture history.
        notes = patch.object(release_notes, "generate_notes", return_value=self.notes)
        notes.start()
        self.addCleanup(notes.stop)

    def test_recovers_and_verifies_exact_release_assets(self) -> None:
        for repository in (
            source.SOURCE_REPOSITORY,
            "git@github.com:ai-shifu/skills.git",
            "ssh://git@github.com/ai-shifu/skills.git",
        ):
            with (
                self.subTest(repository=repository),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                assets, _ = github_releases.prepare_assets(
                    self.original, "v1.2.3", self.commit, root / "assets"
                )
                manifest = root / "assets/release.json"
                report = json.loads(manifest.read_text())
                report["source"]["repository"] = repository
                # Builder provenance may differ when a historical source is rebuilt.
                report["builder"] = {
                    "repository": "https://example.invalid/old-builder.git",
                    "commit": "f" * 40,
                    "dirty": False,
                }
                manifest.write_text(json.dumps(report))
                self._refresh_checksums(assets)
                self._download(root, assets)
                self.last_transport.assert_called_once()

    def test_corrupt_attachment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, _ = github_releases.prepare_assets(
                self.original, "v1.2.3", self.commit, root / "assets"
            )
            next(asset for asset in assets if asset.suffix == ".zip").write_bytes(
                b"corrupt"
            )
            with self.assertRaisesRegex(ValueError, "checksum differs"):
                self._download(root, assets)

    def test_rejects_invalid_release_id_before_creating_reconstruction(self) -> None:
        for kind in (
            "parent",
            "absolute",
            "nested_parent",
            "output_itself",
            "empty",
            "null",
            "number",
            "list",
        ):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                outside = root / "escaped-release"
                release_ids = {
                    "parent": "../escaped-release",
                    "absolute": str(outside),
                    "nested_parent": "nested/../../escaped-release",
                    "output_itself": str(root / "download"),
                    "empty": "",
                    "null": None,
                    "number": 42,
                    "list": ["release"],
                }
                assets, _ = github_releases.prepare_assets(
                    self.original, "v1.2.3", self.commit, root / "assets"
                )
                manifest = root / "assets/release.json"
                report = json.loads(manifest.read_text())
                report["release_id"] = release_ids[kind]
                manifest.write_text(json.dumps(report), encoding="utf-8")
                self._refresh_checksums(assets)
                error = (
                    "Release ID must be a nonempty string"
                    if kind in {"empty", "null", "number", "list"}
                    else "escapes release directory"
                )
                with (
                    patch.object(github_releases, "extract_archive") as extract,
                    self.assertRaisesRegex(ValueError, error),
                ):
                    self._download(root, assets)
                extract.assert_not_called()
                self.assertFalse(outside.exists())
                self.assertEqual(
                    {path.name for path in (root / "download").iterdir()},
                    {asset.name for asset in assets},
                )

    def test_rejects_self_consistent_forged_canonical_body(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attacker_repo = root / "attacker-source"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    str(self.fixture.source_repo),
                    str(attacker_repo),
                ],
                check=True,
                capture_output=True,
            )

            def git(*args: str) -> str:
                return subprocess.run(
                    ["git", *args],
                    cwd=attacker_repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            git("config", "user.name", "Source Test")
            git("config", "user.email", "source-test@example.com")
            skill = attacker_repo / "skills/ai-shifu-course-creator/SKILL.md"
            skill.write_text(skill.read_text() + "\nUntrusted canonical instruction.\n")
            git("add", "skills/ai-shifu-course-creator/SKILL.md")
            git("commit", "-m", "fixture changed instruction")
            forged = build.build(
                SimpleNamespace(
                    source_repo_url=str(attacker_repo),
                    source_ref=git("rev-parse", "HEAD"),
                    expected_version="1.2.3",
                    skill_name="ai-shifu-course-creator",
                    output=str(root / "forged-dist"),
                )
            )
            report = json.loads((forged / "release.json").read_text())
            report["source"] = dict(self.original_report["source"])
            report["source_committed_at"] = self.original_report["source_committed_at"]
            for record in report["artifacts"]["doubao"]["embedded_skills"].values():
                record["source_commit"] = self.commit
            self._write_forged_manifest(forged, report)
            self._assert_self_consistent_forgery_rejected(root, forged, changed_zips=4)

    def test_rejects_self_consistent_forged_companion_body(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            forged = root / "forged-release"
            shutil.copytree(self.original, forged)
            report = json.loads((forged / "release.json").read_text())
            record = report["artifacts"]["doubao"]
            name = "course-direction-advisor"
            embedded = record["embedded_skills"][name]
            skill = (
                forged / record["directory"] / "workspace/skills" / name / "SKILL.md"
            )
            frontmatter, body = skill_metadata.split_skill_document(
                skill.read_text(), str(skill)
            )
            body += "\nUntrusted companion instruction.\n"
            skill.write_text(f"---\n{frontmatter}\n---\n{body}")
            source_text = f"---\n{embedded['source_frontmatter']}\n---\n{body}"
            digest = artifacts.content_hash(source_text.encode())
            embedded["source_skill_sha256"] = digest
            embedded["source_files"]["SKILL.md"]["sha256"] = digest
            embedded["source_tree_sha256"] = artifacts.manifest_tree_hash(
                embedded["source_files"]
            )
            embedded["body_sha256"] = artifacts.content_hash(body.encode())
            self.fixture.refresh_doubao_hashes(forged, report)
            self._write_forged_manifest(forged, report)
            self._assert_self_consistent_forgery_rejected(root, forged, changed_zips=1)

    def test_rejects_self_consistent_forged_channel_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            forged = root / "forged-release"
            shutil.copytree(self.original, forged)
            report = json.loads((forged / "release.json").read_text())
            record = report["artifacts"]["doubao"]
            package = forged / record["directory"]
            profile = json.loads(record["source_profile_json"])
            profile["readme_intro"] += "\nUntrusted channel presentation."
            record["source_profile_json"] = json.dumps(profile, ensure_ascii=False)
            record["source_profile_sha256"] = artifacts.content_hash(
                record["source_profile_json"].encode()
            )
            (package / "agent.yml").write_text(
                doubao.render_agent_yml(
                    profile, self.fixture.source_frontmatter(report)
                )
            )
            (package / "README.md").write_text(doubao.render_readme(profile))
            self.fixture.refresh_doubao_hashes(forged, report)
            self._write_forged_manifest(forged, report)
            self._assert_self_consistent_forgery_rejected(root, forged, changed_zips=1)

    def test_repository_spoof_cannot_choose_a_source_fetch(self) -> None:
        for repository in (
            "https://github.com/attacker/skills.git",
            "https://evil.example/github.com/ai-shifu/skills.git",
            "https://github.com@evil.example/ai-shifu/skills.git",
        ):
            with (
                self.subTest(repository=repository),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                assets, _ = github_releases.prepare_assets(
                    self.original, "v1.2.3", self.commit, root / "assets"
                )
                manifest = root / "assets/release.json"
                report = json.loads(manifest.read_text())
                report["source"]["repository"] = repository
                manifest.write_text(json.dumps(report))
                self._refresh_checksums(assets)
                self._assert_checksums(assets)
                with (
                    patch.object(publishing, "AutomatedPublisher") as publisher,
                    self.assertRaisesRegex(ValueError, "(?i)repository"),
                ):
                    self._download(root, assets, submit=True)
                self.last_transport.assert_not_called()
                publisher.assert_not_called()

    def test_source_timestamp_must_match_even_when_archives_do_not_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, _ = github_releases.prepare_assets(
                self.original, "v1.2.3", self.commit, root / "assets"
            )
            manifest = root / "assets/release.json"
            report = json.loads(manifest.read_text())
            report["source_committed_at"] = "2000-01-01T00:00:00+00:00"
            manifest.write_text(json.dumps(report))
            self._refresh_checksums(assets)
            self._assert_checksums(assets)
            with self.assertRaisesRegex(
                ValueError, "(?i)(tagged source|source build|trusted source)"
            ):
                self._download(root, assets)

    def test_source_fetch_failure_prevents_channel_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, _ = github_releases.prepare_assets(
                self.original, "v1.2.3", self.commit, root / "assets"
            )
            with (
                patch.object(publishing, "AutomatedPublisher") as publisher,
                self.assertRaisesRegex((OSError, ValueError), "(?i)(source|rebuild)"),
            ):
                self._download(
                    root,
                    assets,
                    submit=True,
                    fetch_error=OSError("fixture source transport unavailable"),
                )
            self.last_transport.assert_called_once()
            publisher.assert_not_called()

    def _write_forged_manifest(self, release_dir: Path, report: dict) -> None:
        report["release_id"] = (
            f"ai-shifu-course-creator-1.2.3-{self.commit[:7]}-{report['release_sha256'][:7]}"
        )
        (release_dir / "release.json").write_text(json.dumps(report))

    def _assert_self_consistent_forgery_rejected(
        self, root: Path, forged: Path, *, changed_zips: int
    ) -> None:
        # All downloaded checksums and the self-reported source proofs are valid.
        # Rejection must come from comparison with an independent tagged-source build.
        verification.verify(forged)
        report = json.loads((forged / "release.json").read_text())
        self.assertEqual(report["source"], self.original_report["source"])
        self.assertEqual(
            sum(
                artifacts.file_hash(forged / report["artifacts"][channel]["archive"])
                != artifacts.file_hash(
                    self.original
                    / self.original_report["artifacts"][channel]["archive"]
                )
                for channel in artifacts.CHANNEL_ORDER
            ),
            changed_zips,
        )
        assets, _ = github_releases.prepare_assets(
            forged, "v1.2.3", self.commit, root / "assets"
        )
        self._assert_checksums(assets)
        with (
            patch.object(publishing, "AutomatedPublisher") as publisher,
            self.assertRaisesRegex(
                ValueError, "(?i)(tagged source|source build|trusted source)"
            ),
        ):
            self._download(root, assets, submit=True)
        self.last_transport.assert_called_once()
        publisher.assert_not_called()

    @staticmethod
    def _refresh_checksums(assets: list[Path]) -> None:
        checksums = next(asset for asset in assets if asset.name == "SHA256SUMS")
        checksums.write_text(
            "".join(
                f"{artifacts.file_hash(asset)}  {asset.name}\n"
                for asset in assets
                if asset.name != "SHA256SUMS"
            ),
            encoding="utf-8",
        )

    def _assert_checksums(self, assets: list[Path]) -> None:
        checksums = next(asset for asset in assets if asset.name == "SHA256SUMS")
        expected = {
            asset.name: artifacts.file_hash(asset)
            for asset in assets
            if asset.name != "SHA256SUMS"
        }
        actual = {
            name: digest
            for digest, name in (
                line.split("  ", 1) for line in checksums.read_text().splitlines()
            )
        }
        self.assertEqual(actual, expected)

    def _download(
        self,
        root: Path,
        assets: list[Path],
        *,
        submit: bool = False,
        fetch_error: Exception | None = None,
    ) -> None:
        mapping = {asset.name: asset for asset in assets}
        fetch_source = source.fetch_source

        def trusted_transport(repository: str, destination: Path, source_ref: str):
            self.assertEqual(repository, source.SOURCE_REPOSITORY)
            self.assertEqual(source_ref, self.commit)
            if fetch_error is not None:
                raise fetch_error
            commit, _ = fetch_source(
                str(self.fixture.source_repo), destination, source_ref
            )
            return commit, repository

        def fake_gh(*args: str, **kwargs):
            if args[:2] == ("release", "view"):
                return type(
                    "Response",
                    (),
                    {
                        "stdout": json.dumps(
                            {
                                "isDraft": False,
                                "tagName": "v1.2.3",
                                "assets": [{"name": name} for name in mapping],
                            }
                        )
                    },
                )()
            if args[:2] == ("release", "download"):
                name = args[args.index("--pattern") + 1]
                shutil.copy2(mapping[name], Path(args[args.index("--dir") + 1]) / name)
                return type("Response", (), {"stdout": ""})()
            if args[0] == "api":
                self.assertEqual(args[1], "repos/ai-shifu/skills/commits/v1.2.3")
                return type("Response", (), {"stdout": self.commit})()
            raise AssertionError(args)

        with (
            patch.object(github_releases, "gh", side_effect=fake_gh),
            patch.object(
                build, "fetch_source", side_effect=trusted_transport
            ) as transport,
        ):
            self.last_transport = transport
            if submit:
                channel_submission.publish(
                    "v1.2.3",
                    "ai-shifu/skills",
                    "clawhub",
                    root / "download",
                    execute=True,
                )
                return
            recovered = github_releases.download(
                "v1.2.3", "ai-shifu/skills", root / "download"
            )
        self.assertEqual(
            recovered.name,
            json.loads(mapping["release.json"].read_text())["release_id"],
        )
        verification.verify(recovered)
        report = json.loads((recovered / "release.json").read_text())
        self.assertEqual(report["source"]["commit"], self.commit)


if __name__ == "__main__":
    unittest.main()
