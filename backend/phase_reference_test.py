import os
import sys
from types import SimpleNamespace

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.reference_evaluation import evaluate_with_reference


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
        _frame(0.54, 0.02, 0.68, _base_angles(elbow=130, knee=172, shoulder=82)),
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
        _frame(0.25, 0.04, 0.64, _base_angles(elbow=72, shoulder=84)),
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


def test_block_uses_max_reach_phase():
    frames = [
        _frame(0.42, 0.20, 0.60, _base_angles()),
        _frame(0.36, 0.18, 0.65, _base_angles(knee=170)),
        _frame(0.30, 0.14, 0.61, _base_angles()),
        _frame(0.20, 0.10, 0.55, _base_angles(elbow=145, shoulder=120)),
        _frame(0.28, 0.14, 0.58, _base_angles()),
        _frame(0.40, 0.18, 0.60, _base_angles()),
    ]

    result = evaluate_with_reference("block", frames)

    assert result["report"]["mode"] == "heuristic"
    assert result["contact_index"] == 3
    assert "elbow_not_straight" in result["issues"]
    assert "hands_not_high" in result["issues"]


def main():
    test_receive_uses_platform_phase()
    test_set_uses_release_phase()
    test_block_uses_max_reach_phase()
    print("phase reference ok")
    print("checked actions: receive, set, block")


if __name__ == "__main__":
    main()
