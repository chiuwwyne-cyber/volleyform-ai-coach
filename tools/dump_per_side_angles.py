"""Dump LEFT and RIGHT joint angles separately, to measure the aggregation divergence.

angle/angle.py combines the two sides as elbow/shoulder = max(left, right) and
knee = min(...). local-analyzer.js averages them instead. The reference bands were
built with the backend convention and the browser applies them with a different one,
which is a known divergence that evaluation_parity_test.mjs pins but nobody had ever
put a number on.

This puts a number on it. Measured on the 38 block and set clips, switching to the
averaged estimator moves the contact-frame reading enough to change the verdict on
several clips -- and every one of those clips is assumed-correct footage, so every
flip is a false positive on the path real users are on.

Kept because fixing that divergence is the next piece of work, and this is how to
tell whether the fix helped.

Usage:
    .venv/Scripts/python.exe tools/dump_per_side_angles.py [out.json]
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from angle.angle import calculate_angle_3d, get_angles, _best_landmarks
from backend.phase_segmentation import segment_action
from pose.pose import get_pose_from_video
from tools.build_reference import (
    DATASET_DIR,
    MAX_FRAMES,
    _joint_is_offscreen_guess,
    _load_phase_scope,
)

# Which action/phase/joints to scan. block and set are the two where elbow and
# shoulder are most strongly coupled (r=0.87 and r=0.74), so they are where a
# change of estimator moves the pair furthest. Add actions here to widen the scan.
SCAN_TARGETS = {
    "block": ("contact", ("elbow", "shoulder")),
    "set": ("contact", ("elbow", "shoulder")),
}


def _scan(video_path):
    """Like build_reference._process_clip, but KEEPS the world landmarks.

    _process_clip drops them after handing them to get_angles. That is fine when
    all you want is the aggregated angle, but per-side angles have to be measured
    on the same points get_angles used -- and get_angles measures on world
    landmarks. Recomputing from image landmarks instead would silently produce a
    different number and make this whole comparison meaningless.
    """
    frames = []
    for pose_data in get_pose_from_video(
        video_path, process_width=640, frame_stride=2, include_image=False
    ):
        if len(frames) >= MAX_FRAMES:
            break
        if len(pose_data) == 4:
            landmarks, world_landmarks, _frame, _hands = pose_data
        else:
            landmarks, world_landmarks, _frame = pose_data
        frames.append({
            "landmarks": landmarks,
            "world": world_landmarks,
            "angles": get_angles(landmarks, world_landmarks),
        })
    return frames

# Mirrored from angle/angle.py and local-analyzer.js -- both read the same triples,
# they only disagree about how to combine the two sides.
TRIPLES = {
    "elbow": {"left": (11, 13, 15), "right": (12, 14, 16)},
    "shoulder": {"left": (13, 11, 23), "right": (14, 12, 24)},
}

DEFAULT_OUT = os.path.join(ROOT_DIR, "dataset", "per_side_angles.json")


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    phase_scope = _load_phase_scope()
    rows = []

    for action, (phase, joints) in SCAN_TARGETS.items():
        action_dir = os.path.join(DATASET_DIR, action)
        if not os.path.isdir(action_dir):
            continue
        for clip_name in sorted(n for n in os.listdir(action_dir) if n.lower().endswith(".mp4")):
            print(f"[{action}] {clip_name} ...", flush=True)
            frames = _scan(os.path.join(action_dir, clip_name))
            segments = segment_action(action, [f["landmarks"] for f in frames])
            if not segments:
                continue
            index = segments.get(phase)
            if index is None:
                continue
            allowed = phase_scope.get(f"{action}/{clip_name}")
            if allowed is not None and phase not in allowed:
                continue

            landmarks = frames[index]["landmarks"]
            # world landmarks are what get_angles actually measures on
            points = _best_landmarks(landmarks, frames[index].get("world"))
            row = {"action": action, "clip": clip_name, "phase": phase,
                   "pipeline": {j: round(frames[index]["angles"][j], 3) for j in joints}}
            usable = True
            for joint in joints:
                if _joint_is_offscreen_guess(landmarks, joint):
                    usable = False
                    break
                for side, (a, b, c) in TRIPLES[joint].items():
                    row[f"{joint}_{side}"] = round(
                        calculate_angle_3d(points[a], points[b], points[c]), 3)
            if not usable:
                continue
            rows.append(row)

    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({"rows": rows}, handle, ensure_ascii=False, indent=1)
    print(f"written: {out_path}")
    print(f"{len(rows)} clips with both joints on-screen")


if __name__ == "__main__":
    main()
