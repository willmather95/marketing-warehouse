#!/usr/bin/env python3
"""Nightly warehouse refresh. Schedule it (cron, launchd, a routine) for ~2:30 AM local.

  python loaders/run_nightly.py [--candidates-brand tool]

Steps:
  1) create tables if missing
  2) Search Console incremental load, every site in sites.json (live)
  3) title-rewrite candidates CSV for one brand
  4) GA4 / Meta Ads / Beehiiv loaders (stubs, print only)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(script: str, args: list[str] | None = None):
    cmd = [sys.executable, str(ROOT / script)] + (args or [])
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidates-brand", default=None)
    a = p.parse_args()
    run("schema.py")
    run("gsc_load.py")  # incremental after the first 16-month backfill
    if a.candidates_brand:
        run("title_candidates.py", ["--brand", a.candidates_brand])
    run("ga4_load.py")
    run("beehiiv_load.py")
    run("meta_ads_load.py")
    print("\nnightly complete")


if __name__ == "__main__":
    main()
