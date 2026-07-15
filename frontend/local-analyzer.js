import {
  FilesetResolver,
  HandLandmarker,
  PoseLandmarker,
} from "./vendor/mediapipe/vision_bundle.mjs";

const ACTION_LABELS = {
  spike: "扣球",
  block: "攔網",
  serve: "發球",
  receive: "接球",
  set: "舉球",
};

const SEVERITY_ORDER = { high: 3, medium: 2, low: 1 };

const FEEDBACK = {
  elbow_bad: {
    title: "手肘角度不足",
    severity: "medium",
    message: "手肘太彎時，力量容易卡在前臂，擊球或接球平台會不穩。",
    fixes: ["手肘打開並保持前臂穩定。", "用慢動作練習正確伸展。"],
    body_part: "手肘與前臂",
    instant_cue: "手肘打開，前臂不要縮。",
    practice_drill: "做 10 次慢速揮臂或接球平台定格，每次停 1 秒。",
    why_it_matters: "手肘角度不足會讓力量斷在前臂，球路容易飄或噴飛。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+elbow+arm+position+drill",
  },
  elbow_not_straight: {
    title: "手臂沒有完全伸展",
    severity: "medium",
    message: "攔網時手肘沒有打直，會降低攔網高度與穩定度。",
    fixes: ["把手肘往上推直。", "用肩胛帶動手臂向上。"],
    body_part: "手肘與肩胛",
    instant_cue: "往上伸直，不要只折手腕。",
    practice_drill: "靠牆做 10 次攔網伸手，手肘打直後停住。",
    why_it_matters: "手臂沒有伸展時，肩膀容易代償，攔網高度會下降。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+blocking+arm+extension+drill",
  },
  hands_not_high: {
    title: "雙手高度不足",
    severity: "medium",
    message: "雙手太低會錯過最佳觸球點。",
    fixes: ["先移動到球下方。", "提早把雙手送到額頭上方。"],
    body_part: "雙手高度",
    instant_cue: "先到位，再把手送高。",
    practice_drill: "連續做 8 次原地攔網預備姿勢並定格。",
    why_it_matters: "手太低會錯過最佳觸球點，也會增加肩膀負擔。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+blocking+reach+high+drill",
  },
  shoulder_low: {
    title: "擊球點偏低",
    severity: "medium",
    message: "擊球點偏低時，肩膀容易用不舒服的角度出力。",
    fixes: ["讓觸球點保持在身體前上方。", "用非慣用手指向球。"],
    body_part: "肩膀與擊球點",
    instant_cue: "擊球點放在身體前上方。",
    practice_drill: "用慢動作完成 6 次揮臂，確認手掌高於頭部。",
    why_it_matters: "擊球點太低會讓肩膀夾擠，球也較難控制。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+hitting+contact+point+tutorial",
  },
  knee_bad: {
    title: "膝蓋角度不理想",
    severity: "medium",
    message: "膝蓋控制不足會降低起跳與落地的穩定性。",
    fixes: ["讓髖、膝、踝一起彎曲。", "膝蓋朝向腳尖。"],
    body_part: "膝蓋與腳尖",
    instant_cue: "膝蓋對腳尖，髖膝踝一起彎。",
    practice_drill: "做 8 次小跳落地，落地後停住 2 秒。",
    why_it_matters: "膝蓋沒有對齊時，落地吸震變差並增加受傷風險。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+landing+knee+alignment+drill",
  },
  knee_too_bent: {
    title: "膝蓋控制不足",
    severity: "high",
    message: "膝蓋彎曲過多或塌陷，可能代表髖部沒有一起吸震。",
    fixes: ["髖部往後坐。", "雙腳平均承重並安靜落地。"],
    body_part: "膝蓋與髖部",
    instant_cue: "髖部往後坐，膝蓋不要塌。",
    practice_drill: "做 6 次安靜落地，落地後保持平衡。",
    why_it_matters: "膝蓋塌陷會把壓力集中在膝關節。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+landing+mechanics+knee+alignment",
  },
  wrist_low: {
    title: "手腕低於頭部",
    severity: "medium",
    message: "舉球時手腕太低，出球方向容易不穩。",
    fixes: ["手提前到額頭前上方。", "用指腹緩衝。"],
    body_part: "手腕與額頭位置",
    instant_cue: "手在額頭前上方。",
    practice_drill: "靠牆舉球 20 下，要求球直上直下。",
    why_it_matters: "手腕太低會讓球壓到手腕與拇指。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+wrist+forehead+drill",
  },
  elbow_position_bad: {
    title: "舉球手肘位置不穩",
    severity: "medium",
    message: "手肘過開或過夾會影響出球方向。",
    fixes: ["雙手在額頭前形成三角形。", "用膝蓋與核心送球。"],
    body_part: "舉球手肘",
    instant_cue: "雙手成三角，手肘自然打開。",
    practice_drill: "舉球預備姿勢定格 10 次。",
    why_it_matters: "手肘位置不穩會讓手腕承受太多力量。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+hand+position+elbow",
  },
  setting_hands_not_detected: {
    title: "雙手未完整入鏡",
    severity: "low",
    message: "系統沒有同時看到兩隻手，手型判斷會不完整。",
    fixes: ["讓雙手、額頭和球都在畫面內。", "使用廣角或把手機放遠。"],
    body_part: "雙手入鏡",
    instant_cue: "雙手和額頭都放進畫面。",
    practice_drill: "先錄 3 秒舉球預備姿勢，確認兩手完整入鏡。",
    why_it_matters: "舉球主要靠手型判斷，少一隻手時建議不完整。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+hand+position+tutorial",
  },
  setting_fingers_closed: {
    title: "舉球手指張開不足",
    severity: "medium",
    message: "手指太收容易變成用掌心或手腕頂球。",
    fixes: ["手指自然張開成杯狀。", "用指腹緩衝。"],
    body_part: "手指形狀",
    instant_cue: "手指張開成杯狀。",
    practice_drill: "對牆舉球 15 下，觀察球是否少旋轉。",
    why_it_matters: "手指太收會讓球的方向不穩。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+fingers+triangle+hand+shape",
  },
  setting_hand_spacing_bad: {
    title: "舉球雙手距離不理想",
    severity: "medium",
    message: "雙手太近會夾球，太開會失去控制。",
    fixes: ["拇指和食指形成三角形。", "雙手保持在額頭前上方。"],
    body_part: "雙手距離",
    instant_cue: "拇指食指留三角窗。",
    practice_drill: "慢動作舉球 10 次，保持雙手距離固定。",
    why_it_matters: "雙手距離不穩會讓球偏向一側。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+hand+spacing+drill",
  },
  setting_hands_unbalanced: {
    title: "舉球雙手高度不同",
    severity: "medium",
    message: "左右手高度差太大，球容易旋轉或偏向一側。",
    fixes: ["兩手同時接球、同時推出。", "靠牆練習直上直下。"],
    body_part: "左右手平衡",
    instant_cue: "兩手同時接、同時推。",
    practice_drill: "靠牆舉球 20 下，要求球不旋轉。",
    why_it_matters: "左右手不平衡會讓出球方向不穩。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+no+spin+hand+balance",
  },
  lobster_receive_risk: {
    title: "吃蘿蔔風險偏高",
    severity: "high",
    message: "平台太軟或身體沒有到球後方，球容易卡在前臂或噴飛。",
    fixes: ["手肘伸直鎖住平台。", "用腳步移到球後方。"],
    body_part: "接球平台",
    instant_cue: "手肘鎖住，身體到球後面。",
    practice_drill: "做 10 次低姿勢接球平台定格。",
    why_it_matters: "平台太軟時，球容易吃蘿蔔或直接噴飛。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+passing+platform+avoid+shank",
  },
  receive_platform_unbalanced: {
    title: "接球平台左右不平",
    severity: "medium",
    message: "左右手高度不同會讓平台變斜。",
    fixes: ["兩手併攏形成平面。", "接球前先停住平台。"],
    body_part: "前臂平台角度",
    instant_cue: "兩手併好，平台先停住。",
    practice_drill: "做 10 次平台定格，檢查左右前臂同高。",
    why_it_matters: "平台左右不平會把球導向錯誤方向。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+passing+platform+angle+drill",
  },
  receive_hands_apart: {
    title: "接球雙手距離過開",
    severity: "medium",
    message: "雙手沒有併好，平台面積會變小。",
    fixes: ["接球前先把雙手併好。", "手腕下壓。"],
    body_part: "雙手併合",
    instant_cue: "先併手，再迎球。",
    practice_drill: "做 10 次併手與手腕下壓練習。",
    why_it_matters: "雙手太開會讓球更容易亂彈。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+forearm+passing+hands+together+drill",
  },
};

