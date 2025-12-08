import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../models/auth_token.dart';
import '../models/user.dart';
import '../models/project.dart';
import '../utils/api_config.dart';

/// API service for backend communication
class ApiService {
  final http.Client _client = http.Client();
  AuthToken? _authToken;

  // Singleton pattern
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

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
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/$projectId/blender'),
    );

    request.headers['Authorization'] = 'Bearer $token';

    // Add configuration fields
    request.fields['num_renders'] = numRenders.toString();
    request.fields['resolution_x'] = resolutionX.toString();
    request.fields['resolution_y'] = resolutionY.toString();
    request.fields['samples'] = samples.toString();
    request.fields['randomize_camera'] = randomizeCamera.toString();
    request.fields['randomize_lighting'] = randomizeLighting.toString();

    // Add the Blender file
    request.files.add(await http.MultipartFile.fromPath('blender_file', blenderFilePath));

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 201 || response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to upload Blender file');
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

  /// Dispose client
  void dispose() {
    _client.close();
  }
}
