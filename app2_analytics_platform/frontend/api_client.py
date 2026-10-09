"""Thin client for the App 2 FastAPI backend.

All warehouse access goes through the backend (never direct), so this client is
the single integration point. Degrades gracefully when the backend is down:
every call returns a dict with an 'error' key rather than raising.
"""
from __future__ import annotations

import os

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
_TIMEOUT = 180


def _get(path: str, params: dict | None = None) -> dict:
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": f"backend unreachable: {exc}"}


def _post(path: str, payload: dict) -> dict:
    try:
        r = httpx.post(f"{BACKEND_URL}{path}", json=payload, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": f"backend unreachable: {exc}"}


def health() -> dict:
    return _get("/health")


def tables() -> dict:
    return _get("/tables")


def nl_query(question: str) -> dict:
    return _post("/query", {"question": question})


def raw_query(sql: str) -> dict:
    return _post("/query/raw", {"sql": sql})


def kpis() -> dict:
    return _get("/metrics/kpis")


def financials() -> dict:
    return _get("/metrics/financials")


def forecast(module: str, metric: str | None = None) -> dict:
    return _get(f"/forecast/{module}", {"metric": metric} if metric else None)


def report(topic: str, data: dict | None = None) -> dict:
    return _post("/report", {"topic": topic, "data": data or {}})
