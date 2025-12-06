/// API configuration for backend communication
class ApiConfig {
  // Base URL - Update this to your backend server address
  static const String baseUrl = 'http://10.0.2.2:8002'; // Android emulator localhost
  // Use 'http://localhost:8002' for iOS simulator
  // Use 'http://YOUR_IP:8002' for physical devices

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
