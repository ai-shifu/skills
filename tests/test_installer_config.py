"""Installer configuration and profile changes form one private transaction."""

from __future__ import annotations

import json
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "ai-shifu-course-creator" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import profile_store
from profile_store import ProfileError, ProfileStore, read_private_json, write_private_json


class InstallerConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Older transport-only test modules can install a process-wide dotenv
        # stub. Load this integration dependency independently of sys.modules.
        specification = importlib.machinery.PathFinder.find_spec("dotenv")
        if specification is None or specification.origin is None:
            raise unittest.SkipTest("Installer integration tests require python-dotenv")
        alias = "_installer_test_dotenv"
        actual = importlib.util.spec_from_file_location(
            alias, specification.origin,
            submodule_search_locations=specification.submodule_search_locations,
        )
        module = importlib.util.module_from_spec(actual)
        sys.modules[alias] = module
        actual.loader.exec_module(module)
        cls.dotenv = module

    def setUp(self):
        self.enterContext(mock.patch.object(profile_store, "dotenv_values", self.dotenv.dotenv_values))
        self.enterContext(mock.patch.object(profile_store, "set_key", self.dotenv.set_key))
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.root = self.directory / "configuration"
        self.environment_file = self.root / "cli.env"
        self.template = self.directory / "template.env"
        self.template.write_text("# Defaults\nSHIFU_BASE_URL=\nSHIFU_TOKEN=\nSHIFU_DISABLE_ANALYTICS=\n", encoding="utf-8")
        self.store = ProfileStore(self.root, self.environment_file)

    def source(self, name, content):
        directory = self.directory / name
        directory.mkdir()
        (directory / ".env").write_bytes(content.encode("utf-8"))
        return directory

    def imported(self, directories):
        return self.store.import_installer_configuration(directories, self.template)

    def backups(self):
        return sorted((self.root / "legacy-env").glob("*.env"))

    def test_semantic_duplicates_ignore_comments_quoting_order_and_empty_template(self):
        first = self.source("first", "# First\nSHIFU_BASE_URL='cn'\nSHIFU_TOKEN='selected-token'\nSHIFU_DISABLE_ANALYTICS=1\n")
        second = self.source("second", "SHIFU_DISABLE_ANALYTICS = 1\r\nSHIFU_TOKEN=selected-token\r\n# Another\r\nSHIFU_BASE_URL=cn\r\n")
        empty = self.source("empty", "# Formatted defaults\nSHIFU_TOKEN = ''\nSHIFU_BASE_URL = \"\"\n")
        originals = [(source / ".env").read_bytes() for source in (first, second, empty)]
        result = self.imported([first, second, empty])
        self.assertEqual(result, {"status": "imported", "imported_profiles": ["default"]})
        context = self.store.resolve(environ={})
        self.assertEqual(context.base_url, profile_store.SITE_URLS["cn"])
        self.assertEqual(context.token, "selected-token")
        self.assertEqual(self.store._env_values()["SHIFU_DISABLE_ANALYTICS"], "1")
        self.assertEqual([(source / ".env").read_bytes() for source in (first, second, empty)], originals)
        self.assertEqual(len(self.backups()), 3)
        self.assertTrue(all("selected-token" not in backup.read_text() for backup in self.backups()))
        self.assertNotIn("selected-token", json.dumps(result))

    def test_real_conflict_backs_up_all_originals_without_selecting_or_deleting(self):
        first = self.source("first", "SHIFU_DISABLE_ANALYTICS=1\n")
        second = self.source("second", "SHIFU_DISABLE_ANALYTICS=0\n")
        with self.assertRaisesRegex(ProfileError, "Different legacy configurations"):
            self.imported([first, second])
        self.assertEqual(len(self.backups()), 2)
        self.assertFalse(self.environment_file.exists())
        self.assertFalse(self.store.settings_path.exists())
        self.assertEqual((first / ".env").read_text(), "SHIFU_DISABLE_ANALYTICS=1\n")
        self.assertEqual((second / ".env").read_text(), "SHIFU_DISABLE_ANALYTICS=0\n")

    def test_empty_configurations_do_not_conflict_or_create_a_profile(self):
        sources = [self.source("empty", ""), self.source("default", self.template.read_text())]
        self.assertEqual(self.imported(sources), {"status": "unchanged", "imported_profiles": []})
        self.assertFalse(self.environment_file.exists())
        self.assertFalse(self.store.settings_path.exists())

    def test_existing_edited_configuration_is_preserved_byte_for_byte(self):
        self.root.mkdir()
        current = b"# Selected by user\nSHIFU_DISABLE_ANALYTICS=0\nUSER_SETTING=selected\n"
        self.environment_file.write_bytes(current)
        source = self.source("legacy", "SHIFU_DISABLE_ANALYTICS=1\n")
        self.assertEqual(self.imported([source]), {"status": "preserved", "imported_profiles": []})
        self.assertEqual(self.environment_file.read_bytes(), current)

    def test_selected_options_without_profiles_still_preserve_the_unique_incoming_account(self):
        self.root.mkdir()
        current = b"# Keep my opt-out\nSHIFU_DISABLE_ANALYTICS=1\n"
        self.environment_file.write_bytes(current)
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=selected-token\nSHIFU_DISABLE_ANALYTICS=0\n")
        original_source = (source / ".env").read_bytes()
        result = self.imported([source])
        self.assertEqual(result["status"], "imported")
        self.assertEqual(len(result["imported_profiles"]), 1)
        context = self.store.resolve(result["imported_profiles"][0], environ={})
        self.assertEqual(context.base_url, profile_store.SITE_URLS["cn"])
        self.assertEqual(context.token, "selected-token")
        self.assertEqual(self.environment_file.read_bytes(), current)
        self.assertEqual(self.store._env_values()["SHIFU_DISABLE_ANALYTICS"], "1")
        self.assertEqual((source / ".env").read_bytes(), original_source)
        self.assertTrue(all("selected-token" not in backup.read_text() for backup in self.backups()))

    def test_selected_cli_account_stays_default_when_importing_a_different_source(self):
        self.root.mkdir()
        self.environment_file.write_text(
            "# Keep my selection\nSHIFU_BASE_URL=com\nSHIFU_TOKEN=chosen-token\nSHIFU_DISABLE_ANALYTICS=1\n",
            encoding="utf-8",
        )
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=incoming-token\nSHIFU_DISABLE_ANALYTICS=0\n")
        result = self.imported([source])
        default = self.store.resolve(environ=self.store._env_values())
        self.assertEqual((default.name, default.base_url, default.token),
                         ("default", profile_store.SITE_URLS["com"], "chosen-token"))
        incoming = self.store.resolve(result["imported_profiles"][0], environ={})
        self.assertNotEqual(incoming.name, default.name)
        self.assertEqual((incoming.base_url, incoming.token), (profile_store.SITE_URLS["cn"], "incoming-token"))
        self.assertEqual(self.store._env_values()["SHIFU_DISABLE_ANALYTICS"], "1")
        self.assertIn("# Keep my selection", self.environment_file.read_text())
        self.assertEqual(self.store._env_values().get("SHIFU_BASE_URL"), "")
        self.assertEqual(self.store._env_values().get("SHIFU_TOKEN"), "")
        self.store.logout(default)
        logged_out = self.store.resolve(environ=self.store._env_values())
        self.assertEqual((logged_out.name, logged_out.token), (default.name, ""))
        self.assertEqual(self.store.load_token(incoming), "incoming-token")

    def test_unresolved_selected_cli_credentials_stop_without_guessing(self):
        self.root.mkdir()
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=incoming-token\n")
        for selected in ("SHIFU_TOKEN=unscoped-token\n", "SHIFU_BASE_URL=${SERVICE}\nSHIFU_TOKEN=token\n",
                         "SHIFU_BASE_URL=com\nSHIFU_TOKEN=${TOKEN}\n"):
            with self.subTest(selected=selected):
                self.environment_file.write_text(selected, encoding="utf-8")
                with self.assertRaisesRegex(ProfileError, "Selected CLI credentials need an explicit service URL"):
                    self.imported([source])
                self.assertEqual(self.environment_file.read_text(), selected)
                self.assertFalse(self.store.settings_path.exists())
                self.assertEqual((source / ".env").read_text(), "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=incoming-token\n")

    def test_selected_options_with_legacy_saved_settings_preserve_the_original_default(self):
        self.root.mkdir()
        current = b"SHIFU_DISABLE_ANALYTICS=1\n"
        self.environment_file.write_bytes(current)
        write_private_json(self.store.settings_path, {"base_url": profile_store.SITE_URLS["com"]})
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=selected-token\n")
        result = self.imported([source])
        self.assertEqual(self.environment_file.read_bytes(), current)
        self.assertEqual(self.store.resolve(environ={}).base_url, profile_store.SITE_URLS["com"])
        incoming = self.store.resolve(result["imported_profiles"][0], environ={})
        self.assertEqual((incoming.base_url, incoming.token), (profile_store.SITE_URLS["cn"], "selected-token"))
        self.assertEqual((source / ".env").read_text(), "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=selected-token\n")
        self.assertTrue(all("selected-token" not in backup.read_text() for backup in self.backups()))

    def test_original_unscoped_token_is_bound_only_to_its_saved_service(self):
        for index, (incoming_url, with_template) in enumerate((
            ("cn", False), ("cn", True), ("https://custom.example/teach", False), ("https://custom.example/teach", True),
        )):
            with self.subTest(incoming=incoming_url, template=with_template):
                root = self.directory / f"saved-account-{index}"
                store = ProfileStore(root, root / "cli.env")
                write_private_json(store.settings_path, {"base_url": profile_store.SITE_URLS["com"]})
                write_private_json(root / "credentials.json", {"token": "com-only-token"})
                if with_template:
                    store.env_file.write_bytes(self.template.read_bytes())
                source = self.source(f"incoming-{index}", f"SHIFU_BASE_URL={incoming_url}\n")
                result = store.import_installer_configuration([source], self.template)
                original = store.resolve(environ={})
                incoming = store.resolve(result["imported_profiles"][0], environ={})
                self.assertEqual((original.name, original.base_url, original.token),
                                 ("default", profile_store.SITE_URLS["com"], "com-only-token"))
                self.assertEqual(incoming.base_url, profile_store.normalize_base_url(incoming_url))
                self.assertEqual(incoming.token, "")
                self.assertFalse(store.credentials_path(incoming).exists())
                self.assertFalse((root / "credentials.json").exists())
                self.assertEqual(store.default_profile(), original.name)
                self.assertEqual(store.resolve(environ=store._env_values()).name, original.name)

    def test_selected_preferences_preserve_original_credentials_and_pending_without_settings(self):
        self.root.mkdir()
        current = b"# Keep opt-out\nSHIFU_DISABLE_ANALYTICS=1\n"
        self.environment_file.write_bytes(current)
        write_private_json(self.root / "credentials.json", {"base_url": profile_store.SITE_URLS["com"], "token": "original-token"})
        pending = {"base_url": profile_store.SITE_URLS["com"], "device_code": "original-request", "expires_at": 123}
        write_private_json(self.root / "pending-device-auth.json", pending)
        source = self.source("incoming", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=incoming-token\n")
        result = self.imported([source])
        original = self.store.resolve(environ={})
        incoming = self.store.resolve(result["imported_profiles"][0], environ={})
        self.assertEqual((original.name, original.base_url, original.token),
                         ("default", profile_store.SITE_URLS["com"], "original-token"))
        self.assertEqual(read_private_json(self.store.pending_auth_path(original)), pending)
        self.assertEqual((incoming.base_url, incoming.token), (profile_store.SITE_URLS["cn"], "incoming-token"))
        self.assertFalse(self.store.pending_auth_path(incoming).exists())
        self.assertEqual(self.environment_file.read_bytes(), current)
        self.store.logout(original)
        self.assertFalse(self.store.credentials_path(original).exists())
        self.assertFalse(self.store.pending_auth_path(original).exists())
        self.assertEqual(self.store.resolve(environ=self.store._env_values()).name, "default")
        self.assertEqual(self.store.load_token(incoming), "incoming-token")

    def test_unknown_origin_root_authorization_cannot_borrow_the_incoming_url(self):
        self.root.mkdir()
        current = b"SHIFU_DISABLE_ANALYTICS=1\n"
        self.environment_file.write_bytes(current)
        old_credentials = {"token": "unknown-origin-token"}
        write_private_json(self.root / "credentials.json", old_credentials)
        source = self.source("incoming", "SHIFU_BASE_URL=https://custom.example\n")
        with self.assertRaisesRegex(ProfileError, "original service"):
            self.imported([source])
        self.assertEqual(read_private_json(self.root / "credentials.json"), old_credentials)
        self.assertEqual(self.environment_file.read_bytes(), current)
        self.assertFalse(self.store.settings_path.exists())
        self.assertEqual((source / ".env").read_text(), "SHIFU_BASE_URL=https://custom.example\n")

    def test_preflight_cleanup_keeps_the_existing_selection_across_conflicting_sources(self):
        self.root.mkdir()
        self.environment_file.write_text("SHIFU_BASE_URL=com\nSHIFU_TOKEN=selected-token\n", encoding="utf-8")
        sources = [self.source("first", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=first-token\n"),
                   self.source("second", "SHIFU_BASE_URL=https://custom.example\nSHIFU_TOKEN=second-token\n")]
        for _ in range(2):
            self.assertEqual(self.imported(sources), {"status": "preserved", "imported_profiles": []})
            context = self.store.resolve(environ=self.store._env_values())
            self.assertEqual((context.name, context.base_url, context.token),
                             ("default", profile_store.SITE_URLS["com"], "selected-token"))
            self.assertEqual(len(self.store.list_profiles()), 1)

    def test_existing_selection_preserves_default_and_credentials_across_conflicting_sources(self):
        current_profile = self.store.set_profile("current", "com")
        self.store.save_token(current_profile, "current-token")
        current = b"# Explicit selection\nSHIFU_DISABLE_ANALYTICS=0\nUSER_SETTING=selected\n"
        self.environment_file.write_bytes(current)
        settings = self.store.settings_path.read_bytes()
        sources = [self.source("first", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=first-token\n"),
                   self.source("second", "SHIFU_BASE_URL=com\nSHIFU_TOKEN=second-token\n")]
        self.assertEqual(self.imported(sources), {"status": "preserved", "imported_profiles": []})
        self.assertEqual(self.environment_file.read_bytes(), current)
        self.assertEqual(self.store.settings_path.read_bytes(), settings)
        self.assertEqual(self.store.default_profile(), "current")
        self.assertEqual(self.store.load_token(current_profile), "current-token")
        self.assertEqual(len(self.backups()), 2)

    @unittest.skipIf(os.name == "nt", "POSIX permission bits are not Windows ACLs")
    def test_replacing_a_public_template_creates_a_private_configuration(self):
        self.root.mkdir()
        self.environment_file.write_text("# Reformat\nSHIFU_BASE_URL=''\nSHIFU_TOKEN=''\n", encoding="utf-8")
        self.environment_file.chmod(0o644)
        source = self.source("legacy", "SHIFU_DISABLE_ANALYTICS=1\n")
        self.imported([source])
        self.assertEqual(self.environment_file.stat().st_mode & 0o777, 0o600)
        self.assertTrue(all(backup.stat().st_mode & 0o777 == 0o600 for backup in self.backups()))

    def test_existing_profile_default_and_edited_environment_are_preserved(self):
        existing = self.store.set_profile("current-account", "com")
        self.store.save_token(existing, "current-token")
        current = b"SHIFU_DISABLE_ANALYTICS=0\nUSER_SETTING=selected\n"
        self.environment_file.write_bytes(current)
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=imported-token\nSHIFU_DISABLE_ANALYTICS=1\n")
        result = self.imported([source])
        name = result["imported_profiles"][0]
        self.assertNotEqual(name, "current-account")
        self.assertEqual(self.store.default_profile(), "current-account")
        self.assertEqual(self.store.resolve(environ={}).token, "current-token")
        self.assertEqual(self.store.resolve(name, environ={}).token, "imported-token")
        self.assertEqual(self.environment_file.read_bytes(), current)
        self.assertTrue(all("imported-token" not in backup.read_text() for backup in self.backups()))

    def test_existing_profiles_receive_no_active_dotenv_credentials(self):
        existing = self.store.set_profile("current", "com")
        self.store.save_token(existing, "current-token")
        self.environment_file.write_bytes(self.template.read_bytes())
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=imported-token\nSHIFU_DISABLE_ANALYTICS=1\n")
        result = self.imported([source])
        effective = self.store._env_values()
        self.assertEqual(effective.get("SHIFU_BASE_URL"), "")
        self.assertEqual(effective.get("SHIFU_TOKEN"), "")
        self.assertEqual(effective["SHIFU_DISABLE_ANALYTICS"], "1")
        self.assertEqual(self.store.resolve(environ=effective).name, "current")
        self.assertEqual(self.store.resolve(result["imported_profiles"][0], environ={}).token, "imported-token")

    def test_matching_existing_profile_is_reused_without_changing_default(self):
        current = self.store.set_profile("current", "com")
        matching = self.store.set_profile("matching", "cn")
        self.store.save_token(matching, "shared-token")
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=shared-token\n")
        result = self.imported([source])
        self.assertEqual(result["imported_profiles"], ["matching"])
        self.assertEqual(self.store.default_profile(), current.name)
        self.assertEqual(len(self.store.list_profiles()), 2)

    def test_service_only_configuration_imports_an_unauthenticated_profile(self):
        self.store.set_profile("current", "com")
        source = self.source("legacy", "SHIFU_BASE_URL=cn\n")
        result = self.imported([source])
        imported = self.store.resolve(result["imported_profiles"][0], environ={})
        self.assertEqual(imported.base_url, profile_store.SITE_URLS["cn"])
        self.assertEqual(imported.token, "")
        self.assertEqual(self.store.default_profile(), "current")
        self.assertEqual(self.store._env_values().get("SHIFU_BASE_URL"), "")

    def test_failed_profile_commit_does_not_strand_new_credentials(self):
        self.store.set_profile("current", "com")
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=imported-token\n")
        original = self.store.settings_path.read_bytes()
        real_write = profile_store.write_private_json

        def fail_settings(path, value):
            if Path(path) == self.store.settings_path:
                raise OSError("settings temporarily unavailable")
            return real_write(path, value)

        with mock.patch.object(profile_store, "write_private_json", side_effect=fail_settings):
            with self.assertRaisesRegex(OSError, "temporarily unavailable"):
                self.imported([source])
        self.assertEqual(self.store.settings_path.read_bytes(), original)
        self.assertEqual(list((self.root / "profiles").glob("*/credentials.json")), [])
        self.assertEqual(self.store.default_profile(), "current")
        self.assertTrue(any("imported-token" in backup.read_text() for backup in self.backups()))
        self.imported([source])
        self.assertEqual(self.store.default_profile(), "current")

    def test_unscoped_or_interpolated_credentials_stop_before_any_configuration_change(self):
        self.store.set_profile("current", "cn")
        self.environment_file.write_bytes(self.template.read_bytes())
        settings = self.store.settings_path.read_bytes()
        for index, content in enumerate(("SHIFU_TOKEN=unknown-token\n", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=${EXPORTED_TOKEN}\n",
                                         "SHIFU_BASE_URL=${SERVICE_URL}\nSHIFU_TOKEN=unknown-token\n")):
            with self.subTest(content=content):
                source = self.source(f"legacy-{index}", content)
                with self.assertRaisesRegex(ProfileError, "explicit service URL and literal values"):
                    self.imported([source])
                self.assertEqual(self.environment_file.read_bytes(), self.template.read_bytes())
                self.assertEqual(self.store.settings_path.read_bytes(), settings)
                self.assertEqual((source / ".env").read_text(), content)
        self.assertEqual(len(self.backups()), 3)

    def test_repeat_import_after_logout_does_not_reactivate_or_restore_backup_token(self):
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=imported-token\n")
        self.imported([source])
        context = self.store.resolve(environ={})
        self.store.logout(context)
        self.assertEqual(self.store.load_token(context), "")
        self.imported([source])
        self.assertEqual(self.store.load_token(context), "")
        self.assertTrue(all("imported-token" not in backup.read_text() for backup in self.backups()))
        self.assertEqual(len(self.store.list_profiles()), 1)

    def interrupted_first_import(self, source):
        real_write = profile_store.write_private_json

        def fail_settings(path, value):
            if Path(path) == self.store.settings_path:
                raise OSError("first settings commit interrupted")
            return real_write(path, value)

        with mock.patch.object(profile_store, "write_private_json", side_effect=fail_settings):
            with self.assertRaisesRegex(OSError, "settings commit interrupted"):
                self.imported([source])
        self.assertTrue(self.store.migration_path.exists())

    def test_ordinary_migration_recovery_preserves_installer_receipt_after_logout(self):
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=imported-token\n")
        self.interrupted_first_import(source)
        journal = read_private_json(self.store.migration_path)
        self.assertIn("installer_identity", journal)
        self.store.migrate_legacy()
        context = self.store.resolve(environ={})
        receipts = read_private_json(self.store.settings_path)["installer_imports"]
        self.assertEqual(receipts[journal["installer_identity"]], context.directory.name)
        self.store.logout(context)
        self.imported([source])
        reformatted = self.source("reformatted", "# Same account\nSHIFU_TOKEN='imported-token'\nSHIFU_BASE_URL='cn'\n")
        self.imported([reformatted])
        self.assertEqual(self.store.load_token(context), "")
        self.assertEqual(self.store.default_profile(), context.name)
        self.assertEqual(len(self.store.list_profiles()), 1)
        self.assertTrue(all("imported-token" not in backup.read_text() for backup in self.backups()))

    def test_installer_finishes_pending_migration_before_preserving_a_selected_configuration(self):
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=imported-token\nSHIFU_DISABLE_ANALYTICS=1\n")
        self.interrupted_first_import(source)
        second = self.source("second", "SHIFU_BASE_URL=com\nSHIFU_TOKEN=other-token\n")
        result = self.imported([source, second])
        self.assertEqual(result, {"status": "preserved", "imported_profiles": []})
        self.assertFalse(self.store.migration_path.exists())
        self.assertEqual(self.store.resolve(environ={}).token, "imported-token")
        self.assertEqual(self.store._env_values()["SHIFU_DISABLE_ANALYTICS"], "1")
        self.assertTrue(read_private_json(self.store.settings_path)["installer_imports"])

    def test_receipt_also_preserves_logout_when_a_matching_named_profile_was_reused(self):
        current = self.store.set_profile("named", "cn")
        self.store.save_token(current, "imported-token")
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=imported-token\n")
        self.imported([source])
        self.store.logout(current)
        reformatted = self.source("reformatted", "# Same account\nSHIFU_TOKEN='imported-token'\nSHIFU_BASE_URL='cn'\n")
        self.imported([reformatted])
        self.assertEqual(self.store.load_token(current), "")
        self.assertEqual(len(self.store.list_profiles()), 1)
        self.assertTrue(all("imported-token" not in backup.read_text() for backup in self.backups()))

    def test_consumed_receipt_allows_a_later_service_change_without_replaying_credentials(self):
        self.store.set_profile("current", "com")
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=imported-token\n")
        first = self.imported([source])
        name = first["imported_profiles"][0]
        context = self.store.resolve(name, environ={})
        self.store.logout(context)
        updated = self.store.set_profile(name, "https://moved.example/teach")
        result = self.imported([source])
        self.assertEqual(result["imported_profiles"], [name])
        self.assertEqual(self.store.resolve(name, environ={}).base_url, updated.base_url)
        self.assertEqual(self.store.load_token(updated), "")
        self.assertEqual(self.store.default_profile(), "current")
        self.assertEqual(len(self.store.list_profiles()), 2)
        self.assertTrue(all("imported-token" not in backup.read_text() for backup in self.backups()))

    def test_invalid_receipt_shapes_fail_closed(self):
        current = self.store.set_profile("current", "cn")
        original = read_private_json(self.store.settings_path)
        source = self.source("legacy", "SHIFU_DISABLE_ANALYTICS=1\n")
        for receipts in ([], None, {"not-a-digest": current.directory.name}, {"a" * 64: {}}, {"a" * 64: "missing-profile"}):
            with self.subTest(receipts=receipts):
                write_private_json(self.store.settings_path, {**original, "installer_imports": receipts})
                with self.assertRaisesRegex(ProfileError, "Invalid installer"):
                    self.imported([source])
                self.assertFalse(self.environment_file.exists())

    def test_import_and_logout_wait_for_the_same_configuration_lock(self):
        current = self.store.set_profile("current", "cn")
        self.store.save_token(current, "imported-token")
        source = self.source("legacy", "SHIFU_BASE_URL=cn\nSHIFU_TOKEN=imported-token\n")
        self.imported([source])
        script = """import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from profile_store import ProfileStore
store = ProfileStore(sys.argv[2], sys.argv[3])
Path(sys.argv[7]).write_text('ready')
if sys.argv[4] == 'import':
    store.import_installer_configuration([sys.argv[5]], sys.argv[6])
else:
    store.logout(store.resolve('current', environ={}))
"""
        children = []
        with self.store._configuration_lock():
            for operation in ("import", "logout"):
                ready = self.directory / (operation + ".ready")
                child = subprocess.Popen([sys.executable, "-c", script, str(SCRIPT_DIR), str(self.root),
                                          str(self.environment_file), operation, str(source), str(self.template), str(ready)],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                children.append(child)
                deadline = time.monotonic() + 10
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists(), operation)
                self.assertIsNone(child.poll(), operation + " must wait on the profile lock")
        for child in children:
            stdout, stderr = child.communicate(timeout=15)
            self.assertEqual(child.returncode, 0, stdout + stderr)
        self.assertEqual(self.store.load_token(current), "")
        self.assertTrue(all("imported-token" not in backup.read_text() for backup in self.backups()))


if __name__ == "__main__":
    unittest.main()
