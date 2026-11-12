#!/usr/bin/env python3
"""STUB: Meta Ads loader. Not implemented yet; the nightly run calls it and it prints only.

Needs (never commit these):
- A Marketing API system-user token with ads_read
- Ad account IDs (act_XXXXXXXX)
- Env: META_TOKEN_FILE, META_AD_ACCOUNT_IDS=tool:act_xxx

Planned tables:
  meta_ads_insights_daily(account_id, date, campaign_id, adset_id, ad_id,
                          spend, impressions, clicks, ctr, cpc, leads, ...)
"""
from __future__ import annotations


def main():
    print("meta_ads_load.py: STUB, no pull yet. Needs a Meta token and ad account IDs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
