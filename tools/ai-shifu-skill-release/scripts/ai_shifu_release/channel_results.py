"""Import channel submission receipts into the verified release's report."""

from __future__ import annotations

import json
from pathlib import Path

from .publishing import AUTOMATED_TARGETS
from .release_state import ReleaseContext, ReleaseReport

# Published means upload acceptance; it does not claim independent listing.
REPORT_STATUSES = {
    "submitted": "published",
    "pending_review": "published",
    "already_verified": "verified",
    "needs_review": "needs_review",
    "failed": "failed",
}


def import_results(release_dir: Path, result_files: list[Path]) -> dict:
    """Validate all receipts before updating the report without resubmission."""
    if not result_files:
        raise ValueError("At least one channel result is required")
    release = ReleaseContext.load(release_dir)
    records = {}
    for result_file in result_files:
        result = json.loads(result_file.expanduser().read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            raise ValueError(f"Channel result must contain an object: {result_file}")
        target = result.get("target")
        if target not in AUTOMATED_TARGETS:
            raise ValueError(f"Unsupported channel result target: {target!r}")
        if target in records:
            raise ValueError(f"Duplicate channel result: {target}")
        expected = {
            "source_commit": release.source_commit,
            "version": release.version,
            "tag": f"v{release.version}",
            "archive_sha256": release.metadata["artifacts"][target]["archive_sha256"],
        }
        for key, value in expected.items():
            if result.get(key) != value:
                raise ValueError(f"{target} channel result {key} differs from release")
        status = result.get("status")
        if not isinstance(status, str) or status not in REPORT_STATUSES:
            raise ValueError(f"Unsupported channel result status: {status!r}")
        records[target] = {
            "status": REPORT_STATUSES[status],
            "submission_status": status,
            **expected,
            "artifact_sha256": release.artifact_sha(target),
            "response": result.get("response", result.get("reason", "")),
        }
    ReleaseReport(release).update(records)
    return records
