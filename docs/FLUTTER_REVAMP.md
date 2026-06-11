# Flutter App Revamp Plan (DAW-120 + UX modernization)

Full UX rebuild on top of the **existing, tested service layer**. We keep
`ApiService`, `YoloService`, providers, and models; we replace navigation,
theming, and screens so the app covers every backend capability.

## Why
The app predates the "any design file → STEP → dynamic classes → previews"
work. Gaps: no STEP upload, no class-map editor, no dataset/preview viewer,
new endpoints (`/class-map`, `/features`, `/previews`, `/class-names`)
unwired.

## Keep (do not rewrite)
- `services/yolo_service.dart` — TFLite inference, dynamic labels
- `services/api_service.dart` — extend with missing endpoints, don't replace
- `providers/auth_provider.dart`, `providers/detection_provider.dart`
- `models/*`, `utils/api_config.dart`

## Backend surface the UI must cover
- auth: register, login/json, refresh
- projects: upload (`.step/.stp/.blend/.obj/.stl/.fbx`, multipart name+file),
  list, get, PATCH (name/description/**class_map**), delete,
  GET `/class-map`, GET `/features`, GET file
- jobs: create (render|train), list, get, **SSE** `/stream`,
  **previews** (`/previews`, `/previews/{file}`), cancel
- models: list, get, download (tflite/onnx/coreml), **labels**, **class-names**
- monitoring: health

## Target UX
Bottom-nav shell: **Projects · Detect · Models · Settings**

- **New Project wizard** (the headline fix): pick any supported file (incl.
  STEP) → upload → backend resolves classes (STEP features / part names /
  .blend objects) → **review & edit class map** (DAW-120) → configure render
  → start. Live job progress via SSE.
- **Project detail**: render/train jobs with live progress, **dataset preview
  grid** (annotated previews API), class-map view/edit, train launcher.
- **Models**: list, download w/ progress, set active, show class-names.
- **Detect**: live camera with dynamic labels (exists — restyle).
- **Settings**: backend URL, account, cache.

## Phases (each independently shippable)
0. Plan + design tokens (theme.dart) + nav shell
1. ApiService completion — all missing endpoints + SSE + previews
2. New Project wizard incl. STEP upload + class-map review/edit
3. Project detail: jobs + SSE progress + preview grid
4. Models screen: download/active/class-names
5. Detect screen restyle
6. Settings + polish; remove dead screens

## Constraints
- `provider` (not Riverpod) for state — matches existing.
- Material 3, single theme.dart token source.
- Verify each phase with `flutter analyze` (0 errors) before commit.
