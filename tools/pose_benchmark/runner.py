"""The loop every backend shares: same frames, same order, same timing rules.

A backend supplies one function, `detect(frame_bgr) -> list[person]`, where a
person is a dict mapping contract keypoint names to [x, y, score] with x and y
already normalised to the frame. Everything else - which frames, in what
order, how the clock is read, what gets written down - lives here, so that no
backend can accidentally be measured under kinder conditions than another.

Timing covers inference only. The PNG decode is done outside the clock because
it is identical work for every backend and would otherwise dilute the very
difference the benchmark exists to show.
"""

import json
import os
import platform
import time

import cv2


def load_manifest(frames_dir):
    with open(os.path.join(frames_dir, "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _env_info():
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
    }


def run(backend_name, model_name, frames_dir, out_path, detect,
        on_clip_start=None, extra=None):
    """Run `detect` over every frame in the manifest and write the results.

    `on_clip_start` lets a stateful backend (MediaPipe's video mode keeps a
    tracker between frames) reset itself at a clip boundary. Without it, one
    clip's tracking state would leak into the next clip's first frames.
    """
    manifest = load_manifest(frames_dir)
    results = {
        "backend": backend_name,
        "model": model_name,
        "env": _env_info(),
        "bench_width": manifest["bench_width"],
        "extra": extra or {},
        "clips": {},
    }

    for clip in manifest["clips"]:
        clip_id = clip["clip_id"]
        clip_dir = os.path.join(frames_dir, clip_id)
        if on_clip_start is not None:
            on_clip_start()

        frames_out = []
        for i, name in enumerate(clip["frames"]):
            frame = cv2.imread(os.path.join(clip_dir, name))
            if frame is None:
                raise RuntimeError(f"missing frame {clip_id}/{name}")

            t0 = time.perf_counter()
            persons = detect(frame)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            frames_out.append({
                "i": i,
                "ms": round(elapsed_ms, 2),
                "n_persons": len(persons),
                "kp": persons[0] if persons else None,
            })

        results["clips"][clip_id] = {
            "action": clip["action"],
            "frames": frames_out,
        }
        found = sum(1 for f in frames_out if f["kp"])
        median_ms = sorted(f["ms"] for f in frames_out)[len(frames_out) // 2]
        print(f"  {clip_id}: {found}/{len(frames_out)} frames with a pose, "
              f"median {median_ms:.1f} ms")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh)
    print(f"wrote {out_path}")
    return results


def normalise(keypoints_xy, scores, index_map, width, height):
    """Turn a model's native keypoint array into a contract person dict."""
    person = {}
    for name, idx in index_map.items():
        x, y = float(keypoints_xy[idx][0]), float(keypoints_xy[idx][1])
        person[name] = [x / width, y / height, float(scores[idx])]
    return person


def torso_area(person):
    """Rough on-screen size, used only to pick the primary subject."""
    xs, ys = [], []
    for name in ("left_shoulder", "right_shoulder", "left_hip", "right_hip"):
        kp = person.get(name)
        if kp is None:
            return 0.0
        xs.append(kp[0])
        ys.append(kp[1])
    return (max(xs) - min(xs)) * (max(ys) - min(ys))
