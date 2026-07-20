"""Report motion signals for candidate clips so they can be assigned an action.

Usage:
    .venv\\Scripts\\python.exe tools\\inspect_clips.py dataset\\_candidates

Prints, per clip: how often both wrists are overhead (block / set), how often
one wrist swings alone overhead (spike / serve), how often the hands form a
low joined platform (receive), and how much the hips travel (jump / crouch).
"""

import math
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from pose.pose import get_pose_from_video

MAX_FRAMES = 240


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def inspect(video_path):
    frames = 0
    both_overhead = 0
    one_overhead = 0
    platform = 0
    overhead_close = 0
    hip_min = 1.0
    hip_max = 0.0

    for pose_data in get_pose_from_video(
        video_path, process_width=640, frame_stride=2, include_image=False
    ):
        if frames >= MAX_FRAMES:
            break
        landmarks = pose_data[0]
        frames += 1

        nose_y = landmarks[0].y
        wrist_l, wrist_r = landmarks[15], landmarks[16]
        shoulder_y = (landmarks[11].y + landmarks[12].y) / 2
        hip_y = (landmarks[23].y + landmarks[24].y) / 2
        hip_min = min(hip_min, hip_y)
        hip_max = max(hip_max, hip_y)

        gap = _dist(wrist_l, wrist_r)
        high = max(wrist_l.y, wrist_r.y) < nose_y  # both above nose
        any_high = min(wrist_l.y, wrist_r.y) < nose_y

        if high:
            both_overhead += 1
            if gap < 0.18:
                overhead_close += 1
        elif any_high:
            one_overhead += 1
        if gap < 0.10 and min(wrist_l.y, wrist_r.y) > shoulder_y:
            platform += 1

    if frames == 0:
        return f"{os.path.basename(video_path):28s} NO POSE DETECTED"
    pct = lambda n: round(100 * n / frames)
    return (
        f"{os.path.basename(video_path):28s} frames={frames:3d} "
        f"bothUp={pct(both_overhead):3d}% oneUp={pct(one_overhead):3d}% "
        f"setLike={pct(overhead_close):3d}% platform={pct(platform):3d}% "
        f"hipTravel={round(hip_max - hip_min, 2)}"
    )


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT_DIR, "dataset", "_candidates")
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".mp4"):
            continue
        print(inspect(os.path.join(folder, name)), flush=True)


if __name__ == "__main__":
    main()
