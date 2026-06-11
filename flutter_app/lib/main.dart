import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/auth_provider.dart';
import 'providers/detection_provider.dart';
import 'screens/login_screen.dart';
import 'screens/app_shell.dart';
import 'theme/app_theme.dart';
import 'utils/api_config.dart';

void main() {
  runApp(const YoloVisionApp());
}

class YoloVisionApp extends StatelessWidget {
  const YoloVisionApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => DetectionProvider()),
      ],
      child: MaterialApp(
        title: 'VisionForge',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        home: const AppInitializer(),
      ),
    );
  }
}

/// Initializes the app and determines initial route based on auth state
class AppInitializer extends StatefulWidget {
  const AppInitializer({super.key});

  @override
  State<AppInitializer> createState() => _AppInitializerState();
}

class _AppInitializerState extends State<AppInitializer> {
  bool _isInitializing = true;

  @override
  void initState() {
    super.initState();
    // Defer initialization until after first frame to avoid build-time errors
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initializeApp();
    });
  }

  Future<void> _initializeApp() async {
    try {
      print('🚀 App: Starting initialization');
      await ApiConfig.load();
      // Initialize auth provider to check for existing token
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      await authProvider.initialize();
      print('✅ App: Initialization complete');
    } catch (e) {
      print('❌ App: Initialization error: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isInitializing = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isInitializing) {
      return const Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.visibility,
                size: 80,
                color: Colors.blue,
              ),
              SizedBox(height: 24),
              Text(
                'YOLO Vision',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 16),
              CircularProgressIndicator(),
            ],
          ),
        ),
      );
    }

    // Show home or login based on authentication state
    return Consumer<AuthProvider>(
      builder: (context, authProvider, _) {
        if (authProvider.isAuthenticated) {
          return const AppShell();
        } else {
          return const LoginScreen();
        }
      },
    );
  }
}
