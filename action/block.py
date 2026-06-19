def check_block(angles):
    problems = []

    elbow = angles["elbow"]   # 手肘角度
    shoulder = angles["shoulder"]  # 手臂抬起角度
    knee = angles["knee"]     # 膝蓋角度

    # 手臂是否伸直
    if elbow < 165:
        problems.append("elbow_not_straight")

    # 手是否舉高
    if shoulder < 150:
        problems.append("hands_not_high")

    # 起跳姿勢
    if knee < 140:
        problems.append("knee_too_bent")

    # 沒問題
    if not problems:
        return ["good"]

    return problems