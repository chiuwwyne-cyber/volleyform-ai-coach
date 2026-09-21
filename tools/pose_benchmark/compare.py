"""Turn the per-backend result files into the numbers the write-up quotes.

Three things are reported, in increasing order of how much they matter to
VolleyForm:

1. Speed and hit rate - the easy numbers, and the least interesting ones.
2. Whether the backends are even looking at the same athlete. On a court with
   twelve people this is not a given, and every angle comparison is meaningless
   on the frames where they are not.
3. How far apart the angles are on the frames where they ARE looking at the
   same athlete, measured against the tolerance each joint's band was
   calibrated with.

What this CANNOT report is accuracy. There is no ground truth here: no
motion-capture, no hand-labelled keypoints. Two models disagreeing tells you
that they disagree, not which one is right. Every number below is a
DISAGREEMENT, and calling it an error would be a claim the data cannot support.
"""

import argparse
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contract import ANGLES, COMMON_KEYPOINTS, SCORE_FLOOR, frame_angles

# Two backends count as having found the same athlete when their torso centres
# land within this fraction of the frame of each other. A torso spans roughly
# 0.1-0.2 in these clips, so 0.08 stays inside one body.
SAME_SUBJECT_DIST = 0.08

TORSO = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")


def torso_centre(person):
    pts = [person[n] for n in TORSO
           if person.get(n) and person[n][2] >= SCORE_FLOOR]
    if len(pts) < 2:
        return None
    return (sum(p[0] for p in pts) / len(pts),
            sum(p[1] for p in pts) / len(pts))


def load(results_dir):
    out = {}
    for name in sorted(os.listdir(results_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(results_dir, name), encoding="utf-8") as fh:
            data = json.load(fh)
        out[data["backend"]] = data
    return out


def tolerances(standards_path):
    """The per-joint tolerance VolleyForm calibrated, used purely as a scale."""
    with open(standards_path, encoding="utf-8") as fh:
        std = json.load(fh)
    by_joint = {}
    for action in std["actions"].values():
        for phase in action["phases"].values():
            for joint, band in phase.items():
                if isinstance(band, dict) and "tolerance" in band:
                    by_joint.setdefault(joint, []).append(band["tolerance"])
    return {j: statistics.median(v) for j, v in by_joint.items()}


def per_backend_summary(data):
    all_ms, vis_rates = [], []
    found = total = ang_ok = ang_total = multi = 0

    for clip in data["clips"].values():
        for f in clip["frames"]:
            total += 1
            all_ms.append(f["ms"])
            if f["n_persons"] > 1:
                multi += 1
            if not f["kp"]:
                continue
            found += 1
            vis_rates.append(
                sum(1 for k in COMMON_KEYPOINTS if f["kp"][k][2] >= SCORE_FLOOR)
                / len(COMMON_KEYPOINTS)
            )
            angles = frame_angles(f["kp"])
            ang_total += len(angles)
            ang_ok += sum(1 for v in angles.values() if v is not None)

    median_ms = statistics.median(all_ms)
    return {
        "backend": data["backend"],
        "model": data["model"],
        "frames": total,
        "pose_found": found,
        "pose_found_pct": 100 * found / total,
        "median_ms": median_ms,
        "fps": 1000 / median_ms,
        "mean_ms": statistics.mean(all_ms),
        "keypoint_visible_pct": 100 * statistics.mean(vis_rates) if vis_rates else 0.0,
        "angle_ok_pct": 100 * ang_ok / ang_total if ang_total else 0.0,
        "multi_person_frames_pct": 100 * multi / total,
    }


def pairwise(data_a, data_b, tol):
    """Subject agreement, then angle disagreement where the subject matches."""
    subject_same = subject_cmp = 0
    diffs = {name: [] for name in ANGLES}

    for clip_id, clip_a in data_a["clips"].items():
        clip_b = data_b["clips"][clip_id]
        for fa, fb in zip(clip_a["frames"], clip_b["frames"]):
            if not fa["kp"] or not fb["kp"]:
                continue
            ca, cb = torso_centre(fa["kp"]), torso_centre(fb["kp"])
            if ca is None or cb is None:
                continue
            subject_cmp += 1
            if math.dist(ca, cb) > SAME_SUBJECT_DIST:
                continue
            subject_same += 1

            aa, ab = frame_angles(fa["kp"]), frame_angles(fb["kp"])
            for name in ANGLES:
                if aa[name] is not None and ab[name] is not None:
                    diffs[name].append(abs(aa[name] - ab[name]))

    joint_rows = []
    for name, vals in diffs.items():
        if not vals:
            joint_rows.append({"joint": name, "n": 0})
            continue
        t = tol.get(name.split("_", 1)[1])
        ordered = sorted(vals)
        joint_rows.append({
            "joint": name,
            "n": len(vals),
            "median": statistics.median(vals),
            "p90": ordered[int(0.9 * (len(ordered) - 1))],
            "tolerance": t,
            "over_tolerance_pct": (
                100 * sum(1 for v in vals if v > t) / len(vals)
                if t is not None else None
            ),
        })

    return {
        "subject_compared": subject_cmp,
        "subject_same": subject_same,
        "subject_same_pct": 100 * subject_same / subject_cmp if subject_cmp else 0.0,
        "joints": joint_rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--standards", default="backend/reference_standards.json")
    ap.add_argument("--baseline", default="mediapipe")
    ap.add_argument("--json-out")
    args = ap.parse_args()

    data = load(args.results)
    tol = tolerances(args.standards)
    print("backends: " + ", ".join(data) + "\n")

    print("== 1. speed and hit rate " + "=" * 52)
    print("backend    median ms    FPS   pose found   kp>=floor   angle ok   >1 person")
    summaries = []
    for name in data:
        s = per_backend_summary(data[name])
        summaries.append(s)
        print("{:10s} {:9.1f} {:6.1f} {:11.1f}% {:10.1f}% {:9.1f}% {:10.1f}%".format(
            s["backend"], s["median_ms"], s["fps"], s["pose_found_pct"],
            s["keypoint_visible_pct"], s["angle_ok_pct"],
            s["multi_person_frames_pct"]))

    print("\n== 2. do they track the same athlete as " + args.baseline + "? " + "=" * 22)
    base = data[args.baseline]
    pairs = {}
    for name in data:
        if name == args.baseline:
            continue
        p = pairwise(base, data[name], tol)
        pairs[name] = p
        print("{:10s} same athlete on {}/{} frames ({:.1f}%)".format(
            name, p["subject_same"], p["subject_compared"], p["subject_same_pct"]))

    print("\n== 3. angle disagreement vs " + args.baseline
          + ", same-athlete frames only " + "=" * 5)
    print("   degrees; tol = median calibrated tolerance for that joint")
    for name, p in pairs.items():
        print("\n  -- " + name + " --")
        print("  joint                n   median      p90     tol   over tol")
        for r in p["joints"]:
            if not r["n"]:
                print("  {:16s} {:5d}        -        -       -          -".format(
                    r["joint"], 0))
                continue
            t = "{:.1f}".format(r["tolerance"]) if r["tolerance"] is not None else "-"
            o = ("{:.1f}%".format(r["over_tolerance_pct"])
                 if r["over_tolerance_pct"] is not None else "-")
            print("  {:16s} {:5d} {:8.1f} {:8.1f} {:>7s} {:>10s}".format(
                r["joint"], r["n"], r["median"], r["p90"], t, o))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"summaries": summaries, "pairs": pairs, "tolerances": tol},
                      fh, indent=2)
        print("\nwrote " + args.json_out)


if __name__ == "__main__":
    main()
