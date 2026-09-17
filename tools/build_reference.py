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

from angle.angle import (
    JOINT_LANDMARKS,
    SHAPE_LANDMARKS,
    get_angles,
    get_shape_features,
    landmarks_offscreen,
)
from backend.phase_segmentation import segment_action
from pose.pose import get_pose_from_video
from backend.reference_evaluation import ACTION_RULES, _band_range
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
        # The elbow is sampled at the load too, which no other action does.
        # The only labelled-wrong block footage this project has separates on
        # exactly this number: three spans a tutorial marks with a red cross
        # measure 79.2, 51.6 and 134.7 where the three it marks correct measure
        # 140.0, 125.7 and 142.8. Hand spacing, which was the first guess, does
        # not separate them at all.
        "crouch": ("knee", "elbow"),
    },
    "receive": {
        "contact": ("elbow", "knee", "shoulder"),
    },
    "set": {
        "contact": ("elbow", "shoulder"),
        # The segmenter has always returned a crouch for set (_crouch_near, the
        # lowest hip within four frames of the release) and nothing read it. A
        # setter who never bends their legs pushes the ball with the arms alone,
        # which is the error this samples for. 12 of 24 clips contribute -- the
        # other half have ankles off-screen at that frame.
        "crouch": ("knee",),
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


PHASE_SCOPE_PATH = os.path.join(DATASET_DIR, "clip_phase_scope.json")


def _load_phase_scope():
    """Which phases each clip is allowed to contribute, keyed "<action>/<clip>".

    Added 2026-08-17. A clip can be good evidence for one phase and bad for
    another: live-play block footage carries the deep crouch this dataset lacks
    (measured 80.9 and 105.4 degrees where the whole band's minimum was 120.1),
    while its contact elbows measure 123-139 against a p10 of 141.4, because
    players in a rally do not fully extend. Taking those clips whole would fix
    the knee band and loosen the elbow floor -- the same trade that forced the
    2026-08-05 set revert.

    This is the per-JOINT visibility gate's idea moved up to the phase level.
    Clips not listed contribute every phase, so the file is additive and the
    default behaviour is unchanged.
    """
    if not os.path.exists(PHASE_SCOPE_PATH):
        return {}
    with open(PHASE_SCOPE_PATH, encoding="utf-8") as handle:
        raw = json.load(handle)
    scope = {}
    for key, entry in raw.get("clips", {}).items():
        phases = entry.get("phases")
        if not phases:
            raise ValueError(f"{PHASE_SCOPE_PATH}: {key} lists no phases")
        if not entry.get("reason"):
            # An unexplained scope is indistinguishable from trimming the data
            # until the numbers look right, so refuse to run without one.
            raise ValueError(f"{PHASE_SCOPE_PATH}: {key} has no reason")
        scope[key] = set(phases)
    return scope


def _joint_is_offscreen_guess(landmarks, joint):
    """這個關節的角度是不是算在「畫面外硬猜」的 landmark 上?

    規則本身住在 angle.angle.landmarks_offscreen,判定端也用同一份——校準時
    擋掉的幻覺,上線時不該又被當成真的。這裡只負責把關節翻成 landmark 編號。
    """
    return landmarks_offscreen(landmarks, JOINT_LANDMARKS[joint])


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


def _band(values, joint, has_high_rule=False):
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
        # The largest sample the band actually KEPT. `max` above comes from the
        # untrimmed list, so it can be an IQR outlier the calibration deliberately
        # excluded -- anchoring anything to it would let a sample judged wrong
        # widen the standard. set.contact.elbow shows the gap: max 177.8 against a
        # p90 of 154.0.
        "max_kept": round(trimmed[-1], 1),
        # And the smallest, for the same reason on the other side. Every low-side
        # rule needs it to prove its floor sits below the reference: `min` above is
        # pre-trim, so a floor checked against it can look safe while sitting above
        # a sample the band actually kept. Added 2026-09-17 with the first low-side
        # band whose whole purpose is to fire near the bottom of the data.
        "min_kept": round(trimmed[0], 1),
        "tolerance": tolerance,
        # Computed through the evaluator's own _band_range, not re-derived here.
        # This field used to be `p10/p90 +/- tolerance` while the evaluator capped
        # the high side, so the published artifact advertised 174.8 for block where
        # the app actually enforced 168.0 -- a false contract for anyone reading
        # the JSON, and it is exactly the "output-only field drifts from the code"
        # trap that already bit this project once.
        "accepted_range": [
            round(value, 1)
            for value in _band_range(
                {"p10": p10, "p90": p90, "max_kept": round(trimmed[-1], 1)},
                tolerance,
                has_high_rule=has_high_rule,
            )
        ],
        "convergence": convergence,
        "convergence_state": _convergence_state(convergence, raw_count),
    }


