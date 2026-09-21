"""ViTPose (base-simple) via HuggingFace transformers, on CPU.

ViTPose is a pure top-down pose head: it has no person detector of its own and
is undefined without boxes. Pairing it with RT-DETR here is not an arbitrary
choice - it is the pairing the model card documents, and it keeps the
comparison honest, because RTMPose is likewise measured with its detector
attached. Feeding either model hand-drawn boxes would measure half a system.

This is the accuracy ceiling in the comparison (>80 COCO AP) and also the
heaviest thing in it. Both facts matter to the conclusion.

Runs in the benchmark venv.
"""

import argparse
import os
import sys

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH_DIR)

from contract import COCO_INDEX
from runner import normalise, run, torso_area

POSE_MODEL = "usyd-community/vitpose-base-simple"
DET_MODEL = "PekingU/rtdetr_r50vd_coco_o365"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--det-threshold", type=float, default=0.4)
    args = ap.parse_args()

    import cv2
    import numpy as np
    import torch
    import transformers
    from transformers import (AutoProcessor, RTDetrForObjectDetection,
                              VitPoseForPoseEstimation)

    torch.set_num_threads(os.cpu_count())

    det_processor = AutoProcessor.from_pretrained(DET_MODEL)
    detector = RTDetrForObjectDetection.from_pretrained(DET_MODEL).eval()
    pose_processor = AutoProcessor.from_pretrained(POSE_MODEL)
    pose_model = VitPoseForPoseEstimation.from_pretrained(POSE_MODEL).eval()

    def detect(frame):
        height, width = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        with torch.no_grad():
            det_inputs = det_processor(images=rgb, return_tensors="pt")
            det_out = detector(**det_inputs)
        det = det_processor.post_process_object_detection(
            det_out, target_sizes=torch.tensor([(height, width)]),
            threshold=args.det_threshold,
        )[0]

        # COCO class 0 is "person"; everything else on a volleyball court
        # (the ball, the net posts) would otherwise get a pose fitted to it.
        keep = det["labels"] == 0
        boxes_xyxy = det["boxes"][keep].cpu().numpy()
        if len(boxes_xyxy) == 0:
            return []

        # ViTPose's processor wants COCO xywh, not xyxy.
        boxes_xywh = boxes_xyxy.copy()
        boxes_xywh[:, 2] -= boxes_xywh[:, 0]
        boxes_xywh[:, 3] -= boxes_xywh[:, 1]

        with torch.no_grad():
            pose_inputs = pose_processor(rgb, boxes=[boxes_xywh], return_tensors="pt")
            pose_out = pose_model(**pose_inputs)
        results = pose_processor.post_process_pose_estimation(
            pose_out, boxes=[boxes_xywh]
        )[0]

        persons = []
        for person in results:
            xy = person["keypoints"].cpu().numpy()
            scores = person["scores"].cpu().numpy()
            persons.append(normalise(xy, scores, COCO_INDEX, width, height))
        persons.sort(key=torso_area, reverse=True)
        return persons

    run(
        backend_name="vitpose",
        model_name=f"ViTPose-base-simple (+ RT-DETR person detector)",
        frames_dir=args.frames,
        out_path=args.out,
        detect=detect,
        extra={
            "transformers": transformers.__version__,
            "torch": torch.__version__,
            "pose_model": POSE_MODEL,
            "detector": DET_MODEL,
            "keypoints_native": 17,
            "single_person_by_design": False,
            "emits_world_3d": False,
            "runs_in_browser": False,
        },
    )


if __name__ == "__main__":
    main()
