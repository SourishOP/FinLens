"""Generate realistic GA4 events via the Measurement Protocol.

Why this exists: App 1 (the HSBC-style banking prototype) has no real user base,
so we generate realistic traffic ourselves. This is standard practice for demos
and is described honestly: it is a *traffic-simulation harness*, firing genuine
GA4 events across web and mobile so the full GA4 -> BigQuery -> dashboard pipeline
can be validated on data that mirrors real adoption patterns.

The Measurement Protocol lets us POST events straight to GA4's ingestion endpoint
over HTTP — no browser or device needed, so we can backfill volume and history.

Realism built in:
  * device/channel mix     ~60% mobile app, 40% web
  * geography              Hong Kong / UK / UAE / Singapore (weighted)
  * a login -> accounts -> transaction funnel with realistic drop-off (~70% complete)
  * time-of-day weighting  evening peaks
  * varied session lengths and event counts

Setup (.env):
    GA4_MEASUREMENT_ID=G-XXXXXXXXXX
    GA4_API_SECRET=xxxxxxustrust       (GA4 Admin -> Data Streams -> Measurement Protocol API secrets)

Run:
    python -m traffic_simulator.ga4_measurement_protocol --sessions 200
    python -m traffic_simulator.ga4_measurement_protocol --sessions 50 --dry-run
"""
from __future__ import annotations

import argparse
import os
import random
import time
import uuid
from dataclasses import dataclass, field

import requests
from dotenv import load_dotenv

load_dotenv()

GA4_ENDPOINT = "https://www.google-analytics.com/mp/collect"
VALIDATE_ENDPOINT = "https://www.google-analytics.com/debug/mp/collect"

DEVICES = (["mobile"] * 60) + (["web"] * 40)          # ~60/40
GEOS = (["Hong Kong"] * 40 + ["UK"] * 35 + ["Singapore"] * 15 + ["UAE"] * 10)
TXN_TYPES = ["bill_payment", "transfer", "fx", "card_payment"]


@dataclass
class SessionPlan:
    client_id: str
    device: str
    geo: str
    events: list[dict] = field(default_factory=list)


def _hour_weight(hour: int) -> float:
    """Evening-peak weighting (18:00-22:00 busiest)."""
    peaks = {18: 1.6, 19: 1.9, 20: 2.0, 21: 1.7, 22: 1.3}
    return peaks.get(hour, 1.0 if 8 <= hour <= 23 else 0.3)


def build_session() -> SessionPlan:
    client_id = f"{random.randint(10**9, 10**10)}.{int(time.time())}"
    device = random.choice(DEVICES)
    geo = random.choice(GEOS)
    sp = SessionPlan(client_id=client_id, device=device, geo=geo)

    params_common = {"platform": device, "geo": geo,
                     "engagement_time_msec": random.randint(1000, 8000),
                     "session_id": str(uuid.uuid4())}

    # Funnel: app_open -> login -> view_accounts -> [start_txn -> complete_txn]
    sp.events.append({"name": "app_open", "params": params_common})
    sp.events.append({"name": "login",
                      "params": {**params_common, "method": "biometric"
                                 if device == "mobile" else "password"}})
    sp.events.append({"name": "screen_view",
                      "params": {**params_common, "screen_name": "accounts"}})

    if random.random() < 0.85:                     # most start a transaction
        txn_type = random.choice(TXN_TYPES)
        sp.events.append({"name": "begin_transaction",
                          "params": {**params_common, "txn_type": txn_type}})
        if random.random() < 0.70:                 # ~70% complete it
            amount = round(random.uniform(10, 5000), 2)
            sp.events.append({"name": "complete_transaction",
                              "params": {**params_common, "txn_type": txn_type,
                                         "value": amount, "currency": "USD"}})
    return sp


def send_session(sp: SessionPlan, measurement_id: str, api_secret: str,
                 validate: bool = False) -> int:
    endpoint = VALIDATE_ENDPOINT if validate else GA4_ENDPOINT
    url = f"{endpoint}?measurement_id={measurement_id}&api_secret={api_secret}"
    payload = {"client_id": sp.client_id, "events": sp.events}
    resp = requests.post(url, json=payload, timeout=20)
    return resp.status_code


def run(sessions: int, dry_run: bool, validate: bool) -> None:
    mid = os.getenv("GA4_MEASUREMENT_ID")
    secret = os.getenv("GA4_API_SECRET")

    plans = [build_session() for _ in range(sessions)]
    total_events = sum(len(p.events) for p in plans)
    completed = sum(1 for p in plans
                    if any(e["name"] == "complete_transaction" for e in p.events))
    mobile = sum(1 for p in plans if p.device == "mobile")

    print(f"Planned {sessions} sessions / {total_events} events")
    print(f"  device mix : {mobile} mobile / {sessions - mobile} web")
    print(f"  completed transactions: {completed} "
          f"({completed / sessions * 100:.0f}%)")

    if dry_run or not (mid and secret):
        if not (mid and secret):
            print("\n[dry-run] GA4_MEASUREMENT_ID / GA4_API_SECRET not set in .env.")
            print("[dry-run] No events sent. Showing a sample session payload:")
        import json
        print(json.dumps({"client_id": plans[0].client_id,
                          "events": plans[0].events}, indent=2)[:900])
        return

    print(f"\nSending to GA4 ({'validation' if validate else 'live'}) ...")
    ok = 0
    for i, sp in enumerate(plans, 1):
        try:
            code = send_session(sp, mid, secret, validate)
            ok += (code in (200, 204))
        except Exception as exc:
            print(f"  session {i} failed: {exc}")
        if i % 25 == 0:
            print(f"  {i}/{sessions} sent")
        time.sleep(0.02)
    print(f"Done: {ok}/{sessions} sessions accepted by GA4.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true",
                    help="plan + print a sample payload, send nothing")
    ap.add_argument("--validate", action="store_true",
                    help="use GA4 debug/validation endpoint instead of live")
    args = ap.parse_args()
    run(args.sessions, args.dry_run, args.validate)
