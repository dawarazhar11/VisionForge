import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/project.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';

class TrainingJobCreateScreen extends StatefulWidget {
  final Project project;

  const TrainingJobCreateScreen({super.key, required this.project});

  @override
  State<TrainingJobCreateScreen> createState() => _TrainingJobCreateScreenState();
}

class _TrainingJobCreateScreenState extends State<TrainingJobCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  String _modelType = 'yolo11n';
  int _epochs = 100;
  int _batchSize = 16;
  int _imageSize = 640;
  bool _isSubmitting = false;
  bool _isLoadingDatasets = true;
  List<Map<String, dynamic>> _datasets = [];
  String? _selectedDatasetId;

  // Advanced options
  bool _showAdvancedOptions = false;
  double _validationSplit = 0.2;
  bool _useClassWeights = false;
  bool _useAugmentation = true;
  bool _useMosaic = true;
  bool _useMixup = false;

  final List<Map<String, String>> _modelTypes = [
    {'value': 'yolo11n', 'label': 'YOLO11 Nano (fastest)'},
    {'value': 'yolo11s', 'label': 'YOLO11 Small'},
    {'value': 'yolo11m', 'label': 'YOLO11 Medium'},
    {'value': 'yolo11l', 'label': 'YOLO11 Large (best accuracy)'},
  ];

  @override
  void initState() {
    super.initState();
    _loadDatasets();
  }

  Future<void> _loadDatasets() async {
    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final token = authProvider.accessToken;

      if (token == null) {
        throw Exception('Not authenticated');
      }

      final apiService = ApiService();
      final datasetsData = await apiService.getDatasets(token, widget.project.id);

      setState(() {
        _datasets = datasetsData.cast<Map<String, dynamic>>();
        _isLoadingDatasets = false;
        if (_datasets.isNotEmpty) {
          _selectedDatasetId = _datasets.first['id']?.toString();
        }
      });
    } catch (e) {
      setState(() {
        _isLoadingDatasets = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Warning: Could not load datasets - $e'),
            backgroundColor: Colors.orange,
          ),
        );
      }
    }
  }

  Future<void> _submitTraining() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final token = authProvider.accessToken;

      if (token == null) {
        throw Exception('Not authenticated');
      }

      final apiService = ApiService();
      await apiService.createTrainingJob(
        token,
        widget.project.id,
        _modelType,
        _epochs,
        _batchSize,
        _imageSize,
        datasetId: _selectedDatasetId,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Training job started successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Start Training'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Project: ${widget.project.name}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        widget.project.description ?? '',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Training Configuration',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),

              // Dataset Selection Dropdown
              if (_isLoadingDatasets)
                const LinearProgressIndicator()
              else if (_datasets.isEmpty)
                Card(
                  color: Colors.orange.shade50,
                  child: const Padding(
                    padding: EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(Icons.warning, color: Colors.orange),
                        SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'No datasets available. Upload a dataset first.',
                            style: TextStyle(color: Colors.orange),
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              else
                DropdownButtonFormField<String>(
                  value: _selectedDatasetId,
                  decoration: const InputDecoration(
                    labelText: 'Dataset',
                    border: OutlineInputBorder(),
                    helperText: 'Select dataset to train on',
                  ),
                  items: _datasets.map((dataset) {
                    final name = dataset['name'] ?? 'Unnamed Dataset';
                    final imageCount = dataset['image_count'] ?? 0;
                    return DropdownMenuItem(
                      value: dataset['id']?.toString(),
                      child: Text('$name ($imageCount images)'),
                    );
                  }).toList(),
                  onChanged: (value) {
                    setState(() => _selectedDatasetId = value);
                  },
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please select a dataset';
                    }
                    return null;
                  },
                ),
              const SizedBox(height: 16),

              // Model Type Dropdown
              DropdownButtonFormField<String>(
                value: _modelType,
                decoration: const InputDecoration(
                  labelText: 'Model Type',
                  border: OutlineInputBorder(),
                  helperText: 'Nano is fastest, Large is most accurate',
                ),
                items: _modelTypes.map((model) {
                  return DropdownMenuItem(
                    value: model['value'],
                    child: Text(model['label']!),
                  );
                }).toList(),
                onChanged: (value) {
                  setState(() => _modelType = value!);
                },
              ),
              const SizedBox(height: 16),

              // Epochs
              TextFormField(
                initialValue: _epochs.toString(),
                decoration: const InputDecoration(
                  labelText: 'Epochs',
                  border: OutlineInputBorder(),
                  helperText: 'Number of training iterations (recommended: 50-300)',
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter epochs';
                  }
                  final n = int.tryParse(value);
                  if (n == null || n < 1 || n > 1000) {
                    return 'Enter a value between 1 and 1000';
                  }
                  return null;
                },
                onChanged: (value) {
                  final n = int.tryParse(value);
                  if (n != null) _epochs = n;
                },
              ),
              const SizedBox(height: 16),

              // Batch Size
              TextFormField(
                initialValue: _batchSize.toString(),
                decoration: const InputDecoration(
                  labelText: 'Batch Size',
                  border: OutlineInputBorder(),
                  helperText: 'Images per batch (recommended: 8-32)',
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter batch size';
                  }
                  final n = int.tryParse(value);
                  if (n == null || n < 1 || n > 128) {
                    return 'Enter a value between 1 and 128';
                  }
                  return null;
                },
                onChanged: (value) {
                  final n = int.tryParse(value);
                  if (n != null) _batchSize = n;
                },
              ),
              const SizedBox(height: 16),

              // Image Size
              DropdownButtonFormField<int>(
                value: _imageSize,
                decoration: const InputDecoration(
                  labelText: 'Image Size',
                  border: OutlineInputBorder(),
                  helperText: 'Resolution for training (larger = slower)',
                ),
                items: const [
                  DropdownMenuItem(value: 320, child: Text('320x320 (fastest)')),
                  DropdownMenuItem(value: 480, child: Text('480x480')),
                  DropdownMenuItem(value: 640, child: Text('640x640 (recommended)')),
                  DropdownMenuItem(value: 1280, child: Text('1280x1280 (best quality)')),
                ],
                onChanged: (value) {
                  setState(() => _imageSize = value!);
                },
              ),
              const SizedBox(height: 24),

              // Advanced Options Toggle
              OutlinedButton.icon(
                onPressed: () {
                  setState(() => _showAdvancedOptions = !_showAdvancedOptions);
                },
                icon: Icon(_showAdvancedOptions ? Icons.expand_less : Icons.expand_more),
                label: const Text('Advanced Options'),
              ),
              const SizedBox(height: 16),

              // Advanced Options Panel
              if (_showAdvancedOptions) ...[
                Card(
                  color: Colors.grey.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Validation Split
                        Text(
                          'Validation Split: ${(_validationSplit * 100).toInt()}%',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        Slider(
                          value: _validationSplit,
                          min: 0.1,
                          max: 0.3,
                          divisions: 4,
                          label: '${(_validationSplit * 100).toInt()}%',
                          onChanged: (value) {
                            setState(() => _validationSplit = value);
                          },
                        ),
                        const Text(
                          'Percentage of data used for validation',
                          style: TextStyle(fontSize: 12, color: Colors.grey),
                        ),
                        const Divider(height: 24),

                        // Class Weights
                        SwitchListTile(
                          title: const Text('Use Class Weights'),
                          subtitle: const Text('Balance training for imbalanced datasets'),
                          value: _useClassWeights,
                          onChanged: (value) {
                            setState(() => _useClassWeights = value);
                          },
                        ),
                        const Divider(height: 24),

                        // Data Augmentation
                        SwitchListTile(
                          title: const Text('Data Augmentation'),
                          subtitle: const Text('Apply transformations to training images'),
                          value: _useAugmentation,
                          onChanged: (value) {
                            setState(() => _useAugmentation = value);
                          },
                        ),

                        // Augmentation techniques (only shown if augmentation is enabled)
                        if (_useAugmentation) ...[
                          const SizedBox(height: 12),
                          Padding(
                            padding: const EdgeInsets.only(left: 16),
                            child: Column(
                              children: [
                                CheckboxListTile(
                                  title: const Text('Mosaic Augmentation'),
                                  subtitle: const Text('Combine 4 images into 1'),
                                  value: _useMosaic,
                                  onChanged: (value) {
                                    setState(() => _useMosaic = value ?? true);
                                  },
                                ),
                                CheckboxListTile(
                                  title: const Text('Mixup Augmentation'),
                                  subtitle: const Text('Blend two images together'),
                                  value: _useMixup,
                                  onChanged: (value) {
                                    setState(() => _useMixup = value ?? false);
                                  },
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
              ],

              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isSubmitting ? null : _submitTraining,
                  icon: _isSubmitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.play_arrow),
                  label: Text(_isSubmitting ? 'Starting Training...' : 'Start Training'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.all(16),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
