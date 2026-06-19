# VolleyForm AI Coach

VolleyForm is an open-source volleyball motion analysis web app. It uses MediaPipe 3D pose and hand landmarks to review uploaded or recorded videos and returns focused coaching feedback.

## Live site

https://chiuwwyne-cyber.github.io/volleyform-ai-coach/

## Highlights

- Mobile-first single-page interface
- Direct recording, playback and video upload
- 3D body pose and hand landmark analysis
- Action support for spike, block, serve, receive and set
- Focused coaching cues, drills and video recommendations
- GitHub Pages frontend with a fixed URL
- On-device MediaPipe analysis with no required backend
- Optional Render/Docker backend for shared or heavier processing
- Installable PWA shell
- Low-memory mobile analysis mode

## Run locally

```powershell
.\run_web_app.ps1
```

Open:

```text
http://127.0.0.1:8000
```

## Publish a fixed website

See [PAGES_DEPLOY.md](PAGES_DEPLOY.md).

After GitHub login, the project-local publishing helper can create the public repository and enable Pages:

```powershell
.\publish_fixed_site.ps1 -Repository volleyform-ai-coach -BackendUrl https://your-fixed-api.example
```

Deployment architecture:

```text
GitHub Pages (fixed URL)
        |
        v
MediaPipe Web pose and hand models
        |
        v
Analysis stays in the mobile browser
```

## Tests

```powershell
.\.venv\Scripts\python.exe backend\self_test.py
.\.venv\Scripts\python.exe backend\frontend_contract_test.py
.\.venv\Scripts\python.exe backend\frontend_quality_test.py
.\.venv\Scripts\python.exe backend\feedback_contract_test.py
.\.venv\Scripts\python.exe backend\resource_contract_test.py
```

```powershell
C:\Users\test\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe frontend\app_behavior_test.mjs
```

## License

MIT. See [LICENSE](LICENSE).
