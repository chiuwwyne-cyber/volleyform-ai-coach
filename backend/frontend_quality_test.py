import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
HTML_PATH = os.path.join(ROOT_DIR, "frontend", "index.html")
CSS_PATH = os.path.join(ROOT_DIR, "frontend", "styles.css")
JS_PATH = os.path.join(ROOT_DIR, "frontend", "app.js")
MANIFEST_PATH = os.path.join(ROOT_DIR, "frontend", "manifest.webmanifest")
SERVICE_WORKER_PATH = os.path.join(ROOT_DIR, "frontend", "service-worker.js")
PAGES_WORKFLOW_PATH = os.path.join(ROOT_DIR, ".github", "workflows", "pages.yml")
RENDER_PATH = os.path.join(ROOT_DIR, "render.yaml")


def _read(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def _css_vars(css):
    pairs = re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", css)
    return {name: value for name, value in pairs}


def _relative_luminance(hex_color):
    value = hex_color.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]

    def normalize(channel):
        if channel <= 0.03928:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = [normalize(channel) for channel in channels]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(foreground, background):
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter = max(first, second)
    darker = min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _assert_contrast(name, foreground, background, minimum=4.5):
    ratio = _contrast_ratio(foreground, background)
    if ratio < minimum:
        raise SystemExit(
            f"{name} contrast too low: {ratio:.2f}, expected at least {minimum}"
        )


def main():
    html = _read(HTML_PATH)
    css = _read(CSS_PATH)
    js = _read(JS_PATH)
    local_analyzer = _read(os.path.join(ROOT_DIR, "frontend", "local-analyzer.js"))
    manifest = _read(MANIFEST_PATH)
    service_worker = _read(SERVICE_WORKER_PATH)
    pages_workflow = _read(PAGES_WORKFLOW_PATH)
    render_config = _read(RENDER_PATH)
    tokens = _css_vars(css)

    required_tokens = {
        "bg",
        "surface",
        "panel",
        "ink",
        "muted",
        "line",
        "court",
        "court-dark",
        "blue",
        "link",
        "green",
        "red",
        "gold",
    }
    missing_tokens = sorted(required_tokens - set(tokens))
    if missing_tokens:
        raise SystemExit(f"Missing design tokens: {', '.join(missing_tokens)}")

    _assert_contrast("main text", tokens["ink"], tokens["panel"])
    _assert_contrast("secondary text", tokens["muted"], tokens["panel"])
    _assert_contrast("primary button", "#ffffff", tokens["blue"])
    _assert_contrast("topbar dark", "#ffffff", tokens["court-dark"])
    _assert_contrast("topbar warm", "#ffffff", tokens["court"])
    _assert_contrast("link", tokens["link"], tokens["panel"])

    if "@media (max-width: 860px)" not in css:
        raise SystemExit("Missing mobile responsive breakpoint")
    if "letter-spacing: -" in css:
        raise SystemExit("Negative letter-spacing is not allowed")
    if "font-size: clamp" in css or "font-size: calc" in css:
        raise SystemExit("Font size must not scale with viewport width")
    if "font-family" not in css or "Microsoft JhengHei" not in css:
        raise SystemExit("Missing consistent Chinese UI font stack")
    if 'id="serverStatus" role="status" aria-live="polite"' not in html:
        raise SystemExit("Server status must announce connection changes")
    if 'id="coachPlan" class="coach-plan empty" role="status" aria-live="polite"' not in html:
        raise SystemExit("Coach plan must announce priority guidance")
    if 'id="analyzeBtn" type="button"' not in html:
        raise SystemExit("Analyze button must declare button type")
    if "apiUrl(\"/api/capabilities\")" not in js or "renderActionOptions" not in js:
        raise SystemExit("Frontend must discover actions and modalities from backend capabilities")
    if 'id="backendUrl"' not in html or "volleyballCoachBackendUrl" not in js:
        raise SystemExit("Frontend must let remote web/mobile clients configure backend URL")
    if "手機本地 AI" not in html or "影片不需上傳" not in html:
        raise SystemExit("Frontend must explain private on-device mobile analysis")
    if 'href="./styles.css"' not in html or 'src="./app.js"' not in html:
        raise SystemExit("Frontend assets must use relative paths for GitHub Pages subpaths")
    if 'id="actionChoices"' not in html or "renderActionChoices" not in js:
        raise SystemExit("Action selection must support direct mouse/touch buttons")
    if "./manifest.webmanifest" not in html or "serviceWorker.register" not in js:
        raise SystemExit("Frontend must be installable as a mobile PWA")
    if "coach-header.png" not in html or not os.path.exists(
        os.path.join(ROOT_DIR, "frontend", "assets", "coach-header.png")
    ):
        raise SystemExit("Frontend must include a project-local original visual asset")
    if "start_url" not in manifest or "APP_SHELL" not in service_worker:
        raise SystemExit("PWA manifest and offline shell must be configured")
    if "PoseLandmarker" not in local_analyzer or "HandLandmarker" not in local_analyzer:
        raise SystemExit("Fixed site must include local MediaPipe pose and hand analysis")
    if "detectForVideo" not in local_analyzer or "analyzeMediaLocally" not in js:
        raise SystemExit("Frontend must fall back to local photo/video analysis without a backend")
    if 'accept="video/*,image/*"' not in html or "analyzeImageLocally" not in local_analyzer:
        raise SystemExit("Mobile users must be able to select and analyze album photos")
    if "startRealtimeAnalysis" not in local_analyzer or 'id="startLiveBtn"' not in html:
        raise SystemExit("Frontend must support on-device realtime camera analysis")
    if 'id="poseOverlay"' not in html or ".live-feedback" not in css:
        raise SystemExit("Realtime landmarks and coaching feedback must have dedicated UI")
    if "actions/deploy-pages" not in pages_workflow or "BACKEND_URL" not in pages_workflow:
        raise SystemExit("GitHub Pages workflow must publish the fixed site and API config")
    if "volleyform-ai-api" not in render_config or "healthCheckPath" not in render_config:
        raise SystemExit("Render blueprint must define the fixed public backend")
    if "MediaRecorder" not in js or 'id="recordPreview"' not in html:
        raise SystemExit("Frontend must support direct recording and playback when available")
    if ".connection-panel" not in css or ".utility-btn" not in css:
        raise SystemExit("Remote connection UI must be styled consistently")
    if ".capture-panel" not in css or ".record-actions" not in css:
        raise SystemExit("Recording UI must be styled consistently")
    if 'class="workspace-header"' not in html or ".workspace-badges" not in css:
        raise SystemExit("Frontend must present the analysis workspace before configuration")
    if "4 個分析維度" in html or "拆成 4 個維度" in html:
        raise SystemExit("Design evaluation dimensions must not be shown as product content")
    if "renderCoachPlan" not in js or "instant_cue" not in js or "practice_drill" not in js:
        raise SystemExit("Frontend must render clear coach guidance fields")
    if ".coach-plan" not in css or ".issue-meta" not in css or ".drill-box" not in css:
        raise SystemExit("Frontend must style clear coach guidance fields")
    action_select = re.search(
        r'<select id="action"[^>]*>(?P<body>.*?)</select>',
        html,
        flags=re.DOTALL,
    )
    if not action_select:
        raise SystemExit("Missing action select")
    if action_select.group("body").count("<option value=") > 1:
        raise SystemExit("Action options should be supplied by backend capabilities, not hardcoded")

    print("frontend quality ok")
    print(f"contrast checks: 6")
    print(f"design tokens: {len(required_tokens)}")


if __name__ == "__main__":
    main()
