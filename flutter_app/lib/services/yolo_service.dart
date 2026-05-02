import 'dart:io';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';

/// Bounding box class for compatibility
class BBox {
  final double left;
  final double top;
  final double right;
  final double bottom;

  BBox({required this.left, required this.top, required this.right, required this.bottom});
}

/// Detection result containing bounding box and class information
class DetectionResult {
  final double x; // Center X (0-1)
  final double y; // Center Y (0-1)
  final double width; // Width (0-1)
  final double height; // Height (0-1)
  final double confidence;
  final int classId;
  final String className;

  // Compatibility aliases
  String get label => className;
  Color get color => _getClassColor(classId);

  DetectionResult({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
    required this.confidence,
    required this.classId,
    required this.className,
  });

  /// Convert to absolute coordinates
  Map<String, double> toAbsolute(int imageWidth, int imageHeight) {
    return {
      'left': (x - width / 2) * imageWidth,
      'top': (y - height / 2) * imageHeight,
      'right': (x + width / 2) * imageWidth,
      'bottom': (y + height / 2) * imageHeight,
    };
  }

  /// Get bounding box in absolute coordinates (alias for compatibility)
  BBox get bbox => BBox(
    left: x - width / 2,
    top: y - height / 2,
    right: x + width / 2,
    bottom: y + height / 2,
  );

  /// Get color for this class
  static Color _getClassColor(int classId) {
    final colors = [
      Color(0xFFFF3838), Color(0xFFFF9D97), Color(0xFFFF701F), Color(0xFFFFB21D),
      Color(0xFFCFF231), Color(0xFF48F90A), Color(0xFF92CC17), Color(0xFF3DDB86),
      Color(0xFF1A9334), Color(0xFF00D4BB), Color(0xFF2C99A8), Color(0xFF00C2FF),
      Color(0xFF344593), Color(0xFF6473FF), Color(0xFF0018EC), Color(0xFF8438FF),
      Color(0xFF520085), Color(0xFFCB38FF), Color(0xFFFF95C8), Color(0xFFFF37C7),
    ];
    return colors[classId % colors.length];
  }

  @override
  String toString() {
    return 'DetectionResult(class: $className, conf: ${(confidence * 100).toStringAsFixed(1)}%)';
  }
}

/// YOLO inference service using TFLite
class YoloService {
  Interpreter? _interpreter;
  List<String> _labels = [];
  bool _isInitialized = false;

  // True when output shape is [1, 4+N, 8400] (YOLOv8/v11 column-major)
  // False when output shape is [1, 8400, 5+N] (YOLOv5 row-major)
  bool _isYolov8Format = false;

  // Model configuration
  static const int inputSize = 640;
  static const double confidenceThreshold = 0.5;
  static const double iouThreshold = 0.45;

  bool get isInitialized => _isInitialized;
  List<String> get labels => _labels;

  /// Initialize the YOLO model from a filesystem path.
  Future<void> initialize({
    required String modelPath,
    List<String>? labels,
  }) async {
    try {
      // Load model from file (not a bundled asset)
      _interpreter = await Interpreter.fromFile(File(modelPath));

      // Detect output format from tensor shape
      final outputShape = _interpreter!.getOutputTensor(0).shape;
      // YOLOv8/v11: [1, features, 8400] → features dimension is smaller
      // YOLOv5:     [1, 8400, 5+classes] → detections dimension comes first
      _isYolov8Format = outputShape.length == 3 && outputShape[1] < outputShape[2];

      // Load labels: explicit list > txt file alongside model > empty
      if (labels != null) {
        _labels = labels;
      } else {
        _labels = await _loadLabelsFromFile(modelPath);
      }

      _isInitialized = true;
      print('YOLO model initialized: $_isYolov8Format ? YOLOv8 : YOLOv5 format');
      print('Input shape: ${_interpreter!.getInputTensor(0).shape}');
      print('Output shape: $outputShape');
      print('Labels (${_labels.length}): $_labels');
    } catch (e) {
      print('Failed to initialize YOLO model: $e');
      rethrow;
    }
  }

  /// Try to load labels from a .txt file next to the model file.
  Future<List<String>> _loadLabelsFromFile(String modelPath) async {
    final base = modelPath.replaceAll(RegExp(r'\.[^.]+$'), '');
    for (final candidate in ['$base.txt', '${File(modelPath).parent.path}/labels.txt']) {
      final f = File(candidate);
      if (await f.exists()) {
        final lines = await f.readAsLines();
        final loaded = lines.map((l) => l.trim()).where((l) => l.isNotEmpty).toList();
        if (loaded.isNotEmpty) {
          print('Loaded ${loaded.length} labels from $candidate');
          return loaded;
        }
      }
    }
    print('No label file found alongside $modelPath; class indices will be shown');
    return [];
  }

