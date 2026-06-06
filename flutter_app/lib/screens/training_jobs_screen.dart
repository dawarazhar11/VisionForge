import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../services/job_stream_service.dart';
import 'training_results_screen.dart';

class TrainingJobsScreen extends StatefulWidget {
  const TrainingJobsScreen({super.key});

  @override
  State<TrainingJobsScreen> createState() => _TrainingJobsScreenState();
}

class _TrainingJobsScreenState extends State<TrainingJobsScreen> {
  final ApiService _apiService = ApiService();
  final JobStreamService _jobStreamService = JobStreamService();

  List<dynamic> _jobs = [];
  bool _isLoading = true;
  String? _error;
  Timer? _fallbackPollTimer;
  final Map<String, StreamSubscription<JobProgressEvent>> _sseSubscriptions = {};
  final Set<String> _sseFailedJobs = {};

  @override
  void initState() {
    super.initState();
    _loadJobs();
  }

  @override
  void dispose() {
    _fallbackPollTimer?.cancel();
    _cancelAllSseStreams();
    _jobStreamService.dispose();
    super.dispose();
  }

  void _cancelAllSseStreams() {
    for (final subscription in _sseSubscriptions.values) {
      subscription.cancel();
    }
    _sseSubscriptions.clear();
  }

  Future<void> _loadJobs({bool silent = false}) async {
    if (!silent && mounted) {
      setState(() {
        _isLoading = _jobs.isEmpty;
        _error = null;
      });
    }

    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final token = authProvider.accessToken;

      if (token == null) {
        throw Exception('Not authenticated');
      }

      final jobs = await _apiService.getTrainingJobs(token);

      if (mounted) {
        setState(() {
          _jobs = jobs;
          _isLoading = false;
          _error = null;
        });
        _syncSseStreams(token);
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

  void _syncSseStreams(String token) {
    final activeJobIds = _jobs
        .where((job) => JobProgressEvent.isActiveStatus(_jobStatus(job)))
        .map((job) => job['id'].toString())
        .toSet();

    final staleIds = _sseSubscriptions.keys
        .where((id) => !activeJobIds.contains(id))
        .toList();
    for (final id in staleIds) {
      _sseSubscriptions.remove(id)?.cancel();
      _sseFailedJobs.remove(id);
    }

    for (final jobId in activeJobIds) {
      if (_sseSubscriptions.containsKey(jobId) || _sseFailedJobs.contains(jobId)) {
        continue;
      }
      _startSseStream(jobId, token);
    }

    _updateFallbackPolling();
  }

  void _startSseStream(String jobId, String token) {
    final subscription = _jobStreamService
        .streamJobProgress(jobId, token)
        .listen(
          (event) => _handleProgressEvent(event),
          onError: (_) => _handleSseDisconnect(jobId, token),
          onDone: () {
            _sseSubscriptions.remove(jobId);
            if (_sseFailedJobs.contains(jobId)) return;
            _loadJobs(silent: true);
          },
          cancelOnError: true,
        );

    _sseSubscriptions[jobId] = subscription;
  }

  void _handleProgressEvent(JobProgressEvent event) {
    if (!mounted || event.id.isEmpty) return;

    setState(() {
      final index = _jobs.indexWhere((job) => job['id'].toString() == event.id);
      if (index == -1) return;

      final current = Map<String, dynamic>.from(_jobs[index] as Map);
      current['status'] = event.status;
      current['progress'] = event.progress;
      if (event.stage != null) {
        current['stage'] = event.stage;
      }
      if (event.metrics != null) {
        current['metrics_json'] = event.metrics;
      }
      if (event.errorMessage != null) {
        current['error_message'] = event.errorMessage;
      }
      _jobs[index] = current;
    });

    if (JobProgressEvent.isTerminalStatus(event.status)) {
      _sseSubscriptions.remove(event.id)?.cancel();
      _sseFailedJobs.remove(event.id);
      _updateFallbackPolling();
    }
  }

  void _handleSseDisconnect(String jobId, String token) {
    _sseSubscriptions.remove(jobId)?.cancel();
    _sseFailedJobs.add(jobId);
    _updateFallbackPolling();

    Future.delayed(const Duration(seconds: 2), () {
      if (!mounted || !_sseFailedJobs.contains(jobId)) return;
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final retryToken = authProvider.accessToken;
      if (retryToken == null) return;

      final job = _jobs.cast<Map<String, dynamic>?>().firstWhere(
            (j) => j?['id'].toString() == jobId,
            orElse: () => null,
          );
      if (job != null && JobProgressEvent.isActiveStatus(_jobStatus(job))) {
        _sseFailedJobs.remove(jobId);
        _startSseStream(jobId, retryToken);
        _updateFallbackPolling();
      }
    });
  }

  void _updateFallbackPolling() {
    final needsFallback = _sseFailedJobs.isNotEmpty ||
        _jobs.any((job) {
          final id = job['id'].toString();
          return JobProgressEvent.isActiveStatus(_jobStatus(job)) &&
              !_sseSubscriptions.containsKey(id);
        });

    if (needsFallback) {
      _fallbackPollTimer ??= Timer.periodic(
        const Duration(seconds: 10),
        (_) => _loadJobs(silent: true),
      );
      return;
    }

    _fallbackPollTimer?.cancel();
    _fallbackPollTimer = null;
  }

  String _jobStatus(Map<String, dynamic> job) =>
      job['status']?.toString() ?? 'UNKNOWN';

  String _jobStage(Map<String, dynamic> job) =>
      job['stage']?.toString() ?? job['job_type']?.toString() ?? 'unknown';

  String _jobModelType(Map<String, dynamic> job) {
    final config = job['config_json'];
    if (config is Map && config['model_type'] != null) {
      return config['model_type'].toString();
    }
    return _jobStage(job);
  }

  double _jobProgressValue(Map<String, dynamic> job) {
    final progress = job['progress'];
    if (progress is num) {
      return (progress / 100).clamp(0.0, 1.0);
    }

    final config = job['config_json'];
    final metrics = job['metrics_json'];
    final epochs = config is Map ? (config['epochs'] as num?)?.toInt() : null;
    final currentEpoch = metrics is Map
        ? (metrics['current_epoch'] as num?)?.toInt()
        : (job['current_epoch'] as num?)?.toInt();

    if (epochs != null && epochs > 0 && currentEpoch != null) {
      return (currentEpoch / epochs).clamp(0.0, 1.0);
    }
    return 0.0;
  }

  String? _jobProgressLabel(Map<String, dynamic> job) {
    final progress = job['progress'];
    if (progress is num) {
      return '${progress.toInt()}%';
    }

    final config = job['config_json'];
    final metrics = job['metrics_json'];
    final epochs = config is Map ? (config['epochs'] as num?)?.toInt() : null;
    final currentEpoch = metrics is Map
        ? (metrics['current_epoch'] as num?)?.toInt()
        : (job['current_epoch'] as num?)?.toInt();

    if (epochs != null && epochs > 0) {
      return '${currentEpoch ?? 0}/$epochs epochs';
    }
    return null;
  }

  double? _jobAccuracy(Map<String, dynamic> job) {
    final metrics = job['metrics_json'];
    if (metrics is Map) {
      final accuracy = metrics['accuracy'] ?? metrics['map50'];
      if (accuracy is num) return accuracy.toDouble();
    }
    final accuracy = job['accuracy'];
    if (accuracy is num) return accuracy.toDouble();
    return null;
  }

  bool _isActiveJob(Map<String, dynamic> job) =>
      JobProgressEvent.isActiveStatus(_jobStatus(job));

  bool _isCompletedJob(Map<String, dynamic> job) {
    final status = _jobStatus(job).toUpperCase();
    return status == 'SUCCESS' || status == 'COMPLETED';
  }

  Color _getStatusColor(String status) {
    switch (status.toUpperCase()) {
      case 'SUCCESS':
      case 'COMPLETED':
        return Colors.green;
      case 'RUNNING':
      case 'TRAINING':
        return Colors.blue;
      case 'FAILED':
      case 'ERROR':
        return Colors.red;
      case 'PENDING':
      case 'QUEUED':
        return Colors.orange;
      case 'CANCELLED':
        return Colors.grey;
      default:
        return Colors.grey;
    }
  }

  IconData _getStatusIcon(String status) {
    switch (status.toUpperCase()) {
      case 'SUCCESS':
      case 'COMPLETED':
        return Icons.check_circle;
      case 'RUNNING':
      case 'TRAINING':
        return Icons.play_circle;
      case 'FAILED':
      case 'ERROR':
        return Icons.error;
      case 'PENDING':
      case 'QUEUED':
        return Icons.schedule;
      case 'CANCELLED':
        return Icons.cancel;
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
                          final job = Map<String, dynamic>.from(_jobs[index] as Map);
                          final jobId = job['id']?.toString() ?? '';
                          final status = _jobStatus(job);
                          final modelType = _jobModelType(job);
                          final stage = _jobStage(job);
                          final accuracy = _jobAccuracy(job);
                          final createdAt = job['created_at']?.toString() ?? '';
                          final progress = _jobProgressValue(job);
                          final progressLabel = _jobProgressLabel(job);
                          final isActive = _isActiveJob(job);
                          final isLive = _sseSubscriptions.containsKey(jobId);

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
                                      Text('Type: $modelType'),
                                      Text('Status: ${status.toUpperCase()}'),
                                      if (stage.isNotEmpty && stage != modelType)
                                        Text('Stage: $stage'),
                                      if (isLive)
                                        const Text(
                                          'Live updates',
                                          style: TextStyle(
                                            fontSize: 12,
                                            color: Colors.blue,
                                          ),
                                        ),
                                      if (accuracy != null)
                                        Text(
                                          'Accuracy: ${(accuracy * 100).toStringAsFixed(1)}%',
                                        ),
                                      Text(
                                        'Created: $createdAt',
                                        style: const TextStyle(fontSize: 12),
                                      ),
                                    ],
                                  ),
                                  trailing: isActive
                                      ? SizedBox(
                                          width: 56,
                                          child: Column(
                                            mainAxisAlignment: MainAxisAlignment.center,
                                            children: [
                                              CircularProgressIndicator(value: progress),
                                              if (progressLabel != null) ...[
                                                const SizedBox(height: 4),
                                                Text(
                                                  progressLabel,
                                                  style: const TextStyle(fontSize: 10),
                                                  textAlign: TextAlign.center,
                                                ),
                                              ],
                                            ],
                                          ),
                                        )
                                      : null,
                                ),
                                if (isActive)
                                  Padding(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 16,
                                      vertical: 8,
                                    ),
                                    child: Column(
                                      children: [
                                        LinearProgressIndicator(value: progress),
                                        if (progressLabel != null) ...[
                                          const SizedBox(height: 4),
                                          Text(
                                            progressLabel,
                                            style: const TextStyle(
                                              fontSize: 12,
                                              color: Colors.grey,
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                if (_isCompletedJob(job))
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
                                                  jobId: jobId,
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
