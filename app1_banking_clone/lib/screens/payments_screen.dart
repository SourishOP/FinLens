import 'package:flutter/material.dart';

import '../analytics.dart';
import '../store.dart';
import '../theme.dart';
import 'transaction_screen.dart';

/// "Move money" hub — transfer between accounts, pay a payee, pay a bill.
class PaymentsScreen extends StatefulWidget {
  const PaymentsScreen({super.key});
  @override
  State<PaymentsScreen> createState() => _PaymentsScreenState();
}

class _PaymentsScreenState extends State<PaymentsScreen> {
  @override
  void initState() {
    super.initState();
    Analytics.screenView('move_money');
  }

  @override
  Widget build(BuildContext context) {
    final store = AppScope.of(context);
    return ListView(
      children: [
        _header('Move money'),
        _tile(context, 'Transfer between my accounts', Icons.swap_horiz,
            () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => const TransactionScreen()))),
        _tile(context, 'Send to a payee', Icons.send,
            () => _payeeSheet(context, store)),
        _tile(context, 'Pay a bill', Icons.receipt_long,
            () => _billSheet(context, store)),
        _tile(context, 'Global Money Transfer', Icons.public,
            () => ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('International transfers — demo')))),
      ],
    );
  }

  Widget _header(String t) => Container(
        color: hsbcRed,
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 18),
        child: Text(t,
            style: const TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.w700)),
      );

  Widget _tile(BuildContext c, String label, IconData icon, VoidCallback onTap) =>
      Container(
        color: Colors.white,
        margin: const EdgeInsets.only(bottom: 1),
        child: ListTile(
          leading: CircleAvatar(
              backgroundColor: hsbcRed.withValues(alpha: 0.1),
              child: Icon(icon, color: hsbcRed)),
          title: Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
          trailing: const Icon(Icons.chevron_right, color: hsbcGrey),
          onTap: onTap,
        ),
      );

  void _payeeSheet(BuildContext context, AppState store) {
    Analytics.beginTransaction('transfer');
    _amountSheet(context, store, title: 'Send to a payee',
        options: store.payees.map((p) => p.name).toList(),
        onPay: (fromId, who, amt) {
          final payee = store.payees.firstWhere((p) => p.name == who);
          return store.payPayee(fromId, payee, amt);
        });
  }

  void _billSheet(BuildContext context, AppState store) {
    Analytics.beginTransaction('bill_payment');
    _amountSheet(context, store, title: 'Pay a bill',
        options: store.billers,
        onPay: (fromId, biller, amt) => store.payBill(fromId, biller, amt));
  }

  void _amountSheet(BuildContext context, AppState store,
      {required String title,
      required List<String> options,
      required String? Function(String fromId, String target, double amt) onPay}) {
    String fromId = store.accounts.first.id;
    String target = options.first;
    final amount = TextEditingController();
    String? error;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => Padding(
          padding: EdgeInsets.only(
              left: 20,
              right: 20,
              top: 20,
              bottom: MediaQuery.of(ctx).viewInsets.bottom + 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(title,
                  style: const TextStyle(
                      fontSize: 18, fontWeight: FontWeight.w700)),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: fromId,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'From account'),
                items: store.accounts
                    .map((a) => DropdownMenuItem(
                        value: a.id,
                        child: Text('${a.name} · ${Fmt.money(a.balance)}',
                            overflow: TextOverflow.ellipsis)))
                    .toList(),
                onChanged: (v) => setSheet(() => fromId = v!),
              ),
              DropdownButtonFormField<String>(
                initialValue: target,
                isExpanded: true,
                decoration: Text(title).data!.contains('bill')
                    ? const InputDecoration(labelText: 'Biller')
                    : const InputDecoration(labelText: 'Payee'),
                items: options
                    .map((o) => DropdownMenuItem(value: o, child: Text(o)))
                    .toList(),
                onChanged: (v) => setSheet(() => target = v!),
              ),
              TextField(
                controller: amount,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                    labelText: 'Amount', prefixText: '£ '),
              ),
              if (error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Text(error!, style: const TextStyle(color: hsbcRed)),
                ),
              const SizedBox(height: 18),
              SizedBox(
                height: 50,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                      backgroundColor: hsbcRed,
                      shape: const RoundedRectangleBorder(
                          borderRadius: BorderRadius.all(Radius.circular(4)))),
                  onPressed: () {
                    final amt = double.tryParse(amount.text) ?? 0;
                    final err = onPay(fromId, target, amt);
                    if (err != null) {
                      setSheet(() => error = err);
                      return;
                    }
                    Navigator.of(ctx).pop();
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                        content: Text(
                            '${Fmt.money(amt)} paid to $target. New balance ${Fmt.money(store.account(fromId).balance)}')));
                  },
                  child: const Text('Pay now'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
