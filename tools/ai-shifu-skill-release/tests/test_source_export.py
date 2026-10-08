from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from ai_shifu_release.artifacts import CHANNEL_ORDER
from support import ReleaseFixture


class SourceExportTest(unittest.TestCase):
    def test_builder_tar_umask_does_not_change_release_bytes(self) -> None:
        fixture = ReleaseFixture()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        commit = fixture.git("rev-parse", "main")
        baseline = fixture.build(source_ref=commit)
        expected = json.loads((baseline / "release.json").read_text())
        for umask in ("0077", "0000", "user"):
            with self.subTest(umask=umask):
                with patch.dict(
                    os.environ,
                    {
                        "GIT_CONFIG_COUNT": "1",
                        "GIT_CONFIG_KEY_0": "tar.umask",
                        "GIT_CONFIG_VALUE_0": umask,
                    },
                ):
                    fixture.output = fixture.root / f"dist-{umask}"
                    candidate = fixture.build(source_ref=commit)
                actual = json.loads((candidate / "release.json").read_text())
                self.assertEqual(actual["release_sha256"], expected["release_sha256"])
                self.assertEqual(actual["artifacts"], expected["artifacts"])
                for channel in CHANNEL_ORDER:
                    archive = expected["artifacts"][channel]["archive"]
                    self.assertEqual(
                        (candidate / archive).read_bytes(),
                        (baseline / archive).read_bytes(),
                    )
