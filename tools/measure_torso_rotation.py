"""Measure how far a player's trunk turns, without trusting MediaPipe's z.

WHY THIS EXISTS
---------------
MediaPipe estimates x and y from what it can see, but z (depth) is inferred
from a single RGB view. Turning about the vertical axis is exactly the motion a
single camera sees least of, so z is weakest precisely where trunk rotation
lives. Measured on this repo's 94 dataset clips with the naive method, the
hip-shoulder separation ("X-factor") came out at 6-10 degrees, where the
biomechanics literature reports 30-60 for overhead actions -- and spike even
showed the trunk *more* turned at contact than at cocking, which is backwards.
That is the measurement flattening the movement, not the players.

THE METHOD
----------
A shoulder line of fixed real width W projects to W*|cos(yaw)| on the image
plane. So the amount of turn can be read off the FORESHORTENING, using only x
and y:

    |yaw| = arccos( observed_width_xy / W )

W is recovered per clip as the 90th-percentile observed width -- the frames
where the player is squarest to the camera. z is then used for one thing only:
the SIGN of the turn. A noisy depth estimate still gets the direction right far
more often than it gets the magnitude right, so this puts z where it can do the
least damage.

Measured against the naive method on the same clips, this roughly doubles the
recovered separation (spike 9.5 -> 17.3, serve 5.9 -> 11.4 degrees).

HONEST LIMITS
-------------
- 17 degrees is still short of mocap-grade numbers. Monocular video has a hard
  ceiling; this narrows the gap, it does not close it.
- Hip width is small, so hip foreshortening is noisier than shoulder.
- |cos| is symmetric, so magnitude alone cannot tell a left turn from a right
  one -- that is why the sign still comes from z.
- If a player is never square to the camera in a clip, W is underestimated and
  every angle with it.

Do NOT retune coaching thresholds to these numbers on the assumption they are
ground truth. They are better, not exact.

Usage:
    .venv\\Scripts\\python.exe tools\\measure_torso_rotation.py spike
    .venv\\Scripts\\python.exe tools\\measure_torso_rotation.py            (all)
"""

import math
import os
import statistics as st
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from pose.pose import get_pose_from_video  # noqa: E402
from backend.phase_segmentation import segment_action  # noqa: E402

L_SHOULDER, R_SHOULDER, L_HIP, R_HIP = 11, 12, 23, 24
ACTIONS = ("spike", "serve", "receive", "block", "set")


def _wrap(deg):
    """Fold an angle into [-90, 90]: a trunk line has no front/back identity."""
    while deg > 90:
        deg -= 180
    while deg < -90:
        deg += 180
    return deg


def _percentile(values, fraction=0.9):
    ordered = sorted(values)
    return ordered[max(0, int(len(ordered) * fraction) - 1)]


def measure_clip(video_path, action):
    image_frames, world_frames = [], []
    for data in get_pose_from_video(video_path, process_width=640, frame_stride=2, include_image=False):
        if data[0] is None or data[1] is None:
            continue
        image_frames.append(data[0])
        world_frames.append(data[1])
    if len(image_frames) < 8:
        return None

    segments = segment_action(action, image_frames)
    if not segments or segments.get("contact") is None:
        return None
    contact = segments["contact"]
    cocking = segments.get("crouch")
    cocking = max(0, contact - 3) if cocking is None else cocking
    if max(contact, cocking) >= len(world_frames):
        return None

    def widths(a, b):
        return [math.hypot(w[b].x - w[a].x, w[b].y - w[a].y) for w in world_frames]

    shoulder_widths = widths(L_SHOULDER, R_SHOULDER)
    hip_widths = widths(L_HIP, R_HIP)
    true_shoulder = _percentile(shoulder_widths)
    true_hip = _percentile(hip_widths)
    if true_shoulder <= 1e-6 or true_hip <= 1e-6:
        return None

    def at(index):
        w = world_frames[index]
        shoulder_dz = w[R_SHOULDER].z - w[L_SHOULDER].z
        hip_dz = w[R_HIP].z - w[L_HIP].z
        shoulder = math.degrees(math.acos(max(0.0, min(1.0, shoulder_widths[index] / true_shoulder))))
        hip = math.degrees(math.acos(max(0.0, min(1.0, hip_widths[index] / true_hip))))
        shoulder = math.copysign(shoulder, shoulder_dz or 1.0)
        hip = math.copysign(hip, hip_dz or 1.0)
        return shoulder, hip, _wrap(shoulder - hip)

    shoulder_c, hip_c, sep_c = at(cocking)
    shoulder_t, hip_t, sep_t = at(contact)
    return {
        "shoulder_cocking": abs(shoulder_c),
        "shoulder_contact": abs(shoulder_t),
        "separation_cocking": abs(sep_c),
        "separation_contact": abs(sep_t),
        "unwind": abs(shoulder_c) - abs(shoulder_t),
    }


def measure_action(action):
    folder = os.path.join(ROOT_DIR, "dataset", action)
    if not os.path.isdir(folder):
        return None
    rows = []
    for name in sorted(f for f in os.listdir(folder) if f.endswith(".mp4")):
        try:
            row = measure_clip(os.path.join(folder, name), action)
        except Exception as exc:  # one bad clip must not kill the run
            print(f"  ! {action}/{name}: {exc}", flush=True)
            continue
        if row:
            rows.append(row)
    if not rows:
        return None
    summary = {key: round(st.median([r[key] for r in rows]), 1) for key in rows[0]}
    summary["clips"] = len(rows)
    return summary


def main():
    wanted = sys.argv[1:] or list(ACTIONS)
    print(f"{'action':8} {'n':>3}  {'|sh|@cock':>9} {'|sh|@contact':>12} "
          f"{'sep@cock':>9} {'sep@contact':>11} {'unwind':>7}")
    for action in wanted:
        if action not in ACTIONS:
            print(f"  ? unknown action: {action}")
            continue
        summary = measure_action(action)
        if not summary:
            print(f"{action:8} no usable clips")
            continue
        print(f"{action:8} {summary['clips']:>3}  {summary['shoulder_cocking']:>9} "
              f"{summary['shoulder_contact']:>12} {summary['separation_cocking']:>9} "
              f"{summary['separation_contact']:>11} {summary['unwind']:>7}")


if __name__ == "__main__":
    main()
