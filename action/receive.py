def check_receive(angles, positions=None, hand_features=None):
    problems = []
    hand_features = hand_features or {}

    elbow = angles["elbow"]
    knee = angles["knee"]
    shoulder = angles.get("shoulder", 180)

    if elbow < 160:
        problems.append("elbow_bad")

    if knee < 140:
        problems.append("knee_too_bent")

    # "吃蘿蔔" risk: platform is likely too soft/unstable, so the ball may jam the forearms.
    if elbow < 170 and shoulder < 95:
        problems.append("lobster_receive_risk")

    if hand_features.get("hands_detected", 0) >= 2:
        hands_level_gap = hand_features.get("hands_level_gap")
        hand_center_gap = hand_features.get("hand_center_gap")
        if hands_level_gap is not None and hands_level_gap > 0.08:
            problems.append("receive_platform_unbalanced")
        if hand_center_gap is not None and hand_center_gap > 0.24:
            problems.append("receive_hands_apart")

    if not problems:
        return ["good"]

    return problems
