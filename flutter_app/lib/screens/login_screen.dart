import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../utils/api_config.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _fullNameController = TextEditingController();
  final _backendUrlController = TextEditingController();

  bool _isLoginMode = true;
  bool _showBackendField = false;

  @override
  void initState() {
    super.initState();
    _backendUrlController.text = ApiConfig.baseUrl;
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _fullNameController.dispose();
    _backendUrlController.dispose();
    super.dispose();
  }

  Future<void> _saveBackendUrl() async {
    await ApiConfig.setBaseUrlOverride(_backendUrlController.text);
    if (mounted) {
      _backendUrlController.text = ApiConfig.baseUrl;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Backend set to ${ApiConfig.baseUrl}')),
      );
      setState(() => _showBackendField = false);
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final authProvider = Provider.of<AuthProvider>(context, listen: false);

    bool success;
    if (_isLoginMode) {
      success = await authProvider.login(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );
    } else {
      success = await authProvider.register(
        email: _emailController.text.trim(),
        password: _passwordController.text,
        fullName: _fullNameController.text.trim().isEmpty
            ? null
            : _fullNameController.text.trim(),
      );
    }

    if (success && mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const HomeScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: Consumer<AuthProvider>(
              builder: (context, authProvider, _) {
                return Form(
                  key: _formKey,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Logo/Title
                      const Icon(
                        Icons.visibility,
                        size: 80,
                        color: Colors.blue,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'YOLO Vision',
                        style: Theme.of(context).textTheme.headlineMedium,
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _isLoginMode ? 'Sign in to continue' : 'Create an account',
                        style: Theme.of(context).textTheme.bodyMedium,
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 24),

                      // Backend URL (collapsible) — for device/local testing
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton.icon(
                          icon: Icon(
                            _showBackendField
                                ? Icons.expand_less
                                : Icons.settings_ethernet,
                            size: 18,
                          ),
                          label: Text(
                            _showBackendField ? 'Hide backend' : 'Backend URL',
                            style: const TextStyle(fontSize: 13),
                          ),
                          onPressed: () => setState(
                              () => _showBackendField = !_showBackendField),
                        ),
                      ),
                      if (_showBackendField) ...[
                        TextFormField(
                          controller: _backendUrlController,
                          keyboardType: TextInputType.url,
                          autocorrect: false,
                          decoration: InputDecoration(
                            labelText: 'Backend URL',
                            hintText: 'http://192.168.0.207:8002',
                            border: const OutlineInputBorder(),
                            prefixIcon: const Icon(Icons.dns),
                            suffixIcon: IconButton(
                              icon: const Icon(Icons.check),
                              onPressed: _saveBackendUrl,
                            ),
                          ),
                          onFieldSubmitted: (_) => _saveBackendUrl(),
                        ),
                        const SizedBox(height: 8),
                      ],
                      const SizedBox(height: 16),

                      // Email field
                      TextFormField(
                        controller: _emailController,
                        keyboardType: TextInputType.emailAddress,
                        decoration: const InputDecoration(
                          labelText: 'Email',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.email),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter your email';
                          }
                          if (!value.contains('@')) {
                            return 'Please enter a valid email';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // Full name field (only for registration)
                      if (!_isLoginMode) ...[
                        TextFormField(
                          controller: _fullNameController,
                          decoration: const InputDecoration(
                            labelText: 'Full Name (Optional)',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.person),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],

                      // Password field
                      TextFormField(
                        controller: _passwordController,
                        obscureText: true,
                        decoration: const InputDecoration(
                          labelText: 'Password',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.lock),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter your password';
                          }
                          if (!_isLoginMode && value.length < 8) {
                            return 'Password must be at least 8 characters';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 24),

                      // Error message
                      if (authProvider.error != null) ...[
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.red.shade200),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.error, color: Colors.red.shade700),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  authProvider.error!,
                                  style: TextStyle(color: Colors.red.shade700),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],

                      // Submit button
                      ElevatedButton(
                        onPressed: authProvider.isLoading ? null : _submit,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                        ),
                        child: authProvider.isLoading
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Text(_isLoginMode ? 'Sign In' : 'Sign Up'),
                      ),
                      const SizedBox(height: 16),

                      // Toggle login/register
                      TextButton(
                        onPressed: () {
                          setState(() {
                            _isLoginMode = !_isLoginMode;
                            authProvider.clearError();
                          });
                        },
                        child: Text(
                          _isLoginMode
                              ? 'Don\'t have an account? Sign Up'
                              : 'Already have an account? Sign In',
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
