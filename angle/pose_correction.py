import math

LEFT = {
    "shoulder": 11, "elbow": 13, "wrist": 15,
    "pinky": 17, "index": 19, "thumb": 21,
    "hip": 23, "knee": 25, "ankle": 27,
    "heel": 29, "foot_index": 31,
}
RIGHT = {
    "shoulder": 12, "elbow": 14, "wrist": 16,
    "pinky": 18, "index": 20, "thumb": 22,
    "hip": 24, "knee": 26, "ankle": 28,
    "heel": 30, "foot_index": 32,
}

# Mirrors the per-action angle thresholds already used in action/*.py.
JOINT_SPECS = {
    "spike": {
        "elbow": {"min": 150, "code": "elbow_bad"},
        "knee": {"min": 150, "code": "knee_bad"},
    },
    "block": {
        "elbow": {"min": 165, "code": "elbow_not_straight"},
        "shoulder": {"min": 150, "code": "hands_not_high"},
        "knee": {"min": 140, "code": "knee_too_bent"},
    },
    "serve": {
        "elbow": {"min": 150, "code": "elbow_bad"},
        "shoulder": {"min": 140, "code": "shoulder_low"},
        "knee": {"min": 150, "code": "knee_bad"},
    },
    "receive": {
        "elbow": {"min": 160, "code": "elbow_bad"},
        "knee": {"min": 140, "code": "knee_too_bent"},
    },
    "set": {
        "elbow": {"min": 140, "max": 175, "code": "elbow_position_bad"},
        "shoulder": {"min": 140, "code": "shoulder_low"},
    },
}

# triplet (A, pivot, C) plus every point that should be carried along when the
# pivot's angle is rotated to a corrected value.
JOINT_CHAIN = {
    "elbow": (("shoulder", "elbow", "wrist"), ("wrist", "pinky", "index", "thumb")),
    "knee": (("hip", "knee", "ankle"), ("ankle", "heel", "foot_index")),
    "shoulder": (("elbow", "shoulder", "hip"), ("elbow", "wrist", "pinky", "index", "thumb")),
}

# Mirrors the relevant severities from backend/feedback.py without importing
# that module (angle/ stays independent of backend/).
_ISSUE_SEVERITY = {
    "elbow_bad": "medium",
    "elbow_not_straight": "medium",
    "hands_not_high": "medium",
    "shoulder_low": "medium",
    "knee_bad": "medium",
    "knee_too_bent": "high",
    "elbow_position_bad": "medium",
    "wrist_low": "medium",
}
_SEVERITY_TO_STATUS = {"high": "red", "medium": "yellow", "low": "yellow"}
_STATUS_RANK = {"green": 0, "yellow": 1, "red": 2}

WRIST_MARGIN = 0.05


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    length = math.sqrt(_dot(a, a))
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def _angle_between(a, b, c):
    ba = _sub(a, b)
    bc = _sub(c, b)
    la = math.sqrt(_dot(ba, ba))
    lc = math.sqrt(_dot(bc, bc))
    if la == 0 or lc == 0:
        return 0.0
    cosine = max(-1.0, min(1.0, _dot(ba, bc) / (la * lc)))
    return math.degrees(math.acos(cosine))


def _rotate_point(point, pivot, axis, angle_deg):
    angle = math.radians(angle_deg)
    p = _sub(point, pivot)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    dot = _dot(p, axis)
    cross = _cross(axis, p)
    rotated = (
        p[0] * cos_a + cross[0] * sin_a + axis[0] * dot * (1 - cos_a),
        p[1] * cos_a + cross[1] * sin_a + axis[1] * dot * (1 - cos_a),
        p[2] * cos_a + cross[2] * sin_a + axis[2] * dot * (1 - cos_a),
    )
    return _add(rotated, pivot)


def _target_angle(current, spec):
    min_a = spec.get("min")
    max_a = spec.get("max")
    if min_a is not None and current < min_a:
        return min_a
    if max_a is not None and current > max_a:
        return max_a
    return None


