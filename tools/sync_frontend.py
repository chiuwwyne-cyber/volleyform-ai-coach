"""Synchronize backend-derived standards and frontend cache build markers.

This keeps the GitHub Pages app from serving stale JavaScript after backend
calibration changes. It is intentionally stdlib-only so launch/publish scripts
can run it before opening or deploying the app.
"""

import argparse
import json
import os
import re
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
REFERENCE_PATH = ROOT_DIR / "backend" / "reference_standards.json"
LOCAL_ANALYZER_PATH = ROOT_DIR / "frontend" / "local-analyzer.js"
INDEX_PATH = ROOT_DIR / "frontend" / "index.html"
APP_PATH = ROOT_DIR / "frontend" / "app.js"
SERVICE_WORKER_PATH = ROOT_DIR / "frontend" / "service-worker.js"
BUILD_INFO_PATH = ROOT_DIR / "frontend" / "build-info.json"

BUILD_RE = re.compile(r"20\d{6}-[A-Za-z0-9-]+-v(\d+)")
SERVICE_WORKER_RE = re.compile(r'volleyform-shell-v(\d+)')
REFERENCE_RE = re.compile(r"const REFERENCE_STANDARDS = \{.*?\n\};", re.S)


def _read(path):
    return path.read_text(encoding="utf-8")


def _write_if_changed(path, content):
    if path.exists() and _read(path) == content:
        return False
    path.write_text(content, encoding="utf-8", newline="")
    return True


def _current_cache_version():
    versions = []
    for path in (INDEX_PATH, APP_PATH, SERVICE_WORKER_PATH):
        if not path.exists():
            continue
        text = _read(path)
        versions.extend(int(match.group(1)) for match in BUILD_RE.finditer(text))
        versions.extend(int(match.group(1)) for match in SERVICE_WORKER_RE.finditer(text))
    return max(versions) if versions else 0


def _build_label(version):
    return f"{date.today().strftime('%Y%m%d')}-frontend-sync-v{version}"


def _replace_build_markers(text, build_label):
    text = re.sub(r"20\d{6}-[A-Za-z0-9-]+-v\d+", build_label, text)
    return text


def _replace_service_worker_cache(text, version):
    return SERVICE_WORKER_RE.sub(f"volleyform-shell-v{version}", text)


def _sync_reference():
    reference = json.loads(_read(REFERENCE_PATH))
    replacement = (
        "const REFERENCE_STANDARDS = "
        + json.dumps(reference, ensure_ascii=False, indent=2)
        + ";"
    )
    source = _read(LOCAL_ANALYZER_PATH)
    updated, count = REFERENCE_RE.subn(replacement, source, count=1)
    if count != 1:
        raise SystemExit("Could not find exactly one REFERENCE_STANDARDS block")
    return _write_if_changed(LOCAL_ANALYZER_PATH, updated)


def sync_frontend(root_dir=ROOT_DIR, build_label=None, bump_if_changed=True):
    os.chdir(root_dir)
    reference_changed = _sync_reference()
    current_version = _current_cache_version()
    next_version = current_version + 1 if reference_changed and bump_if_changed else current_version
    if next_version <= 0:
        next_version = 1
    build_label = build_label or _build_label(next_version)

    changed = reference_changed
    for path in (INDEX_PATH, APP_PATH):
        changed |= _write_if_changed(path, _replace_build_markers(_read(path), build_label))

    sw = _replace_build_markers(_read(SERVICE_WORKER_PATH), build_label)
    sw = _replace_service_worker_cache(sw, next_version)
    changed |= _write_if_changed(SERVICE_WORKER_PATH, sw)

    info = {
        "buildVersion": build_label,
        "serviceWorkerCache": f"volleyform-shell-v{next_version}",
        "referenceSource": "backend/reference_standards.json",
        "generatedAt": date.today().isoformat(),
    }
    changed |= _write_if_changed(
        BUILD_INFO_PATH,
        json.dumps(info, ensure_ascii=False, indent=2) + "\n",
    )
    return {"changed": changed, "buildVersion": build_label, "cacheVersion": next_version}


def main():
    parser = argparse.ArgumentParser(description="Synchronize backend standards into frontend assets")
    parser.add_argument("--build", default="", help="Explicit frontend build label")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    result = sync_frontend(build_label=args.build or None)
    if not args.quiet:
        status = "changed" if result["changed"] else "already current"
        print(f"frontend sync {status}: {result['buildVersion']}")


if __name__ == "__main__":
    main()
