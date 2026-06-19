import argparse
import cgi
import json
import os
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.analyzer import analyze_video
from backend.action_registry import available_action_options
from backend.modalities import capabilities_payload

MAX_UPLOAD_BYTES = 180 * 1024 * 1024


class VolleyballHandler(SimpleHTTPRequestHandler):
    server_version = "VolleyballCoachBackend/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({
                "ok": True,
                "service": "volleyball-ai-coach",
                "capabilities": capabilities_payload(),
            })
            return
        if path == "/api/capabilities":
            payload = capabilities_payload()
            payload["actions"] = available_action_options()
            self._send_json({"ok": True, "capabilities": payload})
            return
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/analyze":
            self.send_error(404, "API endpoint not found")
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_error(400, "Expected multipart/form-data")
            return
        if _content_length_over_limit(self.headers.get("Content-Length")):
            self.send_error(413, "Video file is too large")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )

        file_item = form["video"] if "video" in form else None
        if file_item is None or not getattr(file_item, "filename", ""):
            self.send_error(400, "Missing video file")
            return

        action = form.getfirst("action", "spike")
        frame_stride = _safe_int(form.getfirst("frame_stride", "2"), 2, 1, 8)
        process_width = _safe_int(form.getfirst("process_width", "720"), 720, 360, 900)
        max_frames = _safe_int(form.getfirst("max_frames", "240"), 240, 60, 480)
        modalities = _parse_modalities(form.getfirst("modalities", "pose,hands"))

        suffix = os.path.splitext(file_item.filename)[1] or ".mp4"
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                temp_path = tmp.name
                while True:
                    chunk = file_item.file.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)

            result = analyze_video(
                temp_path,
                action,
                process_width=process_width,
                frame_stride=frame_stride,
                max_frames=max_frames,
                modalities=modalities,
            )
            result["source_filename"] = file_item.filename
            self._send_json({"ok": True, "result": result})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _safe_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _content_length_over_limit(value):
    try:
        return int(value or 0) > MAX_UPLOAD_BYTES
    except ValueError:
        return False


def _parse_modalities(value):
    if not value:
        return []
    value = str(value).strip()
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main():
    parser = argparse.ArgumentParser(description="Volleyball AI Coach backend")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=int(os.environ.get("PORT", "8000")), type=int)
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), VolleyballHandler)
    print(f"Backend running at http://{args.host}:{args.port}")
    print("Open this URL from your phone using this computer's LAN IP.")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
