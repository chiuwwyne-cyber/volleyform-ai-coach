"""Calibrate per-phase joint-angle bands from reference clips.

Usage:
    .venv\\Scripts\\python.exe tools\\build_reference.py

Scans dataset/<action>/*.mp4, extracts pose, segments each clip into key
moments (crouch / contact), and writes percentile bands per action, phase and
joint to backend/reference_standards.json. Only the derived statistics are
committed; the clips themselves stay out of the repository.
"""

import json
import math
import os
import sys
from datetime import date

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from angle.angle import get_angles
from backend.phase_segmentation import segment_action
from pose.pose import get_pose_from_video
from tools.sync_frontend import sync_frontend

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
REFERENCE_TARGET_CLIPS = 20

JOINT_TOLERANCE = {
    # Extra player_grace keeps correct amateur movements from being judged only
    # against elite range-of-motion. The sample term below shrinks as more clips
    # are added, so the accepted band becomes tighter when the data converges.
    "elbow": {"min": 8.0, "max": 22.0, "player_grace": 4.0},
    "shoulder": {"min": 8.0, "max": 22.0, "player_grace": 5.0},
    "knee": {"min": 10.0, "max": 24.0, "player_grace": 6.0},
}


def _percentile(sorted_values, fraction):
    if not sorted_values:
        return None
    index = fraction * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _clamp(value, lower, upper):
    return max(lower, min(upper, value))


def _iqr_bounds(ordered):
    if len(ordered) < 8:
        return None
    p25 = _percentile(ordered, 0.25)
    p75 = _percentile(ordered, 0.75)
    iqr = p75 - p25
    if iqr <= 0:
        return None
    return p25 - 1.5 * iqr, p75 + 1.5 * iqr


def _trim_outliers(values):
    ordered = sorted(values)
    bounds = _iqr_bounds(ordered)
    if not bounds:
        return ordered, ordered, 0
    lower, upper = bounds
    trimmed = [value for value in ordered if lower <= value <= upper]
    outliers = len(ordered) - len(trimmed)
    # Exclude IQR outliers (>1.5*IQR) from the percentile band so a few bad or
    # mis-detected clips (rally/broadcast footage, pose glitches) cannot stretch
    # the accepted range and make the app miss real mistakes. Guard: never trim
    # below ~60% of the samples, so a small class keeps its genuine spread.
    if len(trimmed) < max(5, math.ceil(len(ordered) * 0.6)):
        return ordered, ordered, outliers
    return ordered, trimmed, outliers


def _adaptive_tolerance(ordered, joint):
    count = len(ordered)
    p25 = _percentile(ordered, 0.25)
    p75 = _percentile(ordered, 0.75)
    iqr = max(0.0, p75 - p25)
    limits = JOINT_TOLERANCE.get(joint, {"min": 8.0, "max": 18.0})
    spread_allowance = min(6.0, iqr * 0.18)
    sample_allowance = min(5.0, 9.0 / math.sqrt(max(count, 1)))
    convergence_taper = 1.0 - min(0.45, count / 60.0)
    player_allowance = limits.get("player_grace", 4.0) * convergence_taper
    tolerance = limits["min"] + spread_allowance + sample_allowance + player_allowance
    return round(_clamp(tolerance, limits["min"], limits["max"]), 1)


def _convergence_score(ordered, raw_count, outliers):
    if not ordered:
        return 0.0
    p25 = _percentile(ordered, 0.25)
    p75 = _percentile(ordered, 0.75)
    iqr = max(0.0, p75 - p25)
    count_score = min(1.0, raw_count / REFERENCE_TARGET_CLIPS)
    spread_score = 1.0 / (1.0 + iqr / 45.0)
    outlier_score = 1.0 - min(0.5, outliers / max(raw_count, 1))
    return round(count_score * 0.45 + spread_score * 0.45 + outlier_score * 0.10, 2)


def _convergence_state(score, raw_count):
    if raw_count >= 14 and score >= 0.65:
        return "stable"
    if raw_count >= 5 and score >= 0.45:
        return "usable"
    return "needs_more_data"


def _accepted_range(p10, p90, tolerance):
    return [
        round(_clamp(p10 - tolerance, 0.0, 180.0), 1),
        round(_clamp(p90 + tolerance, 0.0, 180.0), 1),
    ]


def _band(values, joint):
    ordered, trimmed, outliers = _trim_outliers(values)
    raw_count = len(values)
    p10 = round(_percentile(trimmed, 0.10), 1)
    p90 = round(_percentile(trimmed, 0.90), 1)
    tolerance = _adaptive_tolerance(trimmed, joint)
    convergence = _convergence_score(trimmed, raw_count, outliers)
    return {
        "count": len(trimmed),
        "raw_count": raw_count,
        "outliers": outliers,
        "min": round(ordered[0], 1),
        "p10": p10,
        "p25": round(_percentile(trimmed, 0.25), 1),
        "p50": round(_percentile(trimmed, 0.50), 1),
        "p75": round(_percentile(trimmed, 0.75), 1),
        "p90": p90,
        "max": round(ordered[-1], 1),
        "tolerance": tolerance,
        "accepted_range": _accepted_range(p10, p90, tolerance),
        "convergence": convergence,
        "convergence_state": _convergence_state(convergence, raw_count),
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
                joint: _band(values, joint)
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
    sync_result = sync_frontend(ROOT_DIR)
    print(f"synced frontend: {sync_result['buildVersion']}")


if __name__ == "__main__":
    main()
