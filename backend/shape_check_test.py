"""Behaviour tests for the shape checks -- the relationships BETWEEN limbs.

The angle bands read elbow, shoulder and knee one joint at a time. Three block
segments a technique video labels wrong on screen cleared every one of those
bands, because the faults were in how the two hands related to each other and
nothing was watching that. These checks are what watch it, and the test that
matters most here is the off-screen one: MediaPipe reports invented hands with
high confidence, and the gap between two invented hands looks exactly like a
real one.
"""

import json
import os
import sys
from types import SimpleNamespace

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from angle.angle import SHAPE_LANDMARKS, get_shape_features, landmarks_offscreen
from backend.reference_evaluation import _evaluate_shape_checks

# Shoulders at y=0.36 and hips at y=0.61 in every fixture, both centred, so the
# torso length each feature divides by is exactly 0.25 and a raw gap of 0.10
# reads as 0.40. Stated once here because every expected number below comes from
# it. The denominator is torso rather than shoulder width because shoulder width
# collapses when a player is filmed edge-on -- see get_shape_features.
TORSO = 0.25


def _point(x=0.5, y=0.5, visibility=0.95):
    return SimpleNamespace(x=x, y=y, z=0.0, visibility=visibility)


def _landmarks(hand_dy=0.0, hand_dx=0.06, hand_y=0.30, visibility=0.95):
    points = [_point(visibility=visibility) for _index in range(33)]
    points[0] = _point(0.5, 0.22, visibility)
    points[11] = _point(0.40, 0.36, visibility)
    points[12] = _point(0.60, 0.36, visibility)
    points[15] = _point(0.5 - hand_dx / 2, hand_y, visibility)
    points[16] = _point(0.5 + hand_dx / 2, hand_y + hand_dy, visibility)
    points[23] = _point(0.44, 0.61, visibility)
    points[24] = _point(0.56, 0.61, visibility)
    points[27] = _point(0.43, 0.95, visibility)
    points[28] = _point(0.57, 0.95, visibility)
    return points


def _entry(**bands):
    return {"shape_checks": {key.replace("__", "."): spec
                             for key, spec in bands.items()}}


# Invented issue codes, not real ones. SHAPE_CHECKS currently publishes nothing
# -- the two block hand checks were taken back out for lack of evidence -- and
# the machinery still has to be tested and still has to work when the first
# validated check arrives. Binding these fixtures to whichever codes happen to be
# live would make the tests vanish exactly when there is nothing to catch them.
LEVEL_BAND = {"accepted_range": [None, 0.40], "p10": 0.01, "p90": 0.12,
              "code": "fixture_high_side", "side": "high"}
GAP_BAND = {"accepted_range": [0.20, 1.30], "p10": 0.29, "p90": 0.95,
            "code": "fixture_both_sides", "side": "both"}


def _run(landmarks, entry):
    frames = [{"landmarks": landmarks, "angles": {}, "positions": {}}]
    issues = []
    report = {"phases": {}}
    _evaluate_shape_checks(entry, frames, {"contact": 0}, issues, {}, report)
    return issues, report


def test_a_hand_dropped_below_the_other_is_flagged():
    # 0.15 of frame height over a 0.25 torso == 0.60, past the 0.40 ceiling.
    issues, report = _run(_landmarks(hand_dy=0.15),
                          _entry(contact__hand_level_gap=LEVEL_BAND))
    assert "fixture_high_side" in issues, (
        "one hand 0.60 torso-lengths below the other cleared a ceiling of 0.40, "
        "so the check is not reading the measurement: {0}".format(issues))
    assert report["phases"]["contact"]["shape"]["hand_level_gap"]["status"] == "red"


def test_level_hands_are_left_alone():
    issues, report = _run(_landmarks(hand_dy=0.01),
                          _entry(contact__hand_level_gap=LEVEL_BAND))
    assert not issues, (
        "hands 0.04 torso-lengths apart in height -- well inside the p10-p90 of "
        "0.01-0.12 -- were flagged: {0}".format(issues))
    shape = report["phases"]["contact"]["shape"]["hand_level_gap"]
    assert shape["status"] == "green"
    assert shape["value"] == 0.04, (
        "the report must carry the number even when it passes, otherwise the "
        "check cannot be audited against footage later: {0}".format(shape))


