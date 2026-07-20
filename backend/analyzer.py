import os
import sys
from collections import Counter

import cv2

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
MAIN_DIR = os.path.join(ROOT_DIR, "main")
for path in (ROOT_DIR, MAIN_DIR):
    if path not in sys.path:
        sys.path.append(path)

from angle.angle import get_angles, get_hand_features, get_positions
from angle.pose_correction import build_pose_compare
from pose.pose import get_pose_from_video

from backend.action_registry import check_action
from backend.feedback import ACTION_LABELS, SEVERITY_ORDER, feedback_for
from backend.modalities import modality_status, normalize_modalities
from backend.reference_evaluation import evaluate_with_reference
from backend.modality_processors import (
    build_modality_processors,
    finalize_modality_results,
)

PRIMARY_ISSUE_LIMIT = 6
MAX_ACTUAL_SEQUENCE_FRAMES = 40
ISSUE_JOINT_STATUS = {
    "elbow_bad": {"elbow": "yellow"},
    "elbow_not_straight": {"elbow": "yellow", "shoulder": "yellow"},
    "hands_not_high": {"shoulder": "yellow", "wrist": "yellow"},
    "shoulder_low": {"shoulder": "yellow"},
    "knee_bad": {"knee": "yellow"},
    "knee_too_bent": {"knee": "red"},
    "wrist_low": {"wrist": "red"},
    "elbow_position_bad": {"elbow": "yellow", "wrist": "yellow"},
    "setting_hands_not_detected": {"wrist": "yellow"},
    "setting_fingers_closed": {"wrist": "yellow"},
    "setting_hand_spacing_bad": {"wrist": "yellow"},
    "setting_hands_unbalanced": {"wrist": "yellow", "shoulder": "yellow"},
    "lobster_receive_risk": {"elbow": "red", "wrist": "yellow"},
    "receive_platform_unbalanced": {"elbow": "yellow", "wrist": "yellow"},
    "receive_hands_apart": {"wrist": "yellow"},
}
STATUS_RANK = {"green": 0, "yellow": 1, "red": 2}


def _normalize_results(results):
    if not isinstance(results, list) or not results:
        return ["unknown_action"]
    return results


def _round_seconds(value):
    if value is None:
        return None
    return round(max(0.0, float(value)), 1)


def _push_issue_time(issue_times, error_code, time_seconds):
    rounded = _round_seconds(time_seconds)
    if rounded is None:
        return
    times = issue_times.setdefault(error_code, [])
    if not any(abs(existing - rounded) < 0.05 for existing in times):
        times.append(rounded)


def _issue_payload(error_code, count=0, time_seconds=None):
    feedback = feedback_for(error_code)
    times = [_round_seconds(value) for value in (time_seconds or [])]
    times = [value for value in times if value is not None][:8]
    return {
        "code": error_code,
        "count": count,
        "time_seconds": times,
        "first_time_seconds": times[0] if times else None,
        "title": feedback["title"],
        "severity": feedback["severity"],
        "message": feedback["message"],
        "fixes": feedback["fixes"],
        "video_url": feedback["video_url"],
        "body_part": feedback["body_part"],
        "instant_cue": feedback["instant_cue"],
        "practice_drill": feedback["practice_drill"],
        "why_it_matters": feedback["why_it_matters"],
    }


def _merge_joint_status(target, next_status):
    for joint, status in (next_status or {}).items():
        if STATUS_RANK.get(status, 0) > STATUS_RANK.get(target.get(joint, "green"), 0):
            target[joint] = status
    return target


def _joint_status_for_issues(issue_codes):
    status = {"elbow": "green", "knee": "green", "shoulder": "green", "wrist": "green"}
    for code in issue_codes or []:
        _merge_joint_status(status, ISSUE_JOINT_STATUS.get(code))
    return status


def _landmarks_to_triples(world_landmarks):
    return [
        [float(point.x), float(point.y), float(getattr(point, "z", 0.0))]
        for point in world_landmarks
    ]


def _issue_caption(issue_codes, time_seconds):
    rounded = _round_seconds(time_seconds)
    prefix = "影片姿勢" if rounded is None else f"第 {rounded:.1f} 秒"
    first_issue = next((feedback_for(code) for code in issue_codes or [] if code not in ("good", "ok")), None)
    if not first_issue:
        return f"{prefix}：影片中的動作"
    return f"{prefix}：{first_issue['title']}，{first_issue['instant_cue']}"


