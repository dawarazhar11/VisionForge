import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/project.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Project detail: pipeline (render/train jobs with live progress),
/// annotated dataset previews, resolved class list, and launchers.
class ProjectDetailScreen extends StatefulWidget {
  final Project project;
  const ProjectDetailScreen({super.key, required this.project});

  @override
  State<ProjectDetailScreen> createState() => _ProjectDetailScreenState();
}

class _ProjectDetailScreenState extends State<ProjectDetailScreen> {
  final _api = ApiService();
  String? _token;

  List<Map<String, dynamic>> _jobs = [];
  List<String> _classNames = [];
  List<String> _previews = [];
  String? _previewJobId;
  bool _loading = true;
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _token = Provider.of<AuthProvider>(context, listen: false).accessToken;
    _refresh();
    _poll = Timer.periodic(const Duration(seconds: 5), (_) {
      if (_jobs.any((j) => _isActive(j['status']))) _refresh(silent: true);
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  bool _isActive(dynamic status) =>
      status == 'PENDING' || status == 'RUNNING' || status == 'STARTED';

  Future<void> _refresh({bool silent = false}) async {
    if (_token == null) return;
    if (!silent) setState(() => _loading = true);
    try {
      final jobs = await _api.getTrainingJobs(_token!, widget.project.id);
      final jobList = jobs
          .map((j) => Map<String, dynamic>.from(j as Map))
          .toList()
        ..sort((a, b) => (b['created_at'] ?? '')
            .toString()
            .compareTo((a['created_at'] ?? '').toString()));

      Map<String, dynamic>? latestRender;
      for (final j in jobList) {
        if (j['stage'] == 'render' && j['status'] == 'SUCCESS') {
          latestRender = j;
          break;
        }
      }
      var previews = _previews;
      var previewJob = _previewJobId;
      var classes = _classNames;
      if (latestRender != null && latestRender['id'] != _previewJobId) {
        previewJob = latestRender['id'] as String;
        previews = await _api.getJobPreviews(_token!, previewJob);
        final m = latestRender['metrics_json'];
        if (m is Map && m['class_names'] is List) {
          classes = (m['class_names'] as List).map((e) => '$e').toList();
        }
      }

      if (!mounted) return;
      setState(() {
        _jobs = jobList;
        _previews = previews;
        _previewJobId = previewJob;
        _classNames = classes;
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _startJob(String type) async {
    if (_token == null) return;
    try {
      await _api.createJob(
        projectId: widget.project.id,
        jobType: type,
        config: type == 'render'
            ? {
                'num_renders': 40,
                'resolution_x': 640,
                'resolution_y': 640,
                'eevee_samples': 24
              }
            : {'epochs': 30, 'imgsz': 320, 'device': 'cpu'},
      );
      _refresh(silent: true);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(
                '${type == 'render' ? 'Render' : 'Training'} started')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Failed: $e')));
      }
    }
  }

  bool get _hasSuccessfulRender =>
      _jobs.any((j) => j['stage'] == 'render' && j['status'] == 'SUCCESS');

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.project.name),
        actions: [
          IconButton(
              icon: const Icon(Icons.refresh), onPressed: () => _refresh()),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                padding: const EdgeInsets.all(AppTheme.s4),
                children: [
                  _actions(),
                  const SizedBox(height: AppTheme.s5),
                  if (_classNames.isNotEmpty) ...[
                    _sectionTitle('Detected classes'),
                    _classChips(),
                    const SizedBox(height: AppTheme.s5),
                  ],
                  if (_previews.isNotEmpty) ...[
                    _sectionTitle('Dataset preview'),
                    _previewGrid(),
                    const SizedBox(height: AppTheme.s5),
                  ],
                  _sectionTitle('Pipeline'),
                  if (_jobs.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: AppTheme.s4),
                      child: Text(
                          'No jobs yet. Start a render to generate data.'),
                    )
                  else
                    ..._jobs.map(_jobCard),
                ],
              ),
            ),
    );
  }

  Widget _actions() {
    return Row(
      children: [
        Expanded(
          child: FilledButton.icon(
            onPressed: () => _startJob('render'),
            icon: const Icon(Icons.movie_filter),
            label: const Text('Render'),
          ),
        ),
        const SizedBox(width: AppTheme.s3),
        Expanded(
          child: FilledButton.tonalIcon(
            onPressed: _hasSuccessfulRender ? () => _startJob('train') : null,
            icon: const Icon(Icons.model_training),
            label: const Text('Train'),
          ),
        ),
      ],
    );
  }

  Widget _sectionTitle(String t) => Padding(
        padding: const EdgeInsets.only(bottom: AppTheme.s2),
        child: Text(t, style: Theme.of(context).textTheme.titleMedium),
      );

  Widget _classChips() => Wrap(
        spacing: AppTheme.s2,
        runSpacing: AppTheme.s2,
        children: _classNames
            .map((c) => Chip(
                label: Text(c), visualDensity: VisualDensity.compact))
            .toList(),
      );

  Widget _previewGrid() {
    final headers = {'Authorization': 'Bearer $_token'};
    return SizedBox(
      height: 110,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _previews.length,
        separatorBuilder: (_, __) => const SizedBox(width: AppTheme.s2),
        itemBuilder: (_, i) {
          final url = _api.jobPreviewUrl(_previewJobId!, _previews[i]);
          return ClipRRect(
            borderRadius: BorderRadius.circular(AppTheme.s2),
            child: Image.network(
              url,
              headers: headers,
              width: 150,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Container(
                width: 150,
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                child: const Icon(Icons.broken_image),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _jobCard(Map<String, dynamic> j) {
    final stage = (j['stage'] ?? 'job').toString();
    final status = (j['status'] ?? '').toString();
    final progress =
        (j['progress'] is num) ? (j['progress'] as num).toInt() : 0;
    final active = _isActive(status);

    Color statusColor;
    switch (status) {
      case 'SUCCESS':
        statusColor = Colors.green;
        break;
      case 'FAILED':
        statusColor = Theme.of(context).colorScheme.error;
        break;
      default:
        statusColor = Theme.of(context).colorScheme.primary;
    }

    final metrics = j['metrics_json'];
    final hasError = status == 'FAILED' &&
        metrics is Map &&
        metrics['error'] != null;

    return Card(
      margin: const EdgeInsets.only(bottom: AppTheme.s3),
      child: Padding(
        padding: const EdgeInsets.all(AppTheme.s4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                    stage == 'render'
                        ? Icons.movie_filter
                        : Icons.model_training,
                    size: 20),
                const SizedBox(width: AppTheme.s2),
                Text(stage.isEmpty
                    ? 'Job'
                    : stage[0].toUpperCase() + stage.substring(1),
                    style: Theme.of(context).textTheme.titleSmall),
                const Spacer(),
                Text(status,
                    style: TextStyle(
                        color: statusColor, fontWeight: FontWeight.w600)),
              ],
            ),
            if (active) ...[
              const SizedBox(height: AppTheme.s3),
              LinearProgressIndicator(
                  value: progress > 0 ? progress / 100 : null),
              const SizedBox(height: AppTheme.s1),
              Text('$progress%',
                  style: Theme.of(context).textTheme.bodySmall),
            ],
            if (hasError) ...[
              const SizedBox(height: AppTheme.s2),
              Text(
                (metrics)['error'].toString(),
                style: TextStyle(
                    color: Theme.of(context).colorScheme.error, fontSize: 12),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
