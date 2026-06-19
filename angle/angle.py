import math


def _point3(point):
    return (
        float(point.x),
        float(point.y),
        float(getattr(point, "z", 0.0)),
    )


def _vector(a, b):
    return (
        a[0] - b[0],
        a[1] - b[1],
        a[2] - b[2],
    )


def _length(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def calculate_angle_3d(a, b, c):
    a = _point3(a)
    b = _point3(b)
    c = _point3(c)

    ba = _vector(a, b)
    bc = _vector(c, b)
    ba_len = _length(ba)
    bc_len = _length(bc)

    if ba_len == 0 or bc_len == 0:
        return 0.0

    cosine = (
        ba[0] * bc[0] +
        ba[1] * bc[1] +
        ba[2] * bc[2]
    ) / (ba_len * bc_len)
    cosine = max(-1.0, min(1.0, cosine))

    return round(math.degrees(math.acos(cosine)), 2)


def calculate_angle(a, b, c):
    return calculate_angle_3d(a, b, c)


def _best_landmarks(image_landmarks, world_landmarks=None):
    # MediaPipe world landmarks preserve body depth better than image x/y/z.
    return world_landmarks if world_landmarks is not None else image_landmarks


def get_angles(image_landmarks, world_landmarks=None):
    landmarks = _best_landmarks(image_landmarks, world_landmarks)
    angles = {}

    l_shoulder = landmarks[11]
    l_elbow = landmarks[13]
    l_wrist = landmarks[15]
    left_elbow = calculate_angle_3d(l_shoulder, l_elbow, l_wrist)

    r_shoulder = landmarks[12]
    r_elbow = landmarks[14]
    r_wrist = landmarks[16]
    right_elbow = calculate_angle_3d(r_shoulder, r_elbow, r_wrist)
    angles["elbow"] = max(left_elbow, right_elbow)

    l_hip = landmarks[23]
    l_knee = landmarks[25]
    l_ankle = landmarks[27]
    left_knee = calculate_angle_3d(l_hip, l_knee, l_ankle)

    r_hip = landmarks[24]
    r_knee = landmarks[26]
    r_ankle = landmarks[28]
    right_knee = calculate_angle_3d(r_hip, r_knee, r_ankle)
    angles["knee"] = min(left_knee, right_knee)

    left_shoulder = calculate_angle_3d(l_elbow, l_shoulder, l_hip)
    right_shoulder = calculate_angle_3d(r_elbow, r_shoulder, r_hip)
    angles["shoulder"] = max(left_shoulder, right_shoulder)

    shoulder_mid = (
        (l_shoulder.x + r_shoulder.x) / 2,
        (l_shoulder.y + r_shoulder.y) / 2,
        (getattr(l_shoulder, "z", 0.0) + getattr(r_shoulder, "z", 0.0)) / 2,
    )
    hip_mid = (
        (l_hip.x + r_hip.x) / 2,
        (l_hip.y + r_hip.y) / 2,
        (getattr(l_hip, "z", 0.0) + getattr(r_hip, "z", 0.0)) / 2,
    )
    torso_depth = abs(shoulder_mid[2] - hip_mid[2])
    angles["torso_depth"] = round(torso_depth, 4)
    angles["prediction_space"] = "3d" if world_landmarks is not None else "image_3d"

    return angles


def get_positions(image_landmarks, world_landmarks=None):
    landmarks = _best_landmarks(image_landmarks, world_landmarks)
    positions = {}

    wrist_y = min(landmarks[15].y, landmarks[16].y)
    head_y = landmarks[0].y
    wrist_z = min(
        getattr(landmarks[15], "z", 0.0),
        getattr(landmarks[16], "z", 0.0),
    )
    head_z = getattr(landmarks[0], "z", 0.0)

    positions["wrist_y"] = wrist_y
    positions["head_y"] = head_y
    positions["wrist_z"] = wrist_z
    positions["head_z"] = head_z
    positions["prediction_space"] = "3d" if world_landmarks is not None else "image_3d"

    return positions


def _distance2(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def _hand_span(hand):
    wrist = hand[0]
    tips = [hand[i] for i in (4, 8, 12, 16, 20)]
    return max(_distance2(wrist, tip) for tip in tips)


def _finger_extension_ratio(hand):
    # Ratio > 1 usually means fingers are open instead of curled into the palm.
    wrist = hand[0]
    ratios = []
    for tip_idx, pip_idx in ((8, 6), (12, 10), (16, 14), (20, 18)):
        tip_dist = _distance2(wrist, hand[tip_idx])
        pip_dist = _distance2(wrist, hand[pip_idx])
        if pip_dist > 0:
            ratios.append(tip_dist / pip_dist)
    if not ratios:
        return 0.0
    return sum(ratios) / len(ratios)


def get_hand_features(hand_landmarks):
    features = {
        "hands_detected": 0,
        "hand_span": 0.0,
        "finger_extension": 0.0,
        "hand_center_gap": None,
        "hands_level_gap": None,
    }

    if not hand_landmarks:
        return features

    hands = [hand for hand in (hand_landmarks.get("left"), hand_landmarks.get("right")) if hand]
    features["hands_detected"] = len(hands)
    if not hands:
        return features

    spans = [_hand_span(hand) for hand in hands]
    extensions = [_finger_extension_ratio(hand) for hand in hands]
    features["hand_span"] = round(sum(spans) / len(spans), 4)
    features["finger_extension"] = round(sum(extensions) / len(extensions), 3)

    if len(hands) == 2:
        left_wrist = hands[0][0]
        right_wrist = hands[1][0]
        features["hand_center_gap"] = round(abs(left_wrist.x - right_wrist.x), 4)
        features["hands_level_gap"] = round(abs(left_wrist.y - right_wrist.y), 4)

    return features
