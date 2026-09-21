"""YOLO11-Pose (Ultralytics) on CPU.

Single-stage: detection and keypoints come out of one forward pass, which is
the whole selling point against RTMPose's detector-plus-head pipeline.

The `n` weight is used by default because it is the variant anyone would
actually reach for on a CPU-only deployment; `--weights yolo11s-pose.pt` and up
trade speed for accuracy if that comparison is wanted.

NOTE ON LICENCE: Ultralytics ships under AGPL-3.0. Benchmarking it here is
fine, but shipping it inside VolleyForm would put the whole public repository
under AGPL. That is a finding, not a footnote.

Runs in the benchmark venv (torch + numpy 2), not the project env.
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
    ap.add_argument("--weights", default="yolo11n-pose.pt")
    args = ap.parse_args()

    import torch
    import ultralytics
    from ultralytics import YOLO

    torch.set_num_threads(os.cpu_count())
    model = YOLO(args.weights)

    def detect(frame):
        height, width = frame.shape[:2]
        # verbose=False keeps Ultralytics' per-frame logging out of the clock.
        result = model.predict(frame, verbose=False, device="cpu")[0]
        if result.keypoints is None or len(result.keypoints) == 0:
            return []

        xy = result.keypoints.xy.cpu().numpy()
        conf = result.keypoints.conf
        if conf is None:
            return []
        conf = conf.cpu().numpy()

        persons = [
            normalise(xy[i], conf[i], COCO_INDEX, width, height)
            for i in range(len(xy))
        ]
        persons.sort(key=torso_area, reverse=True)
        return persons

    run(
        backend_name="yolopose",
        model_name=f"YOLO11-Pose ({args.weights})",
        frames_dir=args.frames,
        out_path=args.out,
        detect=detect,
        extra={
            "ultralytics": ultralytics.__version__,
            "torch": torch.__version__,
            "weights": args.weights,
            "keypoints_native": 17,
            "single_person_by_design": False,
            "emits_world_3d": False,
            "runs_in_browser": False,
            "licence": "AGPL-3.0",
        },
    )


if __name__ == "__main__":
    main()
