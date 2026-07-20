"""Split an action clip into key moments so each phase can use its own standard.

Trajectory uses image landmarks (normalized, y grows downward): MediaPipe world
landmarks are hip-centered, so whole-body motion such as a jump disappears in
world space.
"""

OVERHEAD_ACTIONS = ("spike", "serve", "block")
SUPPORTED_ACTIONS = ("spike", "serve", "block", "receive", "set")

MIN_FRAMES = 6
SMOOTH_WINDOW = 3


def _smooth(values, window=SMOOTH_WINDOW):
    if len(values) < window:
        return list(values)
    half = window // 2
    smoothed = []
    for i in range(len(values)):
        lo = max(0, i - half)
        hi = min(len(values), i + half + 1)
        smoothed.append(sum(values[lo:hi]) / (hi - lo))
    return smoothed


def _wrist_y(landmarks):
    return min(landmarks[15].y, landmarks[16].y)


def _avg_wrist_y(landmarks):
    return (landmarks[15].y + landmarks[16].y) / 2


def _wrist_gap(landmarks):
    return abs(landmarks[15].x - landmarks[16].x)


def _wrist_level_gap(landmarks):
    return abs(landmarks[15].y - landmarks[16].y)


def _nose_y(landmarks):
    return landmarks[0].y


def _shoulder_y(landmarks):
    return (landmarks[11].y + landmarks[12].y) / 2


def _hip_y(landmarks):
    return (landmarks[23].y + landmarks[24].y) / 2


def _crouch_before(frame_landmarks, contact_index):
    if contact_index <= 0:
        return None
    hip_ys = _smooth([_hip_y(points) for points in frame_landmarks])
    before = range(contact_index)
    crouch = max(before, key=lambda i: hip_ys[i])
    # A flat lead-in (no real dip before the action) is not a loading phase.
    if hip_ys[crouch] - min(hip_ys[: contact_index + 1]) < 0.02:
        return None
    return crouch


def _crouch_near(frame_landmarks, contact_index, radius=4):
    hip_ys = _smooth([_hip_y(points) for points in frame_landmarks])
    start = max(0, contact_index - radius)
    stop = min(len(frame_landmarks), contact_index + radius + 1)
    if start >= stop:
        return None
    return max(range(start, stop), key=lambda i: hip_ys[i])


def _segment_overhead(frame_landmarks):
    wrist_ys = _smooth([_wrist_y(points) for points in frame_landmarks])
    contact = min(range(len(wrist_ys)), key=lambda i: wrist_ys[i])
    return {"crouch": _crouch_before(frame_landmarks, contact), "contact": contact}


def _segment_set(frame_landmarks):
    scores = []
    for points in frame_landmarks:
        wrist_y = _avg_wrist_y(points)
        target_y = _nose_y(points) + 0.03
        overhead_penalty = 0.0 if wrist_y < _shoulder_y(points) else 0.35
        scores.append(
            abs(wrist_y - target_y)
            + _wrist_gap(points) * 1.2
            + _wrist_level_gap(points)
            + overhead_penalty
        )
    contact = min(range(len(scores)), key=lambda i: scores[i])
    return {"crouch": _crouch_near(frame_landmarks, contact), "contact": contact}


def _segment_receive(frame_landmarks):
    scores = []
    for points in frame_landmarks:
        wrist_y = _avg_wrist_y(points)
        shoulder_y = _shoulder_y(points)
        target_y = shoulder_y + 0.18
        low_platform_penalty = 0.0 if wrist_y > shoulder_y else 0.35
        scores.append(
            abs(wrist_y - target_y)
            + _wrist_gap(points) * 1.8
            + _wrist_level_gap(points) * 1.2
            + low_platform_penalty
        )
    contact = min(range(len(scores)), key=lambda i: scores[i])
    return {"crouch": _crouch_near(frame_landmarks, contact), "contact": contact}


def segment_action(action_type, frame_landmarks):
    """Return key phase indexes for the requested volleyball action.

    frame_landmarks: list of per-frame image-landmark sequences (33 points).
    The returned contact index means the action's main ball-contact moment:
    attack/serve/block reach, setting release, or receive platform.
    """
    if action_type not in SUPPORTED_ACTIONS:
        return None
    if not frame_landmarks or len(frame_landmarks) < MIN_FRAMES:
        return None

    if action_type in OVERHEAD_ACTIONS:
        return _segment_overhead(frame_landmarks)
    if action_type == "set":
        return _segment_set(frame_landmarks)
    if action_type == "receive":
        return _segment_receive(frame_landmarks)
    return None
