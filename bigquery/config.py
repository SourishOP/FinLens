"""Warehouse configuration + backend detection.

The platform works in two modes, chosen automatically:

  * BIGQUERY mode  -- when GCP_PROJECT_ID is set and credentials are available.
                      Load jobs and queries hit real Google BigQuery.
  * LOCAL mode     -- otherwise. A local SQLite database at data/warehouse.db
                      mirrors the same dataset.table structure, so everything is
                      demoable with zero cloud setup. Switch to BigQuery later by
                      filling in .env -- no code changes needed.

Dataset layering (identical in both modes):
    raw      -> data exactly as ingested
    staging  -> cleaned / typed
    marts    -> business-ready aggregates + prediction outputs
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).resolve().parents[1]
LOCAL_DB_PATH = _ROOT / "data" / "warehouse.db"


@dataclass(frozen=True)
class WarehouseConfig:
    project_id: str | None
    dataset_raw: str
    dataset_staging: str
    dataset_marts: str
    max_bytes_billed: int
    credentials_path: str | None

    @property
    def mode(self) -> str:
        creds_ok = (self.credentials_path and Path(self.credentials_path).exists())
        if self.project_id and (creds_ok or os.getenv("GOOGLE_CLOUD_ADC") == "1"):
            return "bigquery"
        return "local"

    def dataset(self, layer: str) -> str:
        return {"raw": self.dataset_raw, "staging": self.dataset_staging,
                "marts": self.dataset_marts}[layer]


def load_config() -> WarehouseConfig:
    return WarehouseConfig(
        project_id=os.getenv("GCP_PROJECT_ID"),
        dataset_raw=os.getenv("BQ_DATASET_RAW", "hsbc_raw"),
        dataset_staging=os.getenv("BQ_DATASET_STAGING", "hsbc_staging"),
        dataset_marts=os.getenv("BQ_DATASET_MARTS", "hsbc_marts"),
        max_bytes_billed=int(os.getenv("BQ_MAX_BYTES_BILLED", "1000000000")),
        credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    )


if __name__ == "__main__":
    cfg = load_config()
    print(f"Warehouse mode: {cfg.mode.upper()}")
    print(f"  project_id : {cfg.project_id or '(none)'}")
    print(f"  datasets   : {cfg.dataset_raw} / {cfg.dataset_staging} / {cfg.dataset_marts}")
    if cfg.mode == "local":
        print(f"  local db   : {LOCAL_DB_PATH}")
        print("  -> fill in .env (GCP_PROJECT_ID + GOOGLE_APPLICATION_CREDENTIALS) "
              "to use real BigQuery.")
