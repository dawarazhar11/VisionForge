import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:dio/dio.dart';
import '../models/auth_token.dart';
import '../models/user.dart';
import '../models/project.dart';
import '../utils/api_config.dart';

/// API service for backend communication
class ApiService {
  final http.Client _client = http.Client();
  late final Dio _dio;
  AuthToken? _authToken;

  // Singleton pattern
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal() {
    // Initialize Dio with longer timeout for large file uploads
    _dio = Dio(BaseOptions(
      connectTimeout: const Duration(minutes: 5),
      receiveTimeout: const Duration(minutes: 10),
      sendTimeout: const Duration(minutes: 10),
    ));
  }

  /// Get authorization headers
  Map<String, String> get _headers {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (_authToken != null) {
      headers['Authorization'] = _authToken!.authorizationHeader;
    }

    return headers;
  }

  /// Set authentication token
  void setAuthToken(AuthToken token) {
    _authToken = token;
  }

  /// Clear authentication token
  void clearAuthToken() {
    _authToken = null;
  }

  /// Register new user
  Future<User> register({
    required String email,
    required String password,
    String? fullName,
  }) async {
    final response = await _client.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.authRegister}'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
        if (fullName != null) 'full_name': fullName,
      }),
    );

    if (response.statusCode == 201) {
      return User.fromJson(jsonDecode(response.body));
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Registration failed');
    }
  }

  /// Login user
  Future<AuthToken> login({
    required String email,
    required String password,
  }) async {
    final url = '${ApiConfig.baseUrl}${ApiConfig.authLogin}';
    print('🌐 ApiService: POST $url');
    print('🌐 ApiService: Email: $email');

    final response = await _client.post(
      Uri.parse(url),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );

    print('🌐 ApiService: Response status: ${response.statusCode}');
    print('🌐 ApiService: Response body: ${response.body}');

    if (response.statusCode == 200) {
      final token = AuthToken.fromJson(jsonDecode(response.body));
      setAuthToken(token);
      return token;
    } else {
      final error = jsonDecode(response.body);
      final errorMessage = error['detail'] ?? 'Login failed';
      print('❌ ApiService: Login error: $errorMessage');
      throw Exception(errorMessage);
    }
  }

  /// Refresh access token
  Future<AuthToken> refreshToken(String refreshToken) async {
    final response = await _client.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.authRefresh}'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'refresh_token': refreshToken,
      }),
    );

    if (response.statusCode == 200) {
      final token = AuthToken.fromJson(jsonDecode(response.body));
      setAuthToken(token);
      return token;
    } else {
      throw Exception('Token refresh failed');
    }
  }

  /// Get user projects
  Future<List<dynamic>> getProjects(String token) async {
    final response = await _client.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      // Backend returns list directly or wrapped in 'projects' key
      if (data is List) {
        return data;
      } else if (data is Map && data.containsKey('projects')) {
        return data['projects'] as List<dynamic>;
      }
      return [];
    } else {
      throw Exception('Failed to load projects');
    }
  }

  /// Create new project
  Future<Map<String, dynamic>> createProject(
    String token,
    String name,
    String? description,
  ) async {
    try {
      final response = await _client.post(
        Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'name': name,
          if (description != null && description.isNotEmpty) 'description': description,
        }),
      );

      print('Create project response status: ${response.statusCode}');
      print('Create project response body: ${response.body}');

      if (response.statusCode == 201 || response.statusCode == 200) {
        if (response.body.isEmpty) {
          return {'message': 'Project created successfully'};
        }
        return jsonDecode(response.body);
      } else {
        // Try to parse error response
        String errorMessage = 'Failed to create project';
        try {
          final error = jsonDecode(response.body);
          errorMessage = error['detail'] ?? error['message'] ?? errorMessage;
        } catch (e) {
          // If response isn't JSON, use the raw body
          errorMessage = response.body.isNotEmpty
              ? response.body
              : 'Server returned status ${response.statusCode}';
        }
        throw Exception(errorMessage);
      }
    } catch (e) {
      print('Create project error: $e');
      if (e is FormatException) {
        throw Exception('Invalid response format from server. Please check backend.');
      }
      rethrow;
    }
  }

  /// Create job
  Future<Map<String, dynamic>> createJob({
    required String projectId,
    required String jobType,
    required Map<String, dynamic> config,
  }) async {
    final response = await _client.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.jobs}/'),
      headers: _headers,
      body: jsonEncode({
        'project_id': projectId,
        'job_type': jobType,
        'config': config,
      }),
    );

    if (response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to create job');
    }
  }

  /// Get job status
  Future<Map<String, dynamic>> getJobStatus(String jobId) async {
    final response = await _client.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.jobs}/$jobId'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get job status');
    }
  }

  /// Create training job
  Future<Map<String, dynamic>> createTrainingJob(
    String token,
    String projectId,
    String modelType,
    int epochs,
    int batchSize,
    int imageSize, {
    required String datasetId,
  }) async {
    final response = await _client.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.jobs}/'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'project_id': projectId,
        'job_type': 'training',
        'config': {
          'model_type': modelType,
          'epochs': epochs,
          'batch_size': batchSize,
          'image_size': imageSize,
          'dataset_id': datasetId,
        },
      }),
    );

    if (response.statusCode == 201 || response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to create training job');
    }
  }

  /// Get all training jobs
  Future<List<dynamic>> getTrainingJobs(String token, [String? projectId]) async {
    final url = projectId != null
      ? '${ApiConfig.baseUrl}${ApiConfig.projects}/$projectId/training'
      : '${ApiConfig.baseUrl}${ApiConfig.jobs}/';

    final response = await _client.get(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      // Backend returns list directly or wrapped in 'jobs' key
      if (data is List) {
        return data;
      } else if (data is Map && data.containsKey('jobs')) {
        return data['jobs'] as List<dynamic>;
      }
      return [];
    } else {
      throw Exception('Failed to load training jobs');
    }
  }

  /// Get datasets for a project
  Future<List<dynamic>> getDatasets(String token, String projectId) async {
    final response = await _client.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/$projectId/datasets/'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data is List) {
        return data;
      } else if (data is Map && data.containsKey('datasets')) {
        return data['datasets'] as List<dynamic>;
      }
      return [];
    } else {
      throw Exception('Failed to load datasets');
    }
  }

  /// Upload dataset (images and annotations)
  Future<Map<String, dynamic>> uploadDataset(
    String token,
    String projectId,
    List<String> imagePaths,
    List<String> annotationPaths, {
    Function(int uploaded, int total)? onProgress,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/$projectId/datasets/upload'),
    );

    request.headers.addAll({
      'Authorization': 'Bearer $token',
    });

    // Add image files
    for (int i = 0; i < imagePaths.length; i++) {
      final file = File(imagePaths[i]);
      request.files.add(await http.MultipartFile.fromPath(
        'images',
        file.path,
        filename: file.path.split(Platform.pathSeparator).last,
      ));

      // Add corresponding annotation if exists
      if (i < annotationPaths.length) {
        final annotFile = File(annotationPaths[i]);
        request.files.add(await http.MultipartFile.fromPath(
          'annotations',
          annotFile.path,
          filename: annotFile.path.split(Platform.pathSeparator).last,
        ));
      }

      onProgress?.call(i + 1, imagePaths.length);
    }

    final response = await _client.send(request);
    final responseBody = await response.stream.bytesToString();

    if (response.statusCode == 201 || response.statusCode == 200) {
      return jsonDecode(responseBody);
    } else {
      final error = jsonDecode(responseBody);
      throw Exception(error['detail'] ?? 'Failed to upload dataset');
    }
  }

  /// Upload Blender file for synthetic data generation
  /// This is a two-step process:
  /// 1. Upload the .blend file to /projects/upload
  /// 2. Create a rendering job via /jobs/
  Future<Map<String, dynamic>> uploadBlenderFile({
    required String token,
    required String projectId,
    required String blenderFilePath,
    int numRenders = 100,
    int resolutionX = 640,
    int resolutionY = 640,
    int samples = 64,
    bool randomizeCamera = true,
    bool randomizeLighting = true,
    Function(int, int)? onProgress,
  }) async {
    try {
      print('📤 Step 1: Uploading Blender file with Dio...');

      // Get file info
      final file = File(blenderFilePath);
      final fileLength = await file.length();
      final fileName = file.path.split(Platform.pathSeparator).last;

      print('📁 File: $fileName (${(fileLength / 1024 / 1024).toStringAsFixed(2)} MB)');

      // Step 1: Upload the Blender file to /projects/upload using Dio
      final formData = FormData.fromMap({
        'project_id': projectId,
        'file': await MultipartFile.fromFile(
          blenderFilePath,
          filename: fileName,
        ),
      });

      final uploadResponse = await _dio.post(
        '${ApiConfig.baseUrl}${ApiConfig.projects}/upload',
        data: formData,
        options: Options(
          headers: {
            'Authorization': 'Bearer $token',
          },
        ),
        onSendProgress: (sent, total) {
          print('📊 Upload progress: ${(sent / total * 100).toStringAsFixed(1)}% ($sent / $total bytes)');
          onProgress?.call(sent, total);
        },
      );

      if (uploadResponse.statusCode != 201 && uploadResponse.statusCode != 200) {
        final error = uploadResponse.data;
        throw Exception(error['detail'] ?? 'Failed to upload Blender file');
      }

      final uploadResult = uploadResponse.data;
      final fileId = uploadResult['file_id'] ?? uploadResult['id'];

      print('✅ Step 1 complete: File uploaded with ID: $fileId');
      print('📋 Step 2: Creating rendering job...');

      // Step 2: Create a rendering job
      final jobResponse = await _dio.post(
        '${ApiConfig.baseUrl}${ApiConfig.jobs}/',
        data: {
          'project_id': projectId,
          'job_type': 'render',
          'config': {
            'file_id': fileId,
            'num_renders': numRenders,
            'resolution_x': resolutionX,
            'resolution_y': resolutionY,
            'samples': samples,
            'randomize_camera': randomizeCamera,
            'randomize_lighting': randomizeLighting,
          },
        },
        options: Options(
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
        ),
      );

      if (jobResponse.statusCode != 201 && jobResponse.statusCode != 200) {
        final error = jobResponse.data;
        throw Exception(error['detail'] ?? 'Failed to create rendering job');
      }

      final jobResult = jobResponse.data;
      print('✅ Step 2 complete: Rendering job created with ID: ${jobResult['id']}');

      return {
        'file_id': fileId,
        'job_id': jobResult['id'],
        'job': jobResult,
      };
    } on DioException catch (e) {
      print('❌ Dio Error in uploadBlenderFile:');
      print('   Type: ${e.type}');
      print('   Message: ${e.message}');
      print('   Response: ${e.response?.data}');

      if (e.type == DioExceptionType.connectionTimeout) {
        throw Exception('Connection timeout. Please check your network connection.');
      } else if (e.type == DioExceptionType.sendTimeout) {
        throw Exception('Upload timeout. The file is too large or connection is too slow.');
      } else if (e.type == DioExceptionType.receiveTimeout) {
        throw Exception('Server response timeout. Please try again.');
      } else if (e.response != null) {
        final error = e.response!.data;
        throw Exception(error['detail'] ?? error['message'] ?? 'Upload failed');
      } else {
        throw Exception('Network error: ${e.message}');
      }
    } catch (e) {
      print('❌ Error in uploadBlenderFile: $e');
      rethrow;
    }
  }

  /// Download model file with progress
  Future<void> downloadModel(
    String token,
    String modelId,
    String savePath, {
    Function(int received, int total)? onProgress,
  }) async {
    final request = http.Request(
      'GET',
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.models}/$modelId/download'),
    );
    request.headers.addAll({
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    });

    final response = await _client.send(request);

    if (response.statusCode == 200) {
      final contentLength = response.contentLength ?? 0;
      int received = 0;
      final List<int> bytes = [];

      await for (var chunk in response.stream) {
        bytes.addAll(chunk);
        received += chunk.length;
        onProgress?.call(received, contentLength);
      }

      final file = File(savePath);
      await file.writeAsBytes(bytes);
    } else {
      throw Exception('Failed to download model');
    }
  }

  /// Trigger server-side export of a trained model to the given format.
  /// Returns the export_path from the server response.
  Future<Map<String, dynamic>> exportModel(
    String token,
    String modelId, {
    String format = 'tflite',
    int imgsz = 640,
    bool optimize = false,
    bool half = false,
    bool int8 = false,
  }) async {
    final response = await _client.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.models}/$modelId/export'),
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer $token'},
      body: jsonEncode({
        'format': format,
        'imgsz': imgsz,
        'optimize': optimize,
        'half': half,
        'int8': int8,
        'simplify': true,
        'batch': 1,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Export failed (${response.statusCode}): ${response.body}');
  }

  /// Download an already-exported model file (TFLite, ONNX, etc.) to savePath.
  Future<void> downloadExportedModel(
    String token,
    String modelId,
    String format,
    String savePath, {
    Function(int received, int total)? onProgress,
  }) async {
    await _dio.download(
      '${ApiConfig.baseUrl}${ApiConfig.models}/$modelId/export/$format/download',
      savePath,
      options: Options(headers: {'Authorization': 'Bearer $token'}),
      onReceiveProgress: onProgress,
    );
  }

  /// Download the labels .txt file for a trained model.
  Future<void> downloadModelLabels(
    String token,
    String modelId,
    String savePath,
  ) async {
    await _dio.download(
      '${ApiConfig.baseUrl}${ApiConfig.models}/$modelId/labels',
      savePath,
      options: Options(headers: {'Authorization': 'Bearer $token'}),
    );
  }

  /// Full TFLite package download: export → download .tflite → download labels.txt.
  ///
  /// Saves model as [modelDir]/model.tflite and labels as [modelDir]/labels.txt.
  /// Returns the tflite file path on success.
  Future<String> downloadTFLitePackage(
    String token,
    String modelId,
    String modelDir, {
    Function(String stage, int received, int total)? onProgress,
  }) async {
    final dir = Directory(modelDir);
    await dir.create(recursive: true);

    // 1 — trigger export
    onProgress?.call('exporting', 0, 1);
    final exportResult = await exportModel(token, modelId, format: 'tflite');
    if (exportResult['success'] != true) {
      throw Exception('Export failed: ${exportResult['error_message']}');
    }

    // 2 — download TFLite file
    final tflitePath = '$modelDir/model.tflite';
    await downloadExportedModel(
      token, modelId, 'tflite', tflitePath,
      onProgress: (r, t) => onProgress?.call('downloading_model', r, t),
    );

    // 3 — download labels
    final labelsPath = '$modelDir/labels.txt';
    await downloadModelLabels(token, modelId, labelsPath);

    return tflitePath;
  }

  /// Dispose client
  void dispose() {
    _client.close();
  }
}