Object.assign(ACTION_LABELS, {
  spike: "扣球",
  block: "攔網",
  serve: "發球",
  receive: "接球",
  set: "舉球",
});

Object.assign(FEEDBACK, {
  elbow_bad: {
    title: "手肘伸展不足",
    severity: "medium",
    message: "手肘沒有充分打開，力量會卡在前臂，扣球、發球或接球平台都會變得不穩。",
    fixes: ["讓手肘自然伸開，前臂保持穩定。", "先用慢動作練習完整伸展，再逐步加速。"],
    body_part: "手肘與前臂",
    instant_cue: "手肘打開，前臂不要縮。",
    practice_drill: "做 10 次慢速揮臂或接球平台定格，每次停 1 秒確認手肘角度。",
    why_it_matters: "手肘角度不足會讓力量集中在前臂與手腕，容易造成代償與擊球不穩。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+elbow+arm+position+drill",
  },
  elbow_not_straight: {
    title: "手臂沒有向上延伸",
    severity: "medium",
    message: "攔網時手臂若沒有往上延伸，攔網高度與封阻面積都會下降。",
    fixes: ["手掌往上推到最高點。", "肩胛保持上提，不要只靠手腕補高度。"],
    body_part: "手肘與肩膀",
    instant_cue: "手往上穿過球，不要停在臉前。",
    practice_drill: "靠牆做 10 次攔網伸手定格，手肘伸直後停住。",
    why_it_matters: "手臂沒有延伸時，肩膀和手腕容易代償，也會讓攔網封阻角度變小。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+blocking+arm+extension+drill",
  },
  hands_not_high: {
    title: "雙手高度不足",
    severity: "medium",
    message: "雙手太低會錯過最佳觸球點，攔網和舉球都會變被動。",
    fixes: ["雙手提到額頭上方或球的前上方。", "保持胸口打開，肩膀不要塌下來。"],
    body_part: "雙手高度",
    instant_cue: "手高一點，提前準備。",
    practice_drill: "連續 8 次原地攔網或舉球預備姿勢定格。",
    why_it_matters: "手太低會讓肩膀臨時硬拉，增加肩膀和手腕負擔。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+blocking+reach+high+drill",
  },
  shoulder_low: {
    title: "擊球點偏低",
    severity: "medium",
    message: "擊球點太低時，肩膀容易硬拉，球也比較難往下壓。",
    fixes: ["把觸球點放在身體前上方。", "先用非慣用手指向球，幫助身體對位。"],
    body_part: "肩膀與擊球點",
    instant_cue: "球在身體前上方再打。",
    practice_drill: "用慢動作空揮 6 次，確認手掌在頭前上方通過。",
    why_it_matters: "擊球點偏低會讓肩膀承受過多扭轉，也會降低攻擊角度。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+hitting+contact+point+tutorial",
  },
  knee_bad: {
    title: "膝蓋角度不理想",
    severity: "medium",
    message: "膝蓋沒有配合彎曲與伸展，起跳和落地會比較不穩。",
    fixes: ["髖、膝、腳踝一起吸收力量。", "膝蓋方向對齊腳尖，不要內扣。"],
    body_part: "膝蓋與腳踝",
    instant_cue: "膝蓋對腳尖，落地一起彎。",
    practice_drill: "做 8 次小跳落地，落地後停住 2 秒檢查膝蓋方向。",
    why_it_matters: "膝蓋沒有對齊時，落地衝擊會集中在膝關節，增加受傷風險。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+landing+knee+alignment+drill",
  },
  knee_too_bent: {
    title: "膝蓋過度彎曲",
    severity: "high",
    message: "膝蓋彎得太深或內扣，代表落地衝擊沒有被髖和腳踝一起分散。",
    fixes: ["落地時屁股往後坐。", "雙腳與肩同寬，安靜落地。"],
    body_part: "膝蓋與髖部",
    instant_cue: "屁股往後坐，膝蓋不要夾。",
    practice_drill: "做 6 次安靜落地，落地時保持膝蓋對腳尖。",
    why_it_matters: "膝蓋內扣會把壓力集中到韌帶和膝關節，是需要優先修正的受傷風險。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+landing+mechanics+knee+alignment",
  },
  wrist_low: {
    title: "手腕低於額頭",
    severity: "medium",
    message: "舉球時手腕太低，球容易往前飄或旋轉變多。",
    fixes: ["雙手舉到額頭上方。", "手指張開成三角形，手腕放鬆。"],
    body_part: "手腕與額頭位置",
    instant_cue: "雙手在額頭上方接球。",
    practice_drill: "靠牆舉球 20 下，要求球幾乎不旋轉。",
    why_it_matters: "手腕太低會讓手指和手腕承受更多力量，容易讓出球方向不穩。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+wrist+forehead+drill",
  },
  elbow_position_bad: {
    title: "舉球手肘位置不穩",
    severity: "medium",
    message: "手肘太開或太夾都會影響出球方向。",
    fixes: ["雙手在額頭前形成三角形。", "用膝蓋和核心送球，不只靠手臂。"],
    body_part: "舉球手肘",
    instant_cue: "雙手成三角，手肘自然打開。",
    practice_drill: "舉球預備姿勢定格 10 次，再做慢速送球。",
    why_it_matters: "手肘位置不穩會讓肩膀和手腕代償，也會讓球路忽左忽右。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+hand+position+elbow",
  },
  setting_hands_not_detected: {
    title: "雙手沒有完整入鏡",
    severity: "low",
    message: "系統沒有同時看到兩隻手，舉球手型判斷會比較不準。",
    fixes: ["讓手、額頭和球都在畫面中間。", "使用廣角或把手機放遠一點。"],
    body_part: "雙手入鏡",
    instant_cue: "手和額頭都要進畫面。",
    practice_drill: "先錄 3 秒舉球預備姿勢，確認雙手完整入鏡。",
    why_it_matters: "舉球主要靠手型判斷，少一隻手時建議會不完整。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+hand+position+tutorial",
  },
  setting_fingers_closed: {
    title: "舉球手指張開不足",
    severity: "medium",
    message: "手指太閉合會讓球變成用掌心或手腕推出。",
    fixes: ["手指自然張開成碗狀。", "掌心不要碰到球，讓手指緩衝。"],
    body_part: "手指手型",
    instant_cue: "手指張開，像捧一顆球。",
    practice_drill: "原地舉球 15 下，觀察球是否幾乎不旋轉。",
    why_it_matters: "手指沒有張開會讓出球不穩，也容易讓手腕承受過多力量。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+fingers+triangle+hand+shape",
  },
  setting_hand_spacing_bad: {
    title: "舉球雙手距離不理想",
    severity: "medium",
    message: "雙手太近會夾球，太開會讓球不受控。",
    fixes: ["拇指和食指形成三角形。", "雙手保持在額頭前上方。"],
    body_part: "雙手距離",
    instant_cue: "雙手留一顆球的空間。",
    practice_drill: "慢動作舉球 10 次，保持雙手距離固定。",
    why_it_matters: "雙手距離不穩會讓球偏向單邊，影響二傳品質。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+hand+spacing+drill",
  },
  setting_hands_unbalanced: {
    title: "舉球雙手高度不同",
    severity: "medium",
    message: "左右手高度差太大，球容易側旋或偏向一邊。",
    fixes: ["雙手同時接球、同時推出。", "靠牆練習讓球直上直下。"],
    body_part: "左右手平衡",
    instant_cue: "雙手同時接，同時推。",
    practice_drill: "靠牆舉球 20 下，要求球線垂直。",
    why_it_matters: "左右手不平衡會造成出球方向不穩，長期也會讓單側手腕負擔變大。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+setting+no+spin+hand+balance",
  },
  lobster_receive_risk: {
    title: "容易吃蘿蔔的接球姿勢",
    severity: "high",
    message: "平台太軟或身體沒有對準來球，球容易打到前臂邊緣而噴掉。",
    fixes: ["手肘伸直，平台鎖穩。", "用腳步先到球後面，再用身體面向目標。"],
    body_part: "接球平台",
    instant_cue: "平台硬一點，身體站到球後面。",
    practice_drill: "做 10 次低姿勢接球平台定格，確認肩膀、手臂和目標方向一致。",
    why_it_matters: "平台角度不穩會讓球噴向不可控方向，也是初學者最常見的失誤來源。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+passing+platform+avoid+shank",
  },
  receive_platform_unbalanced: {
    title: "接球平台左右不平",
    severity: "medium",
    message: "左右手高度不同會讓平台角度歪掉。",
    fixes: ["雙手扣好，平台保持同一平面。", "接球前先把肩膀面向目標。"],
    body_part: "前臂平台角度",
    instant_cue: "手扣好，平台一整片。",
    practice_drill: "做 10 次平台定格，檢查左右前臂是否同高。",
    why_it_matters: "平台左右不平會讓球偏離目標方向，增加連續失分機率。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+passing+platform+angle+drill",
  },
  receive_hands_apart: {
    title: "接球雙手距離太開",
    severity: "medium",
    message: "雙手沒有扣好，平台面積會變小。",
    fixes: ["接球前先把雙手扣好。", "手腕往下壓，前臂併成平面。"],
    body_part: "雙手扣合",
    instant_cue: "先扣手，再接球。",
    practice_drill: "做 10 次扣手與手腕下壓練習。",
    why_it_matters: "雙手分開會讓球打到手部縫隙，容易造成方向亂飄。",
    video_url: "https://www.youtube.com/results?search_query=volleyball+forearm+passing+hands+together+drill",
  },
});

