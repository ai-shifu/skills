from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_build_release


TOOL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = TOOL_ROOT.parents[1]


class ReleaseEntrypointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = test_build_release.BuildReleaseTest()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.tearDown)
        with patch.dict(os.environ, {
            "AISHIFU_PUBLISHER_NAME": "Release Test",
            "AISHIFU_PUBLISHER_EMAIL": "release@example.com",
        }):
            cls.release_dir = cls.fixture.build()

    def test_verify_and_manual_plan_work_from_both_roots(self) -> None:
        for cwd in (REPOSITORY_ROOT, TOOL_ROOT):
            with self.subTest(cwd=cwd):
                entrypoint = os.path.relpath(TOOL_ROOT / "scripts/release.py", cwd)
                verified = subprocess.run(
                    [sys.executable, entrypoint, "verify", str(self.release_dir)],
                    cwd=cwd, check=True, capture_output=True, text=True,
                )
                self.assertIn("release verified", verified.stdout)
                # The candidate points at a local fixture repository, never GitHub.
                planned = subprocess.run(
                    [sys.executable, entrypoint, "manual-plan",
                     str(self.release_dir), "--target", "all"],
                    cwd=cwd, check=True, capture_output=True, text=True,
                )
                plan = json.loads(planned.stdout)
                self.assertEqual(set(plan), {"workbuddy", "qclaw", "doubao"})
                for target in plan.values():
                    self.assertEqual(target["status"], "pending_manual")
                    self.assertTrue(Path(target["upload_path"]).is_file())
                self.assertEqual(len(plan["doubao"]["runtime_tests"][
                    "recommended_instructions"
                ]), 3)

    def test_channel_wrappers_resolve_entrypoint_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            interpreter = temporary_root / "python3"
            interpreter.write_text(
                f"#!{sys.executable}\n"
                "import json, sys\n"
                "print(json.dumps(sys.argv[1:]))\n",
                encoding="utf-8",
            )
            interpreter.chmod(0o755)
            env = dict(os.environ, PATH=f"{temporary}{os.pathsep}{os.environ['PATH']}")
            env.pop("DIST_DIR", None)
            for cwd in (REPOSITORY_ROOT, TOOL_ROOT):
                for wrapper in ("workbuddy/build-zip.sh", "qclaw/build.sh"):
                    for output in (None, str(temporary_root / "custom-output")):
                        with self.subTest(cwd=cwd, wrapper=wrapper, output=output):
                            invocation_env = dict(env)
                            if output is not None:
                                invocation_env["DIST_DIR"] = output
                            result = subprocess.run(
                                [str(TOOL_ROOT / "channels" / wrapper)],
                                cwd=cwd, env=invocation_env, check=True,
                                capture_output=True, text=True,
                            )
                            self.assertEqual(json.loads(result.stdout), [
                                str(TOOL_ROOT / "scripts/release.py"), "build",
                                "--output", output or str(TOOL_ROOT / "dist"),
                            ])
