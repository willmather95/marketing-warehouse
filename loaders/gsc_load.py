#!/usr/bin/env python3
"""Load GSC search analytics (date x page x query) into brain.duckdb.

Read-only against GSC. Incremental: after the first 16-month backfill, re-pulls
from (max_date - REVISE_DAYS) forward to account for GSC revisions/lag.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:  # the demo and tests don't need the Google client
    service_account = build = None
    HttpError = Exception

from config import (
    GSC_LAG_DAYS,
    GSC_MONTHS,
    GSC_REVISE_DAYS,
    GSC_SCOPES,
    gsc_key_file,
    gsc_properties,
)
from schema import connect, init_schema


def get_service(key_path: Path):
    if not key_path.is_file():
        raise FileNotFoundError(f"missing service account file: {key_path}")
    mode = key_path.stat().st_mode & 0o777
    if mode & 0o077:
        raise PermissionError(f"service account file must be mode 600, got {oct(mode)}")
    creds = service_account.Credentials.from_service_account_file(
        str(key_path), scopes=GSC_SCOPES
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def month_windows(start: date, end: date):
    """Yield inclusive (chunk_start, chunk_end) month-sized windows."""
    cur = start
    while cur <= end:
        if cur.month == 12:
            next_month = date(cur.year + 1, 1, 1)
        else:
            next_month = date(cur.year, cur.month + 1, 1)
        chunk_end = min(end, next_month - timedelta(days=1))
        yield cur, chunk_end
        cur = chunk_end + timedelta(days=1)


def fetch_page_query(service, property_url: str, start: date, end: date):
    """Paginate searchanalytics for dimensions date, page, query."""
    rows_out = []
    start_row = 0
    page_size = 25000
    while True:
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["date", "page", "query"],
            "rowLimit": page_size,
            "startRow": start_row,
            "dataState": "final",
        }
        for attempt in range(5):
            try:
                resp = (
                    service.searchanalytics()
                    .query(siteUrl=property_url, body=body)
                    .execute(num_retries=3)
                )
                break
            except HttpError as e:
                status = getattr(e.resp, "status", None)
                if status in (429, 500, 503) and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise
        batch = resp.get("rows", []) or []
        rows_out.extend(batch)
        if len(batch) < page_size:
            break
        start_row += page_size
        time.sleep(0.2)
    return rows_out


def upsert_rows(con, brand: str, property_url: str, rows, pulled_at: datetime):
    if not rows:
        return 0
    # Delete overlapping dates then insert (simpler than MERGE for DuckDB versions).
    dates = sorted({r["keys"][0] for r in rows})
    con.execute(
        "DELETE FROM gsc_page_query WHERE property = ? AND date >= ? AND date <= ?",
        [property_url, dates[0], dates[-1]],
    )
    payload = [
        (
            property_url,
            brand,
            r["keys"][0],
            r["keys"][1],
            r["keys"][2],
            float(r.get("clicks", 0)),
            float(r.get("impressions", 0)),
            float(r.get("ctr", 0)),
            float(r.get("position", 0)),
            pulled_at,
        )
        for r in rows
    ]
    con.executemany(
        """
        INSERT INTO gsc_page_query
        (property, brand, date, page, query, clicks, impressions, ctr, position, pulled_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    return len(payload)


def refresh_meta(con, brand: str, property_url: str, notes: str = ""):
    stats = con.execute(
        """
        SELECT MIN(date), MAX(date), COUNT(*)
        FROM gsc_page_query
        WHERE property = ?
        """,
        [property_url],
    ).fetchone()
    con.execute(
        """
        INSERT OR REPLACE INTO gsc_load_meta
        (property, brand, min_date, max_date, row_count, last_pulled_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            property_url,
            brand,
            stats[0],
            stats[1],
            int(stats[2] or 0),
            datetime.now(timezone.utc).replace(tzinfo=None),
            notes,
        ],
    )


def resolve_range(con, property_url: str, full: bool):
    today = date.today()
    end = today - timedelta(days=GSC_LAG_DAYS)
    if full:
        start = end - timedelta(days=int(GSC_MONTHS * 30.44))
        return start, end, "full"
    row = con.execute(
        "SELECT max_date FROM gsc_load_meta WHERE property = ?", [property_url]
    ).fetchone()
    if not row or not row[0]:
        start = end - timedelta(days=int(GSC_MONTHS * 30.44))
        return start, end, "full-first"
    start = row[0] - timedelta(days=GSC_REVISE_DAYS)
    if start > end:
        start = end - timedelta(days=GSC_REVISE_DAYS)
    return start, end, "incremental"


def load_property(entry, full: bool = False):
    service = get_service(gsc_key_file())
    con = connect()
    try:
        start, end, mode = resolve_range(con, entry["property"], full=full)
        print(
            f"[{entry['brand']}] {entry['property']} mode={mode} "
            f"{start}..{end} ({entry.get('note', '')})"
        )
        total = 0
        pulled_at = datetime.now(timezone.utc).replace(tzinfo=None)
        for c_start, c_end in month_windows(start, end):
            print(f"  chunk {c_start}..{c_end} ...", flush=True)
            rows = fetch_page_query(service, entry["property"], c_start, c_end)
            n = upsert_rows(con, entry["brand"], entry["property"], rows, pulled_at)
            total += n
            print(f"  chunk rows={n}", flush=True)
            time.sleep(0.3)
        refresh_meta(con, entry["brand"], entry["property"], notes=entry.get("note", ""))
        meta = con.execute(
            "SELECT min_date, max_date, row_count FROM gsc_load_meta WHERE property = ?",
            [entry["property"]],
        ).fetchone()
        print(
            f"[{entry['brand']}] done pulled_this_run={total} "
            f"stored={meta[2]} range={meta[0]}..{meta[1]}"
        )
        return {
            "brand": entry["brand"],
            "property": entry["property"],
            "pulled": total,
            "stored": meta[2],
            "min_date": str(meta[0]),
            "max_date": str(meta[1]),
        }
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="force 16-month backfill")
    parser.add_argument(
        "--brand",
        choices=[e["brand"] for e in gsc_properties()] + ["all"],
        default="all",
    )
    args = parser.parse_args()
    init_schema()
    results = []
    for entry in gsc_properties():
        if args.brand != "all" and entry["brand"] != args.brand:
            continue
        try:
            results.append(load_property(entry, full=args.full))
        except Exception as e:
            print(f"[{entry['brand']}] ERROR {type(e).__name__}: {e}", file=sys.stderr)
            results.append(
                {
                    "brand": entry["brand"],
                    "property": entry["property"],
                    "error": f"{type(e).__name__}: {e}",
                }
            )
    print("--- summary ---")
    for r in results:
        print(r)
    # exit non-zero if any failed
    if any("error" in r for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