def test_both_sided_band_fires_on_the_low_end_too():
    # Hands 0.03 apart over a 0.25 torso == 0.12, under the 0.20 floor.
    issues, _report = _run(_landmarks(hand_dx=0.03),
                           _entry(contact__hand_gap=GAP_BAND))
    assert "fixture_both_sides" in issues, (
        "hands pressed to 0.12 torso-lengths apart cleared a floor of 0.20, so "
        "the low side of a two-sided band is not checked: {0}".format(issues))


def test_offscreen_hands_are_never_judged():
    """The whole reason the gate exists.

    MediaPipe does not report that it cannot see the hands -- it reports a
    confident position below the frame edge. A block filmed tight on the upper
    body puts both wrists off the bottom, and the invented gap between them is
    as plausible-looking as a real one. Judging it invents an error out of
    nothing.
    """
    issues, report = _run(_landmarks(hand_dy=0.15, hand_y=1.18),
                          _entry(contact__hand_level_gap=LEVEL_BAND))
    assert not issues, (
        "hands placed at y=1.18 and 1.33 -- both off the bottom of the frame -- "
        "were judged and flagged. That is the app telling a user their "
        "technique is wrong from a position no camera saw: {0}".format(issues))
    assert "shape" not in report["phases"].get("contact", {}), (
        "an unjudgeable frame still produced a shape report, which would show a "
        "measured-looking number for a hand that was never in shot")


def test_high_confidence_does_not_rescue_an_offscreen_hand():
    """Confidence 0.99 on a landmark 0.18 outside the frame is still a guess."""
    issues, _report = _run(_landmarks(hand_dy=0.15, hand_y=1.18, visibility=0.99),
                           _entry(contact__hand_level_gap=LEVEL_BAND))
    assert not issues, (
        "a hand 0.18 beyond the frame edge was accepted because MediaPipe said "
        "it was 99% sure. A confident hallucination is still a hallucination, "
        "which is the pexels_6217341 failure: {0}".format(issues))


def test_a_hand_just_clipped_by_the_edge_is_still_judged():
    """The gate must not become "anything near the edge is unusable".

    A wrist at y=1.08 with good confidence is cropped by a sliver and its
    position is still worth something. The strict version of this rule cut the
    block knee samples from 16 to 3, which is not a fix but a demolition.

    The upper hand sits at 0.93 and the lower at 1.08, so only one of the two is
    clipped -- 0.15 apart over a 0.25 torso is 0.60, past the ceiling.
    """
    issues, report = _run(_landmarks(hand_dy=0.15, hand_y=0.93),
                          _entry(contact__hand_level_gap=LEVEL_BAND))
    assert "fixture_high_side" in issues, (
        "a clearly uneven pair of hands was waved through because the lower "
        "wrist sat 0.08 past the frame edge at 0.95 confidence: {0}".format(issues))
    assert report["phases"]["contact"]["shape"]["hand_level_gap"]["status"] == "red"


def test_every_measurable_feature_declares_its_landmarks():
    """SHAPE_LANDMARKS must cover everything get_shape_features can produce.

    That table is what tells the off-screen gate which points to inspect. Adding
    a sixth feature to angle.py and forgetting this table is the one realistic
    way a check reaches users with no gate in front of it, and nothing else
    would notice -- the feature would work, and only be wrong when the limb was
    out of shot.
    """
    measurable = set(get_shape_features(_landmarks()))
    declared = set(SHAPE_LANDMARKS)
    assert measurable <= declared, (
        "get_shape_features produces {0}, which SHAPE_LANDMARKS does not "
        "declare, so the off-screen gate has nothing to check for it".format(
            sorted(measurable - declared)))
    assert declared <= measurable, (
        "SHAPE_LANDMARKS declares {0}, which get_shape_features never "
        "produces -- a stale entry hides the drift this test looks "
        "for".format(sorted(declared - measurable)))


