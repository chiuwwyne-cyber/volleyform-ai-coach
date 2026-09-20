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


def _point(x=0.5, y=0.5, z=0.0, visibility=0.95):
    return SimpleNamespace(x=x, y=y, z=z, visibility=visibility)


def _landmarks(wrist_y=0.45, wrist_gap=0.18, wrist_level_gap=0.0, hip_y=0.62,
               ankle_y=0.92, ankle_visibility=0.95):
    points = [_point() for _index in range(33)]
    points[0] = _point(0.5, 0.22)
    points[11] = _point(0.44, 0.36)
    points[12] = _point(0.56, 0.36)
    points[15] = _point(0.5 - wrist_gap / 2, wrist_y - wrist_level_gap / 2)
    points[16] = _point(0.5 + wrist_gap / 2, wrist_y + wrist_level_gap / 2)
    points[23] = _point(0.46, hip_y)
    points[24] = _point(0.54, hip_y)
    points[27] = _point(0.46, ankle_y, visibility=ankle_visibility)
    points[28] = _point(0.54, ankle_y, visibility=ankle_visibility)
    return points


def _frame(wrist_y, wrist_gap, hip_y, angles, positions=None, hands=None,
           ankle_y=0.92, ankle_visibility=0.95):
    landmarks = _landmarks(wrist_y=wrist_y, wrist_gap=wrist_gap, hip_y=hip_y,
                           ankle_y=ankle_y, ankle_visibility=ankle_visibility)
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


# Low-side bands whose floor sits ABOVE their own smallest kept sample, so a
# clip the calibration treated as correct is flagged by the standard built from
# it. Measured 2026-09-17; the gap in degrees is recorded so a drift shows up as
# a number rather than a pass.
#
# This is arithmetic, not a bug to fix by moving thresholds. The floor is
# p10 - tolerance, and p10 puts 10% of the kept samples below it by definition;
# whether any land outside depends on whether tolerance covers the p10-to-minimum
# gap. It is also where the false-positive rate comes from: 25 of 292 reference
# samples (8.6%) are flagged by the bands built from them, which is the same
# order as the 10.1% leave-one-out rate measured on 2026-09-14.
#
# Listed rather than asserted away. _band_range is low = p10 - tolerance and
# high = p90 + tolerance, so emptying this table means ENLARGING tolerance -- which
# widens every band until real errors stop being caught. (Shrinking it does the
# opposite: a narrower band flags MORE of the reference, not fewer.)
KNOWN_FLOORS_INSIDE_THE_DATA = {
    ("spike", "contact", "elbow"): -3.6,
    ("spike", "contact", "shoulder"): -10.5,
    ("serve", "crouch", "knee"): -2.9,
}


def test_low_side_floors_stay_where_they_were_measured():
    """The mirror of the ceiling test, which had no counterpart until now.

    Compare against `min_kept`, not `min`: `min` is taken before IQR trimming, so
    a floor checked against it can look safe while sitting above a sample the
    calibration actually accepted -- the same trap the high-side test documents.

    Eleven of the fourteen low-side bands clear their own data. The three that do
    not are named above with the gap that was measured; this test fails if a new
    band joins them, if one of them gets worse, or if one quietly gets better and
    nobody updates the record.
    """
    from backend.reference_evaluation import ACTION_RULES

    measured = {}
    for action, phases in ACTION_RULES.items():
        entry = reference_for(action)
        for phase, joints in phases.items():
            for joint, rule in joints.items():
                if not rule.get("low"):
                    continue
                band, tolerance, _source = _band_for(action, entry, phase, joint)
                if not band:
                    continue
                kept_min = band.get("min_kept")
                assert kept_min is not None, (
                    f"{action}.{phase}.{joint} has no min_kept; rebuild with "
                    "tools/build_reference.py")
                lo, _hi = _band_range(band, tolerance,
                                      has_high_rule=bool(rule.get("high")))
                gap = round(kept_min - lo, 1)
                if gap < 0:
                    measured[(action, phase, joint)] = gap

    assert set(measured) == set(KNOWN_FLOORS_INSIDE_THE_DATA), (
        "the set of bands whose floor cuts into their own reference changed.{0}"
        "  now: {1}{0}  recorded: {2}{0}"
        "A band that newly appears here will flag clips the calibration "
        "accepted. One that disappears is good news that belongs in the "
        "table.".format(chr(10), sorted(measured), 
                        sorted(KNOWN_FLOORS_INSIDE_THE_DATA)))
    for key, recorded in KNOWN_FLOORS_INSIDE_THE_DATA.items():
        assert measured[key] >= recorded - 0.5, (
            f"{key} cuts {abs(measured[key])} degrees into its own reference, "
            f"worse than the {abs(recorded)} recorded")


