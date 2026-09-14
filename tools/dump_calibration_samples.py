"""Dump every calibration sample the standard is built from, one row per decision.

Why this exists: `reference_standards.json` publishes percentiles, not the values
behind them, so there is no way to ask "would this clip be flagged by the standard
it helped build?" without re-running the whole 35-minute pose scan. That question
is the only in-house source of a false-positive number, because every clip in
dataset/ is assumed-correct footage -- a flag on one of them is a false positive
by construction.

Everything here imports from build_reference rather than reimplementing it. An
analysis that used a slightly different visibility gate or a different segmenter
would produce confident numbers about a pipeline that does not exist, which is
worse than having no numbers. `audit_sample_visibility.py --dump` is NOT usable
for this: it predates the 2026-08-18 x-axis fix and stores only y and visibility,
so it cannot reproduce the gate the pipeline actually applies.

Usage:
    .venv/Scripts/python.exe tools/dump_calibration_samples.py [out.json]
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.phase_segmentation import segment_action
from tools.build_reference import (
    ACTION_PHASE_JOINTS,
    ACTIONS,
    DATASET_DIR,
    _joint_is_offscreen_guess,
    _load_phase_scope,
    _process_clip,
)

DEFAULT_OUT = os.path.join(ROOT_DIR, "dataset", "calibration_samples.json")


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    phase_scope = _load_phase_scope()
    rows = []
    skipped_clips = []

    for action in ACTIONS:
        action_dir = os.path.join(DATASET_DIR, action)
        if not os.path.isdir(action_dir):
            continue
        clips = sorted(n for n in os.listdir(action_dir) if n.lower().endswith(".mp4"))
        phase_joints = ACTION_PHASE_JOINTS.get(action, {})

        for clip_name in clips:
            print(f"[{action}] {clip_name} ...", flush=True)
            frames = _process_clip(os.path.join(action_dir, clip_name))
            segments = segment_action(action, [f["landmarks"] for f in frames])
            if not segments:
                # Same outcome as the build: the clip contributes nothing at all.
                skipped_clips.append({"action": action, "clip": clip_name,
                                      "reason": "no usable segmentation",
                                      "frames": len(frames)})
                continue

            allowed = phase_scope.get(f"{action}/{clip_name}")
            for phase, index in (("contact", segments.get("contact")),
                                 ("crouch", segments.get("crouch"))):
                if index is None or phase not in phase_joints:
                    continue
                landmarks = frames[index]["landmarks"]
                scoped_out = allowed is not None and phase not in allowed
                for joint in phase_joints[phase]:
                    # Record dropped and scoped-out rows too. A band that rests on
                    # far fewer samples than the clip count suggests is exactly how
                    # the 23.6-degree knee survived, so the analysis needs to see
                    # what was excluded, not just what survived.
                    rows.append({
                        "action": action,
                        "clip": clip_name,
                        "phase": phase,
                        "joint": joint,
                        "angle": round(float(frames[index]["angles"][joint]), 3),
                        "kept": not scoped_out and not _joint_is_offscreen_guess(landmarks, joint),
                        "scoped_out": scoped_out,
                        "offscreen": _joint_is_offscreen_guess(landmarks, joint),
                    })

    payload = {"rows": rows, "skipped_clips": skipped_clips}
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)

    kept = sum(1 for r in rows if r["kept"])
    print(f"written: {out_path}")
    print(f"{len(rows)} rows, {kept} kept, {len(rows) - kept} excluded, "
          f"{len(skipped_clips)} clip(s) with no segmentation")


if __name__ == "__main__":
    main()
