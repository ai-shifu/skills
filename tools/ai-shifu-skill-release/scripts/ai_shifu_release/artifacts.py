"""Create deterministic archives and verify shared artifact integrity."""

from __future__ import annotations

import hashlib
import re
import shutil
import stat
import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from ai_shifu_release.skill_metadata import render_skill_variant

EXCLUDED_NAMES = {
    ".DS_Store",
    ".git",
    ".gitignore",
    ".idea",
    ".update-check.json",
    ".update-check.dev.json",
    ".vscode",
    "__pycache__",
    "design",
    "dist",
    "evals",
}


SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
)


ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


RELEASE_SCHEMA_VERSION = 6


# Order feeds release_sha256; changing it breaks verification of existing releases.
CHANNEL_ORDER = ("clawhub", "skillhub", "workbuddy", "doubao")


def is_excluded(path: PurePosixPath) -> bool:
    return any(
        part in EXCLUDED_NAMES
        or (part.startswith(".env") and part != ".env.example")
        or part.endswith(".pyc")
        for part in path.parts
    )


def copy_tree(
    source: Path, destination: Path, *, ignored: set[str] | None = None
) -> None:
    ignored = ignored or set()
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        posix = PurePosixPath(relative.as_posix())
        if is_excluded(posix) or posix.parts[0] in ignored or item.is_symlink():
            continue
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def iter_files(root: Path):
    return (path for path in sorted(root.rglob("*")) if path.is_file())


def scan_tree(root: Path) -> None:
    for path in iter_files(root):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if is_excluded(relative):
            raise ValueError(f"Forbidden file in artifact: {relative}")
        content = path.read_bytes()
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            raise ValueError(f"Possible secret in artifact: {relative}")


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in iter_files(root):
        relative = path.relative_to(root).as_posix()
        mode = stat.S_IMODE(path.stat().st_mode)
        digest.update(f"{relative}\0{mode:o}\0".encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def directory_contents(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in iter_files(root)
    }


def directory_manifest(root: Path) -> dict[str, dict[str, str]]:
    return {
        path.relative_to(root).as_posix(): {
            "mode": f"{stat.S_IMODE(path.stat().st_mode):o}",
            "sha256": file_hash(path),
        }
        for path in iter_files(root)
    }


def manifest_tree_hash(manifest: dict[str, dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(manifest):
        item = manifest[relative]
        digest.update(f"{relative}\0{item['mode']}\0".encode())
        digest.update(bytes.fromhex(item["sha256"]))
    return digest.hexdigest()


def zip_subtree_contents(path: Path, root: str) -> dict[str, bytes]:
    verify_zip(path)
    prefix = f"{root.rstrip('/')}/"
    contents: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if not info.filename.startswith(prefix):
                raise ValueError(f"ZIP member outside {prefix}: {info.filename}")
            if info.is_dir():
                continue
            relative = info.filename[len(prefix) :]
            if relative:
                contents[relative] = archive.read(info)
    return contents


def expected_variant_contents(
    canonical: dict[str, bytes],
    updates: dict[str, str],
    source: str,
    *,
    top_level_version: str = "",
) -> dict[str, bytes]:
    expected = dict(canonical)
    skill_text = expected["SKILL.md"].decode("utf-8")
    expected["SKILL.md"] = render_skill_variant(
        skill_text, updates, source, top_level_version=top_level_version
    ).encode("utf-8")
    return expected


def assert_contents_equal(
    actual: dict[str, bytes], expected: dict[str, bytes], label: str
) -> None:
    if actual.keys() != expected.keys():
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        raise ValueError(f"{label} file set mismatch: missing={missing}, extra={extra}")
    changed = [name for name in sorted(expected) if actual[name] != expected[name]]
    if changed:
        raise ValueError(f"{label} content mismatch: {changed}")


def write_zip(source: Path, output: Path, root_name: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in iter_files(source):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(f"{root_name}/{relative}", ZIP_TIMESTAMP)
            mode = stat.S_IMODE(path.stat().st_mode)
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def verify_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names: set[str] = set()
        for info in archive.infolist():
            name = info.filename
            if name in names:
                raise ValueError(f"Duplicate ZIP member: {name}")
            names.add(name)
            relative = PurePosixPath(name)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or is_excluded(relative)
            ):
                raise ValueError(f"Forbidden ZIP member in {path.name}: {name}")
            mode = info.external_attr >> 16
            if info.is_dir():
                if not stat.S_ISDIR(mode):
                    raise ValueError(f"Non-directory ZIP entry: {name}")
                continue
            if not stat.S_ISREG(mode):
                raise ValueError(f"Non-file ZIP entry: {name}")
            content = archive.read(info)
            if any(pattern.search(content) for pattern in SECRET_PATTERNS):
                raise ValueError(f"Possible secret in {path.name}: {name}")


def artifact_hashes(record: dict) -> list[str]:
    if "tree_sha256" in record:
        return [record["tree_sha256"], record["archive_sha256"]]
    return [record["sha256"]]


def release_hash(hashes: Iterable[str]) -> str:
    """Hash artifact digests in the release's canonical channel order."""
    return hashlib.sha256("\0".join(hashes).encode()).hexdigest()


def artifact_path(release_dir: Path, relative: str) -> Path:
    path = (release_dir / relative).resolve()
    if release_dir.resolve() not in path.parents:
        raise ValueError(f"Artifact escapes release directory: {relative}")
    return path
