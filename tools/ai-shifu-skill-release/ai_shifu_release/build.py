"""Coordinate source export and construction of all channel artifacts."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Protocol

from ai_shifu_release import TOOL_ROOT
from ai_shifu_release.artifacts import (
    CHANNEL_ORDER,
    RELEASE_SCHEMA_VERSION,
    artifact_hashes,
    content_hash,
    release_hash,
)
from ai_shifu_release.channels import BuildContext, doubao
from ai_shifu_release.channels.doubao import build_doubao_artifact
from ai_shifu_release.channels.registry import build_registry_artifact
from ai_shifu_release.channels.workbuddy import build_workbuddy_artifact
from ai_shifu_release.skill_metadata import read_frontmatter, split_skill_document
from ai_shifu_release.source import (
    SOURCE_REF,
    export_skill,
    export_tree,
    fetch_source,
    git_metadata,
    load_publisher,
    run,
)
from ai_shifu_release.verify import verify

CHANNEL_BUILDERS: dict[str, Callable[[str, BuildContext], dict]] = {
    "clawhub": build_registry_artifact,
    "skillhub": build_registry_artifact,
    "workbuddy": build_workbuddy_artifact,
    "doubao": build_doubao_artifact,
}


class BuildOptions(Protocol):
    source_repo_url: str
    source_ref: str
    expected_version: str
    skill_name: str
    output: str


def build(args: BuildOptions) -> Path:
    project = TOOL_ROOT
    output_root = Path(args.output).expanduser().resolve()

    with tempfile.TemporaryDirectory(prefix="ai-shifu-build-") as temporary:
        temporary_root = Path(temporary)
        source_repo = temporary_root / "github-source"
        source_ref = getattr(args, "source_ref", SOURCE_REF)
        commit, remote = fetch_source(args.source_repo_url, source_repo, source_ref)
        publisher = load_publisher(source_repo, commit)
        channels = temporary_root / "channels"
        export_tree(
            source_repo,
            commit,
            "tools/ai-shifu-skill-release/channels",
            channels,
            normalize_git_modes=True,
        )
        source_skill = temporary_root / "source-skill"
        export_skill(source_repo, commit, args.skill_name, source_skill)
        profile = doubao.load_profile(channels / "doubao/profile.json")
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
        expected_version = getattr(args, "expected_version", "")
        if expected_version and metadata["version"] != expected_version:
            raise ValueError(
                f"Source version {metadata['version']} does not match expected {expected_version}"
            )
        if metadata["version_management"] != "standalone":
            raise ValueError("Canonical skill must use version_management: standalone")
        display_name = metadata.get("name", "").strip()
        if not display_name:
            raise ValueError("Canonical skill must define name")

        source_skill_bytes = (source_skill / "SKILL.md").read_bytes()
        _, source_body = split_skill_document(
            source_skill_bytes.decode("utf-8"), "GitHub SKILL.md"
        )
        context = BuildContext(
            source_skill=source_skill,
            source_skills=source_skills,
            source_commit=commit,
            channels=channels,
            stage=temporary_root / "release",
            skill_name=args.skill_name,
            version=metadata["version"],
            display_name=display_name,
            publisher=publisher,
        )
        records = {
            channel: CHANNEL_BUILDERS[channel](channel, context)
            for channel in CHANNEL_ORDER
        }

        release_hashes = [
            digest
            for channel in CHANNEL_ORDER
            for digest in artifact_hashes(records[channel])
        ]
        release_sha = release_hash(release_hashes)
        release_id = (
            f"{args.skill_name}-{context.version}-{commit[:7]}-{release_sha[:7]}"
        )
        builder_commit, builder_remote, builder_dirty = git_metadata(project)
        stage = context.stage
        source_time = run("git", "show", "-s", "--format=%cI", commit, cwd=source_repo)
        report = {
            "schema_version": RELEASE_SCHEMA_VERSION,
            "release_id": release_id,
            "release_sha256": release_sha,
            "source_committed_at": source_time,
            "source": {"repository": remote, "ref": source_ref, "commit": commit},
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
        (stage / "release.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )

        destination = output_root / release_id
        if destination.exists():
            existing = json.loads(
                (destination / "release.json").read_text(encoding="utf-8")
            )
            if existing.get("release_sha256") != release_sha:
                raise ValueError(
                    f"Existing release has different content: {destination}"
                )
            if (
                existing.get("source") != report["source"]
                or existing.get("skill") != report["skill"]
            ):
                raise ValueError(
                    f"Existing release has different source metadata: {destination}; "
                    "choose another --output directory"
                )
            verify(destination)
            return destination
        output_root.mkdir(parents=True, exist_ok=True)
        shutil.move(stage, destination)

    verify(destination)
    return destination
