"""Phase-aware evaluation against calibrated or heuristic action standards.

The analyzer first finds the action's key moment, then judges only the joints
that matter for that moment. Calibrated p10-p90 bands from
tools/build_reference.py are preferred. Actions without enough reference clips
use one central heuristic profile so the rule can be replaced by data later.
"""

import json
import os

from backend.phase_segmentation import segment_action

REFERENCE_PATH = os.path.join(os.path.dirname(__file__), "reference_standards.json")

# Fallback degrees of grace beyond a calibrated p10-p90 band. New reference
# files carry per-joint tolerance, which better fits non-professional players.
DEFAULT_BAND_TOLERANCE = 5.0
MAX_BAND_TOLERANCE = 24.0
MIN_CLIPS = 5
RECEIVE_LOBSTER_ELBOW_RISK = 125.0
RECEIVE_LOBSTER_SHOULDER_RISK = 55.0
RECEIVE_LOBSTER_REFERENCE_MARGIN = 4.0

HEURISTIC_STANDARDS = {
    "spike": {
        "contact": {"elbow": {"p10": 150, "p90": 180}, "shoulder": {"p10": 120, "p90": 180}},
        "crouch": {"knee": {"p10": 80, "p90": 165}},
    },
    "serve": {
        "contact": {"elbow": {"p10": 150, "p90": 180}, "shoulder": {"p10": 120, "p90": 180}},
        "crouch": {"knee": {"p10": 95, "p90": 170}},
    },
    "block": {
        "contact": {
            "elbow": {"p10": 165, "p90": 180},
            "shoulder": {"p10": 145, "p90": 180},
        },
        "crouch": {"knee": {"p10": 95, "p90": 165}},
    },
    "receive": {
        "contact": {
            "elbow": {"p10": 155, "p90": 180},
            "knee": {"p10": 95, "p90": 165},
            "shoulder": {"p10": 70, "p90": 135},
        },
    },
    "set": {
        "contact": {
            "elbow": {"p10": 90, "p90": 165},
            "shoulder": {"p10": 95, "p90": 175},
        },
    },
}

ACTION_RULES = {
    "spike": {
        "contact": {
            "elbow": {"low": "elbow_bad"},
            "shoulder": {"low": "shoulder_low"},
        },
        "crouch": {"knee": {"low": "knee_too_bent", "high": "knee_bad"}},
    },
    "serve": {
        "contact": {
            "elbow": {"low": "elbow_bad"},
            "shoulder": {"low": "shoulder_low"},
        },
        "crouch": {"knee": {"low": "knee_too_bent", "high": "knee_bad"}},
    },
    "block": {
        "contact": {
            "elbow": {"low": "elbow_not_straight"},
            "shoulder": {"low": "hands_not_high"},
        },
        "crouch": {"knee": {"low": "knee_too_bent", "high": "knee_bad"}},
    },
    "receive": {
        "contact": {
            "elbow": {"low": "elbow_bad"},
            "knee": {"low": "knee_too_bent", "high": "knee_bad"},
            "shoulder": {},
        },
    },
    "set": {
        "contact": {
            "elbow": {"low": "elbow_position_bad", "high": "elbow_position_bad"},
            "shoulder": {"low": "shoulder_low"},
        },
    },
}

PHASE_LABELS = {
    "spike": {"contact": "hit", "crouch": "load"},
    "serve": {"contact": "serve_contact", "crouch": "load"},
    "block": {"contact": "max_reach", "crouch": "pre_jump"},
    "receive": {"contact": "platform_contact"},
    "set": {"contact": "set_release"},
}

_reference_cache = None


def _load_reference():
    global _reference_cache
    if _reference_cache is None:
        try:
            with open(REFERENCE_PATH, "r", encoding="utf-8") as file:
                _reference_cache = json.load(file)
        except (OSError, json.JSONDecodeError):
            _reference_cache = {}
    return _reference_cache


def reference_for(action_type):
    actions = _load_reference().get("actions", {})
    entry = actions.get(action_type)
    if not entry or entry.get("clips", 0) < MIN_CLIPS:
        return None
    return entry


