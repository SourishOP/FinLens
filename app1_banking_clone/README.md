# App 1 — HSBC-style banking prototype (GA4 data source)

A Flutter app that runs on **web + Android + iOS from one codebase**. Its only job
is to emit **real GA4 events we legitimately own** (login, screen views, a
transaction funnel) so App 2 can demonstrate GA4 → BigQuery digital-adoption
analytics. It is a prototype, never connected to HSBC's real systems.

## Status

Source is complete and ready to run, but **Flutter SDK is not installed on this
machine**, so it hasn't been built here. The Python **traffic simulator**
(`traffic_simulator/`) produces the same GA4 events over HTTP and is verified
working now — use that to populate GA4 immediately, and build this app when you
have Flutter.

## Event schema (matches the traffic simulator)

`app_open` → `login` → `screen_view(accounts)` → `begin_transaction` →
`complete_transaction` (with `txn_type`, `value`, `currency`, `platform`, `geo`).

## Setup (when you have Flutter)

```powershell
# 1. Install Flutter SDK: https://docs.flutter.dev/get-started/install/windows
flutter --version

# 2. Create a Firebase project + GA4, then wire it up:
dart pub global activate flutterfire_cli
flutterfire configure        # generates lib/firebase_options.dart

# 3. From app1_banking_clone/:
flutter pub get
flutter run -d chrome        # web
# flutter run -d <device>    # Android/iOS (iOS build needs macOS)
```

Clicking through the app logs real GA4 events. Link GA4 → BigQuery (Task 9) and
they flow into App 2's dashboards.

## Files

- `lib/main.dart` — app entry, Firebase init, HSBC theme, analytics observer.
- `lib/analytics.dart` — GA4 helper (event names shared with the simulator).
- `lib/screens/` — login → accounts → transaction (the instrumented funnel).
- `pubspec.yaml` — firebase_core + firebase_analytics.
