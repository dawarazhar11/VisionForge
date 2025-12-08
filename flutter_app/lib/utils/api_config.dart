/// API configuration for backend communication
class ApiConfig {
  // Base URL - Backend server via Netbird VPN
  static const String baseUrl = 'http://100.108.186.54:8002';
  // Using Netbird mesh VPN for continuous connectivity
  // Physical device: Netbird IP address (currently 100.108.186.54)

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
