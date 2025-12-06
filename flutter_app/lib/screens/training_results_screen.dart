import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';

class TrainingResultsScreen extends StatefulWidget {
  final String jobId;
  final String jobName;

  const TrainingResultsScreen({
    super.key,
    required this.jobId,
    required this.jobName,
  });

  @override
  State<TrainingResultsScreen> createState() => _TrainingResultsScreenState();
}

class _TrainingResultsScreenState extends State<TrainingResultsScreen> {
  Map<String, dynamic>? _results;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadResults();
  }

  Future<void> _loadResults() async {
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
      // final results = await apiService.getTrainingResults(token, widget.jobId);

      // Mock data for UI demonstration
      final results = {
        'metrics': {
          'map50': 0.856,
          'map50_95': 0.672,
          'precision': 0.883,
          'recall': 0.792,
          'final_loss': 0.0234,
        },
        'training_time': 3420,
        'epochs_completed': 100,
        'best_epoch': 87,
        'class_metrics': {
          'small_screw': {'precision': 0.91, 'recall': 0.84, 'map50': 0.88},
          'large_screw': {'precision': 0.87, 'recall': 0.81, 'map50': 0.85},
          'bracket': {'precision': 0.92, 'recall': 0.88, 'map50': 0.90},
        },
        'loss_history': [
          {'epoch': 0, 'train_loss': 0.524, 'val_loss': 0.498},
          {'epoch': 20, 'train_loss': 0.145, 'val_loss': 0.162},
          {'epoch': 40, 'train_loss': 0.068, 'val_loss': 0.081},
          {'epoch': 60, 'train_loss': 0.041, 'val_loss': 0.053},
          {'epoch': 80, 'train_loss': 0.028, 'val_loss': 0.039},
          {'epoch': 100, 'train_loss': 0.023, 'val_loss': 0.034},
        ],
      };

      setState(() {
        _results = results;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Training Results - ${widget.jobName}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadResults,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _isLoading
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
                        onPressed: _loadResults,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : _buildResultsView(),
    );
  }

  Widget _buildResultsView() {
    if (_results == null) {
      return const Center(child: Text('No results available'));
    }

    final metrics = _results!['metrics'] as Map<String, dynamic>;
    final classMetrics = _results!['class_metrics'] as Map<String, dynamic>?;
    final trainingTime = _results!['training_time'] as int;
    final epochsCompleted = _results!['epochs_completed'] as int;
    final bestEpoch = _results!['best_epoch'] as int;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Summary Card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.check_circle, color: Colors.green, size: 32),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Training Completed',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            Text(
                              '$epochsCompleted epochs in ${_formatDuration(trainingTime)}',
                              style: const TextStyle(color: Colors.grey),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    children: [
                      Expanded(
                        child: _buildMetricTile(
                          'mAP@50',
                          '${(metrics['map50'] * 100).toStringAsFixed(1)}%',
                          Colors.blue,
                        ),
                      ),
                      Expanded(
                        child: _buildMetricTile(
                          'mAP@50-95',
                          '${(metrics['map50_95'] * 100).toStringAsFixed(1)}%',
                          Colors.purple,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _buildMetricTile(
                          'Precision',
                          '${(metrics['precision'] * 100).toStringAsFixed(1)}%',
                          Colors.green,
                        ),
                      ),
                      Expanded(
                        child: _buildMetricTile(
                          'Recall',
                          '${(metrics['recall'] * 100).toStringAsFixed(1)}%',
                          Colors.orange,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _buildMetricTile(
                          'Final Loss',
                          metrics['final_loss'].toStringAsFixed(4),
                          Colors.red,
                        ),
                      ),
                      Expanded(
                        child: _buildMetricTile(
                          'Best Epoch',
                          bestEpoch.toString(),
                          Colors.amber,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Per-Class Metrics
          if (classMetrics != null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Per-Class Performance',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 16),
                    ...classMetrics.entries.map((entry) {
                      final className = entry.key;
                      final classData = entry.value as Map<String, dynamic>;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              className.replaceAll('_', ' ').toUpperCase(),
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Expanded(
                                  child: _buildMiniMetric(
                                    'Precision',
                                    '${(classData['precision'] * 100).toStringAsFixed(1)}%',
                                  ),
                                ),
                                Expanded(
                                  child: _buildMiniMetric(
                                    'Recall',
                                    '${(classData['recall'] * 100).toStringAsFixed(1)}%',
                                  ),
                                ),
                                Expanded(
                                  child: _buildMiniMetric(
                                    'mAP@50',
                                    '${(classData['map50'] * 100).toStringAsFixed(1)}%',
                                  ),
                                ),
                              ],
                            ),
                            if (entry.key != classMetrics.keys.last)
                              const Divider(height: 24),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Loss Chart Placeholder
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Training Progress',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 16),
                  Container(
                    height: 200,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.show_chart, size: 48, color: Colors.grey.shade400),
                          const SizedBox(height: 8),
                          Text(
                            'Loss chart visualization',
                            style: TextStyle(color: Colors.grey.shade600),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '(Requires chart library like fl_chart)',
                            style: TextStyle(
                              color: Colors.grey.shade500,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Actions
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Download model feature - to be implemented'),
                      ),
                    );
                  },
                  icon: const Icon(Icons.download),
                  label: const Text('Download Best Model'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Export metrics feature - to be implemented'),
                      ),
                    );
                  },
                  icon: const Icon(Icons.file_download),
                  label: const Text('Export Metrics'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetricTile(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: color.withOpacity(0.8),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMiniMetric(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 11, color: Colors.grey),
        ),
        Text(
          value,
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  String _formatDuration(int seconds) {
    final hours = seconds ~/ 3600;
    final minutes = (seconds % 3600) ~/ 60;
    final secs = seconds % 60;

    if (hours > 0) {
      return '${hours}h ${minutes}m ${secs}s';
    } else if (minutes > 0) {
      return '${minutes}m ${secs}s';
    } else {
      return '${secs}s';
    }
  }
}
