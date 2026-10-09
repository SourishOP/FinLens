"""Scheduled refresh jobs — velocity matched to each data source.

Design (as agreed): refresh rate matches how fast each source actually changes.
  * Share price  -> every 30 MINUTES (genuinely fast-moving market data).
  * Data Packs   -> once DAILY (quarterly data; only re-processes new documents).
  * GA4 ingest   -> hourly refresh of the warehouse session tables.

Uses APScheduler (cross-platform, self-contained — better than Windows Task
Scheduler for a portable demo). Runs in the foreground; Ctrl+C to stop.

    python -m scheduler.run_scheduler
    python -m scheduler.run_scheduler --once   # run each job once and exit
"""
from __future__ import annotations

import argparse
import datetime as dt


def job_share_price() -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] refreshing share price (30-min)")
    try:
        from bigquery.warehouse import get_warehouse
        from bigquery.load_to_bq import load_market_data
        load_market_data(get_warehouse())
    except Exception as exc:
        print(f"  share-price refresh failed: {exc}")


def job_datapacks() -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] checking Data Packs (daily)")
    try:
        from scrapers.hsbc_financials_scraper import run as scrape
        from parsers.datapack_parser import parse_from_registry
        scrape()                 # idempotent: only downloads new packs
        parse_from_registry()
    except Exception as exc:
        print(f"  Data Pack refresh failed: {exc}")


def job_ga4() -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] refreshing GA4 session tables (hourly)")
    try:
        from bigquery.ga4_ingest import ingest
        ingest()
    except Exception as exc:
        print(f"  GA4 refresh failed: {exc}")


def run_once() -> None:
    job_share_price(); job_datapacks(); job_ga4()
    print("All jobs ran once.")


def run_forever() -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler
    sched = BlockingScheduler()
    sched.add_job(job_share_price, "interval", minutes=30, id="share_price")
    sched.add_job(job_datapacks, "interval", hours=24, id="datapacks")
    sched.add_job(job_ga4, "interval", hours=1, id="ga4")
    print("Scheduler started: share price /30min, Data Packs /24h, GA4 /1h.")
    print("Running initial pass now, then on schedule. Ctrl+C to stop.")
    run_once()
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nScheduler stopped.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run each job once, exit")
    args = ap.parse_args()
    run_once() if args.once else run_forever()
