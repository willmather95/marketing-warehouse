#!/usr/bin/env python3
"""Build a demo warehouse from made-up Search Console rows, then pick title rewrites.

  pip install duckdb && python demo/make_demo.py

No credentials and no network. The site, pages and queries are invented. The shape
(date x page x query, clicks, impressions, ctr, position) matches what gsc_load.py stores.
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("WAREHOUSE_DIR", str(ROOT / "demo" / "out"))
sys.path.insert(0, str(ROOT / "loaders"))

import config  # noqa: E402
from gsc_load import refresh_meta, upsert_rows  # noqa: E402
from schema import connect, init_schema  # noqa: E402
import title_candidates  # noqa: E402

PROPERTY = "https://www.example-tool.com/"
TOPICS = ["hsa-limits", "fsa-vs-hsa", "hsa-eligible-expenses", "hsa-rollover", "dependent-care-fsa",
          "hsa-investing", "hsa-contribution-deadline", "lpfsa", "hsa-reimbursement", "hra-vs-hsa"]


def fake_rows(days: int = 120, seed: int = 7):
    rnd = random.Random(seed)
    end = date(2026, 11, 10)
    rows = []
    for t_i, topic in enumerate(TOPICS):
        base_pos = 2 + t_i * 0.8
        # a few pages under-earn clicks for their position: those are the rewrite picks
        ctr_factor = 0.45 if t_i in (1, 4, 7) else rnd.uniform(1.0, 1.3)
        for d in range(days):
            day = end - timedelta(days=d)
            for q in (topic.replace("-", " "), topic.replace("-", " ") + " 2026"):
                pos = max(1.0, rnd.gauss(base_pos, 0.6))
                imp = rnd.randint(5, 40)
                exp = title_candidates.expected_ctr(pos)
                clicks = sum(rnd.random() < exp * ctr_factor for _ in range(imp))
                rows.append({"keys": [day.isoformat(), f"{PROPERTY}{topic}", q],
                             "clicks": clicks, "impressions": imp,
                             "ctr": clicks / imp, "position": round(pos, 2)})
    return rows


def main():
    init_schema()
    con = connect()
    try:
        n = upsert_rows(con, "tool", PROPERTY, fake_rows(), datetime(2026, 11, 12, 8, 32))
        refresh_meta(con, "tool", PROPERTY, notes="made-up demo data")
        print(f"loaded {n:,} made-up rows into {config.DB_PATH}")
    finally:
        con.close()
    out, picks = title_candidates.run("tool")
    print(f"{len(picks)} title-rewrite candidates -> {out}")
    for r in picks[:5]:
        print(f"  {r['page']:52} pos {r['avg_position']:5}  ctr {r['ctr']:.3f} vs {r['expected_ctr']:.3f} expected")
    return picks


if __name__ == "__main__":
    main()
