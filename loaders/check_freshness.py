#!/usr/bin/env python3
"""After the nightly load: is every site's data fresh, and did any row count drop?

  python loaders/check_freshness.py      # exit 1 and print problems if anything needs a look
"""
from __future__ import annotations

import datetime
import json
import sys

import config
from schema import connect

STALE_DAYS = 4  # Search Console lags 2-3 days


def main() -> int:
    state_path = config.OUTPUTS_DIR / "freshness-state.json"
    prev = json.loads(state_path.read_text()) if state_path.is_file() else {}
    con = connect(read_only=True)
    try:
        rows = con.execute(
            "SELECT brand, max_date, row_count FROM gsc_load_meta ORDER BY brand"
        ).fetchall()
    finally:
        con.close()
    today = datetime.date.today()
    problems, now = [], {}
    for brand, max_date, count in rows:
        age = (today - max_date).days
        now[brand] = {"max_date": str(max_date), "rows": int(count)}
        if age > STALE_DAYS:
            problems.append(f"{brand}: data is {age} days old (max_date {max_date})")
        if brand in prev and count < prev[brand]["rows"]:
            problems.append(f"{brand}: row count dropped {prev[brand]['rows']} -> {count}")
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(now, indent=2))
    for b, v in now.items():
        print(f"{b:12} rows {v['rows']:>9,}  current to {v['max_date']}")
    if problems:
        print("NEEDS A LOOK:\n  " + "\n  ".join(problems))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
