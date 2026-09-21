"""Behaviour tests for the shared scanner gate.

The scanners decide which footage ever becomes a reference clip, so a wrong
answer here does not produce a visible bug -- it silently moves a band, and the
app then flags correct technique. These tests exist because the rules they cover
were each written after footage got through.
"""

import os
import sys
from types import SimpleNamespace

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from tools.dataset_clips.clip_quality import (
    SUBJECT_JUMP,
    TORSO_FLOOR,
    frame_is_usable,
    legs_offscreen,
    subject_runs,
    torso_length,
)


def _point(x=0.5, y=0.5, visibility=0.95):
    return SimpleNamespace(x=x, y=y, z=0.0, visibility=visibility)


def _pose(ankle_y=0.95, ankle_vis=0.95, knee_y=0.80, hip_y=0.61, hip_x=0.5):
    points = [_point() for _index in range(33)]
    points[11] = _point(0.40, 0.36)
    points[12] = _point(0.60, 0.36)
    points[23] = _point(hip_x - 0.06, hip_y)
    points[24] = _point(hip_x + 0.06, hip_y)
    points[25] = _point(0.46, knee_y)
    points[26] = _point(0.54, knee_y)
    points[27] = _point(0.46, ankle_y, ankle_vis)
    points[28] = _point(0.54, ankle_y, ankle_vis)
    return points


def test_legs_below_the_frame_are_refused_however_confident():
    """The failure the old visibility rule could not see.

    MediaPipe does not report "the legs are out of shot" -- it reports a
    confident position below the bottom edge. block_scan_events required
    visibility >= 0.6, which an invented leg clears easily.
    """
    assert legs_offscreen(_pose(ankle_y=1.25, ankle_vis=0.99)), (
        "ankles 0.25 below the frame at 99% confidence were accepted as seen")


def test_legs_clipped_by_a_sliver_are_still_usable():
    """And the gate must not become 'anything near the edge is unusable'.

    The strict version of this rule cut the block knee samples from 16 to 3,
    which is a demolition rather than a fix.
    """
    assert not legs_offscreen(_pose(ankle_y=1.03, ankle_vis=0.90)), (
        "ankles 0.03 past the edge at 0.90 confidence were refused")


def test_an_occluded_but_in_frame_leg_is_not_refused_for_confidence_alone():
    """A leg hidden behind the body sits mid-frame with low confidence.

    The old rule (visibility >= 0.5 or 0.6) threw these away. The two-tier gate
    only consults confidence for landmarks that are actually near an edge.
    """
    assert not legs_offscreen(_pose(ankle_y=0.85, ankle_vis=0.30)), (
        "an in-frame leg was refused because MediaPipe was unsure about it")


def test_one_off_screen_leg_is_enough_to_refuse():
    """Both sides must be checked, because the angle takes the extreme of them.

    get_angles computes knee = min(left, right). A single invented leg wins that
    minimum outright, so a gate watching one side would pass exactly the frame
    whose angle is about to be decided by the leg it did not look at.
    """
    for side, indices in (("左", (25, 27)), ("右", (26, 28))):
        points = _pose()
        for index in indices:
            points[index] = _point(0.5, 1.30, 0.99)
        assert legs_offscreen(points), (
            f"the {side} leg was 0.30 below the frame and the gate passed the "
            "frame, so knee = min(left, right) would be decided by a landmark "
            "no camera saw")


def test_a_player_too_far_away_is_refused():
    """The far-regime bound, which nothing in the old scanners had.

    MAX_NORM bounds the close-up regime where the torso denominator collapses.
    A 16-minute match recording produced torsos down to 0.008 of frame height --
    a few dozen pixels, where landmark noise rivals the angles being judged.
    """
    tiny = _pose()
    tiny[11] = _point(0.49, 0.50)
    tiny[12] = _point(0.51, 0.50)
    tiny[23] = _point(0.49, 0.52)
    tiny[24] = _point(0.51, 0.52)
    assert torso_length(tiny) < TORSO_FLOOR
    ok, reason = frame_is_usable(tiny)
    assert not ok and "torso" in reason, (
        "a player 0.02 torso-lengths tall was accepted: {0}".format(reason))


def test_a_normal_player_passes():
    """The floor must not reject ordinary footage.

    Measured: across the 209 reference samples that clear the off-screen gate,
    TORSO_FLOOR excludes exactly one.
    """
    ok, reason = frame_is_usable(_pose())
    assert ok, f"an ordinary full-body frame was refused: {reason}"


def test_tracking_that_moves_to_another_body_splits_the_run():
    """The check that had no equivalent anywhere.

    MediaPipe returns one pose and never says "nobody here". On a court with
    twelve players it simply picks one, and a video where it followed a bystander
    for its entire length passed every check the pipeline had.
    """
    here = [_pose(hip_x=0.30) for _index in range(10)]
    there = [_pose(hip_x=0.75) for _index in range(10)]
    runs = subject_runs(here + there)
    assert len(runs) == 2, (
        "the hip centre jumped 0.45 of the frame -- further than a body can "
        "travel between samples -- and the run was not split: {0}".format(
            [len(r) for r in runs]))
    assert [len(r) for r in runs] == [10, 10]


def test_ordinary_movement_does_not_split_the_run():
    """A player crossing the court must stay one run.

    A jump threshold small enough to split real movement would make every clip
    look like a subject switch and the check would be discarded as useless.
    """
    frames = [_pose(hip_x=0.30 + 0.04 * i) for i in range(10)]
    assert 0.04 < SUBJECT_JUMP
    runs = subject_runs(frames)
    assert len(runs) == 1, (
        "steady movement of 0.04 per frame was read as {0} different "
        "people".format(len(runs)))


def test_a_frame_with_no_pose_ends_the_run():
    """Losing the subject and reacquiring is a switch, not a continuation.

    Without this, a gap where MediaPipe found nobody would silently join a run
    that starts on one player and ends on another.
    """
    runs = subject_runs([_pose()] * 4 + [None] * 2 + [_pose()] * 4)
    assert len(runs) == 2, [len(r) for r in runs]
    assert [len(r) for r in runs] == [4, 4]


def test_runs_report_original_indices():
    """The scanner needs frame numbers to cut on, not positions within a run."""
    runs = subject_runs([_pose(hip_x=0.30)] * 3 + [_pose(hip_x=0.80)] * 3)
    assert [i for i, _f in runs[1]] == [3, 4, 5], (
        "indices are relative to the run, so any cut made from them lands in "
        "the wrong place: {0}".format([i for i, _f in runs[1]]))


def main():
    test_legs_below_the_frame_are_refused_however_confident()
    test_legs_clipped_by_a_sliver_are_still_usable()
    test_an_occluded_but_in_frame_leg_is_not_refused_for_confidence_alone()
    test_one_off_screen_leg_is_enough_to_refuse()
    test_a_player_too_far_away_is_refused()
    test_a_normal_player_passes()
    test_tracking_that_moves_to_another_body_splits_the_run()
    test_ordinary_movement_does_not_split_the_run()
    test_a_frame_with_no_pose_ends_the_run()
    test_runs_report_original_indices()
    print("clip quality ok")
    print("checked: off-screen gate, edge tolerance, occlusion, torso floor, "
          "subject continuity")


if __name__ == "__main__":
    main()