let visionFilesetPromise;
let poseLandmarkerPromise;
let handLandmarkerPromise;
let lastPoseTimestamp = -1;
let lastHandTimestamp = -1;

const POSE_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 7],
  [0, 4], [4, 5], [5, 6], [6, 8],
  [9, 10], [11, 12], [11, 13], [13, 15],
  [15, 17], [15, 19], [15, 21], [17, 19],
  [12, 14], [14, 16], [16, 18], [16, 20],
  [16, 22], [18, 20], [11, 23], [12, 24],
  [23, 24], [23, 25], [24, 26], [25, 27],
  [26, 28], [27, 29], [28, 30], [29, 31],
  [30, 32], [27, 31], [28, 32],
];

const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20],
  [0, 17],
];

function assetUrl(relativePath) {
  return new URL(relativePath, import.meta.url).href;
}

async function visionFileset() {
  if (!visionFilesetPromise) {
    visionFilesetPromise = FilesetResolver.forVisionTasks(
      assetUrl("./vendor/mediapipe/wasm"),
    );
  }
  return visionFilesetPromise;
}

async function poseLandmarker() {
  if (!poseLandmarkerPromise) {
    poseLandmarkerPromise = visionFileset().then((vision) =>
      PoseLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: assetUrl("./models/pose_landmarker_lite.task"),
          delegate: "CPU",
        },
        runningMode: "VIDEO",
        numPoses: 1,
        minPoseDetectionConfidence: 0.45,
        minPosePresenceConfidence: 0.45,
        minTrackingConfidence: 0.45,
        outputSegmentationMasks: false,
      }),
    );
  }
  return poseLandmarkerPromise;
}

async function handLandmarker() {
  if (!handLandmarkerPromise) {
    handLandmarkerPromise = visionFileset().then((vision) =>
      HandLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: assetUrl("./models/hand_landmarker.task"),
          delegate: "CPU",
        },
        runningMode: "VIDEO",
        numHands: 2,
        minHandDetectionConfidence: 0.4,
        minHandPresenceConfidence: 0.4,
        minTrackingConfidence: 0.4,
      }),
    );
  }
  return handLandmarkerPromise;
}

function nextTimestamp(requested, previous) {
  return Math.max(Math.round(requested), previous + 1);
}

function detectPose(detector, source, requestedTimestamp) {
  const timestamp = nextTimestamp(requestedTimestamp, lastPoseTimestamp);
  lastPoseTimestamp = timestamp;
  return detector.detectForVideo(source, timestamp);
}

function detectHands(detector, source, requestedTimestamp) {
  if (!detector) return null;
  const timestamp = nextTimestamp(requestedTimestamp, lastHandTimestamp);
  lastHandTimestamp = timestamp;
  return detector.detectForVideo(source, timestamp);
}

function average(values) {
  const finite = values.filter(Number.isFinite);
  if (!finite.length) return null;
  return finite.reduce((sum, value) => sum + value, 0) / finite.length;
}

function angleAt(a, b, c) {
  if (!a || !b || !c) return null;
  const ba = [a.x - b.x, a.y - b.y, (a.z || 0) - (b.z || 0)];
  const bc = [c.x - b.x, c.y - b.y, (c.z || 0) - (b.z || 0)];
  const dot = ba[0] * bc[0] + ba[1] * bc[1] + ba[2] * bc[2];
  const magA = Math.hypot(...ba);
  const magC = Math.hypot(...bc);
  if (!magA || !magC) return null;
  const cosine = Math.max(-1, Math.min(1, dot / (magA * magC)));
  return (Math.acos(cosine) * 180) / Math.PI;
}

function poseFeatures(landmarks) {
  const elbow = average([
    angleAt(landmarks[11], landmarks[13], landmarks[15]),
    angleAt(landmarks[12], landmarks[14], landmarks[16]),
  ]);
  const knee = average([
    angleAt(landmarks[23], landmarks[25], landmarks[27]),
    angleAt(landmarks[24], landmarks[26], landmarks[28]),
  ]);
  const shoulder = average([
    angleAt(landmarks[13], landmarks[11], landmarks[23]),
    angleAt(landmarks[14], landmarks[12], landmarks[24]),
  ]);
  return {
    angles: {
      elbow: elbow ?? 180,
      knee: knee ?? 180,
      shoulder: shoulder ?? 180,
    },
    positions: {
      wrist_y: average([landmarks[15]?.y, landmarks[16]?.y]) ?? 1,
      head_y: landmarks[0]?.y ?? 0,
    },
  };
}

