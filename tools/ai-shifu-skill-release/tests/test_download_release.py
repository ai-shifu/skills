from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from support import ReleaseFixture

from ai_shifu_release import github_releases
from ai_shifu_release import verify as verification


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
