#!/usr/bin/env python3
"""Copy canonical manifests into a local ai-shifu-website checkout."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        tmp.write_bytes(source.read_bytes())
        os.replace(tmp, destination)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Sync canonical Skill manifests to the Chinese website checkout"
    )
    parser.add_argument(
        "--website-repo",
        type=Path,
        default=repo_root.parent / "ai-shifu-website",
        help="Path to the ai-shifu-website checkout",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify that the website copies match; do not write",
    )
    args = parser.parse_args()

    website_repo = args.website_repo.expanduser().resolve()
    if not (website_repo / ".git").exists() or not (website_repo / "zh").is_dir():
        print(f"Invalid ai-shifu-website checkout: {website_repo}", file=sys.stderr)
        return 1

    sources = sorted((repo_root / "manifests").glob("*.json"))
    if not sources:
        print("No canonical manifests found", file=sys.stderr)
        return 1

    destination_dir = website_repo / "zh" / ".well-known" / "skills"
    mismatches: list[str] = []
    for source in sources:
        destination = destination_dir / source.name
        matches = destination.is_file() and destination.read_bytes() == source.read_bytes()
        if args.check:
            if not matches:
                mismatches.append(source.name)
        elif not matches:
            atomic_copy(source, destination)
            print(f"Synced {source.name} -> {destination}")

    if mismatches:
        print(
            "Website manifest copies are stale: " + ", ".join(mismatches),
            file=sys.stderr,
        )
        return 1
    if args.check:
        print(f"Verified {len(sources)} website manifest copy/copies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
