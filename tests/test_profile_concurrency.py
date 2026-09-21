"""Cross-process regression coverage for shared profile settings transactions."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "ai-shifu-course-creator" / "scripts"
WORKER = r"""
import sys, time
from pathlib import Path
import profile_store as profiles

root, action, name, label, gate = sys.argv[1:]
root = Path(root)
store = profiles.ProfileStore(root / 'config', root / '.env')
original_write = profiles.write_private_json

def guarded_write(path, data):
    if path == store.settings_path:
        (root / (label + '-snapshot')).touch()
        if gate == 'yes':
            deadline = time.monotonic() + 10
            while not (root / 'release').exists():
                if time.monotonic() > deadline:
                    raise RuntimeError('test gate timed out')
                time.sleep(0.01)
    return original_write(path, data)

profiles.write_private_json = guarded_write
(root / (label + '-started')).touch()
if action == 'set':
    store.set_profile(name, 'com')
elif action == 'default':
    store.default_profile(name)
elif action == 'migrate-set':
    store.migrate_legacy()
    store.set_profile(name, 'com')
elif action == 'lock':
    with store._configuration_lock():
        (root / (label + '-locked')).touch()
        time.sleep(10)
elif action == 'timeout':
    try:
        with store._configuration_lock(timeout=0.1):
            raise RuntimeError('acquired a lock held by another process')
    except profiles.ProfileError:
        pass
"""


class ProfileConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe = subprocess.run([sys.executable, "-c", "import dotenv"], capture_output=True, timeout=10)
        if probe.returncode:
            raise unittest.SkipTest("Profile subprocess tests require python-dotenv")

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.config = self.root / "config"
        self.config.mkdir()
        self.processes = []
        self.addCleanup(self.stop_workers)

    def stop_workers(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def start(self, action, name, label, *, gated=False):
        process = subprocess.Popen(
            [sys.executable, "-c", WORKER, str(self.root), action, name, label,
             "yes" if gated else "no"],
            env={**os.environ, "PYTHONPATH": str(SCRIPT_DIR)},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.processes.append(process)
        return process

    def wait_for(self, name):
        deadline = time.monotonic() + 5
        while not (self.root / name).exists():
            if time.monotonic() > deadline:
                self.fail(f"Worker did not reach {name}")
            time.sleep(0.01)

    def finish(self, process):
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0, stdout + stderr)

    def settings(self):
        return json.loads((self.config / "settings.json").read_text())

    def overlap(self, first_action, first_name, second_action, second_name):
        first = self.start(first_action, first_name, "first", gated=True)
        self.wait_for("first-snapshot")
        second = self.start(second_action, second_name, "second")
        self.wait_for("second-started")
        # The first is paused after reading its snapshot. A concurrent writer
        # must neither reach a write nor exit on half-migrated legacy state.
        time.sleep(0.2)
        try:
            self.assertFalse((self.root / "second-snapshot").exists())
            self.assertIsNone(second.poll())
        finally:
            (self.root / "release").touch()
            self.finish(first)
            self.finish(second)

    def test_concurrent_creations_keep_both_profiles_and_the_first_default(self):
        self.overlap("set", "first", "set", "second")
        data = self.settings()
        self.assertEqual(set(data["profiles"]), {"first", "second"})
        self.assertEqual(data["default_profile"], "first")

    def test_concurrent_creation_does_not_revert_a_default_change(self):
        self.finish(self.start("set", "original", "seed1"))
        self.finish(self.start("set", "chosen", "seed2"))
        self.overlap("set", "new", "default", "chosen")
        data = self.settings()
        self.assertEqual(set(data["profiles"]), {"original", "chosen", "new"})
        self.assertEqual(data["default_profile"], "chosen")

    def test_concurrent_migration_and_creation_keep_referenced_credentials(self):
        (self.config / "settings.json").write_text(json.dumps({"base_url": "https://app.ai-shifu.cn"}))
        (self.config / "credentials.json").write_text(json.dumps({"token": "legacy-test-token"}))
        self.overlap("migrate-set", "first", "migrate-set", "second")
        data = self.settings()
        self.assertEqual(set(data["profiles"]), {"default", "first", "second"})
        self.assertEqual(data["default_profile"], "default")
        credentials = list((self.config / "profiles").glob("*/credentials.json"))
        self.assertEqual(len(credentials), 1)
        self.assertEqual(credentials[0].parent.name, data["profiles"]["default"]["id"])
        self.assertEqual(json.loads(credentials[0].read_text())["token"], "legacy-test-token")
        self.assertFalse((self.config / ".profile-migration.json").exists())

    def test_lock_times_out_and_is_released_when_owner_is_terminated(self):
        owner = self.start("lock", "", "owner")
        self.wait_for("owner-locked")
        self.finish(self.start("timeout", "", "waiter"))
        owner.terminate()
        owner.communicate(timeout=5)
        self.finish(self.start("set", "after-exit", "next"))
        self.assertEqual(self.settings()["default_profile"], "after-exit")


if __name__ == "__main__":
    unittest.main()
