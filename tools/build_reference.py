"""Calibrate per-phase joint-angle bands from reference clips.

Usage:
    .venv\\Scripts\\python.exe tools\\build_reference.py

Scans dataset/<action>/*.mp4, extracts pose, segments each clip into key
moments (crouch / contact), and writes percentile bands per action, phase and
joint to backend/reference_standards.json. Only the derived statistics are
committed; the clips themselves stay out of the repository.
"""

import json
import math
import os
import sys
from datetime import date

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from angle.angle import get_angles
from backend.phase_segmentation import segment_action
from pose.pose import get_pose_from_video
from tools.sync_frontend import sync_frontend

DATASET_DIR = os.path.join(ROOT_DIR, "dataset")
OUTPUT_PATH = os.path.join(ROOT_DIR, "backend", "reference_standards.json")

ACTIONS = ("spike", "serve", "block", "receive", "set")
ACTION_PHASE_JOINTS = {
    "spike": {
        "contact": ("elbow", "shoulder"),
        "crouch": ("knee",),
    },
    "serve": {
        "contact": ("elbow", "shoulder"),
        "crouch": ("knee",),
    },
    "block": {
        "contact": ("elbow", "shoulder"),
        "crouch": ("knee",),
    },
    "receive": {
        "contact": ("elbow", "knee", "shoulder"),
    },
    "set": {
        "contact": ("elbow", "shoulder"),
    },
}
MAX_FRAMES = 300
REFERENCE_TARGET_CLIPS = 20

JOINT_TOLERANCE = {
    # Extra player_grace keeps correct amateur movements from being judged only
    # against elite range-of-motion. The sample term below shrinks as more clips
    # are added, so the accepted band becomes tighter when the data converges.
    "elbow": {"min": 8.0, "max": 22.0, "player_grace": 4.0},
    "shoulder": {"min": 8.0, "max": 22.0, "player_grace": 5.0},
    "knee": {"min": 10.0, "max": 24.0, "player_grace": 6.0},
}


def _percentile(sorted_values, fraction):
    if not sorted_values:
        return None
    index = fraction * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _clamp(value, lower, upper):
    return max(lower, min(upper, value))


def _iqr_bounds(ordered):
    if len(ordered) < 8:
        return None
    p25 = _percentile(ordered, 0.25)
    p75 = _percentile(ordered, 0.75)
    iqr = p75 - p25
    if iqr <= 0:
        return None
    return p25 - 1.5 * iqr, p75 + 1.5 * iqr


def _trim_outliers(values):
    ordered = sorted(values)
    bounds = _iqr_bounds(ordered)
    if not bounds:
        return ordered, ordered, 0
    lower, upper = bounds
    trimmed = [value for value in ordered if lower <= value <= upper]
    outliers = len(ordered) - len(trimmed)
    # Exclude IQR outliers (>1.5*IQR) from the percentile band so a few bad or
    # mis-detected clips (rally/broadcast footage, pose glitches) cannot stretch
    # the accepted range and make the app miss real mistakes. Guard: never trim
    # below ~60% of the samples, so a small class keeps its genuine spread.
    if len(trimmed) < max(5, math.ceil(len(ordered) * 0.6)):
        return ordered, ordered, outliers
    return ordered, trimmed, outliers


