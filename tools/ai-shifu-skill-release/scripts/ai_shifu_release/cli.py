"""Build, verify, check, and publish AI-Shifu release artifacts."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import build, channel_submission, github_releases, manifest, publishing, version
from .release_state import ReleaseContext
from .source import SOURCE_REF, SOURCE_REPOSITORY
from .verify import verify


def create_parser() -> argparse.ArgumentParser:
    """Define the sole public command interface for release workflows."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    build_command = commands.add_parser("build", help="Build all channel artifacts")
    build_command.add_argument("--skill-name", default="ai-shifu-course-creator")
    build_command.add_argument("--output", default="dist")
    build_command.add_argument(
        "--source-repo-url",
        dest="source_repo_url",
        default=SOURCE_REPOSITORY,
        help="Source Git repository (default: ai-shifu/skills)",
    )
    build_command.add_argument(
        "--source-ref", default=SOURCE_REF, help="main or a full source commit SHA"
    )
    build_command.add_argument(
        "--expected-version",
        default="",
        help="Fail if source SKILL.md has another version",
    )

    bump = commands.add_parser(
        "bump", help="Open a version-bump PR against the skills source repository"
    )
    bump.add_argument("--skill-name", default="ai-shifu-course-creator")
    bump.add_argument(
        "--skill-version", default="", help="Explicit new SemVer for the skill"
    )
    bump.add_argument(
        "--level", choices=version.BUMP_LEVELS, default="", help="SemVer bump level"
    )
    bump.add_argument("--changelog", default="", help="Optional CHANGELOG entry text")
    bump.add_argument("--draft", action="store_true", help="Open the PR as a draft")
    bump.add_argument(
        "--no-pr", action="store_true", help="Push the branch but skip gh pr create"
    )
    bump.add_argument("--repo-url", default=version.PUSH_REPOSITORY)

    verify_command = commands.add_parser("verify", help="Verify an existing release")
    verify_command.add_argument("release_dir")

    check = commands.add_parser(
        "check", help="Authenticate and dry-run registry publication"
    )
    check.add_argument("release_dir")
    check.add_argument(
        "--target", choices=(*publishing.AUTOMATED_TARGETS, "all"), default="all"
    )
    check.add_argument(
        "--clawhub-npx",
        default="",
        help="Path to an npx binary (Node 22) for the clawhub CLI",
    )
    check.add_argument(
        "--skillhub-cli", default="", help="Path to the skillhub CLI binary"
    )

    publish = commands.add_parser("publish", help="Publish a verified release")
    publish.add_argument("release_dir")
    publish.add_argument(
        "--target", choices=(*publishing.AUTOMATED_TARGETS, "all"), default="all"
    )
    publish.add_argument(
        "--execute",
        action="store_true",
        help="Required acknowledgement of remote changes",
    )
    publish.add_argument(
        "--clawhub-npx",
        default="",
        help="Path to an npx binary (Node 22) for the clawhub CLI",
    )
    publish.add_argument(
        "--skillhub-cli", default="", help="Path to the skillhub CLI binary"
    )

    manual_plan = commands.add_parser(
        "manual-plan", help="Show WorkBuddy and Doubao upload artifacts"
    )
    manual_plan.add_argument("release_dir")
    manual_plan.add_argument(
        "--target", choices=(*publishing.MANUAL_TARGETS, "all"), default="all"
    )

    record_manual = commands.add_parser(
        "record-manual", help="Record a manual channel result"
    )
    record_manual.add_argument("release_dir")
    record_manual.add_argument(
        "--target", choices=publishing.MANUAL_TARGETS, required=True
    )
    record_manual.add_argument(
        "--status", choices=publishing.MANUAL_STATUSES, required=True
    )
    record_manual.add_argument("--url", default="")
    record_manual.add_argument("--note", default="")

    activate = commands.add_parser(
        "activate-manifest", help="Open a website PR that bumps the skill manifest"
    )
    activate.add_argument("release_dir")
    activate.add_argument(
        "--notes", default="", help="Manifest notes text (default: Release <version>)"
    )
    activate.add_argument(
        "--auto-notes",
        action="store_true",
        help="Compose notes from the skill's PR titles since the previous manifest version",
    )
    activate.add_argument("--draft", action="store_true", help="Open the PR as a draft")
    activate.add_argument(
        "--no-pr", action="store_true", help="Push the branch but skip gh pr create"
    )
    activate.add_argument(
        "--check-online",
        action="store_true",
        help="Only fetch the live manifest and compare",
    )
    activate.add_argument(
        "--allow-pending",
        action="append",
        default=[],
        choices=manifest.MANIFEST_REQUIRED_MANUAL_TARGETS,
        help="Waive the readiness gate for a manual channel the release owner handles offline",
    )
    activate.add_argument("--repo-url", default=manifest.WEBSITE_REPOSITORY)

    github = commands.add_parser(
        "github-release", help="Publish immutable GitHub Release attachments"
    )
    github.add_argument("release_dir", type=Path)
    github.add_argument("--tag", required=True)
    github.add_argument("--commit", required=True)
    github.add_argument(
        "--prepare-only",
        action="store_true",
        help="Prepare assets without creating a Release",
    )
    github.add_argument(
        "--draft-preview-tag", help="Create and verify a branch-only test Draft Release"
    )
    github.add_argument(
        "--output", type=Path, help="Required output directory for --prepare-only"
    )

    submit = commands.add_parser(
        "submit-channel",
        help="Download, verify, and submit a published GitHub Release to a channel",
    )
    submit.add_argument("--tag", required=True)
    submit.add_argument("--repo", required=True)
    submit.add_argument("--target", required=True, choices=publishing.AUTOMATED_TARGETS)
    submit.add_argument("--output", type=Path, required=True)
    submit.add_argument("--execute", action="store_true")
    return parser


