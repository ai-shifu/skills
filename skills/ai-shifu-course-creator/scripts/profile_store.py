"""Persistent named service profiles and their independent authorization state."""

from __future__ import annotations

import contextlib
import errno
import hashlib
import io
import json
import os
import tempfile
import time
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


class ProfileFormatError(ProfileError):
    """A readable local configuration file has invalid encoding or JSON shape."""


@dataclass(frozen=True)
class ProfileContext:
    name: str | None
    base_url: str
    directory: Path | None
    token: str = field(default="", repr=False)


def _process_config_dir(environ):
    override = str(environ.get("AI_SHIFU_CONFIG_DIR") or "").strip()
    if override:
        return _configuration_path(override, environ)
    xdg_home = str(environ.get("XDG_CONFIG_HOME") or "").strip()
    base = _configuration_path(xdg_home, environ) if xdg_home else _configuration_path("~", environ) / ".config"
    return base / "ai-shifu"


def _configuration_path(value, environ):
    home = environ.get("USERPROFILE" if os.name == "nt" else "HOME") or str(Path.home())
    if home and (value == "~" or value.startswith(("~/", "~\\"))):
        value = str(Path(home) / value[2:]) if value != "~" else home
    return Path(value).expanduser()


def config_dir():
    """Keep the existing cross-platform XDG-style configuration location."""
    return _process_config_dir(os.environ)


def _npm_root_pointer(default_root):
    path = Path(default_root) / "cli-config-root.json"
    data = read_private_json(path)
    if data is None:
        return None
    value = data.get("config_dir")
    if (set(data) != {"schema_version", "config_dir"}
            or type(data.get("schema_version")) is not int or data["schema_version"] != 1
            or not isinstance(value, str) or not value or "\0" in value
            or not Path(value).is_absolute()):
        raise ProfileFormatError(f"Invalid npm configuration root pointer: {path}")
    return Path(value).resolve()


def npm_config_dir(environ=None):
    """Use a recorded npm root without changing unmarked skill installations."""
    environ = os.environ if environ is None else environ
    default_root = _process_config_dir(environ).resolve()
    if str(environ.get("AI_SHIFU_CONFIG_DIR") or "").strip():
        return default_root
    return _npm_root_pointer(default_root) or default_root


def _has_root_selection(root):
    """Detect account state or an existing user choice before switching roots."""
    root = Path(root)
    settings = read_private_json(root / "settings.json")
    if settings is not None:
        if settings.get("schema_version") == 2:
            if ProfileStore(root, root / "cli.env")._settings()["profiles"]:
                return True
        elif settings:
            return True
    if any((root / name).exists() for name in (
        "credentials.json", "pending-device-auth.json", ".profile-migration.json",
    )):
        return True
    profile_directory = root / "profiles"
    if profile_directory.is_dir() and any(profile_directory.iterdir()):
        return True
    environment_file = root / "cli.env"
    if environment_file.exists():
        template = Path(__file__).resolve().parent.parent / ".env.example"
        return _installer_env_values(environment_file.read_bytes()) != _installer_env_values(template.read_bytes())
    return False


def resolve_installer_config_root(default_root, directories, environ=None):
    """Select a legacy root in place; never copy credentials between roots."""
    environ = os.environ if environ is None else environ
    default_root = Path(default_root).resolve()
    process_override = str(environ.get("AI_SHIFU_CONFIG_DIR") or "").strip()
    process_xdg = str(environ.get("XDG_CONFIG_HOME") or "").strip()
    if process_override:
        return _process_config_dir(environ).resolve()
    selected = set()
    for directory in dict.fromkeys(Path(directory) for directory in directories):
        try:
            values = _installer_env_values((directory / ".env").read_bytes())
        except FileNotFoundError:
            continue
        legacy_override = str(values.get("AI_SHIFU_CONFIG_DIR") or "").strip()
        legacy_xdg = str(values.get("XDG_CONFIG_HOME") or "").strip()
        if not legacy_override and not legacy_xdg:
            continue
        override = process_override or legacy_override
        xdg = process_xdg or legacy_xdg
        value = override or xdg
        if "${" in value:
            raise ProfileError("Legacy configuration roots must be literal paths before installation.")
        root = _configuration_path(value, environ)
        selected.add((root if override else root / "ai-shifu").resolve())
    if len(selected) > 1:
        raise ProfileError("Selected legacy installations use different configuration roots; choose a root before installation.")
    pointer = _npm_root_pointer(default_root)
    candidate = next(iter(selected), pointer or default_root)
    if pointer is not None:
        if candidate != pointer:
            raise ProfileError("The selected legacy configuration root differs from the existing npm root; choose a root explicitly.")
        return pointer
    if candidate != default_root and _has_root_selection(default_root):
        raise ProfileError("The current npm configuration root already has an account or user settings; choose a root explicitly.")
    return candidate


