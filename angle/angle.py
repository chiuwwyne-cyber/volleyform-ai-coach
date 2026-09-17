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




def _best_landmarks(image_landmarks, world_landmarks=None):
    # MediaPipe world landmarks preserve body depth better than image x/y/z.
    return world_landmarks if world_landmarks is not None else image_landmarks


def get_shape_features(image_landmarks):
    """Normalised, in-plane shape measures the joint angles cannot express.

    Deliberately computed on IMAGE landmarks, not world ones. These are
    relationships between left and right (how far apart the hands are, how level
    they are), and in the image plane that is exactly what the camera sees.
    Routing them through world landmarks would drag in the depth estimate, which
    is the axis this project has repeatedly found unreliable.

    **Everything is divided by TORSO LENGTH, not by shoulder width.** The first
    version used shoulder width and the scan showed why that cannot work: a
    player filmed edge-on projects both shoulders onto nearly the same x, so the
    denominator collapses. One serve clip measured a hand_level_gap of 81.5 --
    two wrists cannot be 81 body-widths apart in a frame one unit tall, and the
    shoulder width behind it was 0.015. Torso length is a vertical segment, which
    yaw barely foreshortens, and it is the correct scale for a vertical quantity
    anyway. This is the same trap as MAX_NORM in the clip pipeline: a ratio whose
    denominator can vanish does not report a large value, it reports a useless one.

    `torso` and `frontality` are returned alongside so callers can gate on scale
    and on how square the player is to the camera. They are measurements, not
    checks -- the thresholds belong wherever they can be calibrated.
    """
    points = image_landmarks
    shoulder_x = (points[11].x + points[12].x) / 2.0
    shoulder_y = (points[11].y + points[12].y) / 2.0
    hip_x = (points[23].x + points[24].x) / 2.0
    hip_y = (points[23].y + points[24].y) / 2.0
    torso = math.hypot(shoulder_x - hip_x, shoulder_y - hip_y)
    if torso < 1e-4:
        return {}
    shoulder_w = abs(points[11].x - points[12].x)
    return {
        "hand_level_gap": abs(points[15].y - points[16].y) / torso,
        "hand_gap": abs(points[15].x - points[16].x) / torso,
        "stance_width": abs(points[27].x - points[28].x) / torso,
        "wrist_above_shoulder": (shoulder_y - min(points[15].y, points[16].y)) / torso,
        # How far the hands sit sideways from the head. A set is played from
        # directly above the forehead; hands drifting in front of or behind it
        # is a standard coaching fault and one the angle bands cannot express,
        # since the elbow and shoulder angles are the same either way.
        # Absolute, because the sign only says which way the player faces.
        "hands_off_center": abs((points[15].x + points[16].x) / 2.0 - points[0].x) / torso,
        # Shoulders forward of the hips. A blocker leaning into the net cannot
        # jump straight and risks a net touch. Absolute for the same reason.
        "trunk_lean": abs(shoulder_x - hip_x) / torso,
        # In-plane shadow of trunk rotation. tools/measure_torso_rotation.py does
        # this properly, with a body-fixed axis and bone-length-solved depth, but
        # it reports the PEAK over a wind-up window and the evaluator judges one
        # frame. It also leans on z, which this function deliberately avoids.
        # When the shoulders turn away from the camera and the hips do not, the
        # shoulder line foreshortens while the hip line does not, so the ratio
        # drops. It cannot tell which way the player turned, only how much the
        # two lines disagree.
        "shoulder_hip_width_ratio": shoulder_w / max(abs(points[23].x - points[24].x), 1e-6),
        # The LOWER hand, where wrist_above_shoulder takes the higher one. On a
        # serve or spike the non-hitting arm is raised to aim; without it that
        # hand hangs by the hip and this goes sharply negative.
        "low_wrist_above_shoulder": (shoulder_y - max(points[15].y, points[16].y)) / torso,
        # How square the player is to the camera. Near 0 means edge-on, where a
        # left-right distance measures depth rather than separation and means
        # nothing. Reported so the gate can be set from data.
        "frontality": shoulder_w / torso,
        # Absolute scale in frame heights. A player this small carries landmark
        # noise comparable to the quantity being measured.
        "torso": torso,
    }


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


# 每個形狀特徵實際讀到的 landmark,給畫面外 gate 用。與 get_shape_features 放在
# 一起,是因為兩者必須同步:加了特徵卻忘了加這裡,那個特徵就會繞過 gate,
# 直接拿 MediaPipe 在畫面外硬猜的手去判使用者。
# 每個關節實際用到的 landmark。左右兩側都列,因為 get_angles 取
# knee=min(左,右)、elbow/shoulder=max(左,右)——只要**一側**是幻覺就可能正好被選中。
JOINT_LANDMARKS = {
    "knee": (23, 24, 25, 26, 27, 28),
    "elbow": (11, 12, 13, 14, 15, 16),
    "shoulder": (11, 12, 13, 14, 23, 24),
}


