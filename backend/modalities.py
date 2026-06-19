MODALITY_DEFINITIONS = {
    "pose": {
        "label": "身體骨架",
        "available": True,
        "description": "肩、肘、髖、膝、踝與 3D world landmark。",
    },
    "hands": {
        "label": "手部關節",
        "available": True,
        "description": "左右手 21 點，支援托球手型與接球平台判斷。",
    },
    "ball": {
        "label": "球路追蹤",
        "available": False,
        "description": "預留：未來可接 YOLO/追球模型，分析擊球點與球速方向。",
    },
    "audio": {
        "label": "聲音節奏",
        "available": False,
        "description": "預留：未來可分析擊球聲、落地聲與節奏。",
    },
    "wearable": {
        "label": "穿戴感測",
        "available": False,
        "description": "預留：未來可接 IMU、手錶、手機加速度資料。",
    },
    "coach_text": {
        "label": "教練備註",
        "available": False,
        "description": "預留：未來可讓教練輸入觀察，和 AI 結果合併。",
    },
}

DEFAULT_MODALITIES = ["pose", "hands"]


def normalize_modalities(requested):
    if not requested:
        return list(DEFAULT_MODALITIES)

    normalized = []
    for item in requested:
        key = str(item).strip()
        if key in MODALITY_DEFINITIONS and key not in normalized:
            normalized.append(key)

    for required in DEFAULT_MODALITIES:
        if required not in normalized:
            normalized.append(required)

    return normalized


def modality_status(selected):
    selected = set(normalize_modalities(selected))
    statuses = []
    for key, definition in MODALITY_DEFINITIONS.items():
        requested = key in selected
        available = bool(definition["available"])
        if requested and available:
            state = "active"
        elif requested:
            state = "reserved"
        else:
            state = "available" if available else "future"

        statuses.append({
            "id": key,
            "label": definition["label"],
            "description": definition["description"],
            "available": available,
            "requested": requested,
            "state": state,
        })
    return statuses


def capabilities_payload():
    return {
        "default_modalities": list(DEFAULT_MODALITIES),
        "modalities": modality_status(DEFAULT_MODALITIES),
    }