function fingerExtension(hand) {
  if (!hand) return null;
  const wrist = hand[0];
  const tips = [8, 12, 16, 20].map((index) => hand[index]);
  const bases = [5, 9, 13, 17].map((index) => hand[index]);
  const tipDistance = average(tips.map((point) => Math.hypot(point.x - wrist.x, point.y - wrist.y)));
  const baseDistance = average(bases.map((point) => Math.hypot(point.x - wrist.x, point.y - wrist.y)));
  if (!tipDistance || !baseDistance) return null;
  return tipDistance / baseDistance;
}

function handFeatures(hands) {
  const detected = hands?.length || 0;
  const centers = (hands || []).map((hand) => {
    const points = [hand[0], hand[5], hand[9], hand[13], hand[17]];
    return {
      x: average(points.map((point) => point.x)),
      y: average(points.map((point) => point.y)),
    };
  });
  return {
    hands_detected: detected,
    finger_extension: average((hands || []).map(fingerExtension)) ?? 0,
    hand_center_gap:
      centers.length >= 2
        ? Math.hypot(centers[0].x - centers[1].x, centers[0].y - centers[1].y)
        : null,
    hands_level_gap:
      centers.length >= 2 ? Math.abs(centers[0].y - centers[1].y) : null,
  };
}

function checkAction(action, angles, positions, hands) {
  const issues = [];
  if (action === "spike") {
    if (angles.elbow < 150) issues.push("elbow_bad");
    if (angles.knee < 150) issues.push("knee_bad");
  } else if (action === "block") {
    if (angles.elbow < 165) issues.push("elbow_not_straight");
    if (angles.shoulder < 150) issues.push("hands_not_high");
    if (angles.knee < 140) issues.push("knee_too_bent");
  } else if (action === "serve") {
    if (angles.elbow < 150) issues.push("elbow_bad");
    if (angles.shoulder < 140) issues.push("shoulder_low");
    if (angles.knee < 150) issues.push("knee_bad");
  } else if (action === "receive") {
    if (angles.elbow < 160) issues.push("elbow_bad");
    if (angles.knee < 140) issues.push("knee_too_bent");
    if (angles.elbow < 170 && angles.shoulder < 95) issues.push("lobster_receive_risk");
    if (hands.hands_detected >= 2) {
      if (hands.hands_level_gap > 0.08) issues.push("receive_platform_unbalanced");
      if (hands.hand_center_gap > 0.24) issues.push("receive_hands_apart");
    }
  } else if (action === "set") {
    if (positions.wrist_y > positions.head_y) issues.push("wrist_low");
    if (angles.elbow < 140 || angles.elbow > 175) issues.push("elbow_position_bad");
    if (angles.shoulder < 140) issues.push("shoulder_low");
    if (hands.hands_detected < 2) {
      issues.push("setting_hands_not_detected");
    } else {
      if (hands.finger_extension < 1.08) issues.push("setting_fingers_closed");
      if (hands.hand_center_gap < 0.06 || hands.hand_center_gap > 0.32) {
        issues.push("setting_hand_spacing_bad");
      }
      if (hands.hands_level_gap > 0.08) issues.push("setting_hands_unbalanced");
    }
  }
  return issues;
}

function normalizeSeconds(value) {
  if (!Number.isFinite(value)) return null;
  return Number(Math.max(0, value).toFixed(1));
}

function pushIssueTime(issueTimes, code, timeSeconds) {
  const normalized = normalizeSeconds(timeSeconds);
  if (normalized === null) return;
  const times = issueTimes.get(code) || [];
  if (!times.some((time) => Math.abs(time - normalized) < 0.05)) {
    times.push(normalized);
  }
  issueTimes.set(code, times);
}

function issuePayload(code, count, timeSeconds = []) {
  const times = (timeSeconds || [])
    .filter(Number.isFinite)
    .map(normalizeSeconds)
    .filter((value) => value !== null)
    .slice(0, 8);
  return {
    code,
    count,
    time_seconds: times,
    first_time_seconds: times.length ? times[0] : null,
    ...FEEDBACK[code],
  };
}

function coachPlan(primaryIssues, actionLabel, processedFrames) {
  if (!processedFrames) {
    return {
      status: "needs_video",
      headline: "目前沒有足夠骨架可分析",
      focus: "拍攝設定",
      reason: "請確認全身入鏡、光線充足，而且影片中有人物動作。",
      next_steps: ["讓全身完整入鏡。", "固定手機並提高光線。", "重新錄製 5 到 10 秒。"],
      video_url: "https://www.youtube.com/results?search_query=volleyball+camera+setup+analysis",
    };
  }
  if (!primaryIssues.length) {
    return {
      status: "stable",
      headline: `${actionLabel}整體穩定`,
      focus: "維持動作品質",
      reason: "取樣影格沒有出現明顯高風險姿勢。",
      next_steps: ["維持完整熱身。", "保留全身入鏡。", "用相同角度持續比較。"],
      video_url: "https://www.youtube.com/results?search_query=volleyball+warm+up+injury+prevention",
    };
  }
  const first = primaryIssues[0];
  return {
    status: "needs_fix",
    headline: `先修正：${first.title}`,
    focus: first.body_part,
    reason: first.why_it_matters,
    next_steps: [first.instant_cue, first.practice_drill, ...first.fixes].slice(0, 4),
    video_url: first.video_url,
    severity: first.severity,
    issue_code: first.code,
  };
}

const JOINT_SPECS = {
  spike: { elbow: { min: 150, code: "elbow_bad" }, knee: { min: 150, code: "knee_bad" } },
  block: {
    elbow: { min: 165, code: "elbow_not_straight" },
    shoulder: { min: 150, code: "hands_not_high" },
    knee: { min: 140, code: "knee_too_bent" },
  },
  serve: {
    elbow: { min: 150, code: "elbow_bad" },
    shoulder: { min: 140, code: "shoulder_low" },
    knee: { min: 150, code: "knee_bad" },
  },
  receive: { elbow: { min: 160, code: "elbow_bad" }, knee: { min: 140, code: "knee_too_bent" } },
  set: {
    elbow: { min: 140, max: 175, code: "elbow_position_bad" },
    shoulder: { min: 140, code: "shoulder_low" },
  },
};

const LEFT_JOINTS = {
  shoulder: 11, elbow: 13, wrist: 15, pinky: 17, index: 19, thumb: 21,
  hip: 23, knee: 25, ankle: 27, heel: 29, foot_index: 31,
};
const RIGHT_JOINTS = {
  shoulder: 12, elbow: 14, wrist: 16, pinky: 18, index: 20, thumb: 22,
  hip: 24, knee: 26, ankle: 28, heel: 30, foot_index: 32,
};

const JOINT_CHAIN = {
  elbow: [["shoulder", "elbow", "wrist"], ["wrist", "pinky", "index", "thumb"]],
  knee: [["hip", "knee", "ankle"], ["ankle", "heel", "foot_index"]],
  shoulder: [["elbow", "shoulder", "hip"], ["elbow", "wrist", "pinky", "index", "thumb"]],
};

