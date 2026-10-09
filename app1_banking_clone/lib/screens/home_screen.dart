import 'package:flutter/material.dart';

import '../analytics.dart';
import '../store.dart';
import '../theme.dart';
import 'account_detail_screen.dart';
import 'transaction_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    Analytics.screenView('home');
  }

  @override
  Widget build(BuildContext context) {
    final store = AppScope.of(context);
    return AnimatedBuilder(
      animation: store,
      builder: (context, _) {
        return ListView(
          padding: const EdgeInsets.only(bottom: 24),
          children: [
            _greeting(store),
            const SizedBox(height: 8),
            _sectionLabel('Your accounts'),
            ...store.accounts.map((a) => _accountTile(context, a)),
            const SizedBox(height: 8),
            _quickLinks(context),
            const SizedBox(height: 8),
            _sectionLabel('Recent transactions'),
            _recent(store),
          ],
        );
      },
    );
  }

  Widget _greeting(AppState store) => Container(
        color: hsbcRed,
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Good day,',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.85))),
            Text(store.customerName,
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.w700)),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8)),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Total of your money',
                      style: TextStyle(color: Colors.white70, fontSize: 13)),
                  Text(Fmt.money(store.totalBalance),
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _sectionLabel(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
        child: Text(t,
            style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: hsbcGrey,
                letterSpacing: 0.3)),
      );

  Widget _accountTile(BuildContext context, Account a) => Container(
        margin: const EdgeInsets.fromLTRB(12, 0, 12, 1),
        color: Colors.white,
        child: InkWell(
          onTap: () => Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => AccountDetailScreen(accountId: a.id))),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(width: 4, height: 42, color: a.color),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(a.name,
                          style: const TextStyle(fontWeight: FontWeight.w600)),
                      Text(
                          '${a.sortCode.isNotEmpty ? "${a.sortCode}  " : ""}${a.number}',
                          style: const TextStyle(
                              color: hsbcGrey, fontSize: 12)),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(Fmt.money(a.balance),
                        style: TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 16,
                            color: a.balance < 0 ? hsbcRed : hsbcDark)),
                    Text('Available ${Fmt.money(a.available)}',
                        style:
                            const TextStyle(color: hsbcGrey, fontSize: 11)),
                  ],
                ),
                const Icon(Icons.chevron_right, color: hsbcGrey),
              ],
            ),
          ),
        ),
      );

  Widget _quickLinks(BuildContext context) {
    final links = [
      ('Move money', Icons.swap_horiz, 0),
      ('Pay a bill', Icons.receipt_long, 1),
      ('Send to payee', Icons.send, 2),
      ('Statements', Icons.description_outlined, 3),
    ];
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          for (final (label, icon, _) in links)
            InkWell(
              onTap: () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => const TransactionScreen())),
              child: SizedBox(
                width: 72,
                child: Column(
                  children: [
                    CircleAvatar(
                        radius: 24,
                        backgroundColor: hsbcRed.withValues(alpha: 0.1),
                        child: Icon(icon, color: hsbcRed, size: 22)),
                    const SizedBox(height: 6),
                    Text(label,
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 11)),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _recent(AppState store) {
    final txns = store.recentAll;
    return Container(
      color: Colors.white,
      child: Column(
        children: [
          for (final t in txns) _txnRow(t),
          if (txns.isEmpty)
            const Padding(
                padding: EdgeInsets.all(20),
                child: Text('No transactions yet',
                    style: TextStyle(color: hsbcGrey))),
        ],
      ),
    );
  }

  Widget _txnRow(Txn t) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            CircleAvatar(
                radius: 20,
                backgroundColor: bgGrey,
                child: Icon(
                    t.amount >= 0 ? Icons.south_west : Icons.north_east,
                    size: 18,
                    color: t.amount >= 0 ? const Color(0xFF1C8A5B) : hsbcDark)),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(t.title,
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  Text(t.category,
                      style: const TextStyle(color: hsbcGrey, fontSize: 12)),
                ],
              ),
            ),
            Text(Fmt.money(t.amount, sign: t.amount > 0),
                style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: t.amount >= 0 ? const Color(0xFF1C8A5B) : hsbcDark)),
          ],
        ),
      );
}
