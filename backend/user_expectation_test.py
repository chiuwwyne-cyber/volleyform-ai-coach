import json
import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")


def _read(*parts):
    with open(os.path.join(ROOT_DIR, *parts), "r", encoding="utf-8") as file:
        return file.read()


def _ids_in_html(html):
    return set(re.findall(r'id="([^"]+)"', html))


def _assert_contains(source, needle, label):
    if needle not in source:
        raise SystemExit(f"Missing {label}: {needle}")


def test_user_facing_text_is_readable():
    html = _read("frontend", "index.html")
    required_text = [
        "產生 QR Code",
        "安裝到手機",
        "排球動作分析工作台",
        "本次訓練動作",
        "取得動作",
        "即時分析尚未開啟",
        "開始錄影",
        "開始 AI 分析",
        "分析結果",
        "姿勢比對",
    ]
    for text in required_text:
        _assert_contains(html, text, "readable Traditional Chinese UI text")
    if "\ufffd" in html:
        raise SystemExit("Frontend contains replacement characters, likely mojibake")


def test_core_sports_app_expectations_are_present():
    html = _read("frontend", "index.html")
    js = _read("frontend", "app.js")
    local_analyzer = _read("frontend", "local-analyzer.js")
    service_worker = _read("frontend", "service-worker.js")
    manifest = json.loads(_read("frontend", "manifest.webmanifest"))
    api_contract = _read("API_CONTRACT.md")
    ids = _ids_in_html(html)

    required_ids = {
        "shareQrBtn",
        "installAppBtn",
        "backendUrl",
        "action",
        "actionChoices",
        "powerMode",
        "video",
        "recordPreview",
        "imagePreview",
        "poseOverlay",
        "startLiveBtn",
        "stopLiveBtn",
        "startRecordBtn",
        "stopRecordBtn",
        "clearRecordBtn",
        "analyzeBtn",
        "coachSummary",
        "coachPlan",
        "issues",
        "poseCompareActual",
        "poseCompareCorrected",
        "poseViewToggle",
        "modalityList",
    }
    missing_ids = sorted(required_ids - ids)
    if missing_ids:
        raise SystemExit(f"Missing expected public-beta UI controls: {missing_ids}")

    for action in ("spike", "block", "serve", "receive", "set"):
        _assert_contains(js, action, f"{action} action support")
        _assert_contains(api_contract, action, f"{action} API support")

    expected_capabilities = {
        "mobile upload": 'accept="video/*,image/*"',
        "direct recording": "navigator.mediaDevices.getUserMedia",
        "recorded playback": "recordPreview.controls = true",
        "short mobile recording": "maxRecordingMs = 12000",
        "low-power profile": 'mobile: { frame_stride: "4", process_width: "480", max_frames: "150" }',
        "realtime analysis": "startRealtimeAnalysis",
        "on-device local analysis": "analyzeMediaLocally",
        "3D pose comparison": "createPoseViewport",
        "front/side view switch": "poseViewToggle",
        "coach video links": "video-link",
        "QR sharing": "resolveShareUrl",
        "fresh launcher share config": "runtime-share.json",
        "PWA registration": "serviceWorker.register",
        "accepted angle range": "accepted_range",
        "reference convergence": "convergence",
    }
    combined = "\n".join([html, js, local_analyzer, api_contract])
    for label, needle in expected_capabilities.items():
        _assert_contains(combined, needle, label)

    if manifest.get("display") != "standalone" or not manifest.get("icons"):
        raise SystemExit("PWA manifest must support installable standalone mode")
    if "volleyform-shell-v" not in service_worker or "cache.addAll(APP_SHELL)" not in service_worker:
        raise SystemExit("Service worker must cache the app shell for mobile/offline use")


def test_public_beta_gaps_are_known_not_hidden():
    readme = _read("README.md")
    app = _read("frontend", "app.js")
    advanced_gaps = {
        "cloud athlete library": "Optional Render/Docker backend" in readme,
        "voice-over annotation": "voice" in app.lower(),
        "multi-camera capture": "multicam" in app.lower() or "multi-cam" in app.lower(),
        "manual drawing tools": "draw" in app.lower() and "annotate" in app.lower(),
    }
    # These are not required for this public beta, but keeping the list explicit
    # prevents us from overstating the app as a full team film platform.
    assert advanced_gaps["cloud athlete library"]
    assert not advanced_gaps["voice-over annotation"]
    assert not advanced_gaps["multi-camera capture"]
    assert not advanced_gaps["manual drawing tools"]


def main():
    test_user_facing_text_is_readable()
    test_core_sports_app_expectations_are_present()
    test_public_beta_gaps_are_known_not_hidden()
    print("user expectation ok")
    print("checked: mobile capture, replay, realtime, 3D compare, feedback, sharing, PWA")
    print("known advanced gaps: voice-over, multicam, drawing annotation")


if __name__ == "__main__":
    main()
