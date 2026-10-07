"""Read public release settings from the exact source revision."""

from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import urlsplit

import tomllib

from . import source

SOURCE_TOOL_PATH = "tools/ai-shifu-skill-release"
CONFIG_PATH = f"{SOURCE_TOOL_PATH}/release.toml"
LEGACY_CONFIG_PATH = f"{SOURCE_TOOL_PATH}/publisher.toml"


@dataclass(frozen=True)
class ClawHubConfig:
    owner: str = "heshaofu2"
    endpoint: str = "https://clawhub.ai"
    package: str = "clawhub@latest"
    node_version: str = "22"


@dataclass(frozen=True)
class SkillHubConfig:
    endpoint: str = "https://api.skillhub.cn"
    cli_version: str = "2026.8.5"
    cli_url: str = (
        "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/"
        "install/skillhub-cli-2026.8.5.tar.gz"
    )
    cli_sha256: str = "3bbe2ba15ada2eb7a94a2b760fead83be5f4164ab28a6c8b0944dbc539f7e236"


@dataclass(frozen=True)
class WorkBuddyConfig:
    template_dir: str = "channels/workbuddy"


@dataclass(frozen=True)
class DoubaoConfig:
    profile: str = "channels/doubao/profile.json"
    workspace_dir: str = "channels/doubao/workspace"


@dataclass(frozen=True)
class ReleaseConfig:
    publisher: dict[str, str]
    clawhub: ClawHubConfig = field(default_factory=ClawHubConfig)
    skillhub: SkillHubConfig = field(default_factory=SkillHubConfig)
    workbuddy: WorkBuddyConfig = field(default_factory=WorkBuddyConfig)
    doubao: DoubaoConfig = field(default_factory=DoubaoConfig)


class ReleaseSource(Protocol):
    source_repository: str
    source_commit: str


def _table(value: object, location: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be a TOML table")
    return value


def _keys(table: dict, expected: set[str], location: str) -> None:
    unknown = set(table) - expected
    missing = expected - set(table)
    if unknown:
        raise ValueError(f"{location} contains unknown keys: {sorted(unknown)}")
    if missing:
        raise ValueError(f"{location} is missing required keys: {sorted(missing)}")


def _reject_credentials(table: dict, location: str = "release.toml") -> None:
    for key, value in table.items():
        normalized = key.lower().replace("-", "_")
        if re.search(
            r"(?:^|_)(?:token|secret|password|credential|credentials|api_key|"
            r"access_key|private_key)(?:$|_)",
            normalized,
        ):
            raise ValueError(f"{location}.{key} is a secret configuration key")
        if isinstance(value, dict):
            _reject_credentials(value, f"{location}.{key}")


def _text(table: dict, key: str, location: str) -> str:
    value = table[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location}.{key} must be a non-empty string")
    if value != value.strip() or any(ord(character) < 32 for character in value):
        raise ValueError(f"{location}.{key} contains whitespace or control characters")
    return value


def _url(value: str, location: str) -> str:
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as error:
        raise ValueError(f"{location} must be a valid HTTPS URL") from error
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
        or (port is not None and not 1 <= port <= 65535)
        or any(character.isspace() for character in value)
    ):
        raise ValueError(f"{location} must be an HTTPS URL without credentials")
    return value


def _channel_relative(value: str, location: str) -> PurePosixPath:
    relative = PurePosixPath(value)
    if (
        "\\" in value
        or relative.is_absolute()
        or ".." in relative.parts
        or len(relative.parts) < 2
        or relative.parts[0] != "channels"
    ):
        raise ValueError(f"{location} must stay inside channels/")
    return relative


def channel_path(exported_channels: Path, configured_path: str) -> Path:
    """Resolve a tool-relative asset against the selected source's exported channels."""
    relative = _channel_relative(configured_path, "Channel asset path")
    root = exported_channels.resolve()
    target = root.joinpath(*relative.parts[1:]).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Channel asset path escapes channels/")
    return target


def _publisher(table: object, origin: str) -> dict[str, str]:
    publisher = _table(table, f"{origin} publisher")
    _keys(publisher, {"name", "email"}, f"{origin} publisher")
    values = {}
    for key in ("name", "email"):
        value = _text(publisher, key, f"{origin} publisher")
        if "__PUBLISHER_" in value or value in {"your-name", "you@example.com"}:
            raise ValueError(f"{origin} publisher.{key} contains a placeholder")
        values[key] = value
    return values


