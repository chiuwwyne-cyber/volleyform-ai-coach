import json
import math
import os
import sys
from types import SimpleNamespace

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.phase_segmentation import segment_action
from backend.reference_evaluation import (
    _band_for,
    _band_range,
    evaluate_with_reference,
    reference_for,
)


def _standards():
    path = os.path.join(ROOT_DIR, "backend", "reference_standards.json")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _point(x=0.5, y=0.5, z=0.0):
    return SimpleNamespace(x=x, y=y, z=z)


def _landmarks(wrist_y=0.45, wrist_gap=0.18, wrist_level_gap=0.0, hip_y=0.62):
    points = [_point() for _index in range(33)]
    points[0] = _point(0.5, 0.22)
    points[11] = _point(0.44, 0.36)
    points[12] = _point(0.56, 0.36)
    points[15] = _point(0.5 - wrist_gap / 2, wrist_y - wrist_level_gap / 2)
    points[16] = _point(0.5 + wrist_gap / 2, wrist_y + wrist_level_gap / 2)
    points[23] = _point(0.46, hip_y)
    points[24] = _point(0.54, hip_y)
    return points


def _frame(wrist_y, wrist_gap, hip_y, angles, positions=None, hands=None):
    landmarks = _landmarks(wrist_y=wrist_y, wrist_gap=wrist_gap, hip_y=hip_y)
    return {
        "landmarks": landmarks,
        "world": landmarks,
        "angles": angles,
        "positions": positions or {"wrist_y": wrist_y, "head_y": 0.22},
        "hand_features": hands or {"hands_detected": 2, "finger_extension": 1.2},
        "time_seconds": len(str(wrist_y)),
    }


def _base_angles(elbow=170, knee=130, shoulder=120):
    return {"elbow": elbow, "knee": knee, "shoulder": shoulder}


def test_receive_uses_platform_phase():
    frames = [
        _frame(0.52, 0.26, 0.60, _base_angles()),
        _frame(0.50, 0.22, 0.62, _base_angles()),
        _frame(0.55, 0.18, 0.64, _base_angles()),
        _frame(0.54, 0.14, 0.66, _base_angles()),
        _frame(0.54, 0.02, 0.68, _base_angles(elbow=110, knee=178, shoulder=45)),
        _frame(0.57, 0.20, 0.65, _base_angles()),
    ]

    result = evaluate_with_reference("receive", frames)

    assert result["report"]["mode"] == "reference"
    assert result["report"]["clips"] >= 5
    assert result["contact_index"] == 4
    assert "elbow_bad" in result["issues"]
    assert "knee_bad" in result["issues"]
    assert "lobster_receive_risk" in result["issues"]


def test_set_uses_release_phase():
    frames = [
        _frame(0.48, 0.20, 0.62, _base_angles()),
        _frame(0.38, 0.16, 0.63, _base_angles()),
        _frame(0.25, 0.04, 0.64, _base_angles(elbow=72, shoulder=58)),
        _frame(0.31, 0.10, 0.63, _base_angles()),
        _frame(0.42, 0.18, 0.62, _base_angles()),
        _frame(0.46, 0.22, 0.61, _base_angles()),
    ]

    result = evaluate_with_reference("set", frames)

    assert result["report"]["mode"] == "reference"
    assert result["report"]["clips"] >= 5
    assert result["contact_index"] == 2
    assert "elbow_position_bad" in result["issues"]
    assert "shoulder_low" in result["issues"]


def test_reference_band_uses_dynamic_tolerance():
    entry = {
        "clips": 8,
        "phases": {
            "contact": {
                "elbow": {"p10": 100, "p90": 150, "tolerance": 12.5}
            }
        },
    }

    _band, tolerance, source = _band_for("receive", entry, "contact", "elbow")

    assert tolerance == 12.5
    assert source == "reference"


def test_block_uses_max_reach_phase():
    frames = [
        _frame(0.42, 0.20, 0.60, _base_angles()),
        _frame(0.36, 0.18, 0.65, _base_angles(knee=170)),
        _frame(0.30, 0.14, 0.61, _base_angles()),
        _frame(0.20, 0.10, 0.55, _base_angles(elbow=120, shoulder=90)),
        _frame(0.28, 0.14, 0.58, _base_angles()),
        _frame(0.40, 0.18, 0.60, _base_angles()),
    ]

    result = evaluate_with_reference("block", frames)

    assert result["report"]["mode"] == "reference"
    assert result["report"]["clips"] >= 5
    assert result["contact_index"] == 3
    assert "elbow_not_straight" in result["issues"]
    assert "hands_not_high" in result["issues"]


