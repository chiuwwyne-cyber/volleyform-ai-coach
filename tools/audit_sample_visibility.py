"""稽核:`build_reference.py` 收進 band 的每個樣本,關節真的看得到嗎?

## 為什麼要有這支

2026-08-17 發現 `block` 的 crouch.knee `min` 是 **23.6°**——解剖學上不可能。查下去
是 `pexels_10350518` 這段的 crouch 格兩隻腳踝都在畫面外(y=1.36/1.42)、可見度只有
0.07/0.12。**MediaPipe 自己都回報看不到,`build_reference.py` 照樣把幻覺出來的角度
收進 band。**

`tools/dataset_clips/README.md` 早就記了這個陷阱,但只用在「驗新片」,從來沒有回頭
套用到既有資料集,而且**校準流程本身完全不檢查可見度**。

## 量法上的兩個坑

1. **角度用 world landmarks,可見度要看 image landmarks。** `get_angles()` 走
   `_best_landmarks()`,優先用 world;但 world 是以髖部為原點的座標,y 不是螢幕座標,
   「y>1 代表出畫面」只在 image landmarks 上成立。`_process_clip` 存的
   `frame["landmarks"]` 就是 image 那組,用它。

2. **左右取捨會挑到壞的那邊。** `knee = min(左,右)`、`elbow`/`shoulder` = `max(左,右)`。
   所以只要**一側**是幻覺,就可能正好被選中。因此門檻是「該關節用到的 landmark
   全部都要過」,不是「至少一側過」。

用法:`.venv\\Scripts\\python.exe tools\\audit_sample_visibility.py [action ...]`
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from angle.angle import get_angles  # noqa: E402
from backend.phase_segmentation import segment_action  # noqa: E402
from pose.pose import get_pose_from_video  # noqa: E402
from tools.build_reference import (  # noqa: E402
    ACTION_PHASE_JOINTS,
    ACTIONS,
    DATASET_DIR,
    MAX_FRAMES,
)

MIN_VISIBILITY = 0.5
MAX_Y = 1.0

# 每個關節實際用到的 landmark(左右都算,因為 min/max 可能挑到壞的那側)
JOINT_LANDMARKS = {
    "knee": (23, 24, 25, 26, 27, 28),
    "elbow": (11, 12, 13, 14, 15, 16),
    "shoulder": (11, 12, 13, 14, 23, 24),
}


def _bad_landmarks(landmarks, joint):
    bad = []
    for idx in JOINT_LANDMARKS[joint]:
        lm = landmarks[idx]
        if lm.visibility < MIN_VISIBILITY or lm.y > MAX_Y or lm.y < 0.0:
            bad.append((idx, round(lm.visibility, 2), round(lm.y, 2)))
    return bad


def dump_samples(actions, out_path):
    """存下每個校準樣本的角度＋它用到的 landmark 狀態。

    存這份的理由:整趟 pose 掃描要 35 分鐘,而「門檻該設多少」需要反覆試。把原始
    資料存下來,之後試新規則就是幾秒的事,不必每次重跑——也避免因為嫌慢而少試幾個
    門檻就草率定案。
    """
    import json

    rows = []
    for action in actions:
        action_dir = os.path.join(DATASET_DIR, action)
        if not os.path.isdir(action_dir):
            continue
        phase_joints = ACTION_PHASE_JOINTS.get(action, {})
        for name in sorted(n for n in os.listdir(action_dir) if n.lower().endswith(".mp4")):
            frames = []
            for data in get_pose_from_video(os.path.join(action_dir, name),
                                            process_width=640, frame_stride=2,
                                            include_image=False):
                frames.append({"landmarks": data[0],
                               "angles": get_angles(data[0], data[1])})
                if len(frames) >= MAX_FRAMES:
                    break
            segments = segment_action(action, [f["landmarks"] for f in frames])
            if not segments:
                continue
            for phase, joints in phase_joints.items():
                idx = segments.get(phase)
                if idx is None:
                    continue
                landmarks = frames[idx]["landmarks"]
                for joint in joints:
                    rows.append({
                        "action": action, "clip": name, "phase": phase, "joint": joint,
                        "angle": round(frames[idx]["angles"][joint], 2),
                        "landmarks": {
                            str(i): {"vis": round(landmarks[i].visibility, 3),
                                     "y": round(landmarks[i].y, 3)}
                            for i in JOINT_LANDMARKS[joint]
                        },
                    })
            print(f"[{action}] {name}", flush=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=1)
    print(f"\nwrote {len(rows)} samples -> {out_path}")
    return rows


def audit(actions):
    grand = {}
    for action in actions:
        action_dir = os.path.join(DATASET_DIR, action)
        if not os.path.isdir(action_dir):
            continue
        phase_joints = ACTION_PHASE_JOINTS.get(action, {})
        clips = sorted(n for n in os.listdir(action_dir) if n.lower().endswith(".mp4"))
        print(f"\n=== {action} ({len(clips)} clips) ===")
        tally = {}
        for name in clips:
            frames = []
            for data in get_pose_from_video(os.path.join(action_dir, name),
                                            process_width=640, frame_stride=2,
                                            include_image=False):
                frames.append({"landmarks": data[0],
                               "angles": get_angles(data[0], data[1])})
                if len(frames) >= MAX_FRAMES:
                    break
            segments = segment_action(action, [f["landmarks"] for f in frames])
            if not segments:
                continue
            for phase, joints in phase_joints.items():
                idx = segments.get(phase)
                if idx is None:
                    continue
                for joint in joints:
                    key = f"{phase}.{joint}"
                    tally.setdefault(key, {"total": 0, "bad": 0, "clips": []})
                    tally[key]["total"] += 1
                    bad = _bad_landmarks(frames[idx]["landmarks"], joint)
                    if bad:
                        tally[key]["bad"] += 1
                        tally[key]["clips"].append(
                            (name, round(frames[idx]["angles"][joint], 1), bad))
        for key, info in sorted(tally.items()):
            pct = 100.0 * info["bad"] / max(1, info["total"])
            print(f"  {key:18} {info['bad']:2d}/{info['total']:2d} 樣本的關節看不到 ({pct:.0f}%)")
            for name, angle, bad in sorted(info["clips"], key=lambda c: c[1]):
                worst = ", ".join(f"lm{i}(vis{v},y{y})" for i, v, y in bad[:3])
                print(f"      {name:32} 角度={angle:6.1f}  {worst}")
        grand[action] = tally
    return grand


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dump_to = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--dump=")), None)
    if dump_to:
        dump_samples(args or list(ACTIONS), dump_to)
    else:
        audit(args or list(ACTIONS))
