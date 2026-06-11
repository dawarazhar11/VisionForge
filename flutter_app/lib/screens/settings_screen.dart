import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
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
  final _backendUrlController = TextEditingController();
  bool _isTestingConnection = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  @override
  void dispose() {
    _backendUrlController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _autoDownloadModels = prefs.getBool('autoDownloadModels') ?? false;
      _highQualityCamera = prefs.getBool('highQualityCamera') ?? true;
      _confidenceThreshold = prefs.getDouble('confidenceThreshold') ?? 0.5;
      _selectedFormat = prefs.getString('modelFormat') ?? 'tflite';
      _backendUrlController.text =
          prefs.getString(ApiConfig.backendUrlPrefKey) ?? '';
    });
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('autoDownloadModels', _autoDownloadModels);
    await prefs.setBool('highQualityCamera', _highQualityCamera);
    await prefs.setDouble('confidenceThreshold', _confidenceThreshold);
    await prefs.setString('modelFormat', _selectedFormat);
    await ApiConfig.setBaseUrlOverride(_backendUrlController.text);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Settings saved'),
          backgroundColor: Colors.green,
        ),
      );
    }
  }

  Future<void> _testBackendConnection() async {
    setState(() => _isTestingConnection = true);

    final testUrl = ApiConfig.baseUrl;
    final uri = Uri.parse('$testUrl${ApiConfig.health}');

    try {
      final response = await http
          .get(uri)
          .timeout(ApiConfig.connectionTimeout);

      if (!mounted) return;

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connected to $testUrl'),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Server responded with status ${response.statusCode}',
            ),
            backgroundColor: Colors.orange,
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Connection failed: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isTestingConnection = false);
      }
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
                  ListTile(
                    leading: Icon(Icons.logout,
                        color: Theme.of(context).colorScheme.error),
                    title: Text('Log Out',
                        style: TextStyle(
                            color: Theme.of(context).colorScheme.error)),
                    onTap: () async {
                      final confirm = await showDialog<bool>(
                        context: context,
                        builder: (ctx) => AlertDialog(
                          title: const Text('Log Out'),
                          content: const Text('Sign out of this account?'),
                          actions: [
                            TextButton(
                                onPressed: () => Navigator.pop(ctx, false),
                                child: const Text('Cancel')),
                            FilledButton(
                                onPressed: () => Navigator.pop(ctx, true),
                                child: const Text('Log Out')),
                          ],
                        ),
                      );
                      if (confirm == true) {
                        await authProvider.logout();
                      }
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

          // Backend Settings
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Backend Server',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Override the API base URL for physical device testing. '
                    'Leave blank to use the default (${ApiConfig.defaultBaseUrl}).',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _backendUrlController,
                    decoration: InputDecoration(
                      labelText: 'Backend URL',
                      hintText: ApiConfig.defaultBaseUrl,
                      prefixIcon: const Icon(Icons.cloud),
                      border: const OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                    enableSuggestions: false,
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _isTestingConnection
                              ? null
                              : () async {
                                  await ApiConfig.setBaseUrlOverride(
                                    _backendUrlController.text,
                                  );
                                  await _testBackendConnection();
                                },
                          icon: _isTestingConnection
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.network_check),
                          label: const Text('Test Connection'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Active URL: ${ApiConfig.baseUrl}',
                    style: Theme.of(context).textTheme.bodySmall,
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
