#!/usr/bin/env python3
"""Submit one verified GitHub Release package to one registry."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import download_release, publish_release


def existing_clawhub_version(publisher: publish_release.AutomatedPublisher) -> bool:
    identity = f"@{publisher.clawhub_owner}/{publisher.release.skill_name}"
    command = [*publisher._clawhub_command(), "--yes", "clawhub@latest", "inspect",
               identity, "--version", publisher.release.version, "--json"]
    try:
        publisher.runner(command)
        return True
    except publish_release.CommandFailure as error:
        if re.search(r"\b(not found|404|no such version)\b", error.output, re.IGNORECASE):
            return False
        raise


def existing_skillhub_version(publisher: publish_release.AutomatedPublisher) -> bool:
    archive = publisher.release.metadata["artifacts"]["skillhub"]["archive"]
    command = [str(publisher._skillhub_cli()), "verify",
               f"{publisher.release.skill_name}@{publisher.release.version}",
               "--zip", str(publisher.release.directory / archive),
               "--host", "https://api.skillhub.cn"]
    try:
        response = publisher.runner(command)
        if not re.search(r"签名与内容校验通过|signature and content verified|verification passed",
                         response.stdout, re.IGNORECASE):
            raise ValueError("SkillHub version exists but its content could not be verified")
        return True
    except publish_release.CommandFailure as error:
        if re.search(r"找不到该版本|version not found|404", error.output, re.IGNORECASE):
            return False
        raise


def classify_submission(target: str, response: object) -> str:
    rendered = json.dumps(response, ensure_ascii=False) if not isinstance(response, str) else response
    if re.search(r"pending[_ -]?review|under[_ -]?review|审核中", rendered, re.IGNORECASE):
        return "pending_review"
    # A successful CLI return means acceptance by the registry. Listing requires
    # independent platform evidence and is never inferred here.
    return "submitted"


def publish(tag: str, repository: str, target: str, output: Path, *, execute: bool) -> dict:
    if target not in publish_release.AUTOMATED_TARGETS:
        raise ValueError(f"Unsupported automatic platform: {target}")
    if not execute:
        raise ValueError("Platform submission requires --execute")
    if target == "skillhub" and os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise ValueError("SkillHub workflow reruns cannot submit; start a new manual run after checking the platform")
    release_dir = download_release.download(tag, repository, output)
    release = publish_release.ReleaseContext.load(release_dir)
    base = {
        "target": target,
        "tag": tag,
        "source_commit": release.source_commit,
        "version": release.version,
        "archive_sha256": release.metadata["artifacts"][target]["archive_sha256"],
    }
    owner = os.environ.get("CLAWHUB_OWNER", "").strip().lstrip("@") if target == "clawhub" else ""
    if target == "clawhub" and not re.fullmatch(r"[A-Za-z0-9_-]+", owner):
        return {**base, "status": "failed", "reason": "ClawHub publisher owner is not configured"}
    publisher = publish_release.AutomatedPublisher(
        release, require_current_main=False, clawhub_owner=owner
    )
    try:
        if target == "clawhub" and existing_clawhub_version(publisher):
            return {**base, "status": "needs_review",
                    "reason": "Exact ClawHub version already exists; inspect its content before retrying"}
        if target == "skillhub" and existing_skillhub_version(publisher):
            return {**base, "status": "already_verified",
                    "reason": "This SkillHub version already matches the Release ZIP"}
    except (publish_release.CommandFailure, ValueError) as error:
        return {**base, "status": "needs_review", "reason": str(error)}
    result = publisher.publish((target,))[target]
    if result["status"] == "failed":
        return {**base, "status": "failed", "response": result["response"]}
    if result["status"] != "published":
        return {**base, "status": "failed", "response": result["response"]}
    return {**base, "status": classify_submission(target, result["response"]),
            "response": result["response"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--target", required=True, choices=publish_release.AUTOMATED_TARGETS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = publish(args.tag, args.repo, args.target, args.output, execute=args.execute)
    (args.output / "platform-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"### {args.target}: {result['status']}\n\n")
            stream.write(f"Release `{args.tag}` · source `{result['source_commit']}`\n\n")
            if result.get("reason"):
                stream.write(result["reason"] + "\n\n")
    if result["status"] in {"failed", "needs_review"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