def _correct_joint(points, side_map, joint_name, target_angle):
    names, distal_names = JOINT_CHAIN[joint_name]
    a_idx, b_idx, c_idx = (side_map[name] for name in names)
    a = points[a_idx]
    b = points[b_idx]
    c = points[c_idx]
    current = _angle_between(a, b, c)

    ba = _norm(_sub(a, b))
    bc = _norm(_sub(c, b))
    axis = _cross(ba, bc)
    axis_len = math.sqrt(_dot(axis, axis))
    if axis_len < 1e-6:
        axis = _cross(ba, (0.0, 1.0, 0.0))
        axis_len = math.sqrt(_dot(axis, axis))
        if axis_len < 1e-6:
            axis = (1.0, 0.0, 0.0)
            axis_len = 1.0
    axis = (axis[0] / axis_len, axis[1] / axis_len, axis[2] / axis_len)

    # The triplet endpoint that actually moves depends on which one is in the
    # distal set (e.g. shoulder correction moves the elbow side, not the hip).
    distal_indices = [side_map[name] for name in distal_names]
    moving_is_c = c_idx in distal_indices
    probe_point = c if moving_is_c else a

    delta = target_angle - current

    def _resulting_angle(applied_delta):
        test_point = _rotate_point(probe_point, b, axis, applied_delta)
        if moving_is_c:
            return _angle_between(a, b, test_point)
        return _angle_between(test_point, b, c)

    if abs(_resulting_angle(-delta) - target_angle) < abs(_resulting_angle(delta) - target_angle):
        delta = -delta

    for idx in distal_indices:
        points[idx] = list(_rotate_point(tuple(points[idx]), tuple(b), axis, delta))


def _correct_wrist_low(points):
    head_y = points[0][1]
    l_wrist_y = points[LEFT["wrist"]][1]
    r_wrist_y = points[RIGHT["wrist"]][1]
    wrist_y = min(l_wrist_y, r_wrist_y)
    if wrist_y <= head_y:
        return False

    delta = (head_y - WRIST_MARGIN) - wrist_y
    for idx in (
        LEFT["wrist"], RIGHT["wrist"],
        LEFT["pinky"], RIGHT["pinky"],
        LEFT["index"], RIGHT["index"],
        LEFT["thumb"], RIGHT["thumb"],
    ):
        x, y, z = points[idx]
        points[idx] = [x, y + delta, z]
    return True


def build_pose_compare(action_type, world_landmarks, issue_codes=None, actual_sequence=None):
    actual_sequence = actual_sequence or []
    if (not world_landmarks or len(world_landmarks) < 33) and not actual_sequence:
        return {"available": False}

    if world_landmarks and len(world_landmarks) >= 33:
        actual = [
            [float(point.x), float(point.y), float(getattr(point, "z", 0.0))]
            for point in world_landmarks
        ]
    else:
        actual = actual_sequence[0]["landmarks"]
    corrected = [list(point) for point in actual]

    spec = JOINT_SPECS.get(action_type, {})
    joint_status = {}

    for joint_name in ("elbow", "knee", "shoulder"):
        joint_spec = spec.get(joint_name)
        status = "green"
        if joint_spec:
            names, _distal = JOINT_CHAIN[joint_name]
            for side_map in (LEFT, RIGHT):
                a = corrected[side_map[names[0]]]
                b = corrected[side_map[names[1]]]
                c = corrected[side_map[names[2]]]
                current = _angle_between(a, b, c)
                target = _target_angle(current, joint_spec)
                if target is not None:
                    _correct_joint(corrected, side_map, joint_name, target)
                    side_status = _SEVERITY_TO_STATUS.get(
                        _ISSUE_SEVERITY.get(joint_spec["code"], "medium"), "yellow"
                    )
                    if _STATUS_RANK[side_status] > _STATUS_RANK[status]:
                        status = side_status
        joint_status[joint_name] = status

    wrist_status = "green"
    if action_type == "set" and _correct_wrist_low(corrected):
        wrist_status = _SEVERITY_TO_STATUS.get(_ISSUE_SEVERITY.get("wrist_low", "medium"), "yellow")
    joint_status["wrist"] = wrist_status

    return {
        "available": True,
        "joint_status": joint_status,
        "actual_landmarks": actual,
        "corrected_landmarks": corrected,
        "actual_sequence": actual_sequence,
    }
