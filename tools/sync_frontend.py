"""Synchronize backend-derived standards and frontend cache build markers.

This keeps the GitHub Pages app from serving stale JavaScript after backend
calibration changes. It is intentionally stdlib-only so launch/publish scripts
can run it before opening or deploying the app.
"""

import argparse
import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"
REFERENCE_PATH = ROOT_DIR / "backend" / "reference_standards.json"
LOCAL_ANALYZER_PATH = ROOT_DIR / "frontend" / "local-analyzer.js"
INDEX_PATH = ROOT_DIR / "frontend" / "index.html"
APP_PATH = ROOT_DIR / "frontend" / "app.js"
SERVICE_WORKER_PATH = ROOT_DIR / "frontend" / "service-worker.js"
BUILD_INFO_PATH = ROOT_DIR / "frontend" / "build-info.json"

BUILD_RE = re.compile(r"20\d{6}-[A-Za-z0-9-]+-v(\d+)")
# The cache name carries a content digest suffix as well as the counter, so two
# different frontends can never share a cache name even if the counter repeats
# (which happens when an asset change is committed without running this script:
# CI then bumps from the same stale base twice). Same name + byte-identical
# service-worker.js means the browser never reinstalls the worker, activate()
# never purges, and every cache-first asset stays stale forever.
SERVICE_WORKER_RE = re.compile(r'volleyform-shell-v(\d+)(?:-[0-9a-f]{8})?')
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


def _cache_name(version, fingerprint):
    return f"volleyform-shell-v{version}-{fingerprint[:8]}"


def _replace_service_worker_cache(text, version, fingerprint):
    return SERVICE_WORKER_RE.sub(_cache_name(version, fingerprint), text)


def _app_shell_files():
    """Every frontend file the service worker can serve from cache.

    APP_SHELL is precached, but the fetch handler also caches anything else
    same-origin that is not network-first -- the vendored libraries (MediaPipe
    wasm, Three.js, the QR lib) and the MediaPipe .task models. Those are
    requested WITHOUT a ?v= build parameter and hit the cache-first branch, so
    if they were left out of the fingerprint a vendor or model upgrade would
    bump nothing and clients would keep the old copy for as long as the cache
    name stayed the same. They are large but rarely change, and hashing them
    costs a fraction of a second.
    """
    text = _read(SERVICE_WORKER_PATH)
    match = re.search(r"const APP_SHELL = \[(.*?)\]", text, re.S)
    paths = []
    if match:
        for entry in re.findall(r'"([^"]+)"', match.group(1)):
            rel = entry.lstrip("./")
            if rel:  # skip the "./" root entry
                paths.append(FRONTEND_DIR / rel)
    for extra_dir in ("vendor", "models"):
        root = FRONTEND_DIR / extra_dir
        if root.is_dir():
            paths.extend(path for path in root.rglob("*") if path.is_file())
    return paths


def _frontend_fingerprint():
    """Content hash of the cached frontend files, version markers normalized.

    Bumping the cache version rewrites the build/cache strings inside the
    shell files, so those markers are stripped before hashing; otherwise every
    bump would change the fingerprint and trigger another bump forever.
    """
    digest = hashlib.sha256()
    paths = list(_app_shell_files()) + [SERVICE_WORKER_PATH]
    for path in sorted(set(paths), key=lambda p: str(p)):
        if not path.exists():
            continue
        # Hash the REPO-RELATIVE path, posix-normalized. Absolute paths differ
        # between this machine and the Linux CI runner, which made the CI's
        # fingerprint never match the committed one: CI then bumped the cache
        # version on every deploy, so the deployed version was always one ahead
        # of main. That is not cosmetic -- it lets a later deploy reuse a cache
        # name that clients already hold, and cache-first assets
        # (krunk-parts.json, icons, manifest) would then never refresh.
        rel = path.relative_to(ROOT_DIR).as_posix()
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
            # Normalize line endings so a git autocrlf checkout (LF->CRLF) does
            # not change the hash and cause a spurious cache bump.
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = BUILD_RE.sub("BUILD", text)
            text = SERVICE_WORKER_RE.sub("shell", text)
            data = text.encode("utf-8")
        except UnicodeDecodeError:
            pass  # binary asset (icons/images): hash the raw bytes
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
    return digest.hexdigest()


def _stored_fingerprint():
    try:
        info = json.loads(_read(BUILD_INFO_PATH))
        return info.get("shellFingerprint")
    except (OSError, ValueError):
        return None


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
    # Any change to a cached frontend file (JS/CSS, the Krunk model asset,
    # icons, ...) — not just recalibrated standards — must bump the cache so
    # clients stop serving the stale service-worker copy. Compare a normalized
    # content fingerprint against the one recorded in the last build-info.json.
    fingerprint = _frontend_fingerprint()
    stored_fingerprint = _stored_fingerprint()
    assets_changed = stored_fingerprint is not None and stored_fingerprint != fingerprint
    current_version = _current_cache_version()
    should_bump = (reference_changed or assets_changed) and bump_if_changed
    next_version = current_version + 1 if should_bump else current_version
    if next_version <= 0:
        next_version = 1
    build_label = build_label or _build_label(next_version)

    changed = reference_changed
    for path in (INDEX_PATH, APP_PATH):
        changed |= _write_if_changed(path, _replace_build_markers(_read(path), build_label))

    sw = _replace_build_markers(_read(SERVICE_WORKER_PATH), build_label)
    sw = _replace_service_worker_cache(sw, next_version, fingerprint)
    changed |= _write_if_changed(SERVICE_WORKER_PATH, sw)

    info = {
        "buildVersion": build_label,
        "serviceWorkerCache": _cache_name(next_version, fingerprint),
        "referenceSource": "backend/reference_standards.json",
        "shellFingerprint": fingerprint,
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