def _serve_frames(contact_angles, crouch_angles=None):
    """A serve: crouch, then reach, with the highest wrist as the contact.

    The crouch angles go on EVERY pre-contact frame, not just the visually
    "loaded" one. `_crouch_before` picks the lowest hip after a 3-frame smooth,
    and that smoothing moved the winner off the frame this fixture used to mark:
    setting crouch knee to 11 landed the evaluator on frame 0, which carried the
    default 130, so the parameter silently did nothing and any crouch test
    written with it would have passed unconditionally. Spreading the angles
    removes the dependence on which frame wins, which is what
    `angle_acceptance_test._frames_for` already does.
    """
    crouch = crouch_angles or _base_angles(knee=150)
    frames = [
        _frame(0.46, 0.20, 0.58, crouch),
        _frame(0.50, 0.18, 0.84, crouch),          # loaded, hips lowest
        _frame(0.34, 0.14, 0.60, crouch),
        _frame(0.16, 0.10, 0.56, contact_angles),  # highest wrist = contact
        _frame(0.30, 0.14, 0.58, _base_angles()),
        _frame(0.44, 0.18, 0.60, _base_angles()),
    ]
    # Fail loudly rather than vacuously if segmentation ever drifts again.
    segments = segment_action("serve", [frame["landmarks"] for frame in frames])
    assert segments["contact"] == 3, (
        f"fixture no longer segments as intended: contact={segments['contact']}"
    )
    assert frames[segments["crouch"]]["angles"] == crouch, (
        f"crouch angles never reach the evaluator: it picked frame "
        f"{segments['crouch']}, which does not carry them"
    )
    return frames


def test_serve_flags_a_low_arm():
    """A serve struck with the arm dropped must still be caught.

    Serve had NO fixed case here for a long time, which mattered because the
    other serve test derives its angles from the band itself and therefore
    cannot notice the band moving. These angles are hard-coded on purpose: if a
    future dataset shifts the standard far enough that a clearly bad serve stops
    being flagged, this fails, which is the whole point.
    """
    result = evaluate_with_reference("serve", _serve_frames(_base_angles(elbow=95, shoulder=40)))

    assert result["report"]["mode"] == "reference"
    assert result["contact_index"] == 3
    assert "elbow_bad" in result["issues"], result["issues"]
    assert "shoulder_low" in result["issues"], result["issues"]


def test_serve_accepts_a_sound_standing_serve():
    """And a textbook standing serve must NOT be nagged at.

    This is the false-positive guard. The 2026-08-16 expansion tightened the
    serve crouch knee floor from 80.4 to 108.3 degrees because the clips added
    were standing serves, so a band that drifts further could start calling a
    normal serve wrong.
    """
    result = evaluate_with_reference("serve", _serve_frames(_base_angles(elbow=165, shoulder=140)))

    assert result["report"]["mode"] == "reference"
    assert "elbow_bad" not in result["issues"], result["issues"]
    assert "shoulder_low" not in result["issues"], result["issues"]

    # And guard the band directly, because the assertions above only bite once a
    # drift is severe. The 2026-08-16 expansion moved the crouch knee floor from
    # 80.4 to 108.3 degrees; at 130 a server bending the knees normally would be
    # told they are wrong, so that is where the line is drawn.
    band, tolerance, _source = _band_for("serve", reference_for("serve"), "crouch", "knee")
    floor = max(0.0, band["p10"] - tolerance)
    assert floor <= 130.0, (
        f"serve crouch knee floor has drifted to {floor:.1f}; a normally bent "
        "knee would now be flagged"
    )


# A straight limb synthesised at realistic landmark noise (sigma 0.01 on
# normalised coordinates) reads a mean of 176.4 and a MINIMUM of 168.3 through
# this pipeline. Guard against the minimum, not the mean: a ceiling at 174 would
# still miss every straight leg that happens to read below it. Using the mean here
# was the first version of this test and it let the bug back in under mutation --
# it passed with block's ceiling at 174.8.
STRAIGHT_LIMB_FLOOR = 168.0

# Checks known to be unfireable, with the reason. serve's own reference contains a
# 170.9-degree crouch knee: standing serves genuinely do not bend, so "you did not
# load your legs" contradicts the data it would be judged against. Recording it
# here beats pretending the check works.
KNOWN_DEAD_HIGH_CHECKS = {
    ("serve", "crouch", "knee"): (
        "standing serves do not load the legs; the reference max is 170.9, so any "
        "ceiling that keeps the reference clips green is above a straight leg"
    ),
}


