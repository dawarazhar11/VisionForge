// Basic app smoke test: the root widget builds without throwing.

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:yolo_vision_app/main.dart';

void main() {
  testWidgets('App builds and shows a MaterialApp', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const YoloVisionApp());

    expect(find.byType(YoloVisionApp), findsOneWidget);
  });
}
