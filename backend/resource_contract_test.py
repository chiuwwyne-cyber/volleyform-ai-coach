import os

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


def _read(relative_path):
    with open(os.path.join(ROOT_DIR, relative_path), "r", encoding="utf-8") as file:
        return file.read()


def main():
    analyzer = _read(os.path.join("backend", "analyzer.py"))
    pose = _read(os.path.join("pose", "pose.py"))
    app = _read(os.path.join("frontend", "app.js"))
    server = _read(os.path.join("backend", "server.py"))
    tunnel = _read("run_remote_tunnel.ps1")
    installer = _read("install_cloudflared.ps1")
    dockerfile = _read("Dockerfile")
    procfile = _read("Procfile")
    cloud_doc = _read("CLOUD_DEPLOY.md")
    pages_workflow = _read(os.path.join(".github", "workflows", "pages.yml"))
    frontend_config = _read(os.path.join("frontend", "config.js"))
    service_worker = _read(os.path.join("frontend", "service-worker.js"))
    gitignore = _read(".gitignore")
    publish_script = _read("publish_fixed_site.ps1")

    if "include_image=False" not in analyzer:
        raise SystemExit("Backend analyzer must disable frame images during API analysis")
    if "include_image=True" not in pose or "output_image = None" not in pose:
        raise SystemExit("Pose stream must support landmark-only analysis")
    if "timeline.pop(0)" not in analyzer or "TIMELINE_LIMIT" not in analyzer:
        raise SystemExit("Timeline must be bounded without copying the full list repeatedly")
    if "recordedChunks = []" not in app or "URL.revokeObjectURL" not in app:
        raise SystemExit("Frontend recording must release chunks and object URLs")
    if "maxRecordingMs = 12000" not in app or "recordingVideoBitsPerSecond = 1600000" not in app:
        raise SystemExit("Frontend recording must limit duration and bitrate")
    if "mediaRecorder.start(recordingTimesliceMs)" not in app:
        raise SystemExit("Frontend recording must request periodic chunks")
    if 'mobile: { frame_stride: "4", process_width: "480", max_frames: "150" }' not in app:
        raise SystemExit("Mobile analysis mode must use reduced processing settings")
    if "MAX_UPLOAD_BYTES = 180 * 1024 * 1024" not in server or "_content_length_over_limit" not in server:
        raise SystemExit("Backend must reject oversized uploads before parsing")
    if 'os.environ.get("PORT", "8000")' not in server:
        raise SystemExit("Backend must support cloud PORT environment variable")
    if "TIMELINE_LIMIT = 24" not in analyzer:
        raise SystemExit("Timeline limit must stay small for mobile-friendly responses")
    if "tools\\cloudflared.exe" not in tunnel or "install_cloudflared.ps1" not in tunnel:
        raise SystemExit("Remote tunnel script must support the project-local cloudflared install")
    if "$MaxAttempts = 3" not in tunnel or "--no-autoupdate" not in tunnel:
        raise SystemExit("Remote tunnel script must retry quick tunnel startup without autoupdate")
    if "cloudflared-windows-amd64.exe" not in installer or "tools" not in installer:
        raise SystemExit("Cloudflared installer must download a project-local executable")
    if "python:3.11-slim" not in dockerfile or "backend/server.py" not in dockerfile:
        raise SystemExit("Dockerfile must run the backend web server")
    if "web: python backend/server.py --host 0.0.0.0" not in procfile:
        raise SystemExit("Procfile must expose the backend web server")
    if "PORT" not in cloud_doc or "Dockerfile" not in cloud_doc:
        raise SystemExit("Cloud deployment guide must document public hosting")
    if "actions/deploy-pages" not in pages_workflow or "BACKEND_URL" not in pages_workflow:
        raise SystemExit("GitHub Pages deployment must inject the fixed backend URL")
    if "apiBase" not in frontend_config or "serviceWorker.register" not in app:
        raise SystemExit("Frontend must support fixed API config and PWA installation")
    if "APP_SHELL" not in service_worker or "coach-header.png" not in service_worker:
        raise SystemExit("Service worker must cache the mobile app shell and visual asset")
    if "tools/cloudflared.exe" not in gitignore or ".venv/" not in gitignore:
        raise SystemExit("Open-source repository must exclude local binaries and environments")
    if "repo create" not in publish_script or "workflow run pages.yml" not in publish_script:
        raise SystemExit("Publishing helper must create the public repo and trigger Pages")

    print("resource contract ok")
    print("checks: mobile resources, remote tunnel, fixed Pages site, cloud deploy, PWA")


if __name__ == "__main__":
    main()
