"""Measure the hand checks against the dataset they have never been measured on.

Five thresholds decide four of the set errors and two of the receive errors:

    receive_platform_unbalanced   hands_level_gap  > 0.08
    receive_hands_apart           hand_center_gap  > 0.24
    setting_fingers_closed        finger_extension < 1.08
    setting_hand_spacing_bad      hand_center_gap  < 0.06 or > 0.32
    setting_hands_unbalanced      hands_level_gap  > 0.08

Unlike the fourteen angle bands, none of them came from data. They are constants
someone chose, and nothing has ever checked whether a correct player clears them.
A threshold sitting inside the reference distribution does not fail loudly -- it
just tells some proportion of correct setters that their hands are wrong.

This dumps what the reference clips actually measure at the judged frame, so the
question can be answered. It reads hand landmarks, which build_reference's own
_process_clip throws away, so it re-runs the pose stream rather than reusing it.

Usage:
    .venv/Scripts/python.exe tools/dump_hand_features.py [out.json]
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from angle.angle import get_angles, get_hand_features
from backend.phase_segmentation import segment_action
from pose.pose import get_pose_from_video
from tools.build_reference import DATASET_DIR, MAX_FRAMES

DEFAULT_OUT = os.path.join(ROOT_DIR, "dataset", "hand_features.json")

# Only the actions whose evaluation reads hand features at all.
ACTIONS = ("set", "receive")

FEATURES = ("hands_detected", "hand_span", "finger_extension",
            "hand_center_gap", "hands_level_gap")


def _process(video_path):
    frames = []
    for pose_data in get_pose_from_video(
        video_path, process_width=640, frame_stride=2, include_image=False
    ):
        if len(frames) >= MAX_FRAMES:
            break
        if len(pose_data) == 4:
            landmarks, world_landmarks, _frame, hands = pose_data
        else:
            landmarks, world_landmarks, _frame = pose_data
            hands = None
        frames.append({
            "landmarks": landmarks,
            "angles": get_angles(landmarks, world_landmarks),
            "hand_features": get_hand_features(hands),
        })
    return frames


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    rows = []
    for action in ACTIONS:
        action_dir = os.path.join(DATASET_DIR, action)
        if not os.path.isdir(action_dir):
            continue
        for clip_name in sorted(n for n in os.listdir(action_dir)
                                if n.lower().endswith(".mp4")):
            print(f"[{action}] {clip_name} ...", flush=True)
            frames = _process(os.path.join(action_dir, clip_name))
            segments = segment_action(action, [f["landmarks"] for f in frames])
            if not segments or segments.get("contact") is None:
                print("  no contact frame", flush=True)
                continue
            index = segments["contact"]
            row = {"action": action, "clip": clip_name, "frame": index}
            hands = frames[index]["hand_features"] or {}
            for name in FEATURES:
                row[name] = hands.get(name)
            rows.append(row)

    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({"rows": rows}, handle, ensure_ascii=False, indent=1)
    print(f"written: {out_path}")
    print(f"{len(rows)} rows")


if __name__ == "__main__":
    main()