def test_high_side_checks_can_actually_fire():
    """An issue code whose threshold is unreachable is decoration, not a check.

    serve's crouch-knee ceiling was exactly 180.0 while the evaluator tests
    `value > hi`, so `knee_bad` could never fire for any input at all. block sat
    at 177.0, which a straight leg clears only about half the time. Both looked
    healthy in reference_standards.json.
    """
    from backend.reference_evaluation import ACTION_RULES

    dead = []
    for action, phases in ACTION_RULES.items():
        entry = reference_for(action)
        for phase, joints in phases.items():
            for joint, rule in joints.items():
                if not rule.get("high"):
                    continue
                band, tolerance, _source = _band_for(action, entry, phase, joint)
                if not band:
                    continue
                _lo, hi = _band_range(band, tolerance, has_high_rule=True)
                if hi > STRAIGHT_LIMB_FLOOR:
                    key = (action, phase, joint)
                    if key not in KNOWN_DEAD_HIGH_CHECKS:
                        dead.append(f"{action}.{phase}.{joint} ceiling {hi:.1f} "
                                    f"sits above the straight-limb floor "
                                    f"({STRAIGHT_LIMB_FLOOR}), so straight limbs "
                                    f"reading below it are never reported")
    assert not dead, (
        "these high-side checks cannot fire; either bound the ceiling or record "
        "them in KNOWN_DEAD_HIGH_CHECKS with a reason:\n  " + "\n  ".join(dead)
    )


def test_band_range_high_cap_uses_kept_maximum():
    """Direct unit check, because the dataset cannot exercise this on its own.

    Right now `max` and `max_kept` happen to be equal for every band that carries
    a high-side code, so swapping one for the other changes nothing and a
    data-driven test cannot see the difference. That is luck, not a property: `max`
    is taken before IQR trimming, so one excluded outlier would silently raise the
    ceiling. Synthetic bands pin the behaviour regardless of what the data does.
    """
    # An outlier at 178 was trimmed; the kept maximum is 150, so the cap applies.
    band = {"p10": 100.0, "p90": 150.0, "max": 178.0, "max_kept": 150.0}
    _lo, high = _band_range(band, 25.0, has_high_rule=True)
    assert high == STRAIGHT_LIMB_FLOOR, (
        f"expected the cap at {STRAIGHT_LIMB_FLOOR}, got {high} -- reading `max` "
        "instead of `max_kept` would give 175.0 and skip the cap"
    )

    # Correct technique itself reaches past the floor: no ceiling can separate it
    # from a straight limb, so leave the range alone rather than flag real form.
    band = {"p10": 120.0, "p90": 167.0, "max": 171.0, "max_kept": 171.0}
    _lo, high = _band_range(band, 19.0, has_high_rule=True)
    assert high == 180.0, f"expected the range untouched, got {high}"

    # No high-side code: nothing to keep live, so the cap must not apply.
    band = {"p10": 100.0, "p90": 150.0, "max": 152.0, "max_kept": 152.0}
    _lo, high = _band_range(band, 25.0, has_high_rule=False)
    assert high == 175.0, f"cap applied without a high-side rule: {high}"


def test_high_side_ceiling_never_flags_its_own_reference():
    """The standard must not call the clips it KEPT wrong on the high side.

    Compare against `max_kept`, not `max`. `max` is taken before IQR trimming, so
    it can be a sample the calibration deliberately threw out -- set.contact.elbow
    reports max 177.8 against a p90 of 154.0, and that outlier is *supposed* to sit
    outside the accepted range. An earlier version of this test asserted against
    `max` and failed on clean code for exactly that reason; the assertion was wrong,
    not the product.
    """
    from backend.reference_evaluation import ACTION_RULES

    for action, phases in ACTION_RULES.items():
        entry = reference_for(action)
        for phase, joints in phases.items():
            for joint, rule in joints.items():
                if not rule.get("high"):
                    continue
                band, tolerance, _source = _band_for(action, entry, phase, joint)
                kept_max = band.get("max_kept")
                if not band or kept_max is None:
                    continue
                _lo, hi = _band_range(band, tolerance, has_high_rule=True)
                assert kept_max <= hi, (
                    f"{action}.{phase}.{joint}: the largest KEPT sample {kept_max} "
                    f"exceeds its own accepted ceiling {hi:.1f}, so a clip the "
                    f"calibration accepted would be flagged by the standard it built"
                )


