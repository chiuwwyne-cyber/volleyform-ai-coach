import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
HTML_PATH = os.path.join(ROOT_DIR, "frontend", "index.html")
JS_PATH = os.path.join(ROOT_DIR, "frontend", "app.js")


def _ids_in_html(html):
    return set(re.findall(r'id="([^"]+)"', html))


def _selectors_in_js(js):
    return set(re.findall(r'querySelector\("#([^"]+)"\)', js))


def main():
    with open(HTML_PATH, "r", encoding="utf-8") as file:
        html = file.read()
    with open(JS_PATH, "r", encoding="utf-8") as file:
        js = file.read()

    ids = _ids_in_html(html)
    selectors = _selectors_in_js(js)
    missing = sorted(selectors - ids)
    if missing:
        raise SystemExit(f"Missing DOM ids used by app.js: {', '.join(missing)}")

    required = {
        "serverStatus",
        "backendUrl",
        "sameOriginBtn",
        "localBackendBtn",
        "healthCheckBtn",
        "connectionNote",
        "action",
        "actionChoices",
        "powerMode",
        "video",
        "analyzeBtn",
        "previewPlaceholder",
        "analysisSummary",
        "installAppBtn",
        "recordPreview",
        "recordStatus",
        "startRecordBtn",
        "stopRecordBtn",
        "clearRecordBtn",
        "coachPlan",
        "issues",
        "timeline",
        "modalityList",
        "modalityResults",
    }
    absent = sorted(required - ids)
    if absent:
        raise SystemExit(f"Missing required UI ids: {', '.join(absent)}")

    print("frontend contract ok")
    print(f"checked ids: {len(selectors)}")


if __name__ == "__main__":
    main()