def record_installer_config_root(default_root, selected_root, environ=None):
    """Publish the path-only pointer after the selected root was imported."""
    environ = os.environ if environ is None else environ
    default_root, selected_root = Path(default_root).resolve(), Path(selected_root).resolve()
    if str(environ.get("AI_SHIFU_CONFIG_DIR") or "").strip() or default_root == selected_root:
        return
    pointer = _npm_root_pointer(default_root)
    if pointer is not None and pointer != selected_root:
        raise ProfileError("The npm configuration root changed during installation; retry with an explicit root.")
    write_private_json(default_root / "cli-config-root.json", {
        "schema_version": 1, "config_dir": str(selected_root),
    })


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
    except (UnicodeError, ValueError) as exc:
        raise ProfileFormatError(f"Invalid configuration file: {path}") from exc
    except OSError as exc:
        raise ProfileError(f"Cannot read configuration file: {path}") from exc
    if not isinstance(data, dict):
        raise ProfileFormatError(f"Expected a JSON object in: {path}")
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


def _clear_private_env_keys(path, keys):
    """Clear selected dotenv values through an owner-only atomic replacement."""
    _write_private_env(path, Path(path).read_bytes(), clear_keys=keys)


def _write_private_env(path, content, *, clear_keys=()):
    """Publish a complete dotenv file with private permissions on every platform."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-profile-")
    try:
        with os.fdopen(fd, "wb") as handle:
            os.chmod(temp_name, 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        for key in clear_keys:
            set_key(temp_name, key, "")
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temp_name)
        raise


def _installer_env_values(content):
    """Compare dotenv values without comments, quoting differences, or expansion."""
    try:
        values = dotenv_values(stream=io.StringIO(content.decode("utf-8")), interpolate=False)
    except (UnicodeError, ValueError) as exc:
        raise ProfileError("Cannot read a legacy environment file as UTF-8 dotenv configuration.") from exc
    return {key: value for key, value in values.items() if value not in (None, "")}


def _installer_credential_identity(base_url, token):
    return _digest(json.dumps([base_url, token], ensure_ascii=False, separators=(",", ":")))


class ProfileStore:
    def __init__(self, root, env_file):
        self.root = Path(root)
        self.env_file = Path(env_file)
        self.settings_path = self.root / "settings.json"
        self.migration_path = self.root / ".profile-migration.json"

    credentials_path = staticmethod(credentials_path)
    pending_auth_path = staticmethod(pending_auth_path)

    @contextlib.contextmanager
    def _configuration_lock(self, timeout=10):
        """Serialize shared settings transactions; OS locks release on process exit."""
        self.root.mkdir(parents=True, exist_ok=True)
        # Never unlink the lock file: waiters must continue locking the same inode.
        fd = os.open(self.root / ".profiles.lock", os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "r+b") as handle:
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                def acquire():
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

                def release():
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                def acquire():
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                def release():
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

            deadline = time.monotonic() + timeout
            while True:
                try:
                    acquire()
                    break
                except OSError as exc:
                    if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise
                    if time.monotonic() >= deadline:
                        raise ProfileError("Profile configuration is busy; retry this command shortly.") from exc
                    time.sleep(0.05)
            try:
                yield
            finally:
                release()

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
        receipts = settings.get("installer_imports", {})
        if not isinstance(receipts, dict) or any(
            not isinstance(identity, str) or len(identity) != 64
            or any(character not in "0123456789abcdef" for character in identity)
            or not isinstance(identifier, str) or identifier not in ids
            for identity, identifier in receipts.items()
        ):
            raise ProfileError("Invalid installer configuration import receipts.")
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
        with self._configuration_lock():
            return self._set_profile(name, url)

    def configure_site(self, url, *, name=None, environ=None):
        """Select and configure the compatibility command's target atomically."""
        with self._configuration_lock():
            context = self.resolve(name=name, environ=environ, named_only=True,
                                   allow_unconfigured=True, load_credentials=False)
            return self._set_profile(context.name if context else "default", url)

    def _set_profile(self, name, url):
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
        if name is None:
            return self._settings()["default_profile"]
        with self._configuration_lock():
            settings = self._settings()
            name = self._context(settings, name).name
            settings["default_profile"] = name
            write_private_json(self.settings_path, settings)
            return name

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

    def _current_auth_context(self, context):
        """Revalidate an authorization context while the caller holds the settings lock."""
        current = self._context(self._settings(), context.name)
        if current.directory != context.directory or current.base_url != context.base_url:
            raise ProfileError("Profile configuration changed; retry the command for the intended profile.")
        return current

    def save_pending_auth(self, context, pending):
        """Bind a pending request to the still-current profile under the settings lock."""
        with self._configuration_lock():
            current = self._current_auth_context(context)
            if normalize_base_url(pending.get("base_url")) != current.base_url:
                raise ProfileError("Pending authorization does not belong to this profile's service.")
            write_private_json(pending_auth_path(current), pending)

    def finish_pending_auth(self, context, device_code, token=None):
        """Consume only the current request, optionally storing its approved token."""
        with self._configuration_lock():
            current = self._current_auth_context(context)
            path = pending_auth_path(current)
            pending = read_private_json(path)
            if (not pending or not device_code or pending.get("device_code") != device_code
                    or normalize_base_url(pending.get("base_url")) != current.base_url):
                raise ProfileError(
                    "Pending authorization changed or was cleared; run login again for this profile."
                )
            if token is not None:
                self.save_token(current, token)
            path.unlink()

    def logout(self, context):
        with self._configuration_lock():
            current = self._current_auth_context(context)
            # Keep credentials until backup cleanup succeeds so a failed logout
            # can retry without losing the token needed to identify its copies.
            try:
                credentials = read_private_json(credentials_path(current))
            except ProfileFormatError:
                # Explicit logout can discard a confirmed corrupt credential
                # file. I/O errors still stop before anything is removed.
                credentials = None
            token = (credentials or {}).get("token")
            token_digests = {_digest(token.strip())} if isinstance(token, str) and token.strip() else set()
            identities = {identity for identity, identifier in self._settings().get("installer_imports", {}).items()
                          if identifier == current.directory.name}
            self._clear_legacy_backup_tokens(token_digests, installer_identities=identities)
            for path in (credentials_path(current), pending_auth_path(current)):
                with contextlib.suppress(FileNotFoundError):
                    path.unlink()

    def _env_values(self, path=None):
        path = self.env_file if path is None else Path(path)
        if not path.exists():
            return {}
        # Legacy migration must inspect saved values, never credentials expanded
        # from the current process environment by python-dotenv.
        return {key: (value or "").strip()
                for key, value in dotenv_values(str(path), interpolate=False).items()}

    def _clear_legacy_backup_tokens(self, expected_digests, *, installer_identities=()):
        """Remove only copies of the affected credential from installer backups."""
        if not expected_digests and not installer_identities:
            return
        try:
            backups = list((self.root / "legacy-env").iterdir())
        except FileNotFoundError:
            return
        for backup in backups:
            # Backups are ordinary installer-created files, never external paths.
            if backup.suffix != ".env" or backup.is_symlink() or not backup.is_file():
                continue
            values = self._env_values(backup)
            token = values.get("SHIFU_TOKEN", "")
            matches = bool(token and _digest(token) in expected_digests)
            if token and not matches and installer_identities:
                try:
                    base_url = normalize_base_url(values.get("SHIFU_BASE_URL", ""))
                except ProfileError:
                    continue
                matches = _installer_credential_identity(base_url, token) in installer_identities
            if matches:
                _clear_private_env_keys(backup, ["SHIFU_TOKEN"])

    def import_installer_configuration(self, directories, template_file):
        """Import selected installation settings under the profile transaction lock.

        Original source files stay untouched. Private backups, profile changes,
        and token cleanup share the same lock as logout and browser login.
        """
        with self._configuration_lock():
            # Complete a prior transaction before any preserved/unchanged return
            # can report installation success while its migration is pending.
            if self.migration_path.exists():
                self._migrate_legacy()
            template = Path(template_file).read_bytes()
            template_values = _installer_env_values(template)
            configurations = {}
            backup_directory = self.root / "legacy-env"
            for directory in dict.fromkeys(Path(directory) for directory in directories):
                source = directory / ".env"
                try:
                    content = source.read_bytes()
                except FileNotFoundError:
                    continue
                backup_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
                backup = backup_directory / (hashlib.sha256(content).hexdigest() + ".env")
                if backup.exists():
                    if backup.is_symlink() or not backup.is_file():
                        raise ProfileError("Invalid installer configuration backup.")
                    # A previous import or logout may have cleared its token.
                    # Never restore the original secret over that sanitized copy.
                    os.chmod(backup, 0o600)
                else:
                    _write_private_env(backup, content)
                values = _installer_env_values(content)
                if values != template_values:
                    fingerprint = json.dumps(values, ensure_ascii=False, sort_keys=True)
                    configurations.setdefault(fingerprint, (content, values))
            existing = self.env_file.read_bytes() if self.env_file.exists() else None
            replace_environment = existing is None or _installer_env_values(existing) == template_values
            if len(configurations) > 1:
                if not replace_environment:
                    # The user has already selected this CLI's configuration;
                    # keep that choice rather than guessing among old installs.
                    return {"status": "preserved", "imported_profiles": []}
                raise ProfileError(
                    f"Different legacy configurations were saved in {backup_directory}. "
                    "Choose one configuration before retrying installation."
                )
            if not configurations:
                return {"status": "unchanged", "imported_profiles": []}
            content, values = next(iter(configurations.values()))
            base_url = str(values.get("SHIFU_BASE_URL") or "").strip()
            token = str(values.get("SHIFU_TOKEN") or "").strip()
            if any("${" in value for value in (base_url, token)) or (token and not base_url):
                raise ProfileError(
                    "Legacy credentials need an explicit service URL and literal values before installation. "
                    "Original files and private backups were preserved."
                )
            if base_url:
                base_url = normalize_base_url(base_url)
            identity = _installer_credential_identity(base_url, token) if base_url else None
            settings = read_private_json(self.settings_path)
            if settings and "schema_version" in settings and settings.get("schema_version") != 2:
                raise ProfileError("Unsupported profile configuration version.")
            if not settings or settings.get("schema_version") != 2:
                if not replace_environment:
                    if not base_url:
                        return {"status": "preserved", "imported_profiles": []}
                    if settings:
                        raise ProfileError(
                            "Migrate the existing legacy profile settings before importing another installation. "
                            "Original files and private backups were preserved."
                        )
                    # A user-selected option such as the analytics opt-out is
                    # independent of the incoming account. Preserve these options
                    # while saving the unique, explicit source account in a profile.
                    selected = _installer_env_values(existing)
                    selected_url = str(selected.get("SHIFU_BASE_URL") or "").strip()
                    selected_token = str(selected.get("SHIFU_TOKEN") or "").strip()
                    if any("${" in value for value in (selected_url, selected_token)) or (selected_token and not selected_url):
                        raise ProfileError(
                            "Selected CLI credentials need an explicit service URL and literal values before installation. "
                            "Original files and private backups were preserved."
                        )
                    if selected_url:
                        selected_url = normalize_base_url(selected_url)
                        # Preserve the selected account as default before saving
                        # a different source as an inactive profile. Migration
                        # retains preferences and clears temporary credentials.
                        self._migrate_legacy(installer_identity=_installer_credential_identity(selected_url, selected_token))
                        initial = self._settings()
                    else:
                        initial = {"schema_version": 2, "default_profile": None, "profiles": {}}
                    name = self._import_installer_profile(initial, base_url, token, identity)
                    if token:
                        self._clear_legacy_backup_tokens({_digest(token)})
                    return {"status": "imported", "imported_profiles": [name]}
                _write_private_env(self.env_file, content)
                self._migrate_legacy(installer_identity=identity)
                names = []
                if identity:
                    migrated = self._settings()
                    identifier = migrated.get("installer_imports", {}).get(identity)
                    names = [name for name, entry in migrated["profiles"].items() if entry["id"] == identifier]
                return {"status": "imported", "imported_profiles": names}

            # Finish any prior committed migration before importing another copy.
            self._migrate_legacy()
            settings = self._settings()
            imported_profiles = []
            if base_url:
                imported_profiles.append(self._import_installer_profile(settings, base_url, token, identity))
            if replace_environment:
                # Existing profiles own credentials. Do not activate the imported
                # source as a temporary dotenv override of the current default.
                credential_keys = [key for key in ("SHIFU_BASE_URL", "SHIFU_TOKEN") if key in values]
                _write_private_env(self.env_file, content, clear_keys=credential_keys)
            if token:
                self._clear_legacy_backup_tokens({_digest(token)})
            return {
                "status": "imported" if replace_environment or imported_profiles else "preserved",
                "imported_profiles": imported_profiles,
            }

    def _import_installer_profile(self, settings, base_url, token, identity):
        """Create or reuse an inactive profile, never replay an imported token."""
        receipts = settings.setdefault("installer_imports", {})
        if identity in receipts:
            identifier = receipts[identity]
            for name, entry in settings["profiles"].items():
                if entry["id"] == identifier:
                    # This source was already consumed. Later logout or service
                    # changes belong to the user, not a reason to replay it.
                    return name
            raise ProfileError("An imported profile no longer exists.")
        for name, entry in settings["profiles"].items():
            if entry["base_url"] == base_url:
                context = self._context(settings, name)
                if not token or self.load_token(context) == token:
                    receipts[identity] = entry["id"]
                    write_private_json(self.settings_path, settings)
                    return name
        name = f"imported-{urlsplit(base_url).hostname}-{identity[:12]}"
        if name in settings["profiles"]:
            raise ProfileError("An imported profile name is already in use; choose an explicit profile before retrying.")
        identifier = str(uuid.uuid4())
        settings["profiles"][name] = {"id": identifier, "base_url": base_url}
        if settings["default_profile"] is None:
            settings["default_profile"] = name
        context = self._context(settings, name)
        try:
            if token:
                self.save_token(context, token)
            receipts[identity] = identifier
            write_private_json(self.settings_path, settings)
        except BaseException:
            # A failed settings commit must not strand an undiscoverable copy
            # of the credential in a newly allocated profile directory.
            committed = read_private_json(self.settings_path) or {}
            if committed.get("profiles", {}).get(name, {}).get("id") != identifier:
                credentials_path(context).unlink(missing_ok=True)
            raise
        return name

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
            _clear_private_env_keys(self.env_file, clear_keys)
        token_digest = journal.get("env_fields", {}).get("SHIFU_TOKEN")
        if token_digest:
            self._clear_legacy_backup_tokens({token_digest})
        self.migration_path.unlink(missing_ok=True)

    def migrate_legacy(self, process_env=None):
        """Migrate saved legacy inputs, never exported process credentials.

        A small journal fixes the new ID before any writes. New files are read
        back before settings commit, and cleanup is resumable after that commit.
        The process environment is intentionally neither read nor modified.
        """
        with self._configuration_lock():
            self._migrate_legacy()

    def _migrate_legacy(self, *, installer_identity=None):
        settings = read_private_json(self.settings_path)
        journal = read_private_json(self.migration_path)
        if journal and "installer_identity" in journal:
            recorded_identity = journal["installer_identity"]
            if installer_identity is not None and installer_identity != recorded_identity:
                raise ProfileError("Installer configuration changed during migration; retry the pending migration first.")
            installer_identity = recorded_identity
        if installer_identity is not None and (
            not isinstance(installer_identity, str) or len(installer_identity) != 64
            or any(character not in "0123456789abcdef" for character in installer_identity)
        ):
            raise ProfileError("Invalid installer migration identity.")
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
        if installer_identity is not None:
            journal["installer_identity"] = installer_identity
        write_private_json(self.migration_path, journal)
        # A retry reuses the staged ID, but removed or foreign legacy sources
        # must not activate files left behind by an interrupted earlier attempt.
        retained_paths = {path for path, _data in records}
        for path in (credentials_path(context), pending_auth_path(context)):
            if path not in retained_paths:
                path.unlink(missing_ok=True)
        for path, data in records:
            write_private_json(path, data)
            if read_private_json(path) != data:
                raise ProfileError("Could not verify migrated profile authorization state.")
        migrated_settings = {
            "schema_version": 2, "default_profile": "default",
            "profiles": {"default": {"id": identifier, "base_url": url}},
        }
        if installer_identity is not None:
            migrated_settings["installer_imports"] = {installer_identity: identifier}
        write_private_json(self.settings_path, migrated_settings)
        self._cleanup_migration(journal)
