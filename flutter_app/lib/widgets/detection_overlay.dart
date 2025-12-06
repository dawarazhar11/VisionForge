import 'package:flutter/material.dart';
import '../services/yolo_service.dart';
import 'dart:math' as math;

/// Widget that renders detection bounding boxes on top of camera preview
class DetectionOverlay extends StatelessWidget {
  final List<Detection> detections;
  final Size previewSize;
  final bool showLabels;
  final bool showConfidence;

  const DetectionOverlay({
    super.key,
    required this.detections,
    required this.previewSize,
    this.showLabels = true,
    this.showConfidence = true,
  });

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: DetectionPainter(
        detections: detections,
        previewSize: previewSize,
        showLabels: showLabels,
        showConfidence: showConfidence,
      ),
      size: previewSize,
    );
  }
}

/// Custom painter for drawing detection boxes
class DetectionPainter extends CustomPainter {
  final List<Detection> detections;
  final Size previewSize;
  final bool showLabels;
  final bool showConfidence;

  DetectionPainter({
    required this.detections,
    required this.previewSize,
    required this.showLabels,
    required this.showConfidence,
  });

  @override
  void paint(Canvas canvas, Size size) {
    for (final detection in detections) {
      _drawDetection(canvas, size, detection);
    }
  }

  void _drawDetection(Canvas canvas, Size size, Detection detection) {
    // Convert normalized coordinates to screen coordinates
    final coords = detection.toAbsolute(
      size.width.toInt(),
      size.height.toInt(),
    );

    final left = coords['left']!;
    final top = coords['top']!;
    final right = coords['right']!;
    final bottom = coords['bottom']!;

    // Get color for this class
    final color = _getColorForClass(detection.classId);

    // Draw bounding box
    final boxPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0;

    final rect = Rect.fromLTRB(left, top, right, bottom);
    canvas.drawRect(rect, boxPaint);

    // Draw label background
    if (showLabels || showConfidence) {
      final label = _buildLabel(detection);
      final textSpan = TextSpan(
        text: label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontWeight: FontWeight.bold,
        ),
      );

      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();

      // Draw label background
      final labelPadding = 4.0;
      final labelRect = Rect.fromLTWH(
        left,
        top - textPainter.height - labelPadding * 2,
        textPainter.width + labelPadding * 2,
        textPainter.height + labelPadding * 2,
      );

      final labelPaint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;

      canvas.drawRect(labelRect, labelPaint);

      // Draw label text
      textPainter.paint(
        canvas,
        Offset(left + labelPadding, top - textPainter.height - labelPadding),
      );
    }

    // Draw corner markers for better visibility
    _drawCornerMarkers(canvas, rect, color);
  }

  void _drawCornerMarkers(Canvas canvas, Rect rect, Color color) {
    final markerLength = 15.0;
    final markerPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4.0
      ..strokeCap = StrokeCap.round;

    // Top-left
    canvas.drawLine(
      Offset(rect.left, rect.top),
      Offset(rect.left + markerLength, rect.top),
      markerPaint,
    );
    canvas.drawLine(
      Offset(rect.left, rect.top),
      Offset(rect.left, rect.top + markerLength),
      markerPaint,
    );

    // Top-right
    canvas.drawLine(
      Offset(rect.right, rect.top),
      Offset(rect.right - markerLength, rect.top),
      markerPaint,
    );
    canvas.drawLine(
      Offset(rect.right, rect.top),
      Offset(rect.right, rect.top + markerLength),
      markerPaint,
    );

    // Bottom-left
    canvas.drawLine(
      Offset(rect.left, rect.bottom),
      Offset(rect.left + markerLength, rect.bottom),
      markerPaint,
    );
    canvas.drawLine(
      Offset(rect.left, rect.bottom),
      Offset(rect.left, rect.bottom - markerLength),
      markerPaint,
    );

    // Bottom-right
    canvas.drawLine(
      Offset(rect.right, rect.bottom),
      Offset(rect.right - markerLength, rect.bottom),
      markerPaint,
    );
    canvas.drawLine(
      Offset(rect.right, rect.bottom),
      Offset(rect.right, rect.bottom - markerLength),
      markerPaint,
    );
  }

  String _buildLabel(Detection detection) {
    final parts = <String>[];

    if (showLabels) {
      parts.add(detection.className);
    }

    if (showConfidence) {
      parts.add('${(detection.confidence * 100).toStringAsFixed(0)}%');
    }

    return parts.join(' ');
  }

  Color _getColorForClass(int classId) {
    // Generate consistent color for each class
    final hue = (classId * 137.5) % 360; // Golden angle for good distribution
    return HSVColor.fromAHSV(1.0, hue, 0.8, 0.9).toColor();
  }

  @override
  bool shouldRepaint(DetectionPainter oldDelegate) {
    return detections != oldDelegate.detections ||
        previewSize != oldDelegate.previewSize;
  }
}

/// Detection statistics widget
class DetectionStats extends StatelessWidget {
  final List<Detection> detections;
  final double fps;
  final String? error;

  const DetectionStats({
    super.key,
    required this.detections,
    required this.fps,
    this.error,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.7),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // FPS counter
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.speed,
                color: _getFpsColor(),
                size: 16,
              ),
              const SizedBox(width: 6),
              Text(
                'FPS: ${fps.toStringAsFixed(1)}',
                style: TextStyle(
                  color: _getFpsColor(),
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Detection count
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.analytics_outlined,
                color: Colors.white,
                size: 16,
              ),
              const SizedBox(width: 6),
              Text(
                'Detections: ${detections.length}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),

          // Error message
          if (error != null) ...[
            const SizedBox(height: 8),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.error_outline,
                  color: Colors.red,
                  size: 16,
                ),
                const SizedBox(width: 6),
                Flexible(
                  child: Text(
                    error!,
                    style: const TextStyle(
                      color: Colors.red,
                      fontSize: 12,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ],

          // Class breakdown
          if (detections.isNotEmpty) ...[
            const SizedBox(height: 8),
            const Divider(color: Colors.white24, height: 1),
            const SizedBox(height: 8),
            ..._buildClassBreakdown(),
          ],
        ],
      ),
    );
  }

  List<Widget> _buildClassBreakdown() {
    final Map<String, int> classCounts = {};
    for (final detection in detections) {
      classCounts[detection.className] =
          (classCounts[detection.className] ?? 0) + 1;
    }

    return classCounts.entries
        .map((entry) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _getColorForClass(entry.key),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '${entry.key}: ${entry.value}',
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ))
        .toList();
  }

  Color _getFpsColor() {
    if (fps >= 20) return Colors.green;
    if (fps >= 10) return Colors.orange;
    return Colors.red;
  }

  Color _getColorForClass(String className) {
    final hue = (className.hashCode % 360).toDouble();
    return HSVColor.fromAHSV(1.0, hue, 0.8, 0.9).toColor();
  }
}