# A high-side issue code needs the ceiling to sit where the error can actually
# land. Two requirements pull against each other, and the data says where they
# meet:
#
#   * don't flag correct technique -> ceiling must clear the largest KEPT sample
#   * catch a limb that never bent  -> ceiling must sit below what a straight limb
#     reads, measured by synthesising one at realistic landmark noise (sigma 0.01):
#     mean 176.4, minimum 168.3
#
# So the ceiling is capped at STRAIGHT_LIMB_FLOOR when that still clears the
# reference. Without this, symmetric tolerance drove serve's crouch knee to
# exactly 180.0 while the evaluator tests `value > hi` -- a check that looks live
# in the UI and is arithmetically dead -- and block sat at 174.8, which a straight
# leg clears only sometimes.
#
# When the largest kept sample is ALREADY above the floor, correct technique and
# the error read the same, and no ceiling can separate them. serve is that case:
# a standing serve genuinely does not bend the knees (max kept 170.9), so the
# check is left alone and recorded as knowingly dead rather than faked.
STRAIGHT_LIMB_FLOOR = 168.0


def _band_range(band, tolerance, has_high_rule=False):
    low = max(0.0, band["p10"] - tolerance)
    high = min(180.0, band["p90"] + tolerance)
    if has_high_rule:
        # max_kept, not max: max is computed before IQR trimming, so a sample the
        # calibration excluded could otherwise raise the ceiling.
        observed_max = band.get("max_kept", band.get("max"))
        if observed_max is not None and float(observed_max) < STRAIGHT_LIMB_FLOOR:
            high = min(high, STRAIGHT_LIMB_FLOOR)
    return low, high


def _reference_tolerance(band):
    try:
        tolerance = float(band.get("tolerance", DEFAULT_BAND_TOLERANCE))
    except (TypeError, ValueError):
        tolerance = DEFAULT_BAND_TOLERANCE
    return max(0.0, min(MAX_BAND_TOLERANCE, tolerance))


def _band_for(action_type, entry, phase, joint):
    if entry:
        band = entry.get("phases", {}).get(phase, {}).get(joint)
        if band:
            return band, _reference_tolerance(band), "reference"
    band = HEURISTIC_STANDARDS.get(action_type, {}).get(phase, {}).get(joint)
    if band:
        return band, 0.0, "heuristic"
    return None, 0.0, None


def _receive_lobster_elbow_threshold():
    entry = reference_for("receive")
    band, tolerance, _source = _band_for("receive", entry, "contact", "elbow")
    if not band:
        return RECEIVE_LOBSTER_ELBOW_RISK
    accepted_low, _accepted_high = _band_range(band, tolerance)
    return min(
        RECEIVE_LOBSTER_ELBOW_RISK,
        max(0.0, accepted_low - RECEIVE_LOBSTER_REFERENCE_MARGIN),
    )


def _round_seconds(value):
    if value is None:
        return None
    return round(max(0.0, float(value)), 1)


def _add_issue(issues, issue_frames, code, phase_index):
    if code not in issues:
        issues.append(code)
    issue_frames.setdefault(code, phase_index)


def _phase_report(action_type, phase, phase_index, frames):
    payload = {
        "frame": phase_index + 1 if phase_index is not None else None,
        "label": PHASE_LABELS.get(action_type, {}).get(phase, phase),
        "joints": {},
    }
    if phase_index is not None:
        time_seconds = _round_seconds(frames[phase_index].get("time_seconds"))
        if time_seconds is not None:
            payload["time_seconds"] = time_seconds
    return payload


def _evaluate_joint(
    action_type,
    entry,
    frames,
    phase,
    phase_index,
    joint,
    rule,
    issues,
    issue_frames,
):
    band, tolerance, source = _band_for(action_type, entry, phase, joint)
    if not band or phase_index is None:
        return None

    value = frames[phase_index]["angles"].get(joint)
    if value is None:
        return None

    lo, hi = _band_range(band, tolerance, has_high_rule=bool(rule.get("high")))
    status = "green"
    issue_code = None
    direction = "ok"
    if value < lo and rule.get("low"):
        status = "red"
        issue_code = rule["low"]
        direction = "low"
        _add_issue(issues, issue_frames, rule["low"], phase_index)
    elif value > hi and rule.get("high"):
        status = "red"
        issue_code = rule["high"]
        direction = "high"
        _add_issue(issues, issue_frames, rule["high"], phase_index)

    return {
        "value": round(value, 1),
        "band": [band["p10"], band["p90"]],
        "tolerance": round(tolerance, 1),
        "accepted_range": [round(lo, 1), round(hi, 1)],
        "convergence": band.get("convergence"),
        "status": status,
        "issue_code": issue_code,
        "direction": direction,
        "source": source,
    }


