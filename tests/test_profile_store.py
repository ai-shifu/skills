"""Transport-free tests for profile identity, credentials, and legacy migration."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "ai-shifu-course-creator" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
try:
    import dotenv  # noqa: F401
except ImportError:
    stub = types.ModuleType("dotenv")
    stub.dotenv_values = lambda *_args, **_kwargs: {}
    stub.set_key = lambda *_args, **_kwargs: None
    sys.modules["dotenv"] = stub

import profile_store
from profile_store import ProfileContext, ProfileError, ProfileStore, read_private_json, write_private_json


class ProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.directory / "configuration"
        self.env_file = self.directory / ".env"
        self.store = ProfileStore(self.root, self.env_file)
        # CLI unit tests install a dotenv stub. Keep fixtures deterministic in
        # both standalone and discovery runs without requiring extra packages.
        self.enterContext(mock.patch.object(profile_store, "dotenv_values", self.read_env))
        self.enterContext(mock.patch.object(profile_store, "set_key", self.set_env_key))

    @staticmethod
    def read_env(path, **_kwargs):
        return {key.strip(): value.strip().strip("'\"")
                for line in Path(path).read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#") and "=" in line
                for key, value in [line.split("=", 1)]}

    @staticmethod
    def set_env_key(path, key, value):
        path = Path(path)
        lines = path.read_text().splitlines()
        path.write_text("\n".join(f"{key}='{value}'" if line.startswith(key + "=") else line
                                  for line in lines) + "\n")

    def legacy(self, url=None, token=None, pending=None):
        if url is not None:
            write_private_json(self.root / "settings.json", {"base_url": url})
        if token is not None:
            write_private_json(self.root / "credentials.json", {"token": token})
        if pending is not None:
            write_private_json(self.root / "pending-device-auth.json", pending)

    def test_names_are_arbitrary_and_directories_are_opaque(self):
        first = self.store.set_profile("  日常 工作  ", "CN")
        second = self.store.set_profile("../客户A/演示", "com")
        self.assertEqual(first.name, "日常 工作")
        self.assertEqual(first.directory.parent, self.root / "profiles")
        self.assertNotIn("客户", str(second.directory))
        self.assertNotEqual(first.directory, second.directory)
        self.assertEqual(self.store.default_profile(), "日常 工作")
        self.assertEqual(self.store.resolve("../客户A/演示", environ={}), second)
        self.assertEqual(self.store.resolve(environ={}), first)

    def test_case_sensitive_names_and_invalid_names(self):
        self.store.set_profile("Demo", "cn")
        self.store.set_profile("demo", "cn")
        self.assertEqual(len(self.store.list_profiles()), 2)
        for name in ("", "   ", "a\nb", "a\x00", "ends\n", "a\u200bb"):
            with self.subTest(name=name), self.assertRaises(ProfileError):
                self.store.set_profile(name, "cn")

    def test_default_changes_only_when_explicitly_requested(self):
        self.store.set_profile("one", "cn")
        self.store.set_profile("two", "com")
        self.store.resolve("two", environ={})
        self.assertEqual(self.store.default_profile(), "one")
        self.assertEqual(self.store.default_profile("two"), "two")
        self.assertEqual(self.store.resolve(environ={}).name, "two")
        with self.assertRaises(ProfileError):
            self.store.resolve("missing", environ={})
        self.assertEqual(self.store.default_profile(), "two")

    def test_aliases_and_full_urls_normalize_equally(self):
        for alias, url in profile_store.SITE_URLS.items():
            self.assertEqual(profile_store.normalize_base_url(alias.upper()), url)
            self.assertEqual(profile_store.normalize_base_url(url + "/"), url)
        self.assertEqual(profile_store.normalize_base_url(" https://EXAMPLE.com:443/Learn/ "),
                         "https://example.com/Learn")
        self.assertEqual(profile_store.normalize_base_url("https://example.com:8443/v1/"),
                         "https://example.com:8443/v1")
        self.assertEqual(profile_store.normalize_base_url("http://[::1]:8000/dev/"),
                         "http://[::1]:8000/dev")
        self.assertEqual(profile_store.normalize_base_url("http://localhost:80"), "http://localhost")

    def test_invalid_urls_never_write_configuration(self):
        for url in ("example.com", "ftp://example.com", "http://example.com", "https://a:0", "https://a:99999",
                    "https://user:pass@example.com", "https://a/?", "https://a/#", "https://a/white space",
                    "https://a\\b", "https://a/\x00", "https://[invalid]"):
            with self.subTest(url=url), self.assertRaises(ProfileError):
                self.store.set_profile("invalid", url)
        self.assertFalse(self.store.settings_path.exists())

    def test_independent_credentials_pending_and_logout(self):
        first = self.store.set_profile("甲", "cn")
        second = self.store.set_profile("乙", "com")
        for context, token in ((first, "first-token"), (second, "second-token")):
            self.store.save_token(context, token)
            write_private_json(self.store.pending_auth_path(context), {
                "base_url": context.base_url, "device_code": context.name,
            })
        self.assertEqual(self.store.resolve("甲", environ={}).token, "first-token")
        self.assertEqual(self.store.resolve("乙", environ={}).token, "second-token")
        self.store.logout(first)
        self.assertFalse(self.store.credentials_path(first).exists())
        self.assertFalse(self.store.pending_auth_path(first).exists())
        self.assertEqual(self.store.load_token(second), "second-token")
        self.assertTrue(self.store.pending_auth_path(second).exists())
        self.assertEqual(self.store.default_profile(), "甲")

    def test_same_service_has_independent_accounts(self):
        first = self.store.set_profile("personal", "cn")
        second = self.store.set_profile("business", "cn")
        self.store.save_token(first, "personal-token")
        self.store.save_token(second, "business-token")
        self.assertEqual(self.store.resolve("personal", environ={}).token, "personal-token")
        self.assertEqual(self.store.resolve("business", environ={}).token, "business-token")

    def test_changed_url_requires_logout_but_equivalent_url_is_safe(self):
        context = self.store.set_profile("one", "cn")
        self.store.save_token(context, "token")
        self.store.set_profile("one", "https://APP.AI-SHIFU.CN:443/")
        self.assertEqual(self.store.load_token(context), "token")
        with self.assertRaises(ProfileError):
            self.store.set_profile("one", "com")
        self.store.logout(context)
        write_private_json(self.store.pending_auth_path(context), {"base_url": context.base_url})
        with self.assertRaises(ProfileError):
            self.store.set_profile("one", "com")
        self.store.logout(context)
        self.assertEqual(self.store.set_profile("one", "com").directory, context.directory)

    def test_explicit_profile_ignores_even_incomplete_environment(self):
        context = self.store.set_profile("saved", "cn")
        self.store.save_token(context, "saved-token")
        for env in ({"SHIFU_BASE_URL": "com"}, {"SHIFU_TOKEN": "exported"},
                    {"SHIFU_BASE_URL": "com", "SHIFU_TOKEN": "exported"}):
            result = self.store.resolve("saved", environ=env)
            self.assertEqual(result.base_url, profile_store.SITE_URLS["cn"])
            self.assertEqual(result.token, "saved-token")
        self.assertEqual(self.store.resolve("saved", environ=env, token="explicit").token, "explicit")
        self.assertEqual(self.store.load_token(context), "saved-token")

    def test_temporary_environment_never_reads_or_writes_saved_tokens(self):
        saved = self.store.set_profile("saved", "cn")
        self.store.save_token(saved, "saved-token")
        env = {"SHIFU_BASE_URL": "com", "SHIFU_TOKEN": "temporary"}
        result = self.store.resolve(environ=env)
        self.assertEqual(result, ProfileContext(None, profile_store.SITE_URLS["com"], None, "temporary"))
        self.assertEqual(self.store.resolve(environ=env, token="override").token, "override")
        self.assertEqual(self.store.resolve(environ={"SHIFU_BASE_URL": "com"}, token="argument").token, "argument")
        self.assertEqual(self.store.resolve(environ={}).token, "saved-token")
        for action in (self.store.credentials_path, self.store.pending_auth_path):
            with self.assertRaises(ProfileError):
                action(result)
        with self.assertRaises(ProfileError):
            self.store.resolve(environ=env, named_only=True)

    def test_partial_temporary_environment_never_falls_back(self):
        saved = self.store.set_profile("saved", "cn")
        self.store.save_token(saved, "saved-token")
        for env in ({"SHIFU_BASE_URL": "com"}, {"SHIFU_TOKEN": "temporary"}):
            with self.subTest(env=env), self.assertRaises(ProfileError):
                self.store.resolve(environ=env)

    def test_metadata_never_discloses_tokens_or_verifies_login(self):
        context = self.store.set_profile("saved", "cn")
        self.store.save_token(context, "secret-token")
        listing = self.store.list_profiles()
        self.assertEqual(listing, [{"name": "saved", "base_url": context.base_url,
                                    "default": True, "credentials_present": True}])
        self.assertNotIn("secret-token", repr(self.store.resolve(environ={})))

    def test_bad_credentials_fail_closed_but_can_be_logged_out(self):
        context = self.store.set_profile("saved", "cn")
        for data in ({"base_url": profile_store.SITE_URLS["com"], "token": "wrong-host"},
                     {"token": "unscoped"}, {"base_url": context.base_url, "token": ""}):
            write_private_json(self.store.credentials_path(context), data)
            with self.assertRaises(ProfileError):
                self.store.resolve(environ={})
            metadata = self.store.resolve(environ={}, load_credentials=False)
            self.store.logout(metadata)
            self.assertFalse(self.store.credentials_path(context).exists())

    def test_corrupt_configuration_does_not_fall_back_to_environment(self):
        self.root.mkdir()
        self.store.settings_path.write_text("{broken")
        with self.assertRaises(ProfileError):
            self.store.resolve(environ={"SHIFU_BASE_URL": "com", "SHIFU_TOKEN": "token"})
        self.assertEqual(self.store.settings_path.read_text(), "{broken")

    def test_unsafe_duplicate_ids_and_invalid_defaults_are_rejected(self):
        self.store.set_profile("one", "cn")
        good = read_private_json(self.store.settings_path)
        for mutate in (lambda data: data["profiles"]["one"].update(id="../../other"),
                       lambda data: data["profiles"].update(two=dict(data["profiles"]["one"])),
                       lambda data: data.update(default_profile="missing"),
                       lambda data: data.update(schema_version=99)):
            data = json.loads(json.dumps(good))
            mutate(data)
            write_private_json(self.store.settings_path, data)
            with self.assertRaises(ProfileError):
                self.store.list_profiles()

    def test_unconfigured_can_be_inspected_without_creating_files(self):
        self.assertIsNone(self.store.resolve(environ={}, allow_unconfigured=True))
        self.assertEqual(self.store.list_profiles(), [])
        self.assertIsNone(self.store.default_profile())
        self.assertFalse(self.root.exists())

    def test_legacy_saved_configuration_migrates_credential_and_pending_together(self):
        self.legacy("https://app.ai-shifu.com/", "old-token", {
            "base_url": "https://app.ai-shifu.com/", "device_code": "pending-code", "expires_at": 123,
        })
        environment = {"SHIFU_BASE_URL": "cn", "SHIFU_TOKEN": "process-token"}
        self.store.migrate_legacy(environment)
        context = self.store.resolve(environ={})
        self.assertEqual((context.name, context.base_url, context.token),
                         ("default", profile_store.SITE_URLS["com"], "old-token"))
        self.assertEqual(read_private_json(self.store.pending_auth_path(context))["device_code"], "pending-code")
        self.assertFalse((self.root / "credentials.json").exists())
        self.assertFalse((self.root / "pending-device-auth.json").exists())
        self.assertEqual(environment, {"SHIFU_BASE_URL": "cn", "SHIFU_TOKEN": "process-token"})
        first_settings = self.store.settings_path.read_bytes()
        self.store.migrate_legacy(environment)
        self.assertEqual(self.store.settings_path.read_bytes(), first_settings)

    def test_legacy_dotenv_precedence_and_selective_cleanup(self):
        self.legacy("https://app.ai-shifu.cn", "older-saved-token")
        self.env_file.write_text("# keep comment\nSHIFU_BASE_URL=https://custom.example/teach/\n"
                                 "SHIFU_TOKEN='file-token'\nOTHER_SETTING=keep\n")
        self.store.migrate_legacy({"SHIFU_TOKEN": "exported-token"})
        context = self.store.resolve(environ={})
        self.assertEqual(context.base_url, "https://custom.example/teach")
        self.assertEqual(context.token, "file-token")
        self.assertEqual(self.read_env(self.env_file), {
            "SHIFU_BASE_URL": "", "SHIFU_TOKEN": "", "OTHER_SETTING": "keep",
        })
        self.assertIn("# keep comment", self.env_file.read_text())
        self.assertEqual(read_private_json(self.root / "credentials.json")["token"], "older-saved-token")

    def test_exported_credentials_alone_are_not_persisted(self):
        self.store.migrate_legacy({"SHIFU_BASE_URL": "cn", "SHIFU_TOKEN": "exported"})
        self.assertFalse(self.store.settings_path.exists())
        self.assertFalse((self.root / "profiles").exists())

    def test_environment_dependent_dotenv_values_are_not_persisted(self):
        self.env_file.write_text("SHIFU_BASE_URL=cn\nSHIFU_TOKEN=${EXPORTED_TOKEN}\n")
        original = self.env_file.read_bytes()
        with mock.patch.dict(os.environ, {"EXPORTED_TOKEN": "never-persist"}):
            self.store.migrate_legacy(os.environ)
        self.assertFalse(self.store.settings_path.exists())
        self.assertFalse((self.root / "profiles").exists())
        self.assertEqual(self.env_file.read_bytes(), original)

    def test_dynamic_dotenv_does_not_block_independent_saved_configuration_migration(self):
        self.legacy("https://app.ai-shifu.com", "saved-token")
        self.env_file.write_text("SHIFU_BASE_URL=cn\nSHIFU_TOKEN=${EXPORTED_TOKEN}\n")
        self.store.migrate_legacy({"EXPORTED_TOKEN": "never-persist"})
        self.assertEqual(self.store.resolve(environ={}).token, "saved-token")
        self.assertEqual(self.store.resolve(environ={}).base_url, profile_store.SITE_URLS["com"])
        self.assertEqual(self.read_env(self.env_file)["SHIFU_TOKEN"], "${EXPORTED_TOKEN}")

    def test_unknown_origin_credentials_and_pending_are_preserved(self):
        self.legacy(token="unknown-token", pending={"device_code": "unscoped-pending"})
        self.env_file.write_text("SHIFU_TOKEN=unknown-file-token\n")
        before = (self.root / "credentials.json").read_bytes()
        self.store.migrate_legacy({"SHIFU_BASE_URL": "cn"})
        self.assertEqual((self.root / "credentials.json").read_bytes(), before)
        self.assertEqual(self.read_env(self.env_file)["SHIFU_TOKEN"], "unknown-file-token")
        self.assertFalse(self.store.settings_path.exists())

    def test_wrong_service_pending_and_credentials_are_preserved(self):
        self.legacy("https://app.ai-shifu.cn", pending={
            "base_url": "https://app.ai-shifu.com", "device_code": "other-service",
        })
        write_private_json(self.root / "credentials.json", {
            "base_url": "https://app.ai-shifu.com", "token": "other-service-token",
        })
        self.store.migrate_legacy({})
        self.assertEqual(self.store.resolve(environ={}).token, "")
        self.assertTrue((self.root / "credentials.json").exists())
        self.assertTrue((self.root / "pending-device-auth.json").exists())

    def test_pending_origin_does_not_establish_an_unscoped_tokens_origin(self):
        self.legacy(token="unknown-token", pending={"base_url": "https://app.ai-shifu.com", "device_code": "pending"})
        self.store.migrate_legacy({})
        self.assertEqual(self.store.resolve(environ={}).token, "")
        self.assertTrue((self.root / "credentials.json").exists())

    def test_migration_recovers_before_settings_commit_with_same_id(self):
        self.legacy("https://app.ai-shifu.cn", "legacy-token")
        real_write = profile_store.write_private_json

        def fail_on_settings(path, data):
            if path == self.store.settings_path:
                raise OSError("simulated crash before settings commit")
            return real_write(path, data)

        with mock.patch.object(profile_store, "write_private_json", side_effect=fail_on_settings):
            with self.assertRaises(OSError):
                self.store.migrate_legacy({})
        identifier = read_private_json(self.store.migration_path)["id"]
        self.assertTrue((self.root / "credentials.json").exists())
        self.store.migrate_legacy({})
        context = self.store.resolve(environ={})
        self.assertEqual(context.directory.name, identifier)
        self.assertEqual(context.token, "legacy-token")
        self.assertFalse(self.store.migration_path.exists())

    def test_migration_recovers_after_commit_without_overwriting_new_credentials(self):
        self.legacy("https://app.ai-shifu.cn", "legacy-token")
        with mock.patch.object(self.store, "_cleanup_migration", side_effect=OSError("cleanup interrupted")):
            with self.assertRaises(OSError):
                self.store.migrate_legacy({})
        context = self.store.resolve(environ={})
        self.store.save_token(context, "new-login-token")
        self.store.migrate_legacy({})
        self.assertEqual(self.store.resolve(environ={}).token, "new-login-token")
        self.assertFalse((self.root / "credentials.json").exists())
        self.assertFalse(self.store.migration_path.exists())

    def test_cleanup_does_not_delete_changed_legacy_sources(self):
        self.legacy("https://app.ai-shifu.cn", "legacy-token")
        self.env_file.write_text("SHIFU_BASE_URL=cn\n")
        with mock.patch.object(self.store, "_cleanup_migration", side_effect=OSError("cleanup interrupted")):
            with self.assertRaises(OSError):
                self.store.migrate_legacy({})
        write_private_json(self.root / "credentials.json", {"token": "changed-token"})
        self.env_file.write_text("SHIFU_BASE_URL=com\n")
        self.store.migrate_legacy({})
        self.assertEqual(read_private_json(self.root / "credentials.json")["token"], "changed-token")
        self.assertEqual(self.read_env(self.env_file)["SHIFU_BASE_URL"], "com")

    def test_new_schema_never_remigrates_dotenv(self):
        self.store.set_profile("saved", "cn")
        self.env_file.write_text("SHIFU_BASE_URL=com\nSHIFU_TOKEN=temporary\n")
        original = self.env_file.read_bytes()
        self.store.migrate_legacy({})
        self.assertEqual(self.env_file.read_bytes(), original)
        self.assertEqual(self.store.default_profile(), "saved")

    @unittest.skipIf(os.name == "nt", "POSIX permission bits are not Windows ACLs")
    def test_private_file_permissions(self):
        context = self.store.set_profile("saved", "cn")
        self.store.save_token(context, "private-token")
        for path in (self.store.settings_path, self.store.credentials_path(context)):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_config_paths_remain_consistent_on_three_platforms(self):
        for home in ("/Users/alice", "/home/alice", "C:/Users/Alice"):
            with self.subTest(home=home), mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(Path, "home", return_value=Path(home)):
                self.assertEqual(profile_store.config_dir(), Path(home) / ".config" / "ai-shifu")
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.directory / "xdg")}, clear=True):
            self.assertEqual(profile_store.config_dir(), self.directory / "xdg" / "ai-shifu")
        with mock.patch.dict(os.environ, {"AI_SHIFU_CONFIG_DIR": str(self.root), "XDG_CONFIG_HOME": "ignored"}, clear=True):
            self.assertEqual(profile_store.config_dir(), self.root)


if __name__ == "__main__":
    unittest.main()
