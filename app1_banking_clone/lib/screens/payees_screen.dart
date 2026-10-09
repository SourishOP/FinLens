import 'package:flutter/material.dart';

import '../analytics.dart';
import '../store.dart';
import '../theme.dart';

/// Manage payees — list, add, delete. Mirrors the HSBC app's payee management.
class PayeesScreen extends StatefulWidget {
  const PayeesScreen({super.key});
  @override
  State<PayeesScreen> createState() => _PayeesScreenState();
}

class _PayeesScreenState extends State<PayeesScreen> {
  @override
  void initState() {
    super.initState();
    Analytics.screenView('payees');
  }

  @override
  Widget build(BuildContext context) {
    final store = AppScope.of(context);
    return AnimatedBuilder(
      animation: store,
      builder: (context, _) => Scaffold(
        backgroundColor: bgGrey,
        body: ListView(
          children: [
            Container(
              color: hsbcRed,
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(20, 18, 20, 18),
              child: const Text('Your payees',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w700)),
            ),
            for (final p in store.payees)
              Container(
                color: Colors.white,
                margin: const EdgeInsets.only(bottom: 1),
                child: ListTile(
                  leading: CircleAvatar(
                      backgroundColor: hsbcRed.withValues(alpha: 0.1),
                      child: Text(p.name[0],
                          style: const TextStyle(
                              color: hsbcRed, fontWeight: FontWeight.w700))),
                  title: Text(p.name,
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text('${p.sortCode}  ${p.accountNumber}'),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline, color: hsbcGrey),
                    onPressed: () => store.removePayee(p.id),
                  ),
                ),
              ),
          ],
        ),
        floatingActionButton: FloatingActionButton.extended(
          backgroundColor: hsbcRed,
          icon: const Icon(Icons.add),
          label: const Text('Add payee'),
          onPressed: () => _addPayee(context, store),
        ),
      ),
    );
  }

  void _addPayee(BuildContext context, AppState store) {
    final name = TextEditingController();
    final sort = TextEditingController();
    final acc = TextEditingController();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Add a payee',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            TextField(controller: name,
                decoration: const InputDecoration(labelText: 'Name')),
            TextField(controller: sort,
                decoration: const InputDecoration(labelText: 'Sort code')),
            TextField(controller: acc,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Account number')),
            const SizedBox(height: 18),
            SizedBox(
              height: 50,
              child: FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: hsbcRed,
                    shape: const RoundedRectangleBorder(
                        borderRadius: BorderRadius.all(Radius.circular(4)))),
                onPressed: () {
                  if (name.text.trim().isEmpty) return;
                  store.addPayee(name.text.trim(),
                      sort.text.trim().isEmpty ? '00-00-00' : sort.text.trim(),
                      acc.text.trim());
                  Navigator.of(ctx).pop();
                },
                child: const Text('Save payee'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
