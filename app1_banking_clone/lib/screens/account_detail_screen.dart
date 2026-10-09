import 'package:flutter/material.dart';

import '../analytics.dart';
import '../store.dart';
import '../theme.dart';

/// Account detail / statement — balance header + full transaction list with
/// running balance, like the HSBC app's account view.
class AccountDetailScreen extends StatefulWidget {
  final String accountId;
  const AccountDetailScreen({super.key, required this.accountId});
  @override
  State<AccountDetailScreen> createState() => _AccountDetailScreenState();
}

class _AccountDetailScreenState extends State<AccountDetailScreen> {
  @override
  void initState() {
    super.initState();
    Analytics.screenView('account_detail');
  }

  @override
  Widget build(BuildContext context) {
    final store = AppScope.of(context);
    return AnimatedBuilder(
      animation: store,
      builder: (context, _) {
        final a = store.account(widget.accountId);
        final txns = store.txnsFor(a.id);
        return Scaffold(
          backgroundColor: bgGrey,
          appBar: AppBar(
            backgroundColor: hsbcRed,
            foregroundColor: Colors.white,
            title: Text(a.name),
            actions: [
              IconButton(
                  onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Statement downloaded (demo)'))),
                  icon: const Icon(Icons.download)),
            ],
          ),
          body: ListView(
            children: [
              Container(
                color: hsbcRed,
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(a.number,
                        style: const TextStyle(
                            color: Colors.white70, letterSpacing: 1)),
                    const SizedBox(height: 4),
                    Text(Fmt.money(a.balance),
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 32,
                            fontWeight: FontWeight.w700)),
                    Text('Available ${Fmt.money(a.available)}',
                        style: const TextStyle(color: Colors.white70)),
                  ],
                ),
              ),
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Text('Transactions',
                    style: TextStyle(
                        fontWeight: FontWeight.w700, color: hsbcGrey)),
              ),
              Container(
                color: Colors.white,
                child: Column(
                  children: [
                    for (final t in txns) _row(t),
                    if (txns.isEmpty)
                      const Padding(
                          padding: EdgeInsets.all(20),
                          child: Text('No transactions',
                              style: TextStyle(color: hsbcGrey))),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _row(Txn t) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(t.title,
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  Text(
                      '${t.category} · ${t.date.day}/${t.date.month}/${t.date.year}',
                      style: const TextStyle(color: hsbcGrey, fontSize: 12)),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(Fmt.money(t.amount, sign: t.amount > 0),
                    style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: t.amount >= 0
                            ? const Color(0xFF1C8A5B)
                            : hsbcDark)),
                Text('Bal ${Fmt.money(t.balanceAfter)}',
                    style: const TextStyle(color: hsbcGrey, fontSize: 11)),
              ],
            ),
          ],
        ),
      );
}