def _parse(contents: str, tool_root: Path | None = None) -> ReleaseConfig:
    data = tomllib.loads(contents)
    _reject_credentials(data)
    _keys(data, {"publisher", "channels"}, "release.toml")
    publisher = _publisher(data["publisher"], "release.toml")
    channels = _table(data["channels"], "channels")
    _keys(channels, {"clawhub", "skillhub", "workbuddy", "doubao"}, "channels")

    clawhub = _table(channels["clawhub"], "channels.clawhub")
    _keys(clawhub, {"owner", "endpoint", "package", "node_version"}, "channels.clawhub")
    clawhub_values = {key: _text(clawhub, key, "channels.clawhub") for key in clawhub}
    if not re.fullmatch(r"[A-Za-z0-9_-]+", clawhub_values["owner"]):
        raise ValueError("channels.clawhub.owner must be a publisher handle")
    _url(clawhub_values["endpoint"], "channels.clawhub.endpoint")
    if not re.fullmatch(
        r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9.+_-]*",
        clawhub_values["package"],
    ):
        raise ValueError("channels.clawhub.package must be a versioned npm package")
    if not re.fullmatch(r"[1-9]\d*", clawhub_values["node_version"]):
        raise ValueError("channels.clawhub.node_version must be a Node major version")

    skillhub = _table(channels["skillhub"], "channels.skillhub")
    _keys(
        skillhub,
        {"endpoint", "cli_version", "cli_url", "cli_sha256"},
        "channels.skillhub",
    )
    skillhub_values = {
        key: _text(skillhub, key, "channels.skillhub") for key in skillhub
    }
    _url(skillhub_values["endpoint"], "channels.skillhub.endpoint")
    _url(skillhub_values["cli_url"], "channels.skillhub.cli_url")
    if not re.fullmatch(r"\d+\.\d+\.\d+", skillhub_values["cli_version"]):
        raise ValueError("channels.skillhub.cli_version must use X.Y.Z")
    if not re.fullmatch(r"[0-9a-f]{64}", skillhub_values["cli_sha256"]):
        raise ValueError("channels.skillhub.cli_sha256 must be a SHA-256 digest")

    workbuddy = _table(channels["workbuddy"], "channels.workbuddy")
    _keys(workbuddy, {"template_dir"}, "channels.workbuddy")
    template_dir = _text(workbuddy, "template_dir", "channels.workbuddy")
    doubao = _table(channels["doubao"], "channels.doubao")
    _keys(doubao, {"profile", "workspace_dir"}, "channels.doubao")
    profile = _text(doubao, "profile", "channels.doubao")
    workspace_dir = _text(doubao, "workspace_dir", "channels.doubao")
    for location, value in (
        ("channels.workbuddy.template_dir", template_dir),
        ("channels.doubao.profile", profile),
        ("channels.doubao.workspace_dir", workspace_dir),
    ):
        _channel_relative(value, location)
        if tool_root is not None:
            channel_path(tool_root / "channels", value)

    return ReleaseConfig(
        publisher=publisher,
        clawhub=ClawHubConfig(**clawhub_values),
        skillhub=SkillHubConfig(**skillhub_values),
        workbuddy=WorkBuddyConfig(template_dir=template_dir),
        doubao=DoubaoConfig(profile=profile, workspace_dir=workspace_dir),
    )


def load(path: Path) -> ReleaseConfig:
    """Read a complete public configuration and validate tool-relative asset paths."""
    path = Path(path).expanduser().resolve()
    return _parse(path.read_text(encoding="utf-8"), path.parent)


def _source_file(repo: Path, commit: str, path: str) -> str | None:
    # ls-tree only returns no entry when the file is absent; Git failures must
    # propagate so transport, revision, or permission errors cannot enable fallback.
    try:
        entry = source.run(
            "git", "ls-tree", "--name-only", commit, "--", path, cwd=repo
        )
        if not entry:
            return None
        return source.run("git", "show", f"{commit}:{path}", cwd=repo)
    except (subprocess.CalledProcessError, OSError) as error:
        raise ValueError(
            "Cannot read release configuration from the source commit"
        ) from error


def load_from_source(repo: Path, commit: str) -> ReleaseConfig:
    """Read exact-commit settings, adapting historical publisher-only releases."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise ValueError("Release configuration requires a full source commit SHA")
    contents = _source_file(repo, commit, CONFIG_PATH)
    if contents is not None:
        return _parse(contents)
    legacy = _source_file(repo, commit, LEGACY_CONFIG_PATH)
    if legacy is None:
        raise ValueError(
            "Missing release configuration: release.toml and legacy publisher.toml are absent"
        )
    data = tomllib.loads(legacy)
    _reject_credentials(data, "publisher.toml")
    _keys(data, {"publisher"}, "publisher.toml")
    return ReleaseConfig(publisher=_publisher(data["publisher"], "publisher.toml"))


def load_for_release(release: ReleaseSource) -> ReleaseConfig:
    """Read settings anchored to a verified release, never to the current checkout."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", release.source_commit):
        raise ValueError("Release configuration requires a full source commit SHA")
    with tempfile.TemporaryDirectory(prefix="ai-shifu-config-") as temporary:
        repo = Path(temporary) / "source"
        try:
            commit, _ = source.fetch_source(
                release.source_repository, repo, release.source_commit
            )
        except (subprocess.CalledProcessError, OSError) as error:
            raise ValueError(
                "Cannot fetch the release configuration's source commit"
            ) from error
        return load_from_source(repo, commit)