# 每個關節實際用到的 landmark。左右兩側都列,因為 get_angles 取
# knee=min(左,右)、elbow/shoulder=max(左,右)——只要**一側**是幻覺就可能正好被選中。
JOINT_LANDMARKS = {
    "knee": (23, 24, 25, 26, 27, 28),
    "elbow": (11, 12, 13, 14, 15, 16),
    "shoulder": (11, 12, 13, 14, 23, 24),
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


PHASE_SCOPE_PATH = os.path.join(DATASET_DIR, "clip_phase_scope.json")


def _load_phase_scope():
    """Which phases each clip is allowed to contribute, keyed "<action>/<clip>".

    Added 2026-08-17. A clip can be good evidence for one phase and bad for
    another: live-play block footage carries the deep crouch this dataset lacks
    (measured 80.9 and 105.4 degrees where the whole band's minimum was 120.1),
    while its contact elbows measure 123-139 against a p10 of 141.4, because
    players in a rally do not fully extend. Taking those clips whole would fix
    the knee band and loosen the elbow floor -- the same trade that forced the
    2026-08-05 set revert.

    This is the per-JOINT visibility gate's idea moved up to the phase level.
    Clips not listed contribute every phase, so the file is additive and the
    default behaviour is unchanged.
    """
    if not os.path.exists(PHASE_SCOPE_PATH):
        return {}
    with open(PHASE_SCOPE_PATH, encoding="utf-8") as handle:
        raw = json.load(handle)
    scope = {}
    for key, entry in raw.get("clips", {}).items():
        phases = entry.get("phases")
        if not phases:
            raise ValueError(f"{PHASE_SCOPE_PATH}: {key} lists no phases")
        if not entry.get("reason"):
            # An unexplained scope is indistinguishable from trimming the data
            # until the numbers look right, so refuse to run without one.
            raise ValueError(f"{PHASE_SCOPE_PATH}: {key} has no reason")
        scope[key] = set(phases)
    return scope


def _joint_is_offscreen_guess(landmarks, joint):
    """這個關節的角度是不是算在「畫面外硬猜」的 landmark 上?

    2026-08-17 加。`block` 的 crouch.knee 最小值曾是 **23.6°**——解剖學上不可能——
    因為那一格兩隻腳踝都在畫面下方外面(y=1.36/1.42)、可見度只有 0.07/0.12。
    MediaPipe 對看不見的部位仍會輸出座標,校準流程卻從不檢查,所以幻覺出來的角度
    直接進了 band。全資料集掃過後,block 的 crouch.knee 有 13/16 個樣本是這樣來的。

    **兩個條件要同時成立才丟**,這點是量出來的、不是猜的:
      * 只看可見度會誤殺**遮擋**(手肘在畫面正中央被身體擋住,vis 0.41,估計仍可用)
      * 只看出畫面會誤殺**剛好被裁到邊**(腳踝 y=1.02 但 vis 0.82,角度合理)
    先前試過「vis<0.5 或出畫面就丟」的嚴格版,會把 block 膝角從 16 個砍到 3 個,
    那不是修正是把資料集毀掉。目前這組門檻只動到 14 個 band 裡的 5 個。
    """
    for index in JOINT_LANDMARKS[joint]:
        landmark = landmarks[index]
        beyond = max(landmark.y - 1.0, -landmark.y)  # >0 表示在畫面外
        if beyond <= 0.0:
            continue
        if beyond > OFFSCREEN_MARGIN:
            return True   # 明顯在外:沒被觀測到就是沒被觀測到
        if landmark.visibility < OFFSCREEN_VISIBILITY:
            return True   # 只是擦邊,但模型自己也沒把握
    return False


def _adaptive_tolerance(ordered, joint):
    count = len(ordered)
    p25 = _percentile(ordered, 0.25)
    p75 = _percentile(ordered, 0.75)
    iqr = max(0.0, p75 - p25)
    limits = JOINT_TOLERANCE.get(joint, {"min": 8.0, "max": 18.0})
    spread_allowance = min(6.0, iqr * 0.18)
    sample_allowance = min(5.0, 9.0 / math.sqrt(max(count, 1)))
    convergence_taper = 1.0 - min(0.45, count / 60.0)
    player_allowance = limits.get("player_grace", 4.0) * convergence_taper
    tolerance = limits["min"] + spread_allowance + sample_allowance + player_allowance
    return round(_clamp(tolerance, limits["min"], limits["max"]), 1)


def _convergence_score(ordered, raw_count, outliers):
    if not ordered:
        return 0.0
    p25 = _percentile(ordered, 0.25)
    p75 = _percentile(ordered, 0.75)
    iqr = max(0.0, p75 - p25)
    count_score = min(1.0, raw_count / REFERENCE_TARGET_CLIPS)
    spread_score = 1.0 / (1.0 + iqr / 45.0)
    outlier_score = 1.0 - min(0.5, outliers / max(raw_count, 1))
    return round(count_score * 0.45 + spread_score * 0.45 + outlier_score * 0.10, 2)


def _convergence_state(score, raw_count):
    if raw_count >= 14 and score >= 0.65:
        return "stable"
    if raw_count >= 5 and score >= 0.45:
        return "usable"
    return "needs_more_data"


def _accepted_range(p10, p90, tolerance):
    return [
        round(_clamp(p10 - tolerance, 0.0, 180.0), 1),
        round(_clamp(p90 + tolerance, 0.0, 180.0), 1),
    ]


def _band(values, joint):
    ordered, trimmed, outliers = _trim_outliers(values)
    raw_count = len(values)
    p10 = round(_percentile(trimmed, 0.10), 1)
    p90 = round(_percentile(trimmed, 0.90), 1)
    tolerance = _adaptive_tolerance(trimmed, joint)
    convergence = _convergence_score(trimmed, raw_count, outliers)
    return {
        "count": len(trimmed),
        "raw_count": raw_count,
        "outliers": outliers,
        "min": round(ordered[0], 1),
        "p10": p10,
        "p25": round(_percentile(trimmed, 0.25), 1),
        "p50": round(_percentile(trimmed, 0.50), 1),
        "p75": round(_percentile(trimmed, 0.75), 1),
        "p90": p90,
        "max": round(ordered[-1], 1),
        # The largest sample the band actually KEPT. `max` above comes from the
        # untrimmed list, so it can be an IQR outlier the calibration deliberately
        # excluded -- anchoring anything to it would let a sample judged wrong
        # widen the standard. set.contact.elbow shows the gap: max 177.8 against a
        # p90 of 154.0.
        "max_kept": round(trimmed[-1], 1),
        "tolerance": tolerance,
        "accepted_range": _accepted_range(p10, p90, tolerance),
        "convergence": convergence,
        "convergence_state": _convergence_state(convergence, raw_count),
    }


def _process_clip(video_path):
    frames = []
    for pose_data in get_pose_from_video(
        video_path, process_width=640, frame_stride=2, include_image=False
    ):
        if len(frames) >= MAX_FRAMES:
            break
        if len(pose_data) == 4:
            landmarks, world_landmarks, _frame, _hands = pose_data
        else:
            landmarks, world_landmarks, _frame = pose_data
        frames.append(
            {
                "landmarks": landmarks,
                "angles": get_angles(landmarks, world_landmarks),
            }
        )
    return frames


def main():
    result = {
        "version": 1,
        "generated": date.today().isoformat(),
        "source": "dataset/MANIFEST.md",
        "actions": {},
    }

    phase_scope = _load_phase_scope()
    if phase_scope:
        print(f"phase scope: {len(phase_scope)} clip(s) limited to specific phases")

    for action in ACTIONS:
        action_dir = os.path.join(DATASET_DIR, action)
        if not os.path.isdir(action_dir):
            continue
        clips = sorted(
            name for name in os.listdir(action_dir) if name.lower().endswith(".mp4")
        )
        if not clips:
            continue

        phase_joints = ACTION_PHASE_JOINTS.get(action, {})
        samples = {
            phase: {joint: [] for joint in joints}
            for phase, joints in phase_joints.items()
        }
        dropped = {}
        scoped_out = {}
        used_clips = 0

        for clip_name in clips:
            clip_path = os.path.join(action_dir, clip_name)
            print(f"[{action}] {clip_name} ...", flush=True)
            frames = _process_clip(clip_path)
            segments = segment_action(action, [frame["landmarks"] for frame in frames])
            if not segments:
                print(f"  skipped: no usable segmentation ({len(frames)} frames)")
                continue

            contact = segments["contact"]
            crouch = segments["crouch"]
            allowed = phase_scope.get(f"{action}/{clip_name}")
            for phase, index in (("contact", contact), ("crouch", crouch)):
                if index is None or phase not in samples:
                    continue
                if allowed is not None and phase not in allowed:
                    scoped_out.setdefault(phase, []).append(clip_name)
                    continue
                landmarks = frames[index]["landmarks"]
                for joint in phase_joints[phase]:
                    if _joint_is_offscreen_guess(landmarks, joint):
                        dropped.setdefault(f"{phase}.{joint}", []).append(
                            (clip_name, round(frames[index]["angles"][joint], 1)))
                        continue
                    samples[phase][joint].append(frames[index]["angles"][joint])
            used_clips += 1

        if used_clips == 0:
            continue

        phases = {}
        for phase, joints in phase_joints.items():
            phase_stats = {}
            for joint, values in samples[phase].items():
                if not values:
                    continue
                band = _band(values, joint)
                skipped = dropped.get(f"{phase}.{joint}", [])
                if skipped:
                    # Recorded in the output, not just printed: a band quietly built
                    # from fewer samples than the clip count suggests is exactly how
                    # the 23.6-degree knee survived unnoticed for weeks.
                    band["dropped_offscreen"] = len(skipped)
                    band["clips_available"] = len(values) + len(skipped)
                phase_stats[joint] = band
            if phase_stats:
                phases[phase] = phase_stats

        result["actions"][action] = {"clips": used_clips, "phases": phases}
        print(f"[{action}] calibrated from {used_clips}/{len(clips)} clips")
        for phase, names in sorted(scoped_out.items()):
            print(f"  SCOPED OUT {len(names)} clip(s) from {phase} by "
                  f"dataset/clip_phase_scope.json: {', '.join(sorted(names))}")
        for key, skipped in sorted(dropped.items()):
            phase, joint = key.split(".", 1)
            kept = len(samples[phase][joint])
            listed = ", ".join(f"{name} {angle}"
                               for name, angle in sorted(skipped, key=lambda s: s[1])[:4])
            print(f"  DROPPED {len(skipped)} {key} sample(s) — joint off-screen and "
                  f"unconfident: {listed}{' ...' if len(skipped) > 4 else ''}")
            if kept < 10:
                print(f"  ^ WARNING: {key} now rests on {kept} samples — treat that "
                      f"threshold as weakly grounded")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    print(f"written: {OUTPUT_PATH}")
    sync_result = sync_frontend(ROOT_DIR)
    print(f"synced frontend: {sync_result['buildVersion']}")


if __name__ == "__main__":
    main()