def _positions_for(frame):
    positions = frame.get("positions") or {}
    if "wrist_y" in positions and "head_y" in positions:
        return positions
    landmarks = frame.get("landmarks") or []
    if len(landmarks) < 17:
        return positions
    return {
        "wrist_y": min(landmarks[15].y, landmarks[16].y),
        "head_y": landmarks[0].y,
    }


def _evaluate_hand_shape(action_type, frames, contact, issues, issue_frames):
    frame = frames[contact]
    hand_features = frame.get("hand_features") or {}

    if action_type == "receive":
        if hand_features.get("hands_detected", 0) >= 2:
            if (hand_features.get("hands_level_gap") or 0) > 0.08:
                _add_issue(issues, issue_frames, "receive_platform_unbalanced", contact)
            if (hand_features.get("hand_center_gap") or 0) > 0.24:
                _add_issue(issues, issue_frames, "receive_hands_apart", contact)

        angles = frame.get("angles", {})
        if (
            angles.get("elbow", 180) < _receive_lobster_elbow_threshold()
            and angles.get("shoulder", 180) < RECEIVE_LOBSTER_SHOULDER_RISK
        ):
            _add_issue(issues, issue_frames, "lobster_receive_risk", contact)
        return

    if action_type == "set":
        positions = _positions_for(frame)
        if positions.get("wrist_y", 0) > positions.get("head_y", 1):
            _add_issue(issues, issue_frames, "wrist_low", contact)

        if hand_features.get("hands_detected", 0) < 2:
            _add_issue(issues, issue_frames, "setting_hands_not_detected", contact)
            return

        if hand_features.get("finger_extension", 0) < 1.08:
            _add_issue(issues, issue_frames, "setting_fingers_closed", contact)
        hand_center_gap = hand_features.get("hand_center_gap")
        if hand_center_gap is not None and (hand_center_gap < 0.06 or hand_center_gap > 0.32):
            _add_issue(issues, issue_frames, "setting_hand_spacing_bad", contact)
        if (hand_features.get("hands_level_gap") or 0) > 0.08:
            _add_issue(issues, issue_frames, "setting_hands_unbalanced", contact)


def evaluate_with_reference(action_type, frames):
    """Return phase-aware issues or None when the action cannot be segmented."""
    if action_type not in ACTION_RULES:
        return None

    segments = segment_action(action_type, [frame["landmarks"] for frame in frames])
    if not segments:
        return None

    entry = reference_for(action_type)
    mode = "reference" if entry else "heuristic"
    issues = []
    issue_frames = {}
    report = {
        "mode": mode,
        "clips": entry.get("clips", 0) if entry else 0,
        "phases": {},
    }

    for phase, joint_rules in ACTION_RULES[action_type].items():
        phase_index = segments.get(phase)
        phase_payload = _phase_report(action_type, phase, phase_index, frames)
        for joint, rule in joint_rules.items():
            joint_payload = _evaluate_joint(
                action_type,
                entry,
                frames,
                phase,
                phase_index,
                joint,
                rule,
                issues,
                issue_frames,
            )
            if joint_payload:
                phase_payload["joints"][joint] = joint_payload
        report["phases"][phase] = phase_payload

    contact = segments["contact"]
    _evaluate_hand_shape(action_type, frames, contact, issues, issue_frames)
    report["issues"] = issues
    report["issue_frames"] = issue_frames

    return {
        "issues": issues,
        "issue_frames": issue_frames,
        "contact_index": contact,
        "crouch_index": segments.get("crouch"),
        "report": report,
    }
