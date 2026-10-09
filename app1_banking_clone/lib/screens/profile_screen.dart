import 'package:flutter/material.dart';

import '../analytics.dart';
import '../store.dart';
import '../theme.dart';
import 'login_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});
  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  @override
  void initState() {
    super.initState();
    Analytics.screenView('profile');
  }

  @override
  Widget build(BuildContext context) {
    final store = AppScope.of(context);
    final name = store.customerName;
    final items = [
      ('Personal details', Icons.person_outline),
      ('Security & devices', Icons.lock_outline),
      ('Statements & documents', Icons.description_outlined),
      ('Manage alerts', Icons.notifications_none),
      ('Help & support', Icons.help_outline),
    ];
    return ListView(
      children: [
        Container(
          color: hsbcRed,
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
          child: Column(
            children: [
              CircleAvatar(
                  radius: 36,
                  backgroundColor: Colors.white,
                  child: Text(
                      name.split(' ').map((e) => e[0]).take(2).join(),
                      style: const TextStyle(
                          color: hsbcRed,
                          fontSize: 26,
                          fontWeight: FontWeight.w700))),
              const SizedBox(height: 10),
              Text(name,
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w700)),
              const Text('Advance customer since 2019',
                  style: TextStyle(color: Colors.white70, fontSize: 13)),
            ],
          ),
        ),
        const SizedBox(height: 8),
        for (final (label, icon) in items)
          Container(
            color: Colors.white,
            margin: const EdgeInsets.only(bottom: 1),
            child: ListTile(
              leading: Icon(icon, color: hsbcDark),
              title: Text(label),
              trailing: const Icon(Icons.chevron_right, color: hsbcGrey),
              onTap: () {},
            ),
          ),
        const SizedBox(height: 16),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
                foregroundColor: hsbcRed,
                side: const BorderSide(color: hsbcRed),
                minimumSize: const Size.fromHeight(48)),
            icon: const Icon(Icons.logout),
            label: const Text('Log off'),
            onPressed: () => Navigator.of(context).pushAndRemoveUntil(
                MaterialPageRoute(builder: (_) => const LoginScreen()),
                (r) => false),
          ),
        ),
      ],
    );
  }
}
