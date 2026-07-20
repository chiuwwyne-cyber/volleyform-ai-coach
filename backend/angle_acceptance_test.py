import os
import sys
from types import SimpleNamespace

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.reference_evaluation import (  # noqa: E402
    ACTION_RULES,
    _reference_tolerance,
    evaluate_with_reference,
    reference_for,
)


OVERHEAD_ACTIONS = {"spike", "serve", "block"}
EXPECTED_LOW_ISSUES = {
    "spike": {"contact": {"elbow": "elbow_bad", "shoulder": "shoulder_low"}},
    "serve": {"contact": {"elbow": "elbow_bad", "shoulder": "shoulder_low"}},
    "block": {
        "contact": {"elbow": "elbow_not_straight", "shoulder": "hands_not_high"}
    },
    "receive": {"contact": {"elbow": "elbow_bad"}},
    "set": {"contact": {"elbow": "elbow_position_bad", "shoulder": "shoulder_low"}},
}
EXPECTED_HIGH_ISSUES = {
    "spike": {"crouch": {"knee": "knee_bad"}},
    "serve": {"crouch": {"knee": "knee_bad"}},
    "block": {"crouch": {"knee": "knee_bad"}},
    "receive": {"contact": {"knee": "knee_bad"}},
    "set": {"contact": {"elbow": "elbow_position_bad"}},
}


def _point(x=0.5, y=0.5, z=0.0):
    return SimpleNamespace(x=x, y=y, z=z)


def _landmarks(wrist_y=0.45, wrist_gap=0.16, wrist_level_gap=0.0, hip_y=0.62):
    points = [_point() for _index in range(33)]
    points[0] = _point(0.5, 0.22)
    points[11] = _point(0.44, 0.36)
    points[12] = _point(0.56, 0.36)
    points[15] = _point(0.5 - wrist_gap / 2, wrist_y - wrist_level_gap / 2)
    points[16] = _point(0.5 + wrist_gap / 2, wrist_y + wrist_level_gap / 2)
    points[23] = _point(0.46, hip_y)
    points[24] = _point(0.54, hip_y)
    return points


def _frame(wrist_y, wrist_gap, hip_y, angles, hands=None):
    return {
        "landmarks": _landmarks(wrist_y=wrist_y, wrist_gap=wrist_gap, hip_y=hip_y),
        "world": [],
        "angles": dict(angles),
        "positions": {"wrist_y": wrist_y, "head_y": 0.22},
        "hand_features": hands
        or {
            "hands_detected": 2,
            "finger_extension": 1.2,
            "hand_center_gap": 0.12,
            "hands_level_gap": 0.02,
        },
        "time_seconds": 1.0,
    }


def _band(action, phase, joint):
    entry = reference_for(action)
    assert entry, f"{action} must use reference mode for acceptance testing"
    band = entry["phases"][phase][joint]
    tolerance = _reference_tolerance(band)
    return band, tolerance


def _mid_angle(action, phase, joint):
    return _band(action, phase, joint)[0]["p50"]


def _slight_low_angle(action, phase, joint):
    band, tolerance = _band(action, phase, joint)
    return band["p10"] - max(1.0, tolerance * 0.8)


def _slight_high_angle(action, phase, joint):
    band, tolerance = _band(action, phase, joint)
    return min(180.0, band["p90"] + max(1.0, tolerance * 0.8))


def _wrong_low_angle(action, phase, joint):
    band, tolerance = _band(action, phase, joint)
    return band["p10"] - tolerance - 8.0


def _wrong_high_angle(action, phase, joint):
    band, tolerance = _band(action, phase, joint)
    return band["p90"] + tolerance + 8.0


def _default_angles(action):
    angles = {"elbow": 150.0, "shoulder": 130.0, "knee": 130.0}
    for phase, joints in ACTION_RULES[action].items():
        for joint in joints:
            angles[joint] = _mid_angle(action, phase, joint)
    return angles