def test_the_block_load_elbow_floor_clears_its_reference():
    """The band added 2026-09-17 must be one of the eleven that clear.

    Its whole purpose is to fire near the bottom of the data, which is exactly
    where a floor starts catching correct technique. Asserted separately from the
    table above so it can never be waved through by being added to it.
    """
    band, tolerance, _source = _band_for("block", reference_for("block"),
                                         "crouch", "elbow")
    lo, _hi = _band_range(band, tolerance, has_high_rule=False)
    assert band["min_kept"] > lo, (
        f"block.crouch.elbow floor {lo:.1f} is above its smallest kept sample "
        f"{band['min_kept']}, so a reference block would be told its arms "
        "dropped")

def _block_frames(crouch_elbow=140, contact_elbow=170, contact_shoulder=170):
    """A block: load, rise, peak, land.

    The load angles go on every pre-contact frame for the reason the serve
    fixture records -- `_crouch_before` smooths the hip series before picking,
    so pinning them to one visually-loaded frame lands the evaluator elsewhere.
    """
    load = _base_angles(elbow=crouch_elbow, knee=120, shoulder=60)
    return [
        _frame(0.42, 0.20, 0.60, load),
        _frame(0.36, 0.18, 0.65, load),
        _frame(0.30, 0.14, 0.61, load),
        _frame(0.20, 0.10, 0.55,
               _base_angles(elbow=contact_elbow, knee=170, shoulder=contact_shoulder)),
        _frame(0.28, 0.14, 0.58, load),
        _frame(0.40, 0.18, 0.60, load),
    ]


def test_block_flags_arms_dropped_at_the_load():
    """Arms hanging at the load, which no angle band watched before today.

    The only labelled-wrong block footage this project has separates here and
    nowhere else: the spans a tutorial marks with a red cross measure 79.2, 51.6
    and 134.7 at the load elbow, against 140.0, 125.7 and 142.8 for the spans it
    marks correct. Hand spacing, the first hypothesis, does not separate them.
    """
    result = evaluate_with_reference("block", _block_frames(crouch_elbow=45))

    assert "block_arms_dropped" in result["issues"], (
        "a block loaded with the elbows at 45 degrees -- arms hanging by the "
        "sides -- was not flagged: {0}".format(result["issues"]))


def test_block_accepts_hands_held_at_the_load():
    """And the far more common correct case must stay silent.

    140 degrees is the median of the reference loads, so a flag here means the
    floor has risen into the data.
    """
    result = evaluate_with_reference("block", _block_frames(crouch_elbow=140))

    assert "block_arms_dropped" not in result["issues"], (
        "a block loaded at 140 degrees, the middle of the reference, was told "
        "its arms had dropped: {0}".format(result["issues"]))


