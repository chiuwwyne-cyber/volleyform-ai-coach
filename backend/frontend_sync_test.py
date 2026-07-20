import json
import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


def _read(*parts):
    with open(os.path.join(ROOT_DIR, *parts), "r", encoding="utf-8") as file:
        return file.read()


def test_reference_standards_are_synced_to_frontend():
    backend_reference = json.loads(_read("backend", "reference_standards.json"))
    local_analyzer = _read("frontend", "local-analyzer.js")
    match = re.search(r"const REFERENCE_STANDARDS = (\{.*?\n\});", local_analyzer, re.S)
    if not match:
        raise SystemExit("Frontend local analyzer is missing REFERENCE_STANDARDS")
    frontend_reference = json.loads(match.group(1))
    assert frontend_reference == backend_reference


def test_frontend_build_markers_are_consistent():
    build_info = json.loads(_read("frontend", "build-info.json"))
    index = _read("frontend", "index.html")
    app = _read("frontend", "app.js")
    service_worker = _read("frontend", "service-worker.js")
    build = build_info["buildVersion"]
    cache = build_info["serviceWorkerCache"]
    assert build in index
    assert build in app
    assert cache in service_worker


def test_index_replaces_stale_build_query():
    index = _read("frontend", "index.html")
    assert "requestedBuild !== currentFrontendBuild" in index
    assert "params.set(\"build\", currentFrontendBuild)" in index
    assert "window.history.replaceState" in index


def main():
    test_reference_standards_are_synced_to_frontend()
    test_frontend_build_markers_are_consistent()
    test_index_replaces_stale_build_query()
    print("frontend sync ok")
    print("checked: backend reference sync, build markers, stale build rewrite")


if __name__ == "__main__":
    main()