const ISSUE_SEVERITY = {
  elbow_bad: "medium",
  elbow_not_straight: "medium",
  hands_not_high: "medium",
  shoulder_low: "medium",
  knee_bad: "medium",
  knee_too_bent: "high",
  elbow_position_bad: "medium",
  wrist_low: "medium",
};
const SEVERITY_TO_STATUS = { high: "red", medium: "yellow", low: "yellow" };
const STATUS_RANK = { green: 0, yellow: 1, red: 2 };
const WRIST_MARGIN = 0.05;
const MAX_ACTUAL_SEQUENCE_FRAMES = 40;
const ISSUE_JOINT_STATUS = {
  elbow_bad: { elbow: "yellow" },
  elbow_not_straight: { elbow: "yellow", shoulder: "yellow" },
  hands_not_high: { shoulder: "yellow", wrist: "yellow" },
  shoulder_low: { shoulder: "yellow" },
  knee_bad: { knee: "yellow" },
  knee_too_bent: { knee: "red" },
  wrist_low: { wrist: "red" },
  elbow_position_bad: { elbow: "yellow", wrist: "yellow" },
  setting_hands_not_detected: { wrist: "yellow" },
  setting_fingers_closed: { wrist: "yellow" },
  setting_hand_spacing_bad: { wrist: "yellow" },
  setting_hands_unbalanced: { wrist: "yellow", shoulder: "yellow" },
  lobster_receive_risk: { elbow: "red", wrist: "yellow" },
  receive_platform_unbalanced: { elbow: "yellow", wrist: "yellow" },
  receive_hands_apart: { wrist: "yellow" },
};

function mergeJointStatus(target, next) {
  for (const [joint, status] of Object.entries(next || {})) {
    if (STATUS_RANK[status] > STATUS_RANK[target[joint] || "green"]) {
      target[joint] = status;
    }
  }
  return target;
}

function jointStatusForIssues(issueCodes) {
  const status = { elbow: "green", knee: "green", shoulder: "green", wrist: "green" };
  for (const code of issueCodes || []) {
    mergeJointStatus(status, ISSUE_JOINT_STATUS[code]);
  }
  return status;
}

function issueCaption(issueCodes) {
  const issue = (issueCodes || []).map((code) => FEEDBACK[code]).find(Boolean);
  if (!issue) return "影片分析到的姿勢影格";
  return `影片錯誤：${issue.title}。${issue.instant_cue}`;
}

function issueCaptionAtTime(issueCodes, timeSeconds = null) {
  const issue = (issueCodes || []).map((code) => FEEDBACK[code]).find(Boolean);
  const normalized = normalizeSeconds(timeSeconds);
  const prefix = normalized === null ? "影片姿勢" : `第 ${normalized.toFixed(1)} 秒`;
  if (!issue) return `${prefix}：影片中的動作`;
  return `${prefix}：${issue.title}，${issue.instant_cue}`;
}

function worldLandmarksToTriples(worldLandmarks) {
  return worldLandmarks.map((point) => [point.x, point.y, point.z || 0]);
}

function rememberActualFrame(frames, worldLandmarks, issueCodes, severity, timeSeconds = null, hold = 720) {
  if (!worldLandmarks || worldLandmarks.length < 33) return;
  const safeIssueCodes = Array.isArray(issueCodes) ? issueCodes : [];
  const normalized = normalizeSeconds(timeSeconds);
  const frame = {
    landmarks: worldLandmarksToTriples(worldLandmarks),
    joint_status: jointStatusForIssues(safeIssueCodes),
    caption: issueCaptionAtTime(safeIssueCodes, normalized),
    severity: severity || 0,
    time_seconds: normalized,
    hold,
  };
  frames.push(frame);
  if (frames.length > MAX_ACTUAL_SEQUENCE_FRAMES) {
    frames.shift();
  }
}

function vecSub(a, b) {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}
function vecAdd(a, b) {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}
function vecCross(a, b) {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}
function vecDot(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}
function vecNorm(a) {
  const length = Math.hypot(a[0], a[1], a[2]);
  if (!length) return [0, 0, 0];
  return [a[0] / length, a[1] / length, a[2] / length];
}
function angleBetween(a, b, c) {
  const ba = vecSub(a, b);
  const bc = vecSub(c, b);
  const la = Math.hypot(...ba);
  const lc = Math.hypot(...bc);
  if (!la || !lc) return 0;
  const cosine = Math.max(-1, Math.min(1, vecDot(ba, bc) / (la * lc)));
  return (Math.acos(cosine) * 180) / Math.PI;
}
function rotatePoint(point, pivot, axis, angleDeg) {
  const angle = (angleDeg * Math.PI) / 180;
  const p = vecSub(point, pivot);
  const cosA = Math.cos(angle);
  const sinA = Math.sin(angle);
  const dot = vecDot(p, axis);
  const cross = vecCross(axis, p);
  const rotated = [
    p[0] * cosA + cross[0] * sinA + axis[0] * dot * (1 - cosA),
    p[1] * cosA + cross[1] * sinA + axis[1] * dot * (1 - cosA),
    p[2] * cosA + cross[2] * sinA + axis[2] * dot * (1 - cosA),
  ];
  return vecAdd(rotated, pivot);
}
function targetAngle(current, spec) {
  if (spec.min !== undefined && current < spec.min) return spec.min;
  if (spec.max !== undefined && current > spec.max) return spec.max;
  return null;
}
function correctJoint(points, sideMap, jointName, target) {
  const [names, distalNames] = JOINT_CHAIN[jointName];
  const aIdx = sideMap[names[0]];
  const bIdx = sideMap[names[1]];
  const cIdx = sideMap[names[2]];
  const a = points[aIdx];
  const b = points[bIdx];
  const c = points[cIdx];
  const current = angleBetween(a, b, c);

  const ba = vecNorm(vecSub(a, b));
  const bc = vecNorm(vecSub(c, b));
  let axis = vecCross(ba, bc);
  let axisLen = Math.hypot(...axis);
  if (axisLen < 1e-6) {
    axis = vecCross(ba, [0, 1, 0]);
    axisLen = Math.hypot(...axis);
    if (axisLen < 1e-6) {
      axis = [1, 0, 0];
      axisLen = 1;
    }
  }
  axis = axis.map((value) => value / axisLen);

  // The triplet endpoint that actually moves depends on which one is in the
  // distal set (e.g. shoulder correction moves the elbow side, not the hip).
  const distalIndices = distalNames.map((name) => sideMap[name]);
  const movingIsC = distalIndices.includes(cIdx);
  const probePoint = movingIsC ? c : a;

  let delta = target - current;
  const resultingAngle = (appliedDelta) => {
    const testPoint = rotatePoint(probePoint, b, axis, appliedDelta);
    return movingIsC ? angleBetween(a, b, testPoint) : angleBetween(testPoint, b, c);
  };
  if (Math.abs(resultingAngle(-delta) - target) < Math.abs(resultingAngle(delta) - target)) {
    delta = -delta;
  }

  for (const idx of distalIndices) {
    points[idx] = rotatePoint(points[idx], b, axis, delta);
  }
}
function correctWristLow(points) {
  const headY = points[0][1];
  const wristY = Math.min(points[LEFT_JOINTS.wrist][1], points[RIGHT_JOINTS.wrist][1]);
  if (wristY <= headY) return false;
  const delta = headY - WRIST_MARGIN - wristY;
  for (const idx of [
    LEFT_JOINTS.wrist, RIGHT_JOINTS.wrist,
    LEFT_JOINTS.pinky, RIGHT_JOINTS.pinky,
    LEFT_JOINTS.index, RIGHT_JOINTS.index,
    LEFT_JOINTS.thumb, RIGHT_JOINTS.thumb,
  ]) {
    points[idx] = [points[idx][0], points[idx][1] + delta, points[idx][2]];
  }
  return true;
}

