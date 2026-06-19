# report_generator.py

from injury_database import ERROR_FEEDBACK


def _dedupe(items):
    seen = set()
    output = []
    for item in items:
        key = item.get("name_en") or item.get("name_zh")
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _severity_rank(level):
    if "高" in level:
        return 3
    if "中" in level:
        return 2
    return 1


def generate_detection_report(results, injury_db, error_to_injury):
    if not results or results == ["good"] or results == ["ok"]:
        return [{
            "status": "good",
            "title": "動作看起來穩定",
            "message": "目前沒有偵測到明顯高風險姿勢。請繼續保持熱身、收操和足夠休息。",
            "priority": "低",
            "fix_now": [
                "維持全身入鏡，讓系統可以穩定追蹤肩、肘、髖、膝、踝。",
                "若已有疼痛或麻木，即使姿勢判定正常，也建議暫停並諮詢物理治療師或醫師。",
            ],
            "drills": [],
            "injuries": [],
            "video_keywords": "volleyball warm up shoulder knee injury prevention",
            "video_url": "https://www.youtube.com/results?search_query=volleyball+warm+up+shoulder+knee+injury+prevention",
        }]

    report = []

    for result in results:
        if result in ["good", "ok"]:
            continue

        feedback = ERROR_FEEDBACK.get(result, {
            "title": "偵測到需要修正的動作",
            "risk_level": "中",
            "what_it_means": "目前姿勢與建議範圍不完全一致。",
            "fix_now": ["放慢動作重新做一次，確認全身都有入鏡。"],
            "drills": ["先做低強度分解動作，再回到完整動作。"],
            "video_keywords": "volleyball technique correction drill",
            "video_url": "https://www.youtube.com/results?search_query=volleyball+technique+correction+drill",
        })

        injuries = []
        for injury_key in error_to_injury.get(result, []):
            info = injury_db.get(injury_key)
            if info:
                injuries.append({
                    "position": info["position"],
                    "name_zh": info["name_zh"],
                    "name_en": info["name_en"],
                    "cause_plain": info["cause_plain"],
                    "advice": info["advice"],
                    "source": info["source"],
                })

        report.append({
            "status": "needs_attention",
            "error_code": result,
            "title": feedback["title"],
            "priority": feedback["risk_level"],
            "priority_rank": _severity_rank(feedback["risk_level"]),
            "message": feedback["what_it_means"],
            "fix_now": feedback["fix_now"],
            "drills": feedback["drills"],
            "video_keywords": feedback["video_keywords"],
            "video_url": feedback["video_url"],
            "injuries": _dedupe(injuries),
        })

    report.sort(key=lambda item: item.get("priority_rank", 0), reverse=True)
    return report


def format_report_text(report, action_name=""):
    lines = []
    header = "智慧傷害風險與修正建議"
    if action_name:
        header += f" - {action_name}"
    lines.append(header)
    lines.append("=" * len(header))

    for idx, item in enumerate(report, start=1):
        lines.append(f"{idx}. {item.get('title', '動作建議')}｜風險：{item.get('priority', '中')}")
        lines.append(f"   判讀：{item.get('message', '')}")

        fixes = item.get("fix_now", [])
        if fixes:
            lines.append("   立即建議：")
            for fix in fixes:
                lines.append(f"   - {fix}")

        drills = item.get("drills", [])
        if drills:
            lines.append("   訓練：")
            for drill in drills:
                lines.append(f"   - {drill}")

        injuries = item.get("injuries", [])
        if injuries:
            names = "、".join(f"{injury['name_zh']}({injury['position']})" for injury in injuries)
            lines.append(f"   可能相關風險：{names}")

        if item.get("video_url"):
            lines.append(f"   影片搜尋：{item['video_url']}")

        lines.append("")

    lines.append("提醒：本系統為動作風險提示，不取代醫師或物理治療師診斷。")
    return "\n".join(lines)
