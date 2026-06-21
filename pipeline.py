"""
WC26 Stats — Full Pipeline

Runs the complete data fetch → compute → build cycle:
  1. Fetch latest match stats from ESPN API
  2. Compute team ratings (ATK/DEF/EFF/AGG)
  3. Build advanced analytics dashboard (6 dimensions)
  4. Generate index with timestamp

Usage:
    python pipeline.py              # Full pipeline
    python pipeline.py --skip-fetch # Skip ESPN fetch (rebuild from existing data)
    python pipeline.py --date 20260616  # Fetch a specific date only

Designed to run in GitHub Actions or locally.
"""

import subprocess
import sys
import os
import argparse
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(SCRIPT_DIR, "public")


def run_step(description, cmd, env=None):
    """Run a pipeline step and exit on failure."""
    print(f"\n{'─' * 60}")
    print(f"  ▶ {description}")
    print(f"{'─' * 60}")

    merged_env = {**os.environ, "REPO_DIR": SCRIPT_DIR}
    if env:
        merged_env.update(env)

    result = subprocess.run(
        cmd,
        cwd=SCRIPT_DIR,
        env=merged_env,
        text=True,
    )

    if result.returncode != 0:
        print(f"\n  ✗ FAILED: {description}")
        print(f"    Exit code: {result.returncode}")
        sys.exit(result.returncode)

    print(f"  ✓ {description}")


def main():
    parser = argparse.ArgumentParser(description="WC26 Stats Pipeline")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Skip ESPN data fetch, rebuild from existing CSVs")
    parser.add_argument("--date", type=str,
                        help="Fetch a specific date only (YYYYMMDD)")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch even if matches already recorded")
    args = parser.parse_args()

    print("=" * 60)
    print("  WC26 Stats — Pipeline")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Ensure public/ exists
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    # Step 1: Fetch data from ESPN
    if not args.skip_fetch:
        fetch_cmd = [sys.executable, "fetch_espn_stats.py", "--no-ratings"]
        if args.date:
            fetch_cmd += ["--date", args.date]
        else:
            fetch_cmd.append("--all")
        if args.force:
            fetch_cmd.append("--force")

        run_step("Fetching match data from ESPN", fetch_cmd)
    else:
        print("\n  ⏭ Skipping ESPN fetch (--skip-fetch)")

    # Step 2: Build advanced dashboard
    run_step("Building advanced analytics dashboard", [sys.executable, "build_dashboard.py"])

    # Step 3: Done
    print("\n" + "=" * 60)
    print("  ✓ Pipeline complete!")
    print(f"    Output: {PUBLIC_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
