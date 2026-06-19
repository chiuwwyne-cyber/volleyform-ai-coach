# Volleyball AI Coach API Contract

This backend runs on the user's computer and exposes HTTP endpoints for any web or mobile frontend on the same network.

## Base URL

Local computer:

```text
http://127.0.0.1:8000
```

Phone on the same Wi-Fi:

```text
http://<computer-lan-ip>:8000
```

## CORS

The backend sends permissive CORS headers:

```text
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

This lets multiple future frontends connect to the same backend.

For standalone web/mobile frontends, point requests at:

```text
http://<computer-lan-ip>:8000/api/...
```

The bundled frontend also includes a backend URL field for this case.

## GET /api/health

Use for uptime checks.

Response:

```json
{
  "ok": true,
  "service": "volleyball-ai-coach",
  "capabilities": {
    "default_modalities": ["pose", "hands"],
    "modalities": []
  }
}
```

## GET /api/capabilities

Use for frontend bootstrapping. This is the preferred endpoint for discovering available actions and analysis modules.

Response:

```json
{
  "ok": true,
  "capabilities": {
    "actions": [
      { "id": "block", "label": "攔網" },
      { "id": "receive", "label": "接球" }
    ],
    "default_modalities": ["pose", "hands"],
    "modalities": [
      {
        "id": "pose",
        "label": "身體骨架",
        "available": true,
        "requested": true,
        "state": "active"
      }
    ]
  }
}
```

## POST /api/analyze

Analyze a video.

Content type:

```text
multipart/form-data
```

Fields:

- `video`: video file
- `action`: `spike | block | serve | receive | set`
- `frame_stride`: analyze every N frames
- `process_width`: inference width before analysis
- `max_frames`: processing limit
- `modalities`: JSON array or comma-separated list, for example `["pose","hands","ball"]`

Response:

```json
{
  "ok": true,
  "result": {
    "action": "receive",
    "action_label": "接球",
    "processed_frames": 120,
    "good_frames": 62,
    "score": 52,
    "coach_summary": "最需要先修正的是...",
    "coach_plan": {
      "status": "needs_fix",
      "headline": "先修正：吃蘿蔔風險偏高",
      "focus": "接球平台",
      "reason": "平台太軟或只伸手撈球時，球很容易吃蘿蔔或直接噴飛。",
      "next_steps": ["手肘鎖住，身體到球後面。"],
      "video_url": "https://www.youtube.com/results?search_query=..."
    },
    "primary_issues": [
      {
        "code": "lobster_receive_risk",
        "title": "吃蘿蔔風險偏高",
        "severity": "high",
        "body_part": "接球平台",
        "instant_cue": "手肘鎖住，身體到球後面。",
        "practice_drill": "做 10 次低姿勢接球平台定格，確認手肘直、平台平。",
        "why_it_matters": "平台太軟或只伸手撈球時，球很容易吃蘿蔔或直接噴飛。",
        "message": "手臂平台太軟...",
        "fixes": ["手肘伸直鎖住平台。"],
        "video_url": "https://www.youtube.com/results?search_query=..."
      }
    ],
    "timeline": [],
    "modalities": [],
    "modality_results": {
      "pose": {},
      "hands": {},
      "reserved": {}
    }
  }
}
```

## Extending With New Modalities

1. Add the module in `backend/modalities.py`.
2. Add a processor in `backend/modality_processors.py` and register it with `register_processor()`.
3. Read from the shared frame context keys: `frame_index`, `landmarks`, `world_landmarks`, `hand_landmarks`, `angles`, `positions`, `hand_features`.
4. Add display text in `frontend/app.js` `metricText()` if the new module needs custom metrics.

The API shape should remain stable. `backend/analyzer.py` should stay mostly unchanged; it only sends each frame context into the registered processors.