def _remember_actual_frame(frames, world_landmarks, issue_codes, severity, time_seconds, hold):
    if world_landmarks is None or len(world_landmarks) < 33:
        return
    safe_issue_codes = [code for code in (issue_codes or []) if code not in ("good", "ok")]
    frames.append({
        "landmarks": _landmarks_to_triples(world_landmarks),
        "joint_status": _joint_status_for_issues(safe_issue_codes),
        "caption": _issue_caption(safe_issue_codes, time_seconds),
        "severity": severity or 0,
        "time_seconds": _round_seconds(time_seconds),
        "hold": hold,
    })
    if len(frames) > MAX_ACTUAL_SEQUENCE_FRAMES:
        frames.pop(0)


def _video_fps(video_path):
    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        return fps if fps > 1 else 30.0
    finally:
        cap.release()


def _coach_summary(primary_issues, action_label, processed_frames):
    if processed_frames == 0:
        return "沒有成功讀到可分析的姿勢。請確認人物全身入鏡、光線足夠，並重新上傳影片。"

    if not primary_issues:
        return f"{action_label}整體看起來穩定。請繼續保持全身入鏡、完整熱身與落地控制。"

    first = primary_issues[0]
    fixes = "、".join(first["fixes"][:2])
    return f"最需要先修正的是「{first['title']}」。{first['message']} 建議先做：{fixes}。"


def _coach_plan(primary_issues, action_label, processed_frames):
    if processed_frames == 0:
        return {
            "status": "needs_video",
            "headline": "目前沒有足夠骨架可分析",
            "focus": "拍攝設定",
            "reason": "系統沒有讀到穩定的人體姿勢，先改善入鏡、光線與鏡頭穩定度。",
            "next_steps": ["讓全身完整入鏡。", "提高光線並固定手機。", "重新錄一段 5 到 10 秒影片。"],
            "video_url": feedback_for("unknown_action")["video_url"],
        }

    if not primary_issues:
        return {
            "status": "stable",
            "headline": f"{action_label}整體穩定",
            "focus": "維持動作品質",
            "reason": "這段影片沒有出現明顯高風險姿勢。",
            "next_steps": ["維持完整熱身。", "保留全身入鏡。", "用相同角度錄下一次訓練做比較。"],
            "video_url": feedback_for("good")["video_url"],
        }

    first = primary_issues[0]
    next_steps = [first["instant_cue"], first["practice_drill"]]
    next_steps.extend(first["fixes"][:2])
    return {
        "status": "needs_fix",
        "headline": f"先修正：{first['title']}",
        "focus": first["body_part"],
        "reason": first["why_it_matters"],
        "next_steps": next_steps[:4],
        "video_url": first["video_url"],
        "severity": first["severity"],
        "issue_code": first["code"],
    }