def run_github_release(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    """Prepare or publish GitHub attachments with the existing release gates."""
    if args.prepare_only and args.draft_preview_tag:
        parser.error("--prepare-only and --draft-preview-tag cannot be combined")
    if args.prepare_only:
        if args.output is None:
            parser.error("--prepare-only requires --output")
        assets, _ = github_releases.prepare_assets(
            args.release_dir.resolve(), args.tag, args.commit, args.output.resolve()
        )
        print("\n".join(str(asset) for asset in assets))
        return
    with tempfile.TemporaryDirectory() as temporary:
        assets, notes = github_releases.prepare_assets(
            args.release_dir.resolve(), args.tag, args.commit, Path(temporary)
        )
        url = github_releases.publish(
            args.draft_preview_tag or args.tag,
            args.commit,
            assets,
            notes,
            draft_preview=bool(args.draft_preview_tag),
            version_tag=args.tag,
        )
        print(url)


def run_channel_submission(args: argparse.Namespace) -> None:
    """Render and persist the actual outcome of a channel submission."""
    result = channel_submission.publish(
        args.tag, args.repo, args.target, args.output, execute=args.execute
    )
    # Retain the existing result filename consumed by workflow artifacts.
    (args.output / "platform-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"### {args.target}: {result['status']}\n\n")
            stream.write(
                f"Release `{args.tag}` · source `{result['source_commit']}`\n\n"
            )
            if result.get("reason"):
                stream.write(result["reason"] + "\n\n")
    if result["status"] in {"failed", "needs_review"}:
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> None:
    """Dispatch a command while preserving its output and exit status."""
    parser = create_parser()
    args = parser.parse_args(argv)
    if args.command == "build":
        print(build.build(args))
    elif args.command == "bump":
        print(json.dumps(version.bump(args), ensure_ascii=False, indent=2))
    elif args.command == "activate-manifest":
        print(json.dumps(manifest.activate(args), ensure_ascii=False, indent=2))
    elif args.command == "github-release":
        run_github_release(args, parser)
    elif args.command == "submit-channel":
        run_channel_submission(args)
    elif args.command == "verify":
        verify(Path(args.release_dir).expanduser().resolve())
        print("release verified")
    elif args.command in {"check", "publish"}:
        if args.command == "publish" and not args.execute:
            parser.error("publish requires --execute; use check for a dry run")
        context = ReleaseContext.load(Path(args.release_dir))
        publisher = publishing.AutomatedPublisher(
            context,
            clawhub_command=(str(Path(args.clawhub_npx).expanduser().resolve()),)
            if args.clawhub_npx
            else None,
            skillhub_cli=Path(args.skillhub_cli).expanduser().resolve()
            if args.skillhub_cli
            else None,
        )
        targets = publishing.expand_automated_targets(args.target)
        results = (
            publisher.check(targets)
            if args.command == "check"
            else publisher.publish(targets)
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))
        if any(result["status"] == "failed" for result in results.values()):
            raise SystemExit(1)
    else:
        context = ReleaseContext.load(Path(args.release_dir))
        publisher = publishing.ManualPublisher(context)
        if args.command == "manual-plan":
            result = publisher.plan(publishing.expand_manual_targets(args.target))
        else:
            result = publisher.record(
                args.target, args.status, url=args.url, note=args.note
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