def _frames_for(action, contact_angles=None, crouch_angles=None):
    contact_angles = contact_angles or {}
    crouch_angles = crouch_angles or {}
    base_angles = _default_angles(action)

    if action in OVERHEAD_ACTIONS:
        frames = [
            _frame(0.50, 0.20, 0.54, {**base_angles, **crouch_angles}),
            _frame(0.42, 0.18, 0.84, {**base_angles, **crouch_angles}),
            _frame(0.32, 0.14, 0.54, {**base_angles, **crouch_angles}),
            _frame(0.18, 0.10, 0.55, {**base_angles, **contact_angles}),
            _frame(0.28, 0.14, 0.58, base_angles),
            _frame(0.40, 0.18, 0.60, base_angles),
        ]
        return frames

    if action == "receive":
        frames = [
            _frame(0.52, 0.26, 0.60, base_angles),
            _frame(0.50, 0.22, 0.62, base_angles),
            _frame(0.55, 0.18, 0.64, base_angles),
            _frame(0.54, 0.14, 0.66, base_angles),
            _frame(0.54, 0.02, 0.68, {**base_angles, **contact_angles}),
            _frame(0.57, 0.20, 0.65, base_angles),
        ]
        return frames

    if action == "set":
        frames = [
            _frame(0.48, 0.20, 0.62, base_angles),
            _frame(0.38, 0.16, 0.63, base_angles),
            _frame(0.19, 0.04, 0.64, {**base_angles, **contact_angles}),
            _frame(0.31, 0.10, 0.63, base_angles),
            _frame(0.42, 0.18, 0.62, base_angles),
            _frame(0.46, 0.22, 0.61, base_angles),
        ]
        return frames

    raise AssertionError(f"Unsupported action: {action}")


def _assert_no_issues(action, frames):
    result = evaluate_with_reference(action, frames)
    assert result["report"]["mode"] == "reference"
    assert result["issues"] == [], f"{action} should pass, got {result['issues']}"
    for phase in result["report"]["phases"].values():
        for payload in phase["joints"].values():
            assert payload["status"] == "green"
            assert payload["tolerance"] > 0
            assert payload["accepted_range"][0] < payload["accepted_range"][1]


def test_professional_midline_angles_pass():
    for action in ACTION_RULES:
        _assert_no_issues(action, _frames_for(action))


def test_slight_user_variation_inside_tolerance_passes():
    for action, phases in EXPECTED_LOW_ISSUES.items():
        for phase, joints in phases.items():
            for joint in joints:
                frames = _frames_for(
                    action,
                    contact_angles={joint: _slight_low_angle(action, phase, joint)}
                    if phase == "contact"
                    else {},
                    crouch_angles={joint: _slight_low_angle(action, phase, joint)}
                    if phase == "crouch"
                    else {},
                )
                _assert_no_issues(action, frames)

    for action, phases in EXPECTED_HIGH_ISSUES.items():
        for phase, joints in phases.items():
            for joint in joints:
                frames = _frames_for(
                    action,
                    contact_angles={joint: _slight_high_angle(action, phase, joint)}
                    if phase == "contact"
                    else {},
                    crouch_angles={joint: _slight_high_angle(action, phase, joint)}
                    if phase == "crouch"
                    else {},
                )
                _assert_no_issues(action, frames)


def test_clear_wrong_angles_are_reported():
    for action, phases in EXPECTED_LOW_ISSUES.items():
        for phase, joints in phases.items():
            for joint, issue in joints.items():
                frames = _frames_for(
                    action,
                    contact_angles={joint: _wrong_low_angle(action, phase, joint)}
                    if phase == "contact"
                    else {},
                    crouch_angles={joint: _wrong_low_angle(action, phase, joint)}
                    if phase == "crouch"
                    else {},
                )
                result = evaluate_with_reference(action, frames)
                assert issue in result["issues"], (action, phase, joint, result)

    for action, phases in EXPECTED_HIGH_ISSUES.items():
        for phase, joints in phases.items():
            for joint, issue in joints.items():
                frames = _frames_for(
                    action,
                    contact_angles={joint: _wrong_high_angle(action, phase, joint)}
                    if phase == "contact"
                    else {},
                    crouch_angles={joint: _wrong_high_angle(action, phase, joint)}
                    if phase == "crouch"
                    else {},
                )
                result = evaluate_with_reference(action, frames)
                assert issue in result["issues"], (action, phase, joint, result)


def test_reference_data_is_converged_enough_for_public_beta():
    for action in ACTION_RULES:
        entry = reference_for(action)
        assert entry and entry["clips"] >= 5
        for phase, joints in entry["phases"].items():
            for joint, band in joints.items():
                assert band["count"] >= 5, (action, phase, joint)
                assert band["accepted_range"][0] <= band["p10"], (action, phase, joint)
                assert band["accepted_range"][1] >= band["p90"], (action, phase, joint)
                assert 0.0 <= band["convergence"] <= 1.0
                assert band["convergence_state"] in {"usable", "stable"}
                assert band["tolerance"] <= 24.0


def main():
    test_professional_midline_angles_pass()
    test_slight_user_variation_inside_tolerance_passes()
    test_clear_wrong_angles_are_reported()
    test_reference_data_is_converged_enough_for_public_beta()
    print("angle acceptance ok")
    print("checked scenarios: professional, slight user variation, clear wrong angle")


if __name__ == "__main__":
    main()
