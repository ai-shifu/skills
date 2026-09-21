"""Run the real CLI in isolated processes against loopback-only fake services."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "ai-shifu-course-creator"


class CourseProfileProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe = subprocess.run(
            [sys.executable, "-c", "import dotenv, requests"],
            capture_output=True, text=True, timeout=15,
        )
        if probe.returncode:
            raise unittest.SkipTest("Process integration tests require requests and python-dotenv")

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.skill = self.root / "skill"
        self.skill.mkdir()
        # Never copy the installed skill's real .env or any user configuration.
        shutil.copytree(SKILL_ROOT / "scripts", self.skill / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(SKILL_ROOT / ".env.example", self.skill / ".env.example")
        (self.skill / "SKILL.md").write_text("---\nname: profile-test\nversion: 1.0.0\n---\n", encoding="utf-8")
        self.config = self.root / "configuration"
        self.env_file = self.skill / ".env"
        self.cli = self.skill / "scripts" / "shifu-cli.py"
        self.requests = []
        self.allowed_tokens = {
            "one": {"issued-one-secret", "saved-token", "file-token", "temporary-one-secret"},
            "two": {"issued-two-secret", "exported-token", "temporary-two-secret"},
        }
        owner = self

        class FakeService(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def respond(self, status, payload):
                content = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def do_POST(self):
                size = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(size) or b"{}")
                owner.requests.append(("POST", self.path, self.headers.get("Cookie"), body))
                prefix = self.path.split("/")[1]
                if prefix not in owner.allowed_tokens:
                    self.respond(404, {"code": 404})
                elif self.path == f"/{prefix}/api/user/device/authorize":
                    self.respond(200, {"code": 0, "data": {
                        "device_code": f"private-device-{prefix}",
                        "user_code": f"PUBLIC-{prefix.upper()}",
                        "verification_uri_complete": f"{owner.origin}/{prefix}/approve?code=PUBLIC-{prefix.upper()}",
                        "interval": 1, "expires_in": 600,
                    }})
                elif self.path == f"/{prefix}/api/user/device/token" and body == {"device_code": f"private-device-{prefix}"}:
                    self.respond(200, {"code": 0, "data": {
                        "status": "approved", "token": f"issued-{prefix}-secret",
                    }})
                else:
                    self.respond(400, {"code": 400})

            def do_GET(self):
                owner.requests.append(("GET", self.path, self.headers.get("Cookie"), None))
                prefix = self.path.split("/")[1]
                cookie = self.headers.get("Cookie", "")
                token = cookie.removeprefix("token=")
                if (urlsplit(self.path).path != f"/{prefix}/api/shifu/shifus"
                        or token not in owner.allowed_tokens.get(prefix, set())):
                    self.respond(401, {"code": 1004})
                else:
                    self.respond(200, {"code": 0, "data": {"items": [], "total": 0}})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeService)
        self.origin = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)

    def run_cli(self, *args, env=None, expected=0):
        process_env = {key: value for key, value in os.environ.items()
                       if not key.startswith(("SHIFU_", "AI_SHIFU_"))}
        process_env.update({
            "AI_SHIFU_CONFIG_DIR": str(self.config),
            "AI_SHIFU_SKILL_TELEMETRY": "off",
            "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
            "PYTHONIOENCODING": "utf-8",
        })
        process_env.update(env or {})
        result = subprocess.run([sys.executable, str(self.cli), *args], cwd=self.root,
                                env=process_env, capture_output=True, text=True, timeout=20,
                                encoding="utf-8")
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        for secret in ("issued-one-secret", "issued-two-secret", "private-device-one", "private-device-two",
                       "saved-token", "file-token", "exported-token", "temporary-one-secret", "temporary-two-secret"):
            self.assertNotIn(secret, result.stdout + result.stderr)
        return result.stdout

    def settings(self):
        return json.loads((self.config / "settings.json").read_text(encoding="utf-8"))

    def profile_dir(self, name):
        return self.config / "profiles" / self.settings()["profiles"][name]["id"]

    def save_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_independent_authorization_prefixes_default_and_logout(self):
        self.run_cli("profile", "set", "日常 工作", "--base-url", self.origin + "/one/")
        self.run_cli("profile", "set", "../客户A", "--base-url", self.origin + "/two/")
        conflicting = {"SHIFU_BASE_URL": self.origin + "/trap", "SHIFU_TOKEN": "exported-token"}
        first = self.run_cli("login", "--profile", "日常 工作", env=conflicting)
        second = self.run_cli("--profile", "../客户A", "login", env=conflicting)
        self.assertIn("--profile='日常 工作' --wait", first)
        self.assertIn("../客户A", second)
        for name, prefix in (("日常 工作", "one"), ("../客户A", "two")):
            pending = json.loads((self.profile_dir(name) / "pending-device-auth.json").read_text())
            self.assertEqual(pending["base_url"], self.origin + "/" + prefix)
            self.assertEqual(pending["device_code"], f"private-device-{prefix}")
        self.run_cli("login", "--wait", "--profile", "../客户A", env=conflicting)
        self.assertTrue((self.profile_dir("日常 工作") / "pending-device-auth.json").exists())
        self.run_cli("--profile=日常 工作", "login", "--wait", env=conflicting)
        for name, prefix in (("日常 工作", "one"), ("../客户A", "two")):
            directory = self.profile_dir(name)
            self.assertFalse((directory / "pending-device-auth.json").exists())
            credentials = json.loads((directory / "credentials.json").read_text())
            self.assertEqual(credentials, {"base_url": self.origin + "/" + prefix,
                                           "token": f"issued-{prefix}-secret"})
        self.run_cli("verify")
        self.run_cli("--profile", "../客户A", "verify", env=conflicting)
        self.run_cli("verify")
        verified = [(path, cookie) for method, path, cookie, _ in self.requests if method == "GET"]
        self.assertEqual(verified, [
            ("/one/api/shifu/shifus?limit=1", "token=issued-one-secret"),
            ("/two/api/shifu/shifus?limit=1", "token=issued-two-secret"),
            ("/one/api/shifu/shifus?limit=1", "token=issued-one-secret"),
        ])
        self.run_cli("logout", "--profile", "../客户A", env=conflicting)
        self.run_cli("verify")
        request_count = len(self.requests)
        self.run_cli("verify", "--profile", "../客户A", expected=1)
        self.assertEqual(len(self.requests), request_count)
        self.assertEqual(json.loads(self.run_cli("profile", "default"))["default_profile"], "日常 工作")

    def test_saved_legacy_migration_ignores_exported_token_and_survives_next_process(self):
        self.save_json(self.config / "settings.json", {"base_url": self.origin + "/one/"})
        self.save_json(self.config / "credentials.json", {"token": "saved-token"})
        self.save_json(self.config / "pending-device-auth.json", {
            "base_url": self.origin + "/one/", "device_code": "private-device-one",
            "interval": 1, "expires_at": 9999999999,
        })
        self.run_cli("verify", env={"SHIFU_BASE_URL": self.origin + "/two", "SHIFU_TOKEN": "exported-token"})
        self.assertEqual(self.requests[-1][1:3], ("/two/api/shifu/shifus?limit=1", "token=exported-token"))
        self.assertFalse((self.config / "credentials.json").exists())
        self.assertFalse((self.config / "pending-device-auth.json").exists())
        credentials = json.loads((self.profile_dir("default") / "credentials.json").read_text())
        self.assertEqual(credentials, {"base_url": self.origin + "/one", "token": "saved-token"})
        self.assertTrue((self.profile_dir("default") / "pending-device-auth.json").exists())
        before = (self.config / "settings.json").read_bytes()
        self.run_cli("verify")
        self.assertEqual(self.requests[-1][1:3], ("/one/api/shifu/shifus?limit=1", "token=saved-token"))
        self.assertEqual((self.config / "settings.json").read_bytes(), before)
        for file in self.root.rglob("*.json"):
            self.assertNotIn("exported-token", file.read_text())

    def test_real_dotenv_migration_clears_only_migrated_fields_before_loading(self):
        self.env_file.write_text(
            f"# preserve this comment\nSHIFU_BASE_URL='{self.origin}/one/'\n"
            "SHIFU_TOKEN=\"file-token\"\nUNCHANGED='spaces and # text'\n",
            encoding="utf-8",
        )
        # Only a process token is supplied. The migrated .env URL must be gone
        # before load_dotenv, so this is incomplete temporary configuration.
        self.run_cli("verify", env={"SHIFU_TOKEN": "exported-token"}, expected=4)
        self.assertFalse(self.requests)
        credentials = json.loads((self.profile_dir("default") / "credentials.json").read_text())
        self.assertEqual(credentials["token"], "file-token")
        contents = self.env_file.read_text()
        self.assertIn("# preserve this comment", contents)
        self.assertIn("UNCHANGED='spaces and # text'", contents)
        self.assertIn("SHIFU_BASE_URL=''", contents)
        self.assertIn("SHIFU_TOKEN=''", contents)
        self.run_cli("verify")
        self.assertEqual(self.requests[-1][1:3], ("/one/api/shifu/shifus?limit=1", "token=file-token"))
        self.assertEqual(self.env_file.read_text(), contents)

    def test_existing_profiles_keep_dotenv_temporary_and_explicit_profile_wins(self):
        self.run_cli("profile", "set", "named", "--base-url", self.origin + "/one")
        self.run_cli("login", "--profile", "named")
        self.run_cli("login", "--profile", "named", "--wait")
        self.env_file.write_text(f"SHIFU_BASE_URL={self.origin}/two\nSHIFU_TOKEN=temporary-two-secret\n")
        before = (self.profile_dir("named") / "credentials.json").read_bytes()
        self.run_cli("verify")
        self.assertEqual(self.requests[-1][1:3], ("/two/api/shifu/shifus?limit=1", "token=temporary-two-secret"))
        self.run_cli("verify", "--profile", "named")
        self.assertEqual(self.requests[-1][1:3], ("/one/api/shifu/shifus?limit=1", "token=issued-one-secret"))
        self.run_cli("verify", env={"SHIFU_BASE_URL": self.origin + "/one", "SHIFU_TOKEN": "temporary-one-secret"})
        self.assertEqual(self.requests[-1][1:3], ("/one/api/shifu/shifus?limit=1", "token=temporary-one-secret"))
        self.run_cli("verify", "--token", "exported-token")
        self.assertEqual(self.requests[-1][1:3], ("/two/api/shifu/shifus?limit=1", "token=exported-token"))
        count = len(self.requests)
        self.run_cli("login", expected=4)
        self.run_cli("verify", "--profile", "unknown", expected=4)
        self.assertEqual(len(self.requests), count)
        self.assertEqual((self.profile_dir("named") / "credentials.json").read_bytes(), before)
        self.assertEqual(self.settings()["default_profile"], "named")


if __name__ == "__main__":
    unittest.main()