# Which landmarks each feature of get_shape_features reads, for the gate below.
# The two must stay in step -- a feature added to that function and not to this
# table is judged with nothing checking its landmarks -- and since they sit at
# opposite ends of this file, backend/shape_check_test.py asserts the two key
# sets are equal rather than trusting anyone to notice.
SHAPE_LANDMARKS = {
    # Every feature divides by torso length, so 11/12/23/24 appear in all of
    # them: an invented hip makes the denominator wrong and every ratio with it.
    "hand_level_gap": (11, 12, 15, 16, 23, 24),
    "hand_gap": (11, 12, 15, 16, 23, 24),
    "stance_width": (11, 12, 23, 24, 27, 28),
    "wrist_above_shoulder": (11, 12, 15, 16, 23, 24),
    "hands_off_center": (0, 11, 12, 15, 16, 23, 24),
    "trunk_lean": (11, 12, 23, 24),
    "shoulder_hip_width_ratio": (11, 12, 23, 24),
    "low_wrist_above_shoulder": (11, 12, 15, 16, 23, 24),
    "frontality": (11, 12, 23, 24),
    "torso": (11, 12, 23, 24),
}


# 兩層規則,兩層都是量出來的:
#   * 明顯在畫面外(超過邊界 0.10 以上)—— **不管信心多高都丟**。
#     `pexels_6217341` 是鏡頭在拍天花板追球、只有指尖在畫面下緣,MediaPipe 卻
#     「有信心地」(vis 0.69-0.78)把整個上半身放在 y=1.01-1.14,算出 177.8° 的手肘。
#     原本只看低信心的版本擋不掉它:**高信心的幻覺仍然是幻覺**。
#   * 剛好切到邊(0 到 0.10)—— 只在低信心時丟。腳踝 y=1.02、可見度 0.82 是被裁到
#     一點點,那個角度還可信,不該誤殺。
OFFSCREEN_MARGIN = 0.10      # 超過畫面邊界多少算「明顯在外」
OFFSCREEN_VISIBILITY = 0.5   # 邊緣地帶才用得到的信心門檻


def landmarks_offscreen(landmarks, indices):
    """這些 landmark 裡有沒有「畫面外硬猜」的?

    2026-08-17 加在校準端,2026-09-17 搬到這裡讓判定端共用。`block` 的
    crouch.knee 最小值曾是 **23.6°**——解剖學上不可能——因為那一格兩隻腳踝都在
    畫面下方外面(y=1.36/1.42)、可見度只有 0.07/0.12。MediaPipe 對看不見的部位
    仍會輸出座標,流程卻從不檢查,幻覺出來的角度就直接進了 band。全資料集掃過
    後,block 的 crouch.knee 有 13/16 個樣本是這樣來的。

    **兩個條件要同時成立才丟**,這點是量出來的、不是猜的:
      * 只看可見度會誤殺**遮擋**(手肘在畫面正中央被身體擋住,vis 0.41,估計仍可用)
      * 只看出畫面會誤殺**剛好被裁到邊**(腳踝 y=1.02 但 vis 0.82,角度合理)
    先前試過「vis<0.5 或出畫面就丟」的嚴格版,會把 block 膝角從 16 個砍到 3 個,
    那不是修正是把資料集毀掉。目前這組門檻只動到 14 個 band 裡的 5 個。
    """
    for index in indices:
        if index >= len(landmarks):
            return True
        landmark = landmarks[index]
        # x 跟 y 都要看。只檢查 y 的話,跑出畫面左右邊界的 landmark 仍會被採用,
        # 而那同樣是沒被觀測到的位置。
        beyond = max(landmark.y - 1.0, -landmark.y,
                     getattr(landmark, "x", 0.5) - 1.0, -getattr(landmark, "x", 0.5))
        if beyond <= 0.0:
            continue
        if beyond > OFFSCREEN_MARGIN:
            return True   # 明顯在外:沒被觀測到就是沒被觀測到
        # 沒有 visibility 欄位時當成 0.0(最沒把握),不是 1.0。這個 gate 的作用是
        # 「不確定就不要判」,而漏判一次遠比誤判一次便宜——後者是使用者會看到的。
        # 校準端餵進來的一定是 MediaPipe 物件、一定有這個欄位,所以這個預設值只
        # 影響判定端。
        if getattr(landmark, "visibility", 0.0) < OFFSCREEN_VISIBILITY:
            return True   # 只是擦邊,但模型自己也沒把握
    return False
