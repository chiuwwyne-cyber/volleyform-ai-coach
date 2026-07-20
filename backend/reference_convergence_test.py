import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

REFERENCE_PATH = os.path.join(ROOT_DIR, "backend", "reference_standards.json")

EXPECTED_MIN_CLIPS = {
    "spike": 17,
    "serve": 14,
    "block": 6,
    "receive": 12,
    "set": 6,
}


def _reference():
    with open(REFERENCE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def test_dataset_counts_did_not_regress():
    actions = _reference()["actions"]
    for action, expected in EXPECTED_MIN_CLIPS.items():
        actual = actions[action]["clips"]
        assert actual >= expected, (action, actual, expected)


def test_bands_publish_tolerance_and_convergence():
    for action, entry in _reference()["actions"].items():
        for phase, joints in entry["phases"].items():
            for joint, band in joints.items():
                accepted = band.get("accepted_range")
                assert isinstance(accepted, list) and len(accepted) == 2
                assert 0 <= accepted[0] <= band["p10"], (action, phase, joint, band)
                assert band["p90"] <= accepted[1] <= 180, (action, phase, joint, band)
                assert 0 < band["tolerance"] <= 24.0, (action, phase, joint, band)
                assert band["convergence_state"] in {"usable", "stable"}
                assert 0.0 <= band["convergence"] <= 1.0


def test_small_reference_sets_stay_conservative():
    actions = _reference()["actions"]
    assert actions["set"]["phases"]["contact"]["elbow"]["convergence_state"] == "usable"
    assert actions["block"]["phases"]["crouch"]["knee"]["convergence_state"] == "usable"
    assert actions["set"]["phases"]["contact"]["elbow"]["tolerance"] >= 20.0
    assert actions["block"]["phases"]["crouch"]["knee"]["tolerance"] >= 20.0


def main():
    test_dataset_counts_did_not_regress()
    test_bands_publish_tolerance_and_convergence()
    test_small_reference_sets_stay_conservative()
    print("reference convergence ok")
    print("checked: clip counts, accepted ranges, adaptive tolerance, convergence states")


if __name__ == "__main__":
    main()
