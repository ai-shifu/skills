#!/usr/bin/env python3
"""Validate every public Skill update manifest with the runtime rules."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def load_update_module(repo_root: Path, skill_name: str) -> ModuleType:
    module_path = repo_root / "skills" / skill_name / "scripts" / "skill_update.py"
    spec = importlib.util.spec_from_file_location(
        f"{skill_name.replace('-', '_')}_skill_update", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runtime validator: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    manifests_dir = repo_root / "manifests"
    manifest_files = sorted(manifests_dir.glob("*.json"))
    if not manifest_files:
        print("No manifests found", file=sys.stderr)
        return 1

    errors: list[str] = []
    for manifest_file in manifest_files:
        skill_name = manifest_file.stem
        skill_md = repo_root / "skills" / skill_name / "SKILL.md"
        try:
            raw = json.loads(manifest_file.read_text(encoding="utf-8"))
            update_module = load_update_module(repo_root, skill_name)
            manifest = update_module.validate_manifest(raw, skill_name)
            metadata = update_module.read_skill_metadata(skill_md)
            if metadata is None:
                raise ValueError(f"cannot read metadata from {skill_md}")
            if metadata.get("version") != manifest["latest"]:
                raise ValueError(
                    "SKILL.md version must equal manifest latest "
                    f"({metadata.get('version')!r} != {manifest['latest']!r})"
                )
        except Exception as exc:
            errors.append(f"{manifest_file}: {exc}")

    if errors:
        print("Manifest validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  error: {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(manifest_files)} Skill update manifest(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
