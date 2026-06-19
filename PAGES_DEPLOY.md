# Fixed Open-Source Website

The stable deployment works directly from GitHub Pages:

1. GitHub Pages hosts the mobile web UI at a fixed URL.
2. MediaPipe Web runs pose and hand analysis inside the mobile browser.
3. A Render API is optional, not required.

## Expected URLs

GitHub Pages:

```text
https://<github-owner>.github.io/<repository>/
```

Render:

```text
https://<render-service-name>.onrender.com
```

## Optional backend

For shared processing or slower phones, Render can still host the Python backend:

1. In Render, create a Blueprint from the repository.
2. Render reads `render.yaml` and `Dockerfile`.
3. Copy the resulting HTTPS URL into the GitHub `BACKEND_URL` variable.

1. Open the GitHub repository settings.
2. Under Pages, choose `GitHub Actions` as the source.
3. Leave `BACKEND_URL` empty to use private on-device analysis.
4. Push to `main` or run the `Deploy fixed website` workflow.

The workflow publishes only the `frontend` directory. All paths are relative, so the app works under a repository subpath instead of requiring the domain root.

## Mobile use

Open the GitHub Pages URL in Chrome or Safari. The app can be added to the home screen. The MediaPipe model files are hosted with the open-source site, and selected videos remain on the device.
