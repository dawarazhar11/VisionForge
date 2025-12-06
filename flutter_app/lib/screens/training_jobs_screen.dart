import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import 'training_results_screen.dart';

class TrainingJobsScreen extends StatefulWidget {
  const TrainingJobsScreen({super.key});

  @override
  State<TrainingJobsScreen> createState() => _TrainingJobsScreenState();
}

class _TrainingJobsScreenState extends State<TrainingJobsScreen> {
  List<dynamic> _jobs = [];
  bool _isLoading = true;
  String? _error;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadJobs();
    // Auto-refresh every 10 seconds
    _refreshTimer = Timer.periodic(const Duration(seconds: 10), (_) => _loadJobs());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadJobs() async {
    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final token = authProvider.accessToken;

      if (token == null) {
        throw Exception('Not authenticated');
      }

      final apiService = ApiService();
      final jobs = await apiService.getTrainingJobs(token);

      if (mounted) {
        setState(() {
          _jobs = jobs;
          _isLoading = false;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'completed':
        return Colors.green;
      case 'running':
      case 'training':
        return Colors.blue;
      case 'failed':
      case 'error':
        return Colors.red;
      case 'pending':
      case 'queued':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }

  IconData _getStatusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'completed':
        return Icons.check_circle;
      case 'running':
      case 'training':
        return Icons.play_circle;
      case 'failed':
      case 'error':
        return Icons.error;
      case 'pending':
      case 'queued':
        return Icons.schedule;
      default:
        return Icons.help;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Training Jobs'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadJobs,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _isLoading && _jobs.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _jobs.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, size: 64, color: Colors.red),
                      const SizedBox(height: 16),
                      Text('Error: $_error'),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadJobs,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : _jobs.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.cloud_queue, size: 64, color: Colors.grey),
                          const SizedBox(height: 16),
                          const Text('No training jobs yet'),
                          const SizedBox(height: 8),
                          const Text(
                            'Create a project and start training',
                            style: TextStyle(color: Colors.grey),
                          ),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _loadJobs,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _jobs.length,
                        itemBuilder: (context, index) {
                          final job = _jobs[index];
                          final jobId = job['id'] ?? '';
                          final status = job['status'] ?? 'unknown';
                          final modelType = job['model_type'] ?? 'Unknown';
                          final epochs = job['epochs'] ?? 0;
                          final currentEpoch = job['current_epoch'] ?? 0;
                          final accuracy = job['accuracy'];
                          final createdAt = job['created_at'] ?? '';
                          final progress = epochs > 0 ? currentEpoch / epochs : 0.0;

                          return Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: Column(
                              children: [
                                ListTile(
                                  leading: CircleAvatar(
                                    backgroundColor: _getStatusColor(status),
                                    child: Icon(
                                      _getStatusIcon(status),
                                      color: Colors.white,
                                    ),
                                  ),
                                  title: Text('Job #$jobId'),
                                  subtitle: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('Model: $modelType'),
                                      Text('Status: ${status.toUpperCase()}'),
                                      if (accuracy != null)
                                        Text('Accuracy: ${(accuracy * 100).toStringAsFixed(1)}%'),
                                      Text('Created: $createdAt', style: const TextStyle(fontSize: 12)),
                                    ],
                                  ),
                                  trailing: status.toLowerCase() == 'running' || status.toLowerCase() == 'training'
                                      ? SizedBox(
                                          width: 50,
                                          child: Column(
                                            mainAxisAlignment: MainAxisAlignment.center,
                                            children: [
                                              CircularProgressIndicator(value: progress),
                                              const SizedBox(height: 4),
                                              Text('$currentEpoch/$epochs', style: const TextStyle(fontSize: 10)),
                                            ],
                                          ),
                                        )
                                      : null,
                                ),
                                if (status.toLowerCase() == 'running' || status.toLowerCase() == 'training')
                                  Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                    child: Column(
                                      children: [
                                        LinearProgressIndicator(value: progress),
                                        const SizedBox(height: 4),
                                        Text(
                                          'Epoch $currentEpoch of $epochs',
                                          style: const TextStyle(fontSize: 12, color: Colors.grey),
                                        ),
                                      ],
                                    ),
                                  ),
                                if (status.toLowerCase() == 'completed')
                                  Padding(
                                    padding: const EdgeInsets.all(16),
                                    child: Row(
                                      mainAxisAlignment: MainAxisAlignment.end,
                                      children: [
                                        ElevatedButton.icon(
                                          onPressed: () {
                                            Navigator.of(context).push(
                                              MaterialPageRoute(
                                                builder: (_) => TrainingResultsScreen(
                                                  jobId: jobId.toString(),
                                                  jobName: 'Job #$jobId - $modelType',
                                                ),
                                              ),
                                            );
                                          },
                                          icon: const Icon(Icons.analytics),
                                          label: const Text('View Results'),
                                        ),
                                      ],
                                    ),
                                  ),
                              ],
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}
