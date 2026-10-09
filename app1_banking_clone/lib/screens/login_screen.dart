import 'package:flutter/material.dart';

import '../analytics.dart';
import '../store.dart';
import '../theme.dart';
import 'main_scaffold.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final name = AppScope.of(context).customerName;
    return Scaffold(
      backgroundColor: Colors.white,
      body: Column(
        children: [
          // HSBC red header band with hexagon + wordmark (brand lockup)
          Container(
            width: double.infinity,
            color: hsbcRed,
            padding: const EdgeInsets.fromLTRB(20, 60, 20, 24),
            child: SafeArea(
              bottom: false,
              child: Row(
                children: [
                  Container(
                    color: Colors.white,
                    padding: const EdgeInsets.all(4),
                    child: const HsbcLogo(size: 30),
                  ),
                  const SizedBox(width: 12),
                  const Text('Lumen Bank',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 26,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1)),
                ],
              ),
            ),
          ),
          Expanded(
            child: Center(
              child: SingleChildScrollView(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 400),
                  child: Padding(
                    padding: const EdgeInsets.all(28),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text('Welcome back, ${name.split(' ').first}',
                            style: const TextStyle(
                                fontSize: 22, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 4),
                        const Text('Log on to Mobile Banking',
                            style: TextStyle(color: hsbcGrey)),
                        const SizedBox(height: 28),
                        _field('Username', Icons.person_outline),
                        const SizedBox(height: 14),
                        _field('Password', Icons.lock_outline, obscure: true),
                        const SizedBox(height: 24),
                        _logOnButton(context, 'Log on', 'password'),
                        const SizedBox(height: 14),
                        Center(
                          child: TextButton.icon(
                            onPressed: () => _enter(context, 'biometric'),
                            icon: const Icon(Icons.fingerprint, color: hsbcRed),
                            label: const Text('Log on with biometrics',
                                style: TextStyle(color: hsbcRed)),
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Center(
                          child: Text('Prototype — demo only, not a real bank',
                              style: TextStyle(color: hsbcGrey, fontSize: 12)),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _logOnButton(BuildContext context, String label, String method) =>
      SizedBox(
        height: 52,
        child: FilledButton(
          style: FilledButton.styleFrom(
              backgroundColor: hsbcRed,
              shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.all(Radius.circular(4)))),
          onPressed: () => _enter(context, method),
          child: Text(label,
              style:
                  const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        ),
      );

  Future<void> _enter(BuildContext context, String method) async {
    await Analytics.login(method);
    if (context.mounted) {
      Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const MainScaffold()));
    }
  }

  Widget _field(String label, IconData icon, {bool obscure = false}) =>
      TextField(
        obscureText: obscure,
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: Icon(icon),
          border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(4),
              borderSide: const BorderSide(color: Color(0xFFCCCCCC))),
        ),
      );
}
