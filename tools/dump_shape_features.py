"""Dump candidate shape features for error checks the bands do not yet cover.

The angle bands judge elbow, shoulder and knee at one or two moments. Coaching
references list errors those three numbers cannot express -- a block with one
hand lower than the other, a receive platform wider than the hips, a stance too
narrow to move from. Adding a check for any of them needs the same evidence the
angle bands have: what correct players actually measure, so a threshold can be
set without flagging them.

Every feature here is measured IN THE IMAGE PLANE and divided by a body width
from the same frame. Both parts matter:

  * in-plane, because depth is the axis MediaPipe estimates worst and this
    project has a whole ADR about how badly that goes
  * normalised, because a player filmed from 10 metres has the same technique as
    one filmed from 3, and raw pixel gaps would say otherwise

Features are recorded for every action, not only the ones with a candidate
check, so the same scan can answer later questions without re-running.

Usage:
    .venv/Scripts/python.exe tools/dump_shape_features.py [out.json]
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from angle.angle import (
    SHAPE_LANDMARKS,
    get_angles,
    get_shape_features,
    landmarks_offscreen,
)
from backend.phase_segmentation import segment_action
from tools.build_reference import (
    ACTIONS,
    DATASET_DIR,
    JOINT_LANDMARKS,
    _joint_is_offscreen_guess,
    _load_phase_scope,
    _process_clip,
)

DEFAULT_OUT = os.path.join(ROOT_DIR, "dataset", "shape_features.json")

def _feature_offscreen(landmarks, feature):
    """Same gate the angle bands use, per feature.

    SHAPE_LANDMARKS is imported rather than copied: the table and the function
    that reads those points have to stay together, or a feature added to one and
    not the other is judged with nothing watching its landmarks.
    """
    return landmarks_offscreen(landmarks, SHAPE_LANDMARKS[feature])

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    out_path = args[0] if args else DEFAULT_OUT
    # Optional action filter, so a question about one action does not cost a
    # thirty-minute sweep of all five.
    wanted = set(args[1:]) or set(ACTIONS)
    phase_scope = _load_phase_scope()
    rows = []

    for action in ACTIONS:
        if action not in wanted:
            continue
        action_dir = os.path.join(DATASET_DIR, action)
        if not os.path.isdir(action_dir):
            continue
        for clip_name in sorted(n for n in os.listdir(action_dir) if n.lower().endswith(".mp4")):
            print(f"[{action}] {clip_name} ...", flush=True)
            frames = _process_clip(os.path.join(action_dir, clip_name))
            segments = segment_action(action, [f["landmarks"] for f in frames])
            if not segments:
                continue
            allowed = phase_scope.get(f"{action}/{clip_name}")
            for phase, index in (("contact", segments.get("contact")),
                                 ("crouch", segments.get("crouch"))):
                # Deliberately NOT filtered by ACTION_PHASE_JOINTS. The point of
                # this scan is to answer "what could be judged that is not",
                # and skipping the unsampled phases makes it unable to. set has
                # a crouch the segmenter finds and nothing reads; that question
                # cost a whole extra sweep to ask the first time.
                if index is None:
                    continue
                if allowed is not None and phase not in allowed:
                    continue
                landmarks = frames[index]["landmarks"]
                shape = get_shape_features(landmarks) or None
                if shape is None:
                    continue
                row = {"action": action, "clip": clip_name, "phase": phase}
                # All three angles at both phases, not only the ones the bands
                # currently judge. block has no crouch elbow band, and the only
                # labelled-wrong block footage separates on exactly that number
                # -- a question this scan could not answer when it recorded the
                # knee alone.
                for joint in ("elbow", "knee", "shoulder"):
                    row[joint] = round(float(frames[index]["angles"][joint]), 2)
                    row[joint + "_ok"] = not _joint_is_offscreen_guess(landmarks, joint)
                for name, value in shape.items():
                    row[name] = round(float(value), 4)
                    row[name + "_ok"] = not _feature_offscreen(landmarks, name)
                rows.append(row)

    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({"rows": rows}, handle, ensure_ascii=False, indent=1)
    print(f"written: {out_path}")
    print(f"{len(rows)} rows")


if __name__ == "__main__":
    main()
