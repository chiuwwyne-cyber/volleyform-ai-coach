"""Measure the arm shape of each action from the real dataset clips.

Feeds the numbers that frontend/pose-3d.js is tuned to. Run it, then compare
against the demo with frontend/pose_geometry_test.mjs and the phase tables in
pose-3d.js. Sampling point: the CONTACT frame that segment_action() picks --
the same instant the analyzer scores -- so demo and analysis talk about the
same moment.

Current medians (2026-08-16, elbow / elevation):
    serve   136 / 34      receive 147 / -45
    block   144 / 56      set     133 / 24
The spike aiming arm is measured separately by measure_aim_arm.py, because it
is sampled during the WIND-UP, not at contact.
"""
import math
import os
import statistics as st
import sys

ROOT = r"C:\Users\test\Desktop\volleyball"
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from pose.pose import get_pose_from_video          # noqa: E402
from backend.phase_segmentation import segment_action  # noqa: E402

L_SH, R_SH, L_EL, R_EL, L_WR, R_WR = 11, 12, 13, 14, 15, 16
L_HIP, R_HIP, NOSE = 23, 24, 0
L_KN, R_KN = 25, 26


def angle(a, b, c):
    v1 = (a.x - b.x, a.y - b.y, a.z - b.z)
    v2 = (c.x - b.x, c.y - b.y, c.z - b.z)
    d = math.dist((0, 0, 0), v1) * math.dist((0, 0, 0), v2)
    if d == 0:
        return 180.0
    return math.degrees(math.acos(max(-1.0, min(1.0, sum(v1[i] * v2[i] for i in range(3)) / d))))


def analyse(path, action):
    frames = []
    for data in get_pose_from_video(path, process_width=640, frame_stride=2, include_image=False):
        if data[0] is None:
            continue
        frames.append(data[0])
    if len(frames) < 8:
        return None
    seg = segment_action(action, frames)
    if not seg or seg.get("contact") is None:
        return None
    f = frames[min(seg["contact"], len(frames) - 1)]
    torso = abs(((f[L_HIP].y + f[R_HIP].y) / 2) - ((f[L_SH].y + f[R_SH].y) / 2))
    if torso < 1e-4:
        return None

    def arm(sh, el, wr):
        lift = (f[NOSE].y - f[wr].y) / torso
        elbow = angle(f[sh], f[el], f[wr])
        dx = math.hypot(f[wr].x - f[sh].x, f[wr].z - f[sh].z)
        dy = f[sh].y - f[wr].y
        elev = math.degrees(math.atan2(dy, dx)) if dx > 1e-6 else 90.0
        return lift, elbow, elev

    ll, le, lv = arm(L_SH, L_EL, L_WR)
    rl, re, rv = arm(R_SH, R_EL, R_WR)
    gap = math.dist((f[L_WR].x, f[L_WR].y), (f[R_WR].x, f[R_WR].y)) / torso
    knee = (angle(f[L_HIP], f[L_KN], f[27]) + angle(f[R_HIP], f[R_KN], f[28])) / 2
    # high arm = whichever wrist is higher (smaller y)
    high = (ll, le, lv) if f[L_WR].y < f[R_WR].y else (rl, re, rv)
    low = (rl, re, rv) if f[L_WR].y < f[R_WR].y else (ll, le, lv)
    return {"high_lift": high[0], "high_elbow": high[1], "high_elev": high[2],
            "low_lift": low[0], "low_elbow": low[1], "low_elev": low[2],
            "gap": gap, "knee": knee}


def main():
    for action in ("serve", "receive", "block", "set"):
        folder = os.path.join("dataset", action)
        rows = []
        for name in sorted(f for f in os.listdir(folder) if f.endswith(".mp4")):
            try:
                r = analyse(os.path.join(folder, name), action)
            except Exception:
                continue
            if r:
                rows.append(r)
        if not rows:
            print(f"{action}: no usable clips")
            continue
        med = lambda k: st.median([r[k] for r in rows])  # noqa: E731
        print(f"\n=== {action}  (n={len(rows)}, at the contact frame) ===")
        print(f"  higher arm : lift {med('high_lift'):+5.2f}  elbow {med('high_elbow'):5.0f}  "
              f"elev {med('high_elev'):5.0f}")
        print(f"  lower arm  : lift {med('low_lift'):+5.2f}  elbow {med('low_elbow'):5.0f}  "
              f"elev {med('low_elev'):5.0f}")
        print(f"  wrist gap  : {med('gap'):.2f} torso-lengths     knee {med('knee'):.0f} deg")


if __name__ == "__main__":
    main()
