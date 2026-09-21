"""Persistent named service profiles and their independent authorization state."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import unicodedata
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values, set_key


SITE_URLS = {"cn": "https://app.ai-shifu.cn", "com": "https://app.ai-shifu.com"}
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class ProfileError(ValueError):
    """A profile, its credentials, or an explicit override is unusable."""


@dataclass(frozen=True)
class ProfileContext:
    name: str | None
    base_url: str
    directory: Path | None
    token: str = field(default="", repr=False)


def config_dir():
    """Keep the existing cross-platform XDG-style configuration location."""
    override = os.environ.get("AI_SHIFU_CONFIG_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    xdg_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg_home).expanduser() if xdg_home else Path.home() / ".config"
    return base / "ai-shifu"


def normalize_base_url(value):
    """Expand URL shortcuts and normalize an origin with an optional path prefix."""
    if not isinstance(value, str):
        raise ProfileError("Provide a service URL or the cn/com shortcut.")
    value = value.strip()
    value = SITE_URLS.get(value.lower(), value)
    try:
        parsed = urlsplit(value)
        hostname, port = parsed.hostname, parsed.port
        valid = (
            bool(hostname) and (port is None or port > 0)
            and parsed.username is None and parsed.password is None
            and "?" not in value and "#" not in value and "\\" not in value
            and not any(c.isspace() or unicodedata.category(c).startswith("C") for c in value)
            and parsed.scheme in {"http", "https"}
        )
    except ValueError:
        valid = False
    if not valid:
        raise ProfileError("Provide a service URL with a hostname and no credentials, query, or fragment.")
    if parsed.scheme != "https" and hostname not in LOOPBACK_HOSTS:
        raise ProfileError("Service URLs must use HTTPS; HTTP is only supported on localhost.")
    # Normalize host casing and default ports while preserving case-sensitive paths.
    host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and (parsed.scheme, port) not in {("https", 443), ("http", 80)}:
        host += f":{port}"
    return urlunsplit((parsed.scheme, host, parsed.path.rstrip("/"), "", ""))


def normalize_profile_name(name):
    if not isinstance(name, str):
        raise ProfileError("A profile name must be text.")
    # Validate before trimming so a trailing newline cannot become a valid name.
    if any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in name):
        raise ProfileError("Profile names must not contain control characters.")
    name = name.strip()
    if not name:
        raise ProfileError("A profile name must not be empty.")
    return name


def read_private_json(path):
    """Read state strictly; corrupt existing state must never look unconfigured."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ProfileError(f"Cannot read configuration file: {path}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"Expected a JSON object in: {path}")
    return data