def analyze_video(
    video_path,
    action_type,
    process_width=720,
    frame_stride=2,
    max_frames=240,
    modalities=None,
):
    selected_modalities = normalize_modalities(modalities)
    issue_counts = Counter()
    issue_times = {}
    processed_frames = 0
    modality_processors = build_modality_processors(selected_modalities)
    key_frame_landmarks = None
    key_frame_severity = -1
    key_frame_issue_codes = []
    actual_sequence = []
    eval_frames = []
    frame_times = []
    fps = _video_fps(video_path)
    sequence_hold = max(180, min(1200, (frame_stride / fps) * 1000 if fps else 720))

    stream = get_pose_from_video(
        video_path,
        process_width=process_width,
        frame_stride=frame_stride,
        include_image=False,
    )

    for pose_data in stream:
        if processed_frames >= max_frames:
            break

        if len(pose_data) == 4:
            landmarks, world_landmarks, _frame, hand_landmarks = pose_data
        else:
            landmarks, world_landmarks, _frame = pose_data
            hand_landmarks = None

        angles = get_angles(landmarks, world_landmarks)
        positions = get_positions(landmarks, world_landmarks)
        hand_features = get_hand_features(hand_landmarks)
        frame_index = processed_frames + 1
        raw_frame_number = frame_index * frame_stride
        time_seconds = raw_frame_number / fps if fps else None
        frame_context = {
            "frame_index": frame_index,
            "time_seconds": time_seconds,
            "landmarks": landmarks,
            "world_landmarks": world_landmarks,
            "hand_landmarks": hand_landmarks,
            "angles": angles,
            "positions": positions,
            "hand_features": hand_features,
        }
        for processor in modality_processors:
            processor.observe(frame_context)

        eval_frames.append(
            {
                "landmarks": landmarks,
                "world": world_landmarks,
                "angles": angles,
                "positions": positions,
                "hand_features": hand_features,
                "time_seconds": time_seconds,
            }
        )
        frame_times.append(time_seconds)

        results = _normalize_results(
            check_action(action_type, angles, positions, hand_features)
        )

        processed_frames = frame_index

        if results not in (["good"], ["ok"]):
            for result in results:
                if result not in ("good", "ok"):
                    issue_counts[result] += 1
                    _push_issue_time(issue_times, result, time_seconds)

        frame_severity = sum(
            SEVERITY_ORDER.get(result, 0) for result in results if result not in ("good", "ok")
        )
        _remember_actual_frame(
            actual_sequence,
            world_landmarks,
            results,
            frame_severity,
            time_seconds,
            sequence_hold,
        )
        if world_landmarks is not None and frame_severity > key_frame_severity:
            key_frame_severity = frame_severity
            key_frame_landmarks = world_landmarks
            key_frame_issue_codes = [result for result in results if result not in ("good", "ok")]

    # Phase-aware evaluation: judge key moments against calibrated player bands
    # instead of holding every frame of a dynamic action to one static rule.
    phase_eval = evaluate_with_reference(action_type, eval_frames) if eval_frames else None
    phase_analysis = {"mode": "legacy"}
    if phase_eval:
        phase_analysis = phase_eval["report"]
        issue_counts = Counter(phase_eval["issues"])
        contact_index = phase_eval["contact_index"]
        issue_times = {}
        for code, phase_index in phase_eval.get("issue_frames", {}).items():
            if phase_index is not None:
                _push_issue_time(issue_times, code, frame_times[phase_index])
        phase_issues_by_index = {}
        for code, phase_index in phase_eval.get("issue_frames", {}).items():
            if phase_index is not None:
                phase_issues_by_index.setdefault(phase_index, []).append(code)
        actual_sequence = []
        for index, frame in enumerate(eval_frames):
            frame_issue_codes = phase_issues_by_index.get(index, [])
            frame_severity = sum(SEVERITY_ORDER.get(code, 0) for code in frame_issue_codes)
            _remember_actual_frame(
                actual_sequence,
                frame["world"],
                frame_issue_codes,
                frame_severity,
                frame_times[index],
                sequence_hold,
            )
        contact_world = eval_frames[contact_index]["world"]
        if contact_world is not None:
            key_frame_landmarks = contact_world
            key_frame_issue_codes = phase_eval["issues"]

    primary_issues = [
        _issue_payload(code, count, issue_times.get(code))
        for code, count in issue_counts.most_common()
    ]
    primary_issues.sort(
        key=lambda item: (SEVERITY_ORDER.get(item["severity"], 0), item["count"]),
        reverse=True,
    )

    action_label = ACTION_LABELS.get(action_type, action_type)
    pose_compare = build_pose_compare(
        action_type,
        key_frame_landmarks,
        key_frame_issue_codes,
        actual_sequence,
    )

    modality_results = finalize_modality_results(
        modality_processors,
        selected_modalities,
    )

    return {
        "action": action_type,
        "action_label": action_label,
        "processed_frames": processed_frames,
        "primary_issues": primary_issues[:PRIMARY_ISSUE_LIMIT],
        "phase_analysis": phase_analysis,
        "pose_compare": pose_compare,
        "coach_summary": _coach_summary(primary_issues, action_label, processed_frames),
        "coach_plan": _coach_plan(primary_issues, action_label, processed_frames),
        "modalities": modality_status(selected_modalities),
        "modality_results": modality_results,
        "settings": {
            "process_width": process_width,
            "frame_stride": frame_stride,
            "max_frames": max_frames,
            "modalities": selected_modalities,
        },
    }
