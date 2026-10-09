"""Load produced CSVs into the warehouse (BigQuery or local SQLite mirror).

Pipeline:
  1. Load each catalog file into the `raw` layer.
  2. Run SQL transforms (raw -> staging -> marts) via sql_transforms/.
  3. Load the live stock-price series into raw (fetched fresh via yfinance).

Run:
    python -m bigquery.load_to_bq
"""
from __future__ import annotations

import pandas as pd

from bigquery.schema import CATALOG
from bigquery.warehouse import get_warehouse


def load_raw(wh) -> list[str]:
    loaded = []
    for spec in CATALOG:
        if not spec.source_csv.exists():
            print(f"[load] SKIP {spec.layer}.{spec.table}: {spec.source_csv.name} "
                  "not found (run the relevant model/parser first)")
            continue
        df = pd.read_csv(spec.source_csv)
        n = wh.load_dataframe(df, spec.layer, spec.table)
        print(f"[load] {spec.layer}.{spec.table}: {n} rows")
        loaded.append(f"{spec.layer}.{spec.table}")
    return loaded


def load_market_data(wh) -> None:
    """Fetch the live HSBC share price and land it in raw (fresh each run)."""
    try:
        from modelling.common.market_data import load_prices
        prices = load_prices(period="2y", interval="1d").reset_index()
        prices["Date"] = pd.to_datetime(prices["Date"]).dt.strftime("%Y-%m-%d")
        n = wh.load_dataframe(prices, "raw", "share_price")
        print(f"[load] raw.share_price: {n} rows")
    except Exception as exc:
        print(f"[load] share_price skipped: {exc}")


def run_transforms(wh) -> None:
    from bigquery.sql_transforms.transforms import run_all
    run_all(wh)


def main():
    wh = get_warehouse()
    print("\n--- Loading raw layer ---")
    load_raw(wh)
    load_market_data(wh)
    print("\n--- Running transforms (staging + marts) ---")
    run_transforms(wh)
    print("\n--- Tables now in warehouse ---")
    for t in sorted(wh.list_tables()):
        print(f"  {t}")


if __name__ == "__main__":
    main()
