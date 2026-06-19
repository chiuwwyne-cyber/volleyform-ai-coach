def check_serve(angles):
    problems = []

    elbow = angles["elbow"]        # 手肘角度（揮手）
    shoulder = angles["shoulder"]  # 手臂抬起角度
    knee = angles["knee"]          # 膝蓋角度

    # 揮手是否足夠伸展
    if elbow < 150:
        problems.append("elbow_bad")

    # 手是否抬高（準備擊球）
    if shoulder < 140:
        problems.append("shoulder_low")

    # 下半身穩定性（不要過度彎）
    if knee < 150:
        problems.append("knee_bad")

    # 沒問題
    if not problems:
        return ["good"]

    return problems