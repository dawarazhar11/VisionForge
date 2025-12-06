import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'dart:io';

class ModelComparisonScreen extends StatefulWidget {
  const ModelComparisonScreen({super.key});

  @override
  State<ModelComparisonScreen> createState() => _ModelComparisonScreenState();
}

class _ModelComparisonScreenState extends State<ModelComparisonScreen> {
  String? _model1Path;
  String? _model2Path;
  String? _testImagePath;
  bool _isComparing = false;

  Map<String, dynamic>? _model1Results;
  Map<String, dynamic>? _model2Results;

  Future<void> _selectModel(int modelNumber) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['tflite', 'onnx', 'mlmodel'],
      dialogTitle: 'Select Model ${modelNumber}',
    );

    if (result != null && result.files.single.path != null) {
      setState(() {
        if (modelNumber == 1) {
          _model1Path = result.files.single.path;
        } else {
          _model2Path = result.files.single.path;
        }
      });
    }
  }

  Future<void> _selectTestImage() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      dialogTitle: 'Select Test Image',
    );

    if (result != null && result.files.single.path != null) {
      setState(() {
        _testImagePath = result.files.single.path;
      });
    }
  }

  Future<void> _runComparison() async {
    if (_model1Path == null || _model2Path == null || _testImagePath == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select both models and a test image'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() {
      _isComparing = true;
    });

    // Simulate model comparison (replace with actual inference)
    await Future.delayed(const Duration(seconds: 2));

    setState(() {
      _model1Results = {
        'detections': 5,
        'inference_time': 0.045,
        'fps': 22.2,
        'avg_confidence': 0.87,
        'objects': [
          {'class': 'screw', 'confidence': 0.92},
          {'class': 'bracket', 'confidence': 0.85},
          {'class': 'hole', 'confidence': 0.81},
        ],
      };

      _model2Results = {
        'detections': 6,
        'inference_time': 0.062,
        'fps': 16.1,
        'avg_confidence': 0.81,
        'objects': [
          {'class': 'screw', 'confidence': 0.88},
          {'class': 'bracket', 'confidence': 0.79},
          {'class': 'hole', 'confidence': 0.76},
          {'class': 'screw', 'confidence': 0.85},
        ],
      };

      _isComparing = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Model Comparison'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Info Card
            Card(
              color: Colors.blue.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Icon(Icons.compare_arrows, color: Colors.blue.shade700),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Compare two models side-by-side on the same test image to see performance differences.',
                        style: TextStyle(color: Colors.blue.shade900),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Model Selection
            Row(
              children: [
                Expanded(
                  child: _buildModelCard(
                    'Model 1',
                    _model1Path,
                    () => _selectModel(1),
                    Colors.blue,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildModelCard(
                    'Model 2',
                    _model2Path,
                    () => _selectModel(2),
                    Colors.purple,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Test Image Selection
            Card(
              child: ListTile(
                leading: const Icon(Icons.image, color: Colors.green),
                title: Text(
                  _testImagePath != null
                      ? _testImagePath!.split(Platform.pathSeparator).last
                      : 'No test image selected',
                ),
                subtitle: const Text('Click to select test image'),
                trailing: ElevatedButton.icon(
                  onPressed: _selectTestImage,
                  icon: const Icon(Icons.folder_open, size: 18),
                  label: const Text('Browse'),
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Run Comparison Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isComparing ? null : _runComparison,
                icon: _isComparing
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.play_arrow),
                label: Text(_isComparing ? 'Running Comparison...' : 'Run Comparison'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.all(16),
                ),
              ),
            ),
            const SizedBox(height: 32),

            // Results
            if (_model1Results != null && _model2Results != null) ...[
              Text(
                'Comparison Results',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),

              // Performance Metrics
              Row(
                children: [
                  Expanded(
                    child: _buildMetricsCard(
                      'Model 1',
                      _model1Results!,
                      Colors.blue,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: _buildMetricsCard(
                      'Model 2',
                      _model2Results!,
                      Colors.purple,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Winner Card
              _buildWinnerCard(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildModelCard(String title, String? path, VoidCallback onTap, Color color) {
    return Card(
      elevation: path != null ? 4 : 1,
      color: path != null ? color.withOpacity(0.1) : null,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(
              path != null ? Icons.check_circle : Icons.cloud_upload,
              size: 48,
              color: path != null ? color : Colors.grey,
            ),
            const SizedBox(height: 12),
            Text(
              title,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: path != null ? color : null,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              path != null ? path.split(Platform.pathSeparator).last : 'Not selected',
              style: const TextStyle(fontSize: 12),
              textAlign: TextAlign.center,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: onTap,
              icon: const Icon(Icons.folder_open, size: 16),
              label: const Text('Select'),
              style: ElevatedButton.styleFrom(
                backgroundColor: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricsCard(String title, Map<String, dynamic> results, Color color) {
    return Card(
      color: color.withOpacity(0.1),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
                color: color,
              ),
            ),
            const Divider(height: 24),
            _buildMetricRow('Detections', '${results['detections']}'),
            _buildMetricRow('Inference Time', '${(results['inference_time'] * 1000).toInt()} ms'),
            _buildMetricRow('FPS', '${results['fps'].toStringAsFixed(1)}'),
            _buildMetricRow('Avg Confidence', '${(results['avg_confidence'] * 100).toInt()}%'),
            const SizedBox(height: 12),
            const Text(
              'Detected Objects:',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
            ),
            const SizedBox(height: 8),
            ...List.generate(
              (results['objects'] as List).length,
              (index) {
                final obj = results['objects'][index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        obj['class'],
                        style: const TextStyle(fontSize: 12),
                      ),
                      Text(
                        '${(obj['confidence'] * 100).toInt()}%',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: color,
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12)),
          Text(
            value,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWinnerCard() {
    final model1Fps = _model1Results!['fps'] as double;
    final model2Fps = _model2Results!['fps'] as double;
    final model1Conf = _model1Results!['avg_confidence'] as double;
    final model2Conf = _model2Results!['avg_confidence'] as double;

    final model1Score = model1Fps * model1Conf;
    final model2Score = model2Fps * model2Conf;

    final winner = model1Score > model2Score ? 'Model 1' : 'Model 2';
    final winnerColor = model1Score > model2Score ? Colors.blue : Colors.purple;

    return Card(
      color: winnerColor.withOpacity(0.1),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(Icons.emoji_events, size: 48, color: winnerColor),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Winner',
                    style: TextStyle(
                      fontSize: 12,
                      color: winnerColor.withOpacity(0.7),
                    ),
                  ),
                  Text(
                    winner,
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: winnerColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Best combination of speed and accuracy',
                    style: TextStyle(
                      fontSize: 12,
                      color: winnerColor.withOpacity(0.7),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
