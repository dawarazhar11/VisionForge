import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:path_provider/path_provider.dart';
import '../services/yolo_service.dart';

class DetectionScreen extends StatefulWidget {
  const DetectionScreen({super.key});

  @override
  State<DetectionScreen> createState() => _DetectionScreenState();
}

class _DetectionScreenState extends State<DetectionScreen> {
  CameraController? _cameraController;
  List<CameraDescription>? _cameras;
  bool _isInitialized = false;
  bool _isDetecting = false;
  String? _error;

  // Detection state
  List<DetectionResult> _detections = [];
  double _confidenceThreshold = 0.25;
  int _fps = 0;
  DateTime? _lastFrameTime;

  // YOLO service
  YoloService? _yoloService;
  String? _activeModelPath;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      // Get available cameras
      _cameras = await availableCameras();

      if (_cameras == null || _cameras!.isEmpty) {
        setState(() {
          _error = 'No cameras found';
        });
        return;
      }

      // Load active model path
      final prefs = await SharedPreferences.getInstance();
      _activeModelPath = prefs.getString('active_model_path');

      if (_activeModelPath == null || !File(_activeModelPath!).existsSync()) {
        setState(() {
          _error = 'No active model selected. Please download and activate a model first.';
        });
        return;
      }

      // Initialize YOLO service
      _yoloService = YoloService();
      await _yoloService!.loadModel(_activeModelPath!);

      // Initialize camera controller
      _cameraController = CameraController(
        _cameras![0],
        ResolutionPreset.high,
        enableAudio: false,
      );

      await _cameraController!.initialize();

      // Start image stream for detection
      _cameraController!.startImageStream((CameraImage image) {
        if (!_isDetecting) {
          _isDetecting = true;
          _runDetection(image);
        }
      });

      setState(() {
        _isInitialized = true;
      });
    } catch (e) {
      setState(() {
        _error = 'Camera initialization failed: $e';
      });
    }
  }

  Future<void> _runDetection(CameraImage image) async {
    try {
      // Calculate FPS
      final now = DateTime.now();
      if (_lastFrameTime != null) {
        final elapsed = now.difference(_lastFrameTime!).inMilliseconds;
        if (elapsed > 0) {
          setState(() {
            _fps = (1000 / elapsed).round();
          });
        }
      }
      _lastFrameTime = now;

      // Run YOLO inference
      final results = await _yoloService!.detectObjects(
        image,
        confidenceThreshold: _confidenceThreshold,
      );

      setState(() {
        _detections = results;
      });
    } catch (e) {
      debugPrint('Detection error: $e');
    } finally {
      _isDetecting = false;
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _yoloService?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Live Detection'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showSettings,
          ),
        ],
      ),
      body: _error != null
          ? _buildError()
          : !_isInitialized
              ? const Center(child: CircularProgressIndicator())
              : _buildDetectionView(),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () {
                Navigator.of(context).pushReplacementNamed('/models');
              },
              icon: const Icon(Icons.download),
              label: const Text('Go to Models'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetectionView() {
    return Column(
      children: [
        // Camera preview with bounding boxes
        Expanded(
          child: Stack(
            children: [
              // Camera preview
              Center(
                child: AspectRatio(
                  aspectRatio: _cameraController!.value.aspectRatio,
                  child: CameraPreview(_cameraController!),
                ),
              ),
              // Bounding boxes overlay
              Center(
                child: AspectRatio(
                  aspectRatio: _cameraController!.value.aspectRatio,
                  child: CustomPaint(
                    painter: BoundingBoxPainter(
                      detections: _detections,
                      imageSize: Size(
                        _cameraController!.value.previewSize!.height,
                        _cameraController!.value.previewSize!.width,
                      ),
                    ),
                  ),
                ),
              ),
              // FPS counter
              Positioned(
                top: 16,
                right: 16,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.7),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '$_fps FPS',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
              // Detection count
              Positioned(
                top: 16,
                left: 16,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.7),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${_detections.length} objects',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        // Controls
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.grey[100],
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 8,
                offset: const Offset(0, -2),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text(
                    'Confidence:',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(width: 8),
                  Text('${(_confidenceThreshold * 100).toInt()}%'),
                  Expanded(
                    child: Slider(
                      value: _confidenceThreshold,
                      min: 0.1,
                      max: 0.9,
                      divisions: 8,
                      onChanged: (value) {
                        setState(() {
                          _confidenceThreshold = value;
                        });
                      },
                    ),
                  ),
                ],
              ),
              // Detection list
              if (_detections.isNotEmpty) ...[
                const Divider(),
                const Text(
                  'Detections:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  height: 80,
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: _detections.length,
                    itemBuilder: (context, index) {
                      final detection = _detections[index];
                      return Card(
                        margin: const EdgeInsets.only(right: 8),
                        child: Padding(
                          padding: const EdgeInsets.all(8),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                detection.label,
                                style: const TextStyle(fontWeight: FontWeight.bold),
                              ),
                              Text(
                                '${(detection.confidence * 100).toInt()}%',
                                style: TextStyle(
                                  color: Colors.grey[600],
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  void _showSettings() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Detection Settings'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.model_training),
              title: const Text('Active Model'),
              subtitle: Text(_activeModelPath?.split(Platform.pathSeparator).last ?? 'None'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                Navigator.of(context).pop();
                Navigator.of(context).pushNamed('/models');
              },
            ),
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('Model Info'),
              subtitle: Text('FPS: $_fps'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}

class BoundingBoxPainter extends CustomPainter {
  final List<DetectionResult> detections;
  final Size imageSize;

  BoundingBoxPainter({
    required this.detections,
    required this.imageSize,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0;

    final textPainter = TextPainter(
      textDirection: TextDirection.ltr,
      textAlign: TextAlign.left,
    );

    for (var detection in detections) {
      // Scale bounding box to screen size
      final scaleX = size.width / imageSize.width;
      final scaleY = size.height / imageSize.height;

      final left = detection.bbox.left * scaleX;
      final top = detection.bbox.top * scaleY;
      final right = detection.bbox.right * scaleX;
      final bottom = detection.bbox.bottom * scaleY;

      final rect = Rect.fromLTRB(left, top, right, bottom);

      // Draw bounding box
      paint.color = detection.color;
      canvas.drawRect(rect, paint);

      // Draw label background
      final labelText = '${detection.label} ${(detection.confidence * 100).toInt()}%';
      textPainter.text = TextSpan(
        text: labelText,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontWeight: FontWeight.bold,
        ),
      );
      textPainter.layout();

      final labelRect = Rect.fromLTWH(
        left,
        top - textPainter.height - 4,
        textPainter.width + 8,
        textPainter.height + 4,
      );

      canvas.drawRect(
        labelRect,
        Paint()..color = detection.color,
      );

      // Draw label text
      textPainter.paint(canvas, Offset(left + 4, top - textPainter.height - 2));
    }
  }

  @override
  bool shouldRepaint(BoundingBoxPainter oldDelegate) {
    return oldDelegate.detections != detections;
  }
}
