def check_spike(angles):
    problems = []

    elbow = angles["elbow"]
    knee = angles["knee"]

    # 手肘判斷
    if elbow < 150:
        problems.append("elbow_bad")

    # 膝蓋判斷（防受傷🔥）
    if knee < 150:
        problems.append("knee_bad")

    # 沒問題
    if not problems:
        return ["good"]

    return problems