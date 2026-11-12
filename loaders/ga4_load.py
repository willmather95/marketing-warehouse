#!/usr/bin/env python3
"""STUB: GA4 loader. Not implemented yet; the nightly run calls it and it prints only.

Needs (never commit these):
- A service account with GA4 Data API read access on each property
- GA4 property IDs (numeric properties/XXXXXXX)
- Env: GA4_KEY_FILE, GA4_PROPERTY_IDS=tool:123,news:456

Planned tables:
  ga4_sessions_daily(property_id, date, sessions, users, engaged_sessions, ...)
  ga4_page_daily(property_id, date, page_path, views, ...)
  ga4_events_daily(property_id, date, event_name, count, ...)
"""
from __future__ import annotations


def main():
    print("ga4_load.py: STUB, no pull yet. Needs GA4 property IDs and a service account.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