function buildPoseCompare(action, worldLandmarks, issueCodes = [], actualSequence = []) {
  if ((!worldLandmarks || worldLandmarks.length < 33) && !actualSequence.length) {
    return { available: false };
  }

  const actual = worldLandmarks?.length >= 33
    ? worldLandmarksToTriples(worldLandmarks)
    : actualSequence[0].landmarks;
  const corrected = actual.map((point) => [...point]);
  const spec = JOINT_SPECS[action] || {};
  const jointStatus = {};

  for (const jointName of ["elbow", "knee", "shoulder"]) {
    const jointSpec = spec[jointName];
    let status = "green";
    if (jointSpec) {
      const [names] = JOINT_CHAIN[jointName];
      for (const sideMap of [LEFT_JOINTS, RIGHT_JOINTS]) {
        const a = corrected[sideMap[names[0]]];
        const b = corrected[sideMap[names[1]]];
        const c = corrected[sideMap[names[2]]];
        const current = angleBetween(a, b, c);
        const target = targetAngle(current, jointSpec);
        if (target !== null) {
          correctJoint(corrected, sideMap, jointName, target);
          const sideStatus = SEVERITY_TO_STATUS[ISSUE_SEVERITY[jointSpec.code] || "medium"];
          if (STATUS_RANK[sideStatus] > STATUS_RANK[status]) status = sideStatus;
        }
      }
    }
    jointStatus[jointName] = status;
  }

  mergeJointStatus(jointStatus, jointStatusForIssues(issueCodes));

  let wristStatus = "green";
  if (action === "set" && correctWristLow(corrected)) {
    wristStatus = SEVERITY_TO_STATUS[ISSUE_SEVERITY.wrist_low];
  }
  if (STATUS_RANK[wristStatus] > STATUS_RANK[jointStatus.wrist || "green"]) {
    jointStatus.wrist = wristStatus;
  }
  if (!jointStatus.wrist) jointStatus.wrist = "green";

  return {
    available: true,
    joint_status: jointStatus,
    actual_landmarks: actual,
    corrected_landmarks: corrected,
    actual_sequence: actualSequence,
  };
}

function modalityPayload(poseFrames, handFrames, selectedModalities, angleSums, handSums) {
  const selected = new Set(selectedModalities);
  const modalities = [
    { id: "pose", label: "3D 身體骨架", description: "全身關節與角度", state: "active" },
    { id: "hands", label: "手部關節", description: "手指、手腕與雙手距離", state: "active" },
    { id: "ball", label: "球路追蹤", description: "保留擴充", state: "reserved" },
    { id: "audio", label: "聲音節奏", description: "保留擴充", state: "reserved" },
    { id: "wearable", label: "穿戴感測", description: "保留擴充", state: "reserved" },
    { id: "coach_text", label: "教練備註", description: "保留擴充", state: "reserved" },
  ].map((item) => ({ ...item, requested: selected.has(item.id) }));
  return {
    modalities,
    modality_results: {
      pose: {
        frames_with_pose: poseFrames,
        average_elbow_angle: poseFrames ? Math.round(angleSums.elbow / poseFrames) : null,
        average_knee_angle: poseFrames ? Math.round(angleSums.knee / poseFrames) : null,
      },
      hands: {
        frames_with_hands: handFrames,
        average_finger_extension: handFrames
          ? Number((handSums.extension / handFrames).toFixed(2))
          : null,
        average_hand_gap: handFrames
          ? Number((handSums.gap / handFrames).toFixed(2))
          : null,
      },
      reserved: {
        ball: "球路模型預留",
        audio: "聲音節奏模型預留",
        wearable: "穿戴裝置模型預留",
        coach_text: "教練文字模型預留",
      },
    },
  };
}

function waitForEvent(target, eventName) {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      target.removeEventListener(eventName, onDone);
      target.removeEventListener("error", onError);
    };
    const onDone = () => {
      cleanup();
      resolve();
    };
    const onError = () => {
      cleanup();
      reject(new Error("瀏覽器無法讀取這個影片格式。"));
    };
    target.addEventListener(eventName, onDone, { once: true });
    target.addEventListener("error", onError, { once: true });
  });
}

async function seekVideo(video, time) {
  if (Math.abs(video.currentTime - time) < 0.005) return;
  const ready = waitForEvent(video, "seeked");
  video.currentTime = time;
  await ready;
}

function sampleCountForMode(mode) {
  if (mode === "mobile") return 16;
  if (mode === "quality") return 40;
  return 26;
}

function analysisResult({
  action,
  powerMode,
  modalities,
  sampleCount,
  issueCounts,
  issueTimes = new Map(),
  poseCompare,
  angleSums,
  handSums,
  poseFrames,
  handFrames,
  engine = "mediapipe-web-local",
}) {
  const primaryIssues = [...issueCounts.entries()]
    .map(([code, count]) => issuePayload(code, count, issueTimes.get(code)))
    .sort(
      (a, b) =>
        SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity] || b.count - a.count,
    )
    .slice(0, 6);
  const actionLabel = ACTION_LABELS[action] || action;
  const modality = modalityPayload(
    poseFrames,
    handFrames,
    modalities,
    angleSums,
    handSums,
  );

  return {
    action,
    action_label: actionLabel,
    processed_frames: poseFrames,
    primary_issues: primaryIssues,
    pose_compare: poseCompare || { available: false },
    coach_summary: poseFrames
      ? primaryIssues.length
        ? `最需要先修正的是「${primaryIssues[0].title}」。${primaryIssues[0].message}`
        : `${actionLabel}整體看起來穩定，請繼續保持完整熱身與落地控制。`
      : "沒有成功讀到可分析的姿勢。請確認人物全身入鏡、光線足夠。",
    coach_plan: coachPlan(primaryIssues, actionLabel, poseFrames),
    ...modality,
    settings: {
      engine,
      power_mode: powerMode,
      sample_count: sampleCount,
      modalities,
    },
  };
}

function modalityPayload(poseFrames, handFrames, selectedModalities, angleSums, handSums) {
  const selected = new Set(selectedModalities);
  const modalities = [
    { id: "pose", label: "3D 身體骨架", description: "全身關節、軀幹與角度", state: "active" },
    { id: "hands", label: "手部關節", description: "手指、手腕與雙手距離", state: "active" },
    { id: "ball", label: "球路追蹤", description: "保留給後續多模態分析", state: "reserved" },
    { id: "audio", label: "聲音節奏", description: "保留給擊球聲與節奏分析", state: "reserved" },
    { id: "wearable", label: "穿戴感測", description: "保留給 IMU 或手環資料", state: "reserved" },
    { id: "coach_text", label: "教練備註", description: "保留給人工標註與文字回饋", state: "reserved" },
  ].map((item) => ({ ...item, requested: selected.has(item.id) }));

  return {
    modalities,
    modality_results: {
      pose: {
        frames_with_pose: poseFrames,
        average_elbow_angle: poseFrames ? Math.round(angleSums.elbow / poseFrames) : null,
        average_knee_angle: poseFrames ? Math.round(angleSums.knee / poseFrames) : null,
      },
      hands: {
        frames_with_hands: handFrames,
        average_finger_extension: handFrames
          ? Number((handSums.extension / handFrames).toFixed(2))
          : null,
        average_hand_gap: handFrames
          ? Number((handSums.gap / handFrames).toFixed(2))
          : null,
      },
      reserved: {
        ball: "球路追蹤欄位已預留。",
        audio: "聲音節奏欄位已預留。",
        wearable: "穿戴感測欄位已預留。",
        coach_text: "教練備註欄位已預留。",
      },
    },
  };
}

