#!/usr/bin/env python3
"""Build, verify, check, and publish AI-Shifu release artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import activate_manifest, build_release, bump_version, publish_release


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="Build all channel artifacts")
    build.set_defaults(source_repo_url=build_release.SOURCE_REPOSITORY)
    build.add_argument("--skill-name", default="ai-shifu-course-creator")
    build.add_argument("--output", default="dist")

    bump = commands.add_parser("bump", help="Open a version-bump PR against the skills source repository")
    bump.add_argument("--skill-name", default="ai-shifu-course-creator")
    bump.add_argument("--skill-version", default="", help="Explicit new SemVer for the skill")
    bump.add_argument("--level", choices=bump_version.BUMP_LEVELS, default="", help="SemVer bump level")
    bump.add_argument("--changelog", default="", help="Optional CHANGELOG entry text")
    bump.add_argument("--draft", action="store_true", help="Open the PR as a draft")
    bump.add_argument("--no-pr", action="store_true", help="Push the branch but skip gh pr create")
    bump.add_argument("--repo-url", default=bump_version.PUSH_REPOSITORY)

    verify = commands.add_parser("verify", help="Verify an existing release")
    verify.add_argument("release_dir")

    check = commands.add_parser("check", help="Authenticate and dry-run registry publication")
    check.add_argument("release_dir")
    check.add_argument("--target", choices=(*publish_release.AUTOMATED_TARGETS, "all"), default="all")
    check.add_argument("--clawhub-npx", default="", help="Path to an npx binary (Node 22) for the clawhub CLI")
    check.add_argument("--skillhub-cli", default="", help="Path to the skillhub CLI binary")

    publish = commands.add_parser("publish", help="Publish a verified release")
    publish.add_argument("release_dir")
    publish.add_argument("--target", choices=(*publish_release.AUTOMATED_TARGETS, "all"), default="all")
    publish.add_argument("--execute", action="store_true", help="Required acknowledgement of remote changes")
    publish.add_argument("--clawhub-npx", default="", help="Path to an npx binary (Node 22) for the clawhub CLI")
    publish.add_argument("--skillhub-cli", default="", help="Path to the skillhub CLI binary")

    manual_plan = commands.add_parser(
        "manual-plan", help="Show WorkBuddy, QClaw, and Doubao upload artifacts"
    )
    manual_plan.add_argument("release_dir")
    manual_plan.add_argument("--target", choices=(*publish_release.MANUAL_TARGETS, "all"), default="all")

    record_manual = commands.add_parser("record-manual", help="Record a manual channel result")
    record_manual.add_argument("release_dir")
    record_manual.add_argument("--target", choices=publish_release.MANUAL_TARGETS, required=True)
    record_manual.add_argument("--status", choices=publish_release.MANUAL_STATUSES, required=True)
    record_manual.add_argument("--url", default="")
    record_manual.add_argument("--note", default="")

    activate = commands.add_parser("activate-manifest", help="Open a website PR that bumps the skill manifest")
    activate.add_argument("release_dir")
    activate.add_argument("--notes", default="", help="Manifest notes text (default: Release <version>)")
    activate.add_argument(
        "--auto-notes", action="store_true",
        help="Compose notes from the skill's PR titles since the previous manifest version",
    )
    activate.add_argument("--draft", action="store_true", help="Open the PR as a draft")
    activate.add_argument("--no-pr", action="store_true", help="Push the branch but skip gh pr create")
    activate.add_argument("--check-online", action="store_true", help="Only fetch the live manifest and compare")
    activate.add_argument(
        "--allow-pending", action="append", default=[],
        choices=publish_release.MANIFEST_REQUIRED_MANUAL_TARGETS,
        help="Waive the readiness gate for a manual channel the release owner handles offline",
    )
    activate.add_argument("--repo-url", default=activate_manifest.WEBSITE_REPOSITORY)

    args = parser.parse_args()
    if args.command == "build":
        print(build_release.build(args))
    elif args.command == "bump":
        print(json.dumps(bump_version.bump(args), ensure_ascii=False, indent=2))
    elif args.command == "activate-manifest":
        print(json.dumps(activate_manifest.activate(args), ensure_ascii=False, indent=2))
    elif args.command == "verify":
        build_release.verify(Path(args.release_dir).expanduser().resolve())
        print("release verified")
    elif args.command in {"check", "publish"}:
        if args.command == "publish" and not args.execute:
            parser.error("publish requires --execute; use check for a dry run")
        context = publish_release.ReleaseContext.load(Path(args.release_dir))
        publisher = publish_release.AutomatedPublisher(
            context,
            clawhub_command=(str(Path(args.clawhub_npx).expanduser().resolve()),) if args.clawhub_npx else None,
            skillhub_cli=Path(args.skillhub_cli).expanduser().resolve() if args.skillhub_cli else None,
        )
        targets = publish_release.expand_automated_targets(args.target)
        results = publisher.check(targets) if args.command == "check" else publisher.publish(targets)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        if any(result["status"] == "failed" for result in results.values()):
            raise SystemExit(1)
    else:
        context = publish_release.ReleaseContext.load(Path(args.release_dir))
        publisher = publish_release.ManualPublisher(context)
        if args.command == "manual-plan":
            result = publisher.plan(publish_release.expand_manual_targets(args.target))
        else:
            result = publisher.record(args.target, args.status, url=args.url, note=args.note)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
