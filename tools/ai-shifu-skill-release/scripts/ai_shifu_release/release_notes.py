"""Collect complete, source-pinned release changes and render typed notes.

GitHub sources require authoritative, fully paginated PR metadata. Local Git
sources without an explicit GitHub identity support offline preparation; their
subject-derived PR metadata is explicitly distinguished in the snapshot.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

TYPE_ORDER = (
    "feat",
    "fix",
    "perf",
    "refactor",
    "docs",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
    "other",
)
TYPE_HEADINGS = dict(
    zip(
        TYPE_ORDER,
        (
            "Features",
            "Bug Fixes",
            "Performance",
            "Refactoring",
            "Documentation",
            "Tests",
            "Build",
            "CI",
            "Maintenance",
            "Reverts",
            "Other Changes",
        ),
    )
)
RULES_VERSION = 1
_SHA = re.compile(r"[0-9a-fA-F]{40}\Z")
_TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z")
_PREFIX = re.compile(r"^([a-z]+)(?:\([^\r\n()]+\))?(!)?:\s*", re.IGNORECASE)
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_GITHUB_URL = re.compile(
    r"(?:https?://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?\Z",
    re.IGNORECASE,
)


class _GitHubLookupError(ValueError):
    """Keep HTTP failures distinct from malformed or incomplete metadata."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def github_repository_name(source_repository: str) -> str:
    """Return owner/repository for a GitHub URL, never infer from local origin."""
    match = _GITHUB_URL.fullmatch(str(source_repository))
    return match.group(1) if match else ""


def parse_change_type(title: str) -> str:
    match = _PREFIX.match(title)
    value = match.group(1).lower() if match else "other"
    value = "feat" if value == "feature" else value
    return value if value in TYPE_ORDER else "other"


def title_body(title: str) -> str:
    """Remove a recognized type prefix while retaining a breaking marker."""
    match = _PREFIX.match(title)
    if not match or parse_change_type(title) == "other":
        return title
    return ("! " if match.group(2) else "") + title[match.end() :]


def _timestamp(value: str) -> float:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("missing timezone")
        return parsed.astimezone(timezone.utc).timestamp()
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid or missing change timestamp: {value!r}") from error


