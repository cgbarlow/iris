"""Genericness invariant CI guard (ADR-214).

The pytest harness lets local test runs catch violations before they
hit CI. Mirrors `scripts/check_aggregation_genericness.py` exactly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_genericness_invariant_passes() -> None:
    """No banned domain terms in code paths. See ADR-214."""
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "check_aggregation_genericness.py"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Genericness invariant violation:\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
