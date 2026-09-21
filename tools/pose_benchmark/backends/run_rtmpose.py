"""RTMPose (OpenMMLab) via rtmlib + ONNX Runtime, on CPU.

Run as the full two-stage pipeline (person detector -> pose head) rather than
as a bare pose head fed ground-truth boxes. A bare head would post a flattering
speed number for a system nobody can actually deploy: on real footage the
detector is not optional, and its cost is part of the model's cost.

RTMPose is top-1 in the published OKS comparisons and the usual production
recommendation, so it is the strongest case against staying on MediaPipe.

Runs in the benchmark venv (onnxruntime + numpy 2), not the project env.
"""

import argparse
import os
import sys

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH_DIR)

from contract import COCO_INDEX
from runner import normalise, run, torso_area


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", default="balanced",
                    choices=["lightweight", "balanced", "performance"])
    args = ap.parse_args()

    from rtmlib import Body
    import onnxruntime

    body = Body(mode=args.mode, backend="onnxruntime", device="cpu")

    def detect(frame):
        height, width = frame.shape[:2]
        keypoints, scores = body(frame)
        if keypoints is None or len(keypoints) == 0:
            return []
        persons = [
            normalise(keypoints[i], scores[i], COCO_INDEX, width, height)
            for i in range(len(keypoints))
        ]
        # The contract records one subject per frame. RTMPose returns everyone
        # on court, so the largest torso is taken as the primary - the same
        # heuristic MediaPipe applies internally. How often that choice is
        # ambiguous is reported separately as n_persons.
        persons.sort(key=torso_area, reverse=True)
        return persons

    run(
        backend_name="rtmpose",
        model_name=f"RTMPose ({args.mode} preset, RTMDet person detector)",
        frames_dir=args.frames,
        out_path=args.out,
        detect=detect,
        extra={
            "onnxruntime": onnxruntime.__version__,
            "providers": onnxruntime.get_available_providers(),
            "keypoints_native": 17,
            "single_person_by_design": False,
            "emits_world_3d": False,
            "runs_in_browser": False,
            "mode": args.mode,
        },
    )


if __name__ == "__main__":
    main()
