import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:provider/provider.dart';
import '../providers/detection_provider.dart';
import '../widgets/detection_overlay.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _cameraController;
  List<CameraDescription>? _cameras;
  bool _isInitialized = false;
  bool _isDetecting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
    _initializeYolo();
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();

      if (_cameras == null || _cameras!.isEmpty) {
        setState(() {
          _error = 'No cameras available';
        });
        return;
      }

      _cameraController = CameraController(
        _cameras![0],
        ResolutionPreset.high,
        enableAudio: false,
      );

      await _cameraController!.initialize();

      // Start image stream for detection
      _cameraController!.startImageStream(_processCameraImage);

      if (mounted) {
        setState(() {
          _isInitialized = true;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Failed to initialize camera: $e';
      });
    }
  }

  Future<void> _initializeYolo() async {
    final detectionProvider = Provider.of<DetectionProvider>(context, listen: false);

    try {
      // Initialize YOLO model from assets
      // Note: You need to add your trained model to assets/models/
      await detectionProvider.initialize(
        modelPath: 'assets/models/yolo_model.tflite',
        labels: _getMechanicalComponentLabels(),
      );
    } catch (e) {
      setState(() {
        _error = 'Failed to initialize YOLO: $e';
      });
    }
  }

  /// Process camera frame for detection
  void _processCameraImage(CameraImage cameraImage) {
    if (!_isDetecting) {
      _isDetecting = true;

      final detectionProvider = Provider.of<DetectionProvider>(context, listen: false);
      detectionProvider.processFrame(cameraImage).then((_) {
        _isDetecting = false;
      });
    }
  }

  /// Get mechanical component labels
  List<String> _getMechanicalComponentLabels() {
    // Replace with your actual labels from training
    return [
      'small_screw',
      'small_hole',
      'large_screw',
      'large_hole',
      'bracket',
      'metal_component',
    ];
  }

  @override
  void dispose() {
    _cameraController?.stopImageStream();
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Object Detection'),
        backgroundColor: Colors.black,
      ),
      body: _buildBody(),
      backgroundColor: Colors.black,
    );
  }

  Widget _buildBody() {
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              _error!,
              style: const TextStyle(color: Colors.white),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Go Back'),
            ),
          ],
        ),
      );
    }

    if (!_isInitialized) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    return Consumer<DetectionProvider>(
      builder: (context, detectionProvider, _) {
        // Get camera preview size for overlay scaling
        final size = MediaQuery.of(context).size;
        final cameraAspectRatio = _cameraController!.value.aspectRatio;

        return Stack(
          fit: StackFit.expand,
          children: [
            // Camera preview
            Center(
              child: AspectRatio(
                aspectRatio: cameraAspectRatio,
                child: CameraPreview(_cameraController!),
              ),
            ),

            // Detection overlay
            if (detectionProvider.isInitialized)
              Center(
                child: AspectRatio(
                  aspectRatio: cameraAspectRatio,
                  child: DetectionOverlay(
                    detections: detectionProvider.detections,
                    previewSize: Size(
                      size.width,
                      size.width / cameraAspectRatio,
                    ),
                  ),
                ),
              ),

            // Detection stats
            Positioned(
              top: 16,
              left: 16,
              child: DetectionStats(
                detections: detectionProvider.detections,
                fps: detectionProvider.fps,
                error: detectionProvider.error,
              ),
            ),

            // Model status indicator
            if (!detectionProvider.isInitialized)
              Positioned(
                top: 16,
                right: 16,
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.8),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation(Colors.white),
                        ),
                      ),
                      SizedBox(width: 8),
                      Text(
                        'Loading model...',
                        style: TextStyle(color: Colors.white, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
