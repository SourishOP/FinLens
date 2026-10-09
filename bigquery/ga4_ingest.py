"""Ingest GA4 events into the warehouse — real export OR local simulation.

Two paths:
  * REAL: when a GA4 -> BigQuery export exists (dataset `analytics_<propertyId>`
    with daily `events_*` tables), we flatten the events' `event_params` in
    BigQuery SQL and aggregate to the session grain, emitting the SAME tidy
    session + event tables the simulator produces (identical schema). See
    the "Going live" section of README.md to enable it.
  * LOCAL fallback: generate the same tidy tables from the traffic simulator's
    session planner, so modelling/traffic and modelling/transactions can run and
    be demoed with zero cloud setup. The schema is identical, so swapping to the
    real export needs no model changes.

Output tables (warehouse `raw` layer):
  ga4_sessions(session_date, platform, device_category, geo, country, channel,
               source, browser, operating_system, age_band, gender, user_type,
               first_seen_date, sessions, engaged, engagement_time_sec,
               transactions, txn_value)  -- one row per session
  ga4_events(event_date, platform, geo, channel, event_name, event_count,
             event_value)

Run:
    python -m bigquery.ga4_ingest                 # auto (real if available, else sim)
    python -m bigquery.ga4_ingest --days 120 --daily-sessions 400   # sim size
"""
from __future__ import annotations

import argparse
import datetime as dt
import random

import numpy as np
import pandas as pd

from bigquery.warehouse import get_warehouse
from traffic_simulator.ga4_measurement_protocol import build_session


# GA4-report dimensions for the simulation.
_CHANNELS = (["Organic Search"] * 32 + ["Direct"] * 24 + ["Paid Search"] * 14 +
             ["Referral"] * 12 + ["Social"] * 10 + ["Email"] * 8)
_SOURCES = {"Organic Search": "google", "Direct": "(direct)",
            "Paid Search": "google_ads", "Referral": "partner-site.com",
            "Social": "linkedin", "Email": "newsletter"}
_BROWSERS = (["Chrome"] * 55 + ["Safari"] * 25 + ["Edge"] * 12 + ["Firefox"] * 8)
_OS_BY_DEVICE = {"mobile": (["iOS"] * 55 + ["Android"] * 45),
                 "desktop": (["Windows"] * 60 + ["macOS"] * 32 + ["Linux"] * 8),
                 "tablet": (["iPadOS"] * 70 + ["Android"] * 30)}
_AGE_BANDS = (["18-24"] * 18 + ["25-34"] * 30 + ["35-44"] * 24 +
              ["45-54"] * 15 + ["55-64"] * 9 + ["65+"] * 4)
_GENDERS = ["male"] * 52 + ["female"] * 48