  /// Alias for initialize() - for backward compatibility
  Future<void> loadModel(String modelPath, {List<String>? labels}) async {
    return initialize(modelPath: modelPath, labels: labels);
  }

  /// Alias for detectFromCamera() - for backward compatibility
  Future<List<DetectionResult>> detectObjects(CameraImage cameraImage, {double? confidenceThreshold}) async {
    return detectFromCamera(cameraImage, confidenceThreshold: confidenceThreshold);
  }

  /// Run inference on camera frame
  Future<List<DetectionResult>> detectFromCamera(CameraImage cameraImage, {double? confidenceThreshold}) async {
    if (!_isInitialized || _interpreter == null) {
      throw Exception('YOLO model not initialized');
    }

    try {
      final image = _convertCameraImage(cameraImage);
      if (image == null) return [];

      final resized = img.copyResize(
        image,
        width: inputSize,
        height: inputSize,
        interpolation: img.Interpolation.linear,
      );

      final input = _preprocessImage(resized);
      final output = await _runInference(input);
      return _postprocessOutput(output, confidenceThreshold ?? YoloService.confidenceThreshold);
    } catch (e) {
      print('Detection error: $e');
      return [];
    }
  }

  /// Run inference on image file
  Future<List<DetectionResult>> detectFromFile(String imagePath, {double? confidenceThreshold}) async {
    if (!_isInitialized || _interpreter == null) {
      throw Exception('YOLO model not initialized');
    }

    try {
      final bytes = await File(imagePath).readAsBytes();
      final image = img.decodeImage(bytes);
      if (image == null) throw Exception('Failed to decode image');

      final resized = img.copyResize(
        image,
        width: inputSize,
        height: inputSize,
        interpolation: img.Interpolation.linear,
      );

      final input = _preprocessImage(resized);
      final output = await _runInference(input);
      return _postprocessOutput(output, confidenceThreshold ?? YoloService.confidenceThreshold);
    } catch (e) {
      print('Detection error: $e');
      rethrow;
    }
  }

  /// Convert CameraImage to Image
  img.Image? _convertCameraImage(CameraImage cameraImage) {
    try {
      if (cameraImage.format.group == ImageFormatGroup.yuv420) {
        return _convertYUV420ToImage(cameraImage);
      } else if (cameraImage.format.group == ImageFormatGroup.bgra8888) {
        return _convertBGRA8888ToImage(cameraImage);
      }
      return null;
    } catch (e) {
      print('Error converting camera image: $e');
      return null;
    }
  }

  /// Convert YUV420 to RGB
  img.Image _convertYUV420ToImage(CameraImage cameraImage) {
    final int width = cameraImage.width;
    final int height = cameraImage.height;
    final img.Image image = img.Image(width: width, height: height);

    final int uvRowStride = cameraImage.planes[1].bytesPerRow;
    final int uvPixelStride = cameraImage.planes[1].bytesPerPixel ?? 1;

    for (int y = 0; y < height; y++) {
      for (int x = 0; x < width; x++) {
        final int uvIndex =
            uvPixelStride * (x / 2).floor() + uvRowStride * (y / 2).floor();
        final int index = y * width + x;

        final yp = cameraImage.planes[0].bytes[index];
        final up = cameraImage.planes[1].bytes[uvIndex];
        final vp = cameraImage.planes[2].bytes[uvIndex];

        int r = (yp + vp * 1436 / 1024 - 179).round().clamp(0, 255);
        int g = (yp - up * 46549 / 131072 + 44 - vp * 93604 / 131072 + 91)
            .round()
            .clamp(0, 255);
        int b = (yp + up * 1814 / 1024 - 227).round().clamp(0, 255);

        image.setPixelRgb(x, y, r, g, b);
      }
    }

    return image;
  }

  /// Convert BGRA8888 to RGB
  img.Image _convertBGRA8888ToImage(CameraImage cameraImage) {
    return img.Image.fromBytes(
      width: cameraImage.width,
      height: cameraImage.height,
      bytes: cameraImage.planes[0].bytes.buffer,
      order: img.ChannelOrder.bgra,
    );
  }

  /// Preprocess image to model input format
  Float32List _preprocessImage(img.Image image) {
    final input = Float32List(1 * inputSize * inputSize * 3);
    int pixelIndex = 0;

    for (int y = 0; y < inputSize; y++) {
      for (int x = 0; x < inputSize; x++) {
        final pixel = image.getPixel(x, y);
        input[pixelIndex++] = pixel.r / 255.0;
        input[pixelIndex++] = pixel.g / 255.0;
        input[pixelIndex++] = pixel.b / 255.0;
      }
    }

    return input;
  }