def test_a_joint_outside_the_frame_is_not_judged():
    """Feet out of shot must produce no verdict, not a verdict about the feet.

    MediaPipe does not report that it cannot see the ankles -- it reports a
    position below the frame with a confidence attached. build_reference has
    dropped those samples since 2026-08-17; the evaluator did not, so the app
    judged the one thing the calibration refuses to learn from.

    Measured on the reference set: 4 of the 25 samples the bands flag are
    computed this way, including a 23.6 degree block knee.
    """
    def dig(ankle_y, ankle_visibility):
        """Shaped like test_receive_uses_platform_phase, whose segmentation works.

        The platform phase is the frame where the hands come together, so the
        wrist gap has to close to 0.02 for the segmenter to find a contact at all.
        A shorter fixture returns no segments and evaluate_with_reference returns
        None, which is how the first version of this test failed.
        """
        angles = _base_angles(elbow=170, knee=40, shoulder=120)
        gaps = [0.26, 0.22, 0.18, 0.14, 0.02, 0.20]
        hips = [0.60, 0.62, 0.64, 0.66, 0.68, 0.65]
        wrists = [0.52, 0.50, 0.55, 0.54, 0.54, 0.57]
        return [
            _frame(w, g, h, angles, ankle_y=ankle_y,
                   ankle_visibility=ankle_visibility)
            for w, g, h in zip(wrists, gaps, hips)
        ]
    # The control. A 40 degree knee is far below any receive floor, so if this
    # does not fire the test below proves nothing.
    visible = evaluate_with_reference("receive", dig(0.92, 0.95))
    assert "knee_too_bent" in visible["issues"], (
        "a 40 degree receive knee with the ankles in frame was not flagged, so "
        "the off-screen half of this test cannot mean anything: {0}".format(
            visible["issues"]))

    # Same angles, ankles 0.25 below the bottom edge.
    offscreen = evaluate_with_reference("receive", dig(1.25, 0.12))
    assert "knee_too_bent" not in offscreen["issues"], (
        "the app told a user their knees were wrong from ankles MediaPipe placed "
        "0.25 below the bottom of the frame at 0.12 confidence: {0}".format(
            offscreen["issues"]))
    knee = offscreen["report"]["phases"]["contact"]["joints"].get("knee", {})
    assert knee.get("judged") is False and knee.get("status") == "unknown", (
        "an unjudged joint must say so in the report rather than vanish, or the "
        "app cannot tell the user why it went quiet: {0}".format(knee))

    # And the elbow in the same frames, whose landmarks are all in shot, must
    # still be judged -- the gate is per joint, not per frame.
    assert offscreen["report"]["phases"]["contact"]["joints"]["elbow"].get("judged") is not False, (
        "off-screen ankles stopped the elbow being judged, so the gate is "
        "throwing away the whole frame")


def _set_frames(crouch_knee=130, contact_angles=None, hands=None):
    """A set: approach, load, release, recover.

    The load angles go on every pre-release frame, for the reason the serve
    fixture records -- _crouch_near smooths the hip series before picking, so
    pinning them to one frame lands the evaluator elsewhere.
    """
    load = _base_angles(elbow=120, knee=crouch_knee, shoulder=105)
    release = contact_angles or _base_angles(elbow=120, knee=crouch_knee, shoulder=105)
    return [
        _frame(0.48, 0.20, 0.62, load, hands=hands),
        _frame(0.38, 0.16, 0.63, load, hands=hands),
        _frame(0.25, 0.04, 0.64, release, hands=hands),
        _frame(0.31, 0.10, 0.63, load, hands=hands),
        _frame(0.42, 0.18, 0.62, load, hands=hands),
        _frame(0.46, 0.22, 0.61, load, hands=hands),
    ]


def test_set_flags_legs_that_never_bend():
    """A setter pushing with the arms alone, which nothing watched before today.

    set had no crouch band at all, even though the segmenter has always returned
    one. The ceiling sits at the straight-limb floor, so this only fires on a
    knee that is essentially locked.
    """
    result = evaluate_with_reference("set", _set_frames(crouch_knee=178))

    assert "set_legs_not_used" in result["issues"], (
        "a set played with the knees at 178 degrees -- locked straight -- was "
        "not flagged: {0}".format(result["issues"]))