def _simulate(days: int, daily_sessions: int, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create GA4-shaped daily session + event tables with the full set of
    dimensions GA4's standard reports use: channel/source (Acquisition),
    device/browser/OS (Tech), country (Demographics/geo), new-vs-returning +
    first-seen cohort date (Retention), engagement time & engaged sessions
    (Engagement). Weekly seasonality + growth trend give the series real signal.
    """
    random.seed(seed)
    np.random.seed(seed)
    today = dt.date.today()
    session_rows, event_rows = [], []
    # a pool of "returning" users seen on earlier days, keyed by first-seen date
    returning_pool: list[str] = []

    # device mix including tablet (GA4 Tech report)
    device_pool = ["mobile"] * 58 + ["desktop"] * 34 + ["tablet"] * 8

    for d in range(days):
        day = today - dt.timedelta(days=days - 1 - d)
        weekday = day.weekday()
        season = 0.75 if weekday >= 5 else 1.0
        trend = 1.0 + 0.004 * d
        n = max(10, int(daily_sessions * season * trend *
                        np.random.normal(1.0, 0.08)))

        for _ in range(n):
            device = random.choice(device_pool)
            geo = random.choice(["Hong Kong"] * 40 + ["United Kingdom"] * 35 +
                                ["Singapore"] * 15 + ["United Arab Emirates"] * 10)
            channel = random.choice(_CHANNELS)
            browser = random.choice(_BROWSERS)
            osys = random.choice(_OS_BY_DEVICE[device])
            age = random.choice(_AGE_BANDS)
            gender = random.choice(_GENDERS)

            # new vs returning + cohort first-seen date
            is_returning = bool(returning_pool) and random.random() < 0.42
            if is_returning:
                first_seen = random.choice(returning_pool)
                user_type = "returning"
            else:
                first_seen = day.isoformat()
                user_type = "new"
                returning_pool.append(first_seen)
                if len(returning_pool) > 4000:
                    returning_pool.pop(0)

            # engagement
            engagement_sec = max(2, int(np.random.gamma(2.2, 40)))
            engaged = engagement_sec >= 10
            # funnel -> transaction
            started = random.random() < 0.85
            completed = started and random.random() < 0.70
            txn_type = random.choice(["bill_payment", "transfer", "fx", "card_payment"])
            txn_value = round(random.uniform(10, 5000), 2) if completed else 0.0

            session_rows.append({
                "session_date": day.isoformat(),
                "platform": device, "device_category": device,
                "geo": geo, "country": geo,
                "channel": channel, "source": _SOURCES[channel],
                "browser": browser, "operating_system": osys,
                "age_band": age, "gender": gender,
                "user_type": user_type, "first_seen_date": first_seen,
                "sessions": 1, "engaged": int(engaged),
                "engagement_time_sec": engagement_sec,
                "transactions": int(completed),
                "txn_value": txn_value,
            })

            # event stream (GA4 Engagement 'events' report)
            evs = ["session_start", "page_view"]
            if engaged:
                evs.append("user_engagement")
            evs.append("screen_view")
            if started:
                evs.append("begin_transaction")
            if completed:
                evs.append("complete_transaction")
            for name in evs:
                event_rows.append({
                    "event_date": day.isoformat(), "platform": device,
                    "geo": geo, "channel": channel, "event_name": name,
                    "value": txn_value if name == "complete_transaction" else 0.0})

    sessions = pd.DataFrame(session_rows)
    events = (pd.DataFrame(event_rows)
              .groupby(["event_date", "platform", "geo", "channel", "event_name"])
              .agg(event_count=("event_name", "size"),
                   event_value=("value", "sum")).reset_index())
    return sessions, events


def _try_real_export(wh) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Attempt to read a real GA4->BigQuery export. Returns None if unavailable.

    Flattens the `events_*` wildcard in BigQuery SQL and returns two tidy,
    already-aggregated DataFrames with the SAME column contract the simulator
    emits (so the downstream GA4 reports work unchanged):
      * sessions: one row per session (user_pseudo_id + ga_session_id).
      * events:   one row per event_date + event_name.
    The real export's device/geo/traffic RECORDS are sparse here, so geo/
    device are read from the Measurement-Protocol `event_params` and the
    GA4-standard channel grouping is mapped from traffic_source; everything is
    COALESCEd to sensible defaults so a missing field never throws.
    """
    if wh.cfg.mode != "bigquery":
        return None
    import os
    prop = os.getenv("GA4_EXPORT_DATASET")  # e.g. analytics_123456789
    if not prop:
        return None
    src = f"`{wh.cfg.project_id}.{prop}.events_*`"
    try:
        sessions_sql = f"""
        WITH ev AS (
          SELECT
            PARSE_DATE('%Y%m%d', event_date) AS session_date,
            user_pseudo_id,
            CAST(COALESCE((SELECT value.int_value FROM UNNEST(event_params)
                           WHERE key='ga_session_id'), 0) AS STRING) AS gsid,
            (SELECT value.int_value FROM UNNEST(event_params)
             WHERE key='ga_session_number') AS session_number,
            (SELECT value.string_value FROM UNNEST(event_params)
             WHERE key='platform') AS plat,
            COALESCE(device.category, (SELECT value.string_value
             FROM UNNEST(event_params) WHERE key='platform')) AS dev_cat,
            COALESCE(NULLIF(geo.country, '(not set)'),
                     (SELECT value.string_value FROM UNNEST(event_params)
                      WHERE key='geo')) AS country_raw,
            device.web_info.browser AS browser_raw,
            device.operating_system AS os_raw,
            traffic_source.medium AS medium,
            traffic_source.source AS src_raw,
            (SELECT value.int_value FROM UNNEST(event_params)
             WHERE key='engagement_time_msec') AS eng_msec,
            (SELECT value.int_value FROM UNNEST(event_params)
             WHERE key='session_engaged') AS sess_engaged,
            DATE(TIMESTAMP_MICROS(user_first_touch_timestamp)) AS first_touch,
            event_name
          FROM {src}
        ),
        sess AS (
          SELECT
            session_date, user_pseudo_id, gsid,
            MIN(session_number)                           AS session_number,
            ANY_VALUE(plat)                               AS platform,
            ANY_VALUE(dev_cat)                            AS device_category,
            ANY_VALUE(country_raw)                        AS country,
            ANY_VALUE(browser_raw)                        AS browser,
            ANY_VALUE(os_raw)                             AS operating_system,
            ANY_VALUE(medium)                             AS medium,
            ANY_VALUE(src_raw)                            AS source_raw,
            SUM(IFNULL(eng_msec, 0)) / 1000.0             AS engagement_time_sec,
            MAX(IFNULL(sess_engaged, 0))                  AS sess_engaged,
            MIN(first_touch)                              AS first_touch,
            COUNTIF(event_name IN ('purchase', 'complete_transaction')) AS transactions
          FROM ev
          GROUP BY session_date, user_pseudo_id, gsid
        ),
        first_seen AS (
          SELECT user_pseudo_id,
                 MIN(COALESCE(first_touch, session_date)) AS first_seen_date
          FROM sess GROUP BY user_pseudo_id
        )
        SELECT
          s.session_date,
          COALESCE(s.platform, s.device_category, '(unknown)')      AS platform,
          COALESCE(s.device_category, '(unknown)')                  AS device_category,
          COALESCE(NULLIF(s.country, ''), '(unknown)')              AS geo,
          COALESCE(NULLIF(s.country, ''), '(unknown)')              AS country,
          CASE
            WHEN LOWER(s.medium) IN ('cpc', 'ppc', 'paid') THEN 'Paid Search'
            WHEN LOWER(s.medium) = 'organic' THEN 'Organic Search'
            WHEN LOWER(s.medium) = 'referral' THEN 'Referral'
            WHEN LOWER(s.medium) IN ('email', 'newsletter') THEN 'Email'
            WHEN LOWER(s.medium) IN ('social', 'social-network') THEN 'Social'
            WHEN s.medium IS NULL OR s.medium IN ('', '(none)') THEN 'Direct'
            ELSE 'Direct'
          END                                                       AS channel,
          COALESCE(NULLIF(s.source_raw, ''), '(direct)')            AS source,
          COALESCE(NULLIF(s.browser, ''), '(unknown)')              AS browser,
          COALESCE(NULLIF(s.operating_system, ''), '(unknown)')     AS operating_system,
          '(unknown)'                                               AS age_band,
          '(unknown)'                                               AS gender,
          CASE
            WHEN s.session_number = 1 THEN 'new'
            WHEN s.session_number IS NULL AND s.session_date = fs.first_seen_date THEN 'new'
            ELSE 'returning'
          END                                                       AS user_type,
          CAST(fs.first_seen_date AS STRING)                        AS first_seen_date,
          1                                                         AS sessions,
          CASE WHEN s.sess_engaged = 1 OR s.engagement_time_sec > 0
               THEN 1 ELSE 0 END                                    AS engaged,
          CAST(ROUND(s.engagement_time_sec) AS INT64)               AS engagement_time_sec,
          s.transactions,
          0.0                                                       AS txn_value
        FROM sess s
        JOIN first_seen fs USING (user_pseudo_id)
        """
        events_sql = f"""
        SELECT PARSE_DATE('%Y%m%d', event_date) AS event_date,
               '(unknown)' AS platform, '(unknown)' AS geo, 'Direct' AS channel,
               event_name,
               COUNT(*)   AS event_count,
               0.0        AS event_value
        FROM {src}
        GROUP BY event_date, event_name
        """
        sessions = wh.query(sessions_sql)
        events = wh.query(events_sql)
        return sessions, events
    except Exception as exc:
        print(f"[ga4] real export read failed ({exc}); using simulation")
        return None


def ingest(days: int = 120, daily_sessions: int = 300) -> None:
    wh = get_warehouse()
    real = _try_real_export(wh)
    if real is not None and not real[0].empty:
        sessions, events = real
        print(f"[ga4] loaded REAL GA4 export: {len(sessions)} session rows")
    else:
        sessions, events = _simulate(days, daily_sessions)
        print(f"[ga4] SIMULATED GA4 data: {len(sessions)} session rows "
              f"over {days} days")

    wh.load_dataframe(sessions, "raw", "ga4_sessions")
    if not events.empty:
        wh.load_dataframe(events, "raw", "ga4_events")
    print("[ga4] wrote raw.ga4_sessions"
          + (" + raw.ga4_events" if not events.empty else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--daily-sessions", type=int, default=300)
    args = ap.parse_args()
    ingest(args.days, args.daily_sessions)