function coachPlan(primaryIssues, actionLabel, processedFrames) {
  if (!processedFrames) {
    return {
      status: "needs_video",
      headline: "目前沒有足夠姿勢可分析",
      focus: "拍攝設定",
      reason: "請確認全身、雙手與落地動作完整入鏡，廣角鏡頭可保留腳步與手部軌跡。",
      next_steps: ["讓全身從頭到腳都入鏡。", "錄 5 到 10 秒完整動作。", "手機放穩並避免逆光。"],
      video_url: "https://www.youtube.com/results?search_query=volleyball+camera+setup+analysis",
    };
  }

  if (!primaryIssues.length) {
    return {
      status: "stable",
      headline: `${actionLabel}整體穩定`,
      focus: "維持動作品質",
      reason: "這段影片沒有出現明顯高風險動作，建議繼續用不同角度確認腳步、手部與落地。",
      next_steps: ["保持完整熱身。", "再錄正面與側面各一段。", "逐步提高速度，不要一次加太快。"],
      video_url: "https://www.youtube.com/results?search_query=volleyball+warm+up+injury+prevention",
    };
  }

  const first = primaryIssues[0];
  return {
    status: "needs_fix",
    headline: `優先修正：${first.title}`,
    focus: first.body_part,
    reason: first.why_it_matters,
    next_steps: [first.instant_cue, first.practice_drill, ...first.fixes].slice(0, 4),
    video_url: first.video_url,
    severity: first.severity,
    issue_code: first.code,
  };
}

function analysisResult({
  action,
  powerMode,
  modalities,
  sampleCount,
  issueCounts,
  issueTimes = new Map(),
  poseCompare,
  angleSums,
  handSums,
  poseFrames,
  handFrames,
  engine = "mediapipe-web-local",
}) {
  const primaryIssues = [...issueCounts.entries()]
    .map(([code, count]) => issuePayload(code, count, issueTimes.get(code)))
    .sort(
      (a, b) =>
        SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity] || b.count - a.count,
    )
    .slice(0, 6);
  const actionLabel = ACTION_LABELS[action] || action;
  const modality = modalityPayload(
    poseFrames,
    handFrames,
    modalities,
    angleSums,
    handSums,
  );

  return {
    action,
    action_label: actionLabel,
    processed_frames: poseFrames,
    primary_issues: primaryIssues,
    pose_compare: poseCompare || { available: false },
    coach_summary: poseFrames
      ? primaryIssues.length
        ? `最需要先修正的是「${primaryIssues[0].title}」。${primaryIssues[0].message}`
        : `${actionLabel}整體看起來穩定，請繼續保持完整熱身、腳步節奏與落地控制。`
      : "沒有讀到可分析的姿勢。請確認全身、雙手與落地動作完整入鏡。",
    coach_plan: coachPlan(primaryIssues, actionLabel, poseFrames),
    ...modality,
    settings: {
      engine,
      power_mode: powerMode,
      sample_count: sampleCount,
      modalities,
    },
  };
}

export async function analyzeVideoLocally({
  file,
  action,
  powerMode = "mobile",
  modalities = ["pose", "hands"],
  onProgress = () => {},
}) {
  const objectUrl = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.src = objectUrl;
  video.muted = true;
  video.playsInline = true;
  video.preload = "auto";

  try {
    if (video.readyState < 1) await waitForEvent(video, "loadedmetadata");
    const duration = Math.min(Number.isFinite(video.duration) ? video.duration : 0, 12);
    if (!duration) throw new Error("影片沒有可分析的時間長度。");

    onProgress("載入手機端姿勢模型", 0);
    const pose = await poseLandmarker();
    const needsHands = modalities.includes("hands");
    const hands = needsHands ? await handLandmarker() : null;

    const requestedSamples = sampleCountForMode(powerMode);
    const sampleCount = Math.max(1, Math.min(requestedSamples, Math.ceil(duration * 5)));
    const issueCounts = new Map();
    const issueTimes = new Map();
    const angleSums = { elbow: 0, knee: 0 };
    const handSums = { extension: 0, gap: 0 };
    let poseFrames = 0;
    let handFrames = 0;
    let keyFrameLandmarks = null;
    let keyFrameIssueCodes = [];
    let keyFrameSeverity = -1;
    const actualSequence = [];
    const sequenceHold = sampleCount > 1
      ? Math.max(180, Math.min(1200, (duration / (sampleCount - 1)) * 1000))
      : 720;

    for (let index = 0; index < sampleCount; index += 1) {
      const time = sampleCount === 1 ? 0 : (duration * index) / (sampleCount - 1);
      const sampleTime = Math.min(time, Math.max(0, duration - 0.001));
      await seekVideo(video, sampleTime);
      const timestampMs = performance.now();
      const poseResult = detectPose(pose, video, timestampMs);
      const poseLandmarks = poseResult.landmarks?.[0];
      if (!poseLandmarks) {
        onProgress(`分析影格 ${index + 1}/${sampleCount}`, (index + 1) / sampleCount);
        await new Promise((resolve) => setTimeout(resolve, 0));
        continue;
      }

      const { angles, positions } = poseFeatures(poseLandmarks);
      const handResult = detectHands(hands, video, timestampMs);
      const features = handFeatures(handResult?.landmarks || []);
      const frameIssues = checkAction(action, angles, positions, features);

      poseFrames += 1;
      angleSums.elbow += angles.elbow;
      angleSums.knee += angles.knee;
      if (features.hands_detected > 0) {
        handFrames += 1;
        handSums.extension += features.finger_extension || 0;
        handSums.gap += features.hand_center_gap || 0;
      }

      for (const code of frameIssues) {
        issueCounts.set(code, (issueCounts.get(code) || 0) + 1);
        pushIssueTime(issueTimes, code, sampleTime);
      }

      const worldLandmarks = poseResult.worldLandmarks?.[0];
      const frameSeverity = frameIssues.reduce(
        (sum, code) => sum + (SEVERITY_ORDER[FEEDBACK[code]?.severity] || 0),
        0,
      );
      rememberActualFrame(actualSequence, worldLandmarks, frameIssues, frameSeverity, sampleTime, sequenceHold);
      if (worldLandmarks && frameSeverity > keyFrameSeverity) {
        keyFrameSeverity = frameSeverity;
        keyFrameLandmarks = worldLandmarks;
        keyFrameIssueCodes = frameIssues;
      }

      onProgress(`分析影格 ${index + 1}/${sampleCount}`, (index + 1) / sampleCount);
      await new Promise((resolve) => setTimeout(resolve, 0));
    }

    return analysisResult({
      action,
      powerMode,
      modalities,
      sampleCount,
      issueCounts,
      issueTimes,
      poseCompare: buildPoseCompare(action, keyFrameLandmarks, keyFrameIssueCodes, actualSequence),
      angleSums,
      handSums,
      poseFrames,
      handFrames,
    });
  } finally {
    video.removeAttribute("src");
    video.load();
    URL.revokeObjectURL(objectUrl);
  }
}

function imageMaxDimension(powerMode) {
  if (powerMode === "quality") return 1280;
  if (powerMode === "balanced") return 960;
  return 720;
}

async function loadImage(file) {
  const objectUrl = URL.createObjectURL(file);
  const image = document.createElement("img");
  image.src = objectUrl;
  image.decoding = "async";
  try {
    if (typeof image.decode === "function") {
      await image.decode();
    } else {
      await waitForEvent(image, "load");
    }
    return { image, objectUrl };
  } catch (error) {
    URL.revokeObjectURL(objectUrl);
    throw error;
  }
}

