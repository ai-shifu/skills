#!/usr/bin/env python3
"""AI-Shifu Course CLI - Unified tool for course CRUD operations."""

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

# ── Constants ──────────────────────────────────────────────────────────────────
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

DEFAULT_BASE_URL = "https://app.ai-shifu.cn"


# ── Shared Infrastructure ──────────────────────────────────────────────────────
def load_env():
    """Load environment variables from the skill's .env file."""
    if ENV_FILE.exists():
        load_dotenv(dotenv_path=ENV_FILE, override=False)


def save_env(token):
    """Persist token to the skill's .env file."""
    env_path = str(ENV_FILE)
    if not ENV_FILE.exists():
        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENV_FILE.touch(mode=0o600)
    set_key(env_path, "SHIFU_TOKEN", token)
    os.chmod(env_path, 0o600)


def resolve_auth(args):
    """Resolve token from CLI args or .env. Base URL is fixed to DEFAULT_BASE_URL."""
    token = getattr(args, "token", None) or os.environ.get("SHIFU_TOKEN")
    if not token:
        print("Error: no token available. Run 'shifu-cli.py login' first, "
              "or use --token / set SHIFU_TOKEN in .env")
        sys.exit(1)

    return DEFAULT_BASE_URL, token


def api(base_url, token, method, path, **kwargs):
    """Make an API call, exit on error."""
    url = f"{base_url}/api/shifu{path}"
    headers = {"Cookie": f"token={token}", "Content-Type": "application/json"}
    kwargs.setdefault("timeout", 30)
    resp = getattr(requests, method)(url, headers=headers, **kwargs)
    if not resp.ok:
        print(f"API error: {method.upper()} {path} (HTTP {resp.status_code})")
        print(f"  Response: {resp.text[:500]}")
        sys.exit(1)
    data = resp.json()
    if data.get("code") != 0:
        print(f"API error: {method.upper()} {path}")
        print(f"  Response: {json.dumps(data, ensure_ascii=False)}")
        sys.exit(1)
    return data.get("data")


def api_safe(base_url, token, method, path, **kwargs):
    """Make an API call, return None on error instead of exiting."""
    url = f"{base_url}/api/shifu{path}"
    headers = {"Cookie": f"token={token}", "Content-Type": "application/json"}
    kwargs.setdefault("timeout", 30)
    try:
        resp = getattr(requests, method)(url, headers=headers, **kwargs)
        if not resp.ok:
            return None
        data = resp.json()
        if data.get("code") != 0:
            return None
        return data.get("data")
    except (requests.RequestException, json.JSONDecodeError):
        return None


def safe_join_path(base_dir, filename):
    """Safely join base_dir and filename, preventing path traversal attacks."""
    joined = os.path.realpath(os.path.join(base_dir, filename))
    base = os.path.realpath(base_dir)
    if not joined.startswith(base + os.sep) and joined != base:
        print(f"Warning: path traversal detected, rejecting: {filename}")
        return None
    return joined


def fmt_time(ts):
    """Format an ISO timestamp for display, return '' if missing."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts[:16] if len(ts) >= 16 else ts


# ── course.json Schema Validator ───────────────────────────────────────────────
# See ADR-001 §D3 and adr-001-implementation-plan.md S1 for the rules.
PLACEHOLDER_PREFIX = "new:"


def _is_placeholder_bid(bid):
    """A bid is a placeholder if it starts with 'new:'. Real server bids are 32-char hex UUIDs."""
    return isinstance(bid, str) and bid.startswith(PLACEHOLDER_PREFIX)


def _collect_structure_bids(structure, path="structure", errors=None, seen=None):
    """Recursively walk the structure tree and collect every outline_item_bid.

    Returns the flat set of bids found. Records duplicate-bid errors and
    malformed-node errors into `errors`.
    """
    if errors is None:
        errors = []
    if seen is None:
        seen = set()
    if not isinstance(structure, list):
        errors.append(f"{path}: must be a JSON array")
        return seen
    for i, node in enumerate(structure):
        node_path = f"{path}[{i}]"
        if not isinstance(node, dict):
            errors.append(f"{node_path}: must be an object")
            continue
        bid = node.get("outline_item_bid")
        if not isinstance(bid, str) or not bid:
            errors.append(f"{node_path}: missing or empty 'outline_item_bid'")
        else:
            if bid in seen:
                errors.append(f"{node_path}: duplicate outline_item_bid {bid!r} in structure tree")
            seen.add(bid)
        children = node.get("children", [])
        if not isinstance(children, list):
            errors.append(f"{node_path}.children: must be an array")
        else:
            _collect_structure_bids(children, f"{node_path}.children", errors, seen)
    return seen


def _validate_course_json(data, mode="push"):
    """Validate a course.json document against the ADR-001 §D3 schema.

    Args:
        data: Parsed JSON dict.
        mode: "push" (no placeholder bids allowed) or "import" (placeholders allowed).

    Returns:
        list[str]: error messages (empty list means valid).
    """
    if mode not in ("push", "import"):
        raise ValueError(f"_validate_course_json: invalid mode {mode!r}")
    errors = []

    if not isinstance(data, dict):
        return ["root: course.json must be a JSON object"]

    # Top-level keys
    required_top = ["version", "course", "structure", "items", "global_variables", "deployment"]
    for k in required_top:
        if k not in data:
            errors.append(f"root: missing required field {k!r}")
    if errors:
        return errors  # Don't probe further if structure is incomplete.

    # course block
    course = data["course"]
    if not isinstance(course, dict):
        errors.append("course: must be an object")
    else:
        title = course.get("title", "")
        if not isinstance(title, str) or not title.strip():
            errors.append("course.title: required, must be a non-empty string")
        cp = course.get("course_prompt", "")
        if not isinstance(cp, str):
            errors.append("course.course_prompt: must be a string (may be empty)")

    # items block
    items = data["items"]
    if not isinstance(items, dict):
        errors.append("items: must be an object keyed by outline_item_bid")
        items = {}
    else:
        for bid, item in items.items():
            ipath = f"items[{bid!r}]"
            if not isinstance(item, dict):
                errors.append(f"{ipath}: must be an object")
                continue
            t = item.get("type")
            if t not in ("chapter", "lesson"):
                errors.append(f"{ipath}.type: must be 'chapter' or 'lesson', got {t!r}")
            title = item.get("title", "")
            if not isinstance(title, str):
                errors.append(f"{ipath}.title: must be a string")
            mdf = item.get("markdownflow_prompt", "")
            if not isinstance(mdf, str):
                errors.append(f"{ipath}.markdownflow_prompt: must be a string (may be empty)")
            if mode == "push" and _is_placeholder_bid(bid):
                errors.append(f"{ipath}: placeholder bid {bid!r} not allowed in push mode "
                              "(should have been replaced with a real bid)")

    # structure tree
    structure_bids = _collect_structure_bids(data["structure"], errors=errors)

    # Cross-validate items <-> structure correspondence
    items_bids = set(items.keys()) if isinstance(items, dict) else set()
    only_in_structure = structure_bids - items_bids
    only_in_items = items_bids - structure_bids
    for bid in sorted(only_in_structure):
        errors.append(f"structure references outline_item_bid {bid!r} that is missing from items{{}}")
    for bid in sorted(only_in_items):
        errors.append(f"items contains outline_item_bid {bid!r} that is missing from structure tree")

    if mode == "push":
        for bid in structure_bids:
            if _is_placeholder_bid(bid):
                errors.append(f"structure references placeholder bid {bid!r} in push mode")

    # deployment block
    deployment = data["deployment"]
    if not isinstance(deployment, dict):
        errors.append("deployment: must be an object")
    else:
        rev_map = deployment.get("draft_pulled_at_revision", {})
        if rev_map and not isinstance(rev_map, dict):
            errors.append("deployment.draft_pulled_at_revision: must be an object {bid: int}")
        elif isinstance(rev_map, dict):
            for bid in rev_map:
                if _is_placeholder_bid(bid):
                    errors.append(
                        f"deployment.draft_pulled_at_revision: placeholder bid {bid!r} should not have a revision"
                    )
                if bid not in items_bids:
                    errors.append(
                        f"deployment.draft_pulled_at_revision[{bid!r}]: not present in items{{}}"
                    )

    return errors


def _load_course_json(path):
    """Load and parse a course.json file. Exit on read or parse error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: course file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def _atomic_write_json(path, data):
    """Write JSON to path atomically (temp file + rename). Pretty-printed UTF-8."""
    path = os.fspath(path)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


# ── Course directory layout ───────────────────────────────────────────────────
# A course is a directory containing course.json plus optional reserved subdirs
# (assets/ for binary resources to upload to OSS, drafts/ for extract/embed
# scratch files, etc.). See ADR-001 §D2.
COURSE_JSON_FILENAME = "course.json"


def _course_json_path(course_dir):
    """Resolve <course-dir>/course.json. Accepts a directory path; returns the path
    to the canonical course.json file inside it."""
    return os.path.join(os.fspath(course_dir), COURSE_JSON_FILENAME)


def _ensure_course_dir(course_dir):
    """Create the course directory if it does not yet exist. No-op if it does."""
    os.makedirs(os.fspath(course_dir), exist_ok=True)


# ── Wire <-> course.json transformation ────────────────────────────────────────
# See ADR-001 §D3 (schema) and §D10 (pull protocol).
# Platform UNIT_TYPE values (see ai-shifu/src/api/flaskr/service/shifu/consts.py):
#   400 = "guest"  (default; typically used for top-level chapters)
#   401 = "trial"  (typically used for child lessons)
#   402 = "normal" (paid content)
# We map int -> local type; the local type names "chapter" / "lesson" reflect typical
# usage but the platform itself only enforces access-level semantics.
WIRE_TYPE_TO_LOCAL = {400: "chapter", 401: "lesson", 402: "lesson"}
LOCAL_TYPE_TO_WIRE_NAME = {"chapter": "guest", "lesson": "trial"}


