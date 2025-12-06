import 'dart:io';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';

/// Detection result containing bounding box and class information
class Detection {
  final double x; // Center X (0-1)
  final double y; // Center Y (0-1)
  final double width; // Width (0-1)
  final double height; // Height (0-1)
  final double confidence;
  final int classId;
  final String className;

  Detection({
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

  @override
  String toString() {
    return 'Detection(class: $className, conf: ${(confidence * 100).toStringAsFixed(1)}%)';
  }
}

/// YOLO inference service using TFLite
class YoloService {
  Interpreter? _interpreter;
  List<String> _labels = [];
  bool _isInitialized = false;

  // Model configuration
  static const int inputSize = 640;
  static const double confidenceThreshold = 0.5;
  static const double iouThreshold = 0.45;

  bool get isInitialized => _isInitialized;
  List<String> get labels => _labels;

  /// Initialize the YOLO model
  Future<void> initialize({
    required String modelPath,
    List<String>? labels,
  }) async {
    try {
      // Load model
      _interpreter = await Interpreter.fromAsset(modelPath);

      // Load labels
      if (labels != null) {
        _labels = labels;
      } else {
        // Default COCO labels (you should replace with your actual labels)
        _labels = _getDefaultLabels();
      }

      _isInitialized = true;
      print('YOLO model initialized successfully');
      print('Input shape: ${_interpreter!.getInputTensor(0).shape}');
      print('Output shape: ${_interpreter!.getOutputTensor(0).shape}');
    } catch (e) {
      print('Failed to initialize YOLO model: $e');
      rethrow;
    }
  }

  /// Run inference on camera frame
  Future<List<Detection>> detectFromCamera(CameraImage cameraImage) async {
    if (!_isInitialized || _interpreter == null) {
      throw Exception('YOLO model not initialized');
    }

    try {
      // Convert CameraImage to Image
      final image = _convertCameraImage(cameraImage);
      if (image == null) {
        return [];
      }

      // Resize to input size
      final resized = img.copyResize(
        image,
        width: inputSize,
        height: inputSize,
        interpolation: img.Interpolation.linear,
      );

      // Preprocess image
      final input = _preprocessImage(resized);

      // Run inference
      final output = await _runInference(input);

      // Postprocess results
      final detections = _postprocessOutput(output);

      return detections;
    } catch (e) {
      print('Detection error: $e');
      return [];
    }
  }

  /// Run inference on image file
  Future<List<Detection>> detectFromFile(String imagePath) async {
    if (!_isInitialized || _interpreter == null) {
      throw Exception('YOLO model not initialized');
    }

    try {
      // Load and decode image
      final bytes = await File(imagePath).readAsBytes();
      final image = img.decodeImage(bytes);
      if (image == null) {
        throw Exception('Failed to decode image');
      }

      // Resize to input size
      final resized = img.copyResize(
        image,
        width: inputSize,
        height: inputSize,
        interpolation: img.Interpolation.linear,
      );

      // Preprocess image
      final input = _preprocessImage(resized);

      // Run inference
      final output = await _runInference(input);

      // Postprocess results
      final detections = _postprocessOutput(output);

      return detections;
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

        // Normalize to [0, 1] and convert to RGB order
        input[pixelIndex++] = pixel.r / 255.0;
        input[pixelIndex++] = pixel.g / 255.0;
        input[pixelIndex++] = pixel.b / 255.0;
      }
    }

    return input;
  }

  /// Run inference
  Future<List<List<double>>> _runInference(Float32List input) async {
    // Reshape input
    final inputTensor = input.reshape([1, inputSize, inputSize, 3]);

    // Prepare output buffer
    // YOLO output shape: [1, num_detections, 85] for COCO
    // [x, y, w, h, confidence, class0_prob, class1_prob, ...]
    final outputShape = _interpreter!.getOutputTensor(0).shape;
    final numDetections = outputShape[1];
    final numValues = outputShape[2];

    final output = List.generate(
      1,
      (_) => List.generate(
        numDetections,
        (_) => List<double>.filled(numValues, 0.0),
      ),
    );

    // Run inference
    _interpreter!.run(inputTensor, output);

    return output[0];
  }

  /// Postprocess model output to detections
  List<Detection> _postprocessOutput(List<List<double>> output) {
    final List<Detection> detections = [];

    for (final detection in output) {
      // YOLO output format: [x, y, w, h, confidence, class_probs...]
      final confidence = detection[4];

      if (confidence < confidenceThreshold) {
        continue;
      }

      // Find class with highest probability
      int classId = 0;
      double maxProb = detection[5];
      for (int i = 6; i < detection.length; i++) {
        if (detection[i] > maxProb) {
          maxProb = detection[i];
          classId = i - 5;
        }
      }

      // Final confidence = objectness * class_probability
      final finalConfidence = confidence * maxProb;

      if (finalConfidence < confidenceThreshold) {
        continue;
      }

      detections.add(Detection(
        x: detection[0],
        y: detection[1],
        width: detection[2],
        height: detection[3],
        confidence: finalConfidence,
        classId: classId,
        className: classId < _labels.length ? _labels[classId] : 'unknown',
      ));
    }

    // Apply Non-Maximum Suppression
    return _nonMaximumSuppression(detections);
  }

  /// Apply Non-Maximum Suppression to remove overlapping boxes
  List<Detection> _nonMaximumSuppression(List<Detection> detections) {
    // Sort by confidence (descending)
    detections.sort((a, b) => b.confidence.compareTo(a.confidence));

    final List<Detection> result = [];

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
  double _calculateIoU(Detection a, Detection b) {
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

    if (interRight < interLeft || interBottom < interTop) {
      return 0.0;
    }

    final interArea = (interRight - interLeft) * (interBottom - interTop);
    final aArea = a.width * a.height;
    final bArea = b.width * b.height;
    final unionArea = aArea + bArea - interArea;

    return interArea / unionArea;
  }

  /// Get default COCO labels
  List<String> _getDefaultLabels() {
    return [
      'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train',
      'truck', 'boat', 'traffic light', 'fire hydrant', 'stop sign',
      'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
      'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag',
      'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
      'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
      'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon',
      'bowl', 'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot',
      'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant',
      'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
      'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
      'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
      'hair drier', 'toothbrush'
    ];
  }

  /// Dispose resources
  void dispose() {
    _interpreter?.close();
    _interpreter = null;
    _isInitialized = false;
  }
}
