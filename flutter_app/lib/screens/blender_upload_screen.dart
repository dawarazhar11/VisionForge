import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'dart:io';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../models/project.dart';

class BlenderUploadScreen extends StatefulWidget {
  final Project project;

  const BlenderUploadScreen({super.key, required this.project});

  @override
  State<BlenderUploadScreen> createState() => _BlenderUploadScreenState();
}

class _BlenderUploadScreenState extends State<BlenderUploadScreen> {
  String? _blenderFilePath;
  bool _isUploading = false;
  double _uploadProgress = 0.0;

  // Rendering configuration
  int _numRenders = 100;
  int _resolutionX = 640;
  int _resolutionY = 640;
  int _samples = 64;
  bool _randomizeCamera = true;
  bool _randomizeLighting = true;

  Future<void> _selectBlenderFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['blend'],
      dialogTitle: 'Select Blender File',
    );

    if (result != null && result.files.single.path != null) {
      setState(() {
        _blenderFilePath = result.files.single.path;
      });
    }
  }

  Future<void> _uploadAndGenerate() async {
    if (_blenderFilePath == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select a Blender file first'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() {
      _isUploading = true;
      _uploadProgress = 0.0;
    });

    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final token = authProvider.accessToken;

      if (token == null) {
        throw Exception('Not authenticated');
      }

      final apiService = ApiService();

      // TODO: Implement actual Blender upload API call
      // await apiService.uploadBlenderFile(
      //   token,
      //   widget.project.id,
      //   _blenderFilePath!,
      //   numRenders: _numRenders,
      //   resolutionX: _resolutionX,
      //   resolutionY: _resolutionY,
      //   samples: _samples,
      //   randomizeCamera: _randomizeCamera,
      //   randomizeLighting: _randomizeLighting,
      //   onProgress: (uploaded, total) {
      //     setState(() {
      //       _uploadProgress = uploaded / total;
      //     });
      //   },
      // );

      // Mock upload for demonstration
      for (int i = 0; i <= 100; i++) {
        await Future.delayed(const Duration(milliseconds: 20));
        setState(() {
          _uploadProgress = i / 100;
        });
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Blender file uploaded! Synthetic dataset generation started.'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Upload failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
          _uploadProgress = 0.0;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Blender Synthetic Data'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Info Card
            Card(
              color: Colors.blue.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Icon(Icons.info_outline, color: Colors.blue.shade700),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Upload a Blender scene (.blend) to generate synthetic training data with automatic randomization and annotations.',
                        style: TextStyle(color: Colors.blue.shade900),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // File Selection
            Text(
              'Blender Scene File',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: const Icon(Icons.insert_drive_file, color: Colors.orange),
                title: Text(
                  _blenderFilePath != null
                      ? _blenderFilePath!.split(Platform.pathSeparator).last
                      : 'No file selected',
                ),
                subtitle: Text(
                  _blenderFilePath ?? 'Click to select .blend file',
                  style: const TextStyle(fontSize: 12),
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: ElevatedButton.icon(
                  onPressed: _isUploading ? null : _selectBlenderFile,
                  icon: const Icon(Icons.folder_open, size: 18),
                  label: const Text('Browse'),
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Rendering Configuration
            Text(
              'Rendering Configuration',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    // Number of Renders
                    Row(
                      children: [
                        const Expanded(
                          flex: 2,
                          child: Text('Number of Images:'),
                        ),
                        Expanded(
                          flex: 3,
                          child: Slider(
                            value: _numRenders.toDouble(),
                            min: 10,
                            max: 1000,
                            divisions: 99,
                            label: _numRenders.toString(),
                            onChanged: _isUploading ? null : (value) {
                              setState(() => _numRenders = value.toInt());
                            },
                          ),
                        ),
                        SizedBox(
                          width: 60,
                          child: Text(
                            _numRenders.toString(),
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                    const Divider(),

                    // Resolution
                    Row(
                      children: [
                        const Expanded(
                          flex: 2,
                          child: Text('Resolution:'),
                        ),
                        Expanded(
                          flex: 3,
                          child: DropdownButton<int>(
                            value: _resolutionX,
                            isExpanded: true,
                            onChanged: _isUploading ? null : (value) {
                              setState(() {
                                _resolutionX = value!;
                                _resolutionY = value;
                              });
                            },
                            items: const [
                              DropdownMenuItem(value: 320, child: Text('320x320')),
                              DropdownMenuItem(value: 416, child: Text('416x416')),
                              DropdownMenuItem(value: 640, child: Text('640x640')),
                              DropdownMenuItem(value: 1280, child: Text('1280x1280')),
                            ],
                          ),
                        ),
                        const SizedBox(width: 60),
                      ],
                    ),
                    const Divider(),

                    // Samples
                    Row(
                      children: [
                        const Expanded(
                          flex: 2,
                          child: Text('Render Quality:'),
                        ),
                        Expanded(
                          flex: 3,
                          child: Slider(
                            value: _samples.toDouble(),
                            min: 16,
                            max: 256,
                            divisions: 15,
                            label: '$_samples samples',
                            onChanged: _isUploading ? null : (value) {
                              setState(() => _samples = value.toInt());
                            },
                          ),
                        ),
                        SizedBox(
                          width: 60,
                          child: Text(
                            _samples.toString(),
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                    const Divider(),

                    // Randomization Options
                    SwitchListTile(
                      title: const Text('Randomize Camera'),
                      subtitle: const Text('Vary camera position and angle'),
                      value: _randomizeCamera,
                      onChanged: _isUploading ? null : (value) {
                        setState(() => _randomizeCamera = value);
                      },
                    ),
                    SwitchListTile(
                      title: const Text('Randomize Lighting'),
                      subtitle: const Text('Vary light intensity and color'),
                      value: _randomizeLighting,
                      onChanged: _isUploading ? null : (value) {
                        setState(() => _randomizeLighting = value);
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Estimation
            Card(
              color: Colors.grey.shade100,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Estimated Generation:',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text('Total Images: $_numRenders'),
                    Text('Resolution: ${_resolutionX}x$_resolutionY'),
                    Text('Estimated Time: ${(_numRenders * 2 / 60).toStringAsFixed(1)} minutes'),
                    Text('Estimated Size: ${(_numRenders * 0.5).toStringAsFixed(1)} MB'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Upload Progress
            if (_isUploading) ...[
              const Text(
                'Uploading...',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              LinearProgressIndicator(value: _uploadProgress),
              const SizedBox(height: 8),
              Text(
                '${(_uploadProgress * 100).toInt()}%',
                style: const TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 24),
            ],

            // Upload Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isUploading ? null : _uploadAndGenerate,
                icon: _isUploading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.cloud_upload),
                label: Text(_isUploading ? 'Uploading...' : 'Upload & Generate Dataset'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.all(16),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
