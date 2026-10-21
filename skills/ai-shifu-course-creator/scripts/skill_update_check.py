#!/usr/bin/env python3
"""Fail-open Skill update checks backed by published GitHub Releases."""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests

SKILL_NAME = "ai-shifu-course-creator"
SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_ROOT / "SKILL.md"
GITHUB_RELEASES_URL = "https://github.com/ai-shifu/skills/releases"
MANIFEST_URL = "https://api.github.com/repos/ai-shifu/skills/releases/latest"

SCHEMA_VERSION = 1
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
LOOPBACK_MANIFEST_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
MAX_MANIFEST_BYTES = 64 * 1024
MAX_NOTES_CHARS = 500
RELEASE_TAG_PATTERN = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
VERSION_MANAGEMENT_STANDALONE = "standalone"
VERSION_MANAGEMENT_PLUGIN = "plugin"
AUTOMATIC_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
AUTOMATIC_FAILURE_DELAY_SECONDS = 5 * 60
AUTOMATIC_LOOKUP_TIMEOUT_SECONDS = 2


class ManifestError(ValueError):
    """The remote manifest is not safe to consume."""


def _validate_manifest_source_url(url: str, *, allow_loopback: bool) -> None:
    """Allow the official HTTPS source, or an explicit loopback-only dev source."""
    parsed = urlparse(url)
    if parsed.username is not None or parsed.password is not None:
        raise ManifestError("manifest URL must not contain credentials")
    if allow_loopback:
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in LOOPBACK_MANIFEST_HOSTS
        ):
            raise ManifestError("development manifest URL must use a loopback host")
        return
    if url != MANIFEST_URL:
        raise ManifestError("version source must use the official GitHub Releases endpoint")


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def parse_semver(value: object) -> tuple[int, int, int] | None:
    """Parse the deliberately small MAJOR.MINOR.PATCH subset used by Skills."""
    if not isinstance(value, str) or not SEMVER_PATTERN.fullmatch(value):
        return None
    try:
        major, minor, patch = (int(part) for part in value.split("."))
    except (TypeError, ValueError):
        return None
    return major, minor, patch


def read_skill_metadata(skill_md: Path = SKILL_MD) -> dict[str, str] | None:
    """Read scalar frontmatter and version fields inside the metadata mapping."""
    try:
        lines = skill_md.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None

    result: dict[str, str] = {}
    in_metadata = False
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        if not line.strip() or ":" not in line:
            continue
        if not line[0].isspace():
            key, value = line.split(":", 1)
            key = key.strip()
            in_metadata = key == "metadata"
            if key != "metadata":
                result[key] = value.strip().strip("\"'")
        elif in_metadata and line.startswith("  ") and not line.startswith("   "):
            key, value = line.strip().split(":", 1)
            if key in {"version", "version_management"} and key not in result:
                result[key] = value.strip().strip("\"'")
    return None


