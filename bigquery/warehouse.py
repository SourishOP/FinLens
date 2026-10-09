"""Unified warehouse interface over BigQuery (cloud) or SQLite (local).

Both backends expose the same two operations the rest of the platform needs:

    load_dataframe(df, layer, table)   -> write/replace a table
    query(sql)                         -> run SQL, return a DataFrame

Tables are addressed as `<dataset>.<table>` in BigQuery and `<dataset>__<table>`
in SQLite (SQLite has no datasets, so we fold the dataset into the name but keep
the same logical identity). The NL->SQL feature in App 2 writes BigQuery-style SQL;
in local mode we do a light translation of the dataset-qualified names.
"""
from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod

import pandas as pd

from bigquery.config import LOCAL_DB_PATH, WarehouseConfig, load_config


class Warehouse(ABC):
    def __init__(self, cfg: WarehouseConfig):
        self.cfg = cfg

    @abstractmethod
    def load_dataframe(self, df: pd.DataFrame, layer: str, table: str,
                       if_exists: str = "replace") -> int: ...

    @abstractmethod
    def query(self, sql: str) -> pd.DataFrame: ...

    @abstractmethod
    def list_tables(self) -> list[str]: ...

    def fqtn(self, layer: str, table: str) -> str:
        """Fully-qualified table name for this backend."""
        return f"{self.cfg.dataset(layer)}.{table}"


# ---------------------------------------------------------------------------
# Local SQLite backend
# ---------------------------------------------------------------------------
class LocalWarehouse(Warehouse):
    def __init__(self, cfg: WarehouseConfig):
        super().__init__(cfg)
        LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return sqlite3.connect(LOCAL_DB_PATH)

    def _sqlite_name(self, layer: str, table: str) -> str:
        return f"{self.cfg.dataset(layer)}__{table}"

    def load_dataframe(self, df, layer, table, if_exists="replace") -> int:
        name = self._sqlite_name(layer, table)
        with self._conn() as con:
            df.to_sql(name, con, if_exists=if_exists, index=False)
        return len(df)

    def query(self, sql: str) -> pd.DataFrame:
        with self._conn() as con:
            return pd.read_sql_query(self._translate(sql), con)

    def list_tables(self) -> list[str]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        # present them back in dotted dataset.table form
        return [r[0].replace("__", ".", 1) for r in rows]

    def _translate(self, sql: str) -> str:
        """Map BigQuery `dataset.table` (and backticked) to SQLite `dataset__table`."""
        out = sql.replace("`", "")
        for layer in ("raw", "staging", "marts"):
            ds = self.cfg.dataset(layer)
            out = out.replace(f"{ds}.", f"{ds}__")
            out = out.replace(f"{self.cfg.project_id}.{ds}__", f"{ds}__") \
                if self.cfg.project_id else out
        return out


# ---------------------------------------------------------------------------
# BigQuery backend
# ---------------------------------------------------------------------------
class BigQueryWarehouse(Warehouse):
    def __init__(self, cfg: WarehouseConfig):
        super().__init__(cfg)
        from google.cloud import bigquery
        self._bq = bigquery
        self.client = bigquery.Client(project=cfg.project_id)
        self._ensure_datasets()

    def _ensure_datasets(self):
        for layer in ("raw", "staging", "marts"):
            ds_id = f"{self.cfg.project_id}.{self.cfg.dataset(layer)}"
            try:
                self.client.get_dataset(ds_id)
            except Exception:
                ds = self._bq.Dataset(ds_id)
                ds.location = "EU"  # HSBC is EU-listed; keep data in EU
                self.client.create_dataset(ds, exists_ok=True)

    def load_dataframe(self, df, layer, table, if_exists="replace") -> int:
        dest = f"{self.cfg.project_id}.{self.cfg.dataset(layer)}.{table}"
        disp = ("WRITE_TRUNCATE" if if_exists == "replace" else "WRITE_APPEND")
        job_cfg = self._bq.LoadJobConfig(write_disposition=disp)
        job = self.client.load_table_from_dataframe(df, dest, job_config=job_cfg)
        job.result()
        return len(df)

    def query(self, sql: str) -> pd.DataFrame:
        job_cfg = self._bq.QueryJobConfig(
            maximum_bytes_billed=self.cfg.max_bytes_billed)
        # create_bqstorage_client=False forces the standard REST download path,
        # so we don't need the 'bigquery.readsessions.create' permission (the
        # BigQuery Storage Read API). Keeps the service account minimal.
        return self.client.query(sql, job_config=job_cfg).to_dataframe(
            create_bqstorage_client=False)

    def list_tables(self) -> list[str]:
        out = []
        for layer in ("raw", "staging", "marts"):
            ds = self.cfg.dataset(layer)
            for t in self.client.list_tables(f"{self.cfg.project_id}.{ds}"):
                out.append(f"{ds}.{t.table_id}")
        return out


def get_warehouse(cfg: WarehouseConfig | None = None) -> Warehouse:
    cfg = cfg or load_config()
    if cfg.mode == "bigquery":
        print("[warehouse] using BigQuery")
        return BigQueryWarehouse(cfg)
    print("[warehouse] using LOCAL SQLite mirror (no GCP creds found)")
    return LocalWarehouse(cfg)


if __name__ == "__main__":
    wh = get_warehouse()
    print("tables:", wh.list_tables())
