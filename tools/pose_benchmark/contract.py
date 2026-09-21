"""What every pose backend in this benchmark must agree on.

The whole point of the comparison is that the numbers are commensurable, so the
contract is deliberately narrow: the 13 joints every model in the field emits,
in normalised image coordinates, measured on the identical decoded frame.

Two things are kept out on purpose:

* Depth. MediaPipe alone produces a world-space z; RTMPose, YOLO-Pose and
  ViTPose are 2D keypoint detectors. Comparing a 3D angle against a 2D one
  would be comparing two different quantities, so every angle here is the
  in-plane one and the depth question is reported separately.
* Anything MediaPipe-shaped. No 33-point indices, no `visibility` semantics.
  A contract written in the incumbent's vocabulary would make the incumbent
  win by construction.
"""

import math

# The intersection of BlazePose-33 and COCO-17. Face and foot detail differ
# between the two skeletons and none of VolleyForm's judgements use them.
COMMON_KEYPOINTS = (
    "nose",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
)

# BlazePose-33 -> contract.
BLAZEPOSE_INDEX = {
    "nose": 0,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
}

# COCO-17 -> contract. Shared by RTMPose, YOLO-Pose and ViTPose.
COCO_INDEX = {
    "nose": 0,
    "left_shoulder": 5, "right_shoulder": 6,
    "left_elbow": 7, "right_elbow": 8,
    "left_wrist": 9, "right_wrist": 10,
    "left_hip": 11, "right_hip": 12,
    "left_knee": 13, "right_knee": 14,
    "left_ankle": 15, "right_ankle": 16,
}

# The joints VolleyForm actually judges on, as (a, vertex, c) triples.
ANGLES = {
    "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_shoulder": ("left_elbow", "left_shoulder", "left_hip"),
    "right_shoulder": ("right_elbow", "right_shoulder", "right_hip"),
    "left_knee": ("left_hip", "left_knee", "left_ankle"),
    "right_knee": ("right_hip", "right_knee", "right_ankle"),
    "left_hip": ("left_shoulder", "left_hip", "left_knee"),
    "right_hip": ("right_shoulder", "right_hip", "right_knee"),
}

# Every frame is resized to this width before it reaches any backend, so that
# "which model is faster" is not secretly "which clip was 4K".
BENCH_WIDTH = 960

# Below this, a backend is treated as not having found the joint at all.
SCORE_FLOOR = 0.30


def angle_2d(a, b, c):
    """In-plane angle at vertex b, in degrees, or None if a point is missing."""
    if a is None or b is None or c is None:
        return None
    bax, bay = a[0] - b[0], a[1] - b[1]
    bcx, bcy = c[0] - b[0], c[1] - b[1]
    ba_len = math.hypot(bax, bay)
    bc_len = math.hypot(bcx, bcy)
    if ba_len == 0 or bc_len == 0:
        return None
    cosine = (bax * bcx + bay * bcy) / (ba_len * bc_len)
    cosine = max(-1.0, min(1.0, cosine))
    return round(math.degrees(math.acos(cosine)), 2)


def frame_angles(keypoints, score_floor=SCORE_FLOOR):
    """Angles for one frame's keypoint dict, skipping any joint below floor."""
    def pt(name):
        kp = keypoints.get(name)
        if kp is None or kp[2] < score_floor:
            return None
        return (kp[0], kp[1])

    out = {}
    for name, (a, b, c) in ANGLES.items():
        out[name] = angle_2d(pt(a), pt(b), pt(c))
    return out
