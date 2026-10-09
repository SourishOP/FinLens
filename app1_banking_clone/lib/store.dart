// Central app state — makes the banking app functional (not a static mockup).
//
// Holds accounts, transactions and payees. Transfers and payments actually move
// money: balances update and a transaction is appended, so the UI reflects real
// state changes. Exposed to the widget tree via an InheritedNotifier (no extra
// package needed).
import 'package:flutter/material.dart';

import 'analytics.dart';

class Account {
  final String id;
  final String name;
  final String number; // masked
  final String sortCode;
  double balance;
  double available;
  final Color color;
  Account({
    required this.id,
    required this.name,
    required this.number,
    required this.sortCode,
    required this.balance,
    required this.available,
    required this.color,
  });
}

class Txn {
  final String title;
  final String category;
  final double amount; // negative = money out
  final DateTime date;
  final double balanceAfter;
  Txn(this.title, this.category, this.amount, this.date, this.balanceAfter);
}

class Payee {
  final String id;
  final String name;
  final String sortCode;
  final String accountNumber;
  Payee(this.id, this.name, this.sortCode, this.accountNumber);
}

class AppState extends ChangeNotifier {
  // The logged-in customer.
  String customerName = 'Sourish Das';

  final List<Account> accounts = [
    Account(
        id: 'cur',
        name: 'Advance Current Account',
        number: '•••• 4821',
        sortCode: '40-12-07',
        balance: 3240.55,
        available: 3740.55, // includes a small arranged overdraft
        color: const Color(0xFFDB0011)),
    Account(
        id: 'sav',
        name: 'Online Bonus Saver',
        number: '•••• 9930',
        sortCode: '40-12-07',
        balance: 18500.00,
        available: 18500.00,
        color: const Color(0xFF1C8A5B)),
    Account(
        id: 'cc',
        name: 'Credit Card',
        number: '•••• 1127',
        sortCode: '',
        balance: -642.18,
        available: 4357.82, // credit limit minus balance
        color: const Color(0xFF11182C)),
  ];

  final Map<String, List<Txn>> _txns = {};

  final List<Payee> payees = [
    Payee('p1', 'Alex Thompson', '20-00-00', '•••• 5567'),
    Payee('p2', 'Priya Nair', '09-01-28', '•••• 8842'),
    Payee('p3', 'Landlord — Flat 4B', '30-99-50', '•••• 1200'),
  ];

  final List<String> billers = [
    'British Gas', 'Thames Water', 'Vodafone', 'Council Tax', 'Netflix', 'TV Licence'
  ];

  AppState() {
    _seedHistory();
  }

  Account account(String id) => accounts.firstWhere((a) => a.id == id);

  List<Txn> txnsFor(String accountId) =>
      List.unmodifiable(_txns[accountId] ?? const []);

  List<Txn> get recentAll {
    final all = <Txn>[];
    _txns.forEach((_, list) => all.addAll(list));
    all.sort((a, b) => b.date.compareTo(a.date));
    return all.take(8).toList();
  }

  double get totalBalance =>
      accounts.where((a) => a.id != 'cc').fold(0.0, (s, a) => s + a.balance);

  void _seedHistory() {
    final now = DateTime.now();
    final cur = account('cur');
    final seed = <Txn>[
      Txn('Salary — Acme Ltd', 'Income', 4200.00, now.subtract(const Duration(days: 2)), 0),
      Txn('Tesco', 'Groceries', -54.30, now.subtract(const Duration(days: 3)), 0),
      Txn('Spotify', 'Subscription', -9.99, now.subtract(const Duration(days: 4)), 0),
      Txn('TfL travel', 'Transport', -28.40, now.subtract(const Duration(days: 5)), 0),
      Txn('Shell', 'Fuel', -61.75, now.subtract(const Duration(days: 6)), 0),
    ];
    // compute running balances backward from current balance
    double running = cur.balance;
    final withBal = <Txn>[];
    for (final t in seed) {
      withBal.add(Txn(t.title, t.category, t.amount, t.date, running));
      running -= t.amount;
    }
    _txns['cur'] = withBal;
    _txns['sav'] = [
      Txn('Monthly saving', 'Transfer in', 500.00,
          now.subtract(const Duration(days: 1)), account('sav').balance),
    ];
    _txns['cc'] = [
      Txn('Amazon', 'Shopping', -32.49,
          now.subtract(const Duration(days: 1)), account('cc').balance),
    ];
  }

  String? _validate(Account from, double amount) {
    if (amount <= 0) return 'Enter an amount greater than zero.';
    if (amount > from.available) {
      return 'Insufficient funds. Available: £${from.available.toStringAsFixed(2)}.';
    }
    return null;
  }

  /// Move money between the customer's own accounts. Returns null on success,
  /// or an error message.
  String? transferBetweenOwn(String fromId, String toId, double amount,
      {String reference = 'Transfer'}) {
    if (fromId == toId) return 'Choose two different accounts.';
    final from = account(fromId);
    final to = account(toId);
    final err = _validate(from, amount);
    if (err != null) return err;

    _apply(from, -amount, 'To ${to.name}', 'Transfer');
    _apply(to, amount, 'From ${from.name}', 'Transfer');
    Analytics.completeTransaction('transfer', amount);
    notifyListeners();
    return null;
  }

  /// Pay a saved payee from an account.
  String? payPayee(String fromId, Payee payee, double amount,
      {String reference = ''}) {
    final from = account(fromId);
    final err = _validate(from, amount);
    if (err != null) return err;
    _apply(from, -amount, payee.name, 'Payment');
    Analytics.completeTransaction('transfer', amount);
    notifyListeners();
    return null;
  }

  /// Pay a bill to a biller.
  String? payBill(String fromId, String biller, double amount) {
    final from = account(fromId);
    final err = _validate(from, amount);
    if (err != null) return err;
    _apply(from, -amount, biller, 'Bill payment');
    Analytics.completeTransaction('bill_payment', amount);
    notifyListeners();
    return null;
  }

  void addPayee(String name, String sortCode, String accountNumber) {
    payees.add(Payee('p${payees.length + 1}', name, sortCode,
        '•••• ${accountNumber.length >= 4 ? accountNumber.substring(accountNumber.length - 4) : accountNumber}'));
    notifyListeners();
  }

  void removePayee(String id) {
    payees.removeWhere((p) => p.id == id);
    notifyListeners();
  }

  void _apply(Account acc, double delta, String title, String category) {
    acc.balance += delta;
    acc.available += delta;
    final list = _txns.putIfAbsent(acc.id, () => []);
    list.insert(0, Txn(title, category, delta, DateTime.now(), acc.balance));
  }
}

/// Makes AppState available to the whole widget tree and rebuilds on change.
class AppScope extends InheritedNotifier<AppState> {
  const AppScope({super.key, required AppState state, required super.child})
      : super(notifier: state);

  static AppState of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope not found in widget tree');
    return scope!.notifier!;
  }
}
