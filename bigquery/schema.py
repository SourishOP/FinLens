"""Logical table catalog for the warehouse (documentation + load routing).

Each entry maps a produced data file to a (layer, table) destination. This is the
single place that defines what lands in the warehouse, used by load_to_bq.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class TableSpec:
    layer: str
    table: str
    source_csv: Path
    description: str


CATALOG: list[TableSpec] = [
    TableSpec("raw", "group_income_statement",
              _ROOT / "data" / "financials" / "group_income_statement_long.csv",
              "REAL quarterly group income-statement metrics from HSBC Data Packs."),
    TableSpec("raw", "churn_scored",
              _ROOT / "data" / "predictions" / "churn_scored.csv",
              "SIMULATED customers scored by churn risk (LightGBM)."),
    TableSpec("raw", "acquisition_scored",
              _ROOT / "data" / "predictions" / "acquisition_scored.csv",
              "SIMULATED customers scored by acquisition propensity."),
]
