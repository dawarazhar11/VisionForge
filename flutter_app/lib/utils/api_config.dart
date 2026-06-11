import 'package:shared_preferences/shared_preferences.dart';

/// API configuration for backend communication
class ApiConfig {
  static const String defaultBaseUrl = 'http://192.168.0.207:8002';
  static const String backendUrlPrefKey = 'backendUrlOverride';

  static String? _overrideBaseUrl;

  /// Effective base URL: SharedPreferences override, else compile-time default.
  static String get baseUrl => _overrideBaseUrl ?? defaultBaseUrl;

  static String? get overrideBaseUrl => _overrideBaseUrl;

  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString(backendUrlPrefKey);
    _overrideBaseUrl = _normalizeBaseUrl(stored);
  }

  static Future<void> setBaseUrlOverride(String? url) async {
    final prefs = await SharedPreferences.getInstance();
    final normalized = _normalizeBaseUrl(url);

    if (normalized == null) {
      await prefs.remove(backendUrlPrefKey);
      _overrideBaseUrl = null;
      return;
    }

    await prefs.setString(backendUrlPrefKey, normalized);
    _overrideBaseUrl = normalized;
  }

  static String? _normalizeBaseUrl(String? url) {
    if (url == null) return null;

    final trimmed = url.trim();
    if (trimmed.isEmpty) return null;

    return trimmed.endsWith('/')
        ? trimmed.substring(0, trimmed.length - 1)
        : trimmed;
  }

  static const String apiPrefix = '/api/v1';

  // Endpoints
  static const String authRegister = '$apiPrefix/auth/register';
  static const String authLogin = '$apiPrefix/auth/login/json';
  static const String authRefresh = '$apiPrefix/auth/refresh';

  static const String projects = '$apiPrefix/projects';
  static const String projectsUpload = '$apiPrefix/projects/upload';

  static const String jobs = '$apiPrefix/jobs';

  static const String models = '$apiPrefix/models';

  static const String health = '/health';

  // Timeouts
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
}
