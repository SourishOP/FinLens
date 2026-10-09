import 'package:flutter/material.dart';

import '../analytics.dart';
import '../store.dart';
import '../theme.dart';

/// Move money between the customer's own accounts — a real, working transfer
/// that validates funds and updates balances in the store.
class TransactionScreen extends StatefulWidget {
  const TransactionScreen({super.key});
  @override
  State<TransactionScreen> createState() => _TransactionScreenState();
}

class _TransactionScreenState extends State<TransactionScreen> {
  String? _fromId, _toId;
  final _amount = TextEditingController();
  final _ref = TextEditingController(text: 'Transfer');
  String? _error;
  bool _done = false;
  double _sent = 0;

  @override
  void initState() {
    super.initState();
    Analytics.screenView('move_money');
    Analytics.beginTransaction('transfer');
  }

  @override
  Widget build(BuildContext context) {
    final store = AppScope.of(context);
    _fromId ??= store.accounts.first.id;
    _toId ??= store.accounts[1].id;

    return Scaffold(
      backgroundColor: bgGrey,
      appBar: AppBar(
        backgroundColor: hsbcRed,
        foregroundColor: Colors.white,
        title: const Text('Move money'),
      ),
      body: _done ? _success(store) : _form(store),
    );
  }

  Widget _form(AppState store) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _accountPicker(store, 'From', _fromId!, (v) => setState(() => _fromId = v)),
          const SizedBox(height: 12),
          _accountPicker(store, 'To', _toId!, (v) => setState(() => _toId = v)),
          const SizedBox(height: 16),
          Container(
            color: Colors.white,
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _amount,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
              decoration: const InputDecoration(
                  prefixText: '£ ',
                  hintText: '0.00',
                  border: InputBorder.none),
              onChanged: (_) => setState(() => _error = null),
            ),
          ),
          const SizedBox(height: 12),
          Container(
            color: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: TextField(
              controller: _ref,
              decoration: const InputDecoration(
                  labelText: 'Reference', border: InputBorder.none),
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, style: const TextStyle(color: hsbcRed)),
            ),
          const SizedBox(height: 24),
          SizedBox(
            height: 52,
            child: FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: hsbcRed,
                  shape: const RoundedRectangleBorder(
                      borderRadius: BorderRadius.all(Radius.circular(4)))),
              onPressed: () => _submit(store),
              child: const Text('Continue',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),
          ),
        ],
      );

  Widget _accountPicker(AppState store, String label, String value,
          ValueChanged<String?> onChanged) =>
      Container(
        color: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: DropdownButtonFormField<String>(
          initialValue: value,
          isExpanded: true,
          decoration: InputDecoration(labelText: label, border: InputBorder.none),
          items: store.accounts
              .map((a) => DropdownMenuItem(
                  value: a.id,
                  child: Text('${a.name} · ${Fmt.money(a.balance)}',
                      overflow: TextOverflow.ellipsis)))
              .toList(),
          onChanged: onChanged,
        ),
      );

  void _submit(AppState store) {
    final amt = double.tryParse(_amount.text) ?? 0;
    final err = store.transferBetweenOwn(_fromId!, _toId!, amt,
        reference: _ref.text);
    if (err != null) {
      setState(() => _error = err);
      return;
    }
    setState(() {
      _done = true;
      _sent = amt;
    });
  }

  Widget _success(AppState store) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircleAvatar(
                  radius: 40,
                  backgroundColor: Color(0xFF1C8A5B),
                  child: Icon(Icons.check, color: Colors.white, size: 44)),
              const SizedBox(height: 18),
              Text('${Fmt.money(_sent)} transferred',
                  style: const TextStyle(
                      fontSize: 20, fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text('New balance: ${Fmt.money(store.account(_fromId!).balance)}',
                  style: const TextStyle(color: hsbcGrey)),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                      backgroundColor: hsbcRed,
                      shape: const RoundedRectangleBorder(
                          borderRadius: BorderRadius.all(Radius.circular(4)))),
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Done'),
                ),
              ),
            ],
          ),
        ),
      );
}
