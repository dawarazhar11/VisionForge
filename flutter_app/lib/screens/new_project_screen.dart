import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';

import '../models/project.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'project_detail_screen.dart';

/// New Project wizard: pick any supported design file (incl. STEP),
/// upload it (creates the project), configure render, and start.
class NewProjectScreen extends StatefulWidget {
  const NewProjectScreen({super.key});

  @override
  State<NewProjectScreen> createState() => _NewProjectScreenState();
}

class _NewProjectScreenState extends State<NewProjectScreen> {
  static const _supported = ['step', 'stp', 'blend', 'obj', 'stl', 'fbx'];

  final _nameController = TextEditingController();
  String? _filePath;
  String? _fileName;

  int _numRenders = 40;
  int _resolution = 640;
  int _samples = 24;

  bool _busy = false;
  double _uploadProgress = 0;
  String _stage = '';

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    // iOS greys out unknown extensions (.step/.stp) under FileType.custom,
    // so accept any file and validate the extension ourselves.
    final result = await FilePicker.platform.pickFiles(type: FileType.any);
    if (result == null || result.files.single.path == null) return;
    final f = result.files.single;
    final ext = f.name.contains('.')
        ? f.name.split('.').last.toLowerCase()
        : '';
    if (!_supported.contains(ext)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                'Unsupported file ".$ext". Choose a STEP/STP/BLEND/OBJ/STL/FBX file.'),
          ),
        );
      }
      return;
    }
    setState(() {
      _filePath = f.path;
      _fileName = f.name;
      if (_nameController.text.trim().isEmpty) {
        _nameController.text = f.name.replaceAll(RegExp(r'\.[^.]+$'), '');
      }
    });
  }

  String? get _ext => _fileName?.split('.').last.toLowerCase();

  String get _modeHint {
    switch (_ext) {
      case 'step':
      case 'stp':
        return 'STEP — classes come from CAD part names, or feature types '
            '(hole, boss…) for a single part.';
      case 'blend':
        return '.blend — one class per named mesh object.';
      default:
        return 'Mesh file — one class per object.';
    }
  }

  Future<void> _createAndRender() async {
    final name = _nameController.text.trim();
    if (name.isEmpty || _filePath == null) return;
    final token = Provider.of<AuthProvider>(context, listen: false).accessToken;
    if (token == null) return;

    setState(() {
      _busy = true;
      _stage = 'Uploading…';
      _uploadProgress = 0;
    });

    final api = ApiService();
    try {
      final project = await api.uploadProjectFile(
        token: token,
        name: name,
        filePath: _filePath!,
        onProgress: (sent, total) {
          if (mounted && total > 0) {
            setState(() => _uploadProgress = sent / total);
          }
        },
      );
      final projectId = project['id'] as String;

      setState(() => _stage = 'Starting render…');
      await api.createJob(
        projectId: projectId,
        jobType: 'render',
        config: {
          'num_renders': _numRenders,
          'resolution_x': _resolution,
          'resolution_y': _resolution,
          'eevee_samples': _samples,
        },
      );

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => ProjectDetailScreen(
            project: Project.fromJson(project),
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final canSubmit = !_busy &&
        _filePath != null &&
        _nameController.text.trim().isNotEmpty;

    return Scaffold(
      appBar: AppBar(title: const Text('New Project')),
      body: AbsorbPointer(
        absorbing: _busy,
        child: ListView(
          padding: const EdgeInsets.all(AppTheme.s4),
          children: [
            // File picker card
            Card(
              child: InkWell(
                onTap: _pickFile,
                child: Padding(
                  padding: const EdgeInsets.all(AppTheme.s4),
                  child: Row(
                    children: [
                      Icon(
                        _filePath == null
                            ? Icons.upload_file
                            : Icons.insert_drive_file,
                        size: 36,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      const SizedBox(width: AppTheme.s4),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _fileName ?? 'Select a design file',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 2),
                            Text(
                              _filePath == null
                                  ? 'STEP, STP, BLEND, OBJ, STL, FBX'
                                  : _modeHint,
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                      if (_filePath != null)
                        TextButton(onPressed: _pickFile, child: const Text('Change')),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: AppTheme.s4),

            TextField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: 'Project name'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: AppTheme.s5),

            Text('Render settings',
                style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: AppTheme.s2),

            _stepperRow('Images', _numRenders, 10, 200, 10,
                (v) => setState(() => _numRenders = v)),
            _resolutionRow(),
            _stepperRow('EEVEE samples', _samples, 8, 96, 8,
                (v) => setState(() => _samples = v)),

            const SizedBox(height: AppTheme.s6),

            if (_busy) ...[
              LinearProgressIndicator(
                value: _stage.startsWith('Uploading') ? _uploadProgress : null,
              ),
              const SizedBox(height: AppTheme.s2),
              Text(_stage, textAlign: TextAlign.center),
              const SizedBox(height: AppTheme.s4),
            ],

            FilledButton.icon(
              onPressed: canSubmit ? _createAndRender : null,
              icon: const Icon(Icons.play_arrow),
              label: const Text('Create & Start Render'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _stepperRow(String label, int value, int min, int max, int step,
      ValueChanged<int> onChanged) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppTheme.s1),
      child: Row(
        children: [
          Expanded(child: Text(label)),
          IconButton(
            icon: const Icon(Icons.remove_circle_outline),
            onPressed: value > min ? () => onChanged(value - step) : null,
          ),
          SizedBox(
            width: 44,
            child: Text('$value', textAlign: TextAlign.center),
          ),
          IconButton(
            icon: const Icon(Icons.add_circle_outline),
            onPressed: value < max ? () => onChanged(value + step) : null,
          ),
        ],
      ),
    );
  }

  Widget _resolutionRow() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppTheme.s1),
      child: Row(
        children: [
          const Expanded(child: Text('Resolution')),
          SegmentedButton<int>(
            segments: const [
              ButtonSegment(value: 640, label: Text('640')),
              ButtonSegment(value: 960, label: Text('960')),
              ButtonSegment(value: 1280, label: Text('1280')),
            ],
            selected: {_resolution},
            onSelectionChanged: (s) => setState(() => _resolution = s.first),
          ),
        ],
      ),
    );
  }
}
