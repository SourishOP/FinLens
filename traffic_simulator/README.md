# Traffic simulator (GA4 Measurement Protocol)

Generates realistic GA4 events for App 1 since the prototype has no real users.
Honest framing: a **traffic-simulation harness** firing genuine GA4 events so the
full GA4 → BigQuery → dashboard pipeline can be validated on data that mirrors
real adoption patterns.

## Run

```powershell
# Dry run (no creds needed) — plans sessions + prints a sample payload:
python -m traffic_simulator.ga4_measurement_protocol --sessions 200 --dry-run

# Validate against GA4's debug endpoint (needs creds, sends to validation only):
python -m traffic_simulator.ga4_measurement_protocol --sessions 50 --validate

# Live — sends real events to your GA4 property:
python -m traffic_simulator.ga4_measurement_protocol --sessions 500
```

## Setup (.env)

```
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
GA4_API_SECRET=...        # GA4 Admin -> Data Streams -> Measurement Protocol API secrets
```

## Realism built in

- device mix ~60% mobile / 40% web
- geographies: Hong Kong / UK / UAE / Singapore (weighted)
- funnel: app_open → login → accounts → begin_transaction → complete_transaction
- ~60% of sessions complete a transaction (0.85 start × 0.70 complete)
- evening-peak time weighting

Event names match App 1's Flutter instrumentation, so real and simulated traffic
share one schema in GA4 and BigQuery.