def validate_manifest(
    raw: object, expected_skill_name: str = SKILL_NAME
) -> dict[str, Any]:
    """Validate schema and cross-field invariants; return a shallow copy."""
    if not isinstance(raw, dict):
        raise ManifestError("manifest must be an object")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError("unsupported schema_version")
    if raw.get("skill_name") != expected_skill_name:
        raise ManifestError("skill_name mismatch")

    latest = parse_semver(raw.get("latest"))
    minimum = parse_semver(raw.get("min_supported"))
    if latest is None or minimum is None:
        raise ManifestError("invalid latest or min_supported")
    if minimum > latest:
        raise ManifestError("min_supported exceeds latest")

    notes = raw.get("notes")
    if not isinstance(notes, str) or len(notes) > MAX_NOTES_CHARS:
        raise ManifestError("invalid notes")

    if _parse_utc(raw.get("published_at")) is None:
        raise ManifestError("invalid published_at")

    update_url = raw.get("update_url")
    if not isinstance(update_url, str):
        raise ManifestError("invalid update_url")
    parsed_url = urlparse(update_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ManifestError("update_url must use HTTPS")

    return dict(raw)


def validate_github_release(raw: object) -> dict[str, Any]:
    """Normalize the latest published stable release into local update metadata."""
    if not isinstance(raw, dict):
        raise ManifestError("release must be an object")
    if raw.get("draft") is not False or raw.get("prerelease") is not False:
        raise ManifestError("release must be published and stable")
    tag = raw.get("tag_name")
    if not isinstance(tag, str) or not RELEASE_TAG_PATTERN.fullmatch(tag):
        raise ManifestError("release tag must use vMAJOR.MINOR.PATCH")
    update_url = f"{GITHUB_RELEASES_URL}/tag/{tag}"
    if raw.get("html_url") != update_url:
        raise ManifestError("release URL must match its official repository and tag")
    notes = raw.get("body")
    if notes is None:
        notes = ""
    if not isinstance(notes, str):
        raise ManifestError("release notes must be text")
    return validate_manifest({
        "schema_version": SCHEMA_VERSION,
        "skill_name": SKILL_NAME,
        "latest": tag[1:],
        # Releases do not declare an unsupported-version policy.
        "min_supported": "0.0.0",
        "notes": notes[:MAX_NOTES_CHARS],
        "published_at": raw.get("published_at"),
        "update_url": update_url,
    })


def determine_update(
    local_version: str,
    manifest: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    """Pure SemVer decision logic. The manifest must already be validated."""
    local = parse_semver(local_version)
    if local is None:
        raise ManifestError("invalid local version")

    minimum = parse_semver(manifest["min_supported"])
    latest = parse_semver(manifest["latest"])
    if minimum is None or latest is None:
        raise ManifestError("validated manifest contains invalid versions")

    if local < minimum:
        status = "update_required"
    elif local < latest:
        status = "update_recommended"
    else:
        status = "latest"

    return {
        "status": status,
        "skill_name": manifest["skill_name"],
        "local_version": local_version,
        "latest": manifest["latest"],
        "min_supported": manifest["min_supported"],
        "notes": manifest["notes"],
        "update_url": manifest["update_url"],
        "source": source,
    }


def _response_header(response: Any, name: str) -> str:
    headers = getattr(response, "headers", {})
    value = headers.get(name, "") if hasattr(headers, "get") else ""
    return value if isinstance(value, str) else ""


def _read_response_body(response: Any) -> bytes:
    length = _response_header(response, "Content-Length")
    if length:
        try:
            if int(length) > MAX_MANIFEST_BYTES:
                raise ManifestError("manifest response exceeds size limit")
        except ValueError as exc:
            raise ManifestError("invalid Content-Length") from exc

    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_content(chunk_size=8192):
        if not chunk:
            continue
        size += len(chunk)
        if size > MAX_MANIFEST_BYTES:
            raise ManifestError("manifest response exceeds size limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _close_response(response: Any) -> None:
    close = getattr(response, "close", None)
    if callable(close):
        close()


def fetch_manifest(
    *,
    manifest_url: str = MANIFEST_URL,
    allow_loopback: bool = False,
    http_get: Callable[..., Any] = requests.get,
) -> tuple[dict[str, Any], str]:
    """Fetch release metadata, or an explicit loopback development manifest."""
    _validate_manifest_source_url(manifest_url, allow_loopback=allow_loopback)

    headers = {"Accept": "application/vnd.github+json"}
    if allow_loopback:
        headers["Accept"] = "application/json"

    response = http_get(
        manifest_url,
        headers=headers,
        timeout=(3, 5),
        allow_redirects=True,
        stream=True,
    )
    final_url = getattr(response, "url", manifest_url) or manifest_url
    try:
        _validate_manifest_source_url(final_url, allow_loopback=allow_loopback)
    except ManifestError:
        _close_response(response)
        raise

    if response.status_code != 200:
        _close_response(response)
        raise ManifestError(f"unexpected HTTP status {response.status_code}")

    try:
        body = _read_response_body(response)
    finally:
        _close_response(response)
    try:
        raw = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("manifest is not valid UTF-8 JSON") from exc
    manifest = validate_manifest(raw) if allow_loopback else validate_github_release(raw)
    return manifest, "network"


def check_for_update(
    *,
    skill_md: Path = SKILL_MD,
    manifest_url: str = MANIFEST_URL,
    allow_loopback: bool = False,
    http_get: Callable[..., Any] = requests.get,
) -> dict[str, Any]:
    """Run the complete fail-open check and always return a public result."""
    try:
        metadata = read_skill_metadata(skill_md)
        if metadata is None:
            raise ManifestError("missing local metadata")
        version_management = metadata.get(
            "version_management", VERSION_MANAGEMENT_STANDALONE
        )
        if version_management == VERSION_MANAGEMENT_PLUGIN:
            return {"status": "check_skipped", "source": "plugin_managed"}
        if version_management != VERSION_MANAGEMENT_STANDALONE:
            return {
                "status": "check_skipped",
                "source": "invalid_version_management",
            }
        local_version = metadata.get("version", "")
        if parse_semver(local_version) is None:
            raise ManifestError("invalid local version")
        manifest, source = fetch_manifest(
            manifest_url=manifest_url,
            allow_loopback=allow_loopback,
            http_get=http_get,
        )
        return determine_update(
            local_version,
            manifest,
            source=source,
        )
    except Exception:
        return {"status": "check_skipped", "source": "none"}


@contextlib.contextmanager
def _automatic_check_lock(path: Path):
    """Use one persistent inode and an OS lock that releases on process exit."""
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "r+b") as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            acquire = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            release = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            acquire = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        acquire()
        try:
            yield
        finally:
            release()


def _write_automatic_state(path: Path, state: dict[str, Any]) -> None:
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".update-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.chmod(temporary, 0o600)
            json.dump(state, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def _read_automatic_state(path: Path, local_version: str, current_time: float) -> dict[str, Any]:
    empty = {
        "schema_version": 1, "source": MANIFEST_URL, "local_version": local_version,
        "last_attempt_at": 0, "last_success_at": 0,
        "retry_after_seconds": 0, "notified_versions": [],
    }
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return empty
    if not isinstance(state, dict) or type(state.get("schema_version")) is not int or any(
        state.get(key) != empty[key] for key in ("schema_version", "source", "local_version")
    ):
        return empty
    notified = state.get("notified_versions")
    if not isinstance(notified, list) or any(parse_semver(version) is None for version in notified):
        return empty
    reset_schedule = {**empty, "notified_versions": notified}
    for key in ("last_attempt_at", "last_success_at", "retry_after_seconds"):
        value = state.get(key)
        try:
            valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
        except OverflowError:
            valid = False
        if not valid:
            return reset_schedule
    if (
        state["last_attempt_at"] > current_time or state["last_success_at"] > current_time
        or state["last_success_at"] > state["last_attempt_at"]
    ):
        return reset_schedule
    return {key: state[key] for key in empty}


def _server_retry_delay(response: Any) -> float:
    """Keep rate-limit hints internal to the automatic worker."""
    if response.status_code not in {403, 429}:
        return 0
    current_time = datetime.now(timezone.utc).timestamp()
    waits = [0.0]
    retry_after = _response_header(response, "Retry-After")
    try:
        waits.append(float(retry_after))
    except ValueError:
        try:
            waits.append(parsedate_to_datetime(retry_after).timestamp() - current_time)
        except (TypeError, ValueError, OverflowError):
            pass
    try:
        waits.append(float(_response_header(response, "X-RateLimit-Reset")) - current_time)
    except ValueError:
        pass
    return max(wait for wait in waits if math.isfinite(wait))


def _automatic_check_worker(skill_md: Path) -> dict[str, Any]:
    retry_after_seconds = 0.0

    def get(url, **kwargs):
        nonlocal retry_after_seconds
        response = requests.get(url, **kwargs)
        final_url = getattr(response, "url", MANIFEST_URL) or MANIFEST_URL
        if final_url == MANIFEST_URL:
            retry_after_seconds = _server_retry_delay(response)
        return response

    return {
        "result": check_for_update(skill_md=skill_md, http_get=get),
        "retry_after_seconds": retry_after_seconds,
    }


def _run_automatic_check(*, skill_md: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--automatic-worker", str(skill_md)],
        capture_output=True, text=True, timeout=AUTOMATIC_LOOKUP_TIMEOUT_SECONDS,
        check=True,
    )
    return json.loads(completed.stdout)


def automatic_check_for_update(
    state_dir: Path,
    *,
    skill_md: Path = SKILL_MD,
    now: datetime | None = None,
    run_check: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Return a newly discovered update once; all automatic failures stay quiet."""
    try:
        metadata = read_skill_metadata(skill_md)
        if not metadata or metadata.get("name") != SKILL_NAME or metadata.get(
            "version_management", VERSION_MANAGEMENT_STANDALONE
        ) != VERSION_MANAGEMENT_STANDALONE:
            return None
        local_version = metadata.get("version", "")
        local = parse_semver(local_version)
        if local is None:
            return None
        current_time = (now or datetime.now(timezone.utc)).timestamp()
        directory = Path(state_dir) / "update-check"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        identity = hashlib.sha256(f"{MANIFEST_URL}\n{local_version}".encode()).hexdigest()
        state_path = directory / f"{identity}.json"
        with _automatic_check_lock(directory / f"{identity}.lock"):
            state = _read_automatic_state(state_path, local_version, current_time)
            if state["last_success_at"] and current_time - state["last_success_at"] < AUTOMATIC_CHECK_INTERVAL_SECONDS:
                return None
            if current_time - state["last_attempt_at"] < state["retry_after_seconds"]:
                return None
            # Verify persistence before networking and recover promptly after a crash.
            state["last_attempt_at"] = current_time
            state["retry_after_seconds"] = AUTOMATIC_FAILURE_DELAY_SECONDS
            _write_automatic_state(state_path, state)
            try:
                outcome = (run_check or _run_automatic_check)(skill_md=skill_md)
            except Exception:
                state["last_attempt_at"] = (now or datetime.now(timezone.utc)).timestamp()
                _write_automatic_state(state_path, state)
                return None
            state["last_attempt_at"] = (now or datetime.now(timezone.utc)).timestamp()
            outcome = outcome if isinstance(outcome, dict) else {}
            result = outcome.get("result", outcome)
            result = result if isinstance(result, dict) else {}
            latest = parse_semver(result.get("latest"))
            minimum = parse_semver(result.get("min_supported"))
            expected_status = (
                "update_required" if minimum is not None and local < minimum
                else "update_recommended" if latest is not None and local < latest
                else "latest"
            )
            successful = (
                result.get("status") == expected_status
                and result.get("source") == "network"
                and result.get("skill_name") == SKILL_NAME
                and result.get("local_version") == local_version
                and latest is not None and minimum is not None and minimum <= latest
                and result.get("update_url") == f"{GITHUB_RELEASES_URL}/tag/v{result.get('latest')}"
            )
            if not successful:
                wait = outcome.get("retry_after_seconds", 0)
                if isinstance(wait, (int, float)) and not isinstance(wait, bool) and math.isfinite(wait):
                    state["retry_after_seconds"] = max(AUTOMATIC_FAILURE_DELAY_SECONDS, wait)
                    _write_automatic_state(state_path, state)
                return None
            state["last_success_at"] = state["last_attempt_at"]
            state["retry_after_seconds"] = 0
            notify = latest > local and result["latest"] not in state["notified_versions"]
            if notify:
                state["notified_versions"].append(result["latest"])
            _write_automatic_state(state_path, state)
            return result if notify else None
    except Exception:
        return None


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--automatic-worker":
    print(json.dumps(_automatic_check_worker(Path(sys.argv[2])), separators=(",", ":")))
