import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../providers/auth_provider.dart';
import '../utils/api_config.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _autoDownloadModels = false;
  bool _highQualityCamera = true;
  double _confidenceThreshold = 0.5;
  String _selectedFormat = 'tflite';

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _autoDownloadModels = prefs.getBool('autoDownloadModels') ?? false;
      _highQualityCamera = prefs.getBool('highQualityCamera') ?? true;
      _confidenceThreshold = prefs.getDouble('confidenceThreshold') ?? 0.5;
      _selectedFormat = prefs.getString('modelFormat') ?? 'tflite';
    });
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('autoDownloadModels', _autoDownloadModels);
    await prefs.setBool('highQualityCamera', _highQualityCamera);
    await prefs.setDouble('confidenceThreshold', _confidenceThreshold);
    await prefs.setString('modelFormat', _selectedFormat);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Settings saved'),
          backgroundColor: Colors.green,
        ),
      );
    }
  }

  Future<void> _clearCache() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Cache'),
        content: const Text('This will delete all downloaded models and cached data. Continue?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Clear'),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      // TODO: Implement cache clearing
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Cache cleared')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _saveSettings,
            tooltip: 'Save Settings',
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Account Section
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Account',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  ListTile(
                    leading: const Icon(Icons.person),
                    title: const Text('Email'),
                    subtitle: Text(authProvider.userEmail ?? 'Not logged in'),
                  ),
                  ListTile(
                    leading: const Icon(Icons.vpn_key),
                    title: const Text('Change Password'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Password change coming soon')),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Detection Settings
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Detection Settings',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  ListTile(
                    title: const Text('Confidence Threshold'),
                    subtitle: Text('${(_confidenceThreshold * 100).toInt()}%'),
                  ),
                  Slider(
                    value: _confidenceThreshold,
                    min: 0.1,
                    max: 1.0,
                    divisions: 18,
                    label: '${(_confidenceThreshold * 100).toInt()}%',
                    onChanged: (value) {
                      setState(() => _confidenceThreshold = value);
                    },
                  ),
                  const Divider(),
                  SwitchListTile(
                    title: const Text('High Quality Camera'),
                    subtitle: const Text('Use 1080p resolution'),
                    value: _highQualityCamera,
                    onChanged: (value) {
                      setState(() => _highQualityCamera = value);
                    },
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Model Settings
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Model Settings',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  SwitchListTile(
                    title: const Text('Auto-download Models'),
                    subtitle: const Text('Automatically download new trained models'),
                    value: _autoDownloadModels,
                    onChanged: (value) {
                      setState(() => _autoDownloadModels = value);
                    },
                  ),
                  const Divider(),
                  ListTile(
                    title: const Text('Preferred Format'),
                    subtitle: Text(_selectedFormat.toUpperCase()),
                    trailing: DropdownButton<String>(
                      value: _selectedFormat,
                      items: const [
                        DropdownMenuItem(value: 'tflite', child: Text('TFLite')),
                        DropdownMenuItem(value: 'onnx', child: Text('ONNX')),
                        DropdownMenuItem(value: 'coreml', child: Text('CoreML')),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setState(() => _selectedFormat = value);
                        }
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // App Info
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'App Information',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  ListTile(
                    leading: const Icon(Icons.info),
                    title: const Text('Version'),
                    subtitle: const Text('1.0.0'),
                  ),
                  ListTile(
                    leading: const Icon(Icons.cloud),
                    title: const Text('API Server'),
                    subtitle: Text(ApiConfig.baseUrl),
                  ),
                  ListTile(
                    leading: const Icon(Icons.delete),
                    title: const Text('Clear Cache'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: _clearCache,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
