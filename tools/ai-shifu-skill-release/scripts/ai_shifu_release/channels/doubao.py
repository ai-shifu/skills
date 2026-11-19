"""Build and verify Doubao Plugin packages and historical partner packages."""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath

from ai_shifu_release.artifacts import (
    artifact_path,
    assert_contents_equal,
    content_hash,
    directory_contents,
    directory_manifest,
    expected_variant_contents,
    file_hash,
    scan_tree,
    tree_hash,
    verify_zip,
    write_zip,
    zip_subtree_contents,
)
from ai_shifu_release.channels import BuildContext, doubao_legacy
from ai_shifu_release.config import channel_path
from ai_shifu_release.skill_metadata import (
    build_skill_variant,
    read_skill_document,
)
from ai_shifu_release.skill_metadata import (
    parse_frontmatter as parse_skill_frontmatter,
)

PLUGIN_FORMAT = "plugin-v1"
ICON_PATH = "./com.doubao/assets/plugin-icon.png"
MAX_PACKAGE_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ENTRIES = 1024
MAX_SKILLS = 10


def validate_archive_limits(archive: Path) -> None:
    if archive.stat().st_size > MAX_PACKAGE_BYTES:
        raise ValueError("Doubao plugin ZIP exceeds 16 MiB")
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if len(entries) > MAX_ENTRIES:
            raise ValueError("Doubao plugin exceeds 1024 ZIP entries")
        if any(entry.file_size > MAX_FILE_BYTES for entry in entries):
            raise ValueError("Doubao plugin ZIP contains a file exceeding 2 MiB")
        if sum(entry.file_size for entry in entries) > MAX_PACKAGE_BYTES:
            raise ValueError("Doubao plugin ZIP exceeds 16 MiB uncompressed")


def load_profile(path: Path) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    validate_profile(profile)
    return profile


def validate_profile(profile: dict) -> None:
    # The profile also owns the manual test scenarios, including for old releases.
    doubao_legacy.validate_profile(profile)
    package_format = profile.get("package_format")
    if package_format not in (None, PLUGIN_FORMAT):
        raise ValueError(f"Unsupported Doubao package format: {package_format}")
    if package_format == PLUGIN_FORMAT:
        if len(profile["id"]) > 64:
            raise ValueError("Doubao plugin name must be at most 64 characters")
        if not 1 <= len(profile["skills"]) <= MAX_SKILLS:
            raise ValueError("Doubao plugin must contain at most 10 skills")
        for item in profile["skills"]:
            if len(item["name"]) > 64 or len(item["display_name"]) > 128:
                raise ValueError("Doubao skill name or display name is too long")


def render_plugin(profile: dict, version: str) -> dict:
    return {
        "name": profile["id"],
        "version": version,
        "description": profile["description"],
        "extensions": {
            "com.doubao": {
                "displayName": {"zh": profile["name"]},
                "displayDescription": {"zh": profile["description"]},
                "icon": ICON_PATH,
            }
        },
    }


def skill_overrides(skill: dict, source: dict[str, str]) -> dict[str, str]:
    name = skill["name"]
    description = source.get("description", "")
    if source.get("name") != name:
        raise ValueError(f"Doubao skill name mismatch: {name}")
    if not description.strip() or len(description) > 1024:
        raise ValueError(
            f"Doubao skill description must be 1 to 1024 characters: {name}"
        )
    overrides = {
        "metadata.display_name": skill["display_name"],
        "metadata.display_description": description.replace(
            "MarkdownFlow (MDF)", "MarkdownFlow"
        ),
    }
    version_management = source.get("version_management")
    if version_management == "standalone":
        overrides["version_management"] = "plugin"
    elif version_management not in {None, "", "plugin"}:
        raise ValueError(f"Doubao source skill has invalid version_management: {name}")
    return overrides


def parse_frontmatter(text: str) -> dict[str, str]:
    frontmatter, _ = doubao_legacy.split_skill_document(text, "Doubao SKILL.md")
    fields = parse_skill_frontmatter(frontmatter)
    in_metadata = False
    for line in frontmatter.splitlines():
        if line and not line[0].isspace():
            in_metadata = line == "metadata:"
        elif in_metadata:
            match = re.fullmatch(r"  (display_name|display_description):\s*(.+)", line)
            if match:
                fields[f"metadata.{match.group(1)}"] = json.loads(match.group(2))
    return fields


