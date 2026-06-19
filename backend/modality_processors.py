from backend.modalities import MODALITY_DEFINITIONS, normalize_modalities


FRAME_CONTEXT_KEYS = (
    "frame_index",
    "landmarks",
    "world_landmarks",
    "hand_landmarks",
    "angles",
    "positions",
    "hand_features",
)

PROCESSOR_FACTORIES = {}


def register_processor(modality_id, factory):
    if modality_id not in MODALITY_DEFINITIONS:
        raise KeyError(f"Unknown modality: {modality_id}")
    PROCESSOR_FACTORIES[modality_id] = factory


def build_modality_processors(selected_modalities):
    processors = []
    for modality_id in normalize_modalities(selected_modalities):
        definition = MODALITY_DEFINITIONS.get(modality_id)
        factory = PROCESSOR_FACTORIES.get(modality_id)
        if definition and definition["available"] and factory:
            processors.append(factory())
    return processors


def finalize_modality_results(processors, selected_modalities):
    results = {processor.modality_id: processor.finalize() for processor in processors}
    reserved = {}
    selected = set(normalize_modalities(selected_modalities))

    for modality_id in selected:
        definition = MODALITY_DEFINITIONS.get(modality_id)
        if definition and not definition["available"]:
            reserved[modality_id] = "已預留 API 欄位，尚未接入模型。"

    results["reserved"] = reserved
    return results


def _average(total, count):
    if count <= 0:
        return None
    return round(total / count, 2)


class PoseMetricsProcessor:
    modality_id = "pose"

    def __init__(self):
        self.frames_with_pose = 0
        self.angle_totals = {
            "elbow": 0.0,
            "knee": 0.0,
            "shoulder": 0.0,
        }

    def observe(self, context):
        angles = context["angles"]
        self.frames_with_pose += 1
        for key in self.angle_totals:
            self.angle_totals[key] += float(angles.get(key, 0.0))

    def finalize(self):
        return {
            "frames_with_pose": self.frames_with_pose,
            "average_elbow_angle": _average(self.angle_totals["elbow"], self.frames_with_pose),
            "average_knee_angle": _average(self.angle_totals["knee"], self.frames_with_pose),
            "average_shoulder_angle": _average(self.angle_totals["shoulder"], self.frames_with_pose),
        }


class HandMetricsProcessor:
    modality_id = "hands"

    def __init__(self):
        self.frames_with_hands = 0
        self.finger_extension_total = 0.0
        self.hand_gap_total = 0.0
        self.hand_gap_count = 0

    def observe(self, context):
        hand_features = context["hand_features"]
        if hand_features.get("hands_detected", 0) <= 0:
            return

        self.frames_with_hands += 1
        self.finger_extension_total += float(hand_features.get("finger_extension") or 0.0)
        if hand_features.get("hand_center_gap") is not None:
            self.hand_gap_total += float(hand_features["hand_center_gap"])
            self.hand_gap_count += 1

    def finalize(self):
        return {
            "frames_with_hands": self.frames_with_hands,
            "average_finger_extension": _average(
                self.finger_extension_total,
                self.frames_with_hands,
            ),
            "average_hand_gap": _average(self.hand_gap_total, self.hand_gap_count),
        }


register_processor("pose", PoseMetricsProcessor)
register_processor("hands", HandMetricsProcessor)