def test_receive_shoulder_is_covered_elsewhere():
    """The empty receive shoulder rule is safe only while the lobster rule reads shoulder.

    ACTION_RULES["receive"]["contact"]["shoulder"] is {} on purpose: a standalone
    band there would flag correct low platforms, because a receive shoulder is
    only a fault when the arms are bent too. lobster_receive_risk carries that
    judgement instead. If someone ever simplifies that rule down to the elbow
    alone -- or removes it -- the empty table stops being a deliberate choice and
    becomes a real hole where the shoulder is never judged at all.
    """
    from backend.reference_evaluation import ACTION_RULES

    assert ACTION_RULES["receive"]["contact"]["shoulder"] == {}, (
        "this test exists to justify an EMPTY receive shoulder rule; a real band "
        "now exists, so re-read the reasoning before deleting either one"
    )

    def _receive(shoulder):
        return [
            _frame(0.52, 0.26, 0.60, _base_angles()),
            _frame(0.50, 0.22, 0.62, _base_angles()),
            _frame(0.55, 0.18, 0.64, _base_angles()),
            _frame(0.54, 0.14, 0.66, _base_angles()),
            _frame(0.54, 0.02, 0.68, _base_angles(elbow=95, shoulder=shoulder)),
            _frame(0.57, 0.20, 0.65, _base_angles()),
        ]

    dropped = evaluate_with_reference("receive", _receive(shoulder=35))
    assert "lobster_receive_risk" in dropped["issues"], (
        "a receive with bent arms AND dropped shoulders reports nothing about the "
        "shoulder, and the rule table has no band to fall back on: {0}".format(dropped["issues"])
    )

    # The half that mutation testing needs. Same bent elbow, shoulders held up:
    # if the rule ever stops reading shoulder, this still says lobster and the
    # assertion above passes for the wrong reason.
    lifted = evaluate_with_reference("receive", _receive(shoulder=140))
    assert "lobster_receive_risk" not in lifted["issues"], (
        "lobster_receive_risk fired on a receive whose shoulders were at 140 "
        "degrees, so it is no longer reading the shoulder -- the empty rule "
        "table is now a genuine gap: {0}".format(lifted["issues"])
    )


def test_joint_model_catches_what_the_bands_cannot():
    """Elbow 130 with shoulder 175 is inside BOTH block bands and still wrong.

    The bands judge each joint alone, which assumes they move independently. In a
    real block they do not -- elbow and shoulder correlate at r=0.87 -- so the pair
    of bands accepts a rectangle that no reference clip occupies the corners of.
    A bent elbow with the shoulder driven to its limit is one of those corners:
    both numbers pass, the combination never happens.

    Hard-coded angles on purpose. Deriving them from the fitted model would make
    the test agree with whatever the model says, including after the model breaks.
    """
    frames = [
        _frame(0.42, 0.20, 0.60, _base_angles()),
        _frame(0.36, 0.18, 0.65, _base_angles(knee=170)),
        _frame(0.30, 0.14, 0.61, _base_angles()),
        _frame(0.20, 0.10, 0.55, _base_angles(elbow=130, shoulder=175)),
        _frame(0.28, 0.14, 0.58, _base_angles()),
        _frame(0.40, 0.18, 0.60, _base_angles()),
    ]

    result = evaluate_with_reference("block", frames)

    assert result["contact_index"] == 3
    assert "elbow_not_straight" not in result["issues"], (
        "130 should be inside the block elbow band; if it is not, this test is no "
        f"longer testing the joint model: {result['issues']}"
    )
    assert "hands_not_high" not in result["issues"], result["issues"]
    assert "elbow_shoulder_mismatch" in result["issues"], (
        "the joint model let through a pose that is inside both bands and outside "
        f"every reference clip: {result['issues']}"
    )


def test_joint_model_leaves_sound_form_alone():
    """And the middle of the reference distribution must stay silent.

    This is the false-positive half. An extra check can only ADD flags, so it is
    the one kind of change that can make the app worse for players who are already
    doing it right -- the exact failure this project weights heaviest.
    """
    frames = [
        _frame(0.42, 0.20, 0.60, _base_angles()),
        _frame(0.36, 0.18, 0.65, _base_angles(knee=170)),
        _frame(0.30, 0.14, 0.61, _base_angles()),
        _frame(0.20, 0.10, 0.55, _base_angles(elbow=152, shoulder=139)),
        _frame(0.28, 0.14, 0.58, _base_angles()),
        _frame(0.40, 0.18, 0.60, _base_angles()),
    ]

    result = evaluate_with_reference("block", frames)

    assert "elbow_shoulder_mismatch" not in result["issues"], result["issues"]
    model = result["report"]["phases"]["contact"].get("joint_model")
    assert model is not None, "the joint model should report even when it passes"
    assert model["status"] == "green", model
    assert model["distance"] < model["threshold"], model


