#!/usr/bin/env python3
"""Run the AI-Shifu skill release command interface."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_shifu_release.cli import main

if __name__ == "__main__":
    main()
