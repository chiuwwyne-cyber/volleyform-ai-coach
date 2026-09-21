"""Reconcile RTMPose's measured speed with its published speed.

The headline in the literature - RTMPose-m at 70-90 FPS on a CPU - is the POSE
HEAD alone, timed on a pre-cropped person box. A deployed system has to find
the person first, and rtmlib's presets bundle a YOLOX detector to do it. If the
measured end-to-end figure is far off the published one, the detector is the
first suspect, and this settles it by timing the two stages separately instead
of arguing about it.

ONE PRESET PER PROCESS, deliberately. Each ONNX Runtime session spins up its
own thread pool sized to the machine, so holding three presets open at once
oversubscribes the CPU several times over and inflates every number. An earlier
version of this script did exactly that and reported a 597 ms detector that
measures 182 ms when it has the machine to itself. Loop over presets in the
shell, not in here.

Run in the benchmark venv, with nothing else competing for the CPU.
"""

import argparse
import json
import os
import statistics
import time

import cv2


def load_frames(frames_dir, limit):
    with open(os.path.join(frames_dir, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)

    paths, meta = [], []
    for clip in manifest["clips"]:
        for name in clip["frames"]:
            paths.append(os.path.join(frames_dir, clip["clip_id"], name))
            meta.append(clip["clip_id"])

    if limit and limit < len(paths):
        # Take an even stride so every clip stays represented.
        step = len(paths) / limit
        picked = [int(i * step) for i in range(limit)]
        paths = [paths[i] for i in picked]
        meta = [meta[i] for i in picked]

    return [cv2.imread(p) for p in paths], meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--mode", required=True,
                    choices=["lightweight", "balanced", "performance"])
    ap.add_argument("--out")
    ap.add_argument("--limit", type=int, default=0, help="0 = every frame")
    ap.add_argument("--warmup", type=int, default=5)
    args = ap.parse_args()

    from rtmlib.tools.solution.body import Body

    frames, _ = load_frames(args.frames, args.limit)
    body = Body(mode=args.mode, backend="onnxruntime", device="cpu")
    det, pose = body.det_model, body.pose_model

    for frame in frames[:args.warmup]:
        boxes = det(frame)
        if len(boxes):
            pose(frame, bboxes=boxes)

    det_ms, pose_ms, n_boxes = [], [], []
    for frame in frames:
        t0 = time.perf_counter()
        boxes = det(frame)
        t1 = time.perf_counter()
        if len(boxes):
            pose(frame, bboxes=boxes)
        t2 = time.perf_counter()
        det_ms.append((t1 - t0) * 1000)
        pose_ms.append((t2 - t1) * 1000)
        n_boxes.append(len(boxes))

    row = {
        "mode": args.mode,
        "frames": len(frames),
        "median_det_ms": statistics.median(det_ms),
        "median_pose_ms": statistics.median(pose_ms),
        "median_total_ms": statistics.median([d + p for d, p in zip(det_ms, pose_ms)]),
        "median_boxes": statistics.median(n_boxes),
        "median_pose_ms_per_person": statistics.median(
            [p / b for p, b in zip(pose_ms, n_boxes) if b]),
        "detector_share_pct": 100 * statistics.median(det_ms) / statistics.median(
            [d + p for d, p in zip(det_ms, pose_ms)]),
    }

    print("{:12s} n={:3d}  det {:7.1f} ms + pose {:6.1f} ms = {:7.1f} ms "
          "({:4.1f} FPS)  detector is {:.0f}% of it  |  {:.0f} people, "
          "{:.1f} ms/person".format(
              row["mode"], row["frames"], row["median_det_ms"],
              row["median_pose_ms"], row["median_total_ms"],
              1000 / row["median_total_ms"], row["detector_share_pct"],
              row["median_boxes"], row["median_pose_ms_per_person"]))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(row, fh, indent=2)


if __name__ == "__main__":
    main()
