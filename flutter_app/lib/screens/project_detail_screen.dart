import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import '../models/project.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import 'training_job_create_screen.dart';
import 'datasets_screen.dart';
import 'blender_upload_screen.dart';
import 'annotation_screen.dart';

class ProjectDetailScreen extends StatefulWidget {
  final Project project;

  const ProjectDetailScreen({super.key, required this.project});

  @override
  State<ProjectDetailScreen> createState() => _ProjectDetailScreenState();
}

class _ProjectDetailScreenState extends State<ProjectDetailScreen> {
  int _selectedIndex = 0;
  bool _isUploading = false;
  double _uploadProgress = 0.0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.project.name),
      ),
      body: _selectedIndex == 0
          ? _buildOverviewTab()
          : _selectedIndex == 1
              ? _buildDatasetsTab()
              : _buildTrainingTab(),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (index) => setState(() => _selectedIndex = index),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.info_outline),
            label: 'Overview',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.dataset),
            label: 'Datasets',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.model_training),
            label: 'Training',
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Project Information',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  _buildInfoRow('Name', widget.project.name),
                  _buildInfoRow('Description', widget.project.description ?? 'No description'),
                  _buildInfoRow('Created', widget.project.createdAt?.toString() ?? 'Unknown'),
                  _buildInfoRow('ID', widget.project.id),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Quick Actions',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  ListTile(
                    leading: const Icon(Icons.upload_file, color: Colors.blue),
                    title: const Text('Upload Dataset'),
                    subtitle: const Text('Add training images'),
                    trailing: _isUploading
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.chevron_right),
                    onTap: _isUploading ? null : _uploadDataset,
                  ),
                  const Divider(),
                  ListTile(
                    leading: const Icon(Icons.play_arrow, color: Colors.green),
                    title: const Text('Start Training'),
                    subtitle: const Text('Train a new model'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => TrainingJobCreateScreen(project: widget.project),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }

  Future<void> _uploadDataset() async {
    try {
      // Pick images
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['jpg', 'jpeg', 'png'],
        allowMultiple: true,
        dialogTitle: 'Select Images',
      );

      if (result == null || result.files.isEmpty) return;

      final imagePaths = result.files.map((f) => f.path!).toList();

      // Ask if user wants to select annotation files
      final hasAnnotations = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Annotations'),
          content: const Text('Do you have annotation files (.txt) for these images?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('No, Upload Images Only'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Yes, Select Annotations'),
            ),
          ],
        ),
      );

      List<String> annotationPaths = [];
      if (hasAnnotations == true) {
        final annotResult = await FilePicker.platform.pickFiles(
          type: FileType.custom,
          allowedExtensions: ['txt'],
          allowMultiple: true,
          dialogTitle: 'Select Annotation Files',
        );
        if (annotResult != null) {
          annotationPaths = annotResult.files.map((f) => f.path!).toList();
        }
      }

      setState(() {
        _isUploading = true;
        _uploadProgress = 0.0;
      });

      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final token = authProvider.accessToken!;
      final apiService = ApiService();

      await apiService.uploadDataset(
        token,
        widget.project.id,
        imagePaths,
        annotationPaths,
        onProgress: (uploaded, total) {
          setState(() {
            _uploadProgress = uploaded / total;
          });
        },
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Successfully uploaded ${imagePaths.length} images!'),
            backgroundColor: Colors.green,
          ),
        );
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

  Widget _buildDatasetsTab() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (_isUploading) ...[
            const Icon(Icons.cloud_upload, size: 64, color: Colors.blue),
            const SizedBox(height: 16),
            Text('Uploading... ${(_uploadProgress * 100).toInt()}%'),
            const SizedBox(height: 16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: LinearProgressIndicator(value: _uploadProgress),
            ),
          ] else ...[
            const Icon(Icons.dataset, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            const Text('Manage Your Datasets'),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => DatasetsScreen(project: widget.project),
                  ),
                );
              },
              icon: const Icon(Icons.folder),
              label: const Text('View Datasets'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _uploadDataset,
              icon: const Icon(Icons.upload),
              label: const Text('Upload New Dataset'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => BlenderUploadScreen(project: widget.project),
                  ),
                );
              },
              icon: const Icon(Icons.view_in_ar),
              label: const Text('Generate Synthetic Data'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => AnnotationScreen(project: widget.project),
                  ),
                );
              },
              icon: const Icon(Icons.draw),
              label: const Text('Capture & Annotate'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTrainingTab() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.model_training, size: 64, color: Colors.grey),
          const SizedBox(height: 16),
          const Text('No training jobs yet'),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => TrainingJobCreateScreen(project: widget.project),
                ),
              );
            },
            icon: const Icon(Icons.play_arrow),
            label: const Text('Start Training'),
          ),
        ],
      ),
    );
  }
}
