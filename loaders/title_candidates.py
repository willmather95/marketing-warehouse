#!/usr/bin/env python3
"""Title-rewrite candidates: pages at avg position 1-10 with CTR below the expected curve.

  python loaders/title_candidates.py --brand tool
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import config
from config import EXPECTED_CTR_BY_POSITION
from schema import connect, init_schema


CURVE_NOTE = (
    "Expected CTR curve: industry-average organic CTR by position "
    "(AWR-style desktop US averages for positions 1-10). "
    "Fractional positions are linearly interpolated between adjacent integers. "
    "Values: "
    + ", ".join(f"{k}={v:.4f}" for k, v in EXPECTED_CTR_BY_POSITION.items())
)


def expected_ctr(position: float) -> float:
    if position is None or position < 1:
        return EXPECTED_CTR_BY_POSITION[1]
    if position >= 10:
        return EXPECTED_CTR_BY_POSITION[10]
    lo = int(position)
    hi = lo + 1
    if hi > 10:
        return EXPECTED_CTR_BY_POSITION[10]
    frac = position - lo
    return (
        EXPECTED_CTR_BY_POSITION[lo] * (1 - frac)
        + EXPECTED_CTR_BY_POSITION[hi] * frac
    )


def run(brand: str, window_days: int = 90, min_impressions: int = 50):
    init_schema()
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    con = connect(read_only=True)
    try:
        max_date = con.execute(
            "SELECT MAX(date) FROM gsc_page_query WHERE brand = ?", [brand]
        ).fetchone()[0]
        if not max_date:
            raise RuntimeError(f"no GSC rows loaded for brand {brand!r}")
        start = max_date - timedelta(days=window_days - 1)
        rows = con.execute(
            """
            SELECT
              page,
              SUM(clicks) AS clicks,
              SUM(impressions) AS impressions,
              CASE WHEN SUM(impressions) > 0
                   THEN SUM(clicks) * 1.0 / SUM(impressions)
                   ELSE 0 END AS ctr,
              CASE WHEN SUM(impressions) > 0
                   THEN SUM(position * impressions) / SUM(impressions)
                   ELSE NULL END AS avg_position
            FROM gsc_page_query
            WHERE brand = ?
              AND date BETWEEN ? AND ?
            GROUP BY page
            HAVING SUM(impressions) >= ?
               AND avg_position BETWEEN 1 AND 10
            ORDER BY page
            """,
            [brand, start, max_date, min_impressions],
        ).fetchall()
    finally:
        con.close()

    out_rows = []
    for page, clicks, impressions, ctr, avg_pos in rows:
        exp = expected_ctr(float(avg_pos))
        gap = exp - float(ctr)
        if gap <= 0:
            continue
        out_rows.append(
            {
                "page": page,
                "avg_position": round(float(avg_pos), 2),
                "impressions": int(impressions),
                "clicks": int(clicks),
                "ctr": round(float(ctr), 4),
                "expected_ctr": round(exp, 4),
                "gap": round(gap, 4),
                "window_start": str(start),
                "window_end": str(max_date),
            }
        )
    out_rows.sort(key=lambda r: (-r["gap"], -r["impressions"]))

    out_path = config.OUTPUTS_DIR / f"{brand}_title_rewrite_candidates.csv"
    import csv

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "page",
                "avg_position",
                "impressions",
                "clicks",
                "ctr",
                "expected_ctr",
                "gap",
                "window_start",
                "window_end",
            ],
        )
        w.writeheader()
        w.writerows(out_rows)

    note_path = config.OUTPUTS_DIR / f"{brand}_title_rewrite_candidates.NOTES.md"
    note_path.write_text(
        f"# {brand} title-rewrite candidates\n\n"
        f"- Window: last {window_days} days with data ({start} to {max_date})\n"
        f"- Filters: avg position 1-10, impressions >= {min_impressions}, CTR below expected\n"
        f"- {CURVE_NOTE}\n"
        f"- Rows: {len(out_rows)}\n"
        f"- Output: `{out_path}`\n",
        encoding="utf-8",
    )
    print(f"wrote {out_path} rows={len(out_rows)}")
    return out_path, out_rows


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--brand", required=True)
    p.add_argument("--window-days", type=int, default=90)
    p.add_argument("--min-impressions", type=int, default=50)
    a = p.parse_args()
    run(a.brand, a.window_days, a.min_impressions)
