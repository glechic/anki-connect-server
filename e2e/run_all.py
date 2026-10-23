#!/usr/bin/env python3
"""Run all single-server black-box suites against one anki-connect-server.

Usage:
    python3 e2e/run_all.py [BASE_URL]        # default http://localhost:8765

Runs the six topic suites sequentially (scheduling, reads, tags,
revlog_stats, models, meta) against the same server. The suites use
disjoint fixture names, so they coexist on one collection; review-count
assertions are relative by design.

This doubles as the regression pass: run all suites against the current
build before and after a change — any behavioral difference is a
regression. The sync suite is NOT run here: it needs its own
three-server topology with a local anki.syncserver — its topology
commands live in e2e/suite_sync.py's docstring.

Exit code is non-zero if any check fails or a suite crashes.
"""

from __future__ import annotations

import subprocess
import sys

SUITES = [
    "suite_scheduling.py",
    "suite_reads.py",
    "suite_tags.py",
    "suite_revlog_stats.py",
    "suite_models.py",
    "suite_meta.py",
]


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
    totals = {"passed": 0, "failed": 0, "observations": 0}
    failed_suites: list[str] = []

    for suite in SUITES:
        print(f"\n{'=' * 70}\n== {suite}\n{'=' * 70}")
        proc = subprocess.run(
            [sys.executable, f"e2e/{suite}", base],
            capture_output=True,
            text=True,
        )
        for line in proc.stdout.splitlines():
            if line.startswith("TOTAL:"):
                print(f"  {line.strip()}")
                parts = line.split()
                totals["passed"] += int(parts[1])
                totals["failed"] += int(parts[3])
                totals["observations"] += int(parts[5])
            elif line.startswith("[FAIL]"):
                print(f"  {line.strip()}")
        if proc.returncode != 0 and "TOTAL:" not in proc.stdout:
            print(proc.stdout[-2000:])
            print(proc.stderr[-2000:])
            failed_suites.append(suite)
        elif "TOTAL:" in proc.stdout and "0 failed" not in proc.stdout:
            failed_suites.append(suite)

    print(f"\n{'=' * 70}")
    print(
        f"ALL SUITES: {totals['passed']} passed, {totals['failed']} failed, "
        f"{totals['observations']} observations"
    )
    if failed_suites:
        print(f"Failing suites: {', '.join(failed_suites)}")
        return 1
    print("Sync suite not run (needs its own topology — see suite_sync.py docstring)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
