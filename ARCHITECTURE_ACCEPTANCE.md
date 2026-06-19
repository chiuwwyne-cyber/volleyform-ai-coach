# Volleyball AI Coach Acceptance Notes

## Requirement Mapping

### 1. Backend runs on the user's computer

Evidence:

- `backend/server.py` starts a local HTTP server.
- `run_web_app.ps1` launches the backend with `--host 0.0.0.0 --port 8000`.
- Phone users connect through the computer's LAN IP.

### 2. Frontend and backend are separated

Evidence:

- Backend code lives in `backend/`.
- Frontend code lives in `frontend/`.
- Frontend communicates through HTTP endpoints:
  - `GET /api/capabilities`
  - `POST /api/analyze`

### 3. Backend has no UI

Evidence:

- `backend/server.py` does not call `cv2.imshow`, `cv2.namedWindow`, or other UI functions.
- OpenCV UI remains only in the older desktop path under `main/main.py`.

### 4. Web/mobile frontend

Evidence:

- `frontend/index.html` is responsive through `frontend/styles.css`.
- File input uses `accept="video/*" capture="environment"` for mobile recording and upload.
- The frontend includes a MediaRecorder-based recording panel with playback preview and keeps the same upload/analyze path.
- The backend serves the frontend from `/`, so phone browsers can open it directly.

### 5. All frontends can connect to backend

Evidence:

- `backend/server.py` sends permissive CORS headers.
- `API_CONTRACT.md` documents stable endpoints and payloads.
- `GET /api/capabilities` exposes action labels and modalities for any frontend.
- `frontend/index.html` includes a backend URL field so a standalone web/mobile client can point at `http://<computer-lan-ip>:8000`.

### 6. Frontend design consistency

Evidence:

- `frontend/styles.css` defines shared tokens for color, font, surfaces, borders, and status colors.
- Layout uses repeated panels, consistent spacing, and a clear control/result structure.
- Responsive breakpoint keeps the same hierarchy on mobile.

### 7. User can understand what is wrong

Evidence:

- `backend/feedback.py` maps every issue code to:
  - readable title
  - risk severity
  - body part
  - instant cue
  - practice drill
  - explanation
  - concrete fixes
  - video search link
- `backend/analyzer.py` returns `coach_plan` so the frontend can show the priority correction first.
- `frontend/app.js` renders primary issues, fixes, timeline, coach summary, and coach plan.

### 8. Future multimodal expansion

Evidence:

- `backend/modalities.py` defines active and future analysis modules.
- `backend/modality_processors.py` registers per-modality processors, so future modules can attach without rewriting the main analysis loop.
- `backend/analyzer.py` returns `modalities` and `modality_results`.
- `frontend/app.js` dynamically renders modality capability and output.
- `API_CONTRACT.md` documents how to add ball, audio, wearable, and coach text modules.

## Current Active Modalities

- `pose`: body pose and 3D world landmarks.
- `hands`: left and right hand landmarks.

## Reserved Modalities

- `ball`: ball tracking.
- `audio`: sound and rhythm.
- `wearable`: phone/watch/IMU sensor data.
- `coach_text`: coach notes and human observations.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -c "import pathlib; files=['backend/analyzer.py','backend/server.py','backend/feedback.py','backend/modalities.py','backend/modality_processors.py','backend/action_registry.py','backend/self_test.py','backend/frontend_contract_test.py']; [compile(pathlib.Path(f).read_text(encoding='utf-8'), f, 'exec') for f in files]; print('python syntax ok')"
```

```powershell
C:\Users\test\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe --check frontend\app.js
```

```powershell
C:\Users\test\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe frontend\app_behavior_test.mjs
```

```powershell
.\.venv\Scripts\python.exe backend\frontend_contract_test.py
```

```powershell
.\.venv\Scripts\python.exe backend\frontend_quality_test.py
```

```powershell
.\.venv\Scripts\python.exe backend\feedback_contract_test.py
```

```powershell
.\.venv\Scripts\python.exe backend\backend_no_ui_test.py
```

```powershell
.\.venv\Scripts\python.exe backend\resource_contract_test.py
```

```powershell
.\.venv\Scripts\python.exe backend\self_test.py
```
