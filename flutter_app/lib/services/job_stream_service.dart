import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../utils/api_config.dart';

/// SSE progress payload from GET /api/v1/jobs/{id}/stream.
class JobProgressEvent {
  final String id;
  final String status;
  final int progress;
  final String? stage;
  final Map<String, dynamic>? metrics;
  final String? errorMessage;
  final String eventType;

  const JobProgressEvent({
    required this.id,
    required this.status,
    required this.progress,
    this.stage,
    this.metrics,
    this.errorMessage,
    this.eventType = 'progress',
  });

  factory JobProgressEvent.fromJson(Map<String, dynamic> json, {String eventType = 'progress'}) {
    return JobProgressEvent(
      id: json['id']?.toString() ?? '',
      status: json['status']?.toString() ?? 'UNKNOWN',
      progress: (json['progress'] as num?)?.toInt() ?? 0,
      stage: json['stage']?.toString(),
      metrics: json['metrics'] is Map
          ? Map<String, dynamic>.from(json['metrics'] as Map)
          : null,
      errorMessage: json['error_message']?.toString(),
      eventType: eventType,
    );
  }

  factory JobProgressEvent.error(String message) {
    return JobProgressEvent(
      id: '',
      status: 'FAILED',
      progress: 0,
      errorMessage: message,
      eventType: 'error',
    );
  }

  static bool isTerminalStatus(String status) {
    switch (status.toUpperCase()) {
      case 'SUCCESS':
      case 'FAILED':
      case 'CANCELLED':
        return true;
      default:
        return false;
    }
  }

  static bool isActiveStatus(String status) {
    switch (status.toUpperCase()) {
      case 'PENDING':
      case 'RUNNING':
      case 'QUEUED':
        return true;
      default:
        return false;
    }
  }
}

/// SSE client for job progress streaming.
class JobStreamService {
  final http.Client _client;

  JobStreamService({http.Client? client}) : _client = client ?? http.Client();

  String jobStreamUrl(String jobId) =>
      '${ApiConfig.baseUrl}${ApiConfig.jobs}/$jobId/stream';

  Stream<JobProgressEvent> streamJobProgress(String jobId, String token) async* {
    final request = http.Request('GET', Uri.parse(jobStreamUrl(jobId)));
    request.headers['Accept'] = 'text/event-stream';
    request.headers['Authorization'] = 'Bearer $token';
    request.headers['Cache-Control'] = 'no-cache';

    final response = await _client.send(request);

    if (response.statusCode != 200) {
      throw Exception('SSE connect failed (${response.statusCode})');
    }

    var pending = '';
    await for (final chunk in response.stream.transform(utf8.decoder)) {
      pending += chunk;

      while (pending.contains('\n\n')) {
        final splitIndex = pending.indexOf('\n\n');
        final block = pending.substring(0, splitIndex);
        pending = pending.substring(splitIndex + 2);

        final parsed = _parseSseBlock(block);
        if (parsed == null) continue;

        yield parsed;

        if (parsed.eventType == 'error' ||
            JobProgressEvent.isTerminalStatus(parsed.status)) {
          return;
        }
      }
    }
  }

  JobProgressEvent? _parseSseBlock(String block) {
    String? eventType;
    String? dataLine;

    for (final rawLine in block.split('\n')) {
      final line = rawLine.trimRight();
      if (line.startsWith('event:')) {
        eventType = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        dataLine = line.substring(5).trim();
      }
    }

    if (dataLine == null || dataLine.isEmpty) return null;

    final data = jsonDecode(dataLine);
    if (data is! Map<String, dynamic>) return null;

    if (eventType == 'error') {
      return JobProgressEvent.error(
        data['message']?.toString() ?? 'Stream error',
      );
    }

    return JobProgressEvent.fromJson(data, eventType: eventType ?? 'progress');
  }

  void dispose() {
    _client.close();
  }
}
