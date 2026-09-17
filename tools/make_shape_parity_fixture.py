"""Generate the fixture that pins the browser's shape maths to Python's.

local-analyzer.js re-implements get_shape_features and landmarks_offscreen,
because GitHub Pages has no backend and the browser is the app users actually
run. Text assertions can only show the two look alike. This fixture makes both
sides compute the same landmark sets and compare against the same numbers, so a
divergence in the arithmetic fails a test instead of quietly judging users by a
different rule than the one the bands were calibrated under.

Regenerate after any change to get_shape_features or landmarks_offscreen:

    .venv/Scripts/python.exe tools/make_shape_parity_fixture.py
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from angle.angle import SHAPE_LANDMARKS, get_shape_features, landmarks_offscreen

OUT_PATH = os.path.join(ROOT_DIR, "frontend", "shape_parity_fixture.json")


class Point:
    def __init__(self, x, y, visibility):
        self.x = x
        self.y = y
        self.z = 0.0
        self.visibility = visibility

    def as_dict(self):
        return {"x": self.x, "y": self.y, "z": 0.0, "visibility": self.visibility}


def _pose(hand_dy=0.0, hand_dx=0.06, hand_y=0.30, shoulder_dx=0.20,
          visibility=0.95, ankle_dx=0.14, lean=0.0, hand_shift=0.0,
          nose_x=0.5):
    """Shoulders at y=0.36 and hips at y=0.61, so an upright torso is 0.25.

    `lean` shifts the shoulders sideways over fixed hips, which is what makes
    torso a diagonal rather than a vertical drop -- without a leaning case the
    fixture cannot tell hypot from abs(dy), and a browser using either passes.
    """
    points = [Point(0.5, 0.5, visibility) for _index in range(33)]
    points[0] = Point(nose_x, 0.22, visibility)
    points[11] = Point(0.5 + lean - shoulder_dx / 2, 0.36, visibility)
    points[12] = Point(0.5 + lean + shoulder_dx / 2, 0.36, visibility)
    points[15] = Point(0.5 + hand_shift - hand_dx / 2, hand_y, visibility)
    points[16] = Point(0.5 + hand_shift + hand_dx / 2, hand_y + hand_dy, visibility)
    points[23] = Point(0.44, 0.61, visibility)
    points[24] = Point(0.56, 0.61, visibility)
    points[27] = Point(0.5 - ankle_dx / 2, 0.95, visibility)
    points[28] = Point(0.5 + ankle_dx / 2, 0.95, visibility)
    return points


# Each case names the property it exists to pin. The awkward ones matter most:
# a browser that agrees on the easy pose and disagrees on the edge of the frame
# still judges users by a different rule.
CASES = [
    ("typical", _pose()),
    ("one_hand_dropped", _pose(hand_dy=0.15)),
    ("hands_pressed_together", _pose(hand_dx=0.03)),
    ("hands_wide", _pose(hand_dx=0.30)),
    # A wrist a sliver past the bottom edge, still confident: judged.
    ("wrist_clipped_by_edge", _pose(hand_dy=0.15, hand_y=0.93)),
    # Both wrists well outside: refused however confident MediaPipe is.
    ("hands_offscreen", _pose(hand_dy=0.15, hand_y=1.18)),
    ("hands_offscreen_confident", _pose(hand_dy=0.15, hand_y=1.18, visibility=0.99)),
    # Clipped, and the model itself is unsure: refused.
    ("wrist_clipped_low_confidence", _pose(hand_dy=0.15, hand_y=0.93, visibility=0.2)),
    # Filmed edge-on. The shoulders project onto nearly one point, which is what
    # broke the first version of these features when it divided by that width.
    ("edge_on", _pose(shoulder_dx=0.01)),
    ("wrists_above_shoulders", _pose(hand_y=0.10)),
    # Exactly on the margin. Hands raised out of the top of the frame put a
    # wrist at y=-0.1, where `beyond` is 0.1 exactly -- the one input that tells
    # `> OFFSCREEN_MARGIN` apart from `>=`, and a real framing for every overhead
    # action. (The bottom edge cannot test this: 1.1 - 1.0 is not 0.1 in binary.)
    ("wrist_exactly_on_the_margin", _pose(hand_y=-0.10, hand_dy=0.30)),
    # Leaning forward, so the torso is a diagonal. Distinguishes a torso measured
    # as hypot(dx, dy) from one measured as the vertical drop alone.
    ("leaning_forward", _pose(lean=0.18, hand_dy=0.15)),
    ("leaning_and_edge_on", _pose(lean=0.18, shoulder_dx=0.01)),
    # Hands pushed to one side and then the other. Every earlier case put the
    # hand midpoint exactly on the nose, so hands_off_center was 0 in all of
    # them and dropping the abs() changed nothing -- the fixture could not see
    # a sign error. These two must produce the SAME value.
    ("hands_shifted_left", _pose(hand_shift=-0.09)),
    ("hands_shifted_right", _pose(hand_shift=0.09)),
    # And the nose away from the body centre, so a check reading the shoulder
    # midpoint instead of the nose reads a different number.
    ("head_turned_off_centre", _pose(nose_x=0.58, hand_shift=0.02)),
]


def main():
    cases = []
    for name, points in CASES:
        features = get_shape_features(points)
        cases.append({
            "name": name,
            "landmarks": [point.as_dict() for point in points],
            "features": {key: round(value, 9) for key, value in features.items()},
            "offscreen": {feature: landmarks_offscreen(points, indices)
                          for feature, indices in SHAPE_LANDMARKS.items()},
        })

    payload = {
        "note": ("Generated by tools/make_shape_parity_fixture.py. Both "
                 "backend/shape_check_test.py and frontend/"
                 "evaluation_parity_test.mjs assert against it."),
        "shape_landmarks": {key: list(value) for key, value in SHAPE_LANDMARKS.items()},
        "cases": cases,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
    print(f"written: {OUT_PATH}")
    print(f"{len(cases)} cases, {len(SHAPE_LANDMARKS)} features")


if __name__ == "__main__":
    main()