export async function analyzeImageLocally({
  file,
  action,
  powerMode = "mobile",
  modalities = ["pose", "hands"],
  onProgress = () => {},
}) {
  const { image, objectUrl } = await loadImage(file);
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d", { alpha: false });

  try {
    const sourceWidth = image.naturalWidth || image.width;
    const sourceHeight = image.naturalHeight || image.height;
    if (!sourceWidth || !sourceHeight || !context) {
      throw new Error("無法讀取這張照片，請改用 JPG 或 PNG 後再試。");
    }

    const maxDimension = imageMaxDimension(powerMode);
    const scale = Math.min(1, maxDimension / Math.max(sourceWidth, sourceHeight));
    canvas.width = Math.max(1, Math.round(sourceWidth * scale));
    canvas.height = Math.max(1, Math.round(sourceHeight * scale));
    context.drawImage(image, 0, 0, canvas.width, canvas.height);

    onProgress("載入手機端姿勢模型", 0);
    const pose = await poseLandmarker();
    const needsHands = modalities.includes("hands");
    const hands = needsHands ? await handLandmarker() : null;
    const requestedTimestamp = performance.now();
    const poseResult = detectPose(pose, canvas, requestedTimestamp);
    const poseLandmarks = poseResult.landmarks?.[0];
    const issueCounts = new Map();
    const issueTimes = new Map();
    const angleSums = { elbow: 0, knee: 0 };
    const handSums = { extension: 0, gap: 0 };
    let poseFrames = 0;
    let handFrames = 0;
    let poseCompare = { available: false };

    if (poseLandmarks) {
      const { angles, positions } = poseFeatures(poseLandmarks);
      const handResult = detectHands(hands, canvas, requestedTimestamp);
      const features = handFeatures(handResult?.landmarks || []);
      const frameIssues = checkAction(action, angles, positions, features);

      poseFrames = 1;
      angleSums.elbow = angles.elbow;
      angleSums.knee = angles.knee;
      if (features.hands_detected > 0) {
        handFrames = 1;
        handSums.extension = features.finger_extension || 0;
        handSums.gap = features.hand_center_gap || 0;
      }
      for (const code of frameIssues) {
        issueCounts.set(code, 1);
        pushIssueTime(issueTimes, code, 0);
      }
      const actualSequence = [];
      const worldLandmarks = poseResult.worldLandmarks?.[0];
      const frameSeverity = frameIssues.reduce(
        (sum, code) => sum + (SEVERITY_ORDER[FEEDBACK[code]?.severity] || 0),
        0,
      );
      rememberActualFrame(actualSequence, worldLandmarks, frameIssues, frameSeverity, 0, 720);
      poseCompare = buildPoseCompare(action, worldLandmarks, frameIssues, actualSequence);
    }

    onProgress("照片分析完成", 1);
    return analysisResult({
      action,
      powerMode,
      modalities,
      sampleCount: 1,
      issueCounts,
      issueTimes,
      poseCompare,
      angleSums,
      handSums,
      poseFrames,
      handFrames,
      engine: "mediapipe-web-local-image",
    });
  } finally {
    context?.clearRect(0, 0, canvas.width, canvas.height);
    canvas.width = 1;
    canvas.height = 1;
    image.removeAttribute("src");
    URL.revokeObjectURL(objectUrl);
  }
}

export function analyzeMediaLocally(options) {
  if (options.file?.type?.startsWith("image/")) {
    return analyzeImageLocally(options);
  }
  return analyzeVideoLocally(options);
}

const REALTIME_INTERVALS = {
  mobile: 360,
  balanced: 240,
  quality: 150,
};

function drawLandmarks(context, landmarks, connections, color, pointColor, width) {
  if (!landmarks?.length) return;
  context.lineCap = "round";
  context.lineJoin = "round";
  context.lineWidth = width;
  context.strokeStyle = color;
  for (const [from, to] of connections) {
    const first = landmarks[from];
    const second = landmarks[to];
    if (!first || !second) continue;
    context.beginPath();
    context.moveTo(first.x * context.canvas.width, first.y * context.canvas.height);
    context.lineTo(second.x * context.canvas.width, second.y * context.canvas.height);
    context.stroke();
  }
  context.fillStyle = pointColor;
  for (const point of landmarks) {
    context.beginPath();
    context.arc(
      point.x * context.canvas.width,
      point.y * context.canvas.height,
      Math.max(2.5, width * 0.85),
      0,
      Math.PI * 2,
    );
    context.fill();
  }
}

function drawRealtimeOverlay(canvas, video, poseLandmarks, handLandmarks) {
  const width = video.videoWidth || 1;
  const height = video.videoHeight || 1;
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, width, height);
  const lineWidth = Math.max(2, Math.round(width / 360));
  drawLandmarks(context, poseLandmarks, POSE_CONNECTIONS, "#ffffff", "#ed5d38", lineWidth);
  for (const hand of handLandmarks || []) {
    drawLandmarks(context, hand, HAND_CONNECTIONS, "#ffd34f", "#1bd6a0", lineWidth);
  }
}

function realtimeIssuePayload(history) {
  const counts = new Map();
  for (const codes of history) {
    for (const code of codes) counts.set(code, (counts.get(code) || 0) + 1);
  }
  return [...counts.entries()]
    .map(([code, count]) => issuePayload(code, count))
    .sort(
      (a, b) =>
        SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity] || b.count - a.count,
    )
    .slice(0, 3);
}

export async function startRealtimeAnalysis({
  video,
  canvas,
  getAction,
  getModalities = () => ["pose", "hands"],
  getPowerMode = () => "mobile",
  onUpdate = () => {},
}) {
  const pose = await poseLandmarker();
  const needsHands = getModalities().includes("hands");
  const hands = needsHands ? await handLandmarker() : null;
  const issueHistory = [];
  let animationFrame = 0;
  let stopped = false;
  let lastProcessedAt = 0;
  let frameCounter = 0;
  let fpsWindowStart = performance.now();
  let measuredFps = 0;

  const processFrame = (now) => {
    if (stopped) return;
    animationFrame = requestAnimationFrame(processFrame);
    const interval = REALTIME_INTERVALS[getPowerMode()] || REALTIME_INTERVALS.mobile;
    if (video.readyState < 2 || now - lastProcessedAt < interval) return;
    lastProcessedAt = now;

    const poseResult = detectPose(pose, video, now);
    const poseLandmarks = poseResult.landmarks?.[0];
    if (!poseLandmarks) {
      issueHistory.length = 0;
      drawRealtimeOverlay(canvas, video, null, []);
      onUpdate({ poseDetected: false, issues: [], fps: measuredFps });
      return;
    }

    const modalities = getModalities();
    const handResult = modalities.includes("hands") ? detectHands(hands, video, now) : null;
    const handLandmarks = handResult?.landmarks || [];
    const { angles, positions } = poseFeatures(poseLandmarks);
    const handData = handFeatures(handLandmarks);
    const frameIssues = checkAction(getAction(), angles, positions, handData);
    issueHistory.push(frameIssues);
    if (issueHistory.length > 5) issueHistory.shift();

    frameCounter += 1;
    if (now - fpsWindowStart >= 2000) {
      measuredFps = Math.round((frameCounter * 1000) / (now - fpsWindowStart));
      frameCounter = 0;
      fpsWindowStart = now;
    }

    drawRealtimeOverlay(canvas, video, poseLandmarks, handLandmarks);
    const currentIssues = realtimeIssuePayload(issueHistory);
    onUpdate({
      poseDetected: true,
      issues: currentIssues,
      cue: currentIssues[0]?.instant_cue || "動作穩定，保持全身與手腳完整入鏡。",
      angles: {
        elbow: Math.round(angles.elbow),
        knee: Math.round(angles.knee),
        shoulder: Math.round(angles.shoulder),
      },
      handsDetected: handData.hands_detected,
      fps: measuredFps,
    });
  };

  animationFrame = requestAnimationFrame(processFrame);
  return {
    stop() {
      stopped = true;
      cancelAnimationFrame(animationFrame);
      issueHistory.length = 0;
      const context = canvas.getContext("2d");
      context.clearRect(0, 0, canvas.width, canvas.height);
      canvas.width = 1;
      canvas.height = 1;
    },
  };
}