def test_set_accepts_a_normally_bent_knee():
    """133 is the median of the reference loads; a flag here means the ceiling moved."""
    result = evaluate_with_reference("set", _set_frames(crouch_knee=133))

    assert "set_legs_not_used" not in result["issues"], (
        "a set loaded at 133 degrees, the middle of the reference, was told its "
        "legs were unused: {0}".format(result["issues"]))


def test_set_flags_hands_beside_the_head():
    """The first shape check to ship, and the first set error outside the angles.

    A set is played from above the forehead. The elbow and shoulder angles read
    the same whether the hands are there or a foot to one side, so no band could
    express this. 21 reference samples run 0.004 to 0.327 torso-lengths sideways
    with nothing trimmed; the published ceiling sits above all of them.
    """
    entry = reference_for("set")
    band = (entry.get("shape_checks") or {}).get("contact.hands_off_center")
    assert band, (
        "set publishes no hands_off_center check; rebuild with "
        "tools/build_reference.py")
    ceiling = band["accepted_range"][1]
    assert band["max_kept"] <= ceiling, (
        f"the widest reference set ({band['max_kept']}) is past its own ceiling "
        f"({ceiling}), so a clip the calibration accepted would be flagged")

    # Hands a third of a torso to the left of the nose, on a body whose torso is
    # 0.25 tall: 0.0833/0.25 = 0.33, inside. Doubling the offset clears the ceiling.
    def with_offset(offset):
        """Hands offset from the NOSE, which sits away from the body centre here.

        The shoulders stay at 0.44/0.56 and the nose moves to 0.40, so a check
        reading the shoulder midpoint instead of the nose measures a different
        number. An earlier fixture put both at 0.5 and could not tell them apart.
        """
        frames = _set_frames()
        for frame in frames:
            points = frame["landmarks"]
            points[0] = _point(0.40, 0.22)
            points[15] = _point(0.40 + offset - 0.03, 0.25)
            points[16] = _point(0.40 + offset + 0.03, 0.25)
        return frames

    inside = evaluate_with_reference("set", with_offset(0.25 * 0.20))
    assert "set_hands_off_forehead" not in inside["issues"], (
        "hands 0.20 torso-lengths off centre -- inside the reference spread -- "
        "were flagged: {0}".format(inside["issues"]))

    outside = evaluate_with_reference("set", with_offset(0.25 * 0.90))
    assert "set_hands_off_forehead" in outside["issues"], (
        "hands 0.90 torso-lengths off centre -- nearly three times the widest "
        "reference set -- were not flagged: {0}".format(outside["issues"]))


def test_collapsed_hand_detection_is_not_judged_for_spacing():
    """One hand detected twice must not become "your hands are too close".

    MediaPipe reports both hands on the same visible hand with a gap of ~0.001,
    which is narrower than a wrist. Of the 6 reference set clips where both hands
    are detected at the judged frame, 4 read that way and every one of them is
    flagged setting_hand_spacing_bad -- two thirds of the clips the calibration
    treats as correct, told their hands are wrong.
    """
    collapsed = {"hands_detected": 2, "finger_extension": 1.2,
                 "hand_span": 0.07, "hand_center_gap": 0.0006,
                 "hands_level_gap": 0.0004}
    result = evaluate_with_reference("set", _set_frames(hands=collapsed))
    assert "setting_hand_spacing_bad" not in result["issues"], (
        "hands reported 0.0006 apart -- under 1% of a hand span, narrower than a "
        "wrist -- were judged for spacing: {0}".format(result["issues"]))

    # The control: a real pair at the same gap value must still be judged, so
    # the gate is reading the RATIO and not just rejecting small numbers.
    tiny_hands = {"hands_detected": 2, "finger_extension": 1.2,
                  "hand_span": 0.004, "hand_center_gap": 0.0006,
                  "hands_level_gap": 0.0004}
    judged = evaluate_with_reference("set", _set_frames(hands=tiny_hands))
    assert "setting_hand_spacing_bad" in judged["issues"], (
        "a genuinely narrow pair (gap 0.0006 against a 0.004 span) was skipped, "
        "so the gate is rejecting small gaps rather than collapsed pairs: "
        "{0}".format(judged["issues"]))