def validate_package(
    root: Path,
    profile: dict,
    source_frontmatter: dict[str, dict[str, str]],
    version: str | None = None,
) -> None:
    if profile.get("package_format") != PLUGIN_FORMAT:
        return doubao_legacy.validate_package(root, profile, source_frontmatter)
    validate_profile(profile)
    root = root.resolve()
    plugin_file = root / "plugin.json"
    if not plugin_file.is_file():
        raise ValueError("Doubao plugin.json is missing")
    plugin = json.loads(plugin_file.read_text(encoding="utf-8"))
    expected_version = version if version is not None else plugin.get("version")
    if not isinstance(expected_version, str) or not re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", expected_version
    ):
        raise ValueError("Doubao plugin version must use X.Y.Z")
    if plugin != render_plugin(profile, expected_version):
        raise ValueError(
            "Doubao plugin.json differs from the channel profile or version"
        )
    if (root / "agent.yml").exists() or (root / "workspace").exists():
        raise ValueError("Doubao plugin contains legacy partner package files")
    icon = artifact_path(root, ICON_PATH)
    doubao_legacy.validate_image(icon, max_bytes=500 * 1024)
    if doubao_legacy.png_dimensions(icon) != (512, 512):
        raise ValueError("Doubao plugin icon must be 512x512 pixels")
    skills_root = root / "skills"
    if not skills_root.is_dir():
        raise ValueError("Doubao plugin skills directory is missing")
    expected_names = sorted(item["name"] for item in profile["skills"])
    actual_names = sorted(path.name for path in skills_root.iterdir() if path.is_dir())
    if actual_names != expected_names or set(source_frontmatter) != set(expected_names):
        raise ValueError("Doubao plugin skill directories or source records mismatch")
    for skill in profile["skills"]:
        name = skill["name"]
        skill_file = artifact_path(root, f"skills/{name}/SKILL.md")
        if not skill_file.is_file():
            raise ValueError(f"Doubao skill is missing SKILL.md: {name}")
        fields = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        source = source_frontmatter[name]
        expected = {
            "name": name,
            "description": source["description"],
            "metadata.display_name": skill["display_name"],
            "metadata.display_description": skill_overrides(skill, source)[
                "metadata.display_description"
            ],
        }
        for field, value in expected.items():
            if fields.get(field) != value:
                raise ValueError(f"Doubao skill frontmatter mismatch: {name} {field}")

    paths = list(root.rglob("*"))
    for path in paths:
        if path.is_symlink() and not path.resolve().is_relative_to(root):
            raise ValueError(
                f"Doubao package symlink escapes plugin root: {path.relative_to(root)}"
            )
    files = [path for path in paths if path.is_file()]
    if len(files) > MAX_ENTRIES:
        raise ValueError("Doubao plugin exceeds 1024 ZIP entries")
    if sum(path.stat().st_size for path in files) > MAX_PACKAGE_BYTES:
        raise ValueError("Doubao plugin exceeds 16 MiB uncompressed")
    for path in files:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(
                f"Doubao plugin file exceeds 2 MiB: {path.relative_to(root)}"
            )
        if path.suffix.lower() == ".png":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(text) for pattern in doubao_legacy.LEAK_PATTERNS):
            raise ValueError(
                f"Doubao package contains a local path or private address: {path.relative_to(root)}"
            )
        if any(word in text for word in doubao_legacy.TEMPLATE_RESIDUE):
            raise ValueError(
                f"Doubao package contains template residue: {path.relative_to(root)}"
            )


