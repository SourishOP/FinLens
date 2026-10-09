// Central GA4 analytics helper.
//
// Wraps FirebaseAnalytics so every screen logs consistent events. These events
// are what flow to GA4 and then (via the GA4->BigQuery export) into App 2's
// dashboards. The event names mirror the traffic simulator so real and
// simulated data share one schema.
import 'package:firebase_analytics/firebase_analytics.dart';

class Analytics {
  static final FirebaseAnalytics _ga = FirebaseAnalytics.instance;

  static FirebaseAnalyticsObserver observer() =>
      FirebaseAnalyticsObserver(analytics: _ga);

  static Future<void> appOpen(String platform, String geo) =>
      _ga.logEvent(name: 'app_open', parameters: {
        'platform': platform,
        'geo': geo,
      });

  static Future<void> login(String method) =>
      _ga.logLogin(loginMethod: method);

  static Future<void> screenView(String screen) =>
      _ga.logScreenView(screenName: screen);

  static Future<void> beginTransaction(String txnType) =>
      _ga.logEvent(name: 'begin_transaction', parameters: {
        'txn_type': txnType,
      });

  static Future<void> completeTransaction(String txnType, double value) =>
      _ga.logEvent(name: 'complete_transaction', parameters: {
        'txn_type': txnType,
        'value': value,
        'currency': 'USD',
      });
}
