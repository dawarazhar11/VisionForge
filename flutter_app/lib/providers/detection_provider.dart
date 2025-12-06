import 'package:flutter/foundation.dart';
import 'package:camera/camera.dart';
import '../services/yolo_service.dart';

/// Detection state provider
class DetectionProvider with ChangeNotifier {
  final YoloService _yoloService = YoloService();

  List<DetectionResult> _detections = [];
  bool _isInitialized = false;
  bool _isProcessing = false;
  String? _error;
  double _fps = 0.0;
  int _frameCount = 0;
  DateTime? _lastFpsUpdate;

  List<DetectionResult> get detections => _detections;
  bool get isInitialized => _isInitialized;
  bool get isProcessing => _isProcessing;
  String? get error => _error;
  double get fps => _fps;

  /// Initialize YOLO model
  Future<void> initialize({
    required String modelPath,
    List<String>? labels,
  }) async {
    try {
      _error = null;
      notifyListeners();

      await _yoloService.loadModel(modelPath);

      _isInitialized = true;
      _lastFpsUpdate = DateTime.now();
      notifyListeners();
    } catch (e) {
      _error = 'Failed to initialize YOLO: $e';
      _isInitialized = false;
      notifyListeners();
      rethrow;
    }
  }

  /// Process camera frame for detection
  Future<void> processFrame(CameraImage cameraImage) async {
    if (!_isInitialized || _isProcessing) {
      return;
    }

    _isProcessing = true;

    try {
      // Run detection
      final results = await _yoloService.detectObjects(
        cameraImage,
        confidenceThreshold: 0.25,
      );

      // Update detections
      _detections = results;

      // Update FPS
      _updateFps();

      _error = null;
    } catch (e) {
      _error = 'Detection error: $e';
      print(_error);
    } finally {
      _isProcessing = false;
      notifyListeners();
    }
  }

  /// Process image file for detection
  Future<List<DetectionResult>> processImage(String imagePath) async {
    if (!_isInitialized) {
      throw Exception('YOLO model not initialized');
    }

    try {
      _error = null;
      notifyListeners();

      // Note: detectFromFile method needs to be implemented in YoloService
      // For now, this is a placeholder
      _detections = [];

      notifyListeners();
      return _detections;
    } catch (e) {
      _error = 'Failed to process image: $e';
      notifyListeners();
      rethrow;
    }
  }

  /// Update FPS counter
  void _updateFps() {
    _frameCount++;

    final now = DateTime.now();
    if (_lastFpsUpdate != null) {
      final elapsed = now.difference(_lastFpsUpdate!).inMilliseconds;

      // Update FPS every second
      if (elapsed >= 1000) {
        _fps = (_frameCount * 1000) / elapsed;
        _frameCount = 0;
        _lastFpsUpdate = now;
      }
    } else {
      _lastFpsUpdate = now;
    }
  }

  /// Clear detections
  void clearDetections() {
    _detections = [];
    notifyListeners();
  }

  /// Clear error message
  void clearError() {
    _error = null;
    notifyListeners();
  }

  /// Get model labels
  List<String> get labels => _yoloService.labels;

  /// Dispose resources
  @override
  void dispose() {
    _yoloService.dispose();
    super.dispose();
  }
}
