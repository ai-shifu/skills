"""Submit one verified GitHub Release package to one registry."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import github_releases, publishing
from .release_state import ReleaseContext


def classify_submission(target: str, response: object) -> str:
    rendered = (
        json.dumps(response, ensure_ascii=False)
        if not isinstance(response, str)
        else response
    )
    if re.search(
        r"pending[_ -]?review|under[_ -]?review|审核中", rendered, re.IGNORECASE
    ):
        return "pending_review"
    # A successful CLI return means acceptance by the registry. Listing requires
    # independent channel evidence and is never inferred here.
    return "submitted"


def publish(
    tag: str, repository: str, target: str, output: Path, *, execute: bool
) -> dict:
    """Submit one immutable release after validating content and retry eligibility."""
    if target not in publishing.AUTOMATED_TARGETS:
        raise ValueError(f"Unsupported automatic channel: {target}")
    if not execute:
        raise ValueError("Channel submission requires --execute")
    if target == "skillhub" and os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise ValueError(
            "SkillHub workflow reruns cannot submit; start a new manual run after checking the channel"
        )
    release_dir = github_releases.download(tag, repository, output)
    release = ReleaseContext.load(release_dir)
    base = {
        "target": target,
        "tag": tag,
        "source_commit": release.source_commit,
        "version": release.version,
        "archive_sha256": release.metadata["artifacts"][target]["archive_sha256"],
    }
    owner = (
        os.environ.get("CLAWHUB_OWNER", "").strip().lstrip("@")
        if target == "clawhub"
        else ""
    )
    if target == "clawhub" and not re.fullmatch(r"[A-Za-z0-9_-]+", owner):
        return {
            **base,
            "status": "failed",
            "reason": "ClawHub publisher owner is not configured",
        }
    publisher = publishing.AutomatedPublisher(
        release, require_current_main=False, clawhub_owner=owner
    )
    try:
        if target == "clawhub" and publisher.existing_clawhub_version():
            return {
                **base,
                "status": "needs_review",
                "reason": "Exact ClawHub version already exists; inspect its content before retrying",
            }
        if target == "skillhub" and publisher.existing_skillhub_version():
            return {
                **base,
                "status": "already_verified",
                "reason": "This SkillHub version already matches the Release ZIP",
            }
    except (publishing.CommandFailure, ValueError) as error:
        return {**base, "status": "needs_review", "reason": str(error)}
    result = publisher.publish((target,))[target]
    if result["status"] == "failed":
        return {**base, "status": "failed", "response": result["response"]}
    if result["status"] != "published":
        return {**base, "status": "failed", "response": result["response"]}
    return {
        **base,
        "status": classify_submission(target, result["response"]),
        "response": result["response"],
    }
