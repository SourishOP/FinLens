import 'package:flutter/material.dart';

import '../analytics.dart';
import '../theme.dart';
import 'home_screen.dart';
import 'payments_screen.dart';
import 'payees_screen.dart';
import 'profile_screen.dart';

// HSBC-style app shell: red top bar + bottom navigation.
class MainScaffold extends StatefulWidget {
  const MainScaffold({super.key});
  @override
  State<MainScaffold> createState() => _MainScaffoldState();
}

class _MainScaffoldState extends State<MainScaffold> {
  int _tab = 0;
  static const _labels = ['Home', 'Move money', 'Payees', 'Profile'];

  @override
  Widget build(BuildContext context) {
    final screens = [
      const HomeScreen(),
      const PaymentsScreen(),
      const PayeesScreen(),
      const ProfileScreen(),
    ];
    return Scaffold(
      backgroundColor: bgGrey,
      appBar: AppBar(
        backgroundColor: hsbcRed,
        elevation: 0,
        titleSpacing: 16,
        title: Row(
          children: [
            Container(
              color: Colors.white,
              padding: const EdgeInsets.all(3),
              child: const HsbcLogo(size: 22),
            ),
            const SizedBox(width: 10),
            const Text('Lumen Bank',
                style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1)),
          ],
        ),
        actions: const [
          Icon(Icons.chat_bubble_outline, color: Colors.white),
          SizedBox(width: 16),
          Icon(Icons.logout, color: Colors.white),
          SizedBox(width: 16),
        ],
      ),
      body: SafeArea(child: screens[_tab]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) {
          setState(() => _tab = i);
          Analytics.screenView(_labels[i].toLowerCase().replaceAll(' ', '_'));
        },
        indicatorColor: hsbcRed.withValues(alpha: 0.12),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home, color: hsbcRed), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.swap_horiz_outlined), selectedIcon: Icon(Icons.swap_horiz, color: hsbcRed), label: 'Move money'),
          NavigationDestination(icon: Icon(Icons.people_outline), selectedIcon: Icon(Icons.people, color: hsbcRed), label: 'Payees'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person, color: hsbcRed), label: 'Profile'),
        ],
      ),
    );
  }
}
