import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/auth_provider.dart';
import 'providers/detection_provider.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

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
        title: 'YOLO Vision',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.blue,
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          appBarTheme: const AppBarTheme(
            centerTitle: true,
            elevation: 0,
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              elevation: 2,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            ),
          ),
        ),
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
    // Initialize auth provider to check for existing token
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    await authProvider.initialize();

    if (mounted) {
      setState(() {
        _isInitializing = false;
      });
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
          return const HomeScreen();
        } else {
          return const LoginScreen();
        }
      },
    );
  }
}
