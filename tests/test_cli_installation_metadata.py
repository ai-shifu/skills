"""Distribution markers select npm configuration without changing channel installs."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "ai-shifu-course-creator" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import skill_update_check


class InstallationMetadataTests(unittest.TestCase):
    def setUp(self):
        self.skill = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.marker = self.skill / ".ai-shifu-cli.json"
        self.metadata = {"schema_version": 1, "distribution": "npm", "version": "2.2.1"}

    def test_valid_marker_is_read_without_writing_state(self):
        self.marker.write_text(json.dumps(self.metadata), encoding="utf-8")
        self.assertEqual(skill_update_check.read_installation_metadata(self.skill), self.metadata)
        self.assertEqual(list(self.skill.iterdir()), [self.marker])

    def test_missing_invalid_or_unrecognized_marker_is_not_an_npm_install(self):
        self.assertIsNone(skill_update_check.read_installation_metadata(self.skill))
        invalid = ["not json", "[]", '{"schema_version":1}',
                   json.dumps({**self.metadata, "schema_version": True}),
                   json.dumps({**self.metadata, "schema_version": 2}),
                   json.dumps({**self.metadata, "distribution": "plugin"}),
                   json.dumps({**self.metadata, "version": "02.2.1"}),
                   json.dumps({**self.metadata, "version": "2.2.1-rc.1"}),
                   json.dumps({**self.metadata, "version": "2.2.1\n"}),
                   json.dumps({**self.metadata, "path": "/untrusted/config"})]
        for document in invalid:
            with self.subTest(document=document):
                self.marker.write_text(document, encoding="utf-8")
                self.assertIsNone(skill_update_check.read_installation_metadata(self.skill))


class InstallationEnvironmentProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe = subprocess.run([sys.executable, "-c", "import dotenv, requests"], capture_output=True)
        if probe.returncode:
            raise unittest.SkipTest("Process integration tests require requests and python-dotenv")

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.skill = self.root / "skill"
        self.skill.mkdir()
        shutil.copytree(SCRIPT_DIR, self.skill / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        self.metadata = {"schema_version": 1, "distribution": "npm", "version": "2.2.1"}
        self.environment = {**os.environ, "AI_SHIFU_CONFIG_DIR": str(self.root / "configuration")}
        self.environment.pop("AI_SHIFU_CLI_ENV_FILE", None)
        self.write_skill("standalone")

    def write_skill(self, management):
        (self.skill / "SKILL.md").write_text(
            "---\nname: ai-shifu-course-creator\ndescription: Test\nmetadata:\n"
            f"  version: 2.2.1\n  version_management: {management}\n---\n",
            encoding="utf-8",
        )

    def selected_environment(self):
        script = """import importlib.util, sys
from pathlib import Path
entry = Path(sys.argv[1])
sys.path.insert(0, str(entry.parent))
spec = importlib.util.spec_from_file_location('isolated_cli', entry)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
print(cli.ENV_FILE)
"""
        result = subprocess.run([sys.executable, "-c", script, str(self.skill / "scripts" / "shifu-cli.py")],
                                env=self.environment, capture_output=True, text=True, check=True)
        self.assertFalse((self.root / "configuration").exists(), "reading selection must not create configuration")
        return Path(result.stdout.strip())

    def test_synchronized_python_fallback_shares_the_migrated_environment(self):
        (self.skill / ".ai-shifu-cli.json").write_text(json.dumps(self.metadata), encoding="utf-8")
        self.assertEqual(self.selected_environment(), self.root / "configuration" / "cli.env")

    def test_unmarked_and_plugin_installations_keep_their_environment(self):
        self.assertEqual(self.selected_environment(), self.skill / ".env")
        (self.skill / ".ai-shifu-cli.json").write_text(json.dumps(self.metadata), encoding="utf-8")
        self.write_skill("plugin")
        self.assertEqual(self.selected_environment(), self.skill / ".env")

    def test_explicit_npm_entrypoint_environment_remains_authoritative(self):
        selected = self.root / "explicit" / "cli.env"
        self.environment["AI_SHIFU_CLI_ENV_FILE"] = str(selected)
        self.assertEqual(self.selected_environment(), selected)

    def loaded_configuration_root(self):
        script = """import importlib.util, sys
from pathlib import Path
entry = Path(sys.argv[1])
sys.path.insert(0, str(entry.parent))
spec = importlib.util.spec_from_file_location('isolated_cli', entry)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
cli.load_env()
print(cli.config_dir())
"""
        result = subprocess.run([sys.executable, "-c", script, str(self.skill / "scripts" / "shifu-cli.py")],
                                env=self.environment, capture_output=True, text=True, check=True)
        return Path(result.stdout.strip())

    def test_synchronized_fallback_keeps_the_install_root_after_loading_dotenv(self):
        (self.skill / ".ai-shifu-cli.json").write_text(json.dumps(self.metadata), encoding="utf-8")
        home = self.root / "home"
        self.environment.update({"HOME": str(home), "USERPROFILE": str(home)})
        self.environment.pop("AI_SHIFU_CONFIG_DIR", None)
        self.environment.pop("XDG_CONFIG_HOME", None)
        selected = home / ".config" / "ai-shifu"
        selected.mkdir(parents=True)
        for variable in ("AI_SHIFU_CONFIG_DIR", "XDG_CONFIG_HOME"):
            with self.subTest(variable=variable):
                (selected / "cli.env").write_text(f"{variable}={self.root / 'redirected'}\n", encoding="utf-8")
                self.assertEqual(self.loaded_configuration_root(), selected)
                self.assertFalse((self.root / "redirected").exists())

    def test_unmarked_and_plugin_dotenv_configuration_selection_is_unchanged(self):
        self.environment.pop("AI_SHIFU_CONFIG_DIR", None)
        selected = self.root / "legacy-configuration"
        (self.skill / ".env").write_text(f"AI_SHIFU_CONFIG_DIR={selected}\n", encoding="utf-8")
        self.assertEqual(self.loaded_configuration_root(), selected)
        (self.skill / ".ai-shifu-cli.json").write_text(json.dumps(self.metadata), encoding="utf-8")
        self.write_skill("plugin")
        self.assertEqual(self.loaded_configuration_root(), selected)


if __name__ == "__main__":
    unittest.main()
