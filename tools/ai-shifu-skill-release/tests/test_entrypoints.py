from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from support import ReleaseFixture

from ai_shifu_release import TOOL_ROOT, cli

REPOSITORY_ROOT = TOOL_ROOT.parents[1]
COMMANDS = (
    "build",
    "bump",
    "verify",
    "check",
    "publish",
    "manual-plan",
    "record-manual",
    "activate-manifest",
    "github-release",
    "submit-channel",
)


class ReleaseEntrypointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = ReleaseFixture()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.tearDown)
        cls.commit = cls.fixture.git("rev-parse", "main")
        cls.release_dir = cls.fixture.build(source_ref=cls.commit)

    def invoke(
        self, cwd: Path, *arguments: str, tool_root: Path = TOOL_ROOT, **options
    ) -> subprocess.CompletedProcess[str]:
        cwd = cwd.resolve()
        entrypoint = os.path.relpath(tool_root / "scripts/release.py", cwd)
        return subprocess.run(
            [sys.executable, entrypoint, *arguments],
            cwd=cwd,
            capture_output=True,
            text=True,
            **options,
        )

    def test_all_commands_show_help_from_any_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for cwd in (REPOSITORY_ROOT, TOOL_ROOT, Path(temporary).resolve()):
                with self.subTest(cwd=cwd, command="root"):
                    help_output = self.invoke(cwd, "--help", check=True)
                    for command in COMMANDS:
                        self.assertIn(command, help_output.stdout)
                for command in COMMANDS:
                    with self.subTest(cwd=cwd, command=command):
                        result = self.invoke(cwd, command, "--help", check=True)
                        self.assertIn(f"release.py {command}", result.stdout)

    def test_download_is_not_a_public_command(self) -> None:
        result = self.invoke(TOOL_ROOT, "download", "--help")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)

    def test_verify_and_manual_plan_work_from_any_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for cwd in (REPOSITORY_ROOT, TOOL_ROOT, Path(temporary).resolve()):
                with self.subTest(cwd=cwd):
                    verified = self.invoke(
                        cwd, "verify", str(self.release_dir), check=True
                    )
                    self.assertEqual(verified.stdout.strip(), "release verified")
                    # The candidate points at a local fixture repository, never GitHub.
                    planned = self.invoke(
                        cwd,
                        "manual-plan",
                        str(self.release_dir),
                        "--target",
                        "all",
                        check=True,
                    )
                    plan = json.loads(planned.stdout)
                    self.assertEqual(set(plan), {"workbuddy", "doubao"})
                    for target in plan.values():
                        self.assertEqual(target["status"], "pending_manual")
                        self.assertTrue(Path(target["upload_path"]).is_file())
                    self.assertEqual(
                        len(
                            plan["doubao"]["runtime_tests"]["recommended_instructions"]
                        ),
                        3,
                    )

    def test_build_entrypoint_accepts_local_pr_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for index, cwd in enumerate((REPOSITORY_ROOT, TOOL_ROOT, root)):
                with self.subTest(cwd=cwd):
                    output = root / f"output-{index}"
                    result = self.invoke(
                        cwd,
                        "build",
                        "--source-repo-url",
                        str(self.fixture.source_repo),
                        "--source-ref",
                        self.commit,
                        "--expected-version",
                        "1.2.3",
                        "--output",
                        str(output),
                        check=True,
                    )
                    release_dir = Path(result.stdout.strip())
                    self.assertEqual(release_dir.parent, output)
                    report = json.loads((release_dir / "release.json").read_text())
                    self.assertEqual(report["source"]["commit"], self.commit)
                    self.assertEqual(
                        set(report["artifacts"]),
                        {
                            "clawhub",
                            "skillhub",
                            "workbuddy",
                            "doubao",
                        },
                    )
                    self.invoke(cwd, "verify", str(release_dir), check=True)

    def test_standalone_copy_builds_without_git_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            standalone = root / "standalone-tool"
            shutil.copytree(
                TOOL_ROOT,
                standalone,
                symlinks=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "dist", "tests"),
            )
            cwd = root / "caller"
            cwd.mkdir()
            result = self.invoke(
                cwd,
                "build",
                "--source-repo-url",
                str(self.fixture.source_repo),
                "--source-ref",
                self.commit,
                "--expected-version",
                "1.2.3",
                "--output",
                "candidate",
                tool_root=standalone,
                check=True,
            )
            release_dir = Path(result.stdout.strip())
            self.assertEqual(release_dir.parent, cwd / "candidate")
            report = json.loads((release_dir / "release.json").read_text())
            self.assertEqual(
                report["builder"], {"repository": None, "commit": None, "dirty": None}
            )
            original = json.loads((self.release_dir / "release.json").read_text())
            self.assertEqual(report["release_sha256"], original["release_sha256"])
            self.assertEqual(report["artifacts"], original["artifacts"])
            verified = self.invoke(
                cwd, "verify", str(release_dir), tool_root=standalone, check=True
            )
            self.assertEqual(verified.stdout.strip(), "release verified")

    def test_github_release_prepares_six_assets_without_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            commands = root / "bin"
            commands.mkdir()
            marker = root / "unexpected-github-call"
            gh = commands / "gh"
            gh.write_text(
                f"#!{sys.executable}\n"
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('called')\n"
                "raise SystemExit(1)\n",
                encoding="utf-8",
            )
            gh.chmod(0o755)
            env = dict(os.environ, PATH=f"{commands}{os.pathsep}{os.environ['PATH']}")
            result = self.invoke(
                root,
                "github-release",
                str(self.release_dir),
                "--tag",
                "v1.2.3",
                "--commit",
                self.commit,
                "--prepare-only",
                "--output",
                "attachments",
                env=env,
                check=True,
            )
            assets = [Path(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(assets), 6)
            self.assertEqual(sum(path.suffix == ".zip" for path in assets), 4)
            self.assertTrue(all(path.parent == root / "attachments" for path in assets))
            self.assertEqual(
                (root / "attachments/release.json").read_bytes(),
                (self.release_dir / "release.json").read_bytes(),
            )
            checksums = (root / "attachments/SHA256SUMS").read_text().splitlines()
            self.assertEqual(len(checksums), 5)
            for path in assets:
                if path.name != "SHA256SUMS":
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    self.assertIn(f"{digest}  {path.name}", checksums)
            self.assertFalse(marker.exists())

    def test_submit_channel_preserves_result_file_and_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for status in (
                "submitted",
                "pending_review",
                "already_verified",
                "failed",
                "needs_review",
            ):
                with self.subTest(status=status):
                    output = root / status
                    output.mkdir()
                    result = {
                        "target": "skillhub",
                        "tag": "v1.2.3",
                        "version": "1.2.3",
                        "source_commit": self.commit,
                        "status": status,
                        "archive_sha256": "fixture-hash",
                    }
                    stdout = io.StringIO()
                    with (
                        patch.dict(os.environ, {}, clear=True),
                        patch.object(
                            cli.channel_submission, "publish", return_value=result
                        ) as submit,
                        redirect_stdout(stdout),
                    ):
                        arguments = [
                            "submit-channel",
                            "--tag",
                            "v1.2.3",
                            "--repo",
                            "ai-shifu/skills",
                            "--target",
                            "skillhub",
                            "--output",
                            str(output),
                            "--execute",
                        ]
                        if status in {"failed", "needs_review"}:
                            with self.assertRaises(SystemExit) as stopped:
                                cli.main(arguments)
                            self.assertEqual(stopped.exception.code, 1)
                        else:
                            cli.main(arguments)
                    submit.assert_called_once_with(
                        "v1.2.3",
                        "ai-shifu/skills",
                        "skillhub",
                        output,
                        execute=True,
                    )
                    self.assertEqual(json.loads(stdout.getvalue()), result)
                    self.assertEqual(
                        json.loads((output / "platform-result.json").read_text()),
                        result,
                    )

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
                for wrapper in ("workbuddy/build-zip.sh",):
                    for output in (None, str(temporary_root / "custom-output")):
                        with self.subTest(cwd=cwd, wrapper=wrapper, output=output):
                            invocation_env = dict(env)
                            if output is not None:
                                invocation_env["DIST_DIR"] = output
                            result = subprocess.run(
                                [str(TOOL_ROOT / "channels" / wrapper)],
                                cwd=cwd,
                                env=invocation_env,
                                check=True,
                                capture_output=True,
                                text=True,
                            )
                            self.assertEqual(
                                json.loads(result.stdout),
                                [
                                    str(TOOL_ROOT / "scripts/release.py"),
                                    "build",
                                    "--output",
                                    output or str(TOOL_ROOT / "dist"),
                                ],
                            )
