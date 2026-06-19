def check_set(angles, positions, hand_features=None):
    problems = []
    hand_features = hand_features or {}

    elbow = angles["elbow"]          # 手肘角度
    shoulder = angles["shoulder"]    # 手臂抬起角度

    wrist_y = positions["wrist_y"]   # 手腕高度
    head_y = positions["head_y"]     # 頭部高度

    # 1️⃣ 手是否在頭上（最重要🔥）
    if wrist_y > head_y:
        problems.append("wrist_low")

    # 2️⃣ 手肘角度（托球要有彈性）
    if elbow < 140 or elbow > 175:
        problems.append("elbow_position_bad")

    # 3️⃣ 手臂抬起角度
    if shoulder < 140:
        problems.append("shoulder_low")

    hands_detected = hand_features.get("hands_detected", 0)
    finger_extension = hand_features.get("finger_extension", 0)
    hand_center_gap = hand_features.get("hand_center_gap")
    hands_level_gap = hand_features.get("hands_level_gap")

    if hands_detected < 2:
        problems.append("setting_hands_not_detected")
    else:
        if finger_extension < 1.08:
            problems.append("setting_fingers_closed")

        if hand_center_gap is not None and (hand_center_gap < 0.06 or hand_center_gap > 0.32):
            problems.append("setting_hand_spacing_bad")

        if hands_level_gap is not None and hands_level_gap > 0.08:
            problems.append("setting_hands_unbalanced")

    # 沒問題
    if not problems:
        return ["good"]

    return problems
