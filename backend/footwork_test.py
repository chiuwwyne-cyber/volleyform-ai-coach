import json
import os
import sys
from types import SimpleNamespace

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.footwork import (  # noqa: E402
    count_approach_steps,
    sample_from_landmarks,
    L_ANKLE,
    R_ANKLE,
)

FIXTURE = os.path.join(ROOT_DIR, "frontend", "footwork_parity_fixture.json")


def _load_fixture():
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_matches_parity_fixture():
    # The fixture is generated FROM this backend function, so it must reproduce it
    # exactly. The frontend mirror is held to the same file, keeping both engines
    # in numeric lockstep.
    for case in _load_fixture()["cases"]:
        got = count_approach_steps(case["samples"])
        assert got == case["expected"], f"{case['name']}: {got} != {case['expected']}"


def test_clean_two_step_counts_four_contacts():
    fixture = {c["name"]: c for c in _load_fixture()["cases"]}
    dense = count_approach_steps(fixture["clean_two_step_dense"]["samples"])
    assert dense["steps"] == 4 and dense["left"] == 2 and dense["right"] == 2
    assert dense["reliable"] is True


def test_sparse_sampling_is_flagged_unreliable():
    # The honesty gate: a real approach sampled too coarsely must not be presented
    # as a trustworthy count, even if the number happens to land right.
    fixture = {c["name"]: c for c in _load_fixture()["cases"]}
    sparse = count_approach_steps(fixture["clean_two_step_sparse"]["samples"])
    assert sparse["reliable"] is False
    assert sparse["cadence_per_s"] is None


def test_standing_still_reports_no_steps():
    fixture = {c["name"]: c for c in _load_fixture()["cases"]}
    still = count_approach_steps(fixture["standing_still"]["samples"])
    assert still["available"] is True and still["steps"] == 0


def test_no_pose_is_unavailable_not_zero():
    # No skeleton must read "unavailable", never a confident "0 steps".
    result = count_approach_steps([])
    assert result["available"] is False and result["steps"] is None


def test_never_emits_a_judgment_field():
    # Footwork is descriptive only. Guard against a future change sneaking an
    # issue/severity/status into the output, which would imply a pass/fail the
    # data cannot support.
    result = count_approach_steps(
        _load_fixture()["cases"][0]["samples"]
    )
    for banned in ("issue", "issue_code", "status", "severity", "error"):
        assert banned not in result


def test_sample_from_landmarks_drops_offscreen_ankle():
    # A low-visibility or off-bottom ankle must become None, not a fake contact.
    lm = [SimpleNamespace(x=0.5, y=0.5, visibility=0.9) for _ in range(33)]
    lm[L_ANKLE] = SimpleNamespace(x=0.5, y=0.999, visibility=0.9)   # off bottom edge
    lm[R_ANKLE] = SimpleNamespace(x=0.5, y=0.8, visibility=0.1)     # invisible
    sample = sample_from_landmarks(lm, 0.4)
    assert sample["la"] is None and sample["ra"] is None


def main():
    test_matches_parity_fixture()
    test_clean_two_step_counts_four_contacts()
    test_sparse_sampling_is_flagged_unreliable()
    test_standing_still_reports_no_steps()
    test_no_pose_is_unavailable_not_zero()
    test_never_emits_a_judgment_field()
    test_sample_from_landmarks_drops_offscreen_ankle()
    print("footwork ok")
    print("checked: parity fixture, 2-step count, sparse gate, standing, no-pose, descriptive-only, offscreen ankle")


if __name__ == "__main__":
    main()