# Shape checks: errors the angle bands cannot express.
#
# elbow/shoulder/knee describe ONE joint each. Coaching references list block
# faults that live in the relationship BETWEEN the two hands -- one hand lower
# than the other leaves a gap a hitter aims at, hands too far apart let the ball
# through the middle. Measured on three segments a technique video itself labels
# wrong, all three passed every angle band; the errors are simply not in those
# three numbers.
#
# Values are ratios (normalised by shoulder or hip width), not degrees, so the
# degree-based JOINT_TOLERANCE does not apply. The threshold rule instead follows
# the one used for the joint model: it must clear every reference sample, because
# every dataset clip is assumed-correct and flagging one is a false positive by
# construction.
# Shape checks to publish, as (action, phase, feature) -> side and issue code.
#
# Deliberately EMPTY. Two block hand checks were built here and taken back out
# on 2026-09-17: measured against the only labelled-wrong footage this project
# has, all three wrong segments sat inside the range of the three correct ones.
# The footage turned out to demonstrate a dropped arm, which separates cleanly
# on the crouch elbow and not at all on hand spacing.
#
# That is not evidence hand spacing is fine -- it is the absence of any evidence
# that a check on it would fire for a real reason. A check nobody can demonstrate
# catching a genuine error is only a new way to flag correct technique.
#
# The machinery below and in backend/reference_evaluation.py stays, with tests:
# three receive candidates are still shape checks awaiting their distributions.
SHAPE_CHECKS = {
    # A set is played from directly above the forehead. Hands drifting sideways
    # is a standard fault that no angle band can express -- the elbow and shoulder
    # read the same whether the hands are above the head or beside it.
    #
    # 21 reference samples run 0.004 to 0.327 torso-lengths with nothing trimmed,
    # the tightest of the eight distributions measured (ceiling 2.2x the median;
    # trunk_lean came out at 6-18x, which is a threshold no body can reach).
    ("set", "contact", "hands_off_center"): {"side": "high",
                                             "code": "set_hands_off_forehead"},
}
# How far past the reference spread a threshold sits, in IQR units.
SHAPE_TOLERANCE_K = 1.5
# And never inside the observed samples, whatever the IQR says.
SHAPE_CLEARANCE = 1.15


