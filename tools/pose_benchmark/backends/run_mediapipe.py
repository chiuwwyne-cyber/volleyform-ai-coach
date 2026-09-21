"""MediaPipe Pose (BlazePose) - the incumbent, run the way VolleyForm runs it.

Uses Holistic with static_image_mode=False and model_complexity=1, matching
pose/pose.py. Benchmarking it in static-image mode instead would be measuring a
configuration the app never ships.

Runs in the PROJECT environment, not the benchmark venv, because mediapipe
0.10.9 and the ONNX/torch models want incompatible numpy versions - which is
itself one of the findings.
"""

import argparse
import os
import sys

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH_DIR)

from contract import BLAZEPOSE_INDEX
from runner import run

from mediapipe import solutions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import cv2
    import mediapipe

    state = {"holistic": None}

    def new_holistic():
        if state["holistic"] is not None:
            state["holistic"].close()
        state["holistic"] = solutions.holistic.Holistic(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            enable_segmentation=False,
            refine_face_landmarks=False,
            min_detection_confidence=0.45,
            min_tracking_confidence=0.45,
        )

    def detect(frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = state["holistic"].process(rgb)
        if not result.pose_landmarks:
            return []
        lms = result.pose_landmarks.landmark
        # MediaPipe's x/y are already normalised to the frame; `visibility` is
        # its confidence and is read here as the contract's score.
        person = {
            name: [float(lms[i].x), float(lms[i].y), float(lms[i].visibility)]
            for name, i in BLAZEPOSE_INDEX.items()
        }
        return [person]

    run(
        backend_name="mediapipe",
        model_name="BlazePose (Holistic, model_complexity=1)",
        frames_dir=args.frames,
        out_path=args.out,
        detect=detect,
        on_clip_start=new_holistic,
        extra={
            "version": mediapipe.__version__,
            "keypoints_native": 33,
            "single_person_by_design": True,
            "emits_world_3d": True,
            "runs_in_browser": True,
        },
    )
    if state["holistic"] is not None:
        state["holistic"].close()


if __name__ == "__main__":
    main()
