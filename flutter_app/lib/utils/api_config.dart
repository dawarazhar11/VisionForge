/// API configuration for backend communication
class ApiConfig {
  // Base URL - Backend server running on PC at 192.168.0.16
  static const String baseUrl = 'http://192.168.0.16:8002';
  // iOS simulator: use 'http://localhost:8002' if backend on Mac
  // Physical device: use PC's IP address (currently 192.168.0.16)

  static const String apiPrefix = '/api/v1';

  // Endpoints
  static const String authRegister = '$apiPrefix/auth/register';
  static const String authLogin = '$apiPrefix/auth/login/json';
  static const String authRefresh = '$apiPrefix/auth/refresh';

  static const String projects = '$apiPrefix/projects';
  static const String projectsUpload = '$apiPrefix/projects/upload';

  static const String jobs = '$apiPrefix/jobs';

  static const String models = '$apiPrefix/models';

  // Timeouts
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
}
