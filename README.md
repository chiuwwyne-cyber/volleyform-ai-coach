# VolleyForm AI Coach

VolleyForm is an open-source volleyball motion analysis web app. It uses MediaPipe 3D pose and hand landmarks to review uploaded or recorded videos and returns focused coaching feedback.

## Live site

https://chiuwwyne-cyber.github.io/volleyform-ai-coach/

## Highlights

- Mobile-first single-page interface
- Mobile album photo/video upload, recording and playback
- Low-power realtime camera analysis with live joint overlays
- 3D body pose and hand landmark analysis
- Action support for spike, block, serve, receive and set
- Focused coaching cues, drills and video recommendations
- GitHub Pages frontend with a fixed base URL and a fresh launch URL each run
- On-device MediaPipe analysis with no required backend
- Optional Render/Docker backend for shared or heavier processing
- Installable PWA shell
- Low-memory mobile analysis mode

## Run locally

Double-click [VolleyForm.bat](VolleyForm.bat) (or the desktop shortcut it creates) to start the backend, try to start a public Cloudflare backend tunnel, and open the public open-source frontend automatically. The launcher opens the GitHub Pages URL, not `127.0.0.1`, so the in-page QR Code can be scanned by a phone.

Every launch creates a fresh URL with `session=` and, when Cloudflare Tunnel is available, the current `backend=` address. This matters when the computer changes networks and the temporary backend URL changes. The launcher also updates a desktop shortcut named `VolleyForm 本次網址.url` so the latest phone/share URL is always easy to reopen.

Or run it manually:

```powershell
.\run_web_app.ps1
```

Open:

```text
https://chiuwwyne-cyber.github.io/volleyform-ai-coach/
```

The local `127.0.0.1:8000` address is only used internally for the backend API and tunnel origin; the user-facing frontend and QR Code use the fresh public launch URL.

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