def test_joint_model_does_not_pile_on():
    """When a band already flagged the joint, the joint model stays quiet.

    Elbow 100 with shoulder 175 is 8.25 away from the reference centre, so the
    model would happily fire -- but the elbow band already said "arm not straight",
    and saying it twice in different words reads as two problems. Every extra
    message spends the trust that makes the others worth reading.
    """
    frames = [
        _frame(0.42, 0.20, 0.60, _base_angles()),
        _frame(0.36, 0.18, 0.65, _base_angles(knee=170)),
        _frame(0.30, 0.14, 0.61, _base_angles()),
        _frame(0.20, 0.10, 0.55, _base_angles(elbow=100, shoulder=175)),
        _frame(0.28, 0.14, 0.58, _base_angles()),
        _frame(0.40, 0.18, 0.60, _base_angles()),
    ]

    result = evaluate_with_reference("block", frames)

    assert "elbow_not_straight" in result["issues"], result["issues"]
    assert "elbow_shoulder_mismatch" not in result["issues"], (
        "the joint model piled onto a fault the band already reported: "
        f"{result['issues']}"
    )


def test_joint_model_threshold_still_clears_its_own_reference():
    """The cutoff itself needs a guard, because no behaviour test covers it.

    Dropping the block threshold from 3.3 to 0.5 -- which would flag very nearly
    every block a user ever films -- passed all three behaviour tests above. They
    check a pose the model should catch and a pose it should not, and a pose at the
    centre of the distribution stays inside even an absurd cutoff. So the tests can
    all be green while the check has become a false-positive machine.

    These are the two rules build_reference applies when it picks the number, read
    back off the published file:
      * above max_accepted_md -- clears every clip the bands already accept, so the
        new check invents no flag on footage the calibration called correct
      * at least sqrt(chi2(0.99, df=2)) -- never rejects more than ~1% of its own
        fitted distribution
    and the third rule, that the model still rejects enough of the accepted box to
    be worth its risk.
    """
    # Mirrored from tools/build_reference.py rather than imported: that module pulls
    # in mediapipe, and a several-second import in a fast unit test gets skipped.
    MAHALANOBIS_FLOOR = 3.03
    JOINT_MODEL_MIN_GAIN = 0.05

    standards = _standards()["actions"]
    checked = 0
    for action, entry in sorted(standards.items()):
        model = entry.get("joint_model")
        if not model:
            continue
        checked += 1
        key = f"{action}.{model['phase']}"
        assert model["threshold"] > model["max_accepted_md"], (
            f"{key}: cutoff {model['threshold']} does not clear {model['max_accepted_md']}, "
            "the worst clip the bands already accept -- the joint check would flag a "
            "clip the calibration itself treats as correct form"
        )
        assert model["threshold"] >= MAHALANOBIS_FLOOR, (
            f"{key}: cutoff {model['threshold']} rejects "
            f"{100 * math.exp(-model['threshold'] ** 2 / 2):.0f}% of the model's own "
            "distribution; anything under 3.03 is a false-positive storm"
        )
        assert model["newly_rejected"] >= JOINT_MODEL_MIN_GAIN, (
            f"{key}: this model now rejects only {model['newly_rejected']:.1%} of what "
            "the independent bands accept, so it agrees with them and only adds a way "
            "to be wrong -- drop it from JOINT_MODEL_PHASES rather than keep it"
        )
    assert checked, "no joint model found in reference_standards.json"


def main():
    test_receive_uses_platform_phase()
    test_set_uses_release_phase()
    test_reference_band_uses_dynamic_tolerance()
    test_block_uses_max_reach_phase()
    test_serve_flags_a_low_arm()
    test_serve_accepts_a_sound_standing_serve()
    test_high_side_checks_can_actually_fire()
    test_band_range_high_cap_uses_kept_maximum()
    test_high_side_ceiling_never_flags_its_own_reference()
    test_receive_shoulder_is_covered_elsewhere()
    test_joint_model_catches_what_the_bands_cannot()
    test_joint_model_leaves_sound_form_alone()
    test_joint_model_does_not_pile_on()
    test_joint_model_threshold_still_clears_its_own_reference()
    print("phase reference ok")
    print("checked actions: receive, set, block, serve")


if __name__ == "__main__":
    main()
