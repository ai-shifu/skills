"""Shell-independent Windows login guidance preserves arbitrary profile names."""

import importlib.util
import json
import sys
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


if __name__ == "__main__":
    unittest.main()
