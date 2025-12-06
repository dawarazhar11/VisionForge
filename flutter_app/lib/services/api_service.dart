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
  Future<List<dynamic>> getProjects() async {
    final response = await _client.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.projects}/'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['projects'] as List<dynamic>;
    } else {
      throw Exception('Failed to load projects');
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
  Future<List<int>> downloadModel(String modelId) async {
    final response = await _client.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.models}/$modelId/download'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return response.bodyBytes;
    } else {
      throw Exception('Failed to download model');
    }
  }

  /// Dispose client
  void dispose() {
    _client.close();
  }
}
