ACTION_LABELS = {
    "spike": "扣球",
    "block": "攔網",
    "serve": "發球",
    "receive": "接球",
    "set": "托球",
}


ERROR_FEEDBACK = {
    "good": {
        "title": "動作穩定",
        "severity": "low",
        "message": "這段動作沒有偵測到明顯高風險姿勢。",
        "fixes": ["保持全身入鏡，維持熱身與收操。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+warm+up+injury+prevention",
    },
    "elbow_bad": {
        "title": "手肘角度不足",
        "severity": "medium",
        "message": "手肘太彎時，力量容易卡在前臂，擊球或接球平台會變不穩。",
        "fixes": ["擊球前讓手肘抬高並打開。", "接球時手肘伸直，前臂形成穩定平台。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+elbow+arm+position+drill",
    },
    "elbow_not_straight": {
        "title": "手肘沒有完全伸展",
        "severity": "medium",
        "message": "攔網或擊球時手臂沒有打開，容易讓肩膀和手肘代償。",
        "fixes": ["把手肘往上推直。", "用肩胛把手臂送高，不要只伸手腕。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+blocking+arm+extension+drill",
    },
    "hands_not_high": {
        "title": "雙手高度不足",
        "severity": "medium",
        "message": "攔網或托球時手太低，會錯過最佳觸球點，也可能增加肩膀壓力。",
        "fixes": ["提早移動到球下方。", "先讓肩胛上旋，再把手送高。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+blocking+reach+high+drill",
    },
    "shoulder_low": {
        "title": "肩膀或擊球點偏低",
        "severity": "medium",
        "message": "擊球點偏低時，肩膀容易用夾擠姿勢出力，球也比較容易失控。",
        "fixes": ["讓觸球點保持在身體前上方。", "扣球時用非慣用手指向球，幫助拉高擊球點。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+hitting+contact+point+tutorial",
    },
    "knee_bad": {
        "title": "膝蓋角度不理想",
        "severity": "medium",
        "message": "膝蓋太直會吸震不足，過度彎曲或內夾會增加膝蓋負擔。",
        "fixes": ["起跳與落地時讓髖、膝、踝一起彎曲。", "膝蓋朝向腳尖，不要往內倒。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+landing+knee+alignment+drill",
    },
    "knee_too_bent": {
        "title": "膝蓋控制不足",
        "severity": "high",
        "message": "膝蓋彎曲過多或塌陷，可能代表落地吸震不足或髖部沒有一起出力。",
        "fixes": ["落地時髖部往後坐。", "練習安靜落地，讓雙腳平均承重。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+landing+mechanics+knee+alignment",
    },
    "wrist_low": {
        "title": "手腕低於頭部",
        "severity": "medium",
        "message": "托球時手腕太低，球會壓到手腕與拇指，方向也比較不穩。",
        "fixes": ["手提前到額頭前上方。", "用指腹緩衝，不要用掌心或手腕硬頂。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+setting+wrist+forehead+drill",
    },
    "elbow_position_bad": {
        "title": "托球手肘位置不穩",
        "severity": "medium",
        "message": "手肘過開或過夾會讓手腕承受太多力量，也會影響出球方向。",
        "fixes": ["雙手在額頭前上方形成三角形。", "用膝蓋與核心把球送出，手腕只做微調。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+setting+hand+position+elbow",
    },
    "setting_hands_not_detected": {
        "title": "托球手部未完整入鏡",
        "severity": "low",
        "message": "系統沒有同時看到兩隻手，托球手型判斷會不完整。",
        "fixes": ["讓雙手、額頭和球都保持在鏡頭內。", "使用廣角或把手機放遠一點。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+setting+hand+position+tutorial",
    },
    "setting_fingers_closed": {
        "title": "托球手指張開不足",
        "severity": "medium",
        "message": "手指太收時容易用掌心或手腕頂球，球的方向會不穩。",
        "fixes": ["雙手形成三角窗，手指自然張開成杯狀。", "觸球時用指腹緩衝。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+setting+fingers+triangle+hand+shape",
    },
    "setting_hand_spacing_bad": {
        "title": "托球雙手距離不理想",
        "severity": "medium",
        "message": "雙手太近會夾球，太開會失去控制，出球容易飄。",
        "fixes": ["拇指和食指形成穩定三角形。", "托球時雙手保持在額頭前上方。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+setting+hand+spacing+drill",
    },
    "setting_hands_unbalanced": {
        "title": "托球雙手高度不一致",
        "severity": "medium",
        "message": "左右手高度差太大時，球容易旋轉或偏向一側。",
        "fixes": ["雙手同時接球、同時推出。", "靠牆托球，觀察球是否直上直下。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+setting+no+spin+hand+balance",
    },
    "lobster_receive_risk": {
        "title": "吃蘿蔔風險偏高",
        "severity": "high",
        "message": "手臂平台太軟、手肘彎曲或身體沒有降下來，球容易卡在前臂或直接噴飛。",
        "fixes": ["手肘伸直鎖住平台。", "用腳步移到球後方，不要只伸手撈球。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+passing+platform+avoid+shank",
    },
    "receive_platform_unbalanced": {
        "title": "接球平台左右不平",
        "severity": "medium",
        "message": "左右手高度不同會讓平台變斜，球容易偏向一側。",
        "fixes": ["兩手併攏後讓前臂形成平面。", "接球前先停住平台再迎球。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+passing+platform+angle+drill",
    },
    "receive_hands_apart": {
        "title": "接球雙手距離過開",
        "severity": "medium",
        "message": "雙手沒有併好時，平台面積變小，容易吃蘿蔔或讓球亂彈。",
        "fixes": ["接球前先把雙手併好。", "手腕下壓，前臂保持同一平面。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+forearm+passing+hands+together+drill",
    },
    "unknown_action": {
        "title": "姿勢資訊不足",
        "severity": "medium",
        "message": "系統沒有取得足夠的骨架資訊，可能是人沒有完整入鏡或光線不足。",
        "fixes": ["讓全身入鏡。", "保持鏡頭穩定並增加光線。"],
        "video_url": "https://www.youtube.com/results?search_query=volleyball+camera+setup+analysis",
    },
}


SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1}


DEFAULT_ISSUE_DETAIL = {
    "body_part": "全身姿勢",
    "instant_cue": "先讓全身完整入鏡，再重新分析。",
    "practice_drill": "固定手機位置，錄 5 秒正面與側面動作。",
    "why_it_matters": "鏡頭與骨架資訊不足時，系統無法穩定判斷動作問題。",
}


ISSUE_DETAILS = {
    "elbow_bad": {
        "body_part": "手肘與前臂",
        "instant_cue": "手肘打開，前臂不要縮。",
        "practice_drill": "做 10 次慢速擊球或接球平台定格，每次停 1 秒檢查手肘。",
        "why_it_matters": "手肘角度不足會讓力量斷在前臂，球路容易飄或噴飛。",
    },
    "elbow_not_straight": {
        "body_part": "手肘與肩胛",
        "instant_cue": "往上伸直，不要只折手腕。",
        "practice_drill": "靠牆做攔網伸手，確認手肘完全打直再落下。",
        "why_it_matters": "手臂沒有伸展時，肩膀會代償，攔網高度與穩定度都會下降。",
    },
    "hands_not_high": {
        "body_part": "雙手高度",
        "instant_cue": "先到位，再把手送到球上方。",
        "practice_drill": "連續做 8 次原地攔網或托球預備姿勢，定格檢查雙手是否高於額頭。",
        "why_it_matters": "手太低會錯過最佳觸球點，也會讓肩膀用不舒服的角度出力。",
    },
    "shoulder_low": {
        "body_part": "肩膀與擊球點",
        "instant_cue": "擊球點放在身體前上方。",
        "practice_drill": "用非慣用手指球，慢速完成 6 次扣球揮臂。",
        "why_it_matters": "擊球點太低會讓肩膀夾擠，球也比較難往目標方向走。",
    },
    "knee_bad": {
        "body_part": "膝蓋與腳尖",
        "instant_cue": "膝蓋對腳尖，髖膝踝一起彎。",
        "practice_drill": "做 8 次小跳落地，落地後停住 2 秒看膝蓋是否內夾。",
        "why_it_matters": "膝蓋沒有對齊時，落地吸震會變差，也會增加受傷風險。",
    },
    "knee_too_bent": {
        "body_part": "膝蓋與髖部",
        "instant_cue": "髖部往後坐，膝蓋不要塌。",
        "practice_drill": "做 6 次安靜落地，要求雙腳平均承重、落地聲變小。",
        "why_it_matters": "膝蓋過度彎曲或塌陷代表控制不足，容易把壓力集中在膝蓋。",
    },
    "wrist_low": {
        "body_part": "手腕與額頭位置",
        "instant_cue": "手在額頭前上方，不要低於臉。",
        "practice_drill": "靠牆托球 20 下，要求球直上直下且手腕不往下掉。",
        "why_it_matters": "手腕太低會讓球壓到手腕與拇指，出球方向也容易不穩。",
    },
    "elbow_position_bad": {
        "body_part": "托球手肘",
        "instant_cue": "雙手成三角，手肘自然打開。",
        "practice_drill": "托球預備姿勢定格 10 次，確認手肘不過夾也不外張。",
        "why_it_matters": "手肘位置不穩會讓手腕承受太多力量，出球容易旋轉。",
    },
    "setting_hands_not_detected": {
        "body_part": "雙手入鏡",
        "instant_cue": "雙手、額頭和球都放進畫面。",
        "practice_drill": "先錄 3 秒托球預備姿勢，確認兩隻手都被畫出關節點。",
        "why_it_matters": "托球主要靠手型判斷，少一隻手時建議會不完整。",
    },
    "setting_fingers_closed": {
        "body_part": "手指形狀",
        "instant_cue": "手指張開成杯狀，用指腹接球。",
        "practice_drill": "對牆托球 15 下，觀察球是否少旋轉、路線是否直。",
        "why_it_matters": "手指太收會變成用掌心或手腕頂球，容易被判持球或出球不穩。",
    },
    "setting_hand_spacing_bad": {
        "body_part": "雙手距離",
        "instant_cue": "拇指食指留三角窗。",
        "practice_drill": "用慢動作托球 10 次，檢查雙手距離是否固定。",
        "why_it_matters": "雙手太近會夾球，太開會失控，兩者都會讓球飄。",
    },
    "setting_hands_unbalanced": {
        "body_part": "左右手平衡",
        "instant_cue": "兩手同時接、同時推。",
        "practice_drill": "靠牆托球 20 下，要求球不旋轉並回到額頭前。",
        "why_it_matters": "左右手高度不一致會讓球旋轉或偏向一側。",
    },
    "lobster_receive_risk": {
        "body_part": "接球平台",
        "instant_cue": "手肘鎖住，身體到球後面。",
        "practice_drill": "做 10 次低姿勢接球平台定格，確認手肘直、平台平。",
        "why_it_matters": "平台太軟或只伸手撈球時，球很容易吃蘿蔔或直接噴飛。",
    },
    "receive_platform_unbalanced": {
        "body_part": "前臂平台角度",
        "instant_cue": "兩手併好，平台先停住。",
        "practice_drill": "連續 10 次接球預備定格，檢查左右前臂是否同高。",
        "why_it_matters": "平台左右不平會把球導向錯誤方向。",
    },
    "receive_hands_apart": {
        "body_part": "雙手併合",
        "instant_cue": "先併手，再迎球。",
        "practice_drill": "接球前做 10 次併手與手腕下壓，固定平台形狀。",
        "why_it_matters": "雙手太開會讓平台面積變小，球更容易亂彈。",
    },
    "unknown_action": DEFAULT_ISSUE_DETAIL,
}


def feedback_for(error_code):
    payload = dict(ERROR_FEEDBACK.get(error_code, ERROR_FEEDBACK["unknown_action"]))
    detail = ISSUE_DETAILS.get(error_code, DEFAULT_ISSUE_DETAIL)
    payload.update(detail)
    return payload
