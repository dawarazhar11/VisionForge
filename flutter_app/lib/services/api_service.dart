import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/auth_token.dart';
import '../models/user.dart';
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
    final response = await _client.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.authLogin}'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      final token = AuthToken.fromJson(jsonDecode(response.body));
      setAuthToken(token);
      return token;
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Login failed');
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
  Future<List<dynamic>> getProjects([String? token]) async {
    final headers = token != null
      ? {'Content-Type': 'application/json', 'Authorization': 'Bearer $token'}
      : _headers;

    final response = await _client.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['projects'] as List<dynamic>;
    } else {
      throw Exception('Failed to load projects');
    }
  }

  /// Create new project
  Future<Map<String, dynamic>> createProject(String token, String name, [String? description]) async {
    final response = await _client.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'name': name,
        if (description != null) 'description': description,
      }),
    );

    if (response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to create project');
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

  /// Download model file
  Future<List<int>> downloadModel(String token, String modelId, String filePath, {Function(int, int)? onProgress}) async {
    final response = await _client.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.models}/$modelId/download'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      return response.bodyBytes;
    } else {
      throw Exception('Failed to download model');
    }
  }

  /// Get training jobs
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
      return data['jobs'] as List<dynamic>;
    } else {
      throw Exception('Failed to load training jobs');
    }
  }

  /// Get datasets for a project
  Future<List<dynamic>> getDatasets(String token, String projectId) async {
    final response = await _client.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/$projectId/datasets'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['datasets'] as List<dynamic>;
    } else {
      throw Exception('Failed to load datasets');
    }
  }

  /// Upload dataset
  Future<Map<String, dynamic>> uploadDataset(
    String token,
    String projectId,
    List<String> imagePaths,
    List<String> annotationPaths,
    {Function(int, int)? onProgress}
  ) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/$projectId/datasets'),
    );

    request.headers['Authorization'] = 'Bearer $token';

    // Add image files
    for (var imagePath in imagePaths) {
      request.files.add(await http.MultipartFile.fromPath('images', imagePath));
    }

    // Add annotation files
    for (var annotationPath in annotationPaths) {
      request.files.add(await http.MultipartFile.fromPath('annotations', annotationPath));
    }

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to upload dataset');
    }
  }

  /// Create training job
  Future<Map<String, dynamic>> createTrainingJob(
    String token,
    String projectId,
    String modelType,
    int epochs,
    int batchSize,
    int imageSize,
    {required String datasetId}
  ) async {
    final response = await _client.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/$projectId/training'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'dataset_id': datasetId,
        'model_type': modelType,
        'epochs': epochs,
        'batch_size': batchSize,
        'image_size': imageSize,
      }),
    );

    if (response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to create training job');
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

  /// Dispose client
  void dispose() {
    _client.close();
  }
}
