"""Shell-independent Windows login guidance preserves arbitrary profile names."""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "ai-shifu-course-creator" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location("profile_login_hints_cli", SCRIPT_DIR / "shifu-cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class ProfileLoginHintTests(unittest.TestCase):
    def setUp(self):
        self.process_environment = dict(cli.os.environ)
        self.enterContext(mock.patch.dict(cli.os.environ, {}, clear=True))

    def test_windows_hints_round_trip_without_shell_interpretation(self):
        names = ["Daily Work", "客户 A", "a&echo injected", "quote\"name", "quote'name",
                 "%USERNAME%", "!expanded!", "$(whoami)", "a|b", "a^b", "-demo"]
        for name in names:
            for wait in (False, True):
                with self.subTest(name=name, wait=wait), mock.patch.object(
                    cli.platform, "system", return_value="Windows",
                ), mock.patch.object(cli.shlex, "quote", side_effect=AssertionError("POSIX quoting used")):
                    hint = cli._login_instruction(types.SimpleNamespace(name=name), wait=wait)
                prefix = "Invoke shifu-cli.py with this argument list (JSON, not a shell command): "
                self.assertTrue(hint.startswith(prefix))
                argv = json.loads(hint[len(prefix):])
                args = cli.build_parser().parse_args(argv)
                self.assertEqual(args.profile, name)
                self.assertEqual(args.wait, wait)

    def test_windows_auth_recovery_uses_the_same_literal_argument_guidance(self):
        context = types.SimpleNamespace(name="客户 & A")
        with mock.patch.object(cli.platform, "system", return_value="Windows"):
            self.assertIn(cli._login_instruction(context), cli._auth_recovery(context))

    def test_npm_hints_use_the_installed_command(self):
        context = types.SimpleNamespace(name="客户 & A")
        with mock.patch.dict(cli.os.environ, {"AI_SHIFU_CLI_ENV_FILE": "/user/cli.env"}):
            for system in ("Darwin", "Windows"):
                with self.subTest(system=system), mock.patch.object(cli.platform, "system", return_value=system):
                    hint = cli._login_instruction(context, wait=True)
                    self.assertNotIn("shifu-cli.py", hint)
                    if system == "Windows":
                        prefix = "Invoke shifu with this argument list (JSON, not a shell command): "
                        self.assertTrue(hint.startswith(prefix))
                        argv = json.loads(hint[len(prefix):])
                    else:
                        self.assertTrue(hint.startswith("Run `shifu login "))
                        argv = cli.shlex.split(hint.removeprefix("Run `").removesuffix("`"))[1:]
                    args = cli.build_parser().parse_args(argv)
                    self.assertEqual(args.profile, context.name)
                    self.assertTrue(args.wait)

    def test_compatibility_hints_keep_the_embedded_command(self):
        with mock.patch.object(cli.platform, "system", return_value="Darwin"):
            self.assertEqual(cli._login_instruction(types.SimpleNamespace(name="default")),
                             "Run `shifu-cli.py login --profile=default`")

    def test_synchronized_fallback_quotes_python_and_script_paths(self):
        python = "/Applications/课程 工具/bin/python"
        entry = str((Path(tempfile.gettempdir()) / "课程 Skill" / "shifu-cli.py").resolve())
        profile = "客户 A & 'quote' $(whoami)"
        with mock.patch.object(cli, "_NPM_SYNCHRONIZED", True), \
                mock.patch.object(cli.sys, "executable", python), \
                mock.patch.object(cli, "__file__", entry):
            for system in ("Darwin", "Windows"):
                with self.subTest(system=system), mock.patch.object(cli.platform, "system", return_value=system):
                    hint = cli._login_instruction(types.SimpleNamespace(name=profile), wait=True)
                    if system == "Windows":
                        prefix = "Invoke this complete argument list (JSON, not a shell command): "
                        self.assertTrue(hint.startswith(prefix))
                        arguments = json.loads(hint[len(prefix):])
                    else:
                        arguments = cli.shlex.split(hint.removeprefix("Run `").removesuffix("`"))
                    self.assertEqual(arguments, [python, entry, "login", f"--profile={profile}", "--wait"])

    def test_real_marker_selects_a_runnable_python_fallback_in_a_child_process(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        skill = root / "课程 Skill"
        shutil.copytree(SCRIPT_DIR, skill / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        (skill / ".ai-shifu-cli.json").write_text(
            json.dumps({"schema_version": 1, "distribution": "npm", "version": "2.2.1"}), encoding="utf-8",
        )
        (skill / "SKILL.md").write_text(
            "---\nname: ai-shifu-course-creator\ndescription: Test\nmetadata:\n"
            "  version: 2.2.1\n  version_management: standalone\n---\n", encoding="utf-8",
        )
        environment = {**self.process_environment, "AI_SHIFU_CONFIG_DIR": str(root / "configuration"),
                       "PYTHONIOENCODING": "utf-8"}
        environment.pop("AI_SHIFU_CLI_ENV_FILE", None)
        environment.pop("AI_SHIFU_CLI_DISTRIBUTION", None)
        entry = skill / "scripts" / "shifu-cli.py"
        profile = "客户 A & 'quote' $(whoami)"
        script = """import importlib.util, sys, types
from pathlib import Path
entry = Path(sys.argv[1])
sys.path.insert(0, str(entry.parent))
spec = importlib.util.spec_from_file_location('marked_fallback', entry)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
assert cli._NPM_SYNCHRONIZED
cli.platform.system = lambda: sys.argv[3]
print(cli._login_instruction(types.SimpleNamespace(name=sys.argv[2]), wait=True))
"""
        for system in ("Darwin", "Windows"):
            with self.subTest(system=system):
                result = subprocess.run([sys.executable, "-c", script, str(entry), profile, system],
                                        env=environment, encoding="utf-8", capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                hint = result.stdout.strip()
                if system == "Windows":
                    prefix = "Invoke this complete argument list (JSON, not a shell command): "
                    self.assertTrue(hint.startswith(prefix))
                    arguments = json.loads(hint[len(prefix):])
                else:
                    arguments = cli.shlex.split(hint.removeprefix("Run `").removesuffix("`"))
                self.assertEqual(arguments, [sys.executable, str(entry), "login", f"--profile={profile}", "--wait"])


if __name__ == "__main__":
    unittest.main()
