"""What do real spikers actually do with the NON-hitting arm?

The demo currently points it straight at the ball, which makes a near-vertical
arm. Rather than guess a better number, measure the 17 real spike clips.

For each clip: find the contact frame, decide which arm hit (the higher wrist),
then look at the wind-up frames before contact and measure the OTHER arm:

  lift   = (head_y - wrist_y) / torso   how far above the head the wrist sits,
                                        in torso-lengths. 0 = level with the
                                        head, negative = below it.
  elbow  = elbow angle in degrees       180 = perfectly straight
  elev   = angle of shoulder->wrist off horizontal, degrees. 90 = straight up.

All three are scale-free, so clips filmed at different distances still compare.
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


def angle(a, b, c):
    v1 = (a.x - b.x, a.y - b.y, a.z - b.z)
    v2 = (c.x - b.x, c.y - b.y, c.z - b.z)
    d = math.dist((0, 0, 0), v1) * math.dist((0, 0, 0), v2)
    if d == 0:
        return 180.0
    cos = sum(v1[i] * v2[i] for i in range(3)) / d
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def analyse(path):
    frames = []
    for data in get_pose_from_video(path, process_width=640, frame_stride=2, include_image=False):
        if data[0] is None:
            continue
        frames.append(data[0])
    if len(frames) < 8:
        return None
    seg = segment_action("spike", frames)
    if not seg or seg.get("contact") is None:
        return None
    contact = min(seg["contact"], len(frames) - 1)

    c = frames[contact]
    # image y grows downward: the higher wrist has the SMALLER y
    hitting_right = c[R_WR].y < c[L_WR].y
    sh, el, wr = (L_SH, L_EL, L_WR) if hitting_right else (R_SH, R_EL, R_WR)

    rows = []
    for i in range(max(0, contact - 8), contact + 1):
        f = frames[i]
        torso = abs(((f[L_HIP].y + f[R_HIP].y) / 2) - ((f[L_SH].y + f[R_SH].y) / 2))
        if torso < 1e-4:
            continue
        lift = (f[NOSE].y - f[wr].y) / torso
        elbow = angle(f[sh], f[el], f[wr])
        dx = f[wr].x - f[sh].x
        dy = f[sh].y - f[wr].y          # positive = wrist above shoulder
        elev = math.degrees(math.atan2(dy, abs(dx))) if abs(dx) > 1e-6 else 90.0
        rows.append((lift, elbow, elev))
    if not rows:
        return None
    # the wind-up peak: the frame where that arm is highest
    peak = max(rows, key=lambda r: r[0])
    return {"lift": peak[0], "elbow": peak[1], "elev": peak[2],
            "hand": "R" if hitting_right else "L"}


def main():
    folder = os.path.join("dataset", "spike")
    rows = []
    for name in sorted(f for f in os.listdir(folder) if f.endswith(".mp4")):
        try:
            r = analyse(os.path.join(folder, name))
        except Exception as exc:
            print(f"  ! {name}: {exc}", flush=True)
            continue
        if r:
            rows.append(r)
            print(f"  {name:28} lift={r['lift']:+5.2f} elbow={r['elbow']:5.1f} "
                  f"elev={r['elev']:5.1f} hits with {r['hand']}", flush=True)
    if not rows:
        print("no usable clips")
        return
    print(f"\nn={len(rows)}  (non-hitting arm at its highest point in the wind-up)")
    for key, label in (("lift", "wrist above head, in torso-lengths"),
                       ("elbow", "elbow angle (180 = straight)"),
                       ("elev", "elevation off horizontal (90 = straight up)")):
        vals = [r[key] for r in rows]
        print(f"  {label:42} median {st.median(vals):6.1f}   "
              f"range {min(vals):.1f} .. {max(vals):.1f}")
    print(f"\n  right-handed clips: {sum(1 for r in rows if r['hand'] == 'R')}/{len(rows)}")


if __name__ == "__main__":
    main()