def _wire_type_to_local(wire_type):
    """Convert platform outline_item type (int) to local 'chapter'/'lesson'."""
    if wire_type is None:
        return "lesson"
    try:
        return WIRE_TYPE_TO_LOCAL.get(int(wire_type), "lesson")
    except (TypeError, ValueError):
        return "lesson"


def _local_type_to_wire_name(local_type):
    """Convert local 'chapter'/'lesson' to the wire string name ('guest'/'trial')."""
    return LOCAL_TYPE_TO_WIRE_NAME.get(local_type, "trial")


def _transform_export_to_course(export):
    """Map an ai-shifu export-endpoint JSON document to a course.json document.

    See ADR-001 §D10 for the field mapping table.
    """
    if not isinstance(export, dict):
        raise ValueError("export response is not a JSON object")

    shifu = export.get("shifu") or {}
    outline_items = export.get("outline_items") or []
    structure_wire = export.get("structure") or {}

    course = {
        "title": shifu.get("title", "") or "",
        "description": shifu.get("description", "") or "",
        "course_prompt": shifu.get("llm_system_prompt", "") or "",
        "language": "",  # export endpoint does not return language; user fills if needed
    }

    items = {}
    for oi in outline_items:
        if not isinstance(oi, dict):
            continue
        bid = oi.get("outline_item_bid")
        if not isinstance(bid, str) or not bid:
            continue
        items[bid] = {
            "type": _wire_type_to_local(oi.get("type")),
            "title": oi.get("title", "") or "",
            "markdownflow_prompt": oi.get("content", "") or "",
            "used_variables": [],
            "depends_on_lessons": [],
            "source_span_map": [],
        }

    def convert_outline_node(node):
        """Recursively convert a wire structure node (type='outline') to local form."""
        return {
            "outline_item_bid": node.get("bid", "") or "",
            "children": [
                convert_outline_node(c)
                for c in (node.get("children") or [])
                if isinstance(c, dict) and c.get("type") == "outline"
            ],
        }

    structure = []
    # The wire structure root is type='shifu'; outline nodes are its direct children.
    if isinstance(structure_wire, dict) and structure_wire.get("type") == "shifu":
        for top in structure_wire.get("children") or []:
            if isinstance(top, dict) and top.get("type") == "outline":
                structure.append(convert_outline_node(top))

    return {
        "version": "1.0",
        "course": course,
        "structure": structure,
        "items": items,
        "global_variables": [],
        "deployment": {
            "shifu_bid": shifu.get("shifu_bid", "") or "",
            "deployed_url": "",
            "draft_last_pushed_at": None,
            "draft_pulled_at_revision": {},
            "published_at": None,
        },
    }


def _fetch_export(base_url, token, shifu_bid):
    """Download the /export endpoint (file download, not the {code,message,data} envelope).

    Returns the parsed JSON document. Exits on error.
    """
    url = f"{base_url}/api/shifu/shifus/{shifu_bid}/export"
    headers = {"Cookie": f"token={token}"}
    try:
        resp = requests.get(url, headers=headers, timeout=60)
    except requests.RequestException as e:
        print(f"Error: GET /shifus/{shifu_bid}/export failed: {e}", file=sys.stderr)
        sys.exit(1)
    if not resp.ok:
        print(f"Error: GET /shifus/{shifu_bid}/export (HTTP {resp.status_code})", file=sys.stderr)
        print(f"  Response: {resp.text[:500]}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(resp.text)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON from export endpoint: {e}", file=sys.stderr)
        print(f"  First 200 chars: {resp.text[:200]!r}", file=sys.stderr)
        sys.exit(1)


def _fetch_revision(base_url, token, shifu_bid, outline_bid):
    """Fetch the current draft revision for one outline_item via /draft-meta. Returns int or None."""
    meta = api_safe(base_url, token, "get",
                    f"/shifus/{shifu_bid}/draft-meta",
                    params={"outline_bid": outline_bid})
    if isinstance(meta, dict):
        rev = meta.get("revision")
        if isinstance(rev, int):
            return rev
    return None


