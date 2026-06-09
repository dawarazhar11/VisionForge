# E2E MVP Validation Checklist (DAW-33)

iOS-first end-to-end validation: **upload → render → train → TFLite → Flutter camera inference**.

Android is out of scope (DAW-121). Use this checklist for manual runs and `scripts/e2e/validate_mvp.py` for automated API validation.

## Prerequisites

| Item | macOS (dev) | Notes |
|------|-------------|-------|
| Container runtime | Podman (preferred) | `podman machine start` then `podman-compose up -d` |
| Local fallback | Homebrew PG + Redis + `.venv-test` | If Podman fails: `brew services start postgresql@16 redis`, then uvicorn + celery from `backend/.venv-test` (render needs Blender in worker or `BLENDER_PATH` on Mac) |
| API reachable | `http://localhost:8002/health` | Backend on port 8002 |
| Celery worker queues | `rendering,training,default,celery` | Required or jobs stay PENDING |
| Sample upload file | `STEP Files/Test 1.STEP` | STEP works on ARM64 Docker; cadquery geometric labels only |
| Flutter device/simulator | Xcode + `flutter run` | Physical iPhone preferred for camera |

### Known platform blockers

- **ARM64 Docker**: cadquery STEP feature recognition unavailable — STEP renders use geometric heuristics, not part names (DAW-118).
- **`.blend` uploads**: Generic class-map pipeline (DAW-119) auto-detects desk scenes or assigns one class per mesh. Custom maps via `metadata_json.class_map`. Dual-pass segmentation for desk scenes is still legacy-only.
- **Podman machine**: If `podman-compose up -d` fails, run `podman machine init && podman machine start`.

## Phase 1 — Stack & API (automated)

```bash
# Start stack
podman machine start   # if needed
podman-compose up -d

# Smoke: health, auth, project, test job (~30s)
python scripts/e2e/validate_mvp.py --smoke

# Full API pipeline: upload → render → train → TFLite (~30–90 min)
python scripts/e2e/validate_mvp.py --full \
  --upload-file "STEP Files/Test 1.STEP" \
  --num-renders 2 --epochs 1
```

**Pass criteria**

- [ ] `/health` returns 200
- [ ] Register + login succeed
- [ ] Project upload returns 201 with `file_path`
- [ ] Test job reaches `SUCCESS`
- [ ] Render job reaches `SUCCESS` with `images_generated > 0`
- [ ] Train job reaches `SUCCESS` with `best_model_path`
- [ ] TFLite export returns `success: true`
- [ ] Download produces `model.tflite` + `labels.txt`

## Phase 2 — Flutter app (manual, iOS)

### Backend URL

Default compile-time URL: `http://100.108.186.54:8002` (Tailscale) in `flutter_app/lib/utils/api_config.dart`. Override via **Home → Settings → Backend URL** (saved in SharedPreferences).

- iOS Simulator: `http://127.0.0.1:8002` (localhost on the Mac host)
- Physical iPhone: Mac LAN IP (e.g. `http://192.168.x.x:8002`) or Tailscale IP — `localhost` will not reach your Mac
- Use **Test Connection** on Settings after changing the URL

### Steps

```bash
cd flutter_app
flutter pub get
flutter run   # iOS simulator or connected iPhone
```

| Step | Home button / screen | Pass |
|------|----------------------|------|
| 1 | Login / Register | Authenticated, no API errors |
| 2 | **My Projects** | Upload STEP or `.blend`; project visible in list |
| 3 | **Training Jobs** | Create render job; SSE progress updates (DAW-39) |
| 4 | **Training Jobs** | Render completes; create train job |
| 5 | **My Models** | Trained model listed after train SUCCESS |
| 6 | **My Models** | Tap download → TFLite + `labels.txt` saved; tap **Set Active** (or snackbar action) |
| 7 | **Start Detection** (`DetectionScreen`) | Active model loads; live bounding boxes on camera preview |

**Pass criteria**

- [ ] SSE progress bar updates without 10s polling lag
- [ ] TFLite + labels load on **Start Detection** (requires active model from step 6)
- [ ] At least one bounding box overlay on test subject (simulator camera or physical iPhone)

## Phase 3 — Evidence & sign-off

Capture for Linear DAW-33:

- [ ] `validate_mvp.py` JSON summary (full mode)
- [ ] Screenshot: Training Jobs with completed render + train
- [ ] Screenshot: Camera screen with detections
- [ ] Note any FAILED job `error_message` from API

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Jobs stuck PENDING | Celery queue mismatch | Check worker `-Q rendering,training,default,celery` |
| Render FAILED "cadquery" | STEP on ARM64 | Expected; geometric path still runs |
| Render FAILED "Blender not found" | Missing in container | Rebuild worker image |
| Train FAILED "No successful rendering" | Render not done / wrong project | Wait for render SUCCESS |
| Flutter can't reach API | Wrong base URL | Settings → Backend URL |
| TFLite export fails | Missing tensorflow/onnx deps in worker | Check worker logs |

## Related issues

- DAW-119 — Generic class maps (unblocks arbitrary `.blend`)
- DAW-118 — STEP part names → labels
- DAW-120 — Pre-render 3D annotation UI
- DAW-121 — Android (deferred)
