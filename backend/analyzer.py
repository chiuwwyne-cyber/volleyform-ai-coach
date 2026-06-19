import os
import sys
from collections import Counter

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
MAIN_DIR = os.path.join(ROOT_DIR, "main")
for path in (ROOT_DIR, MAIN_DIR):
    if path not in sys.path:
        sys.path.append(path)

from angle.angle import get_angles, get_hand_features, get_positions
from pose.pose import get_pose_from_video

from backend.action_registry import check_action
from backend.feedback import ACTION_LABELS, SEVERITY_ORDER, feedback_for
from backend.modalities import modality_status, normalize_modalities
from backend.modality_processors import (
    build_modality_processors,
    finalize_modality_results,
)

TIMELINE_LIMIT = 24
PRIMARY_ISSUE_LIMIT = 6


def _normalize_results(results):
    if not isinstance(results, list) or not results:
        return ["unknown_action"]
    return results


def _issue_payload(error_code, count=0):
    feedback = feedback_for(error_code)
    return {
        "code": error_code,
        "count": count,
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


def _timeline_issue_payload(error_code):
    feedback = feedback_for(error_code)
    return {
        "code": error_code,
        "title": feedback["title"],
        "severity": feedback["severity"],
    }


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
    timeline = []
    processed_frames = 0
    good_frames = 0
    modality_processors = build_modality_processors(selected_modalities)

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
        frame_context = {
            "frame_index": frame_index,
            "landmarks": landmarks,
            "world_landmarks": world_landmarks,
            "hand_landmarks": hand_landmarks,
            "angles": angles,
            "positions": positions,
            "hand_features": hand_features,
        }
        for processor in modality_processors:
            processor.observe(frame_context)

        results = _normalize_results(
            check_action(action_type, angles, positions, hand_features)
        )

        processed_frames = frame_index

        if results in (["good"], ["ok"]):
            good_frames += 1
        else:
            for result in results:
                if result not in ("good", "ok"):
                    issue_counts[result] += 1

        if processed_frames == 1 or processed_frames % 8 == 0 or results not in (["good"], ["ok"]):
            timeline.append({
                "frame": processed_frames,
                "issues": [
                    _timeline_issue_payload(result)
                    for result in results
                    if result not in ("good", "ok")
                ],
                "ok": results in (["good"], ["ok"]),
            })

        if len(timeline) > TIMELINE_LIMIT:
            timeline.pop(0)

    primary_issues = [
        _issue_payload(code, count)
        for code, count in issue_counts.most_common()
    ]
    primary_issues.sort(
        key=lambda item: (SEVERITY_ORDER.get(item["severity"], 0), item["count"]),
        reverse=True,
    )

    action_label = ACTION_LABELS.get(action_type, action_type)
    score = round((good_frames / processed_frames) * 100) if processed_frames else 0

    modality_results = finalize_modality_results(
        modality_processors,
        selected_modalities,
    )

    return {
        "action": action_type,
        "action_label": action_label,
        "processed_frames": processed_frames,
        "good_frames": good_frames,
        "score": score,
        "primary_issues": primary_issues[:PRIMARY_ISSUE_LIMIT],
        "timeline": timeline,
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