def write_private_json(path, payload):
    """Atomically replace a JSON file without exposing an intermediate plaintext file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.chmod(temp_name, 0o600)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temp_name)
        raise


def credentials_path(context):
    if context.directory is None:
        raise ProfileError("Temporary credentials cannot be saved; select a named profile.")
    return context.directory / "credentials.json"


def pending_auth_path(context):
    if context.directory is None:
        raise ProfileError("Browser authorization requires a named profile.")
    return context.directory / "pending-device-auth.json"


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ProfileStore:
    def __init__(self, root, env_file):
        self.root = Path(root)
        self.env_file = Path(env_file)
        self.settings_path = self.root / "settings.json"
        self.migration_path = self.root / ".profile-migration.json"

    credentials_path = staticmethod(credentials_path)
    pending_auth_path = staticmethod(pending_auth_path)

    def _settings(self):
        settings = read_private_json(self.settings_path)
        if settings is None:
            return {"schema_version": 2, "default_profile": None, "profiles": {}}
        if settings.get("schema_version") != 2:
            raise ProfileError("Legacy configuration must be migrated before using profiles.")
        profiles = settings.get("profiles")
        if not isinstance(profiles, dict):
            raise ProfileError("Profile configuration must contain a profiles object.")
        ids = set()
        for name, entry in profiles.items():
            if normalize_profile_name(name) != name or not isinstance(entry, dict):
                raise ProfileError("Invalid profile configuration.")
            identifier = entry.get("id")
            try:
                valid_id = isinstance(identifier, str) and str(uuid.UUID(identifier)) == identifier
            except ValueError:
                valid_id = False
            if not valid_id or identifier in ids:
                raise ProfileError("Each profile must have its own valid internal ID.")
            ids.add(identifier)
            if normalize_base_url(entry.get("base_url")) != entry["base_url"]:
                raise ProfileError(f"Profile '{name}' has a non-normalized service URL.")
        default = settings.get("default_profile")
        if (profiles and (not isinstance(default, str) or default not in profiles)) or (
            not profiles and default is not None
        ):
            raise ProfileError("The default profile does not identify a configured profile.")
        return settings

    def _context(self, settings, name):
        name = normalize_profile_name(name)
        entry = settings["profiles"].get(name)
        if entry is None:
            raise ProfileError(f"Unknown profile: {name}")
        return ProfileContext(name, entry["base_url"], self.root / "profiles" / entry["id"])

    def list_profiles(self):
        settings = self._settings()
        return [{
            "name": name,
            "base_url": entry["base_url"],
            "default": name == settings["default_profile"],
            "credentials_present": credentials_path(self._context(settings, name)).is_file(),
        } for name, entry in settings["profiles"].items()]

    def set_profile(self, name, url):
        name, url = normalize_profile_name(name), normalize_base_url(url)
        settings = self._settings()
        entry = settings["profiles"].get(name)
        if entry is not None:
            context = self._context(settings, name)
            if entry["base_url"] != url and (
                credentials_path(context).exists() or pending_auth_path(context).exists()
            ):
                raise ProfileError(f"Profile '{name}' has authorization state; run logout for it before changing its URL.")
            entry["base_url"] = url
        else:
            settings["profiles"][name] = {"id": str(uuid.uuid4()), "base_url": url}
            if settings["default_profile"] is None:
                settings["default_profile"] = name
        write_private_json(self.settings_path, settings)
        return self._context(settings, name)

    def default_profile(self, name=None):
        settings = self._settings()
        if name is not None:
            name = self._context(settings, name).name
            settings["default_profile"] = name
            write_private_json(self.settings_path, settings)
        return settings["default_profile"]

    def resolve(self, name=None, environ=None, token=None, allow_unconfigured=False, named_only=False,
                load_credentials=True):
        """Resolve once; explicit profiles ignore all environment credential inputs."""
        environ = os.environ if environ is None else environ
        explicit_token = token.strip() if isinstance(token, str) else ""
        settings = self._settings()
        if name is not None:
            context = self._context(settings, name)
        else:
            env_url = str(environ.get("SHIFU_BASE_URL") or "").strip()
            env_token = str(environ.get("SHIFU_TOKEN") or "").strip()
            if env_url or env_token:
                if named_only:
                    raise ProfileError("This operation requires a named profile; use --profile when temporary configuration is active.")
                if not env_url or not (explicit_token or env_token):
                    raise ProfileError("Temporary configuration requires both SHIFU_BASE_URL and SHIFU_TOKEN (or --token).")
                return ProfileContext(None, normalize_base_url(env_url), None, explicit_token or env_token)
            default = settings["default_profile"]
            if default is None:
                if allow_unconfigured:
                    return None
                raise ProfileError("No default profile is configured. Create one with 'profile set <name> --base-url <URL>'.")
            context = self._context(settings, default)
        return replace(context, token=explicit_token or (self.load_token(context) if load_credentials else ""))

    def load_token(self, context):
        if context.directory is None:
            return context.token
        data = read_private_json(credentials_path(context))
        if data is None:
            return ""
        if normalize_base_url(data.get("base_url")) != context.base_url:
            raise ProfileError(f"Credentials do not belong to the service configured for profile '{context.name}'.")
        token = data.get("token")
        if not isinstance(token, str) or not token.strip():
            raise ProfileError(f"Invalid credentials for profile '{context.name}'; run logout and login for this profile.")
        return token.strip()

    def save_token(self, context, token):
        if not isinstance(token, str) or not token.strip():
            raise ProfileError("Cannot save an empty token.")
        write_private_json(credentials_path(context), {"base_url": context.base_url, "token": token.strip()})

    def logout(self, context):
        for path in (credentials_path(context), pending_auth_path(context)):
            with contextlib.suppress(FileNotFoundError):
                path.unlink()

    def _env_values(self):
        if not self.env_file.exists():
            return {}
        # Legacy migration must inspect saved values, never credentials expanded
        # from the current process environment by python-dotenv.
        return {key: (value or "").strip()
                for key, value in dotenv_values(str(self.env_file), interpolate=False).items()}

    def _cleanup_migration(self, journal):
        """Delete only sources whose contents still match the committed migration."""
        for filename, expected in journal.get("legacy_files", {}).items():
            if filename not in {"credentials.json", "pending-device-auth.json"}:
                raise ProfileError("Invalid profile migration journal.")
            path = self.root / filename
            if path.exists() and _digest(path.read_text(encoding="utf-8")) == expected:
                path.unlink()
        current = self._env_values()
        clear_keys = [key for key, expected in journal.get("env_fields", {}).items()
                      if key in {"SHIFU_BASE_URL", "SHIFU_TOKEN"}
                      and _digest(current.get(key, "")) == expected]
        if clear_keys:
            # Work on a private copy; interruption can leave either the old or new
            # .env but never a half-written file. The journal makes cleanup retryable.
            fd, temp_name = tempfile.mkstemp(dir=str(self.env_file.parent), prefix=".tmp-profile-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    os.chmod(temp_name, 0o600)
                    handle.write(self.env_file.read_text(encoding="utf-8"))
                for key in clear_keys:
                    set_key(temp_name, key, "")
                os.chmod(temp_name, 0o600)
                os.replace(temp_name, self.env_file)
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(temp_name)
                raise
        self.migration_path.unlink(missing_ok=True)

    def migrate_legacy(self, process_env=None):
        """Migrate saved legacy inputs, never exported process credentials.

        A small journal fixes the new ID before any writes. New files are read
        back before settings commit, and cleanup is resumable after that commit.
        The process environment is intentionally neither read nor modified.
        """
        settings = read_private_json(self.settings_path)
        journal = read_private_json(self.migration_path)
        if settings is not None and settings.get("schema_version") == 2:
            self._settings()
            if journal:
                self._cleanup_migration(journal)
            return
        if settings and "schema_version" in settings:
            raise ProfileError("Unsupported profile configuration version.")
        settings = settings or {}
        env = self._env_values()
        # Leave environment-dependent .env configurations as temporary inputs.
        # Their eventual URL/token cannot be proven from saved state alone.
        indirect_env = any("${" in env.get(key, "") for key in ("SHIFU_BASE_URL", "SHIFU_TOKEN"))
        migration_env = {} if indirect_env else env
        old_credentials = read_private_json(self.root / "credentials.json") or {}
        old_pending = read_private_json(self.root / "pending-device-auth.json") or {}
        configured_url = migration_env.get("SHIFU_BASE_URL") or settings.get("base_url")
        raw_url = (configured_url
                   or old_credentials.get("base_url") or old_pending.get("base_url"))
        if not raw_url:
            # An unscoped token cannot establish its own origin. Keep it intact.
            return
        url = normalize_base_url(raw_url)
        identifier = journal.get("id") if journal else str(uuid.uuid4())
        if journal and journal.get("base_url") != url:
            raise ProfileError("Legacy service configuration changed during migration; restore its previous URL and retry.")
        try:
            if str(uuid.UUID(identifier)) != identifier:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as exc:
            raise ProfileError("Invalid profile migration identifier.") from exc
        context = ProfileContext("default", url, self.root / "profiles" / identifier)
        records = []
        env_fields, legacy_files = {}, {}
        env_token = migration_env.get("SHIFU_TOKEN")
        old_token = old_credentials.get("token")
        credential_url = old_credentials.get("base_url") or configured_url
        if env_token and configured_url:
            records.append((credentials_path(context), {"base_url": url, "token": env_token}))
            env_fields["SHIFU_TOKEN"] = _digest(env_token)
        elif (isinstance(old_token, str) and old_token.strip() and credential_url
              and normalize_base_url(credential_url) == url):
            records.append((credentials_path(context), {"base_url": url, "token": old_token.strip()}))
            legacy_files["credentials.json"] = _digest((self.root / "credentials.json").read_text(encoding="utf-8"))
        if old_pending.get("base_url") and normalize_base_url(old_pending["base_url"]) == url:
            records.append((pending_auth_path(context), {**old_pending, "base_url": url}))
            legacy_files["pending-device-auth.json"] = _digest((self.root / "pending-device-auth.json").read_text(encoding="utf-8"))
        if migration_env.get("SHIFU_BASE_URL"):
            env_fields["SHIFU_BASE_URL"] = _digest(migration_env["SHIFU_BASE_URL"])
        journal = {"id": identifier, "base_url": url, "legacy_files": legacy_files, "env_fields": env_fields}
        write_private_json(self.migration_path, journal)
        for path, data in records:
            write_private_json(path, data)
            if read_private_json(path) != data:
                raise ProfileError("Could not verify migrated profile authorization state.")
        write_private_json(self.settings_path, {
            "schema_version": 2, "default_profile": "default",
            "profiles": {"default": {"id": identifier, "base_url": url}},
        })
        self._cleanup_migration(journal)
