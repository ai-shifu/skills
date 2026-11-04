"""npm migration keeps an existing custom profile root in place."""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPOSITORY / "skills/ai-shifu-course-creator/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import profile_store


class NpmConfigurationRootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        specification = importlib.machinery.PathFinder.find_spec("dotenv")
        if specification is None or specification.origin is None:
            raise unittest.SkipTest("Configuration root tests require python-dotenv")
        alias = "_npm_root_test_dotenv"
        actual = importlib.util.spec_from_file_location(
            alias, specification.origin,
            submodule_search_locations=specification.submodule_search_locations,
        )
        cls.dotenv = importlib.util.module_from_spec(actual)
        sys.modules[alias] = cls.dotenv
        actual.loader.exec_module(cls.dotenv)

    def setUp(self):
        self.enterContext(mock.patch.object(profile_store, "dotenv_values", self.dotenv.dotenv_values))
        self.enterContext(mock.patch.object(profile_store, "set_key", self.dotenv.set_key))
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.home = self.directory / "home"
        self.default_root = self.home / ".config/ai-shifu"
        self.environment = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home),
                            "XDG_CONFIG_HOME": str(self.home / ".config")}
        for key in ("AI_SHIFU_CONFIG_DIR", "AI_SHIFU_CLI_ENV_FILE", "SHIFU_BASE_URL", "SHIFU_TOKEN"):
            self.environment.pop(key, None)

    def source(self, name, content):
        directory = self.directory / name
        directory.mkdir()
        (directory / ".env").write_text(content, encoding="utf-8")
        return directory

    def pointer(self, selected):
        profile_store.write_private_json(self.default_root / "cli-config-root.json", {
            "schema_version": 1, "config_dir": str(selected),
        })

    def marked_skill(self):
        skill = self.directory / "marked-skill"
        shutil.copytree(SCRIPT_DIR, skill / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        (skill / "SKILL.md").write_text(
            "---\nname: ai-shifu-course-creator\nmetadata:\n  version: 2.2.1\n"
            "  version_management: standalone\n---\n", encoding="utf-8")
        shutil.copyfile(SCRIPT_DIR.parent / ".env.example", skill / ".env.example")
        (skill / ".ai-shifu-cli.json").write_text(json.dumps({
            "schema_version": 1, "distribution": "npm", "version": "2.2.1",
        }), encoding="utf-8")
        return skill

    def test_marked_fallback_reports_a_bad_pointer_through_the_configuration_error_boundary(self):
        skill = self.marked_skill()
        self.default_root.mkdir(parents=True)
        pointer = self.default_root / "cli-config-root.json"
        pointer.write_text("not json", encoding="utf-8")
        result = subprocess.run([sys.executable, str(skill / "scripts/shifu-cli.py"), "site"],
                                env=self.environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn("Configuration error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(pointer.read_text(), "not json")
        self.assertFalse((skill / ".env").exists())
        self.assertFalse((self.default_root / "cli.env").exists())
        self.assertFalse((self.default_root / "settings.json").exists())

        # An explicit process root remains authoritative even when the default
        # pointer is damaged, and the pointer is never silently rewritten.
        selected = self.directory / "explicit"
        environment = {**self.environment, "AI_SHIFU_CONFIG_DIR": str(selected)}
        result = subprocess.run([sys.executable, str(skill / "scripts/shifu-cli.py"), "site"],
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "selection_required")
        self.assertTrue((selected / "cli.env").is_file())
        self.assertFalse((skill / ".env").exists())
        self.assertEqual(pointer.read_text(), "not json")

    def test_account_independent_fallback_commands_do_not_use_a_placeholder_root(self):
        skill = self.marked_skill()
        self.default_root.mkdir(parents=True)
        (self.default_root / "cli-config-root.json").write_text("not json", encoding="utf-8")
        entrypoint = skill / "scripts/shifu-cli.py"
        help_result = subprocess.run([sys.executable, str(entrypoint), "--help"],
                                     env=self.environment, capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        course = self.directory / "local-course"
        (course / "lessons").mkdir(parents=True)
        (course / "lessons/lesson-01.md").write_text("# A local lesson\n", encoding="utf-8")
        build_result = subprocess.run([sys.executable, str(entrypoint), "build", "--course-dir", str(course)],
                                      env=self.environment, capture_output=True, text=True)
        self.assertEqual(build_result.returncode, 0, build_result.stderr)
        self.assertTrue((course / "shifu-import.json").is_file())
        script = """import importlib.util, sys
from pathlib import Path
entry = Path(sys.argv[1]); sys.path.insert(0, str(entry.parent))
spec = importlib.util.spec_from_file_location('fallback_cli', entry)
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
try:
    cli.config_dir()
except cli.profiles.ProfileError:
    pass
else:
    raise AssertionError('configuration lookup must not fall back to another directory')
cli.check_for_update = lambda: {'status': 'latest'}
sys.argv = [str(entry), 'check-update']; cli.main()
"""
        update_result = subprocess.run([sys.executable, "-c", script, str(entrypoint)],
                                       env=self.environment, capture_output=True, text=True)
        self.assertEqual(update_result.returncode, 0, update_result.stderr)
        self.assertEqual(json.loads(update_result.stdout)["status"], "latest")
        self.assertFalse((skill / ".env").exists())
        self.assertFalse((self.default_root / "cli.env").exists())
        self.assertFalse((self.default_root / "settings.json").exists())

    def test_explicit_process_root_overrides_legacy_values_and_does_not_read_a_pointer(self):
        chosen = self.directory / "chosen"
        chosen.mkdir()
        (chosen / "cli-config-root.json").write_text("broken", encoding="utf-8")
        source = self.source("old", f"AI_SHIFU_CONFIG_DIR={self.directory / 'old-root'}\n")
        environment = {**self.environment, "AI_SHIFU_CONFIG_DIR": str(chosen)}
        self.assertEqual(profile_store.npm_config_dir(environment), chosen)
        self.assertEqual(profile_store.resolve_installer_config_root(chosen, [source], environment), chosen)

    def test_selected_legacy_ai_root_precedes_xdg_but_process_xdg_overrides_the_same_key(self):
        old_ai = self.directory / "old-ai"
        old_xdg = self.directory / "old-xdg"
        ai = self.source("ai", f"AI_SHIFU_CONFIG_DIR={old_ai}\nXDG_CONFIG_HOME={old_xdg}\n")
        self.assertEqual(profile_store.resolve_installer_config_root(self.default_root, [ai], self.environment), old_ai)
        xdg = self.source("xdg", f"XDG_CONFIG_HOME={old_xdg}\n")
        self.assertEqual(profile_store.resolve_installer_config_root(self.default_root, [xdg], self.environment), self.default_root)
        environment = {key: value for key, value in self.environment.items() if key != "XDG_CONFIG_HOME"}
        self.assertEqual(profile_store.resolve_installer_config_root(self.default_root, [xdg], environment), old_xdg / "ai-shifu")
        empty_overrides = {**environment, "AI_SHIFU_CONFIG_DIR": "  ", "XDG_CONFIG_HOME": "  "}
        self.assertEqual(profile_store.resolve_installer_config_root(self.default_root, [xdg], empty_overrides), old_xdg / "ai-shifu")

    def test_valid_pointer_is_shared_by_npm_consumers_and_unmarked_selection_is_unchanged(self):
        selected = self.directory / "custom"
        self.pointer(selected)
        self.assertEqual(profile_store.npm_config_dir(self.environment), selected)
        with mock.patch.dict(os.environ, self.environment, clear=True):
            self.assertEqual(profile_store.config_dir(), self.default_root)

    def test_invalid_pointer_cannot_silently_select_another_root(self):
        self.default_root.mkdir(parents=True)
        invalid = ["[]", "not json", {"schema_version": True, "config_dir": str(self.directory)},
                   {"schema_version": 1, "config_dir": "relative"},
                   {"schema_version": 1, "config_dir": str(self.directory), "extra": True}]
        for document in invalid:
            with self.subTest(document=document):
                (self.default_root / "cli-config-root.json").write_text(
                    document if isinstance(document, str) else json.dumps(document), encoding="utf-8")
                with self.assertRaises(profile_store.ProfileFormatError):
                    profile_store.npm_config_dir(self.environment)

    def test_root_conflicts_leave_account_selection_and_source_files_unchanged(self):
        selected = self.directory / "old-root"
        source = self.source("old", f"AI_SHIFU_CONFIG_DIR={selected}\n")
        original = (source / ".env").read_bytes()
        store = profile_store.ProfileStore(self.default_root, self.default_root / "cli.env")
        store.set_profile("current", "cn")
        before = store.settings_path.read_bytes()
        with self.assertRaisesRegex(profile_store.ProfileError, "already has an account"):
            profile_store.resolve_installer_config_root(self.default_root, [source], self.environment)
        self.assertEqual(store.settings_path.read_bytes(), before)
        self.assertEqual((source / ".env").read_bytes(), original)
        self.assertFalse((self.default_root / "cli-config-root.json").exists())
        self.assertFalse(selected.exists())

    def test_different_custom_roots_and_an_existing_pointer_are_ambiguous(self):
        first = self.source("first", f"AI_SHIFU_CONFIG_DIR={self.directory / 'first-root'}\n")
        second = self.source("second", f"AI_SHIFU_CONFIG_DIR={self.directory / 'second-root'}\n")
        with self.assertRaisesRegex(profile_store.ProfileError, "different configuration roots"):
            profile_store.resolve_installer_config_root(self.default_root, [first, second], self.environment)
        self.pointer(self.directory / "first-root")
        before = (self.default_root / "cli-config-root.json").read_bytes()
        with self.assertRaisesRegex(profile_store.ProfileError, "differs from the existing npm root"):
            profile_store.resolve_installer_config_root(self.default_root, [second], self.environment)
        self.assertEqual((self.default_root / "cli-config-root.json").read_bytes(), before)

    def test_existing_environment_preference_prevents_switching_roots(self):
        self.default_root.mkdir(parents=True)
        (self.default_root / "cli.env").write_text("SHIFU_DISABLE_ANALYTICS=1\n", encoding="utf-8")
        source = self.source("old", f"AI_SHIFU_CONFIG_DIR={self.directory / 'custom'}\n")
        with self.assertRaisesRegex(profile_store.ProfileError, "user settings"):
            profile_store.resolve_installer_config_root(self.default_root, [source], self.environment)

    def test_import_records_custom_root_after_success_and_keeps_existing_account_in_place(self):
        selected = self.directory / "custom-root"
        store = profile_store.ProfileStore(selected, selected / "cli.env")
        context = store.set_profile("teaching", "cn")
        store.save_token(context, "original-account-token")
        credentials = profile_store.credentials_path(context)
        before = credentials.read_bytes()
        source = self.source("old", f"AI_SHIFU_CONFIG_DIR={selected}\nSHIFU_DISABLE_ANALYTICS=1\n")
        original = (source / ".env").read_bytes()
        result = subprocess.run([
            sys.executable, str(REPOSITORY / "cli/migrate-config.py"), str(self.default_root),
            str(SCRIPT_DIR.parent / ".env.example"), str(source),
        ], env=self.environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["config_dir"], str(selected))
        self.assertEqual(profile_store.npm_config_dir(self.environment), selected)
        recovered = profile_store.ProfileStore(selected, selected / "cli.env").resolve(environ={})
        self.assertEqual((recovered.name, recovered.base_url, recovered.token),
                         ("teaching", profile_store.SITE_URLS["cn"], "original-account-token"))
        self.assertEqual(credentials.read_bytes(), before)
        self.assertFalse((self.default_root / "profiles").exists())
        self.assertEqual((source / ".env").read_bytes(), original)
        pointer = self.default_root / "cli-config-root.json"
        if os.name != "nt":
            self.assertEqual(pointer.stat().st_mode & 0o777, 0o600)

        # A synchronized Skill can still reach that same account when npm's
        # executable is absent and the agent uses its Python fallback.
        skill = self.directory / "synchronized-skill"
        shutil.copytree(SCRIPT_DIR, skill / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        (skill / "SKILL.md").write_text(
            "---\nname: ai-shifu-course-creator\nmetadata:\n  version: 2.2.1\n"
            "  version_management: standalone\n---\n", encoding="utf-8")
        (skill / ".ai-shifu-cli.json").write_text(json.dumps({
            "schema_version": 1, "distribution": "npm", "version": "2.2.1",
        }), encoding="utf-8")
        script = """import importlib.util, json, sys
from pathlib import Path
entry = Path(sys.argv[1]); sys.path.insert(0, str(entry.parent))
spec = importlib.util.spec_from_file_location('fallback_cli', entry)
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
print(json.dumps({'root': str(cli.config_dir()), 'profiles': cli.profile_store().list_profiles()}))
"""
        fallback = subprocess.run([sys.executable, "-c", script, str(skill / "scripts/shifu-cli.py")],
                                  env=self.environment, capture_output=True, text=True)
        self.assertEqual(fallback.returncode, 0, fallback.stderr)
        observed = json.loads(fallback.stdout)
        self.assertEqual(observed["root"], str(selected))
        self.assertEqual(observed["profiles"], [{
            "name": "teaching", "base_url": profile_store.SITE_URLS["cn"],
            "default": True, "credentials_present": True,
        }])

    def test_legacy_xdg_root_preserves_the_existing_profile_directory(self):
        selected = self.directory / "legacy-xdg" / "ai-shifu"
        store = profile_store.ProfileStore(selected, selected / "cli.env")
        store.set_profile("international", "com")
        source = self.source("xdg-source", f"XDG_CONFIG_HOME={selected.parent}\n")
        environment = {key: value for key, value in self.environment.items() if key != "XDG_CONFIG_HOME"}
        result = subprocess.run([
            sys.executable, str(REPOSITORY / "cli/migrate-config.py"), str(self.default_root),
            str(SCRIPT_DIR.parent / ".env.example"), str(source),
        ], env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(profile_store.npm_config_dir(environment), selected)
        self.assertEqual(store.default_profile(), "international")
        self.assertFalse((self.default_root / "profiles").exists())


if __name__ == "__main__":
    unittest.main()