# ── Login ──────────────────────────────────────────────────────────────────────
def _login_post(base_url, path, payload, error_prefix):
    """POST to a user-auth endpoint and return parsed JSON, exit on failure."""
    resp = requests.post(
        f"{base_url}{path}",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    if not resp.ok:
        print(f"{error_prefix} (HTTP {resp.status_code}): {resp.text[:200]}")
        sys.exit(1)
    data = resp.json()
    if data.get("code") != 0:
        print(f"{error_prefix}: {data}")
        sys.exit(1)
    return data


def cmd_login(args):
    """SMS login and save token (non-interactive two-step flow)."""
    base_url = DEFAULT_BASE_URL

    phone = args.phone
    if not phone:
        print("Error: --phone is required for login")
        sys.exit(1)

    sms_code = args.sms_code
    masked = phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else phone

    if sms_code:
        # Step 2: Verify code and save token
        print("Verifying code...")
        data = _login_post(base_url, "/api/user/verify_sms_code",
                           {"mobile": phone, "sms_code": sms_code, "login_context": "admin"}, "Verification failed")

        token = data.get("data")
        if not token:
            print(f"No token in response: {data}")
            sys.exit(1)
        # API may return token as a dict (e.g. {"token": "..."}) or a plain string
        if isinstance(token, dict):
            token = token.get("token", "")
        if not token:
            print(f"No token string found in response data: {data}")
            sys.exit(1)

        save_env(token)
        print(f"Login successful! Token saved to {ENV_FILE}")
    else:
        # Step 1: Send SMS code only, then exit
        print(f"Sending SMS code to {masked}...")
        _login_post(base_url, "/api/user/send_sms_code",
                    {"mobile": phone}, "Failed to send SMS")
        print(f"SMS code sent to {masked}. "
              f"Run again with --sms-code <4-digit-code> to complete login.")


# ── List ───────────────────────────────────────────────────────────────────────
def cmd_list(args):
    """List all courses."""
    base_url, token = resolve_auth(args)
    result = api(base_url, token, "get", "/shifus")

    if not result:
        print("No courses found.")
        return

    courses = result if isinstance(result, list) else result.get("items", [])
    if not courses:
        print("No courses found.")
        return

    # Table output
    print(f"{'BID':<34} {'Name':<30} {'Status':<10} {'Updated':<18}")
    print("-" * 94)
    for c in courses:
        bid = c.get("bid", c.get("shifu_bid", ""))
        name = c.get("name", c.get("title", ""))[:28]
        status = c.get("status", "")
        updated = fmt_time(c.get("updated_at", ""))
        print(f"{bid:<34} {name:<30} {status:<10} {updated:<18}")

    print(f"\nTotal: {len(courses)} courses")


# ── Show ───────────────────────────────────────────────────────────────────────
def cmd_show(args):
    """Show course detail / outline tree / MarkdownFlow content."""
    base_url, token = resolve_auth(args)
    shifu_bid = args.shifu_bid
    outline_bid = args.outline_bid

    if outline_bid:
        # Show MarkdownFlow content for a specific lesson
        result = api(base_url, token, "get",
                     f"/shifus/{shifu_bid}/outlines/{outline_bid}/mdflow")
        content = result.get("data", "") if isinstance(result, dict) else result
        revision = result.get("revision", "") if isinstance(result, dict) else ""
        if revision:
            print(f"# Revision: {revision}\n")
        print(content)
    else:
        # Show course detail + outline tree
        detail = api_safe(base_url, token, "get", f"/shifus/{shifu_bid}/detail")
        if detail:
            print(f"Course: {detail.get('name', '')}")
            print(f"BID:    {shifu_bid}")
            desc = detail.get("description", "")
            if desc:
                print(f"Desc:   {desc}")
            model = detail.get("model", "")
            if model:
                print(f"Model:  {model}")
            print()

        tree = api(base_url, token, "get", f"/shifus/{shifu_bid}/outlines")
        if not tree:
            print("No outlines found.")
            return

        def print_tree(items, indent=0):
            for item in items:
                prefix = "  " * indent
                bid = item.get("bid", "")
                name = item.get("name", "")
                print(f"{prefix}- [{bid}] {name}")
                children = item.get("children", [])
                if children:
                    print_tree(children, indent + 1)

        print("Outline tree:")
        print_tree(tree if isinstance(tree, list) else [tree])


# ── History ────────────────────────────────────────────────────────────────────
def cmd_history(args):
    """Show MarkdownFlow revision history for a lesson."""
    base_url, token = resolve_auth(args)
    result = api(base_url, token, "get",
                 f"/shifus/{args.shifu_bid}/outlines/{args.outline_bid}/mdflow/history")

    if not result:
        print("No history found.")
        return

    items = result if isinstance(result, list) else result.get("items", [])
    for item in items:
        rev = item.get("revision", "")
        ts = fmt_time(item.get("created_at", ""))
        user = item.get("created_user_bid", "")
        print(f"  {rev}  {ts}  by {user}")


# ── Export ─────────────────────────────────────────────────────────────────────
def cmd_export(args):
    """Export a course to JSON via backend export API."""
    base_url, token = resolve_auth(args)
    shifu_bid = args.shifu_bid

    # Backend export API returns a file download (not standard JSON envelope)
    url = f"{base_url}/api/shifu/shifus/{shifu_bid}/export"
    headers = {"Cookie": f"token={token}"}
    resp = requests.get(url, headers=headers, timeout=60)

    if resp.status_code != 200:
        print(f"Export failed (HTTP {resp.status_code})")
        try:
            print(f"  Response: {resp.json()}")
        except Exception:
            print(f"  Response: {resp.text[:200]}")
        sys.exit(1)

    if args.output:
        outpath = args.output
        os.makedirs(os.path.dirname(outpath) or ".", exist_ok=True)
        with open(outpath, "wb") as f:
            f.write(resp.content)
        # Count lessons from exported data
        try:
            data = resp.json()
            count = len(data.get("outline_items", []))
            print(f"Exported to {outpath} ({count} lessons)")
        except Exception:
            print(f"Exported to {outpath}")
    else:
        # Pretty-print to stdout
        try:
            data = resp.json()
            print(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception:
            print(resp.text)


# ── Create ─────────────────────────────────────────────────────────────────────
def cmd_create(args):
    """Create a new empty course."""
    base_url, token = resolve_auth(args)
    result = api(base_url, token, "put", "/shifus",
                 json={"name": args.name,
                       "description": args.description or ""})
    bid = result.get("bid") or result.get("shifu_bid")
    print(f"Created course: {bid}")
    print(f"  Name: {args.name}")
    print(f"  URL:  {base_url}/shifu/{bid}")


# ── Update Meta ────────────────────────────────────────────────────────────────
def cmd_update_meta(args):
    """Update course metadata (name, description, system prompt, etc.)."""
    base_url, token = resolve_auth(args)
    shifu_bid = args.shifu_bid

    # Fetch current detail to preserve unchanged fields
    current = api(base_url, token, "get", f"/shifus/{shifu_bid}/detail")

    system_prompt = current.get("system_prompt", "")
    if args.system_prompt_file:
        with open(args.system_prompt_file, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()

    keywords = current.get("keywords", "")
    if isinstance(keywords, list):
        pass  # already a list
    elif isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    payload = {
        "name": args.name if args.name is not None else current.get("name", ""),
        "description": args.description if args.description is not None
                       else current.get("description", ""),
        "avatar": current.get("avatar", ""),
        "keywords": keywords,
        "model": current.get("model", ""),
        "temperature": current.get("temperature", 0.3),
        "system_prompt": system_prompt,
        "tts_enabled": current.get("tts_enabled", False),
        "tts_provider": current.get("tts_provider", "minimax"),
        "tts_model": current.get("tts_model", ""),
        "tts_voice_id": current.get("tts_voice_id", ""),
        "tts_speed": current.get("tts_speed", 1.0),
        "tts_pitch": current.get("tts_pitch", 0),
        "tts_emotion": current.get("tts_emotion", ""),
        "use_learner_language": current.get("use_learner_language", False),
    }
    price = current.get("price")
    if price and price > 0:
        payload["price"] = price

    api(base_url, token, "post", f"/shifus/{shifu_bid}/detail", json=payload)
    print(f"Updated metadata for {shifu_bid}")


# ── Add Chapter ────────────────────────────────────────────────────────────────
def cmd_add_chapter(args):
    """Add a new top-level chapter to a course."""
    base_url, token = resolve_auth(args)
    shifu_bid = args.shifu_bid

    result = api(base_url, token, "put", f"/shifus/{shifu_bid}/outlines",
                 json={"name": args.name})
    outline_bid = result.get("bid") or result.get("outline_item_bid")
    if not outline_bid:
        print(f"Error: chapter created but response did not include a BID", file=sys.stderr)
        print(f"  Response: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)
    print(f"Created chapter: {outline_bid} ({args.name})")


# ── Add Lesson ─────────────────────────────────────────────────────────────────
def cmd_add_lesson(args):
    """Add a new lesson to a course."""
    base_url, token = resolve_auth(args)
    shifu_bid = args.shifu_bid

    # Create outline
    outline_payload = {"name": args.name}
    if args.parent_bid:
        outline_payload["parent_bid"] = args.parent_bid

    result = api(base_url, token, "put", f"/shifus/{shifu_bid}/outlines",
                 json=outline_payload)
    outline_bid = result.get("bid") or result.get("outline_item_bid")
    parent_label = f" under {args.parent_bid}" if args.parent_bid else ""
    print(f"Created lesson: {outline_bid} ({args.name}){parent_label}")

    # Write MarkdownFlow content if provided
    if args.markdownflow_file:
        with open(args.markdownflow_file, "r", encoding="utf-8") as f:
            content = f.read()
        api(base_url, token, "post",
            f"/shifus/{shifu_bid}/outlines/{outline_bid}/mdflow",
            json={"data": content})
        print(f"  MarkdownFlow saved ({len(content)} chars)")


# ── Update Lesson ──────────────────────────────────────────────────────────────
def cmd_update_lesson(args):
    """Update MarkdownFlow content for an existing lesson (with optimistic locking)."""
    base_url, token = resolve_auth(args)
    shifu_bid = args.shifu_bid
    outline_bid = args.outline_bid

    # Step 1: Get current revision from draft-meta (mdflow GET returns content string,
    # not metadata; revision lives on the draft-meta endpoint).
    meta = api(base_url, token, "get",
               f"/shifus/{shifu_bid}/draft-meta",
               params={"outline_bid": outline_bid})
    base_revision = meta.get("revision") if isinstance(meta, dict) else None

    # Step 2: Read new content
    with open(args.markdownflow_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Step 3: POST with base_revision (use `is not None` so revision=0 is preserved)
    payload = {"data": content}
    if base_revision is not None:
        payload["base_revision"] = base_revision

    api(base_url, token, "post",
        f"/shifus/{shifu_bid}/outlines/{outline_bid}/mdflow",
        json=payload)
    print(f"Updated lesson {outline_bid} ({len(content)} chars)")
    if base_revision is not None:
        print(f"  Base revision: {base_revision}")


# ── Rename Lesson ──────────────────────────────────────────────────────────────
def cmd_rename_lesson(args):
    """Rename an existing lesson."""
    base_url, token = resolve_auth(args)
    api(base_url, token, "post",
        f"/shifus/{args.shifu_bid}/outlines/{args.outline_bid}",
        json={"name": args.name})
    print(f"Renamed lesson {args.outline_bid} to: {args.name}")


# ── Delete Lesson ──────────────────────────────────────────────────────────────
def cmd_delete_lesson(args):
    """Delete a lesson from a course."""
    base_url, token = resolve_auth(args)
    api(base_url, token, "delete",
        f"/shifus/{args.shifu_bid}/outlines/{args.outline_bid}")
    print(f"Deleted lesson {args.outline_bid}")


# ── Reorder ────────────────────────────────────────────────────────────────────
def _validate_reorder_tree(node, path="root"):
    """Validate a single node of the reorder tree (recursive)."""
    if not isinstance(node, dict):
        return [f"{path}: must be an object"]
    errors = []
    if "bid" not in node or not isinstance(node["bid"], str) or not node["bid"]:
        errors.append(f"{path}: missing or empty 'bid' (string)")
    children = node.get("children", [])
    if not isinstance(children, list):
        errors.append(f"{path}.children: must be an array")
    else:
        for i, child in enumerate(children):
            errors.extend(_validate_reorder_tree(child, f"{path}.children[{i}]"))
    return errors


def cmd_reorder(args):
    """Reorder course outlines (chapters and lessons) by submitting a complete tree.

    Schema (matches platform ReorderOutlineDto):
        {"outlines": [
            {"bid": "<chapter-bid>", "children": [
                {"bid": "<lesson-bid>", "children": []},
                ...
            ]},
            ...
        ]}
    Supports cross-chapter moves (server's rebuild_positions handles arbitrary children).
    """
    base_url, token = resolve_auth(args)

    # Load tree from --tree-file or --json
    if args.tree_file:
        with open(args.tree_file, "r", encoding="utf-8") as f:
            try:
                outlines = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error: invalid JSON in {args.tree_file}: {e}", file=sys.stderr)
                sys.exit(1)
    elif args.json is not None:
        try:
            outlines = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON in --json: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: --tree-file <path> or --json <json> required", file=sys.stderr)
        sys.exit(1)

    if not isinstance(outlines, list):
        print("Error: outlines must be a JSON array of {bid, children} nodes", file=sys.stderr)
        sys.exit(1)

    # Validate tree structure before submitting
    errors = []
    for i, node in enumerate(outlines):
        errors.extend(_validate_reorder_tree(node, f"outlines[{i}]"))
    if errors:
        print("Error: invalid reorder tree:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    api(base_url, token, "patch",
        f"/shifus/{args.shifu_bid}/outlines/reorder",
        json={"outlines": outlines})
    print(f"Reordered {len(outlines)} top-level outlines")


# ── Import ─────────────────────────────────────────────────────────────────────
def _import_flat(base_url, token, json_file, shifu_bid):
    """Import from flat JSON file (original shifu-api-import.py logic)."""
    with open(json_file, "r", encoding="utf-8") as f:
        import_data = json.load(f)

    shifu_info = import_data["shifu"]
    outline_items = import_data["outline_items"]

    # Create or reuse shifu
    if shifu_bid:
        print(f"Using existing shifu: {shifu_bid}")
    else:
        print(f"Creating new shifu: {shifu_info['title']}")
        result = api(base_url, token, "put", "/shifus",
                     json={"name": shifu_info["title"],
                           "description": shifu_info.get("description", "")})
        shifu_bid = result.get("bid") or result.get("shifu_bid")
        print(f"  Created shifu: {shifu_bid}")

    # Update shifu detail
    keywords = shifu_info.get("keywords", "")
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    detail_payload = {
        "name": shifu_info["title"],
        "description": shifu_info.get("description", ""),
        "avatar": shifu_info.get("avatar_res_bid", ""),
        "keywords": keywords,
        "model": shifu_info.get("llm", ""),
        "temperature": shifu_info.get("llm_temperature", 0.3),
        "system_prompt": shifu_info.get("llm_system_prompt", ""),
    }
    price = shifu_info.get("price")
    if price and price > 0:
        detail_payload["price"] = price
    detail_payload.update({
        "tts_enabled": False,
        "tts_provider": "minimax",
        "tts_model": "",
        "tts_voice_id": "",
        "tts_speed": 1.0,
        "tts_pitch": 0,
        "tts_emotion": "",
        "use_learner_language": False,
    })
    for attempt in range(1, 4):
        result = api_safe(base_url, token, "post", f"/shifus/{shifu_bid}/detail",
                          json=detail_payload)
        if result is not None:
            print("  Updated shifu detail")
            break
        if attempt < 3:
            print(f"  Warning: failed to update shifu detail (attempt {attempt}/3), retrying...")
            time.sleep(1)
        else:
            print("Error: failed to update shifu detail after 3 attempts")
            sys.exit(1)

    # Clean existing outlines (delete children first, then parents)
    tree = api_safe(base_url, token, "get", f"/shifus/{shifu_bid}/outlines")
    if tree and isinstance(tree, list):
        for item in tree:
            for child in item.get("children", []):
                if child.get("bid"):
                    result = api_safe(base_url, token, "delete",
                                      f"/shifus/{shifu_bid}/outlines/{child['bid']}")
                    if result is None:
                        print(f"Error: failed to delete child outline: {child['bid']}")
                        sys.exit(1)
            if item.get("bid"):
                result = api_safe(base_url, token, "delete",
                                  f"/shifus/{shifu_bid}/outlines/{item['bid']}")
                if result is None:
                    print(f"Error: failed to delete outline: {item.get('name', item['bid'])}")
                    sys.exit(1)
                print(f"  Deleted old outline: {item.get('name', item['bid'])}")

    # Separate parents (chapters) and children (lessons) for two-pass creation
    parents = []
    children = []
    for item in outline_items:
        if item.get("parent_bid"):
            children.append(item)
        else:
            parents.append(item)

    bid_map = {}  # old outline_item_bid -> new API bid
    created = []
    total = len(outline_items)
    count = 0

    # Phase 1: Create parent items (chapters)
    for item in parents:
        count += 1
        title = item["title"]
        content = item.get("content", "")
        old_bid = item.get("outline_item_bid", "")

        result = api(base_url, token, "put", f"/shifus/{shifu_bid}/outlines",
                     json={"name": title})
        new_bid = result.get("bid") or result.get("outline_item_bid")
        bid_map[old_bid] = new_bid
        print(f"  [{count}/{total}] Created: {title} ({new_bid})")

        if content:
            api(base_url, token, "post",
                f"/shifus/{shifu_bid}/outlines/{new_bid}/mdflow",
                json={"data": content})
            print(f"    MarkdownFlow saved ({len(content)} chars)")

        created.append({"bid": new_bid, "title": title})
        time.sleep(0.3)

    # Phase 2: Create child items (lessons) with mapped parent_bid
    for item in children:
        count += 1
        title = item["title"]
        content = item.get("content", "")
        old_parent = item["parent_bid"]
        new_parent = bid_map.get(old_parent, old_parent)

        result = api(base_url, token, "put", f"/shifus/{shifu_bid}/outlines",
                     json={"name": title, "parent_bid": new_parent})
        new_bid = result.get("bid") or result.get("outline_item_bid")
        print(f"  [{count}/{total}] Created: {title} ({new_bid})")

        if content:
            api(base_url, token, "post",
                f"/shifus/{shifu_bid}/outlines/{new_bid}/mdflow",
                json={"data": content})
            print(f"    MarkdownFlow saved ({len(content)} chars)")

        created.append({"bid": new_bid, "title": title})
        time.sleep(0.3)

    print(f"\nDone! Shifu: {shifu_bid}")
    print(f"  Course: {shifu_info['title']}")
    print(f"  Chapters: {len(parents)}, Lessons: {len(children)}")
    print(f"  URL: {base_url}/shifu/{shifu_bid}")
    return shifu_bid


def _import_from_course_dir(base_url, token, course_dir):
    """Create a brand-new course from a course directory's course.json (ADR-001 §D9 protocol).

    Flow:
        1. Validate (import mode, placeholders allowed; no existing shifu_bid).
        2. Create empty shifu via PUT /shifus.
        3. Update metadata (title / description / course_prompt) via _push_update_meta.
        4. Add chapters (no parent), then lessons (with parent_bid resolved from local
           structure + bid_remap); record placeholder -> real bid mapping.
        5. Set MarkdownFlow content for items that have non-empty markdownflow_prompt.
        6. Reorder to match local structure exactly.
        7. Auto-pull to overwrite the local file with real bids and fresh revisions.
           This is the §D9 协议要求: callers must NOT see "import succeeded but local
           still has placeholders" as a final state.
    """
    course_dir = os.fspath(course_dir)
    course_file = _course_json_path(course_dir)
    course = _load_course_json(course_file)
    errors = _validate_course_json(course, mode="import")
    if errors:
        print(f"Error: validation failed for {course_file}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    existing_bid = course.get("deployment", {}).get("shifu_bid", "")
    if existing_bid:
        print(f"Error: course.json already has deployment.shifu_bid={existing_bid!r}; "
              f"use `push` to update an existing course (import is for new courses only)",
              file=sys.stderr)
        sys.exit(1)

    course_meta = course.get("course", {})
    title = course_meta.get("title", "")
    if not title.strip():
        print("Error: course.title is required to create a new course", file=sys.stderr)
        sys.exit(1)

    print(f"Creating new shifu '{title}' ...")

    # Step 1: create empty shifu
    create_result = api(base_url, token, "put", "/shifus",
                        json={"name": title,
                              "description": course_meta.get("description", "")})
    shifu_bid = create_result.get("bid") or create_result.get("shifu_bid")
    if not isinstance(shifu_bid, str) or not shifu_bid:
        print(f"Error: shifu creation did not return a bid: {create_result}", file=sys.stderr)
        sys.exit(1)
    print(f"  shifu_bid = {shifu_bid}")

    # From here on, any failure must surface the shifu_bid so the user can recover.
    def _half_failure(stage, exc=None):
        print(f"\n⚠️  Import partially succeeded (shifu_bid={shifu_bid}) but {stage} failed.",
              file=sys.stderr)
        if exc is not None:
            print(f"   Reason: {exc}", file=sys.stderr)
        print(f"   Run manually to recover state:", file=sys.stderr)
        print(f"     shifu-cli pull {shifu_bid} --to {course_file} --force-overwrite",
              file=sys.stderr)
        sys.exit(1)

    try:
        print("  Updating metadata (system_prompt etc.)")
        _push_update_meta(base_url, token, shifu_bid, course_meta)

        items = course.get("items", {})
        structure = course.get("structure", [])
        placeholders = list(items.keys())
        chapters = [b for b in placeholders if items[b].get("type") == "chapter"]
        lessons = [b for b in placeholders if items[b].get("type") == "lesson"]
        parent_map = _compute_parent_map(structure)
        bid_remap = {}

        if chapters:
            print(f"  Adding {len(chapters)} chapter(s)")
            for placeholder in chapters:
                new_bid = _push_create_outline(base_url, token, shifu_bid,
                                               items[placeholder].get("title", ""),
                                               local_type="chapter")
                bid_remap[placeholder] = new_bid
                print(f"    + {placeholder} -> {new_bid}")

        if lessons:
            print(f"  Adding {len(lessons)} lesson(s)")
            for placeholder in lessons:
                parent_local = parent_map.get(placeholder, "")
                parent_real = bid_remap.get(parent_local, parent_local)
                if not parent_real:
                    print(f"Error: lesson {placeholder!r} has no parent in local structure",
                          file=sys.stderr)
                    _half_failure("lesson creation")
                new_bid = _push_create_outline(base_url, token, shifu_bid,
                                               items[placeholder].get("title", ""),
                                               parent_bid=parent_real,
                                               local_type="lesson")
                bid_remap[placeholder] = new_bid
                print(f"    + {placeholder} -> {new_bid} (parent={parent_real})")

        # Apply bid_remap so downstream operations refer to real bids.
        _apply_bid_remap_inplace(course, bid_remap)

        # Set MarkdownFlow content for items that have any.
        items = course["items"]  # rebind to remapped dict
        items_with_content = [b for b in items if items[b].get("markdownflow_prompt")]
        if items_with_content:
            print(f"  Writing MarkdownFlow for {len(items_with_content)} item(s)")
            for bid in items_with_content:
                _push_update_mdflow(base_url, token, shifu_bid, bid,
                                    items[bid].get("markdownflow_prompt", ""))

        # Reorder to match local structure (server adds new outlines in insertion order
        # which usually matches local intent, but reorder is cheap insurance).
        if course.get("structure"):
            print("  Reordering outlines to match local structure")
            _push_reorder(base_url, token, shifu_bid, course["structure"])
    except SystemExit:
        raise
    except Exception as e:
        _half_failure("mutation step", exc=e)

    # Auto-pull to refresh local file with real bids + revisions (§D9 协议要求).
    print(f"\nAuto-pulling to refresh {course_file} with real bids and revisions ...")
    try:
        _do_pull(base_url, token, shifu_bid, course_dir, force_overwrite=True, verbose=False)
    except SystemExit as e:
        if e.code != 0:
            _half_failure("auto-pull")

    print(f"\nImport complete: {shifu_bid}")
    print(f"  URL: {base_url}/shifu/{shifu_bid}")


def cmd_import(args):
    """Create a course on the server (new format: --course-dir <course-dir>;
    --json-file / --legacy-course-dir remain as legacy paths)."""
    base_url, token = resolve_auth(args)

    # Reject the legacy "--shifu-bid <existing>" mode (ADR-001 §D9: import is for
    # brand-new courses only; updating existing courses goes through `push`).
    if args.shifu_bid and not args.new:
        print(f"Error: import no longer supports updating an existing course "
              f"(shifu_bid={args.shifu_bid!r}). Use `push --course-dir <course-dir>` instead. "
              f"See ADR-001 §D9.", file=sys.stderr)
        sys.exit(1)
    if args.new and args.shifu_bid:
        print("Error: omit <shifu_bid> when using --new", file=sys.stderr)
        sys.exit(1)
    if not args.new:
        print("Error: import requires --new (import is for brand-new courses only). "
              "To update an existing course, use `push --course-dir <course-dir>`.",
              file=sys.stderr)
        sys.exit(1)

    if args.course_dir:
        _import_from_course_dir(base_url, token, args.course_dir)
    elif args.legacy_course_dir:
        # Legacy: build flat JSON from old multi-file course directory then import
        json_file = _build_import_json(
            course_dir=args.legacy_course_dir,
            title=getattr(args, "title", None),
            description=getattr(args, "description", None),
            keywords=getattr(args, "keywords", None),
            chapter_name=getattr(args, "chapter_name", None),
        )
        _import_flat(base_url, token, json_file, None)
    elif args.json_file:
        # Legacy: old flat JSON
        _import_flat(base_url, token, args.json_file, None)
    else:
        print("Error: provide --course-dir (new format) "
              "or --json-file / --legacy-course-dir (legacy)", file=sys.stderr)
        sys.exit(1)


# ── Build ──────────────────────────────────────────────────────────────────────
def _extract_lesson_title(content, filename):
    """Extract lesson_title from HTML comment block, fallback to filename."""
    match = re.search(r'lesson_title:\s*(.+)', content)
    if match:
        return match.group(1).strip()
    name = Path(filename).stem
    return name.replace("-", " ").title()


def _build_import_json(course_dir, title=None, description=None,
                       keywords=None, chapter_name=None, output_path=None):
    """Build import JSON from a local course directory. Returns the output file path."""
    lessons_dir = os.path.join(course_dir, "lessons")
    if not os.path.isdir(lessons_dir):
        print(f"Error: lessons directory not found: {lessons_dir}")
        sys.exit(1)

    # Read system prompt if exists
    llm_system_prompt = ""
    sys_prompt_path = os.path.join(course_dir, "system-prompt.md")
    if os.path.exists(sys_prompt_path):
        with open(sys_prompt_path, "r", encoding="utf-8") as f:
            llm_system_prompt = f.read().strip()
        print(f"Loaded system prompt ({len(llm_system_prompt)} chars)")

    # Scan lesson files
    lesson_files = sorted([
        f for f in os.listdir(lessons_dir)
        if f.startswith("lesson-") and f.endswith(".md")
    ])
    if not lesson_files:
        print(f"Error: no lesson-*.md files found in {lessons_dir}")
        sys.exit(1)

    shifu_bid = str(uuid.uuid4()).replace("-", "")

    # Determine title: explicit arg > README > directory name
    if not title:
        readme_path = os.path.join(course_dir, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
            if first_line.startswith("#"):
                title = first_line.lstrip("#").strip()
        if not title:
            title = Path(course_dir).name

    # Load chapter structure from structure.json if exists,
    # otherwise auto-create a single chapter wrapping all lessons
    structure_file = os.path.join(course_dir, "structure.json")
    if os.path.exists(structure_file):
        with open(structure_file, "r", encoding="utf-8") as f:
            chapter_defs = json.load(f).get("chapters", [])
    else:
        chapter_defs = None

    outline_items = []
    structure_chapters = []

    if chapter_defs:
        # Multi-chapter mode: use structure.json definitions
        for ch_idx, ch_def in enumerate(chapter_defs):
            ch_bid = str(uuid.uuid4()).replace("-", "")
            ch_title = ch_def["title"]

            # Chapter item (container, no MarkdownFlow content)
            outline_items.append({
                "outline_item_bid": ch_bid,
                "title": ch_title,
                "type": 401,
                "hidden": 0,
                "parent_bid": "",
                "position": str(ch_idx),
                "prerequisite_item_bids": "",
                "llm": "",
                "llm_temperature": 0,
                "llm_system_prompt": "",
                "ask_enabled_status": 5101,
                "ask_llm": "",
                "ask_llm_temperature": 0.0,
                "ask_llm_system_prompt": "",
                "content": "",
            })

            lesson_children = []
            for ls_idx, ls_def in enumerate(ch_def.get("lessons", [])):
                ls_file = ls_def["file"]
                filepath = safe_join_path(lessons_dir, ls_file)
                if filepath is None:
                    continue
                if not os.path.exists(filepath):
                    print(f"Warning: file not found: {filepath}, skipping")
                    continue
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                item_bid = str(uuid.uuid4()).replace("-", "")
                ls_title = ls_def.get("title") or _extract_lesson_title(content, ls_file)

                outline_items.append({
                    "outline_item_bid": item_bid,
                    "title": ls_title,
                    "type": 401,
                    "hidden": 0,
                    "parent_bid": ch_bid,
                    "position": str(ls_idx),
                    "prerequisite_item_bids": "",
                    "llm": "",
                    "llm_temperature": 0,
                    "llm_system_prompt": llm_system_prompt,
                    "ask_enabled_status": 5101,
                    "ask_llm": "",
                    "ask_llm_temperature": 0.0,
                    "ask_llm_system_prompt": "",
                    "content": content,
                })

                lesson_children.append({
                    "bid": item_bid, "id": 0, "type": "outline",
                    "children": [], "child_count": 0,
                })

            structure_chapters.append({
                "bid": ch_bid, "id": 0, "type": "outline",
                "children": lesson_children,
                "child_count": len(lesson_children),
            })
    else:
        # Single-chapter mode: wrap all lessons under one chapter
        chapter_bid = str(uuid.uuid4()).replace("-", "")
        chapter_title = chapter_name or title

        # Chapter item (container, no MarkdownFlow content)
        outline_items.append({
            "outline_item_bid": chapter_bid,
            "title": chapter_title,
            "type": 401,
            "hidden": 0,
            "parent_bid": "",
            "position": "0",
            "prerequisite_item_bids": "",
            "llm": "",
            "llm_temperature": 0,
            "llm_system_prompt": "",
            "ask_enabled_status": 5101,
            "ask_llm": "",
            "ask_llm_temperature": 0.0,
            "ask_llm_system_prompt": "",
            "content": "",
        })

        lesson_children = []
        for idx, filename in enumerate(lesson_files):
            filepath = safe_join_path(lessons_dir, filename)
            if filepath is None:
                continue
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            item_bid = str(uuid.uuid4()).replace("-", "")
            lesson_title = _extract_lesson_title(content, filename)

            outline_items.append({
                "outline_item_bid": item_bid,
                "title": lesson_title,
                "type": 401,
                "hidden": 0,
                "parent_bid": chapter_bid,
                "position": str(idx),
                "prerequisite_item_bids": "",
                "llm": "",
                "llm_temperature": 0,
                "llm_system_prompt": llm_system_prompt,
                "ask_enabled_status": 5101,
                "ask_llm": "",
                "ask_llm_temperature": 0.0,
                "ask_llm_system_prompt": "",
                "content": content,
            })

            lesson_children.append({
                "bid": item_bid, "id": 0, "type": "outline",
                "children": [], "child_count": 0,
            })

        structure_chapters.append({
            "bid": chapter_bid, "id": 0, "type": "outline",
            "children": lesson_children,
            "child_count": len(lesson_children),
        })

    import_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "shifu": {
            "shifu_bid": shifu_bid,
            "title": title,
            "keywords": keywords or "",
            "description": description or "",
            "avatar_res_bid": "",
            "llm": "",
            "llm_temperature": 0,
            "llm_system_prompt": llm_system_prompt,
            "ask_enabled_status": 5101,
            "ask_llm": "",
            "ask_llm_temperature": 0.0,
            "ask_llm_system_prompt": "",
        },
        "outline_items": outline_items,
        "structure": {
            "bid": shifu_bid,
            "id": 0,
            "type": "shifu",
            "children": structure_chapters,
            "child_count": len(structure_chapters),
        },
    }

    # Output
    if not output_path:
        output_path = os.path.join(course_dir, "shifu-import.json")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(import_data, f, ensure_ascii=False, indent=2)

    chapters = [i for i in outline_items if not i.get("parent_bid")]
    lessons = [i for i in outline_items if i.get("parent_bid")]
    print(f"Generated {output_path}")
    print(f"  Course: {title}")
    print(f"  Chapters: {len(chapters)}, Lessons: {len(lessons)}")
    print(f"  Shifu BID: {shifu_bid}")
    return output_path


def cmd_build(args):
    """Build import JSON from local course directory (no network needed)."""
    _build_import_json(
        course_dir=args.course_dir,
        title=args.title,
        description=args.description,
        keywords=args.keywords,
        chapter_name=args.chapter_name,
        output_path=args.output,
    )


# ── Publish / Archive / Unarchive ──────────────────────────────────────────────
def cmd_publish(args):
    """Publish a course."""
    base_url, token = resolve_auth(args)
    api(base_url, token, "post", f"/shifus/{args.shifu_bid}/publish", json={})
    print(f"Published: {args.shifu_bid}")


def cmd_archive(args):
    """Archive a course."""
    base_url, token = resolve_auth(args)
    api(base_url, token, "post", f"/shifus/{args.shifu_bid}/archive", json={})
    print(f"Archived: {args.shifu_bid}")


def cmd_unarchive(args):
    """Unarchive a course."""
    base_url, token = resolve_auth(args)
    api(base_url, token, "post", f"/shifus/{args.shifu_bid}/unarchive", json={})
    print(f"Unarchived: {args.shifu_bid}")


# ── Extract / Embed (course.json field <-> standalone .md) ────────────────────
# Local-only, no platform calls. See ADR-001 §D7 for the workflow.
def _resolve_extract_embed_field(course, args):
    """Resolve which field to extract/embed based on CLI flags.

    Returns (kind, current_value, setter) where kind is 'lesson' or 'course-prompt',
    current_value is the existing string, and setter(new_value) writes it back into
    the in-memory course dict.
    """
    if args.course_prompt and args.outline_bid:
        print("Error: pick exactly one of --course-prompt or --outline-bid <bid>", file=sys.stderr)
        sys.exit(1)
    if not args.course_prompt and not args.outline_bid:
        print("Error: specify --course-prompt or --outline-bid <bid>", file=sys.stderr)
        sys.exit(1)

    if args.course_prompt:
        course.setdefault("course", {})
        current = course["course"].get("course_prompt", "")
        def setter(new_value):
            course["course"]["course_prompt"] = new_value
        return "course-prompt", current, setter

    bid = args.outline_bid
    items = course.get("items")
    if not isinstance(items, dict) or bid not in items:
        print(f"Error: outline_item_bid {bid!r} not found in items{{}}", file=sys.stderr)
        sys.exit(1)
    item = items[bid]
    if not isinstance(item, dict):
        print(f"Error: items[{bid!r}] is not an object", file=sys.stderr)
        sys.exit(1)
    current = item.get("markdownflow_prompt", "")
    def setter(new_value):
        item["markdownflow_prompt"] = new_value
    return "lesson", current, setter


def cmd_extract(args):
    """Extract a long-text field from course.json into a standalone .md file."""
    course = _load_course_json(_course_json_path(args.course_dir))
    kind, current, _ = _resolve_extract_embed_field(course, args)

    out_path = args.output
    if not out_path:
        print("Error: --output / -o required", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(out_path) and not args.force:
        print(f"Error: {out_path} already exists; use --force to overwrite", file=sys.stderr)
        sys.exit(1)

    parent = os.path.dirname(os.path.abspath(out_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(current)
    if kind == "lesson":
        print(f"Extracted items[{args.outline_bid!r}].markdownflow_prompt ({len(current)} chars) → {out_path}")
    else:
        print(f"Extracted course.course_prompt ({len(current)} chars) → {out_path}")


def cmd_embed(args):
    """Write a standalone .md file back into the corresponding course.json field."""
    course = _load_course_json(_course_json_path(args.course_dir))
    kind, _, setter = _resolve_extract_embed_field(course, args)

    src = args.from_file
    if not src:
        print("Error: --from <path.md> required", file=sys.stderr)
        sys.exit(1)
    try:
        with open(src, "r", encoding="utf-8") as f:
            new_value = f.read()
    except FileNotFoundError:
        print(f"Error: source file not found: {src}", file=sys.stderr)
        sys.exit(1)

    setter(new_value)
    _atomic_write_json(_course_json_path(args.course_dir), course)
    if kind == "lesson":
        print(f"Embedded {len(new_value)} chars from {src} → items[{args.outline_bid!r}].markdownflow_prompt")
    else:
        print(f"Embedded {len(new_value)} chars from {src} → course.course_prompt")


# ── Pull (server -> local course.json, ADR-001 §D4 / §D10) ────────────────────

def _do_pull(base_url, token, shifu_bid, course_dir, force_overwrite=False, verbose=True):
    """Internal pull primitive shared by cmd_pull, cmd_push, and cmd_import.

    Pulls the course into <course-dir>/course.json. Creates the directory if needed.
    Returns the parsed course dict that was written. Raises SystemExit on error.
    """
    course_dir = os.fspath(course_dir)
    out_path = _course_json_path(course_dir)

    if os.path.exists(out_path) and not force_overwrite:
        print(f"Error: {out_path} already exists; use --force-overwrite to replace it",
              file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"Pulling course {shifu_bid} ...")
        print("  Step 1/2: GET /export")
    export = _fetch_export(base_url, token, shifu_bid)
    course = _transform_export_to_course(export)
    item_bids = list(course["items"].keys())

    if verbose:
        print(f"  Step 2/2: GET /draft-meta x {len(item_bids)} (one per outline_item)")
    revisions = {}
    for bid in item_bids:
        rev = _fetch_revision(base_url, token, shifu_bid, bid)
        if rev is not None:
            revisions[bid] = rev
    course["deployment"]["draft_pulled_at_revision"] = revisions

    errors = _validate_course_json(course, mode="push")
    if errors:
        print("Warning: pulled course.json failed local validation "
              "(may indicate a server schema change):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)

    _ensure_course_dir(course_dir)
    _atomic_write_json(out_path, course)

    if verbose:
        n_chapter = sum(1 for it in course["items"].values() if it["type"] == "chapter")
        n_lesson = sum(1 for it in course["items"].values() if it["type"] == "lesson")
        print(f"Wrote {out_path}")
        print(f"  shifu_bid: {course['deployment']['shifu_bid']}")
        print(f"  title:     {course['course']['title']}")
        print(f"  outline_items: {len(item_bids)} ({n_chapter} chapter, {n_lesson} lesson)")
        print(f"  revisions captured: {len(revisions)}/{len(item_bids)}")

    if errors:
        sys.exit(1)
    return course


def cmd_pull(args):
    """Download a course from the server into a local course directory."""
    base_url, token = resolve_auth(args)
    _do_pull(base_url, token, args.shifu_bid, os.fspath(args.course_dir),
             force_overwrite=args.force_overwrite)


# ── Push helpers (server-side mutation primitives) ─────────────────────────────
# These are the granular building blocks shared by cmd_push and cmd_import.
# Each helper is responsible for ONE platform action and returns the data
# the caller needs (e.g. a new outline_item_bid). All errors exit non-zero
# via the shared `api()` function.

def _push_update_meta(base_url, token, shifu_bid, course):
    """Update course-level metadata (title / description / course_prompt) via POST /detail.

    Fetches the current detail to preserve unrelated fields (avatar, keywords, model,
    temperature, TTS, ask config, etc.), since the platform's POST /detail expects
    a complete payload.
    """
    current = api(base_url, token, "get", f"/shifus/{shifu_bid}/detail")

    keywords = current.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    payload = {
        "name": course.get("title", ""),
        "description": course.get("description", ""),
        "avatar": current.get("avatar", ""),
        "keywords": keywords,
        "model": current.get("model", ""),
        "temperature": current.get("temperature", 0.3),
        "system_prompt": course.get("course_prompt", ""),
        "tts_enabled": current.get("tts_enabled", False),
        "tts_provider": current.get("tts_provider", "minimax"),
        "tts_model": current.get("tts_model", ""),
        "tts_voice_id": current.get("tts_voice_id", ""),
        "tts_speed": current.get("tts_speed", 1.0),
        "tts_pitch": current.get("tts_pitch", 0),
        "tts_emotion": current.get("tts_emotion", ""),
        "use_learner_language": current.get("use_learner_language", False),
    }
    price = current.get("price")
    if price and price > 0:
        payload["price"] = price
    api(base_url, token, "post", f"/shifus/{shifu_bid}/detail", json=payload)


def _push_create_outline(base_url, token, shifu_bid, name, parent_bid=None, local_type="lesson"):
    """Create an outline_item via PUT /outlines.

    The platform's `type` parameter is an access-level string (guest/trial/normal,
    backed by ints 400/401/402); by default the platform sets type="guest" (400),
    which is wrong for child nodes. We pass `type` explicitly based on `local_type`
    so chapters land at 400 and lessons at 401.

    Returns the newly assigned real outline_item_bid.
    """
    payload = {"name": name, "type": _local_type_to_wire_name(local_type)}
    if parent_bid:
        payload["parent_bid"] = parent_bid
    result = api(base_url, token, "put", f"/shifus/{shifu_bid}/outlines", json=payload)
    new_bid = result.get("bid") or result.get("outline_item_bid")
    if not isinstance(new_bid, str) or not new_bid:
        print(f"Error: outline created but response did not include a 'bid'", file=sys.stderr)
        print(f"  Response: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)
    return new_bid


def _push_delete_outline(base_url, token, shifu_bid, outline_bid):
    """Delete an outline_item via DELETE /outlines/<bid>."""
    api(base_url, token, "delete", f"/shifus/{shifu_bid}/outlines/{outline_bid}")


def _push_rename_outline(base_url, token, shifu_bid, outline_bid, new_name):
    """Rename an outline_item via POST /outlines/<bid>."""
    api(base_url, token, "post",
        f"/shifus/{shifu_bid}/outlines/{outline_bid}",
        json={"name": new_name})


def _push_update_mdflow(base_url, token, shifu_bid, outline_bid, content, base_revision=None):
    """Save MarkdownFlow content for an outline_item, with optimistic locking when
    a revision is provided.

    Returns the new revision (int) on success.
    """
    payload = {"data": content}
    if base_revision is not None:
        payload["base_revision"] = base_revision
    result = api(base_url, token, "post",
                 f"/shifus/{shifu_bid}/outlines/{outline_bid}/mdflow",
                 json=payload)
    if isinstance(result, dict):
        rev = result.get("new_revision")
        if isinstance(rev, int):
            return rev
    return None


def _push_reorder(base_url, token, shifu_bid, structure):
    """Submit the complete outline tree to the reorder endpoint.

    `structure` is the local course.json structure list (each node is
    {outline_item_bid, children}). We rename `outline_item_bid` -> `bid` to
    match the platform's ReorderOutlineItemDto schema.
    """
    def to_wire(node):
        return {
            "bid": node.get("outline_item_bid", ""),
            "children": [to_wire(c) for c in node.get("children", [])],
        }
    wire_outlines = [to_wire(n) for n in structure]
    api(base_url, token, "patch",
        f"/shifus/{shifu_bid}/outlines/reorder",
        json={"outlines": wire_outlines})


# ── Push helpers (local diff & remap) ──────────────────────────────────────────

def _compute_parent_map(structure):
    """Walk the structure tree once and return {child_bid: parent_bid} for every node.
    Top-level nodes map to ''."""
    parent_map = {}
    def walk(nodes, parent):
        for n in nodes:
            bid = n.get("outline_item_bid", "")
            if bid:
                parent_map[bid] = parent
            walk(n.get("children", []) or [], bid)
    walk(structure or [], "")
    return parent_map


def _topological_order_for_add(items, structure, placeholders):
    """Order placeholder bids so chapters come before their lessons.

    Returns a list of placeholder bids in safe creation order.
    """
    parent_map = _compute_parent_map(structure)
    chapters = [b for b in placeholders if items[b].get("type") == "chapter"]
    lessons = [b for b in placeholders if items[b].get("type") == "lesson"]
    return chapters + lessons


def _apply_bid_remap_inplace(course, bid_remap):
    """Rewrite all placeholder bids in items{} dict and structure tree using bid_remap."""
    if not bid_remap:
        return
    # items dict: replace keys
    new_items = {}
    for k, v in course.get("items", {}).items():
        new_items[bid_remap.get(k, k)] = v
    course["items"] = new_items
    # structure tree: replace outline_item_bid recursively
    def walk(nodes):
        for n in nodes:
            bid = n.get("outline_item_bid", "")
            if bid in bid_remap:
                n["outline_item_bid"] = bid_remap[bid]
            walk(n.get("children", []) or [])
    walk(course.get("structure", []) or [])
    # deployment.draft_pulled_at_revision: replace any keys that got remapped
    rev = course.get("deployment", {}).get("draft_pulled_at_revision", {})
    if isinstance(rev, dict):
        new_rev = {}
        for k, v in rev.items():
            new_rev[bid_remap.get(k, k)] = v
        course["deployment"]["draft_pulled_at_revision"] = new_rev


# ── Push (local course.json -> server, ADR-001 §D4 / §D6) ──────────────────────
def cmd_push(args):
    """Push local course.json changes to the server via fine-grained mutations.

    Algorithm (ADR-001 §D4 / §D6):
      1. Load + validate local course.json (import mode: placeholders allowed).
      2. Fetch remote state via /export to compute diff.
      3. Diff: metadata, items (add/delete/content/rename), structure (reorder).
      4. Apply mutations in safe order: metadata -> add chapters -> add lessons ->
         delete obsolete -> rename -> update mdflow (with optimistic locking) -> reorder.
      5. Re-pull to refresh revisions and reconcile final state.
    """
    base_url, token = resolve_auth(args)
    course_dir = os.fspath(args.course_dir)
    local_path = _course_json_path(course_dir)

    # Step 1: load + validate
    local = _load_course_json(local_path)
    errors = _validate_course_json(local, mode="import")  # placeholders allowed for混合编辑
    if errors:
        print(f"Error: local validation failed for {local_path}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    shifu_bid = local.get("deployment", {}).get("shifu_bid", "")
    if not shifu_bid:
        print(f"Error: course.json has no deployment.shifu_bid; "
              f"use `import --new` for a brand-new course", file=sys.stderr)
        sys.exit(1)

    print(f"Pushing course {shifu_bid} ...")

    # Step 2: fetch remote state
    print("  Step 1: fetch remote state via /export")
    remote_export = _fetch_export(base_url, token, shifu_bid)
    remote = _transform_export_to_course(remote_export)

    # Step 3: compute diff
    local_items = local.get("items", {})
    remote_items = remote.get("items", {})

    metadata_changed = (
        local["course"].get("title", "") != remote["course"].get("title", "")
        or local["course"].get("description", "") != remote["course"].get("description", "")
        or local["course"].get("course_prompt", "") != remote["course"].get("course_prompt", "")
    )

    placeholder_bids = [b for b in local_items if _is_placeholder_bid(b)]
    real_local_bids = set(b for b in local_items if not _is_placeholder_bid(b))
    real_remote_bids = set(remote_items.keys())

    to_add = placeholder_bids
    to_delete = sorted(real_remote_bids - real_local_bids)
    to_update_content = []
    to_update_title = []
    for bid in real_local_bids & real_remote_bids:
        if local_items[bid].get("markdownflow_prompt", "") != remote_items[bid].get("markdownflow_prompt", ""):
            to_update_content.append(bid)
        if local_items[bid].get("title", "") != remote_items[bid].get("title", ""):
            to_update_title.append(bid)

    structure_changed = local.get("structure", []) != remote.get("structure", [])

    print(f"  Diff: meta={'yes' if metadata_changed else 'no'}; "
          f"add={len(to_add)}; delete={len(to_delete)}; "
          f"content={len(to_update_content)}; rename={len(to_update_title)}; "
          f"reorder={'yes' if structure_changed else 'no'}")

    # Early exit if nothing to do.
    if not (metadata_changed or to_add or to_delete or to_update_content
            or to_update_title or structure_changed):
        print("No changes; nothing to push.")
        return

    # Step 4: apply mutations
    bid_remap = {}  # placeholder -> real bid

    if metadata_changed:
        print("  Step 2: update metadata")
        _push_update_meta(base_url, token, shifu_bid, local["course"])

    if to_add:
        ordered = _topological_order_for_add(local_items, local.get("structure", []), to_add)
        chapters = [b for b in ordered if local_items[b].get("type") == "chapter"]
        lessons = [b for b in ordered if local_items[b].get("type") == "lesson"]
        parent_map = _compute_parent_map(local.get("structure", []))

        if chapters:
            print(f"  Step 3a: add {len(chapters)} chapter(s)")
            for placeholder in chapters:
                new_bid = _push_create_outline(base_url, token, shifu_bid,
                                               local_items[placeholder].get("title", ""),
                                               local_type="chapter")
                bid_remap[placeholder] = new_bid
                print(f"    + {placeholder} -> {new_bid}")

        if lessons:
            print(f"  Step 3b: add {len(lessons)} lesson(s)")
            for placeholder in lessons:
                parent_local = parent_map.get(placeholder, "")
                parent_real = bid_remap.get(parent_local, parent_local)
                if not parent_real:
                    print(f"Error: lesson {placeholder!r} has no parent in local structure",
                          file=sys.stderr)
                    sys.exit(1)
                new_bid = _push_create_outline(base_url, token, shifu_bid,
                                               local_items[placeholder].get("title", ""),
                                               parent_bid=parent_real,
                                               local_type="lesson")
                bid_remap[placeholder] = new_bid
                print(f"    + {placeholder} -> {new_bid} (parent={parent_real})")

    # Apply bid_remap to local in-memory so subsequent steps refer to real bids.
    if bid_remap:
        _apply_bid_remap_inplace(local, bid_remap)
        local_items = local["items"]  # rebind to refreshed dict

    if to_delete:
        print(f"  Step 4: delete {len(to_delete)} obsolete outline(s)")
        for bid in to_delete:
            _push_delete_outline(base_url, token, shifu_bid, bid)
            print(f"    - {bid}")

    if to_update_title:
        print(f"  Step 5: rename {len(to_update_title)} outline(s)")
        for bid in to_update_title:
            _push_rename_outline(base_url, token, shifu_bid, bid,
                                 local_items[bid].get("title", ""))
            print(f"    ~ {bid} -> {local_items[bid].get('title', '')!r}")

    # Newly added items also need their initial markdownflow_prompt content set.
    items_needing_content = list(to_update_content)
    for placeholder, new_bid in bid_remap.items():
        if local_items.get(new_bid, {}).get("markdownflow_prompt", ""):
            items_needing_content.append(new_bid)

    if items_needing_content:
        revisions = local.get("deployment", {}).get("draft_pulled_at_revision", {})
        print(f"  Step 6: update mdflow for {len(items_needing_content)} item(s)")
        for bid in items_needing_content:
            base_rev = revisions.get(bid)  # may be None for newly added items
            _push_update_mdflow(base_url, token, shifu_bid, bid,
                                local_items[bid].get("markdownflow_prompt", ""),
                                base_revision=base_rev)
            print(f"    ~ {bid} ({len(local_items[bid].get('markdownflow_prompt', ''))} chars, "
                  f"base_revision={base_rev})")

    if structure_changed:
        print("  Step 7: reorder outline tree")
        _push_reorder(base_url, token, shifu_bid, local.get("structure", []))

    # Step 5: re-pull to refresh local state (revisions + reconcile server-side rewrites)
    print("  Step 8: re-pull to refresh local state")
    _do_pull(base_url, token, shifu_bid, course_dir, force_overwrite=True, verbose=False)

    print(f"Push complete: {shifu_bid}")


# ── Validate (course.json schema check) ────────────────────────────────────────
def cmd_validate(args):
    """Run schema validation on a course directory's course.json (ADR-001 §D3)."""
    course_path = _course_json_path(args.course_dir)
    data = _load_course_json(course_path)
    errors = _validate_course_json(data, mode=args.mode)
    if errors:
        print(f"Validation FAILED ({len(errors)} error(s)) for {course_path} [mode={args.mode}]:",
              file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    print(f"Validation OK: {course_path} [mode={args.mode}]")


# ── CLI Entry Point ────────────────────────────────────────────────────────────
def build_parser():
    """Build and return the argument parser with all subcommands."""
    # Shared parent parser for --token on every subcommand
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--token", default=None,
                               help="JWT token (or SHIFU_TOKEN in .env)")

    parser = argparse.ArgumentParser(
        prog="shifu-cli",
        description="AI-Shifu Course CLI - Unified tool for course CRUD operations",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ── login ──
    p = sub.add_parser("login", parents=[parent_parser],
                       help="SMS login and save token")
    p.add_argument("--phone", required=True, help="Phone number for SMS login")
    p.add_argument("--sms-code", default=None,
                   help="4-digit SMS verification code")

    # ── list ──
    sub.add_parser("list", parents=[parent_parser], help="List all courses")

    # ── show ──
    p = sub.add_parser("show", parents=[parent_parser],
                       help="Show course detail or lesson MarkdownFlow content")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("outline_bid", nargs="?", default=None,
                   help="Outline BID (omit to show tree)")

    # ── history ──
    p = sub.add_parser("history", parents=[parent_parser],
                       help="Show MarkdownFlow revision history")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("outline_bid", help="Outline BID")

    # ── export ──
    p = sub.add_parser("export", parents=[parent_parser],
                       help="Export course to JSON")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("-o", "--output", default=None, help="Output file (stdout if omitted)")

    # ── create ──
    p = sub.add_parser("create", parents=[parent_parser],
                       help="Create a new empty course")
    p.add_argument("--name", required=True, help="Course name")
    p.add_argument("--description", default=None, help="Course description")

    # ── update-meta ──
    p = sub.add_parser("update-meta", parents=[parent_parser],
                       help="Update course metadata")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("--name", default=None, help="New course name")
    p.add_argument("--description", default=None, help="New description")
    p.add_argument("--system-prompt-file", default=None,
                   help="File containing system prompt")

    # ── add-chapter ──
    p = sub.add_parser("add-chapter", parents=[parent_parser],
                       help="Add a new top-level chapter")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("--name", required=True, help="Chapter name")

    # ── add-lesson ──
    p = sub.add_parser("add-lesson", parents=[parent_parser],
                       help="Add a new lesson under a chapter")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("--name", required=True, help="Lesson name")
    p.add_argument("--markdownflow-file", default=None, help="MarkdownFlow content file")
    p.add_argument("--parent-bid", required=True,
                   help="Parent chapter BID (use add-chapter to create one first)")

    # ── update-lesson ──
    p = sub.add_parser("update-lesson", parents=[parent_parser],
                       help="Update lesson MarkdownFlow content")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("outline_bid", help="Outline BID")
    p.add_argument("--markdownflow-file", required=True, help="MarkdownFlow content file")

    # ── rename-lesson ──
    p = sub.add_parser("rename-lesson", parents=[parent_parser],
                       help="Rename a lesson")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("outline_bid", help="Outline BID")
    p.add_argument("--name", required=True, help="New lesson name")

    # ── delete-lesson ──
    p = sub.add_parser("delete-lesson", parents=[parent_parser],
                       help="Delete a lesson")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("outline_bid", help="Outline BID")

    # ── reorder ──
    p = sub.add_parser("reorder", parents=[parent_parser],
                       help="Reorder outlines via a complete tree (supports cross-chapter moves)")
    p.add_argument("shifu_bid", help="Course BID")
    p.add_argument("--tree-file", default=None,
                   help='JSON file containing the outlines tree, schema: '
                        '[{"bid": "<chapter-bid>", "children": [{"bid": "<lesson-bid>", "children": []}]}, ...]')
    p.add_argument("--json", default=None,
                   help="Inline JSON string of the outlines tree (alternative to --tree-file)")

    # ── import ──
    p = sub.add_parser("import", parents=[parent_parser],
                       help="Create a brand-new course on the server (use --new --course-dir). "
                            "For updating an existing course, use `push` instead (ADR-001 §D9)")
    p.add_argument("shifu_bid", nargs="?", default=None,
                   help="(Legacy/deprecated) existing BID; new code paths must use `push`")
    p.add_argument("--new", action="store_true",
                   help="Create a new course (required for the new --course-dir path)")
    p.add_argument("--course-dir", default=None,
                   help="Source course directory (must contain course.json)")
    p.add_argument("--json-file", default=None,
                   help="(Legacy) flat import JSON file")
    p.add_argument("--legacy-course-dir", default=None,
                   help="(Legacy) old multi-file course directory layout with system-prompt.md + lessons/")
    p.add_argument("--title", default=None,
                   help="Course title (only with --legacy-course-dir)")
    p.add_argument("--description", default=None,
                   help="Course description (only with --legacy-course-dir)")
    p.add_argument("--keywords", default=None,
                   help="Keywords, comma-separated (only with --legacy-course-dir)")
    p.add_argument("--chapter-name", default=None,
                   help="Chapter name (only with --legacy-course-dir)")

    # ── build ──
    p = sub.add_parser("build", help="Build import JSON from local course directory")
    p.add_argument("--course-dir", required=True, help="Course directory path")
    p.add_argument("-o", "--output", default=None,
                   help="Output file (default: <course-dir>/shifu-import.json)")
    p.add_argument("--title", default=None, help="Course title")
    p.add_argument("--chapter-name", default=None,
                   help="Chapter name (default: same as course title)")
    p.add_argument("--description", default=None, help="Course description")
    p.add_argument("--keywords", default=None, help="Keywords (comma-separated)")

    # ── publish ──
    p = sub.add_parser("publish", parents=[parent_parser],
                       help="Publish a course")
    p.add_argument("shifu_bid", help="Course BID")

    # ── archive ──
    p = sub.add_parser("archive", parents=[parent_parser],
                       help="Archive a course")
    p.add_argument("shifu_bid", help="Course BID")

    # ── unarchive ──
    p = sub.add_parser("unarchive", parents=[parent_parser],
                       help="Unarchive a course")
    p.add_argument("shifu_bid", help="Course BID")

    # ── pull (server -> local course directory) ──
    p = sub.add_parser("pull", parents=[parent_parser],
                       help="Pull a course from the server into a local course directory "
                            "(ADR-001 §D10: export + draft-meta per outline_item)")
    p.add_argument("shifu_bid", help="Course BID to pull")
    p.add_argument("--to", dest="course_dir", required=True,
                   help="Target course directory (will be created if missing); "
                        "the canonical course.json is written inside it")
    p.add_argument("--force-overwrite", action="store_true",
                   help="Overwrite an existing course.json inside the target directory")

    # ── push (local course directory -> server) ──
    p = sub.add_parser("push", parents=[parent_parser],
                       help="Push local course.json changes to the server via fine-grained diff "
                            "(ADR-001 §D4 / §D6)")
    p.add_argument("--course-dir", dest="course_dir", required=True,
                   help="Source course directory (must contain course.json)")

    # ── extract (local: course.json field -> standalone .md) ──
    p = sub.add_parser("extract",
                       help="Extract a course-prompt or lesson MarkdownFlow field "
                            "from a course directory's course.json into a standalone .md file")
    p.add_argument("--course-dir", required=True, help="Course directory (containing course.json)")
    p.add_argument("--course-prompt", action="store_true",
                   help="Extract course.course_prompt")
    p.add_argument("--outline-bid", default=None,
                   help="Extract items[<bid>].markdownflow_prompt for the given outline_item_bid")
    p.add_argument("-o", "--output", required=True, help="Output .md path")
    p.add_argument("--force", action="store_true",
                   help="Overwrite the output file if it already exists")

    # ── embed (local: standalone .md -> course.json field) ──
    p = sub.add_parser("embed",
                       help="Write a standalone .md file back into the corresponding "
                            "field in the course directory's course.json (atomic)")
    p.add_argument("--course-dir", required=True, help="Course directory (containing course.json)")
    p.add_argument("--course-prompt", action="store_true",
                   help="Embed into course.course_prompt")
    p.add_argument("--outline-bid", default=None,
                   help="Embed into items[<bid>].markdownflow_prompt for the given outline_item_bid")
    p.add_argument("--from", dest="from_file", required=True,
                   help="Source .md path")

    # ── validate (local: course.json schema check) ──
    p = sub.add_parser("validate",
                       help="Run ADR-001 §D3 schema validation on a course directory's course.json")
    p.add_argument("--course-dir", required=True, help="Course directory (containing course.json)")
    p.add_argument("--mode", choices=["push", "import"], default="push",
                   help="Validation mode: 'push' rejects placeholder bids, "
                        "'import' allows them (default: push)")

    return parser


def main():
    load_env()

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "login": cmd_login,
        "list": cmd_list,
        "show": cmd_show,
        "history": cmd_history,
        "export": cmd_export,
        "create": cmd_create,
        "update-meta": cmd_update_meta,
        "add-chapter": cmd_add_chapter,
        "add-lesson": cmd_add_lesson,
        "update-lesson": cmd_update_lesson,
        "rename-lesson": cmd_rename_lesson,
        "delete-lesson": cmd_delete_lesson,
        "reorder": cmd_reorder,
        "import": cmd_import,
        "build": cmd_build,
        "publish": cmd_publish,
        "archive": cmd_archive,
        "unarchive": cmd_unarchive,
        "pull": cmd_pull,
        "push": cmd_push,
        "extract": cmd_extract,
        "embed": cmd_embed,
        "validate": cmd_validate,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
