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

let visionFilesetPromise;
let poseLandmarkerPromise;
let handLandmarkerPromise;

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

function issuePayload(code, count) {
  return { code, count, ...FEEDBACK[code] };
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
    const timeline = [];
    const angleSums = { elbow: 0, knee: 0 };
    const handSums = { extension: 0, gap: 0 };
    let poseFrames = 0;
    let handFrames = 0;
    let goodFrames = 0;

    for (let index = 0; index < sampleCount; index += 1) {
      const time = sampleCount === 1 ? 0 : (duration * index) / (sampleCount - 1);
      await seekVideo(video, Math.min(time, Math.max(0, duration - 0.001)));
      const timestampMs = index * 1000;
      const poseResult = pose.detectForVideo(video, timestampMs);
      const poseLandmarks = poseResult.landmarks?.[0];
      if (!poseLandmarks) {
        onProgress(`分析影格 ${index + 1}/${sampleCount}`, (index + 1) / sampleCount);
        await new Promise((resolve) => setTimeout(resolve, 0));
        continue;
      }

      const { angles, positions } = poseFeatures(poseLandmarks);
      const handResult = hands ? hands.detectForVideo(video, timestampMs) : null;
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

      if (!frameIssues.length) {
        goodFrames += 1;
      } else {
        for (const code of frameIssues) {
          issueCounts.set(code, (issueCounts.get(code) || 0) + 1);
        }
      }

      if (index === 0 || index === sampleCount - 1 || frameIssues.length) {
        timeline.push({
          frame: index + 1,
          ok: frameIssues.length === 0,
          issues: frameIssues.map((code) => ({
            code,
            title: FEEDBACK[code].title,
            severity: FEEDBACK[code].severity,
          })),
        });
      }
      if (timeline.length > 24) timeline.shift();

      onProgress(`分析影格 ${index + 1}/${sampleCount}`, (index + 1) / sampleCount);
      await new Promise((resolve) => setTimeout(resolve, 0));
    }

    const primaryIssues = [...issueCounts.entries()]
      .map(([code, count]) => issuePayload(code, count))
      .sort(
        (a, b) =>
          SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity] || b.count - a.count,
      )
      .slice(0, 6);
    const actionLabel = ACTION_LABELS[action] || action;
    const score = poseFrames ? Math.round((goodFrames / poseFrames) * 100) : 0;
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
      good_frames: goodFrames,
      score,
      primary_issues: primaryIssues,
      timeline,
      coach_summary: poseFrames
        ? primaryIssues.length
          ? `最需要先修正的是「${primaryIssues[0].title}」。${primaryIssues[0].message}`
          : `${actionLabel}整體看起來穩定，請繼續保持完整熱身與落地控制。`
        : "沒有成功讀到可分析的姿勢。請確認人物全身入鏡、光線足夠。",
      coach_plan: coachPlan(primaryIssues, actionLabel, poseFrames),
      ...modality,
      settings: {
        engine: "mediapipe-web-local",
        power_mode: powerMode,
        sample_count: sampleCount,
        modalities,
      },
    };
  } finally {
    video.removeAttribute("src");
    video.load();
    URL.revokeObjectURL(objectUrl);
  }
}
