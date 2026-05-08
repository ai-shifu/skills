#!/usr/bin/env python3
"""Live API helper for the creator-course-analysis-report skill."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv, set_key

SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = SKILL_DIR / ".env"
FALLBACK_ENV_FILE = (
    Path.home()
    / ".codex"
    / "skills"
    / "ai-shifu-course-creator"
    / ".env"
)
REGION_URLS = {
    "cn": "https://app.ai-shifu.cn",
    "global": "https://app.ai-shifu.com",
}
DEFAULT_BASE_URL = REGION_URLS["cn"]
EXPORT_TYPES = {"learner_progress", "follow_up_detail"}


def load_env() -> None:
    if FALLBACK_ENV_FILE.exists():
        load_dotenv(dotenv_path=FALLBACK_ENV_FILE, override=False)
    if ENV_FILE.exists():
        load_dotenv(dotenv_path=ENV_FILE, override=True)


def save_env(token: str | None = None, base_url: str | None = None) -> None:
    if not ENV_FILE.exists():
        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENV_FILE.touch(mode=0o600)
    env_path = str(ENV_FILE)
    if token:
        set_key(env_path, "SHIFU_TOKEN", token)
    if base_url:
        set_key(env_path, "SHIFU_BASE_URL", base_url.rstrip("/"))
    os.chmod(env_path, 0o600)


def resolve_auth(args: argparse.Namespace) -> tuple[str, str]:
    base_url = (getattr(args, "base_url", None) or os.environ.get("SHIFU_BASE_URL") or "").strip()
    token = (getattr(args, "token", None) or os.environ.get("SHIFU_TOKEN") or "").strip()
    if not base_url:
        print(
            "Error: missing base URL. Use --base-url, set SHIFU_BASE_URL in skill .env, "
            "or reuse the ai-shifu-course-creator skill .env.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not token:
        print(
            "Error: missing token. Run `login` first, use --token, set SHIFU_TOKEN "
            "in skill .env, or reuse the ai-shifu-course-creator skill .env.",
            file=sys.stderr,
        )
        sys.exit(1)
    return base_url.rstrip("/"), token


def _login_post(base_url: str, path: str, payload: dict[str, Any], error_prefix: str) -> dict[str, Any]:
    resp = requests.post(
        f"{base_url}{path}",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    if not resp.ok:
        print(
            json.dumps(
                {
                    "ok": False,
                    "http_status": resp.status_code,
                    "url": f"{base_url}{path}",
                    "body": resp.text[:1000],
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        sys.exit(1)
    data = resp.json()
    if data.get("code") != 0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "step": error_prefix,
                    "response": data,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        sys.exit(1)
    return data


def api_request(
    base_url: str,
    token: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> Any:
    url = f"{base_url}/api/dashboard{path}"
    resp = requests.get(
        url,
        params=params,
        headers={
            "Cookie": f"token={token}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    if not resp.ok:
        print(
            json.dumps(
                {
                    "ok": False,
                    "http_status": resp.status_code,
                    "url": resp.url,
                    "body": resp.text[:1000],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)

    payload = resp.json()
    if payload.get("code") != 0:
        if payload.get("code") == 1005:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "code": 1005,
                        "message": "Token Expired",
                        "hint": "Run the `login` command again or update SHIFU_TOKEN.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            sys.exit(1)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(1)
    return payload.get("data")


def cmd_login(args: argparse.Namespace) -> None:
    region = (args.region or "").strip().lower()
    base_url = (args.base_url or "").strip()
    if not base_url:
        base_url = REGION_URLS.get(region, "")
    if not base_url and region in {"", "cn"}:
        base_url = DEFAULT_BASE_URL
    if not base_url:
        base_url = os.environ.get("SHIFU_BASE_URL", "").strip()
    base_url = base_url.rstrip("/")
    if not base_url:
        print(
            "Error: provide --region cn/global or --base-url for login.",
            file=sys.stderr,
        )
        sys.exit(1)

    if region == "global":
        print(
            "Global region does not support SMS login in this helper. "
            "Please log in manually and then save SHIFU_TOKEN / SHIFU_BASE_URL.",
            file=sys.stderr,
        )
        sys.exit(1)

    phone = (args.phone or "").strip()
    if not phone:
        print("Error: --phone is required for login.", file=sys.stderr)
        sys.exit(1)

    sms_code = (args.sms_code or "").strip()
    masked_phone = phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else phone

    if not sms_code:
        _login_post(
            base_url,
            "/api/user/console_send_sms_code",
            {"mobile": phone},
            "console_send_sms_code",
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "step": "sms_sent",
                    "message": f"SMS code sent to {masked_phone}",
                    "next_command": (
                        "python scripts/creator-analysis-cli.py "
                        + (f"--base-url {args.base_url} " if args.base_url else "")
                        + (f"--region {region} " if (not args.base_url and region) else "")
                        + f"login --phone {phone} --sms-code <code>"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    result = _login_post(
        base_url,
        "/api/user/login_sms",
        {
            "mobile": phone,
            "sms_code": sms_code,
            "login_context": "admin",
        },
        "login_sms",
    )
    token_data = result.get("data")
    token = token_data.get("token", "") if isinstance(token_data, dict) else token_data
    token = str(token or "").strip()
    if not token:
        print(
            json.dumps(
                {
                    "ok": False,
                    "message": "Login succeeded but no token was returned.",
                    "response": result,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    # Only save base_url if user explicitly provided --base-url;
    # otherwise preserve whatever is already in .env (e.g. localhost).
    if args.base_url:
        save_env(token=token, base_url=base_url)
    else:
        save_env(token=token)
    print(
        json.dumps(
            {
                "ok": True,
                "step": "login_success",
                "message": f"Login successful for {masked_phone}",
                "saved_to": str(ENV_FILE),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_config(args: argparse.Namespace) -> None:
    if not args.token and not args.base_url:
        print("Nothing to save. Provide --token and/or --base-url.", file=sys.stderr)
        sys.exit(1)
    save_env(token=args.token, base_url=args.base_url)
    print(f"Saved config to {ENV_FILE}")


def cmd_entry(args: argparse.Namespace) -> None:
    base_url, token = resolve_auth(args)
    data = api_request(
        base_url,
        token,
        "/entry",
        params={
            "page_index": args.page_index,
            "page_size": args.page_size,
            **({"timezone": args.timezone} if args.timezone else {}),
        },
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_context(args: argparse.Namespace) -> None:
    base_url, token = resolve_auth(args)
    data = api_request(
        base_url,
        token,
        f"/shifus/{args.shifu_bid}/analysis-context",
        params={k: v for k, v in {"timezone": args.timezone}.items() if v},
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_export(args: argparse.Namespace) -> None:
    if args.export_type not in EXPORT_TYPES:
        print(f"Unsupported export type: {args.export_type}", file=sys.stderr)
        sys.exit(1)
    base_url, token = resolve_auth(args)
    data = api_request(
        base_url,
        token,
        f"/shifus/{args.shifu_bid}/analysis-exports",
        params={
            "type": args.export_type,
            "page_index": args.page_index,
            "page_size": args.page_size,
            **({"timezone": args.timezone} if args.timezone else {}),
        },
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_bundle(args: argparse.Namespace) -> None:
    base_url, token = resolve_auth(args)
    timezone_params = {"timezone": args.timezone} if args.timezone else {}
    context = api_request(
        base_url,
        token,
        f"/shifus/{args.shifu_bid}/analysis-context",
        params=timezone_params,
    )
    bundle: dict[str, Any] = {"context": context, "exports": {}}
    for export_type in args.export_types:
        if export_type not in EXPORT_TYPES:
            print(f"Unsupported export type: {export_type}", file=sys.stderr)
            sys.exit(1)
        bundle["exports"][export_type] = api_request(
            base_url,
            token,
            f"/shifus/{args.shifu_bid}/analysis-exports",
            params={
                "type": export_type,
                "page_index": 1,
                "page_size": args.page_size,
                **timezone_params,
            },
        )
    print(json.dumps(bundle, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Creator course analysis live API helper"
    )
    parser.add_argument("--base-url", default=None, help="Base app URL")
    parser.add_argument("--token", default=None, help="Auth token")

    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser(
        "login",
        help="SMS login and save token/base-url to skill .env",
    )
    login_parser.add_argument(
        "--region",
        default="cn",
        help="Region alias: cn or global",
    )
    login_parser.add_argument("--phone", default=None, help="Phone number")
    login_parser.add_argument(
        "--sms-code",
        default=None,
        help="SMS code for the second login step",
    )
    login_parser.set_defaults(func=cmd_login)

    config_parser = subparsers.add_parser("config", help="Save token/base-url to skill .env")
    config_parser.add_argument("--base-url", default=None, help="Base app URL")
    config_parser.add_argument("--token", default=None, help="Auth token")
    config_parser.set_defaults(func=cmd_config)

    entry_parser = subparsers.add_parser("entry", help="Fetch creator dashboard entry")
    entry_parser.add_argument("--page-index", type=int, default=1)
    entry_parser.add_argument("--page-size", type=int, default=20)
    entry_parser.add_argument("--timezone", default=None, help="Timezone name")
    entry_parser.set_defaults(func=cmd_entry)

    context_parser = subparsers.add_parser("context", help="Fetch analysis context")
    context_parser.add_argument("shifu_bid", help="Course business id")
    context_parser.add_argument("--timezone", default=None, help="Timezone name")
    context_parser.set_defaults(func=cmd_context)

    export_parser = subparsers.add_parser("export", help="Fetch one export type")
    export_parser.add_argument("shifu_bid", help="Course business id")
    export_parser.add_argument("export_type", help="learner_progress or follow_up_detail")
    export_parser.add_argument("--page-index", type=int, default=1)
    export_parser.add_argument("--page-size", type=int, default=100)
    export_parser.add_argument("--timezone", default=None, help="Timezone name")
    export_parser.set_defaults(func=cmd_export)

    bundle_parser = subparsers.add_parser(
        "bundle",
        help="Fetch context plus one or more export types",
    )
    bundle_parser.add_argument("shifu_bid", help="Course business id")
    bundle_parser.add_argument(
        "--export-types",
        nargs="*",
        default=["learner_progress", "follow_up_detail"],
        help="Export types to include",
    )
    bundle_parser.add_argument("--page-size", type=int, default=100)
    bundle_parser.add_argument("--timezone", default=None, help="Timezone name")
    bundle_parser.set_defaults(func=cmd_bundle)

    return parser


def main() -> None:
    load_env()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
