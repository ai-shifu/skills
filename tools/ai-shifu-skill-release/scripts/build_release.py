#!/usr/bin/env python3
"""Build and verify AI-Shifu skill release artifacts."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tomllib
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Protocol

from scripts import doubao_package


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
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
SOURCE_REPOSITORY = "https://github.com/ai-shifu/skills.git"
SOURCE_REF = "main"
RELEASE_SCHEMA_VERSION = 4
# Order feeds release_sha256; changing it breaks verification of existing releases.
CHANNEL_ORDER = ("clawhub", "skillhub", "workbuddy", "qclaw", "doubao")


class BuildOptions(Protocol):
    source_repo_url: str
    skill_name: str
    output: str


def channel_frontmatter_overrides(channel: str, skill_name: str, display_name: str) -> dict[str, str]:
    if channel == "clawhub":
        return {}
    if channel == "skillhub":
        return {"slug": skill_name, "displayName": display_name}
    if channel in {"workbuddy", "qclaw"}:
        return {"version_management": "plugin"}
    raise ValueError(f"Unsupported channel: {channel}")


def run(*args: str, cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _git_metadata(project: Path):
    """Best-effort builder provenance. Degrades to None outside a git work tree
    so the skill can build when copied into a plain (non-git) directory. These
    fields are provenance-only and never feed release_sha256."""
    try:
        commit = run("git", "rev-parse", "HEAD^{commit}", cwd=project)
        remote = run("git", "remote", "get-url", "origin", cwd=project)
        dirty = bool(run("git", "status", "--porcelain", cwd=project))
        return commit, remote, dirty
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None, None, None


def load_publisher(project: Path) -> dict | None:
    """Publisher identity for channel packages. Environment variables win over
    publisher.toml at the skill root; returns None when neither is set."""
    name = os.environ.get("AISHIFU_PUBLISHER_NAME", "")
    email = os.environ.get("AISHIFU_PUBLISHER_EMAIL", "")
    if name:
        return {"name": name, "email": email}
    config_path = project / "publisher.toml"
    if config_path.is_file():
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        publisher = config.get("publisher", {})
        if publisher.get("name"):
            return {"name": publisher["name"], "email": publisher.get("email", "")}
    return None


def is_excluded(path: PurePosixPath) -> bool:
    return any(
        part in EXCLUDED_NAMES
        or (part.startswith(".env") and part != ".env.example")
        or part.endswith(".pyc")
        for part in path.parts
    )


def split_skill_document(text: str, source: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError(f"Missing YAML frontmatter: {source}")
    delimiter = "\n---\n"
    end = text.find(delimiter, 4)
    if end < 0:
        raise ValueError(f"Unclosed YAML frontmatter: {source}")
    return text[4:end], text[end + len(delimiter):]


def parse_frontmatter(frontmatter: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip("'\"")
    return fields


def read_skill_document(skill_file: Path) -> tuple[str, str]:
    text = skill_file.read_bytes().decode("utf-8")
    return split_skill_document(text, str(skill_file))


def read_frontmatter(skill_file: Path) -> dict[str, str]:
    frontmatter, _ = read_skill_document(skill_file)
    fields = parse_frontmatter(frontmatter)
    version = fields.get("version", "")
    if not SEMVER.fullmatch(version):
        raise ValueError(f"Invalid SemVer in {skill_file}: {version!r}")
    if fields.get("version_management") not in {"standalone", "plugin"}:
        raise ValueError(f"Invalid version_management in {skill_file}")
    return fields


def format_frontmatter_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]*", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def update_skill_frontmatter(text: str, updates: dict[str, str], source: str) -> str:
    frontmatter, body = split_skill_document(text, source)
    lines = frontmatter.split("\n")
    for key, value in updates.items():
        pattern = re.compile(rf"^{re.escape(key)}:\s*.*$")
        indexes = [index for index, line in enumerate(lines) if pattern.fullmatch(line)]
        if len(indexes) > 1:
            raise ValueError(f"Duplicate {key} in YAML frontmatter: {source}")
        replacement = f"{key}: {format_frontmatter_value(value)}"
        if indexes:
            lines[indexes[0]] = replacement
        else:
            lines.append(replacement)
    updated_frontmatter = "\n".join(lines)
    updated = f"---\n{updated_frontmatter}\n---\n{body}"
    _, updated_body = split_skill_document(updated, source)
    if updated_body != body:
        raise ValueError(f"SKILL.md body changed while updating frontmatter: {source}")
    return updated


def build_skill_variant(source: Path, destination: Path, updates: dict[str, str]) -> None:
    shutil.copytree(source, destination)
    if not updates:
        return
    skill_file = destination / "SKILL.md"
    text = skill_file.read_bytes().decode("utf-8")
    updated = update_skill_frontmatter(text, updates, str(skill_file))
    skill_file.write_bytes(updated.encode("utf-8"))


def export_skill(repo: Path, commit: str, skill_name: str, destination: Path) -> None:
    archive = subprocess.run(
        ["git", "archive", "--format=tar", f"{commit}:skills/{skill_name}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        for member in tar.getmembers():
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or is_excluded(relative):
                continue
            target = destination.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tar.extractfile(member)
                if source is None:
                    raise ValueError(f"Cannot extract {member.name}")
                target.write_bytes(source.read())
                target.chmod(member.mode)
            else:
                raise ValueError(f"Unsupported archive member: {member.name}")


def fetch_source(repository: str, destination: Path) -> tuple[str, str]:
    destination.mkdir(parents=True)
    run("git", "init", "--quiet", cwd=destination)
    run("git", "remote", "add", "origin", repository, cwd=destination)
    run("git", "fetch", "--quiet", "--depth=1", "origin", f"refs/heads/{SOURCE_REF}", cwd=destination)
    commit = run("git", "rev-parse", "FETCH_HEAD^{commit}", cwd=destination)
    remote = run("git", "remote", "get-url", "origin", cwd=destination)
    return commit, remote


def copy_tree(source: Path, destination: Path, *, ignored: set[str] | None = None) -> None:
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


def _workbuddy_localized(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"WorkBuddy {field} must contain en and zh")
    localized = value
    for language in ("en", "zh"):
        if not isinstance(localized.get(language), str) or not localized[language].strip():
            raise ValueError(f"WorkBuddy {field}.{language} must be a non-empty string")
    return localized


def _workbuddy_reference(contents: dict[str, bytes], reference: object, field: str) -> str:
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError(f"WorkBuddy {field} must be a non-empty path")
    relative = PurePosixPath(reference.removeprefix("./"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"WorkBuddy {field} must stay inside the package")
    path = relative.as_posix()
    if path not in contents:
        raise ValueError(f"WorkBuddy {field} does not exist: {path}")
    return path


def _workbuddy_agent_localized(frontmatter: str, field: str) -> dict[str, str]:
    lines = frontmatter.splitlines()
    marker = f"{field}:"
    try:
        start = lines.index(marker)
    except ValueError as exc:
        raise ValueError(f"WorkBuddy agent {field} is required") from exc
    localized: dict[str, str] = {}
    for line in lines[start + 1:]:
        if line and not line[0].isspace():
            break
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key in {"en", "zh"}:
            localized[key] = value.strip().strip("'\"")
    for language in ("en", "zh"):
        if not localized.get(language):
            raise ValueError(
                f"WorkBuddy agent {field}.{language} must be a non-empty string"
            )
    return localized


def validate_workbuddy_package_contents(
    contents: dict[str, bytes], expected_version: str
) -> None:
    config_path = ".codebuddy-plugin/plugin.json"
    if any(path.startswith(".workbuddy-plugin/") for path in contents):
        raise ValueError("WorkBuddy legacy .workbuddy-plugin directory is not allowed")
    if config_path not in contents:
        raise ValueError(f"WorkBuddy config is missing: {config_path}")
    if "README.md" not in contents:
        raise ValueError("WorkBuddy README.md is required")

    try:
        plugin = json.loads(contents[config_path].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("WorkBuddy plugin.json is not valid UTF-8 JSON") from exc
    if not isinstance(plugin, dict):
        raise ValueError("WorkBuddy plugin.json must contain an object")

    required_strings = (
        "name",
        "version",
        "description",
        "expertType",
        "agentName",
        "avatar",
        "categoryId",
        "plugin",
    )
    for field in required_strings:
        if not isinstance(plugin.get(field), str) or not plugin[field].strip():
            raise ValueError(f"WorkBuddy {field} must be a non-empty string")
    if plugin["version"] != expected_version or not SEMVER.fullmatch(plugin["version"]):
        raise ValueError("WorkBuddy version must match the release version")
    if plugin["expertType"] != "agent":
        raise ValueError("WorkBuddy expertType must be agent")
    if plugin["plugin"] != plugin["name"]:
        raise ValueError("WorkBuddy plugin must match name")
    if plugin["categoryId"] != "15-Education":
        raise ValueError("WorkBuddy AI-Shifu categoryId must be 15-Education")

    author = plugin.get("author")
    if not isinstance(author, dict):
        raise ValueError("WorkBuddy author must contain name and email")
    for field in ("name", "email"):
        if not isinstance(author.get(field), str) or not author[field].strip():
            raise ValueError(f"WorkBuddy author.{field} must be a non-empty string")

    for field in ("displayName", "profession", "displayDescription", "defaultInitPrompt"):
        _workbuddy_localized(plugin.get(field), field)
    description_length = len(plugin["displayDescription"]["zh"])
    if not 40 <= description_length <= 50:
        raise ValueError("WorkBuddy displayDescription.zh must contain 40-50 characters")

    tags = plugin.get("tags")
    if not isinstance(tags, list) or len(tags) != 3:
        raise ValueError("WorkBuddy tags must contain exactly 3 items")
    for index, tag in enumerate(tags):
        _workbuddy_localized(tag, f"tags[{index}]")

    quick_prompts = plugin.get("quickPrompts")
    if not isinstance(quick_prompts, list) or len(quick_prompts) != 3:
        raise ValueError("WorkBuddy quickPrompts must contain exactly 3 items")
    for index, prompt in enumerate(quick_prompts):
        _workbuddy_localized(prompt, f"quickPrompts[{index}]")
    if plugin["defaultInitPrompt"] != quick_prompts[0]:
        raise ValueError("WorkBuddy defaultInitPrompt must match quickPrompts[0]")

    agents = plugin.get("agents")
    if not isinstance(agents, list) or not agents:
        raise ValueError("WorkBuddy agents must contain at least one path")
    agent_paths = [
        _workbuddy_reference(contents, reference, f"agents[{index}]")
        for index, reference in enumerate(agents)
    ]
    primary_agent = f"agents/{plugin['agentName']}.md"
    if primary_agent not in agent_paths:
        raise ValueError("WorkBuddy agentName must match an agents path")

    skills = plugin.get("skills", [])
    if not isinstance(skills, list):
        raise ValueError("WorkBuddy skills must be a path list")
    for index, reference in enumerate(skills):
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError(f"WorkBuddy skills[{index}] must be a non-empty path")
        relative = PurePosixPath(reference.removeprefix("./"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"WorkBuddy skills[{index}] must stay inside the package")
        prefix = f"{relative.as_posix().rstrip('/')}/"
        if not any(path.startswith(prefix) for path in contents):
            raise ValueError(f"WorkBuddy skills[{index}] does not exist: {relative}")

    avatar_path = _workbuddy_reference(contents, plugin["avatar"], "avatar")
    avatar = contents[avatar_path]
    if len(avatar) > 500 * 1024:
        raise ValueError("WorkBuddy avatar must not exceed 500KB")
    if len(avatar) < 24 or avatar[:8] != b"\x89PNG\r\n\x1a\n" or avatar[12:16] != b"IHDR":
        raise ValueError("WorkBuddy avatar must be a PNG")
    width = int.from_bytes(avatar[16:20], "big")
    height = int.from_bytes(avatar[20:24], "big")
    if (width, height) != (512, 512):
        raise ValueError("WorkBuddy avatar must be 512x512 pixels")

    try:
        agent_text = contents[primary_agent].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("WorkBuddy agent must be UTF-8 Markdown") from exc
    agent_frontmatter, _ = split_skill_document(agent_text, primary_agent)
    agent_fields = parse_frontmatter(agent_frontmatter)
    if agent_fields.get("name") != plugin["agentName"]:
        raise ValueError("WorkBuddy agent name must match agentName")
    if not agent_fields.get("description"):
        raise ValueError("WorkBuddy agent description is required")
    if "tools" in agent_fields:
        raise ValueError("WorkBuddy agent must not declare tools")
    for field in ("displayName", "profession"):
        if _workbuddy_agent_localized(agent_frontmatter, field) != plugin[field]:
            raise ValueError(f"WorkBuddy agent {field} must match plugin.json")


def validate_workbuddy_package(root: Path, expected_version: str) -> None:
    validate_workbuddy_package_contents(directory_contents(root), expected_version)


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
    prefix = f"{root.rstrip('/')}/"
    contents: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.startswith(prefix):
                continue
            relative = info.filename[len(prefix):]
            if relative:
                contents[relative] = archive.read(info)
    return contents


def expected_variant_contents(
    canonical: dict[str, bytes],
    updates: dict[str, str],
    source: str,
) -> dict[str, bytes]:
    expected = dict(canonical)
    skill_text = expected["SKILL.md"].decode("utf-8")
    expected["SKILL.md"] = update_skill_frontmatter(skill_text, updates, source).encode("utf-8")
    return expected


def assert_contents_equal(actual: dict[str, bytes], expected: dict[str, bytes], label: str) -> None:
    if actual.keys() != expected.keys():
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        raise ValueError(f"{label} file set mismatch: missing={missing}, extra={extra}")
    changed = [name for name in sorted(expected) if actual[name] != expected[name]]
    if changed:
        raise ValueError(f"{label} content mismatch: {changed}")


def write_zip(source: Path, output: Path, root_name: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in iter_files(source):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(f"{root_name}/{relative}", ZIP_TIMESTAMP)
            mode = stat.S_IMODE(path.stat().st_mode)
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def verify_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts or is_excluded(relative):
                raise ValueError(f"Forbidden ZIP member in {path.name}: {name}")
            content = archive.read(name)
            if any(pattern.search(content) for pattern in SECRET_PATTERNS):
                raise ValueError(f"Possible secret in {path.name}: {name}")


@dataclass(frozen=True)
class BuildContext:
    source_skill: Path
    source_skills: dict[str, Path]
    source_commit: str
    channels: Path
    stage: Path
    skill_name: str
    version: str
    display_name: str

    @property
    def artifacts(self) -> Path:
        return self.stage / "artifacts"

    def record_path(self, path: Path) -> str:
        return path.relative_to(self.stage).as_posix()


def build_registry_artifact(channel: str, context: BuildContext) -> dict:
    overrides = channel_frontmatter_overrides(channel, context.skill_name, context.display_name)
    directory = context.artifacts / channel / context.skill_name
    build_skill_variant(context.source_skill, directory, overrides)
    scan_tree(directory)
    archive = context.artifacts / channel / f"{context.skill_name}-{context.version}.zip"
    write_zip(directory, archive, context.skill_name)
    record = {
        "directory": context.record_path(directory),
        "tree_sha256": tree_hash(directory),
        "archive": context.record_path(archive),
        "archive_sha256": file_hash(archive),
        "archive_root": context.skill_name,
        "version_management": "standalone",
    }
    if overrides:
        record["frontmatter_overrides"] = overrides
    return record


def build_workbuddy_artifact(channel: str, context: BuildContext) -> dict:
    overrides = channel_frontmatter_overrides(channel, context.skill_name, context.display_name)
    root_name = f"workbuddy-ai-shifu-{context.version}"
    stage_dir = context.artifacts / channel / root_name
    copy_tree(context.channels / "workbuddy", stage_dir, ignored={"skills", "build-zip.sh"})
    copy_tree(context.channels / "avatars", stage_dir / "avatars")
    stage_plugin_path = stage_dir / ".codebuddy-plugin/plugin.json"
    stage_plugin = json.loads(stage_plugin_path.read_text(encoding="utf-8"))
    stage_plugin["version"] = context.version
    publisher = load_publisher(context.channels.parent)
    if publisher:
        stage_plugin["author"] = publisher
    else:
        print(
            "warning: no publisher configured (publisher.toml or AISHIFU_PUBLISHER_NAME); "
            "workbuddy plugin.json keeps its placeholder author",
            file=sys.stderr,
        )
    stage_plugin_path.write_text(
        json.dumps(stage_plugin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    build_skill_variant(context.source_skill, stage_dir / "skills" / context.skill_name, overrides)
    validate_workbuddy_package(stage_dir, context.version)
    scan_tree(stage_dir)
    archive = context.artifacts / channel / f"{root_name}.zip"
    write_zip(stage_dir, archive, root_name)
    return {
        "archive": context.record_path(archive),
        "sha256": file_hash(archive),
        "version": context.version,
        "embedded_skill_root": f"{root_name}/skills/{context.skill_name}",
        "frontmatter_overrides": overrides,
    }


def build_qclaw_artifact(channel: str, context: BuildContext) -> dict:
    overrides = channel_frontmatter_overrides(channel, context.skill_name, context.display_name)
    root_name = f"qclaw-ai-shifu-{context.version}"
    stage_dir = context.artifacts / channel / root_name
    stage_dir.mkdir(parents=True)
    for filename in ("AGENTS.md", "SOUL.md", "IDENTITY.md"):
        shutil.copy2(context.channels / "qclaw" / filename, stage_dir / filename)
    build_skill_variant(context.source_skill, stage_dir / "skills" / context.skill_name, overrides)
    scan_tree(stage_dir)
    archive = context.artifacts / channel / f"{root_name}.zip"
    write_zip(stage_dir, archive, root_name)
    return {
        "archive": context.record_path(archive),
        "sha256": file_hash(archive),
        "version": context.version,
        "embedded_skill_root": f"{root_name}/skills/{context.skill_name}",
        "frontmatter_overrides": overrides,
    }


def build_doubao_artifact(channel: str, context: BuildContext) -> dict:
    channel_root = context.channels / channel
    profile = doubao_package.load_profile(channel_root / "profile.json")
    if context.skill_name != profile["primary_skill"]:
        raise ValueError(
            f"Doubao profile supports {profile['primary_skill']}, not {context.skill_name}"
        )
    root_name = f"doubao-ai-shifu-{context.version}"
    stage_dir = context.artifacts / channel / root_name
    workspace = stage_dir / "workspace"
    stage_dir.mkdir(parents=True)
    shutil.copy2(channel_root / "avatar.png", stage_dir / "avatar.png")
    copy_tree(channel_root / "workspace", workspace)

    source_documents: dict[str, tuple[str, str]] = {}
    source_frontmatter: dict[str, dict[str, str]] = {}
    for skill in profile["skills"]:
        name = skill["name"]
        frontmatter, body = read_skill_document(
            context.source_skills[name] / "SKILL.md"
        )
        metadata = parse_frontmatter(frontmatter)
        doubao_package.skill_overrides(skill, metadata)
        source_documents[name] = (frontmatter, body)
        source_frontmatter[name] = metadata

    (stage_dir / "agent.yml").write_text(
        doubao_package.render_agent_yml(profile, source_frontmatter), encoding="utf-8"
    )
    (stage_dir / "README.md").write_text(
        doubao_package.render_readme(profile), encoding="utf-8"
    )

    embedded_skills = {}
    for skill in profile["skills"]:
        name = skill["name"]
        source = context.source_skills[name]
        destination = workspace / "skills" / name
        frontmatter, source_body = source_documents[name]
        metadata = source_frontmatter[name]
        overrides = doubao_package.skill_overrides(skill, metadata)
        source_skill_bytes = (source / "SKILL.md").read_bytes()
        build_skill_variant(source, destination, overrides)
        assert_contents_equal(
            directory_contents(destination),
            expected_variant_contents(
                directory_contents(source), overrides, f"Doubao {name}/SKILL.md"
            ),
            f"doubao {name} directory",
        )
        embedded_skills[name] = {
            "root": f"{root_name}/workspace/skills/{name}",
            "source_commit": context.source_commit,
            "source_tree_sha256": tree_hash(source),
            "source_files": directory_manifest(source),
            "source_skill_sha256": content_hash(source_skill_bytes),
            "source_frontmatter": frontmatter,
            "body_sha256": content_hash(source_body.encode("utf-8")),
            "tree_sha256": tree_hash(destination),
            "frontmatter_overrides": overrides,
        }

    scan_tree(stage_dir)
    doubao_package.validate_package(stage_dir, profile, source_frontmatter)
    archive = context.artifacts / channel / f"{root_name}.zip"
    write_zip(stage_dir, archive, root_name)
    return {
        "directory": context.record_path(stage_dir),
        "tree_sha256": tree_hash(stage_dir),
        "archive": context.record_path(archive),
        "archive_sha256": file_hash(archive),
        "archive_root": root_name,
        "version": context.version,
        "embedded_skills": embedded_skills,
    }


CHANNEL_BUILDERS: dict[str, Callable[[str, BuildContext], dict]] = {
    "clawhub": build_registry_artifact,
    "skillhub": build_registry_artifact,
    "workbuddy": build_workbuddy_artifact,
    "qclaw": build_qclaw_artifact,
    "doubao": build_doubao_artifact,
}


def artifact_hashes(record: dict) -> list[str]:
    if "tree_sha256" in record:
        return [record["tree_sha256"], record["archive_sha256"]]
    return [record["sha256"]]


def build(args: BuildOptions) -> Path:
    project = Path(__file__).resolve().parents[1]
    output_root = Path(args.output).expanduser().resolve()

    with tempfile.TemporaryDirectory(prefix="ai-shifu-build-") as temporary:
        temporary_root = Path(temporary)
        source_repo = temporary_root / "github-source"
        commit, remote = fetch_source(args.source_repo_url, source_repo)
        source_skill = temporary_root / "source-skill"
        export_skill(source_repo, commit, args.skill_name, source_skill)
        profile = doubao_package.load_profile(project / "channels/doubao/profile.json")
        if args.skill_name != profile["primary_skill"]:
            raise ValueError(
                f"Doubao profile supports {profile['primary_skill']}, not {args.skill_name}"
            )
        source_skills = {args.skill_name: source_skill}
        for skill in profile["skills"]:
            name = skill["name"]
            if name in source_skills:
                continue
            companion = temporary_root / "source-skills" / name
            export_skill(source_repo, commit, name, companion)
            source_skills[name] = companion
        metadata = read_frontmatter(source_skill / "SKILL.md")
        if metadata["version_management"] != "standalone":
            raise ValueError("Canonical skill must use version_management: standalone")
        display_name = metadata.get("name", "").strip()
        if not display_name:
            raise ValueError("Canonical skill must define name")

        source_skill_bytes = (source_skill / "SKILL.md").read_bytes()
        _, source_body = split_skill_document(source_skill_bytes.decode("utf-8"), "GitHub SKILL.md")
        context = BuildContext(
            source_skill=source_skill,
            source_skills=source_skills,
            source_commit=commit,
            channels=project / "channels",
            stage=temporary_root / "release",
            skill_name=args.skill_name,
            version=metadata["version"],
            display_name=display_name,
        )
        records = {channel: CHANNEL_BUILDERS[channel](channel, context) for channel in CHANNEL_ORDER}

        release_hashes = [digest for channel in CHANNEL_ORDER for digest in artifact_hashes(records[channel])]
        release_sha = hashlib.sha256("\0".join(release_hashes).encode()).hexdigest()
        release_id = f"{args.skill_name}-{context.version}-{commit[:7]}-{release_sha[:7]}"
        builder_commit, builder_remote, builder_dirty = _git_metadata(project)
        stage = context.stage
        report = {
            "schema_version": RELEASE_SCHEMA_VERSION,
            "release_id": release_id,
            "release_sha256": release_sha,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "source": {"repository": remote, "ref": SOURCE_REF, "commit": commit},
            "builder": {
                "repository": builder_remote,
                "commit": builder_commit,
                "dirty": builder_dirty,
            },
            "skill": {
                "name": args.skill_name,
                "display_name": display_name,
                "version": context.version,
                "source_skill_sha256": content_hash(source_skill_bytes),
                "body_sha256": content_hash(source_body.encode("utf-8")),
            },
            "artifacts": records,
        }
        (stage / "release.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

        destination = output_root / release_id
        if destination.exists():
            existing = json.loads((destination / "release.json").read_text(encoding="utf-8"))
            if existing.get("release_sha256") != release_sha:
                raise ValueError(f"Existing release has different content: {destination}")
            verify(destination)
            return destination
        output_root.mkdir(parents=True, exist_ok=True)
        shutil.move(stage, destination)

    verify(destination)
    return destination


def artifact_path(release_dir: Path, relative: str) -> Path:
    path = (release_dir / relative).resolve()
    if release_dir.resolve() not in path.parents:
        raise ValueError(f"Artifact escapes release directory: {relative}")
    return path


def verify_canonical_skill(release_dir: Path, artifact: dict, skill: dict) -> dict[str, bytes]:
    directory = artifact_path(release_dir, artifact["directory"])
    if tree_hash(directory) != artifact["tree_sha256"]:
        raise ValueError("clawhub directory hash mismatch")
    canonical = directory_contents(directory)
    canonical_skill = canonical["SKILL.md"]
    if content_hash(canonical_skill) != skill["source_skill_sha256"]:
        raise ValueError("clawhub SKILL.md differs from GitHub source")
    frontmatter, body = split_skill_document(canonical_skill.decode("utf-8"), "clawhub SKILL.md")
    fields = parse_frontmatter(frontmatter)
    if fields.get("version") != skill["version"] or fields.get("version_management") != "standalone":
        raise ValueError("clawhub metadata does not match release.json")
    if content_hash(body.encode("utf-8")) != skill["body_sha256"]:
        raise ValueError("clawhub SKILL.md body differs from GitHub source")
    return canonical


def verify_channel_artifact(
    channel: str,
    artifact: dict,
    release_dir: Path,
    skill: dict,
    canonical: dict[str, bytes],
) -> list[str]:
    expected_overrides = channel_frontmatter_overrides(channel, skill["name"], skill["display_name"])
    if (artifact.get("frontmatter_overrides") or {}) != expected_overrides:
        raise ValueError(f"{channel} frontmatter override policy mismatch")
    expected = expected_variant_contents(canonical, expected_overrides, f"{channel} SKILL.md")
    hashes: list[str] = []
    if "directory" in artifact:
        directory = artifact_path(release_dir, artifact["directory"])
        if tree_hash(directory) != artifact["tree_sha256"]:
            raise ValueError(f"{channel} directory hash mismatch")
        scan_tree(directory)
        assert_contents_equal(directory_contents(directory), expected, f"{channel} directory")
        hashes.append(artifact["tree_sha256"])
        archive_sha = artifact["archive_sha256"]
        archive_root = artifact["archive_root"]
    else:
        archive_sha = artifact["sha256"]
        archive_root = artifact["embedded_skill_root"]
    archive = artifact_path(release_dir, artifact["archive"])
    if file_hash(archive) != archive_sha:
        raise ValueError(f"{channel} archive hash mismatch")
    verify_zip(archive)
    if channel == "workbuddy":
        marker = "/skills/"
        embedded_root = artifact["embedded_skill_root"]
        if marker not in embedded_root:
            raise ValueError("workbuddy embedded skill root is invalid")
        package_root = embedded_root.split(marker, 1)[0]
        expected_root = f"workbuddy-ai-shifu-{skill['version']}"
        if package_root != expected_root:
            raise ValueError("workbuddy archive root mismatch")
        validate_workbuddy_package_contents(
            zip_subtree_contents(archive, package_root), skill["version"]
        )
    assert_contents_equal(zip_subtree_contents(archive, archive_root), expected, f"{channel} archive")
    hashes.append(archive_sha)
    return hashes


def verify_embedded_source_variant(
    skill_root: Path,
    record: dict,
    overrides: dict[str, str],
    name: str,
) -> None:
    source_files = record.get("source_files")
    if not isinstance(source_files, dict) or "SKILL.md" not in source_files:
        raise ValueError(f"doubao {name} source file manifest is missing")
    if manifest_tree_hash(source_files) != record.get("source_tree_sha256"):
        raise ValueError(f"doubao {name} source tree manifest mismatch")

    actual_manifest = directory_manifest(skill_root)
    if actual_manifest.keys() != source_files.keys():
        missing = sorted(source_files.keys() - actual_manifest.keys())
        extra = sorted(actual_manifest.keys() - source_files.keys())
        raise ValueError(
            f"doubao {name} source file set mismatch: missing={missing}, extra={extra}"
        )
    for relative, expected in source_files.items():
        if relative == "SKILL.md":
            if actual_manifest[relative]["mode"] != expected["mode"]:
                raise ValueError(f"doubao {name} SKILL.md mode differs from GitHub source")
            continue
        if actual_manifest[relative] != expected:
            raise ValueError(
                f"doubao {name} source file differs from GitHub source: {relative}"
            )

    actual_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    _, body = split_skill_document(actual_text, f"doubao {name}/SKILL.md")
    if content_hash(body.encode("utf-8")) != record.get("body_sha256"):
        raise ValueError(f"doubao {name} body differs from GitHub source")

    source_frontmatter = record.get("source_frontmatter")
    if not isinstance(source_frontmatter, str):
        raise ValueError(f"doubao {name} source frontmatter is missing")
    source_text = f"---\n{source_frontmatter}\n---\n{body}"
    if content_hash(source_text.encode("utf-8")) != record.get("source_skill_sha256"):
        raise ValueError(f"doubao {name} source SKILL.md proof mismatch")
    if content_hash(source_text.encode("utf-8")) != source_files["SKILL.md"]["sha256"]:
        raise ValueError(f"doubao {name} source SKILL.md manifest mismatch")

    expected_text = update_skill_frontmatter(
        source_text, overrides, f"doubao {name}/SKILL.md"
    )
    if actual_text != expected_text:
        raise ValueError(f"doubao {name} SKILL.md contains non-whitelisted changes")


def verify_doubao_artifact(
    artifact: dict,
    release_dir: Path,
    skill: dict,
    source_commit: str,
    canonical: dict[str, bytes],
) -> list[str]:
    project = Path(__file__).resolve().parents[1]
    profile = doubao_package.load_profile(project / "channels/doubao/profile.json")
    if skill["name"] != profile["primary_skill"]:
        raise ValueError("Doubao primary skill does not match release.json")
    directory = artifact_path(release_dir, artifact["directory"])
    expected_root = f"doubao-ai-shifu-{skill['version']}"
    if directory.name != artifact["archive_root"] or directory.name != expected_root:
        raise ValueError("Doubao archive root mismatch")
    if tree_hash(directory) != artifact["tree_sha256"]:
        raise ValueError("doubao directory hash mismatch")
    scan_tree(directory)

    profile_skills = {item["name"]: item for item in profile["skills"]}
    embedded = artifact.get("embedded_skills", {})
    if set(embedded) != set(profile_skills):
        raise ValueError("doubao embedded skill records mismatch")
    source_frontmatter: dict[str, dict[str, str]] = {}
    for name, record in embedded.items():
        if record.get("source_commit") != source_commit:
            raise ValueError(f"doubao {name} source commit mismatch")
        raw_frontmatter = record.get("source_frontmatter")
        if not isinstance(raw_frontmatter, str):
            raise ValueError(f"doubao {name} source frontmatter is missing")
        source_frontmatter[name] = parse_frontmatter(raw_frontmatter)
    doubao_package.validate_package(directory, profile, source_frontmatter)

    for name, record in embedded.items():
        item = profile_skills[name]
        metadata = source_frontmatter[name]
        expected_overrides = doubao_package.skill_overrides(item, metadata)
        if record.get("frontmatter_overrides") != expected_overrides:
            raise ValueError(f"doubao {name} frontmatter override policy mismatch")
        skill_root = directory / "workspace" / "skills" / name
        if tree_hash(skill_root) != record.get("tree_sha256"):
            raise ValueError(f"doubao {name} tree hash mismatch")
        verify_embedded_source_variant(skill_root, record, expected_overrides, name)
        if name == skill["name"]:
            expected = expected_variant_contents(
                canonical, expected_overrides, f"doubao {name}/SKILL.md"
            )
            assert_contents_equal(
                directory_contents(skill_root), expected, f"doubao {name} directory"
            )

    archive = artifact_path(release_dir, artifact["archive"])
    if file_hash(archive) != artifact["archive_sha256"]:
        raise ValueError("doubao archive hash mismatch")
    verify_zip(archive)
    assert_contents_equal(
        zip_subtree_contents(archive, artifact["archive_root"]),
        directory_contents(directory),
        "doubao archive",
    )
    return [artifact["tree_sha256"], artifact["archive_sha256"]]


def verify(release_dir: Path) -> None:
    report = json.loads((release_dir / "release.json").read_text())
    schema_version = report.get("schema_version")
    if schema_version != RELEASE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported release schema {schema_version!r}; rebuild with schema {RELEASE_SCHEMA_VERSION}"
        )

    skill = report["skill"]
    artifacts = report["artifacts"]
    canonical = verify_canonical_skill(release_dir, artifacts["clawhub"], skill)
    hashes: list[str] = []
    for channel in CHANNEL_ORDER:
        if channel == "doubao":
            hashes.extend(
                verify_doubao_artifact(
                    artifacts[channel],
                    release_dir,
                    skill,
                    report["source"]["commit"],
                    canonical,
                )
            )
        else:
            hashes.extend(
                verify_channel_artifact(channel, artifacts[channel], release_dir, skill, canonical)
            )
    expected_release_sha = hashlib.sha256(("\0".join(hashes)).encode()).hexdigest()
    if report.get("release_sha256") != expected_release_sha:
        raise ValueError("Release hash mismatch")
