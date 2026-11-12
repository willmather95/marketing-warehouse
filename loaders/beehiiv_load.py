#!/usr/bin/env python3
"""STUB: Beehiiv loader. Not implemented yet; the nightly run calls it and it prints only.

Needs (never commit these):
- A Beehiiv API key with publication read access
- Publication IDs
- Env: BEEHIIV_KEY_FILE, BEEHIIV_PUBLICATION_IDS=news:pub_xxx

Planned tables:
  beehiiv_posts(publication_id, post_id, title, published_at, web_url, ...)
  beehiiv_stats_daily(publication_id, date, recipients, opens, clicks, unsubs, ...)
"""
from __future__ import annotations


def main():
    print("beehiiv_load.py: STUB, no pull yet. Needs a Beehiiv API key and publication IDs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