def build_doubao_artifact(channel: str, context: BuildContext) -> dict:
    profile_path = channel_path(context.channels, context.config.doubao.profile)
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    validate_profile(profile)
    if profile.get("package_format") != PLUGIN_FORMAT:
        return doubao_legacy.build_doubao_artifact(channel, context)
    if context.skill_name != profile["primary_skill"]:
        raise ValueError(
            f"Doubao profile supports {profile['primary_skill']}, not {context.skill_name}"
        )
    root_name = f"doubao-ai-shifu-{context.version}"
    stage_dir = context.artifacts / channel / root_name
    stage_dir.mkdir(parents=True)
    source_icon = profile_path.parent / PurePosixPath(profile["avatar"])
    if not source_icon.resolve().is_relative_to(context.channels.resolve()):
        raise ValueError("Doubao avatar must stay inside channels/")
    icon = stage_dir / ICON_PATH
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_icon, icon)
    (stage_dir / "plugin.json").write_text(
        json.dumps(
            render_plugin(profile, context.version), ensure_ascii=False, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    embedded_skills = {}
    source_frontmatter = {}
    for skill in profile["skills"]:
        name = skill["name"]
        source = context.source_skills[name]
        frontmatter, body = read_skill_document(source / "SKILL.md")
        metadata = parse_skill_frontmatter(frontmatter)
        source_frontmatter[name] = metadata
        overrides = skill_overrides(skill, metadata)
        destination = stage_dir / "skills" / name
        build_skill_variant(source, destination, overrides)
        assert_contents_equal(
            directory_contents(destination),
            expected_variant_contents(
                directory_contents(source), overrides, f"Doubao {name}/SKILL.md"
            ),
            f"doubao {name} directory",
        )
        embedded_skills[name] = {
            "root": f"skills/{name}",
            "source_commit": context.source_commit,
            "source_tree_sha256": tree_hash(source),
            "source_files": directory_manifest(source),
            "source_skill_sha256": file_hash(source / "SKILL.md"),
            "source_frontmatter": frontmatter,
            "body_sha256": content_hash(body.encode("utf-8")),
            "tree_sha256": tree_hash(destination),
            "frontmatter_overrides": overrides,
        }
    scan_tree(stage_dir)
    validate_package(stage_dir, profile, source_frontmatter, context.version)
    archive = context.artifacts / channel / f"{root_name}.zip"
    write_zip(stage_dir, archive, "")
    validate_archive_limits(archive)
    return {
        "directory": context.record_path(stage_dir),
        "tree_sha256": tree_hash(stage_dir),
        "archive": context.record_path(archive),
        "archive_sha256": file_hash(archive),
        "archive_root": "",
        "version": context.version,
        "source_profile_json": profile_bytes.decode("utf-8"),
        "source_profile_sha256": content_hash(profile_bytes),
        "embedded_skills": embedded_skills,
    }


def verify_doubao_artifact(
    artifact: dict,
    release_dir: Path,
    skill: dict,
    source_commit: str,
    canonical: dict[str, bytes],
) -> list[str]:
    profile_json = artifact.get("source_profile_json")
    if not isinstance(profile_json, str) or content_hash(
        profile_json.encode("utf-8")
    ) != artifact.get("source_profile_sha256"):
        raise ValueError(
            "Doubao source profile is missing or differs from its recorded hash"
        )
    profile = json.loads(profile_json)
    if profile.get("package_format") is None:
        return doubao_legacy.verify_doubao_artifact(
            artifact, release_dir, skill, source_commit, canonical
        )
    validate_profile(profile)
    if skill["name"] != profile["primary_skill"]:
        raise ValueError("Doubao primary skill does not match release.json")
    directory = artifact_path(release_dir, artifact["directory"])
    if (
        directory.name != f"doubao-ai-shifu-{skill['version']}"
        or artifact.get("archive_root") != ""
    ):
        raise ValueError("Doubao plugin archive root mismatch")
    if artifact.get("version") != skill["version"]:
        raise ValueError("Doubao plugin version mismatch")
    if tree_hash(directory) != artifact["tree_sha256"]:
        raise ValueError("doubao directory hash mismatch")
    scan_tree(directory)
    profile_skills = {item["name"]: item for item in profile["skills"]}
    embedded = artifact.get("embedded_skills", {})
    if set(embedded) != set(profile_skills):
        raise ValueError("doubao embedded skill records mismatch")
    source_frontmatter = {}
    for name, record in embedded.items():
        if (
            record.get("source_commit") != source_commit
            or record.get("root") != f"skills/{name}"
        ):
            raise ValueError(f"doubao {name} source commit or root mismatch")
        raw = record.get("source_frontmatter")
        if not isinstance(raw, str):
            raise ValueError(f"doubao {name} source frontmatter is missing")
        source_frontmatter[name] = parse_skill_frontmatter(raw)
    validate_package(directory, profile, source_frontmatter, skill["version"])
    for name, record in embedded.items():
        overrides = skill_overrides(profile_skills[name], source_frontmatter[name])
        if record.get("frontmatter_overrides") != overrides:
            raise ValueError(f"doubao {name} frontmatter override policy mismatch")
        skill_root = directory / "skills" / name
        if tree_hash(skill_root) != record.get("tree_sha256"):
            raise ValueError(f"doubao {name} tree hash mismatch")
        doubao_legacy.verify_embedded_source_variant(
            skill_root, record, overrides, name
        )
        if name == skill["name"]:
            expected = expected_variant_contents(
                canonical, overrides, f"doubao {name}/SKILL.md"
            )
            assert_contents_equal(
                directory_contents(skill_root), expected, f"doubao {name} directory"
            )
    archive = artifact_path(release_dir, artifact["archive"])
    if file_hash(archive) != artifact["archive_sha256"]:
        raise ValueError("doubao archive hash mismatch")
    validate_archive_limits(archive)
    verify_zip(archive)
    assert_contents_equal(
        zip_subtree_contents(archive, ""),
        directory_contents(directory),
        "doubao archive",
    )
    return [artifact["tree_sha256"], artifact["archive_sha256"]]
