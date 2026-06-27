#!/usr/bin/env python3
"""Short finish test — wrapper for run_short_finish_test.py with tests paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
TREATMENT_DIR = TESTS_ROOT.parent / "backend" / "worker" / "scripts" / "treatment"
sys.path.insert(0, str(TREATMENT_DIR))

os.environ.setdefault(
    "CUTS_JSON",
    str(TESTS_ROOT / "fixtures" / "results" / "20260624T225609Z_eKxFuD3-pos" / "cuts_merged_claude.json"),
)
os.environ.setdefault("OUTPUT_ROOT", str(TESTS_ROOT / "render" / "output"))

from run_short_finish_test import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
