import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import '../models/project.dart';

class AnnotationScreen extends StatefulWidget {
  final Project project;

  const AnnotationScreen({super.key, required this.project});

  @override
  State<AnnotationScreen> createState() => _AnnotationScreenState();
}

class _AnnotationScreenState extends State<AnnotationScreen> {
  CameraController? _cameraController;
  List<CameraDescription>? _cameras;
  bool _isInitialized = false;
  String? _error;

  // Annotation state
  String? _capturedImagePath;
  List<BoundingBox> _annotations = [];
  String _selectedClass = 'object';
  bool _isDrawing = false;
  Offset? _drawStart;
  Offset? _drawEnd;

  final List<String> _classes = [
    'object',
    'small_screw',
    'large_screw',
    'bracket',
    'hole',
    'metal_part',
  ];

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();

      if (_cameras == null || _cameras!.isEmpty) {
        setState(() {
          _error = 'No cameras found';
        });
        return;
      }

      _cameraController = CameraController(
        _cameras![0],
        ResolutionPreset.high,
        enableAudio: false,
      );

      await _cameraController!.initialize();

      setState(() {
        _isInitialized = true;
      });
    } catch (e) {
      setState(() {
        _error = 'Camera initialization failed: $e';
      });
    }
  }

  Future<void> _captureImage() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return;
    }

    try {
      final directory = await getApplicationDocumentsDirectory();
      final imagePath = '${directory.path}/annotations/${DateTime.now().millisecondsSinceEpoch}.jpg';
      final imageFile = File(imagePath);

      // Create directory if it doesn't exist
      await imageFile.parent.create(recursive: true);

      final image = await _cameraController!.takePicture();
      await File(image.path).copy(imagePath);

      setState(() {
        _capturedImagePath = imagePath;
        _annotations.clear();
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to capture image: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _saveAnnotations() {
    if (_capturedImagePath == null || _annotations.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No annotations to save'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    // Generate YOLO format annotations
    final annotationPath = _capturedImagePath!.replaceAll('.jpg', '.txt');
    final annotationFile = File(annotationPath);

    final StringBuffer buffer = StringBuffer();
    for (final bbox in _annotations) {
      final classId = _classes.indexOf(bbox.className);
      buffer.writeln('$classId ${bbox.centerX} ${bbox.centerY} ${bbox.width} ${bbox.height}');
    }

    annotationFile.writeAsStringSync(buffer.toString());

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Saved ${_annotations.length} annotations'),
        backgroundColor: Colors.green,
      ),
    );

    // Reset for next image
    setState(() {
      _capturedImagePath = null;
      _annotations.clear();
    });
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Capture & Annotate'),
      ),
      body: _error != null
          ? _buildError()
          : !_isInitialized
              ? const Center(child: CircularProgressIndicator())
              : _capturedImagePath == null
                  ? _buildCameraView()
                  : _buildAnnotationView(),
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
          ],
        ),
      ),
    );
  }

  Widget _buildCameraView() {
    return Column(
      children: [
        Expanded(
          child: Center(
            child: AspectRatio(
              aspectRatio: _cameraController!.value.aspectRatio,
              child: CameraPreview(_cameraController!),
            ),
          ),
        ),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.black87,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.3),
                blurRadius: 8,
                offset: const Offset(0, -2),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              IconButton(
                onPressed: () {
                  if (_cameraController != null &&
                      _cameras != null &&
                      _cameras!.length > 1) {
                    // Switch camera (if multiple available)
                  }
                },
                icon: const Icon(Icons.flip_camera_ios, color: Colors.white),
                iconSize: 32,
              ),
              GestureDetector(
                onTap: _captureImage,
                child: Container(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 4),
                  ),
                  child: Container(
                    margin: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              ),
              IconButton(
                onPressed: () {},
                icon: const Icon(Icons.settings, color: Colors.white),
                iconSize: 32,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildAnnotationView() {
    return Column(
      children: [
        // Image with annotations
        Expanded(
          child: GestureDetector(
            onPanStart: (details) {
              setState(() {
                _isDrawing = true;
                _drawStart = details.localPosition;
                _drawEnd = details.localPosition;
              });
            },
            onPanUpdate: (details) {
              setState(() {
                _drawEnd = details.localPosition;
              });
            },
            onPanEnd: (details) {
              if (_drawStart != null && _drawEnd != null) {
                _addAnnotation();
              }
              setState(() {
                _isDrawing = false;
                _drawStart = null;
                _drawEnd = null;
              });
            },
            child: Container(
              color: Colors.black,
              child: Stack(
                children: [
                  // Image
                  Center(
                    child: Image.file(
                      File(_capturedImagePath!),
                      fit: BoxFit.contain,
                    ),
                  ),
                  // Existing annotations
                  ...List.generate(_annotations.length, (index) {
                    return _buildAnnotationBox(_annotations[index]);
                  }),
                  // Current drawing
                  if (_isDrawing && _drawStart != null && _drawEnd != null)
                    _buildDrawingBox(),
                ],
              ),
            ),
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
            children: [
              // Class selection
              Row(
                children: [
                  const Text(
                    'Class:',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButton<String>(
                      value: _selectedClass,
                      isExpanded: true,
                      items: _classes.map((className) {
                        return DropdownMenuItem(
                          value: className,
                          child: Text(className.replaceAll('_', ' ').toUpperCase()),
                        );
                      }).toList(),
                      onChanged: (value) {
                        setState(() => _selectedClass = value!);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Stats
              Text(
                'Annotations: ${_annotations.length}',
                style: const TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 16),

              // Action buttons
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        setState(() {
                          _capturedImagePath = null;
                          _annotations.clear();
                        });
                      },
                      icon: const Icon(Icons.camera_alt),
                      label: const Text('Recapture'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _annotations.isEmpty
                          ? null
                          : () {
                              setState(() {
                                if (_annotations.isNotEmpty) {
                                  _annotations.removeLast();
                                }
                              });
                            },
                      icon: const Icon(Icons.undo),
                      label: const Text('Undo'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: _annotations.isEmpty ? null : _saveAnnotations,
                      icon: const Icon(Icons.save),
                      label: const Text('Save'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildAnnotationBox(BoundingBox bbox) {
    return Positioned(
      left: bbox.left,
      top: bbox.top,
      child: Container(
        width: bbox.right - bbox.left,
        height: bbox.bottom - bbox.top,
        decoration: BoxDecoration(
          border: Border.all(color: bbox.color, width: 2),
        ),
        child: Align(
          alignment: Alignment.topLeft,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            color: bbox.color,
            child: Text(
              bbox.className,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDrawingBox() {
    final left = _drawStart!.dx < _drawEnd!.dx ? _drawStart!.dx : _drawEnd!.dx;
    final top = _drawStart!.dy < _drawEnd!.dy ? _drawStart!.dy : _drawEnd!.dy;
    final width = (_drawEnd!.dx - _drawStart!.dx).abs();
    final height = (_drawEnd!.dy - _drawStart!.dy).abs();

    return Positioned(
      left: left,
      top: top,
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          border: Border.all(color: Colors.green, width: 2),
        ),
      ),
    );
  }

  void _addAnnotation() {
    if (_drawStart == null || _drawEnd == null) return;

    // TODO: Calculate normalized coordinates based on actual image size
    // For now, using placeholder values
    final bbox = BoundingBox(
      className: _selectedClass,
      left: _drawStart!.dx < _drawEnd!.dx ? _drawStart!.dx : _drawEnd!.dx,
      top: _drawStart!.dy < _drawEnd!.dy ? _drawStart!.dy : _drawEnd!.dy,
      right: _drawStart!.dx > _drawEnd!.dx ? _drawStart!.dx : _drawEnd!.dx,
      bottom: _drawStart!.dy > _drawEnd!.dy ? _drawStart!.dy : _drawEnd!.dy,
      color: Colors.green,
      // Normalized coordinates (0-1) - to be calculated properly
      centerX: 0.5,
      centerY: 0.5,
      width: 0.1,
      height: 0.1,
    );

    setState(() {
      _annotations.add(bbox);
    });
  }
}

class BoundingBox {
  final String className;
  final double left;
  final double top;
  final double right;
  final double bottom;
  final Color color;
  final double centerX;
  final double centerY;
  final double width;
  final double height;

  BoundingBox({
    required this.className,
    required this.left,
    required this.top,
    required this.right,
    required this.bottom,
    required this.color,
    required this.centerX,
    required this.centerY,
    required this.width,
    required this.height,
  });
}