def _shape_band(values, side):
    """Percentiles plus a threshold that no reference sample reaches.

    Two rules, and the binding one differs by feature:
      * p90 + k*IQR (or p10 - k*IQR) -- scaled to how much correct players vary
      * beyond the largest (smallest) kept sample by SHAPE_CLEARANCE -- so a
        clip the calibration accepted can never be flagged, which is the rule the
        joint model uses and the reason it shipped without a single new flag.
    """
    ordered, trimmed, outliers = _trim_outliers(values)
    p10 = round(_percentile(trimmed, 0.10), 4)
    p50 = round(_percentile(trimmed, 0.50), 4)
    p90 = round(_percentile(trimmed, 0.90), 4)
    iqr = max(0.0, _percentile(trimmed, 0.75) - _percentile(trimmed, 0.25))
    lo = hi = None
    if side in ("high", "both"):
        hi = round(max(p90 + SHAPE_TOLERANCE_K * iqr, trimmed[-1] * SHAPE_CLEARANCE), 3)
    if side in ("low", "both"):
        lo = round(min(p10 - SHAPE_TOLERANCE_K * iqr, trimmed[0] / SHAPE_CLEARANCE), 3)
        lo = max(0.0, lo)
    return {
        "count": len(trimmed), "raw_count": len(values), "outliers": outliers,
        "min": round(ordered[0], 4), "p10": p10, "p50": p50, "p90": p90,
        "max": round(ordered[-1], 4), "max_kept": round(trimmed[-1], 4),
        "min_kept": round(trimmed[0], 4), "iqr": round(iqr, 4),
        "accepted_range": [lo, hi], "side": side,
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

    phase_scope = _load_phase_scope()
    if phase_scope:
        print(f"phase scope: {len(phase_scope)} clip(s) limited to specific phases")

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
        shape_samples = {}
        samples = {
            phase: {joint: [] for joint in joints}
            for phase, joints in phase_joints.items()
        }
        dropped = {}
        scoped_out = {}
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
            allowed = phase_scope.get(f"{action}/{clip_name}")
            for phase, index in (("contact", contact), ("crouch", crouch)):
                if index is None or phase not in samples:
                    continue
                if allowed is not None and phase not in allowed:
                    scoped_out.setdefault(phase, []).append(clip_name)
                    continue
                landmarks = frames[index]["landmarks"]
                for joint in phase_joints[phase]:
                    if _joint_is_offscreen_guess(landmarks, joint):
                        dropped.setdefault(f"{phase}.{joint}", []).append(
                            (clip_name, round(frames[index]["angles"][joint], 1)))
                        continue
                    samples[phase][joint].append(frames[index]["angles"][joint])
                # Shape features from the SAME frame, gated the same way. Only
                # the ones SHAPE_CHECKS asks for, so an empty table costs one
                # dict lookup per phase and writes nothing.
                for (check_action, check_phase, feature), _spec in SHAPE_CHECKS.items():
                    if check_action != action or check_phase != phase:
                        continue
                    if landmarks_offscreen(landmarks, SHAPE_LANDMARKS[feature]):
                        continue
                    value = get_shape_features(landmarks).get(feature)
                    if value is not None:
                        shape_samples.setdefault((phase, feature), []).append(value)
            used_clips += 1

        if used_clips == 0:
            continue

        phases = {}
        for phase, joints in phase_joints.items():
            phase_stats = {}
            for joint, values in samples[phase].items():
                if not values:
                    continue
                rule = ACTION_RULES.get(action, {}).get(phase, {}).get(joint, {})
                band = _band(values, joint, has_high_rule=bool(rule.get("high")))
                skipped = dropped.get(f"{phase}.{joint}", [])
                if skipped:
                    # Recorded in the output, not just printed: a band quietly built
                    # from fewer samples than the clip count suggests is exactly how
                    # the 23.6-degree knee survived unnoticed for weeks.
                    band["dropped_offscreen"] = len(skipped)
                    band["clips_available"] = len(values) + len(skipped)
                phase_stats[joint] = band
            if phase_stats:
                phases[phase] = phase_stats

        shape_checks = {}
        for (check_action, phase, feature), spec in SHAPE_CHECKS.items():
            if check_action != action:
                continue
            values = shape_samples.get((phase, feature))
            if not values:
                print(f"  WARNING: shape check {action}.{phase}.{feature} has no "
                      f"samples and was not published")
                continue
            band = _shape_band(values, spec["side"])
            band["code"] = spec["code"]
            shape_checks[f"{phase}.{feature}"] = band
            print(f"  shape check {phase}.{feature} from {len(values)} samples: "
                  f"{band['accepted_range']}")

        result["actions"][action] = {"clips": used_clips, "phases": phases}
        if shape_checks:
            result["actions"][action]["shape_checks"] = shape_checks
        print(f"[{action}] calibrated from {used_clips}/{len(clips)} clips")
        for phase, names in sorted(scoped_out.items()):
            print(f"  SCOPED OUT {len(names)} clip(s) from {phase} by "
                  f"dataset/clip_phase_scope.json: {', '.join(sorted(names))}")
        for key, skipped in sorted(dropped.items()):
            phase, joint = key.split(".", 1)
            kept = len(samples[phase][joint])
            listed = ", ".join(f"{name} {angle}"
                               for name, angle in sorted(skipped, key=lambda s: s[1])[:4])
            print(f"  DROPPED {len(skipped)} {key} sample(s) — joint off-screen and "
                  f"unconfident: {listed}{' ...' if len(skipped) > 4 else ''}")
            if kept < 10:
                print(f"  ^ WARNING: {key} now rests on {kept} samples — treat that "
                      f"threshold as weakly grounded")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    print(f"written: {OUTPUT_PATH}")
    sync_result = sync_frontend(ROOT_DIR)
    print(f"synced frontend: {sync_result['buildVersion']}")


if __name__ == "__main__":
    main()
