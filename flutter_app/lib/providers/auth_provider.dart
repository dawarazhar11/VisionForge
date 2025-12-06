import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../models/auth_token.dart';
import '../models/user.dart';
import '../services/api_service.dart';

/// Authentication state provider
class AuthProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();

  AuthToken? _authToken;
  User? _user;
  bool _isLoading = false;
  String? _error;

  AuthToken? get authToken => _authToken;
  User? get user => _user;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _authToken != null;

  /// Initialize auth state from storage
  Future<void> initialize() async {
    _isLoading = true;
    notifyListeners();

    try {
      final prefs = await SharedPreferences.getInstance();
      final tokenJson = prefs.getString('auth_token');

      if (tokenJson != null) {
        _authToken = AuthToken.fromJson(jsonDecode(tokenJson));
        _apiService.setAuthToken(_authToken!);

        // TODO: Fetch user profile
      }
    } catch (e) {
      _error = 'Failed to load auth state: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Register new user
  Future<bool> register({
    required String email,
    required String password,
    String? fullName,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _user = await _apiService.register(
        email: email,
        password: password,
        fullName: fullName,
      );

      // Auto-login after registration
      return await login(email: email, password: password);
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Login user
  Future<bool> login({
    required String email,
    required String password,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _authToken = await _apiService.login(
        email: email,
        password: password,
      );

      // Save token to storage
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', jsonEncode(_authToken!.toJson()));

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Logout user
  Future<void> logout() async {
    _authToken = null;
    _user = null;
    _apiService.clearAuthToken();

    // Clear storage
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');

    notifyListeners();
  }

  /// Refresh access token
  Future<bool> refreshAccessToken() async {
    if (_authToken == null) return false;

    try {
      _authToken = await _apiService.refreshToken(_authToken!.refreshToken);

      // Save new token to storage
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', jsonEncode(_authToken!.toJson()));

      notifyListeners();
      return true;
    } catch (e) {
      _error = 'Token refresh failed';
      await logout();
      return false;
    }
  }

  /// Clear error message
  void clearError() {
    _error = null;
    notifyListeners();
  }
}
