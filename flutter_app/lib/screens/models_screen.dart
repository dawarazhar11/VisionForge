import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import 'model_comparison_screen.dart';

class ModelsScreen extends StatefulWidget {
  const ModelsScreen({super.key});

  @override
  State<ModelsScreen> createState() => _ModelsScreenState();
}

class _ModelsScreenState extends State<ModelsScreen> {
  List<dynamic> _models = [];
  bool _isLoading = true;
  String? _error;
  Map<String, double> _downloadProgress = {};
  String? _activeModelId;
  String? _activeModelPath;

  @override
  void initState() {
    super.initState();
    _loadActiveModel();
    _loadModels();
  }

  Future<void> _loadActiveModel() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _activeModelId = prefs.getString('active_model_id');
      _activeModelPath = prefs.getString('active_model_path');
    });
  }

  Future<void> _setActiveModel(String modelId, String modelPath) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('active_model_id', modelId);
    await prefs.setString('active_model_path', modelPath);

    setState(() {
      _activeModelId = modelId;
      _activeModelPath = modelPath;
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Model set as active for detection'),
          backgroundColor: Colors.green,
        ),
      );
    }
  }

  Future<void> _loadModels() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final token = authProvider.accessToken;

      if (token == null) {
        throw Exception('Not authenticated');
      }

      final apiService = ApiService();
      // Note: Backend endpoint might return different structure
      // Adjust based on actual API response
      final models = [];  // await apiService.getModels(token);

      setState(() {
        _models = models;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _downloadModel(String modelId, String modelName) async {
    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final token = authProvider.accessToken;

      if (token == null) {
        throw Exception('Not authenticated');
      }

      // Get app documents directory
      final directory = await getApplicationDocumentsDirectory();
      final modelsDir = Directory('${directory.path}/models');
      if (!await modelsDir.exists()) {
        await modelsDir.create(recursive: true);
      }

      final filePath = '${modelsDir.path}/$modelName.tflite';

      setState(() {
        _downloadProgress[modelId] = 0.0;
      });

      final apiService = ApiService();
      await apiService.downloadModel(
        token,
        modelId,
        filePath,
        onProgress: (received, total) {
          if (total > 0) {
            setState(() {
              _downloadProgress[modelId] = received / total;
            });
          }
        },
      );

      setState(() {
        _downloadProgress.remove(modelId);
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Model downloaded to: $filePath'),
            backgroundColor: Colors.green,
            action: SnackBarAction(
              label: 'Set Active',
              textColor: Colors.white,
              onPressed: () => _setActiveModel(modelId, filePath),
            ),
          ),
        );
      }
    } catch (e) {
      setState(() {
        _downloadProgress.remove(modelId);
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Download failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Models'),
        actions: [
          IconButton(
            icon: const Icon(Icons.compare_arrows),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => const ModelComparisonScreen(),
                ),
              );
            },
            tooltip: 'Compare Models',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadModels,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: Column(
        children: [
          // Active model banner
          if (_activeModelId != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                border: Border(
                  bottom: BorderSide(color: Colors.green.shade200),
                ),
              ),
              child: Row(
                children: [
                  Icon(Icons.check_circle, color: Colors.green.shade700),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Active Model for Detection',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.green.shade900,
                          ),
                        ),
                        Text(
                          _activeModelPath?.split(Platform.pathSeparator).last ?? 'Unknown',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.green.shade700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

          // Models list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.error_outline, size: 64, color: Colors.red),
                            const SizedBox(height: 16),
                            Text('Error: $_error'),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: _loadModels,
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      )
                    : _models.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.cloud_off, size: 64, color: Colors.grey),
                                const SizedBox(height: 16),
                                const Text('No trained models yet'),
                                const SizedBox(height: 8),
                                const Text(
                                  'Start a training job to create a model',
                                  style: TextStyle(color: Colors.grey),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: _models.length,
                            itemBuilder: (context, index) {
                              final model = _models[index];
                              final modelId = model['id'] ?? '';
                              final modelName = model['name'] ?? 'Unknown Model';
                              final accuracy = model['accuracy'] ?? 0.0;
                              final createdAt = model['created_at'] ?? '';
                              final isDownloading = _downloadProgress.containsKey(modelId);
                              final progress = _downloadProgress[modelId] ?? 0.0;
                              final isActive = modelId == _activeModelId;

                              return Card(
                                margin: const EdgeInsets.only(bottom: 12),
                                elevation: isActive ? 4 : 1,
                                color: isActive ? Colors.green.shade50 : null,
                                child: Column(
                                  children: [
                                    ListTile(
                                      leading: CircleAvatar(
                                        backgroundColor: isActive ? Colors.green : Colors.blue,
                                        child: Icon(
                                          isActive ? Icons.check_circle : Icons.storage,
                                          color: Colors.white,
                                        ),
                                      ),
                                      title: Row(
                                        children: [
                                          Expanded(child: Text(modelName)),
                                          if (isActive)
                                            Container(
                                              padding: const EdgeInsets.symmetric(
                                                horizontal: 8,
                                                vertical: 4,
                                              ),
                                              decoration: BoxDecoration(
                                                color: Colors.green,
                                                borderRadius: BorderRadius.circular(12),
                                              ),
                                              child: const Text(
                                                'ACTIVE',
                                                style: TextStyle(
                                                  color: Colors.white,
                                                  fontSize: 10,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                            ),
                                        ],
                                      ),
                                      subtitle: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text('Accuracy: ${(accuracy * 100).toStringAsFixed(1)}%'),
                                          Text('Created: $createdAt', style: const TextStyle(fontSize: 12)),
                                        ],
                                      ),
                                      trailing: isDownloading
                                          ? SizedBox(
                                              width: 50,
                                              child: Column(
                                                mainAxisAlignment: MainAxisAlignment.center,
                                                children: [
                                                  CircularProgressIndicator(value: progress),
                                                  const SizedBox(height: 4),
                                                  Text('${(progress * 100).toInt()}%', style: const TextStyle(fontSize: 10)),
                                                ],
                                              ),
                                            )
                                          : Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                IconButton(
                                                  icon: const Icon(Icons.download),
                                                  onPressed: () => _downloadModel(modelId, modelName),
                                                  tooltip: 'Download Model',
                                                ),
                                                if (!isActive)
                                                  IconButton(
                                                    icon: const Icon(Icons.play_circle_outline),
                                                    onPressed: () async {
                                                      // Check if model file exists locally
                                                      final directory = await getApplicationDocumentsDirectory();
                                                      final filePath = '${directory.path}/models/$modelName.tflite';
                                                      if (File(filePath).existsSync()) {
                                                        _setActiveModel(modelId, filePath);
                                                      } else {
                                                        ScaffoldMessenger.of(context).showSnackBar(
                                                          const SnackBar(
                                                            content: Text('Download model first'),
                                                            backgroundColor: Colors.orange,
                                                          ),
                                                        );
                                                      }
                                                    },
                                                    tooltip: 'Set as Active',
                                                  ),
                                              ],
                                            ),
                                    ),
                                    if (isDownloading)
                                      Padding(
                                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                        child: LinearProgressIndicator(value: progress),
                                      ),
                                  ],
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}