def sort_changes(changes: list[dict]) -> list[dict]:
    """Return all changes in type order, newest first within each type."""
    return sorted(
        changes,
        key=lambda change: (
            TYPE_ORDER.index(parse_change_type(change["title"])),
            -_timestamp(change["merged_at"]),
            -(change.get("number") or 0),
            change["commit"],
        ),
    )


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(
            f"Git history lookup failed ({args[0]}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _clone(source_repository: str, destination: Path, head_sha: str) -> None:
    if not _SHA.fullmatch(head_sha):
        raise ValueError("A full source commit SHA is required for release notes")
    result = subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--no-checkout",
            "--",
            str(source_repository),
            str(destination),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(f"Cannot read release source history: {result.stderr.strip()}")
    if _git(destination, "rev-parse", "--is-shallow-repository") == "true":
        _git(destination, "fetch", "--quiet", "--unshallow", "origin")
        if _git(destination, "rev-parse", "--is-shallow-repository") == "true":
            raise ValueError(
                "Release source history is incomplete (shallow repository)"
            )
    try:
        resolved = _resolve(destination, head_sha)
    except ValueError:
        _git(destination, "fetch", "--quiet", "origin", head_sha)
        resolved = _resolve(destination, head_sha)
    if resolved.lower() != head_sha.lower():
        raise ValueError("Release history does not match the requested source commit")


def _resolve(repo: Path, ref: str) -> str:
    if not isinstance(ref, str) or not ref or ref.startswith("-"):
        raise ValueError("A nonempty base reference is required")
    return _git(repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")


def _ancestor(repo: Path, ancestor: str, head: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, head],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise ValueError(f"Cannot verify release ancestry: {result.stderr.strip()}")
    return result.returncode == 0


def _github_json(endpoint: str, *, paginate: bool = False):
    """Fetch JSON, with gh following every REST Link page when requested."""
    command = ["gh", "api"]
    if paginate:
        command += ["--paginate", "--slurp"]
    command.append(endpoint)
    for attempt in range(3):
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
        except OSError as error:
            raise ValueError(
                "GitHub PR metadata requires the authenticated gh CLI"
            ) from error
        if not result.returncode:
            break
        message = result.stderr.lower()
        permanent = re.search(r"http\s+(?:400|401|403|404|422|429)\b", message)
        transient = re.search(
            r"connection reset|timeout|timed out|\beof\b|http\s+(?:502|503|504)\b",
            message,
        )
        if attempt == 2 or permanent or not transient:
            status = re.search(r"http\s+(\d{3})\b", message)
            raise _GitHubLookupError(
                f"GitHub metadata lookup failed for {endpoint}: {result.stderr.strip()}",
                int(status.group(1)) if status else None,
            )
        time.sleep(0.25 * (attempt + 1))
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid GitHub metadata for {endpoint}") from error
    if not paginate:
        return payload
    if not isinstance(payload, list) or any(
        not isinstance(page, list) for page in payload
    ):
        raise ValueError(f"Incomplete paginated GitHub metadata for {endpoint}")
    return [item for page in payload for item in page]


def _repository(source_repository: str, explicit: str) -> str:
    inferred = github_repository_name(source_repository)
    if explicit and not _REPOSITORY.fullmatch(explicit):
        raise ValueError("GitHub repository must use owner/repository")
    if explicit and inferred and explicit.lower() != inferred.lower():
        raise ValueError(
            "GitHub metadata repository differs from the source repository"
        )
    return explicit or inferred


def _branch_ref(repo: Path, branch: str) -> str:
    ref = f"refs/remotes/origin/{branch}"
    try:
        return _resolve(repo, ref)
    except ValueError:
        try:
            _git(repo, "fetch", "--quiet", "origin", f"refs/heads/{branch}:{ref}")
        except ValueError:
            # actions/checkout can leave a detached local source with only
            # remote-tracking refs. A second clone does not copy those refs.
            _git(
                repo,
                "fetch",
                "--quiet",
                "origin",
                f"refs/remotes/origin/{branch}:{ref}",
            )
        return _resolve(repo, ref)


def _default_branch(repo: Path, repository: str = "") -> str:
    if repository:
        metadata = _github_json(f"repos/{repository}")
        branch = metadata.get("default_branch") if isinstance(metadata, dict) else None
        if not isinstance(branch, str) or not branch or branch.startswith("-"):
            raise ValueError("Cannot determine the GitHub source's default branch")
        _branch_ref(repo, branch)
        return branch
    # A local fixture's checked-out feature branch is not its release branch.
    for branch in ("main", "master"):
        try:
            _branch_ref(repo, branch)
            return branch
        except ValueError:
            pass
    result = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip().removeprefix("refs/remotes/origin/")
    raise ValueError("Cannot determine the release source's target branch")


def _matches_paths(files: list[str], paths: tuple[str, ...]) -> bool:
    return not paths or any(
        filename == path.rstrip("/") or filename.startswith(path.rstrip("/") + "/")
        for filename in files
        for path in paths
    )


def _commit_files(repo: Path, sha: str, parents: list[str]) -> list[str]:
    if parents:
        return _git(repo, "diff", "--name-only", parents[0], sha, "--").splitlines()
    return _git(
        repo, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha
    ).splitlines()


def _commit_data(repo: Path, sha: str) -> dict:
    values = _git(
        repo, "show", "-s", "--format=%P%x00%s%x00%b%x00%aN%x00%cI", sha
    ).split("\0")
    if len(values) != 5:
        raise ValueError(f"Cannot read source commit {sha}")
    parents, subject, body, author, timestamp = values
    return {
        "commit": sha,
        "parents": parents.split(),
        "title": subject,
        "body": body,
        "author": author,
        "merged_at": timestamp,
    }


def _offline_pr(commit: dict) -> tuple[int | None, str]:
    title = commit["title"]
    merge = re.match(r"^Merge pull request #(\d+)\b", title)
    suffix = re.search(r"\s*\(#(\d+)\)\s*$", title)
    if merge:
        body = commit["body"].strip().splitlines()
        return int(merge.group(1)), body[0] if body else title
    if suffix:
        return int(suffix.group(1)), title[: suffix.start()].rstrip()
    return None, title


def _collect(
    repo: Path,
    source_repository: str,
    head_sha: str,
    base_ref: str,
    repository: str,
    paths: tuple[str, ...],
    preview: bool,
) -> dict:
    base_sha = _resolve(repo, base_ref) if base_ref else ""
    if base_sha and not _ancestor(repo, base_sha, head_sha):
        raise ValueError("Release base is not an ancestor of the source commit")
    span = f"{base_sha}..{head_sha}" if base_sha else head_sha
    mainline = _git(repo, "rev-list", "--first-parent", span).splitlines()
    range_commits = _git(repo, "rev-list", span).splitlines()
    all_commits = set(range_commits)
    mainline_set = set(mainline)
    target_branch = _default_branch(repo, repository)
    target_head = _resolve(repo, f"refs/remotes/origin/{target_branch}")
    if not preview and not _ancestor(repo, head_sha, target_head):
        raise ValueError(
            "Source commit is not on the target branch; use preview for unmerged changes"
        )
    changes: list[dict] = []
    seen_prs: set[int] = set()
    details: dict[int, dict | None] = {}
    pr_files: dict[int, list[str]] = {}
    unmerged_shas = (
        all_commits - set(_git(repo, "rev-list", target_head).splitlines())
        if preview
        else set()
    )
    # Actions' test merge pins the trial packages, but its first parent only
    # contains main. Include the unmerged branch ancestry for preview notes;
    # merged PR eligibility keeps the original first-parent integration set.
    collection_commits = mainline + [
        sha for sha in range_commits if sha in unmerged_shas and sha not in mainline_set
    ]
    commit_data = {sha: _commit_data(repo, sha) for sha in collection_commits}
    hinted_prs = {
        sha: number
        for sha, commit in commit_data.items()
        if sha not in unmerged_shas
        for number, _ in [_offline_pr(commit)]
        if number is not None
    }
    associations_by_sha: dict[str, list[dict]] = {}
    if repository:

        def association_metadata(sha: str) -> tuple[str, list[dict]]:
            associations = _github_json(
                f"repos/{repository}/commits/{sha}/pulls?per_page=100",
                paginate=True,
            )
            if not isinstance(associations, list):
                raise ValueError(  # noqa: TRY004 - Invalid external payload.
                    f"Invalid PR association list for {sha}"
                )
            for association in associations:
                number = (
                    association.get("number") if isinstance(association, dict) else None
                )
                if (
                    not isinstance(number, int)
                    or isinstance(number, bool)
                    or number <= 0
                ):
                    raise ValueError(f"Missing PR identity associated with {sha}")
            return sha, associations

        def detail_metadata(number: int) -> tuple[int, dict | None]:
            try:
                return number, _github_json(f"repos/{repository}/pulls/{number}")
            except _GitHubLookupError as error:
                # An issue reference can resemble a squash-merge PR suffix.
                # Only a missing hint is optional; authoritative PR failures
                # and all other API failures must still abort collection.
                if error.status == 404 and number not in associated_numbers:
                    return number, None
                raise

        # Read-only requests are independent; consume their results in source
        # order so request completion order can never change the notes.
        with ThreadPoolExecutor(max_workers=4) as executor:
            associations_by_sha = dict(
                executor.map(
                    association_metadata,
                    (sha for sha in collection_commits if sha not in unmerged_shas),
                )
            )
            associated_numbers = {
                association["number"]
                for associations in associations_by_sha.values()
                for association in associations
            }
            numbers = sorted(associated_numbers | set(hinted_prs.values()))
            details = dict(executor.map(detail_metadata, numbers))
    for sha in collection_commits:
        commit = commit_data[sha]
        unmerged = sha in unmerged_shas
        found_pr = False
        if repository and not unmerged:
            candidates = [
                (association["number"], False)
                for association in associations_by_sha[sha]
            ]
            hint = hinted_prs.get(sha)
            if (
                hint is not None
                and not any(number == hint for number, _ in candidates)
                and details[hint] is not None
            ):
                candidates.append((hint, True))
            for number, hint_only in candidates:
                pr = details[number]
                if not isinstance(pr, dict) or pr.get("number") != number:
                    raise ValueError(f"Invalid details for PR #{number}")
                base = pr.get("base") or {}
                base_repo = (base.get("repo") or {}).get("full_name", "")
                if base_repo.lower() != repository.lower():
                    raise ValueError(f"PR #{number} belongs to a different repository")
                if not isinstance(pr.get("merged"), bool):
                    raise ValueError(  # noqa: TRY004 - Invalid external payload.
                        f"Missing merge status for PR #{number}"
                    )
                if not pr["merged"] or base.get("ref") != target_branch:
                    continue
                merge_sha = pr.get("merge_commit_sha")
                if hint_only and merge_sha != sha:
                    continue
                if merge_sha not in all_commits or merge_sha not in mainline_set:
                    continue
                found_pr = True
                if number in seen_prs:
                    continue
                if paths:
                    if number not in pr_files:
                        files = _github_json(
                            f"repos/{repository}/pulls/{number}/files?per_page=100",
                            paginate=True,
                        )
                        if not isinstance(files, list) or any(
                            not isinstance(item, dict) or not item.get("filename")
                            for item in files
                        ):
                            raise ValueError(f"Incomplete file list for PR #{number}")
                        expected_files = pr.get("changed_files")
                        if (
                            not isinstance(expected_files, int)
                            or len(files) != expected_files
                        ):
                            raise ValueError(
                                f"Incomplete file list for PR #{number}; GitHub limits PR file results"
                            )
                        pr_files[number] = [
                            filename
                            for item in files
                            for filename in (
                                item["filename"],
                                item.get("previous_filename", ""),
                            )
                            if filename
                        ]
                    if not _matches_paths(pr_files[number], paths):
                        seen_prs.add(number)
                        continue
                title = pr.get("title")
                timestamp = pr.get("merged_at")
                url = pr.get("html_url")
                if (
                    not isinstance(title, str)
                    or not title.strip()
                    or not isinstance(url, str)
                ):
                    raise ValueError(f"Missing title or URL for PR #{number}")
                if (
                    url.rstrip("/").lower()
                    != f"https://github.com/{repository}/pull/{number}".lower()
                ):
                    raise ValueError(f"Invalid GitHub URL for PR #{number}")
                _timestamp(timestamp)
                user = pr.get("user") or {}
                changes.append(
                    {
                        "number": number,
                        "title": title,
                        "author": user.get("login") or "",
                        "author_is_login": True,
                        "url": url,
                        "merged_at": timestamp,
                        "commit": merge_sha,
                        "change_type": parse_change_type(title),
                        "kind": "pr",
                    }
                )
                seen_prs.add(number)
        if found_pr:
            continue
        if not _matches_paths(_commit_files(repo, sha, commit["parents"]), paths):
            continue
        number, title = (
            _offline_pr(commit)
            if not repository and not unmerged
            else (None, commit["title"])
        )
        if number is not None and number in seen_prs:
            continue
        kind = "preview" if unmerged else "pr" if number is not None else "commit"
        changes.append(
            {
                "number": number,
                "title": title,
                "author": commit["author"],
                "author_is_login": False,
                "url": f"https://github.com/{repository}/commit/{sha}"
                if repository
                else "",
                "merged_at": commit["merged_at"],
                "commit": sha,
                "change_type": parse_change_type(title),
                "kind": kind,
            }
        )
        if number is not None:
            seen_prs.add(number)
    snapshot = {
        "schema_version": 1,
        "rules_version": RULES_VERSION,
        "source_repository": str(source_repository),
        "repository": repository,
        "base_ref": base_ref,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "target_branch": target_branch,
        "paths": list(paths),
        "preview": preview,
        "collection_status": "complete",
        "status": "complete",
        "complete": True,
        "pr_count": sum(change["kind"] == "pr" for change in changes),
        "pr_metadata_verified": bool(repository),
        "metadata_source": "github" if repository else "git-subjects",
        "changes": sort_changes(changes),
    }
    _fingerprint(snapshot)
    return snapshot


def _fingerprint(snapshot: dict) -> None:
    facts = {
        key: value
        for key, value in snapshot.items()
        if key not in ("facts_sha256", "fingerprint")
    }
    digest = hashlib.sha256(
        json.dumps(
            facts, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()
    snapshot["facts_sha256"] = digest
    snapshot["fingerprint"] = digest


def collect_changes(
    source_repository: str,
    head_sha: str,
    *,
    base_ref: str = "",
    github_repository: str = "",
    paths: tuple[str, ...] = (),
    preview: bool = False,
) -> dict:
    """Collect every integrated PR or direct commit in a fixed Git range."""
    repository = _repository(str(source_repository), github_repository)
    with tempfile.TemporaryDirectory(prefix="ai-shifu-notes-") as temporary:
        repo = Path(temporary) / "history"
        _clone(str(source_repository), repo, head_sha)
        return _collect(
            repo,
            str(source_repository),
            head_sha,
            base_ref,
            repository,
            tuple(paths),
            preview,
        )


def _version(value: str) -> tuple[int, int, int]:
    match = _TAG.fullmatch("v" + value)
    if not match:
        raise ValueError(f"Invalid release version: {value!r}")
    return tuple(int(part) for part in match.groups())


def _previous_release(repo: Path, repository: str, head_sha: str, version: str) -> str:
    target_version = _version(version)
    history = _git(repo, "rev-list", "--first-parent", head_sha).splitlines()
    distance = {sha: index for index, sha in enumerate(history)}
    if repository:
        releases = _github_json(
            f"repos/{repository}/releases?per_page=100", paginate=True
        )
        if not isinstance(releases, list):
            raise ValueError("Invalid published release history")
        tags = []
        for release in releases:
            if not isinstance(release, dict) or not isinstance(
                release.get("tag_name"), str
            ):
                raise ValueError(  # noqa: TRY004 - Invalid external payload.
                    "Incomplete published release history"
                )
            if not isinstance(release.get("draft"), bool) or not isinstance(
                release.get("prerelease"), bool
            ):
                raise ValueError(  # noqa: TRY004 - Invalid external payload.
                    "Incomplete published release status"
                )
            if not release["draft"] and not release["prerelease"]:
                tags.append(release["tag_name"])
    else:
        tags = _git(repo, "tag", "--list", "v*").splitlines()
    candidates = []
    for tag in tags:
        match = _TAG.fullmatch(tag)
        if not match:
            continue
        tag_version = tuple(int(part) for part in match.groups())
        if tag_version >= target_version:
            continue
        try:
            sha = _resolve(repo, f"refs/tags/{tag}")
        except ValueError:
            _git(repo, "fetch", "--quiet", "origin", f"refs/tags/{tag}:refs/tags/{tag}")
            sha = _resolve(repo, f"refs/tags/{tag}")
        if sha in distance:
            candidates.append(
                (distance[sha], tuple(-part for part in tag_version), tag)
            )
    return min(candidates)[2] if candidates else ""


def generate_notes(
    source_repository: str,
    head_sha: str,
    version: str,
    *,
    base_ref: str | None = None,
    github_repository: str = "",
    preview: bool = False,
) -> dict:
    """Generate source-pinned notes, selecting a prior published release by default."""
    _version(version)
    repository = _repository(str(source_repository), github_repository)
    with tempfile.TemporaryDirectory(prefix="ai-shifu-notes-") as temporary:
        repo = Path(temporary) / "history"
        _clone(str(source_repository), repo, head_sha)
        selected_base = (
            _previous_release(repo, repository, head_sha, version)
            if base_ref is None
            else base_ref
        )
        snapshot = _collect(
            repo,
            str(source_repository),
            head_sha,
            selected_base,
            repository,
            (),
            preview,
        )
    snapshot["version"] = version
    snapshot["initial_release"] = not bool(selected_base)
    _fingerprint(snapshot)
    return snapshot


def _escape(value: str) -> str:
    value = " ".join(str(value).splitlines())
    return re.sub(r"([\\`*_{\[\]}<>])", r"\\\1", value)


def _render_change(change: dict) -> str:
    title = _escape(title_body(change["title"]))
    number = change.get("number")
    if number is not None:
        # Local offline records intentionally have no unverified GitHub URL.
        identity = (
            f"[#{number}]({change['url']})" if change.get("url") else f"#{number}"
        )
    else:
        short = change["commit"][:7]
        identity = f"[{short}]({change['url']})" if change.get("url") else short
    author = change.get("author")
    byline = ""
    if author:
        byline = (
            f" by {'@' if change.get('author_is_login', True) else ''}{_escape(author)}"
        )
    return f"- {title} ({identity}){byline}"


def render_changelog(snapshot: dict) -> str:
    """Render all PRs exactly once, with direct and unmerged commits separate."""
    changes = snapshot["changes"]
    if any(change.get("kind") not in ("pr", "commit", "preview") for change in changes):
        raise ValueError("Release snapshot contains an unknown change kind")
    for change in changes:
        number = change.get("number")
        if change["kind"] == "pr":
            if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                raise ValueError("Release snapshot contains an invalid PR identity")
        elif number is not None:
            raise ValueError("Only merged PR entries can contain a PR identity")
    changes = sort_changes(changes)
    numbers = [change["number"] for change in changes if change["kind"] == "pr"]
    if len(numbers) != len(set(numbers)):
        raise ValueError("Release snapshot contains duplicate PR identities")
    lines = []
    for change_type in TYPE_ORDER:
        group = [
            change
            for change in changes
            if change["kind"] == "pr"
            and parse_change_type(change["title"]) == change_type
        ]
        if group:
            lines += [f"### {TYPE_HEADINGS[change_type]}", ""]
            lines += [_render_change(change) for change in group]
            lines.append("")
    for kind, heading in (
        ("commit", "Additional commits"),
        ("preview", "Unmerged preview changes"),
    ):
        group = [change for change in changes if change["kind"] == kind]
        if group:
            lines += [f"### {heading}", ""]
            lines += [_render_change(change) for change in group]
            lines.append("")
    if not lines:
        return "- No changes in this release range."
    return "\n".join(lines).rstrip()


def render_notes(snapshot: dict) -> str:
    """Render the existing package boundary with a complete typed changelog."""
    lines = [
        f"AI-Shifu Skills {snapshot.get('version', '')}".rstrip(),
        "",
        f"Source commit: {snapshot['head_sha']}",
        "",
    ]
    if snapshot.get("draft_preview"):
        lines += ["**TEST DRAFT ONLY — do not publish this Release.**", ""]
    elif snapshot.get("preview"):
        lines += ["**PREVIEW ONLY — includes changes that may not be merged.**", ""]
    status = snapshot.get("collection_status", "unknown")
    count = sum(change.get("kind") == "pr" for change in snapshot["changes"])
    lines += [f"Collection status: {status}. Pull requests: {count}.", ""]
    if snapshot.get("initial_release") or not snapshot.get("base_sha"):
        lines += ["Initial release", ""]
    else:
        lines += [f"Base: {snapshot['base_ref']} ({snapshot['base_sha']})", ""]
    lines += [
        (
            "Packages: ClawHub and SkillHub standalone skills; WorkBuddy expert plugin; "
            "Doubao Work partner package. These are downloadable installation packages. "
            "Publication to each channel is tracked separately."
        ),
        "",
    ]
    if not snapshot.get("pr_metadata_verified"):
        lines += [
            "Offline Git history preview: PR metadata has not been verified with GitHub.",
            "",
        ]
    lines += ["## Changelog", "", render_changelog(snapshot), ""]
    if snapshot.get("repository") and snapshot.get("base_sha"):
        url = f"https://github.com/{snapshot['repository']}/compare/{snapshot['base_sha']}...{snapshot['head_sha']}"
        lines += [f"[Full comparison]({url})", ""]
    return "\n".join(lines)


def write_notes(snapshot: dict, output_dir: Path) -> tuple[Path, Path]:
    """Save the complete fact snapshot and its matching Markdown preview."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _fingerprint(snapshot)
    json_path = output_dir / "release-notes.json"
    markdown_path = output_dir / "release-notes.md"
    json_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_notes(snapshot), encoding="utf-8")
    return json_path, markdown_path
