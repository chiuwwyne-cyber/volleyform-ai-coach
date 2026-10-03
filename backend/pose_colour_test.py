import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from angle.pose_correction import (  # noqa: E402
    JOINT_CHAIN,
    JOINT_SPECS,
    LEFT,
    RIGHT,
    _angle_between,
    build_pose_compare,
)
from backend.analyzer import _pose_compare  # noqa: E402

FIXTURE = os.path.join(ROOT_DIR, "frontend", "pose_colour_fixture.json")
ALL_GREEN = {"elbow": "green", "knee": "green", "shoulder": "green", "wrist": "green"}


def _fixture():
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data["action"], [{"landmarks": data["landmarks"]}]


def _legacy_violations(action, points):
    hits = []
    for joint, spec in JOINT_SPECS.get(action, {}).items():
        names = JOINT_CHAIN[joint][0]
        for side in (LEFT, RIGHT):
            angle = _angle_between(*(points[side[name]] for name in names))
            if angle < spec.get("min", -1) or angle > spec.get("max", 999):
                hits.append(joint)
    return hits


def test_fixture_is_a_frame_the_legacy_rule_would_colour():
    # Otherwise the tests below could pass on a frame no rule would ever flag.
    action, sequence = _fixture()
    assert _legacy_violations(action, sequence[0]["landmarks"]), (
        "the fixture no longer violates JOINT_SPECS, so it cannot catch a return "
        "to colouring joints from them"
    )


def test_clean_report_paints_nothing():
    # A non-hitting arm hangs below JOINT_SPECS' shoulder minimum on every serve.
    action, sequence = _fixture()
    pose_compare = _pose_compare(action, None, [], sequence)
    assert pose_compare["available"]
    assert pose_compare["joint_status"] == ALL_GREEN, pose_compare["joint_status"]


def test_colours_follow_the_report_exactly():
    action, sequence = _fixture()
    status = _pose_compare(action, None, ["knee_too_bent"], sequence)["joint_status"]
    assert status == {**ALL_GREEN, "knee": "red"}, status


def test_pose_data_does_not_decide_colours():
    action, sequence = _fixture()
    pose_compare = build_pose_compare(action, None, sequence)
    assert pose_compare["available"]
    assert "joint_status" not in pose_compare


def main():
    test_fixture_is_a_frame_the_legacy_rule_would_colour()
    test_clean_report_paints_nothing()
    test_colours_follow_the_report_exactly()
    test_pose_data_does_not_decide_colours()
    print("pose colour ok")
    print("checked: fixture violates legacy specs, clean report all green, colours == report, pose data colour-free")


if __name__ == "__main__":
    main()
