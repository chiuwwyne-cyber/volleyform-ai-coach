"""Calibrate per-phase joint-angle bands from reference clips.

Usage:
    .venv\\Scripts\\python.exe tools\\build_reference.py

Scans dataset/<action>/*.mp4, extracts pose, segments each clip into key
moments (crouch / contact), and writes percentile bands per action, phase and
joint to backend/reference_standards.json. Only the derived statistics are
committed; the clips themselves stay out of the repository.
"""

import json
import os
import sys
from datetime import date

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from angle.angle import get_angles
from backend.phase_segmentation import segment_action
from pose.pose import get_pose_from_video

DATASET_DIR = os.path.join(ROOT_DIR, "dataset")
OUTPUT_PATH = os.path.join(ROOT_DIR, "backend", "reference_standards.json")

ACTIONS = ("spike", "serve", "block", "receive", "set")
ACTION_PHASE_JOINTS = {
    "spike": {
        "contact": ("elbow", "shoulder"),
        "crouch": ("knee",),
    },
    "serve": {
        "contact": ("elbow", "shoulder"),
        "crouch": ("knee",),
    },
    "block": {
        "contact": ("elbow", "shoulder"),
        "crouch": ("knee",),
    },
    "receive": {
        "contact": ("elbow", "knee", "shoulder"),
    },
    "set": {
        "contact": ("elbow", "shoulder"),
    },
}
MAX_FRAMES = 300


def _percentile(sorted_values, fraction):
    if not sorted_values:
        return None
    index = fraction * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _band(values):
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": round(ordered[0], 1),
        "p10": round(_percentile(ordered, 0.10), 1),
        "p25": round(_percentile(ordered, 0.25), 1),
        "p50": round(_percentile(ordered, 0.50), 1),
        "p75": round(_percentile(ordered, 0.75), 1),
        "p90": round(_percentile(ordered, 0.90), 1),
        "max": round(ordered[-1], 1),
    }


def _process_clip(video_path):
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
        frames.append(
            {
                "landmarks": landmarks,
                "angles": get_angles(landmarks, world_landmarks),
            }
        )
    return frames


def main():
    result = {
        "version": 1,
        "generated": date.today().isoformat(),
        "source": "dataset/MANIFEST.md",
        "actions": {},
    }

    for action in ACTIONS:
        action_dir = os.path.join(DATASET_DIR, action)
        if not os.path.isdir(action_dir):
            continue
        clips = sorted(
            name for name in os.listdir(action_dir) if name.lower().endswith(".mp4")
        )
        if not clips:
            continue

        phase_joints = ACTION_PHASE_JOINTS.get(action, {})
        samples = {
            phase: {joint: [] for joint in joints}
            for phase, joints in phase_joints.items()
        }
        used_clips = 0

        for clip_name in clips:
            clip_path = os.path.join(action_dir, clip_name)
            print(f"[{action}] {clip_name} ...", flush=True)
            frames = _process_clip(clip_path)
            segments = segment_action(action, [frame["landmarks"] for frame in frames])
            if not segments:
                print(f"  skipped: no usable segmentation ({len(frames)} frames)")
                continue

            contact = segments["contact"]
            crouch = segments["crouch"]
            if "contact" in samples:
                for joint in phase_joints["contact"]:
                    samples["contact"][joint].append(frames[contact]["angles"][joint])
            if crouch is not None and "crouch" in samples:
                for joint in phase_joints["crouch"]:
                    samples["crouch"][joint].append(frames[crouch]["angles"][joint])
            used_clips += 1

        if used_clips == 0:
            continue

        phases = {}
        for phase, joints in phase_joints.items():
            phase_stats = {
                joint: _band(values)
                for joint, values in samples[phase].items()
                if values
            }
            if phase_stats:
                phases[phase] = phase_stats

        result["actions"][action] = {"clips": used_clips, "phases": phases}
        print(f"[{action}] calibrated from {used_clips}/{len(clips)} clips")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    print(f"written: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
