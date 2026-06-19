# Fixed Open-Source Website

The stable deployment has two parts:

1. GitHub Pages hosts the mobile web UI at a fixed URL.
2. Render hosts the Python/MediaPipe API at a fixed HTTPS URL.

## Expected URLs

GitHub Pages:

```text
https://<github-owner>.github.io/<repository>/
```

Render:

```text
https://<render-service-name>.onrender.com
```

## Publish the backend

1. Push this repository to a public GitHub repository.
2. In Render, create a new Blueprint from the repository.
3. Render reads `render.yaml` and `Dockerfile`.
4. Wait until `/api/health` returns HTTP 200.
5. Copy the Render HTTPS URL.

## Publish the fixed frontend

1. Open the GitHub repository settings.
2. Under Pages, choose `GitHub Actions` as the source.
3. Add a repository variable named `BACKEND_URL`.
4. Set `BACKEND_URL` to the Render HTTPS URL.
5. Push to `main` or run the `Deploy fixed website` workflow.

The workflow publishes only the `frontend` directory. All paths are relative, so the app works under a repository subpath instead of requiring the domain root.

## Mobile use

Open the GitHub Pages URL in Chrome or Safari. The app can be added to the home screen. The page shell remains available offline, while video analysis still requires internet access to the fixed Render API.
