#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec python3 "$REPO_DIR/scripts/release.py" build \
  --output "${DIST_DIR:-$REPO_DIR/dist}"
