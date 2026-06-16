import 'package:flutter/material.dart';

import 'projects_screen.dart';
import 'detection_screen.dart';
import 'models_screen.dart';
import 'settings_screen.dart';

/// Root navigation shell — bottom nav across the four primary areas.
/// Replaces the legacy button-menu HomeScreen.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;
  final _detectKey = GlobalKey<DetectionScreenState>();

  static const _destinations = [
    NavigationDestination(
      icon: Icon(Icons.folder_outlined),
      selectedIcon: Icon(Icons.folder),
      label: 'Projects',
    ),
    NavigationDestination(
      icon: Icon(Icons.camera_alt_outlined),
      selectedIcon: Icon(Icons.camera_alt),
      label: 'Detect',
    ),
    NavigationDestination(
      icon: Icon(Icons.dataset_outlined),
      selectedIcon: Icon(Icons.dataset),
      label: 'Models',
    ),
    NavigationDestination(
      icon: Icon(Icons.settings_outlined),
      selectedIcon: Icon(Icons.settings),
      label: 'Settings',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: [
          const ProjectsScreen(),
          DetectionScreen(key: _detectKey),
          const ModelsScreen(),
          const SettingsScreen(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        destinations: _destinations,
        onDestinationSelected: (i) {
          final leavingDetect = _index == 1 && i != 1;
          setState(() => _index = i);
          // IndexedStack keeps Detect alive; pause its camera + inference when
          // it's not visible (otherwise it blocks the UI thread app-wide), and
          // resume / refresh the active model when returning to it.
          if (i == 1) {
            _detectKey.currentState?.resumeDetection();
          } else if (leavingDetect) {
            _detectKey.currentState?.pauseDetection();
          }
        },
      ),
    );
  }
}
