import json
import os
import sys
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import cv2
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.server import VolleyballHandler
from backend.feedback import feedback_for


def _make_sample_video(path):
    writer = cv2.VideoWriter(
        path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        12,
        (320, 240),
    )
    for index in range(12):
        frame = np.full((240, 320, 3), 245, dtype=np.uint8)
        cv2.circle(frame, (160, 82 + index), 20, (45, 45, 45), -1)
        cv2.line(frame, (160, 102), (160, 162), (45, 45, 45), 4)
        cv2.line(frame, (160, 122), (112, 142), (45, 45, 45), 4)
        cv2.line(frame, (160, 122), (208, 142), (45, 45, 45), 4)
        cv2.line(frame, (160, 162), (130, 218), (45, 45, 45), 4)
        cv2.line(frame, (160, 162), (190, 218), (45, 45, 45), 4)
        writer.write(frame)
    writer.release()


def _multipart_body(fields, files):
    boundary = "----volleyball-ai-coach-test"
    chunks = []

    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    for name, file_path in files.items():
        filename = os.path.basename(file_path)
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                "Content-Type: video/mp4\r\n\r\n"
            ).encode("utf-8")
        )
        with open(file_path, "rb") as file:
            chunks.append(file.read())
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _request_json(url, data=None, content_type=None):
    body, _headers, _status = _request_raw(url, data=data, content_type=content_type)
    return json.loads(body.decode("utf-8"))


def _request_raw(url, data=None, content_type=None):
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read(), response.headers, response.status


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), VolleyballHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    temp_video = None
    try:
        index_body, index_headers, index_status = _request_raw(f"http://127.0.0.1:{port}/")
        assert index_status == 200
        assert "text/html" in index_headers.get("Content-Type", "")
        assert "VolleyForm AI Coach" in index_body.decode("utf-8")

        health = _request_json(f"http://127.0.0.1:{port}/api/health")
        assert health["ok"] is True
        assert "capabilities" in health
        capabilities_body, capabilities_headers, _status = _request_raw(
            f"http://127.0.0.1:{port}/api/capabilities"
        )
        assert capabilities_headers.get("Access-Control-Allow-Origin") == "*"
        capabilities = json.loads(capabilities_body.decode("utf-8"))
        assert capabilities["ok"] is True
        actions = capabilities["capabilities"]["actions"]
        assert isinstance(actions, list)
        assert all("id" in action and "label" in action for action in actions)
        assert {"spike", "block", "serve", "receive", "set"} <= {
            action["id"] for action in actions
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            temp_video = tmp.name
        _make_sample_video(temp_video)

        body, content_type = _multipart_body(
            {
                "action": "receive",
                "frame_stride": "2",
                "process_width": "360",
                "max_frames": "30",
                "modalities": json.dumps(["pose", "hands", "ball"]),
            },
            {"video": temp_video},
        )
        payload = _request_json(
            f"http://127.0.0.1:{port}/api/analyze",
            data=body,
            content_type=content_type,
        )
        assert payload["ok"] is True
        result = payload["result"]
        assert "score" in result
        assert "modalities" in result
        assert "modality_results" in result
        assert "coach_summary" in result
        assert "coach_plan" in result
        assert "headline" in result["coach_plan"]
        assert "next_steps" in result["coach_plan"]
        assert "ball" in result["modality_results"]["reserved"]

        receive_feedback = feedback_for("lobster_receive_risk")
        for key in ("body_part", "instant_cue", "practice_drill", "why_it_matters"):
            assert key in receive_feedback

        print("self-test ok")
        print(f"health modalities: {len(health['capabilities']['modalities'])}")
        print(f"actions: {len(capabilities['capabilities']['actions'])}")
        print(f"processed frames: {result['processed_frames']}")
    finally:
        server.shutdown()
        server.server_close()
        if temp_video and os.path.exists(temp_video):
            os.remove(temp_video)


if __name__ == "__main__":
    main()