def test_a_feature_with_no_declared_landmarks_is_refused():
    """And if that drift ever happens, the check must refuse, not judge.

    Simulated by removing the entry the way forgetting it would, because the
    static test above cannot show what the evaluator then does.
    """
    removed = SHAPE_LANDMARKS.pop("hand_level_gap")
    try:
        issues, report = _run(_landmarks(hand_dy=0.15),
                              _entry(contact__hand_level_gap=LEVEL_BAND))
    finally:
        SHAPE_LANDMARKS["hand_level_gap"] = removed
    assert not issues, (
        "a feature missing from SHAPE_LANDMARKS was judged with no off-screen "
        "gate in front of it: {0}".format(issues))
    assert not report["phases"], (
        "an undeclared feature still produced a shape report")


def test_an_entry_without_shape_checks_does_nothing():
    """Actions whose shape bands have not been measured stay untouched."""
    for entry in ({}, {"shape_checks": {}}, {"shape_checks": None}, None):
        issues, report = _run(_landmarks(hand_dy=0.15), entry)
        assert not issues and not report["phases"], (
            "an action with no measured shape bands produced output from "
            "entry={0}: {1}".format(entry, issues))


def test_a_missing_phase_is_skipped_not_guessed():
    frames = [{"landmarks": _landmarks(hand_dy=0.15), "angles": {}, "positions": {}}]
    issues = []
    report = {"phases": {}}
    _evaluate_shape_checks(_entry(crouch__hand_level_gap=LEVEL_BAND),
                           frames, {"contact": 0}, issues, {}, report)
    assert not issues, (
        "a check written for a phase the segmenter never found was evaluated "
        "against some other frame: {0}".format(issues))


def test_python_reproduces_the_parity_fixture():
    """The fixture the browser is held to must still describe this code.

    frontend/evaluation_parity_test.mjs runs the real local-analyzer.js against
    the same file. Pinning both sides to one set of numbers is what makes it a
    parity check rather than two implementations tested apart -- and this half
    is what stops the fixture being regenerated to match a bug.
    """
    path = os.path.join(ROOT_DIR, "frontend", "shape_parity_fixture.json")
    with open(path, encoding="utf-8") as handle:
        fixture = json.load(handle)

    assert {k: tuple(v) for k, v in fixture["shape_landmarks"].items()} == SHAPE_LANDMARKS, (
        "the fixture was generated from a different SHAPE_LANDMARKS; rerun "
        "tools/make_shape_parity_fixture.py")

    for case in fixture["cases"]:
        points = [SimpleNamespace(**point) for point in case["landmarks"]]
        measured = {key: round(value, 9)
                    for key, value in get_shape_features(points).items()}
        assert measured == case["features"], (
            "case {0}: get_shape_features now returns {1}, the fixture says "
            "{2}. If the change is intended, rerun "
            "tools/make_shape_parity_fixture.py and check the browser "
            "test still passes.".format(case["name"], measured, case["features"]))
        for feature, indices in SHAPE_LANDMARKS.items():
            assert landmarks_offscreen(points, indices) == case["offscreen"][feature], (
                "case {0}: the off-screen gate changed its mind about "
                "{1}".format(case["name"], feature))


def main():
    test_a_hand_dropped_below_the_other_is_flagged()
    test_level_hands_are_left_alone()
    test_both_sided_band_fires_on_the_low_end_too()
    test_offscreen_hands_are_never_judged()
    test_high_confidence_does_not_rescue_an_offscreen_hand()
    test_a_hand_just_clipped_by_the_edge_is_still_judged()
    test_every_measurable_feature_declares_its_landmarks()
    test_python_reproduces_the_parity_fixture()
    test_a_feature_with_no_declared_landmarks_is_refused()
    test_an_entry_without_shape_checks_does_nothing()
    test_a_missing_phase_is_skipped_not_guessed()
    print("shape check ok")
    print("checked: ceiling, floor, offscreen gate, edge tolerance, "
          "undeclared feature, no-op entry, cross-language fixture")


if __name__ == "__main__":
    main()