  /// Run inference and return raw output as [rows][cols].
  ///
  /// For YOLOv8 [1, features, 8400] the returned list is [features][8400].
  /// For YOLOv5 [1, 8400, 5+N]   the returned list is [8400][5+N].
  Future<List<List<double>>> _runInference(Float32List input) async {
    final inputTensor = input.reshape([1, inputSize, inputSize, 3]);

    final outputShape = _interpreter!.getOutputTensor(0).shape;
    final dim1 = outputShape[1];
    final dim2 = outputShape[2];

    final output = List.generate(
      1,
      (_) => List.generate(dim1, (_) => List<double>.filled(dim2, 0.0)),
    );

    _interpreter!.run(inputTensor, output);

    return output[0]; // [dim1][dim2]
  }

  /// Postprocess model output to detections.
  ///
  /// Handles both:
  ///   YOLOv8/v11: output[features][detections] → features = 4 + num_classes, no objectness
  ///   YOLOv5:     output[detections][5+classes] → col 4 is objectness score
  List<DetectionResult> _postprocessOutput(
    List<List<double>> output,
    double threshold,
  ) {
    final List<DetectionResult> detections = [];

    if (_isYolov8Format) {
      // output is [4+numClasses][8400]
      final int numFeatures = output.length;       // 4 + numClasses
      final int numDetections = output[0].length;  // 8400
      final int numClasses = numFeatures - 4;

      for (int d = 0; d < numDetections; d++) {
        // Find best class
        int bestClass = 0;
        double bestScore = output[4][d];
        for (int c = 1; c < numClasses; c++) {
          final s = output[4 + c][d];
          if (s > bestScore) {
            bestScore = s;
            bestClass = c;
          }
        }

        if (bestScore < threshold) continue;

        detections.add(DetectionResult(
          x: output[0][d],
          y: output[1][d],
          width: output[2][d],
          height: output[3][d],
          confidence: bestScore,
          classId: bestClass,
          className: bestClass < _labels.length ? _labels[bestClass] : 'class_$bestClass',
        ));
      }
    } else {
      // YOLOv5: output is [8400][5+numClasses]
      for (final det in output) {
        final objectness = det[4];
        if (objectness < threshold) continue;

        int bestClass = 0;
        double bestProb = det[5];
        for (int i = 6; i < det.length; i++) {
          if (det[i] > bestProb) {
            bestProb = det[i];
            bestClass = i - 5;
          }
        }

        final finalConf = objectness * bestProb;
        if (finalConf < threshold) continue;

        detections.add(DetectionResult(
          x: det[0],
          y: det[1],
          width: det[2],
          height: det[3],
          confidence: finalConf,
          classId: bestClass,
          className: bestClass < _labels.length ? _labels[bestClass] : 'class_$bestClass',
        ));
      }
    }

    return _nonMaximumSuppression(detections);
  }

  /// Apply Non-Maximum Suppression to remove overlapping boxes
  List<DetectionResult> _nonMaximumSuppression(List<DetectionResult> detections) {
    detections.sort((a, b) => b.confidence.compareTo(a.confidence));

    final List<DetectionResult> result = [];

    while (detections.isNotEmpty) {
      final current = detections.removeAt(0);
      result.add(current);

      detections.removeWhere((detection) {
        final iou = _calculateIoU(current, detection);
        return iou > iouThreshold;
      });
    }

    return result;
  }

  /// Calculate Intersection over Union
  double _calculateIoU(DetectionResult a, DetectionResult b) {
    final aLeft = a.x - a.width / 2;
    final aTop = a.y - a.height / 2;
    final aRight = a.x + a.width / 2;
    final aBottom = a.y + a.height / 2;

    final bLeft = b.x - b.width / 2;
    final bTop = b.y - b.height / 2;
    final bRight = b.x + b.width / 2;
    final bBottom = b.y + b.height / 2;

    final interLeft = aLeft > bLeft ? aLeft : bLeft;
    final interTop = aTop > bTop ? aTop : bTop;
    final interRight = aRight < bRight ? aRight : bRight;
    final interBottom = aBottom < bBottom ? aBottom : bBottom;

    if (interRight < interLeft || interBottom < interTop) return 0.0;

    final interArea = (interRight - interLeft) * (interBottom - interTop);
    final aArea = a.width * a.height;
    final bArea = b.width * b.height;
    final unionArea = aArea + bArea - interArea;

    return interArea / unionArea;
  }

  /// Dispose resources
  void dispose() {
    _interpreter?.close();
    _interpreter = null;
    _isInitialized = false;
  }
}