def test_receive_also_refuses_a_collapsed_hand_pair():
    """The gate has to cover both branches, not just set.

    receive reads the same pair for its platform checks. A collapse there is two
    detections stacked on one hand: the horizontal gap goes to nothing while the
    vertical one can be anything, and hands_level_gap > 0.08 then reports an
    unbalanced platform from a hand that was never separately seen.
    """
    collapsed = {"hands_detected": 2, "hand_span": 0.07,
                 "hand_center_gap": 0.0006, "hands_level_gap": 0.15}
    frames = [
        _frame(w, g, h, _base_angles(elbow=170, knee=130, shoulder=120),
               hands=collapsed)
        for w, g, h in zip([0.52, 0.50, 0.55, 0.54, 0.54, 0.57],
                           [0.26, 0.22, 0.18, 0.14, 0.02, 0.20],
                           [0.60, 0.62, 0.64, 0.66, 0.68, 0.65])
    ]
    result = evaluate_with_reference("receive", frames)
    assert "receive_platform_unbalanced" not in result["issues"], (
        "a platform was called unbalanced from two detections 0.0006 apart "
        "horizontally -- under 1% of a hand span: {0}".format(result["issues"]))

    # Control: the same level gap on a pair that really is two hands must still
    # be reported, or the gate has simply switched the check off.
    real = {"hands_detected": 2, "hand_span": 0.07,
            "hand_center_gap": 0.05, "hands_level_gap": 0.15}
    frames = [
        _frame(w, g, h, _base_angles(elbow=170, knee=130, shoulder=120), hands=real)
        for w, g, h in zip([0.52, 0.50, 0.55, 0.54, 0.54, 0.57],
                           [0.26, 0.22, 0.18, 0.14, 0.02, 0.20],
                           [0.60, 0.62, 0.64, 0.66, 0.68, 0.65])
    ]
    judged = evaluate_with_reference("receive", frames)
    assert "receive_platform_unbalanced" in judged["issues"], (
        "a genuinely uneven platform stopped being reported, so the gate turned "
        "the check off rather than protecting it: {0}".format(judged["issues"]))


def test_a_collapsed_pair_still_has_its_fingers_judged():
    """finger_extension describes ONE hand and survives the collapse.

    Gating it too would throw away a working check to fix a broken one.
    """
    collapsed = {"hands_detected": 2, "finger_extension": 0.9,
                 "hand_span": 0.07, "hand_center_gap": 0.0006,
                 "hands_level_gap": 0.0004}
    result = evaluate_with_reference("set", _set_frames(hands=collapsed))
    assert "setting_fingers_closed" in result["issues"], (
        "closed fingers went unreported because the hand PAIR was unusable, but "
        "finger extension is measured on one hand: {0}".format(result["issues"]))


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
    test_low_side_floors_stay_where_they_were_measured()
    test_the_block_load_elbow_floor_clears_its_reference()
    test_block_flags_arms_dropped_at_the_load()
    test_block_accepts_hands_held_at_the_load()
    test_a_joint_outside_the_frame_is_not_judged()
    test_set_flags_legs_that_never_bend()
    test_set_accepts_a_normally_bent_knee()
    test_set_flags_hands_beside_the_head()
    test_collapsed_hand_detection_is_not_judged_for_spacing()
    test_receive_also_refuses_a_collapsed_hand_pair()
    test_a_collapsed_pair_still_has_its_fingers_judged()
    print("phase reference ok")
    print("checked actions: receive, set, block, serve")


if __name__ == "__main__":
    main()
