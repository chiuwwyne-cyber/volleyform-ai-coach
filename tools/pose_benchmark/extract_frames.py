"""Freeze the benchmark's input frames to disk, once, for every backend.

The backends do not share a Python environment (MediaPipe pins an older numpy
than the ONNX/torch models want), which means they do not share an OpenCV
build either. Decoding each clip separately in each environment would let a
codec difference masquerade as a model difference, so the frames are decoded
exactly once here and every backend is handed the same PNGs.

Frames are taken as a CONTIGUOUS window around each clip's midpoint rather
than strided across the whole clip. Strided sampling would break the temporal
tracking that MediaPipe's video mode depends on, and quietly benchmark it in a
mode VolleyForm never runs it in.
"""

import argparse
import json
import os
import sys

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contract import BENCH_WIDTH

ACTIONS = ("spike", "serve", "receive", "set", "block")


def clip_paths(dataset_dir, clips_per_action):
    for action in ACTIONS:
        action_dir = os.path.join(dataset_dir, action)
        names = sorted(n for n in os.listdir(action_dir) if n.endswith(".mp4"))
        for name in names[:clips_per_action]:
            yield action, name, os.path.join(action_dir, name)


def extract_clip(path, out_dir, window):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start = max(0, total // 2 - window // 2)

    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    os.makedirs(out_dir, exist_ok=True)

    written = []
    for i in range(window):
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        if w != BENCH_WIDTH:
            new_h = max(1, round(h * (BENCH_WIDTH / w)))
            frame = cv2.resize(frame, (BENCH_WIDTH, new_h), interpolation=cv2.INTER_AREA)
        name = f"{i:04d}.png"
        cv2.imwrite(os.path.join(out_dir, name), frame)
        written.append(name)
    cap.release()

    return {
        "source_size": [src_w, src_h],
        "source_total_frames": total,
        "start_frame": start,
        "bench_size": [frame.shape[1], frame.shape[0]] if written else None,
        "frames": written,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset")
    ap.add_argument("--out", required=True, help="directory for extracted frames")
    ap.add_argument("--clips-per-action", type=int, default=2)
    ap.add_argument("--window", type=int, default=30)
    args = ap.parse_args()

    manifest = {"bench_width": BENCH_WIDTH, "window": args.window, "clips": []}
    for action, name, path in clip_paths(args.dataset, args.clips_per_action):
        clip_id = f"{action}__{os.path.splitext(name)[0]}"
        info = extract_clip(path, os.path.join(args.out, clip_id), args.window)
        info.update({"clip_id": clip_id, "action": action, "source": path})
        manifest["clips"].append(info)
        print(f"{clip_id}: {len(info['frames'])} frames "
              f"{info['source_size'][0]}x{info['source_size'][1]} -> {info['bench_size']}")

    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"\n{len(manifest['clips'])} clips, "
          f"{sum(len(c['frames']) for c in manifest['clips'])} frames total")


if __name__ == "__main__":
    main()
