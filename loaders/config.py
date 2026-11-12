"""Shared config for the warehouse loaders. No secrets in this file.

Everything machine-specific comes from environment variables:
  WAREHOUSE_DIR     folder for brain.duckdb, outputs/ (default: ./warehouse)
  WAREHOUSE_SITES   path to a sites JSON file (default: ./sites.json, else sites.example.json)
  GSC_KEY_FILE      service account JSON with Search Console read access (mode 600, outside the repo)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("WAREHOUSE_DIR", REPO_ROOT / "warehouse"))
DB_PATH = Path(os.environ.get("WAREHOUSE_DB", DATA_DIR / "brain.duckdb"))
OUTPUTS_DIR = DATA_DIR / "outputs"


def _sites_file() -> Path:
    if os.environ.get("WAREHOUSE_SITES"):
        return Path(os.environ["WAREHOUSE_SITES"])
    local = REPO_ROOT / "sites.json"
    return local if local.is_file() else REPO_ROOT / "sites.example.json"


def gsc_properties() -> list[dict]:
    """[{brand, property, note}] — exact Search Console property strings."""
    return json.loads(_sites_file().read_text())["gsc_properties"]


def gsc_key_file() -> Path:
    v = os.environ.get("GSC_KEY_FILE")
    if not v:
        raise RuntimeError("set GSC_KEY_FILE to a Search Console service account JSON (mode 600)")
    return Path(v)


GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
GSC_MONTHS = 16  # Search Console keeps ~16 months; the first run backfills all of it
GSC_LAG_DAYS = 2  # final data lags ~2 days
GSC_REVISE_DAYS = 3  # re-pull this many trailing days on incremental runs

# Industry-average organic CTR by position (desktop US averages, positions 1-10).
# A relative benchmark for title-rewrite candidates, not a promise.
EXPECTED_CTR_BY_POSITION = {
    1: 0.2795, 2: 0.1525, 3: 0.1103, 4: 0.0815, 5: 0.0651,
    6: 0.0495, 7: 0.0391, 8: 0.0332, 9: 0.0284, 10: 0.0258,
}
