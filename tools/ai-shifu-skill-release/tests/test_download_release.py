from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_shifu_release import github_releases
from ai_shifu_release import verify as verification
from support import ReleaseFixture


class DownloadReleaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = ReleaseFixture()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.tearDown)
        cls.commit = cls.fixture.git("rev-parse", "main")
        cls.original = cls.fixture.build(source_ref=cls.commit)

    def test_recovers_and_verifies_exact_release_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, _ = github_releases.prepare_assets(
                self.original, "v1.2.3", self.commit, root / "assets"
            )
            self._download(root, assets)

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
                (root / "assets/SHA256SUMS").write_text(
                    "".join(
                        f"{hashlib.sha256(asset.read_bytes()).hexdigest()}  {asset.name}\n"
                        for asset in assets
                        if asset.name != "SHA256SUMS"
                    ),
                    encoding="utf-8",
                )
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

    def _download(self, root: Path, assets: list[Path]) -> None:
        mapping = {asset.name: asset for asset in assets}

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
                return type("Response", (), {"stdout": self.commit})()
            raise AssertionError(args)

        with patch.object(github_releases, "gh", side_effect=fake_gh):
            recovered = github_releases.download(
                "v1.2.3", "ai-shifu/skills", root / "download"
            )
        self.assertEqual(recovered.name, self.original.name)
        verification.verify(recovered)
        report = json.loads((recovered / "release.json").read_text())
        self.assertEqual(report["source"]["commit"], self.commit)


if __name__ == "__main__":
    unittest.main()
