import * as THREE from "./vendor/three/three.module.min.js";

// ---------------------------------------------------------------------------
// Shared vector / rotation math (mirrors angle/pose_correction.py so the same
// joint-angle targets produce the same corrected pose in every runtime).
// ---------------------------------------------------------------------------

function vecSub(a, b) {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}
function vecAdd(a, b) {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}
function vecCross(a, b) {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}
function vecDot(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}
function vecNorm(a) {
  const len = Math.hypot(a[0], a[1], a[2]);
  return len ? [a[0] / len, a[1] / len, a[2] / len] : [0, 0, 0];
}
function angleBetween(a, b, c) {
  const ba = vecNorm(vecSub(a, b));
  const bc = vecNorm(vecSub(c, b));
  const cosine = Math.max(-1, Math.min(1, vecDot(ba, bc)));
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
function rotateToAngle(points, aIdx, bIdx, cIdx, distalIdxs, targetDeg) {
  const a = points[aIdx];
  const b = points[bIdx];
  const c = points[cIdx];
  const current = angleBetween(a, b, c);
  const ba = vecNorm(vecSub(a, b));
  const bc = vecNorm(vecSub(c, b));
  let axis = vecCross(ba, bc);
  let axisLen = Math.hypot(...axis);
  if (axisLen < 1e-6) {
    axis = vecCross(ba, [0, 0, 1]);
    axisLen = Math.hypot(...axis);
    if (axisLen < 1e-6) {
      axis = [1, 0, 0];
      axisLen = 1;
    }
  }
  axis = axis.map((value) => value / axisLen);

  const movingIsC = distalIdxs.includes(cIdx);
  const probePoint = movingIsC ? c : a;

  let delta = targetDeg - current;
  const resultingAngle = (appliedDelta) => {
    const test = rotatePoint(probePoint, b, axis, appliedDelta);
    return movingIsC ? angleBetween(a, b, test) : angleBetween(test, b, c);
  };
  if (Math.abs(resultingAngle(-delta) - targetDeg) < Math.abs(resultingAngle(delta) - targetDeg)) {
    delta = -delta;
  }
  for (const idx of distalIdxs) points[idx] = rotatePoint(points[idx], b, axis, delta);
}

// Generic standing mannequin, independent of any analyzed video. y-down (head
// is the most negative y, feet the most positive), matching the landmark
// convention used by the real analyzer; flipped to Three.js's y-up only at
// render time.
const BASE_POSE = [
  [0, -0.75, 0.05],
  [0, -0.75, 0.05], [0, -0.75, 0.05], [0, -0.75, 0.05], [0, -0.75, 0.05],
  [0, -0.75, 0.05], [0, -0.75, 0.05], [0, -0.75, 0.05], [0, -0.75, 0.05],
  [0, -0.72, 0.06], [0, -0.72, 0.06],
  [-0.19, -0.55, 0], [0.19, -0.55, 0],
  [-0.22, -0.28, 0.02], [0.22, -0.28, 0.02],
  [-0.24, -0.02, 0.03], [0.24, -0.02, 0.03],
  [-0.245, 0.03, 0.04], [0.245, 0.03, 0.04],
  [-0.25, 0.02, 0.05], [0.25, 0.02, 0.05],
  [-0.23, 0, 0.05], [0.23, 0, 0.05],
  [-0.12, 0, 0], [0.12, 0, 0],
  [-0.13, 0.45, 0.03], [0.13, 0.45, 0.03],
  [-0.13, 0.85, 0.02], [0.13, 0.85, 0.02],
  [-0.13, 0.9, -0.03], [0.13, 0.9, -0.03],
  [-0.13, 0.88, 0.09], [0.13, 0.88, 0.09],
];

const ARM_CHAIN = {
  L: { shoulder: 11, elbow: 13, wrist: 15, hand: [15, 17, 19, 21] },
  R: { shoulder: 12, elbow: 14, wrist: 16, hand: [16, 18, 20, 22] },
};
const LEG_CHAIN = {
  L: { hip: 23, knee: 25, ankle: 27, foot: [27, 29, 31] },
  R: { hip: 24, knee: 26, ankle: 28, foot: [28, 30, 32] },
};

const SWING_AXIS = [1, 0, 0]; // sideways axis: rotating around it swings a limb forward/back (+ = forward)

function segmentDistance(points, aIdx, bIdx) {
  const a = points[aIdx];
  const b = points[bIdx];
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}

const HUMAN_SEGMENT_LIMITS = {
  upperArm: segmentDistance(BASE_POSE, 11, 13) * 1.16,
  forearm: segmentDistance(BASE_POSE, 13, 15) * 1.16,
  hand: 0.17,
};

function movePosePoints(points, indices, delta) {
  for (const idx of new Set(indices)) {
    if (!isFiniteTriple(points[idx])) continue;
    points[idx] = vecAdd(points[idx], delta);
  }
}

function clampDistalSegment(points, startIdx, endIdx, carriedIdxs, maxLength) {
  if (!isFiniteTriple(points[startIdx]) || !isFiniteTriple(points[endIdx])) return;
  const start = points[startIdx];
  const end = points[endIdx];
  const vector = vecSub(end, start);
  const length = Math.hypot(...vector);
  if (length <= maxLength || length < 1e-5) return;

  const scale = maxLength / length;
  const clamped = [start[0] + vector[0] * scale, start[1] + vector[1] * scale, start[2] + vector[2] * scale];
  const delta = vecSub(clamped, end);
  movePosePoints(points, [endIdx, ...carriedIdxs], delta);
}

function constrainArmProportions(points, side) {
  const arm = ARM_CHAIN[side];
  const hand = arm.hand.filter((idx) => idx !== arm.wrist);
  clampDistalSegment(points, arm.shoulder, arm.elbow, [arm.wrist, ...hand], HUMAN_SEGMENT_LIMITS.upperArm);
  clampDistalSegment(points, arm.elbow, arm.wrist, hand, HUMAN_SEGMENT_LIMITS.forearm);
  for (const tip of hand) {
    clampDistalSegment(points, arm.wrist, tip, [], HUMAN_SEGMENT_LIMITS.hand);
  }
}

function constrainHumanProportions(points) {
  constrainArmProportions(points, "L");
  constrainArmProportions(points, "R");
}

function buildPose(targets) {
  const points = BASE_POSE.map((point) => [...point]);
  for (const side of ["L", "R"]) {
    const arm = ARM_CHAIN[side];
    const leg = LEG_CHAIN[side];
    const elbowTarget = targets[`elbow${side}`] ?? targets.elbow;
    const shoulderTarget = targets[`shoulder${side}`] ?? targets.shoulder;
    const kneeTarget = targets[`knee${side}`] ?? targets.knee;
    const hipSwing = targets[`hipSwing${side}`] ?? 0;
    const armSwing = targets[`armSwing${side}`] ?? 0;

    rotateToAngle(points, arm.shoulder, arm.elbow, arm.wrist, arm.hand, elbowTarget);
    rotateToAngle(points, arm.elbow, arm.shoulder, leg.hip, [arm.elbow, ...arm.hand], shoulderTarget);
    rotateToAngle(points, leg.hip, leg.knee, leg.ankle, leg.foot, kneeTarget);

    if (armSwing) {
      const distal = [arm.elbow, ...arm.hand];
      for (const idx of distal) points[idx] = rotatePoint(points[idx], points[arm.shoulder], SWING_AXIS, armSwing);
    }
    if (hipSwing) {
      const distal = [leg.knee, ...leg.foot];
      for (const idx of distal) points[idx] = rotatePoint(points[idx], points[leg.hip], SWING_AXIS, hipSwing);
    }
  }
  const root = targets.root || [0, 0, 0];
  return points.map((point) => vecAdd(point, root));
}

// ---------------------------------------------------------------------------
// Demo choreography. Stylized reference cycles, not a biomechanical model.
// ---------------------------------------------------------------------------

const CORRECT_CYCLES = {
  block: [
    { elbow: 152, knee: 152, shoulder: 90, hold: 620, cue: "攔網預備：重心在腳掌前半部，雙手在臉前", ball: [0.18, -1.0, 0.06], actionPhase: "block_ready" },
    { elbow: 142, knee: 112, shoulder: 68, hold: 640, cue: "縮：髖、膝、踝一起彎，手臂不往後甩太大", ball: [0.16, -1.12, 0.04], actionPhase: "block_load" },
    { elbow: 166, knee: 166, shoulder: 148, root: [0, -0.24, 0], hold: 560, cue: "放：髖、膝、踝伸直，雙手直上", ball: [0.14, -1.18, 0.02], actionPhase: "block_rise" },
    { elbow: 178, knee: 174, shoulder: 176, root: [0, -0.42, 0], hold: 720, cue: "封網：手掌過網上方，手腕壓住球路", ballAttach: "block_hands", actionPhase: "block_press" },
    { elbow: 158, knee: 130, shoulder: 105, root: [0, -0.1, 0], hold: 660, cue: "落地：膝蓋對齊腳尖，髖膝踝一起吸震", ball: [0.48, -0.8, 0.46], actionPhase: "block_landing" },
  ],
  serve: [
    { elbow: 158, knee: 168, shoulder: 38, hold: 680, cue: "發球預備：身體側身，左手托球，右手放鬆", ballAttach: "serve_toss_hand", actionPhase: "serve_ready" },
    { elbow: 148, knee: 158, shoulder: 82, hold: 640, cue: "拋球：左手往上送，右手開始引臂", ball: [0.02, -1.24, 0.05], actionPhase: "serve_toss" },
    { elbow: 118, knee: 148, shoulder: 118, armSwingR: -24, hold: 620, cue: "開：右肩往後拉，胸口打開，核心穩住", ball: [0.08, -1.28, 0.08], actionPhase: "serve_load" },
    { elbow: 176, knee: 170, shoulder: 172, root: [0, -0.1, 0.04], hold: 620, cue: "擊球：手在頭前上方，手肘打開後再壓腕", ballAttach: "wrist_r", actionPhase: "serve_contact" },
    { elbow: 150, knee: 150, shoulder: 86, armSwingR: 18, root: [0, 0, 0.08], hold: 660, cue: "收臂：手臂順勢往前下方，不硬拉肩膀", ball: [0.48, -0.68, 0.82], actionPhase: "serve_follow" },
  ],
  receive: [
    { elbow: 168, knee: 142, shoulder: 48, root: [0, 0, -0.18], hold: 640, cue: "接球預備：腳先到球後面，重心低", ball: [0.1, -0.52, -0.95], actionPhase: "receive_ready" },
    { elbow: 172, knee: 125, shoulder: 58, root: [-0.06, 0, -0.06], hold: 540, cue: "移動：小碎步調整，平台先不要亂伸", ball: [0.04, -0.38, -0.48], actionPhase: "receive_step" },
    { elbow: 178, knee: 112, shoulder: 72, root: [0, 0, 0], hold: 760, cue: "縮：膝蓋和髖一起彎，平台鎖成一整片", ballAttach: "platform", actionPhase: "receive_platform" },
    { elbow: 176, knee: 132, shoulder: 66, root: [0, -0.02, 0.06], hold: 620, cue: "放：用腿和身體角度送球，不用手撈", ball: [0.0, -0.86, 0.46], actionPhase: "receive_redirect" },
    { elbow: 166, knee: 148, shoulder: 52, root: [0, 0, 0.12], hold: 620, cue: "回復：平台放鬆，腳步準備下一球", ball: [0.04, -1.16, 0.86], actionPhase: "receive_recover" },
  ],
  set: [
    { elbow: 145, knee: 152, shoulder: 138, hold: 640, cue: "二傳預備：身體側身固定，雙手在額頭上方", ballAttach: "set_incoming", actionPhase: "set_ready" },
    { elbow: 152, knee: 142, shoulder: 154, hold: 620, cue: "接球：手指張開成碗狀，球進到額頭上方", ballAttach: "set_hands", actionPhase: "set_catch" },
    { elbow: 146, knee: 132, shoulder: 150, hold: 560, cue: "縮：手腕放鬆，膝蓋微彎吸收球", ballAttach: "set_hands", actionPhase: "set_cushion" },
    { elbow: 172, knee: 166, shoulder: 168, hold: 680, cue: "放：身體位置不漂移，手指最後推出球", ballAttach: "set_release", actionPhase: "set_release" },
    { elbow: 162, knee: 156, shoulder: 132, hold: 620, cue: "回復：模型位置固定，準備下一球", ballAttach: "set_out", actionPhase: "set_recover" },
  ],
};

// Full run-up, jump and hit sequence for the spike demo: alternating left/right
// strides, the mannequin's root translating across the court, and a ball that
// is tossed, struck, and flies away. Stylized reference, not a biomechanical
// simulation.
const SPIKE_SEQUENCES = {
  correct: [
    { elbow: 170, knee: 165, shoulder: 12, root: [0, 0, -1.3], hold: 620, cue: "扣球助跑：左腳啟動，眼睛看球", ball: [0.15, -1.3, -0.2], spikePhase: "approach" },
    {
      elbow: 165, knee: 155, shoulder: 18, kneeR: 135, hipSwingL: 26, hipSwingR: -22,
      root: [0, 0, -1.0], hold: 520, cue: "扣球腳步 1：左", ball: [0.15, -1.31, -0.16], spikePhase: "left_step",
    },
    {
      elbow: 158, knee: 150, shoulder: 25, kneeL: 132, hipSwingR: 27, hipSwingL: -23,
      root: [0, 0, -0.65], hold: 520, cue: "扣球腳步 2：右，身體開始側身蓄力", ball: [0.15, -1.3, -0.1], spikePhase: "right_step",
    },
    {
      elbow: 148, knee: 140, shoulder: 15, kneeR: 118, hipSwingL: 25, hipSwingR: -20, armSwingL: -20, armSwingR: -20,
      root: [0, 0, -0.28], hold: 560, cue: "最後左腳：腳尖微內扣，身體側身準備起跳", ball: [0.16, -1.26, -0.04], spikePhase: "plant",
    },
    {
      elbow: 148, knee: 100, shoulder: 6, armSwingL: -32, armSwingR: -32,
      root: [0, 0, -0.02], hold: 620, cue: "拉弓蓄力：左肩往前，右肩往後拉", ball: [0.17, -1.2, 0.02], spikePhase: "load",
    },
    {
      elbow: 140, knee: 172, shoulder: 95,
      root: [0, -0.34, 0.05], hold: 560, cue: "側身起跳：肩膀旋轉，右手準備上擺", ball: [0.19, -1.05, 0.06], spikePhase: "jump",
    },
    {
      elbow: 178, knee: 175, shoulder: 178, elbowL: 150, shoulderL: 60,
      root: [0, -0.52, 0.1], hold: 540, cue: "最高點扣球：手掌打在球後上方", ballAttach: "wrist_r", spikePhase: "contact",
    },
    {
      elbow: 128, knee: 138, shoulder: 55,
      root: [0, -0.16, 0.2], hold: 620, cue: "落地緩衝：雙腳吸收衝擊", ball: [0.65, -0.55, 1.0], spikePhase: "landing",
    },
    { elbow: 165, knee: 135, shoulder: 20, root: [0, 0, 0.12], hold: 760, cue: "收尾：維持平衡，準備下一球", ball: [1.05, -0.05, 1.75], spikePhase: "recover" },
  ],
};

function setPoint(points, index, x, y, z) {
  points[index] = [x, y, z];
}

function shapeSetHands(points, variant, options = {}) {
  const head = points[HEAD_INDEX];
  const shoulderCenterX = (points[11][0] + points[12][0]) / 2;
  const z = options.z ?? head[2] + 0.06;
  const wristY = options.wristY ?? (variant === "mistake" ? head[1] + 0.1 : head[1] - 0.18);
  const elbowY = options.elbowY ?? (variant === "mistake" ? head[1] + 0.22 : head[1] + 0.04);
  const spread = options.spread ?? (variant === "mistake" ? 0.22 : 0.12);
  const fingerY = options.fingerY ?? wristY - 0.055;

  setPoint(points, 13, shoulderCenterX - spread * 1.15, elbowY, z);
  setPoint(points, 14, shoulderCenterX + spread * 1.15, elbowY, z);
  setPoint(points, 15, shoulderCenterX - spread, wristY, z);
  setPoint(points, 16, shoulderCenterX + spread, wristY, z);
  setPoint(points, 17, shoulderCenterX - spread - 0.035, wristY - 0.03, z + 0.015);
  setPoint(points, 18, shoulderCenterX + spread + 0.035, wristY - 0.03, z + 0.015);
  setPoint(points, 19, shoulderCenterX - 0.035, fingerY, z + 0.02);
  setPoint(points, 20, shoulderCenterX + 0.035, fingerY, z + 0.02);
  setPoint(points, 21, shoulderCenterX - spread * 0.45, wristY + 0.035, z - 0.005);
  setPoint(points, 22, shoulderCenterX + spread * 0.45, wristY + 0.035, z - 0.005);
}

function poseCenter(points, indices) {
  const valid = indices.map((index) => points[index]).filter(isFiniteTriple);
  if (!valid.length) return [0, 0, 0];
  return valid.reduce((sum, point) => vecAdd(sum, point), [0, 0, 0]).map((value) => value / valid.length);
}

function turnWholePoseSideways(points, angleDeg) {
  const pivot = poseCenter(points, [23, 24, 25, 26]);
  for (let index = 0; index < points.length; index += 1) {
    if (!isFiniteTriple(points[index])) continue;
    points[index] = rotatePoint(points[index], pivot, [0, 1, 0], angleDeg);
  }
}

function shapeSetSideBody(points) {
  offsetPoint(points, 11, -0.015, -0.005, -0.055);
  offsetPoint(points, 12, 0.015, 0.005, 0.055);
  offsetPoint(points, 23, -0.012, 0, -0.035);
  offsetPoint(points, 24, 0.012, 0, 0.035);
  shapeLeftFootInward(points, 0.28);
  shapeRightFootBrace(points, 0.28);
}

function shapeReceivePlatform(points, variant, options = {}) {
  const centerX = (points[23][0] + points[24][0]) / 2;
  const y = options.y ?? (variant === "mistake" ? 0.02 : -0.02);
  const z = options.z ?? (variant === "mistake" ? 0.02 : 0.18);
  const gap = options.gap ?? (variant === "mistake" ? 0.2 : 0.045);
  const elbowY = options.elbowY ?? -0.24;
  setPoint(points, 13, centerX - 0.26, elbowY, z);
  setPoint(points, 14, centerX + 0.26, elbowY, z);
  setPoint(points, 15, centerX - gap, y, z);
  setPoint(points, 16, centerX + gap, y + (variant === "mistake" ? 0.05 : 0), z);
  setPoint(points, 17, centerX - gap - 0.03, y + 0.03, z);
  setPoint(points, 18, centerX + gap + 0.03, y + 0.03, z);
  setPoint(points, 19, centerX - gap * 0.5, y + 0.045, z);
  setPoint(points, 20, centerX + gap * 0.5, y + 0.045, z);
}

function shapeSetBiomechanics(points, variant, frame = {}) {
  if (variant === "mistake") {
    shapeSetHands(points, "mistake");
    return;
  }
  const head = points[HEAD_INDEX];
  const phase = frame.actionPhase;
  shapeSetSideBody(points);
  if (phase === "set_catch") {
    shapeSetHands(points, "correct", { wristY: head[1] - 0.2, elbowY: head[1] + 0.02, spread: 0.13 });
  } else if (phase === "set_cushion") {
    shapeSetHands(points, "correct", { wristY: head[1] - 0.13, elbowY: head[1] + 0.07, spread: 0.14, fingerY: head[1] - 0.2 });
  } else if (phase === "set_release") {
    shapeSetHands(points, "correct", { wristY: head[1] - 0.34, elbowY: head[1] - 0.08, spread: 0.1, fingerY: head[1] - 0.42 });
  } else if (phase === "set_recover") {
    shapeSetHands(points, "correct", { wristY: head[1] - 0.05, elbowY: head[1] + 0.1, spread: 0.14 });
  } else {
    shapeSetHands(points, "correct");
  }
  turnWholePoseSideways(points, SET_SIDE_ANGLE_DEG);
}

function shapeReceiveBiomechanics(points, variant, frame = {}) {
  if (variant === "mistake") {
    shapeReceivePlatform(points, "mistake");
    return;
  }
  const phase = frame.actionPhase;
  if (phase === "receive_ready") {
    shapeReceivePlatform(points, "correct", { y: 0.08, z: 0.16, gap: 0.08, elbowY: -0.18 });
  } else if (phase === "receive_step") {
    shapeReceivePlatform(points, "correct", { y: 0.06, z: 0.2, gap: 0.06, elbowY: -0.2 });
    shapeLeftFootInward(points, 0.35);
  } else if (phase === "receive_platform") {
    shapeReceivePlatform(points, "correct", { y: 0.04, z: 0.24, gap: 0.035, elbowY: -0.24 });
  } else if (phase === "receive_redirect") {
    shapeReceivePlatform(points, "correct", { y: -0.02, z: 0.2, gap: 0.04, elbowY: -0.26 });
    offsetPoseIndices(points, UPPER_BODY_INDICES, 0, -0.02, 0.03);
  } else {
    shapeReceivePlatform(points, "correct");
  }
}

function offsetPoint(points, index, dx = 0, dy = 0, dz = 0) {
  if (!isFiniteTriple(points[index])) return;
  points[index] = [points[index][0] + dx, points[index][1] + dy, points[index][2] + dz];
}

function shapeLeftFootInward(points, amount = 1) {
  const ankle = points[27];
  if (!isFiniteTriple(ankle)) return;
  setPoint(points, 29, ankle[0] - 0.025 * amount, ankle[1] + 0.055, ankle[2] + 0.055 * amount);
  setPoint(points, 31, ankle[0] + 0.13 * amount, ankle[1] + 0.08, ankle[2] - 0.105 * amount);
}

function shapeRightFootBrace(points, amount = 1) {
  const ankle = points[28];
  if (!isFiniteTriple(ankle)) return;
  setPoint(points, 30, ankle[0] + 0.035 * amount, ankle[1] + 0.05, ankle[2] - 0.02 * amount);
  setPoint(points, 32, ankle[0] - 0.075 * amount, ankle[1] + 0.085, ankle[2] + 0.07 * amount);
}

function setOpenSpikeHand(points, side, wrist, spread = 1, palmTilt = 0) {
  const isRight = side === "R";
  const pinky = isRight ? 18 : 17;
  const index = isRight ? 20 : 19;
  const thumb = isRight ? 22 : 21;
  const sideSign = isRight ? 1 : -1;
  setPoint(points, pinky, wrist[0] - sideSign * 0.075 * spread, wrist[1] - 0.09 * spread, wrist[2] + palmTilt - 0.02);
  setPoint(points, index, wrist[0] + sideSign * 0.075 * spread, wrist[1] - 0.105 * spread, wrist[2] + palmTilt + 0.015);
  setPoint(points, thumb, wrist[0] + sideSign * 0.12 * spread, wrist[1] - 0.035 * spread, wrist[2] + palmTilt - 0.065);
}

function shapeBlockHands(points, phase) {
  const head = points[HEAD_INDEX];
  const centerX = (points[11][0] + points[12][0]) / 2;
  const ready = {
    block_ready: { elbowY: head[1] + 0.18, wristY: head[1] - 0.02, spread: 0.2, z: head[2] - 0.02 },
    block_load: { elbowY: head[1] + 0.26, wristY: head[1] + 0.06, spread: 0.22, z: head[2] - 0.04 },
    block_rise: { elbowY: head[1] - 0.06, wristY: head[1] - 0.32, spread: 0.2, z: head[2] - 0.06 },
    block_press: { elbowY: head[1] - 0.16, wristY: head[1] - 0.46, spread: 0.23, z: head[2] - 0.1 },
    block_landing: { elbowY: head[1] + 0.04, wristY: head[1] - 0.16, spread: 0.18, z: head[2] - 0.02 },
  }[phase] || { elbowY: head[1] + 0.1, wristY: head[1] - 0.08, spread: 0.2, z: head[2] - 0.02 };

  setPoint(points, 13, centerX - ready.spread, ready.elbowY, ready.z);
  setPoint(points, 14, centerX + ready.spread, ready.elbowY, ready.z);
  setPoint(points, 15, centerX - ready.spread * 0.8, ready.wristY, ready.z - 0.03);
  setPoint(points, 16, centerX + ready.spread * 0.8, ready.wristY, ready.z - 0.03);
  setOpenSpikeHand(points, "L", points[15], 0.95, -0.03);
  setOpenSpikeHand(points, "R", points[16], 0.95, -0.03);
}

function shapeBlockBiomechanics(points, variant, frame = {}) {
  if (variant !== "correct") return;
  const phase = frame.actionPhase;
  shapeBlockHands(points, phase);
  if (phase === "block_load") {
    shapeLeftFootInward(points, 0.3);
    shapeRightFootBrace(points, 0.3);
  }
  if (phase === "block_press") {
    offsetPoseIndices(points, HAND_INDICES, 0, -0.02, -0.08);
  }
  if (phase === "block_landing") {
    shapeLeftFootInward(points, 0.25);
    shapeRightFootBrace(points, 0.25);
  }
}

function shapeServeBiomechanics(points, variant, frame = {}) {
  if (variant !== "correct") return;
  const head = points[HEAD_INDEX];
  const phase = frame.actionPhase;
  // The trunk turn now comes from ACTION_TORSO_YAW; the old point-nudge would
  // compound with it (on the spike it left contact 33 degrees off square).
  shapeLeftFootInward(points, 0.35);
  shapeRightFootBrace(points, 0.45);

  if (phase === "serve_ready") {
    setPoint(points, 13, -0.24, head[1] + 0.32, -0.02);
    setPoint(points, 15, -0.16, head[1] + 0.18, 0.06);
    setOpenSpikeHand(points, "L", points[15], 0.7, 0.02);
    setPoint(points, 14, 0.33, head[1] + 0.2, 0.18);
    setPoint(points, 16, 0.44, head[1] + 0.38, 0.26);
    setOpenSpikeHand(points, "R", points[16], 0.72, 0.02);
  } else if (phase === "serve_toss") {
    setPoint(points, 13, -0.22, head[1] - 0.08, 0);
    setPoint(points, 15, -0.12, head[1] - 0.34, 0.03);
    setOpenSpikeHand(points, "L", points[15], 0.78, 0.02);
    setPoint(points, 14, 0.36, head[1] + 0.04, 0.24);
    setPoint(points, 16, 0.48, head[1] + 0.18, 0.32);
    setOpenSpikeHand(points, "R", points[16], 0.75, 0.03);
  } else if (phase === "serve_load") {
    setPoint(points, 13, -0.24, head[1] + 0.02, 0);
    setPoint(points, 15, -0.18, head[1] + 0.16, 0.02);
    setOpenSpikeHand(points, "L", points[15], 0.68, 0.01);
    setPoint(points, 14, 0.4, head[1] - 0.06, 0.32);
    setPoint(points, 16, 0.52, head[1] + 0.08, 0.42);
    setOpenSpikeHand(points, "R", points[16], 0.9, 0.04);
  } else if (phase === "serve_contact") {
    setPoint(points, 13, -0.18, head[1] + 0.22, -0.02);
    setPoint(points, 15, -0.16, head[1] + 0.38, -0.04);
    setOpenSpikeHand(points, "L", points[15], 0.65, 0);
    setPoint(points, 14, 0.25, head[1] - 0.18, 0.12);
    setPoint(points, 16, 0.32, head[1] - 0.48, 0.14);
    setOpenSpikeHand(points, "R", points[16], 1, -0.01);
  } else {
    setPoint(points, 13, -0.18, head[1] + 0.28, -0.02);
    setPoint(points, 15, -0.16, head[1] + 0.42, -0.03);
    setOpenSpikeHand(points, "L", points[15], 0.65, 0);
    setPoint(points, 14, 0.3, head[1] + 0.12, -0.08);
    setPoint(points, 16, 0.2, head[1] + 0.34, -0.16);
    setOpenSpikeHand(points, "R", points[16], 0.76, -0.03);
  }
}

function shapeSpikeLoad(points) {
  const head = points[HEAD_INDEX];
  shapeLeftFootInward(points, 1);
  shapeRightFootBrace(points, 0.65);

  setPoint(points, 13, -0.38, head[1] + 0.02, -0.3);
  setPoint(points, 15, -0.54, head[1] - 0.2, -0.36);
  setOpenSpikeHand(points, "L", points[15], 0.85, -0.02);

  setPoint(points, 14, 0.42, head[1] + 0.2, 0.42);
  setPoint(points, 16, 0.54, head[1] + 0.04, 0.48);
  setOpenSpikeHand(points, "R", points[16], 0.9, 0.04);
}

function shapeSpikeJump(points) {
  const head = points[HEAD_INDEX];
  shapeLeftFootInward(points, 0.85);
  setPoint(points, 13, -0.36, head[1] - 0.06, -0.2);
  setPoint(points, 15, -0.48, head[1] - 0.24, -0.24);
  setOpenSpikeHand(points, "L", points[15], 0.82, -0.02);
  setPoint(points, 14, 0.38, head[1] - 0.05, 0.34);
  setPoint(points, 16, 0.4, head[1] - 0.34, 0.3);
  setOpenSpikeHand(points, "R", points[16], 0.95, 0.03);
}

function shapeSpikeContact(points, variant) {
  if (variant !== "correct") return;
  const head = points[HEAD_INDEX];
  shapeLeftFootInward(points, 0.55);
  setPoint(points, 13, -0.34, head[1] + 0.18, -0.04);
  setPoint(points, 15, -0.48, head[1] + 0.42, -0.12);
  setOpenSpikeHand(points, "L", points[15], 0.7, -0.02);
  setPoint(points, 14, 0.22, head[1] - 0.26, 0.12);
  setPoint(points, 16, 0.38, head[1] - 0.7, 0.16);
  setOpenSpikeHand(points, "R", points[16], 1.15, -0.01);
}

function shapeSpikeLanding(points) {
  const head = points[HEAD_INDEX];
  shapeLeftFootInward(points, 0.35);
  setPoint(points, 14, 0.22, head[1] + 0.04, 0.02);
  setPoint(points, 16, 0.26, head[1] + 0.22, 0.02);
  setOpenSpikeHand(points, "R", points[16], 0.72, 0);
}

// How much each action turns its trunk, per phase.
//
// One mechanism for all five actions: rotate whole segments -- shoulders, arms,
// hands and head as one body -- AFTER the shapers have placed the limbs, so the
// arms travel with the torso. The code used to nudge a handful of points by a
// fraction of a unit instead, which left the arms wherever the shapers had
// written them and read as no turn at all.
//
// Yaw about the vertical axis through the hips, in degrees.
//
// SIGN is a FRAMING choice, not a biomechanical one, and it was got wrong once
// by treating it as the latter. The front camera sits at +z, so NEGATIVE yaw
// brings the right shoulder toward +z, i.e. toward the viewer. That is what we
// want: the hitting arm cocks on the near side where the swing is visible,
// instead of disappearing behind the torso. Flip the sign and the action is
// still biomechanically valid -- just filmed from the wrong side, with the
// interesting arm hidden.
const ACTION_TORSO_YAW = {
  // Spike: turns side-on so the hitting shoulder is cocked behind the body,
  // then unwinds into a contact made square to the net. The hips lead and the
  // shoulders trail, so the separation peaks just before take-off -- that
  // stretch across the trunk is what powers the arm.
  // Magnitudes matter as much as the shape here: at 48 degrees the shoulder line
  // still projects to 67% of its width from the front, which reads as "slightly
  // narrower" rather than "side-on" and left the demo looking front-facing. A
  // hitter planting off an angled approach turns much further than that -- the
  // shoulder line comes close to perpendicular to the net at maximum cocking --
  // so the wind-up runs to 66, projecting to ~41% and reading unmistakably.
  // The hips are turned further too: the last step plants across the approach,
  // it does not land square. Separation still peaks at a realistic 44 degrees.
  // A real trunk twists continuously along the spine, so 40+ degrees between the
  // hips and the shoulders looks powerful on a person. This figure cannot do
  // that: the torso is ONE rigid mesh whose lower end is the shorts, and the
  // thighs are separate meshes driven by the hip landmarks. Open a big gap
  // between them and the shorts visibly shear away from the legs -- the figure
  // reads as broken at the waist rather than coiled. So the separation is kept
  // to roughly 18 degrees, enough to show the hips leading, and the legs follow
  // the pelvis closely so the whole body turns as one piece.
  spike: {
    approach: { hips: -4, shoulders: -8 },
    left_step: { hips: -14, shoulders: -20 },
    right_step: { hips: -28, shoulders: -40 },
    plant: { hips: -44, shoulders: -60 }, // planted across, clearly side-on
    load: { hips: -48, shoulders: -66 }, // hips leading by ~18
    jump: { hips: -30, shoulders: -42 }, // shoulders unwind, hips follow
    contact: { hips: -2, shoulders: -6 }, // squared up to the net
    landing: { hips: 6, shoulders: 8 },
    recover: { hips: 0, shoulders: 0 },
  },
  // Serve: the same chain as the spike but smaller, because there is no run-up
  // to turn -- the coil has to come from the stance. The coaching cue already
  // said 身體側身; this is what makes the figure actually stand side-on.
  serve: {
    serve_ready: { hips: -34, shoulders: -46 }, // stance is already side-on
    serve_toss: { hips: -34, shoulders: -48 },
    serve_load: { hips: -42, shoulders: -60 }, // drawn back, hips leading by ~18
    serve_contact: { hips: -2, shoulders: -6 }, // chest square, hit out front
    serve_follow: { hips: 6, shoulders: 12 },
  },
  // Receive: the ball goes where the PLATFORM faces, so here the turn IS the
  // technique rather than decoration. Square to the incoming ball, then turn
  // the platform toward the setter to redirect it -- which is exactly what the
  // cue 用身體角度送球 is describing.
  receive: {
    receive_ready: { hips: 0, shoulders: 0 },
    receive_step: { hips: 6, shoulders: 12 },
    receive_platform: { hips: 5, shoulders: 8 }, // stay behind the ball
    receive_redirect: { hips: 14, shoulders: 26 }, // angle it to the target
    receive_recover: { hips: 4, shoulders: 6 },
  },
  // Block: deliberately near zero. A blocker keeps the shoulders PARALLEL to
  // the net -- turning them opens a seam and deflects the ball out of bounds,
  // so adding a swivel here would be teaching the error. The one real turn is
  // after landing, when the blocker turns to follow the ball back into play.
  block: {
    block_ready: { hips: 0, shoulders: 0 },
    block_load: { hips: 0, shoulders: 0 },
    block_rise: { hips: 0, shoulders: 0 },
    block_press: { hips: 0, shoulders: 0 },
    block_landing: { hips: 6, shoulders: 12 },
  },
  // Set: the ball goes where the shoulders point, so the setter squares up to
  // the target through the release. This is the movement ON TOP of the fixed
  // presentation angle the whole figure already carries (turnWholePoseSideways),
  // which exists so the hand shape stays visible.
  set: {
    set_ready: { hips: -6, shoulders: -12 },
    set_catch: { hips: -5, shoulders: -10 },
    set_cushion: { hips: -3, shoulders: -6 },
    set_release: { hips: 2, shoulders: 5 }, // squared to where the ball is going
    set_recover: { hips: 0, shoulders: 0 },
  },
};

function rotateIndicesYaw(points, indices, pivot, angleDeg) {
  if (!angleDeg) return;
  for (const index of indices) {
    if (!isFiniteTriple(points[index])) continue;
    points[index] = rotatePoint(points[index], pivot, [0, 1, 0], angleDeg);
  }
}

function applyTorsoTurn(points, action, phase) {
  const yaw = ACTION_TORSO_YAW[action]?.[phase];
  if (!yaw) return;
  const pivot = poseCenter(points, [23, 24]);
  // Upper body as one unit, so the armswing rotates with the chest.
  rotateIndicesYaw(points, UPPER_BODY_INDICES, pivot, yaw.shoulders);
  // The legs follow the pelvis closely. They used to lag badly (knees at half
  // the hip yaw, ankles at 15%), which left the thighs pointing at the camera
  // while the shorts -- part of the torso mesh -- had already turned, so the
  // figure looked severed at the waist. Only the feet trail slightly now, which
  // reads as the shoe staying planted rather than the leg being detached.
  rotateIndicesYaw(points, [23, 24], pivot, yaw.hips);
  rotateIndicesYaw(points, [25, 26], pivot, yaw.hips * 0.9);
  rotateIndicesYaw(points, [27, 28], pivot, yaw.hips * 0.8);
  rotateIndicesYaw(points, [29, 30, 31, 32], pivot, yaw.hips * 0.7);
}

function shapeSpikeBiomechanics(points, variant, frame) {
  if (variant !== "correct") return;
  if (frame.spikePhase === "plant") {
    shapeLeftFootInward(points, 1);
    shapeRightFootBrace(points, 0.7);
  }
  if (frame.spikePhase === "load") shapeSpikeLoad(points);
  if (frame.spikePhase === "jump") shapeSpikeJump(points);
  if (frame.spikePhase === "contact") shapeSpikeContact(points, variant);
  if (frame.spikePhase === "landing") shapeSpikeLanding(points);
}

function applyActionShape(points, action, variant, frame) {
  if (action === "set") shapeSetBiomechanics(points, variant, frame);
  if (action === "receive") shapeReceiveBiomechanics(points, variant, frame);
  if (action === "block") shapeBlockBiomechanics(points, variant, frame);
  if (action === "serve") shapeServeBiomechanics(points, variant, frame);
  if (action === "spike") shapeSpikeBiomechanics(points, variant, frame);
  // Last, so the limbs the shapers just placed rotate together with the trunk.
  // The demo poses only: a "mistake" pose is deliberately un-coached.
  if (variant === "correct") {
    applyTorsoTurn(points, action, frame.spikePhase || frame.actionPhase);
  }
  constrainHumanProportions(points);
}

const decodeCue = (value) => decodeURIComponent(value);
const CLEAN_REFERENCE_CUES = {
  block: [
    "%E6%94%94%E7%B6%B2%E9%A0%90%E5%82%99%EF%BC%9A%E8%86%9D%E8%93%8B%E5%BE%AE%E5%BD%8E%EF%BC%8C%E9%9B%99%E6%89%8B%E5%9C%A8%E8%87%89%E5%89%8D",
    "%E4%B8%8B%E8%B9%B2%E8%93%84%E5%8A%9B%EF%BC%9A%E9%AB%96%E3%80%81%E8%86%9D%E3%80%81%E8%85%B3%E8%B8%9D%E4%B8%80%E8%B5%B7%E5%BD%8E",
    "%E5%90%91%E4%B8%8A%E5%B0%81%E7%B6%B2%EF%BC%9A%E6%89%8B%E8%87%82%E7%A9%BF%E9%81%8E%E7%90%83%EF%BC%8C%E6%89%8B%E6%8E%8C%E5%A3%93%E4%BD%8F%E8%B7%AF%E7%B7%9A",
    "%E8%90%BD%E5%9C%B0%E7%B7%A9%E8%A1%9D%EF%BC%9A%E8%86%9D%E8%93%8B%E5%B0%8D%E9%BD%8A%E8%85%B3%E5%B0%96",
  ],
  serve: [
    "%E7%99%BC%E7%90%83%E9%A0%90%E5%82%99%EF%BC%9A%E8%BA%AB%E9%AB%94%E5%81%B4%E8%BA%AB%EF%BC%8C%E9%9D%9E%E6%85%A3%E7%94%A8%E6%89%8B%E6%89%98%E7%90%83",
    "%E6%8B%8B%E7%90%83%E8%88%87%E5%BC%95%E8%87%82%EF%BC%9A%E8%82%A9%E8%86%80%E6%94%BE%E9%AC%86%EF%BC%8C%E4%B8%8D%E8%A6%81%E8%81%B3%E8%82%A9",
    "%E6%9C%80%E9%AB%98%E9%BB%9E%E6%93%8A%E7%90%83%EF%BC%9A%E6%89%8B%E6%8E%8C%E5%9C%A8%E9%A0%AD%E5%89%8D%E4%B8%8A%E6%96%B9",
    "%E9%A0%86%E5%8B%A2%E6%94%B6%E8%87%82%EF%BC%9A%E6%A0%B8%E5%BF%83%E5%B8%B6%E5%8B%95%EF%BC%8C%E4%B8%8D%E7%A1%AC%E6%8B%89%E8%82%A9%E8%86%80",
  ],
  receive: [
    "%E6%8E%A5%E7%90%83%E9%A0%90%E5%82%99%EF%BC%9A%E9%87%8D%E5%BF%83%E4%BD%8E%EF%BC%8C%E8%85%B3%E5%85%88%E5%88%B0%E7%90%83%E5%BE%8C%E9%9D%A2",
    "%E5%B9%B3%E5%8F%B0%E9%8E%96%E7%A9%A9%EF%BC%9A%E6%89%8B%E8%82%98%E4%BC%B8%E7%9B%B4%EF%BC%8C%E5%89%8D%E8%87%82%E6%88%90%E4%B8%80%E6%95%B4%E7%89%87",
    "%E9%9D%A2%E5%90%91%E7%9B%AE%E6%A8%99%EF%BC%9A%E7%94%A8%E8%BA%AB%E9%AB%94%E8%A7%92%E5%BA%A6%E9%80%81%E7%90%83",
  ],
  set: [
    "%E8%88%89%E7%90%83%E9%A0%90%E5%82%99%EF%BC%9A%E9%9B%99%E6%89%8B%E5%9C%A8%E9%A1%8D%E9%A0%AD%E4%B8%8A%E6%96%B9%EF%BC%8C%E6%89%8B%E5%9E%8B%E6%88%90%E4%B8%89%E8%A7%92",
    "%E6%8E%A5%E7%90%83%E7%B7%A9%E8%A1%9D%EF%BC%9A%E6%89%8B%E6%8C%87%E5%BC%B5%E9%96%8B%EF%BC%8C%E6%89%8B%E8%85%95%E6%94%BE%E9%AC%86",
    "%E8%85%BF%E9%83%A8%E9%80%81%E7%90%83%EF%BC%9A%E8%86%9D%E8%93%8B%E4%BC%B8%E5%B1%95%EF%BC%8C%E7%90%83%E5%BE%80%E4%B8%8A%E8%B5%B0",
  ],
  spike: [
    "%E6%89%A3%E7%90%83%E5%8A%A9%E8%B7%91%EF%BC%9A%E5%B7%A6%E8%85%B3%E5%95%9F%E5%8B%95%EF%BC%8C%E7%9C%BC%E7%9D%9B%E7%9C%8B%E7%90%83",
    "%E6%89%A3%E7%90%83%E8%85%B3%E6%AD%A5%201%EF%BC%9A%E5%B7%A6",
    "%E6%89%A3%E7%90%83%E8%85%B3%E6%AD%A5%202%EF%BC%9A%E5%8F%B3%EF%BC%8C%E8%BA%AB%E9%AB%94%E9%96%8B%E5%A7%8B%E8%93%84%E5%8A%9B",
    "%E6%89%A3%E7%90%83%E8%85%B3%E6%AD%A5%203%EF%BC%9A%E5%B7%A6%EF%BC%8C%E9%9B%99%E8%85%B3%E6%BA%96%E5%82%99%E8%B5%B7%E8%B7%B3",
    "%E6%93%BA%E8%87%82%E4%B8%8B%E6%B2%89%EF%BC%9A%E9%AB%96%E8%86%9D%E4%B8%80%E8%B5%B7%E5%BD%8E%EF%BC%8C%E4%B8%8D%E8%A6%81%E8%86%9D%E8%93%8B%E5%85%A7%E6%89%A3",
    "%E8%B5%B7%E8%B7%B3%EF%BC%9A%E8%85%BF%E9%83%A8%E4%BC%B8%E5%B1%95%EF%BC%8C%E6%8A%8A%E8%BA%AB%E9%AB%94%E5%BE%80%E4%B8%8A%E5%B8%B6",
    "%E6%9C%80%E9%AB%98%E9%BB%9E%E6%89%A3%E7%90%83%EF%BC%9A%E6%89%8B%E5%9C%A8%E9%A0%AD%E5%89%8D%E4%B8%8A%E6%96%B9%E6%93%8A%E7%90%83",
    "%E8%90%BD%E5%9C%B0%E7%B7%A9%E8%A1%9D%EF%BC%9A%E9%9B%99%E8%85%B3%E5%90%B8%E6%94%B6%E8%A1%9D%E6%93%8A",
    "%E6%94%B6%E5%B0%BE%EF%BC%9A%E7%B6%AD%E6%8C%81%E5%B9%B3%E8%A1%A1%EF%BC%8C%E6%BA%96%E5%82%99%E4%B8%8B%E4%B8%80%E7%90%83",
  ],
};

function referenceCue(action, index, fallback) {
  if (fallback) return fallback;
  const encoded = CLEAN_REFERENCE_CUES[action]?.[index];
  return encoded ? decodeCue(encoded) : fallback;
}

function spikeHandBallPoint(points) {
  const index = points[20] || points[ARM_CHAIN.R.wrist];
  const pinky = points[18] || index;
  return [
    (index[0] + pinky[0]) / 2,
    Math.min(index[1], pinky[1]) - 0.055,
    (index[2] + pinky[2]) / 2 + 0.025,
  ];
}

function setHandsCenter(points) {
  const left = points[19] || points[15];
  const right = points[20] || points[16];
  return [
    (left[0] + right[0]) / 2,
    Math.min(left[1], right[1]),
    (left[2] + right[2]) / 2,
  ];
}

function setHandsBallPoint(points, lift = 0.16, forward = 0.14) {
  const center = setHandsCenter(points);
  return [
    center[0],
    center[1] - lift,
    center[2] + forward,
  ];
}

function setIncomingBallPoint(points) {
  const center = setHandsCenter(points);
  return [center[0] - 0.015, center[1] - 0.44, center[2] + 0.2];
}

function setReleaseBallPoint(points) {
  const center = setHandsCenter(points);
  return [center[0] + 0.025, center[1] - 0.42, center[2] + 0.22];
}

function setOutBallPoint(points) {
  const center = setHandsCenter(points);
  return [center[0] + 0.055, center[1] - 0.62, center[2] + 0.28];
}

function platformBallPoint(points) {
  const left = points[15];
  const right = points[16];
  return [
    (left[0] + right[0]) / 2,
    Math.min(left[1], right[1]) - 0.09,
    (left[2] + right[2]) / 2 - 0.04,
  ];
}

function blockHandsBallPoint(points) {
  const left = points[19] || points[15];
  const right = points[20] || points[16];
  return [
    (left[0] + right[0]) / 2,
    Math.min(left[1], right[1]) - 0.06,
    (left[2] + right[2]) / 2 - 0.08,
  ];
}

function serveTossHandBallPoint(points) {
  const hand = points[19] || points[15];
  return [hand[0], hand[1] - 0.09, hand[2] + 0.02];
}

function frameBallPoint(action, frame, points) {
  if (frame.ballAttach === "wrist_r") return spikeHandBallPoint(points);
  if (frame.ballAttach === "set_incoming") return setIncomingBallPoint(points);
  if (frame.ballAttach === "set_hands") return setHandsBallPoint(points);
  if (frame.ballAttach === "set_release") return setReleaseBallPoint(points);
  if (frame.ballAttach === "set_out") return setOutBallPoint(points);
  if (frame.ballAttach === "platform") return platformBallPoint(points);
  if (frame.ballAttach === "block_hands") return blockHandsBallPoint(points);
  if (frame.ballAttach === "serve_toss_hand") return serveTossHandBallPoint(points);
  if (frame.ball) return frame.ball;
  if (action === "set") return setHandsBallPoint(points);
  if (action === "receive") return platformBallPoint(points);
  if (action === "block") return blockHandsBallPoint(points);
  return spikeHandBallPoint(points);
}

function buildSequence(action, variant = "correct") {
  void variant;
  const spec = action === "spike"
    ? SPIKE_SEQUENCES.correct
    : (CORRECT_CYCLES[action] || CORRECT_CYCLES.block);
  return spec.map((frame, index) => {
    const points = buildPose(frame);
    applyActionShape(points, action, "correct", frame);
    return {
      points,
      ball: frameBallPoint(action, frame, points),
      hold: frame.hold,
      caption: referenceCue(action, index, frame.cue),
      jointStatus: null,
    };
  });
}

function computeFramesBounds(frames) {
  const min = new THREE.Vector3(Infinity, Infinity, Infinity);
  const max = new THREE.Vector3(-Infinity, -Infinity, -Infinity);
  for (const frame of frames) {
    for (const point of frame.points) {
      const v = toVec3(point);
      min.min(v);
      max.max(v);
    }
    if (frame.ball) {
      const v = toVec3(frame.ball);
      min.min(v);
      max.max(v);
    }
  }
  return { min, max };
}

// Automatically size and center the camera so the whole bounding box (across
// every keyframe, including the ball) stays in frame from front or side.
function frameCamera(bounds, fovDeg, padding = 1.35, aspect = 1) {
  const center = bounds.min.clone().add(bounds.max).multiplyScalar(0.5);
  const size = bounds.max.clone().sub(bounds.min);
  const halfV = Math.max(size.y / 2, 0.2);
  const halfH = Math.max(size.x, size.z) / 2 || 0.2;
  const safeAspect = clamp(Number(aspect) || 1, 0.35, 3.5);
  const halfFov = (fovDeg * Math.PI) / 360;
  const distance = Math.max(halfV, halfH / safeAspect) / Math.tan(halfFov) * padding;
  return { center, distance };
}

function lerpTriples(a, b, t) {
  return a.map((point, index) => [
    point[0] + (b[index][0] - point[0]) * t,
    point[1] + (b[index][1] - point[1]) * t,
    point[2] + (b[index][2] - point[2]) * t,
  ]);
}
function lerpTriple(a, b, t) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}
function easeInOut(t) {
  return t < 0.5 ? 2 * t * t : 1 - ((-2 * t + 2) ** 2) / 2;
}

// ---------------------------------------------------------------------------
// Rendering: a stylized rounded-capsule mannequin, matched to a reference
// figurine look (big head, soft warm tones, no face).
// ---------------------------------------------------------------------------

const BODY_PARTS = [
  { a: 11, b: 12, radius: 0.035, joint: null },
  { a: 11, b: 13, radius: 0.055, joint: "shoulder" },
  { a: 12, b: 14, radius: 0.055, joint: "shoulder" },
  { a: 13, b: 15, radius: 0.045, joint: "elbow" },
  { a: 14, b: 16, radius: 0.045, joint: "elbow" },
  { a: 15, b: 19, radius: 0.019, joint: "wrist" },
  { a: 16, b: 20, radius: 0.019, joint: "wrist" },
  { a: 15, b: 17, radius: 0.014, joint: "wrist" },
  { a: 15, b: 21, radius: 0.014, joint: "wrist" },
  { a: 16, b: 18, radius: 0.014, joint: "wrist" },
  { a: 16, b: 22, radius: 0.014, joint: "wrist" },
  { a: 17, b: 19, radius: 0.01, joint: "wrist" },
  { a: 18, b: 20, radius: 0.01, joint: "wrist" },
  { a: 23, b: 25, radius: 0.075, joint: "knee" },
  { a: 24, b: 26, radius: 0.075, joint: "knee" },
  { a: 25, b: 27, radius: 0.056, joint: "knee" },
  { a: 26, b: 28, radius: 0.056, joint: "knee" },
  { a: 27, b: 29, radius: 0.026, joint: null },
  { a: 28, b: 30, radius: 0.026, joint: null },
  { a: 27, b: 31, radius: 0.035, joint: null },
  { a: 28, b: 32, radius: 0.035, joint: null },
  { a: 29, b: 31, radius: 0.02, joint: null },
  { a: 30, b: 32, radius: 0.02, joint: null },
];
const BODY_COLOR = 0xffffff;
const BODY_SHADOW_COLOR = 0xd7d0c3;
const KRUNK_BODY_COLOR = 0xffffff;
const NECK_RADIUS = 0.038;
const TORSO_RADIUS = 0.17;
const CHEST_RADIUS = 0.14;
const PELVIS_RADIUS = 0.13;
const HEAD_INDEX = 0;
const HEAD_RADIUS = 0.145;
const SET_SIDE_ANGLE_DEG = -58;

const NEUTRAL_COLOR = 0xf1e6d3;
const STATUS_COLOR = { green: BODY_COLOR, yellow: 0xffd34f, red: 0xff5d5d };
const RISK_RING_COLOR = { yellow: 0xffc43d, red: 0xff3b3b };
const DEMO_SLOW_FACTOR = 1.75;
const FRAME_INTERVAL_MS = 1000 / 60;
const DISPLAY_TARGET_HEIGHT = 1.65;
const POSE_GROUND_Y = -0.92;
const MIN_ACTUAL_HOLD_MS = 100;
const MAX_ACTUAL_HOLD_MS = 1200;
const MIN_DISPLAY_WIDTHS = [
  [11, 12, 0.34],
  [13, 14, 0.38],
  [15, 16, 0.32],
  [17, 18, 0.34],
  [19, 20, 0.26],
  [21, 22, 0.26],
  [23, 24, 0.22],
  [25, 26, 0.24],
  [27, 28, 0.22],
  [31, 32, 0.24],
];
const FALLBACK_DEPTH_OFFSETS = {
  0: -0.03,
  11: -0.02,
  12: -0.02,
  13: -0.06,
  14: -0.06,
  15: -0.14,
  16: -0.14,
  17: -0.16,
  18: -0.16,
  19: -0.18,
  20: -0.18,
  21: -0.12,
  22: -0.12,
  23: 0,
  24: 0,
  25: 0.07,
  26: 0.07,
  27: 0.15,
  28: 0.15,
  29: 0.18,
  30: 0.18,
  31: 0.2,
  32: 0.2,
};
const SINGLE_POSE_MOTION = [
  { hold: 620, upperX: -0.018, upperY: 0.004, lowerX: -0.006, handY: 0.012, depth: 0.012 },
  { hold: 620, upperX: 0.012, upperY: -0.008, lowerX: 0.004, handY: -0.006, depth: -0.008 },
  { hold: 620, upperX: 0.018, upperY: 0.002, lowerX: 0.006, handY: 0.008, depth: 0.01 },
  { hold: 620, upperX: -0.01, upperY: -0.004, lowerX: -0.004, handY: -0.004, depth: -0.006 },
];
const UPPER_BODY_INDICES = [0, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22];
const HAND_INDICES = [15, 16, 17, 18, 19, 20, 21, 22];
const LOWER_BODY_INDICES = [23, 24, 25, 26, 27, 28, 29, 30, 31, 32];
const SEQUENCE_ROOT_FOLLOW = 0.28;
const SEQUENCE_POINT_FOLLOW = 0.52;
const ACTUAL_TARGET_FOLLOW = 0.5;
const ACTUAL_RETARGET_LIMITS = {
  elbow: [70, 178],
  shoulder: [10, 178],
  knee: [78, 178],
  armSwing: [-58, 58],
  hipSwing: [-40, 40],
};
const ACTUAL_RETARGET_DEFAULTS = {
  spike: { elbow: 150, shoulder: 75, knee: 142, armSwing: -8, hipSwing: 0 },
  block: { elbow: 168, shoulder: 128, knee: 145, armSwing: 0, hipSwing: 0 },
  serve: { elbow: 155, shoulder: 105, knee: 160, armSwing: -10, hipSwing: 0 },
  receive: { elbow: 174, shoulder: 68, knee: 132, armSwing: 6, hipSwing: 0 },
  set: { elbow: 154, shoulder: 150, knee: 152, armSwing: 0, hipSwing: 0 },
  default: { elbow: 155, shoulder: 95, knee: 150, armSwing: 0, hipSwing: 0 },
};
const ACTUAL_TARGET_KEYS = [
  "elbowL", "elbowR",
  "shoulderL", "shoulderR",
  "kneeL", "kneeR",
  "armSwingL", "armSwingR",
  "hipSwingL", "hipSwingR",
];
const ACTUAL_SINGLE_PROGRESS = {
  spike: 0.68,
  block: 0.58,
  serve: 0.58,
  receive: 0.45,
  set: 0.52,
  default: 0.55,
};
const STATUS_RANK_3D = { green: 0, yellow: 1, red: 2 };

const JOINT_MARKERS = [
  { index: 11, joint: "shoulder", radius: 0.044 },
  { index: 12, joint: "shoulder", radius: 0.044 },
  { index: 13, joint: "elbow", radius: 0.04 },
  { index: 14, joint: "elbow", radius: 0.04 },
  { index: 15, joint: "wrist", radius: 0.036 },
  { index: 16, joint: "wrist", radius: 0.036 },
  { index: 23, joint: null, radius: 0.046 },
  { index: 24, joint: null, radius: 0.046 },
  { index: 25, joint: "knee", radius: 0.044 },
  { index: 26, joint: "knee", radius: 0.044 },
  { index: 27, joint: null, radius: 0.034 },
  { index: 28, joint: null, radius: 0.034 },
];

// Krunk figurine meshes (sliced from Brave Krunk.stl by tools/segment_krunk.py).
// Each bone part is normalized: proximal joint at the origin, distal at Y=1,
// all axes divided by the model bone length, so a single uniform scale places
// it between two pose landmarks with its proportions intact. head/torso/hips
// share the torso frame (centered at hip-mid, +Y toward shoulder-mid).
const KRUNK_ASSET_URL = new URL("./assets/krunk-parts.json", import.meta.url).href;
const KRUNK_BONES = {
  upper_arm_L: { a: 11, b: 13, joint: "shoulder" },
  forearm_L: { a: 13, b: 15, joint: "elbow" },
  upper_arm_R: { a: 12, b: 14, joint: "shoulder" },
  forearm_R: { a: 14, b: 16, joint: "elbow" },
  thigh_L: { a: 23, b: 25, joint: "knee" },
  shin_L: { a: 25, b: 27, joint: "knee" },
  thigh_R: { a: 24, b: 26, joint: "knee" },
  shin_R: { a: 26, b: 28, joint: "knee" },
};
const KRUNK_TORSO_PARTS = ["torso", "hips", "head"];

let krunkPartsPromise = null;
function loadKrunkParts() {
  if (!krunkPartsPromise) {
    krunkPartsPromise = fetch(KRUNK_ASSET_URL)
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("krunk asset"))))
      .then((data) => {
        const geometries = {};
        for (const [name, part] of Object.entries(data.parts || {})) {
          const geometry = new THREE.BufferGeometry();
          const positions = new Float32Array(part.positions.length * 3);
          part.positions.forEach((p, i) => {
            positions[i * 3] = p[0];
            positions[i * 3 + 1] = p[1];
            positions[i * 3 + 2] = p[2];
          });
          const indices = [];
          for (const face of part.faces) indices.push(face[0], face[1], face[2]);
          geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
          geometry.setIndex(indices);
          geometry.computeVertexNormals();
          geometries[name] = geometry;
        }
        return { figure: data.figure || {}, geometries };
      })
      .catch(() => null);
  }
  return krunkPartsPromise;
}

function orientKrunkPart(mesh, proximal, distal) {
  const dir = distal.clone().sub(proximal);
  const length = Math.max(dir.length(), 0.001);
  mesh.position.copy(proximal);
  mesh.scale.setScalar(length);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
}

// The torso needs the SAME treatment plus one more degree of freedom.
// setFromUnitVectors gives the shortest-arc rotation, which carries no twist
// about the direction it aligns to -- and for the torso that direction is the
// hip-to-shoulder spine, which is exactly the axis the trunk rotates about. So
// a torso oriented that way stays front-facing no matter how far the shoulders
// turn, leaving the arms swinging around a chest that never moves.
// Building the full basis from the spine AND the shoulder line fixes it. With
// the shoulders square this reduces to the same identity rotation as before, so
// nothing changes for actions that do not turn (block, and every neutral pose).
function orientKrunkTorso(mesh, proximal, distal, shoulderVec) {
  const dir = distal.clone().sub(proximal);
  const length = Math.max(dir.length(), 0.001);
  mesh.position.copy(proximal);
  mesh.scale.setScalar(length);
  const up = dir.clone().normalize();
  const right = shoulderVec.clone().sub(up.clone().multiplyScalar(shoulderVec.dot(up)));
  if (right.lengthSq() < 1e-8) {
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), up);
    return;
  }
  // NOT negated. The vectors arriving here have already been through toVec3(),
  // which flips the y-down landmark convention into three.js's y-up, so the
  // spine is +Y and the old setFromUnitVectors(+Y, spine) was plain identity on
  // a square pose. Building the basis from +right reproduces that identity
  // exactly and adds only the twist; negating it would yaw the chest 180
  // degrees and leave the figure facing backwards on every pose.
  right.normalize();
  const forward = new THREE.Vector3().crossVectors(right, up).normalize();
  mesh.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(right, up, forward));
}

function statusColor(joint, jointStatus) {
  if (!joint) return BODY_COLOR;
  return STATUS_COLOR[jointStatus?.[joint] || "green"];
}

function applyStatusMaterial(material, color, status = "green") {
  material.color.setHex(color);
  if (!material.emissive) return;
  if (status === "red") {
    material.emissive.setHex(0x5a1010);
    material.emissiveIntensity = 0.42;
  } else if (status === "yellow") {
    material.emissive.setHex(0x4a3600);
    material.emissiveIntensity = 0.32;
  } else {
    material.emissive.setHex(0x000000);
    material.emissiveIntensity = 0;
  }
}

function landmarkTriple(point) {
  if (Array.isArray(point) && point.length >= 3) {
    const triple = [Number(point[0]), Number(point[1]), Number(point[2])];
    return triple.every(Number.isFinite) ? triple : null;
  }
  if (point && typeof point === "object") {
    const triple = [Number(point.x), Number(point.y), Number(point.z ?? 0)];
    return triple.every(Number.isFinite) ? triple : null;
  }
  return null;
}

function toVec3(point) {
  const triple = landmarkTriple(point) || [0, 0, 0];
  // Flip y so the y-down landmark convention becomes Three.js's y-up.
  return new THREE.Vector3(triple[0], -triple[1], triple[2]);
}

function isFiniteTriple(point) {
  return !!landmarkTriple(point);
}

function averageTriple(points) {
  const valid = points.map(landmarkTriple).filter(Boolean);
  if (!valid.length) return [0, 0, 0];
  return valid.reduce(
    (sum, point) => [sum[0] + point[0], sum[1] + point[1], sum[2] + point[2]],
    [0, 0, 0],
  ).map((value) => value / valid.length);
}

function poseDisplayCenter(points) {
  const hips = [points[23], points[24]].filter(isFiniteTriple);
  if (hips.length) return averageTriple(hips);
  const shoulders = [points[11], points[12]].filter(isFiniteTriple);
  if (shoulders.length) return averageTriple(shoulders);
  return averageTriple(points);
}

function poseBounds(points) {
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  for (const point of points) {
    const triple = landmarkTriple(point);
    if (!triple) continue;
    for (let axis = 0; axis < 3; axis += 1) {
      min[axis] = Math.min(min[axis], triple[axis]);
      max[axis] = Math.max(max[axis], triple[axis]);
    }
  }
  if (!Number.isFinite(min[0])) return { min: [0, 0, 0], max: [0, 0, 0], size: [1, 1, 1] };
  return { min, max, size: [max[0] - min[0], max[1] - min[1], max[2] - min[2]] };
}

function averageAxis(points, indices, axis) {
  const values = indices
    .map((index) => landmarkTriple(points[index]))
    .filter(Boolean)
    .map((point) => point[axis])
    .filter(Number.isFinite);
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function shouldConvertYUpToYDown(points) {
  const headY = averageAxis(points, [0, 7, 8, 9, 10], 1);
  const footY = averageAxis(points, [27, 28, 29, 30, 31, 32], 1);
  return headY !== null && footY !== null && headY > footY;
}

function poseDisplayHeight(points, bounds) {
  const headY = averageAxis(points, [0, 7, 8, 9, 10], 1);
  const footY = averageAxis(points, [27, 28, 29, 30, 31, 32], 1);
  if (headY !== null && footY !== null && footY > headY) {
    return Math.max(footY - headY, 0.35);
  }
  const shoulderY = averageAxis(points, [11, 12], 1);
  const hipY = averageAxis(points, [23, 24], 1);
  if (shoulderY !== null && hipY !== null && hipY > shoulderY) {
    return Math.max((hipY - shoulderY) * 2.45, 0.35);
  }
  return Math.max(bounds.size[1], 0.35);
}

function compressDepth(points, maxDepth) {
  const bounds = poseBounds(points);
  if (bounds.size[2] <= maxDepth) return points;
  const centerZ = (bounds.min[2] + bounds.max[2]) / 2;
  const scale = maxDepth / bounds.size[2];
  return points.map((point) => [point[0], point[1], centerZ + (point[2] - centerZ) * scale]);
}

function enforcePairWidth(points, leftIdx, rightIdx, targetWidth) {
  const left = points[leftIdx];
  const right = points[rightIdx];
  if (!isFiniteTriple(left) || !isFiniteTriple(right)) return;
  const current = Math.abs(right[0] - left[0]);
  if (current >= targetWidth) return;
  const midX = (left[0] + right[0]) / 2;
  left[0] = midX - targetWidth / 2;
  right[0] = midX + targetWidth / 2;
}

function addFallbackDepth(points) {
  const bounds = poseBounds(points);
  if (bounds.size[2] >= 0.18) return;
  for (const [key, offset] of Object.entries(FALLBACK_DEPTH_OFFSETS)) {
    const index = Number(key);
    if (isFiniteTriple(points[index])) points[index][2] += offset;
  }
}

function rawPoseTriples(landmarks) {
  if (!landmarks || landmarks.length < 33) return landmarks;
  let raw = landmarks.map((point) => landmarkTriple(point) || [0, 0, 0]);
  if (shouldConvertYUpToYDown(raw)) {
    raw = raw.map((point) => [point[0], -point[1], point[2]]);
  }
  return raw;
}

function finitePoseAngle(points, aIdx, bIdx, cIdx, fallback, limits) {
  const a = landmarkTriple(points?.[aIdx]);
  const b = landmarkTriple(points?.[bIdx]);
  const c = landmarkTriple(points?.[cIdx]);
  if (!a || !b || !c) return fallback;
  const ab = vecSub(a, b);
  const cb = vecSub(c, b);
  if (Math.hypot(...ab) < 1e-5 || Math.hypot(...cb) < 1e-5) return fallback;
  const angle = angleBetween(a, b, c);
  if (!Number.isFinite(angle)) return fallback;
  return clamp(angle, limits[0], limits[1]);
}

function finiteLimbSwing(points, startIdx, endIdx, fallback, limits) {
  const start = landmarkTriple(points?.[startIdx]);
  const end = landmarkTriple(points?.[endIdx]);
  if (!start || !end) return fallback;
  const vector = vecSub(end, start);
  if (Math.hypot(...vector) < 1e-5) return fallback;
  const swing = (Math.atan2(vector[2], Math.abs(vector[1]) + 0.08) * 180) / Math.PI;
  if (!Number.isFinite(swing)) return fallback;
  return clamp(swing, limits[0], limits[1]);
}

function retargetDefaults(action) {
  return ACTUAL_RETARGET_DEFAULTS[action] || ACTUAL_RETARGET_DEFAULTS.default;
}

function actualFrameTargets(raw, action) {
  const defaults = retargetDefaults(action);
  const elbowLimits = ACTUAL_RETARGET_LIMITS.elbow;
  const shoulderLimits = ACTUAL_RETARGET_LIMITS.shoulder;
  const kneeLimits = ACTUAL_RETARGET_LIMITS.knee;

  return {
    elbowL: finitePoseAngle(raw, 11, 13, 15, defaults.elbow, elbowLimits),
    elbowR: finitePoseAngle(raw, 12, 14, 16, defaults.elbow, elbowLimits),
    shoulderL: finitePoseAngle(raw, 13, 11, 23, defaults.shoulder, shoulderLimits),
    shoulderR: finitePoseAngle(raw, 14, 12, 24, defaults.shoulder, shoulderLimits),
    kneeL: finitePoseAngle(raw, 23, 25, 27, defaults.knee, kneeLimits),
    kneeR: finitePoseAngle(raw, 24, 26, 28, defaults.knee, kneeLimits),
    armSwingL: finiteLimbSwing(raw, 11, 15, defaults.armSwing, ACTUAL_RETARGET_LIMITS.armSwing),
    armSwingR: finiteLimbSwing(raw, 12, 16, defaults.armSwing, ACTUAL_RETARGET_LIMITS.armSwing),
    hipSwingL: finiteLimbSwing(raw, 23, 27, defaults.hipSwing, ACTUAL_RETARGET_LIMITS.hipSwing),
    hipSwingR: finiteLimbSwing(raw, 24, 28, defaults.hipSwing, ACTUAL_RETARGET_LIMITS.hipSwing),
  };
}

function strongerStatus(first = "green", second = "green") {
  return (STATUS_RANK_3D[second] || 0) > (STATUS_RANK_3D[first] || 0) ? second : first;
}

function mergeDisplayJointStatus(...statuses) {
  const merged = { shoulder: "green", elbow: "green", wrist: "green", knee: "green" };
  for (const status of statuses) {
    for (const joint of Object.keys(merged)) {
      merged[joint] = strongerStatus(merged[joint], status?.[joint] || "green");
    }
  }
  return merged;
}

function aggregateSequenceJointStatus(frames) {
  return mergeDisplayJointStatus(...frames.map((frame) => frame.displayJointStatus || frame.jointStatus));
}

function smoothActualTargetFrames(frames) {
  if (frames.length < 2) return frames;
  let previous = { ...frames[0].targets };
  return frames.map((frame, index) => {
    if (index === 0) return frame;
    const targets = { ...frame.targets };
    for (const key of ACTUAL_TARGET_KEYS) {
      const current = Number(frame.targets[key]);
      const last = Number(previous[key]);
      if (Number.isFinite(current) && Number.isFinite(last)) {
        targets[key] = last + (current - last) * ACTUAL_TARGET_FOLLOW;
      }
    }
    previous = targets;
    return { ...frame, targets };
  });
}

function actionProgress(action, index, count) {
  if (count <= 1) return ACTUAL_SINGLE_PROGRESS[action] ?? ACTUAL_SINGLE_PROGRESS.default;
  return clamp(index / Math.max(1, count - 1), 0, 1);
}

function finiteTimeSeconds(frame) {
  const seconds = Number(frame?.time_seconds ?? frame?.timeSeconds);
  return Number.isFinite(seconds) ? Math.max(0, seconds) : null;
}

function timelineFrames(frames, action) {
  const ordered = frames
    .map((frame, order) => ({ ...frame, order }))
    .sort((a, b) => {
      const at = finiteTimeSeconds(a);
      const bt = finiteTimeSeconds(b);
      if (at !== null && bt !== null && at !== bt) return at - bt;
      if (at !== null && bt === null) return -1;
      if (at === null && bt !== null) return 1;
      return a.order - b.order;
    });
  const times = ordered.map(finiteTimeSeconds);
  const finiteTimes = times.filter((time) => time !== null);
  const firstTime = finiteTimes.length ? finiteTimes[0] : null;
  const lastTime = finiteTimes.length > 1 ? finiteTimes[finiteTimes.length - 1] : null;

  return ordered.map((frame, index) => {
    const currentTime = times[index];
    const nextTime = times.slice(index + 1).find((time) => time !== null && currentTime !== null && time > currentTime);
    const previousTime = [...times.slice(0, index)].reverse().find((time) => time !== null && currentTime !== null && time < currentTime);
    let hold = frame.hold || 720;
    if (currentTime !== null) {
      const delta = nextTime !== undefined
        ? nextTime - currentTime
        : previousTime !== undefined
          ? currentTime - previousTime
          : 0.1;
      hold = clamp(Math.round(delta * 1000), MIN_ACTUAL_HOLD_MS, MAX_ACTUAL_HOLD_MS);
    }

    let progress = actionProgress(action, index, ordered.length);
    if (currentTime !== null && firstTime !== null && lastTime !== null && lastTime > firstTime) {
      progress = clamp((currentTime - firstTime) / (lastTime - firstTime), 0, 1);
    }
    return { ...frame, hold, progress };
  });
}

function stripTimelineFromCaption(value, fallback = "影片中的動作") {
  const text = String(value || fallback || "").trim();
  return text
    .replace(/^影片時間\s*\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s*秒[：:]\s*/, "")
    .replace(/^第\s*\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s*秒[：:]\s*/, "")
    .trim() || fallback;
}

function relativeSecondCaption(elapsedMs, totalDurationMs, frameCaption, fallbackCaption) {
  const totalSeconds = Math.max(1, Math.round(totalDurationMs / 1000));
  const second = Math.min(totalSeconds, Math.floor(Math.max(0, elapsedMs) / 1000) + 1);
  return `第 ${second} 秒：${stripTimelineFromCaption(frameCaption, fallbackCaption)}`;
}

function sampleActionGuide(action, progress) {
  const guide = buildSequence(action, "correct");
  if (!guide.length) {
    return { points: BASE_POSE.map((point) => [...point]), ball: null, caption: "" };
  }

  const totalDuration = guide.reduce((sum, frame) => sum + (frame.hold || 720), 0);
  const elapsed = clamp(progress, 0, 0.999999) * totalDuration;
  let cursor = 0;
  let index = guide.length - 1;
  for (let i = 0; i < guide.length; i += 1) {
    const hold = guide[i].hold || 720;
    if (elapsed < cursor + hold) {
      index = i;
      break;
    }
    cursor += hold;
  }
  const current = guide[index];
  const next = guide[(index + 1) % guide.length];
  const hold = current.hold || 720;
  const localT = easeInOut(Math.min(1, (elapsed - cursor) / hold));

  return {
    points: lerpTriples(current.points, next.points, localT),
    ball: current.ball && next.ball
      ? lerpTriple(current.ball, next.ball, localT)
      : (current.ball || next.ball || null),
    caption: current.caption || next.caption || "",
  };
}

function hasJointIssue(jointStatus, joint) {
  const status = jointStatus?.[joint];
  return status === "yellow" || status === "red";
}

function rotateToFiniteTarget(points, aIdx, bIdx, cIdx, distalIdxs, targetDeg) {
  if (!Number.isFinite(Number(targetDeg))) return;
  rotateToAngle(points, aIdx, bIdx, cIdx, distalIdxs, Number(targetDeg));
}

function applyActualIssueTargets(points, targets, jointStatus, action) {
  for (const side of ["L", "R"]) {
    const arm = ARM_CHAIN[side];
    const leg = LEG_CHAIN[side];
    if (hasJointIssue(jointStatus, "shoulder")) {
      rotateToFiniteTarget(
        points,
        arm.elbow,
        arm.shoulder,
        leg.hip,
        [arm.elbow, ...arm.hand],
        targets[`shoulder${side}`] ?? targets.shoulder,
      );
    }
    if (hasJointIssue(jointStatus, "elbow")) {
      rotateToFiniteTarget(
        points,
        arm.shoulder,
        arm.elbow,
        arm.wrist,
        arm.hand,
        targets[`elbow${side}`] ?? targets.elbow,
      );
    }
    if (hasJointIssue(jointStatus, "knee")) {
      rotateToFiniteTarget(
        points,
        leg.hip,
        leg.knee,
        leg.ankle,
        leg.foot,
        targets[`knee${side}`] ?? targets.knee,
      );
    }
  }
  constrainHumanProportions(points);
}

function retargetActualTargets(targets, action, frameStatus, guide) {
  const points = guide?.points ? guide.points.map((point) => [...point]) : buildPose(targets);
  applyActualIssueTargets(points, targets, frameStatus, action);
  return points;
}

function retargetActualPose(raw, action, jointStatus) {
  const guide = sampleActionGuide(action, ACTUAL_SINGLE_PROGRESS[action] ?? ACTUAL_SINGLE_PROGRESS.default);
  return retargetActualTargets(actualFrameTargets(raw, action), action, jointStatus, guide);
}

function normalizePosePoints(raw, center, scale) {
  return raw.map((point) => [
    (point[0] - center[0]) * scale,
    (point[1] - center[1]) * scale,
    (point[2] - center[2]) * scale,
  ]);
}

function applyMinimumDisplayWidths(points) {
  for (const [leftIdx, rightIdx, width] of MIN_DISPLAY_WIDTHS) {
    enforcePairWidth(points, leftIdx, rightIdx, width);
  }
}

function medianNumber(values, fallback = 0) {
  const finite = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!finite.length) return fallback;
  const middle = Math.floor(finite.length / 2);
  return finite.length % 2 ? finite[middle] : (finite[middle - 1] + finite[middle]) / 2;
}

function medianTriple(values, fallback = [0, 0, 0]) {
  return [0, 1, 2].map((axis) => medianNumber(values.map((point) => point?.[axis]), fallback[axis]));
}

function sequenceAxisBounds(frames, axis) {
  let min = Infinity;
  let max = -Infinity;
  for (const frame of frames) {
    for (const point of frame.points) {
      if (!isFiniteTriple(point)) continue;
      min = Math.min(min, point[axis]);
      max = Math.max(max, point[axis]);
    }
  }
  if (!Number.isFinite(min)) return { min: 0, max: 0, size: 0 };
  return { min, max, size: max - min };
}

function compressDepthAcrossFrames(frames, maxDepth) {
  const depth = sequenceAxisBounds(frames, 2);
  if (depth.size <= maxDepth) return frames;
  const centerZ = (depth.min + depth.max) / 2;
  const scale = maxDepth / depth.size;
  return frames.map((frame) => ({
    ...frame,
    points: frame.points.map((point) => [point[0], point[1], centerZ + (point[2] - centerZ) * scale]),
  }));
}

function addFallbackDepthAcrossFrames(frames) {
  const depth = sequenceAxisBounds(frames, 2);
  if (depth.size >= 0.18) return frames;
  return frames.map((frame) => {
    const points = frame.points.map((point) => [...point]);
    for (const [key, offset] of Object.entries(FALLBACK_DEPTH_OFFSETS)) {
      const index = Number(key);
      if (isFiniteTriple(points[index])) points[index][2] += offset;
    }
    return { ...frame, points };
  });
}

function shiftPose(points, delta) {
  return points.map((point) => [point[0] + delta[0], point[1] + delta[1], point[2] + delta[2]]);
}

function smoothTriple(previous, current, follow) {
  return [
    previous[0] + (current[0] - previous[0]) * follow,
    previous[1] + (current[1] - previous[1]) * follow,
    previous[2] + (current[2] - previous[2]) * follow,
  ];
}

function stabilizeSequenceRoots(frames) {
  if (frames.length < 2) return frames;
  let stableRoot = poseDisplayCenter(frames[0].points);
  return frames.map((frame, index) => {
    const root = poseDisplayCenter(frame.points);
    if (index > 0) stableRoot = smoothTriple(stableRoot, root, SEQUENCE_ROOT_FOLLOW);
    return { ...frame, points: shiftPose(frame.points, vecSub(stableRoot, root)) };
  });
}

function smoothSequencePoints(frames) {
  if (frames.length < 2) return frames;
  let previous = frames[0].points.map((point) => [...point]);
  return frames.map((frame, index) => {
    if (index === 0) return frame;
    const points = frame.points.map((point, pointIndex) => smoothTriple(previous[pointIndex], point, SEQUENCE_POINT_FOLLOW));
    previous = points.map((point) => [...point]);
    return { ...frame, points };
  });
}

function preparePoseForDisplay(landmarks) {
  const raw = rawPoseTriples(landmarks);
  if (!raw || raw.length < 33) return landmarks;
  const center = poseDisplayCenter(raw);
  const rawBounds = poseBounds(raw);
  const height = poseDisplayHeight(raw, rawBounds);
  const scale = clamp(DISPLAY_TARGET_HEIGHT / height, 0.4, 5);
  let prepared = normalizePosePoints(raw, center, scale);
  prepared = compressDepth(prepared, DISPLAY_TARGET_HEIGHT * 0.75);

  applyMinimumDisplayWidths(prepared);
  addFallbackDepth(prepared);
  return prepared;
}

function preparePoseSequenceForDisplay(sequence, { caption = "", action = "spike" } = {}) {
  const rawFrames = timelineFrames((sequence || [])
    .filter((frame) => frame.landmarks?.length >= 33)
    .map((frame) => ({
      raw: rawPoseTriples(frame.landmarks),
      landmarks: frame.landmarks,
      jointStatus: frame.joint_status || frame.jointStatus || {},
      displayJointStatus: frame.display_joint_status || frame.displayJointStatus || frame.joint_status || frame.jointStatus || {},
      timeSeconds: finiteTimeSeconds(frame),
      hold: frame.hold || 720,
      caption: frame.caption || caption,
    }))
    .filter((frame) => frame.raw?.length >= 33), action);

  if (!rawFrames.length) return [];
  const sequenceStatus = aggregateSequenceJointStatus(rawFrames);
  if (rawFrames.length === 1) {
    return rawFrames.map((frame, index) => {
      const progress = frame.progress ?? actionProgress(action, index, rawFrames.length);
      const guide = sampleActionGuide(action, progress);
      const displayStatus = mergeDisplayJointStatus(frame.displayJointStatus, sequenceStatus);
      return {
        points: retargetActualTargets(actualFrameTargets(frame.raw, action), action, frame.jointStatus, guide),
        ball: guide.ball,
        jointStatus: displayStatus,
        hold: frame.hold,
        caption: frame.caption || guide.caption,
      };
    });
  }

  let targetFrames = rawFrames.map((frame, index) => {
    const progress = frame.progress ?? actionProgress(action, index, rawFrames.length);
    return {
      targets: actualFrameTargets(frame.raw, action),
      frameStatus: frame.jointStatus,
      displayStatus: mergeDisplayJointStatus(frame.displayJointStatus, sequenceStatus),
      progress,
      hold: frame.hold,
      caption: frame.caption,
    };
  });
  targetFrames = smoothActualTargetFrames(targetFrames);

  let frames = targetFrames.map((frame) => {
    const guide = sampleActionGuide(action, frame.progress);
    return {
      points: retargetActualTargets(frame.targets, action, frame.frameStatus, guide),
      ball: guide.ball,
      jointStatus: frame.displayStatus,
      hold: frame.hold,
      caption: frame.caption || guide.caption,
    };
  });

  frames = smoothSequencePoints(frames);
  return frames;
}

function offsetPoseIndices(points, indices, dx = 0, dy = 0, dz = 0) {
  for (const index of indices) {
    if (!isFiniteTriple(points[index])) continue;
    points[index][0] += dx;
    points[index][1] += dy;
    points[index][2] += dz;
  }
}

function buildSinglePoseMotion(frames) {
  if (frames.length !== 1) return frames;
  const base = frames[0];
  return SINGLE_POSE_MOTION.map((phase) => {
    const points = base.points.map((point) => [...point]);
    offsetPoseIndices(points, UPPER_BODY_INDICES, phase.upperX, phase.upperY, phase.depth);
    offsetPoseIndices(points, LOWER_BODY_INDICES, phase.lowerX, 0, phase.depth * 0.35);
    offsetPoseIndices(points, HAND_INDICES, phase.upperX * 0.35, phase.handY, phase.depth * 0.4);
    return {
      ...base,
      points,
      hold: phase.hold,
    };
  });
}

function orientCapsuleVec(mesh, start, end) {
  const mid = start.clone().add(end).multiplyScalar(0.5);
  const dir = end.clone().sub(start);
  const length = Math.max(dir.length(), 0.001);
  mesh.position.copy(mid);
  mesh.scale.set(1, length, 1);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
}

function orientCapsule(mesh, p1, p2) {
  orientCapsuleVec(mesh, toVec3(p1), toVec3(p2));
}

function midVec3(p1, p2) {
  return toVec3(p1).add(toVec3(p2)).multiplyScalar(0.5);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function safeHeadPosition(points, shoulderMid) {
  const rawHead = toVec3(points[HEAD_INDEX]);
  const shoulderWidth = Math.max(toVec3(points[11]).distanceTo(toVec3(points[12])), 0.25);
  const maxSideOffset = shoulderWidth * 0.55;
  const maxDepthOffset = shoulderWidth * 0.7;
  return new THREE.Vector3(
    shoulderMid.x + clamp(rawHead.x - shoulderMid.x, -maxSideOffset, maxSideOffset),
    clamp(rawHead.y, shoulderMid.y + 0.18, shoulderMid.y + 0.46),
    shoulderMid.z + clamp(rawHead.z - shoulderMid.z, -maxDepthOffset, maxDepthOffset),
  );
}

function makeUnitCapsule(radius, color) {
  const geometry = new THREE.CapsuleGeometry(radius, 1, 4, 8);
  const material = new THREE.MeshStandardMaterial({ color, roughness: 0.65, metalness: 0.04 });
  return new THREE.Mesh(geometry, material);
}

function makeSphere(radius, color, widthSegments = 20, heightSegments = 16) {
  const geometry = new THREE.SphereGeometry(radius, widthSegments, heightSegments);
  const material = new THREE.MeshStandardMaterial({ color, roughness: 0.58, metalness: 0.035 });
  return new THREE.Mesh(geometry, material);
}

function makePalmMesh(color) {
  const geometry = new THREE.SphereGeometry(1, 18, 12);
  const material = new THREE.MeshStandardMaterial({ color, roughness: 0.62, metalness: 0.025 });
  return new THREE.Mesh(geometry, material);
}

function normalizedVec3(vector, fallback = new THREE.Vector3(1, 0, 0)) {
  if (!Number.isFinite(vector.lengthSq()) || vector.lengthSq() < 1e-8) {
    return fallback.clone().normalize();
  }
  return vector.clone().normalize();
}

const HAND_DETAIL_SPECS = {
  L: { wrist: 15, elbow: 13, pinky: 17, index: 19, thumb: 21 },
  R: { wrist: 16, elbow: 14, pinky: 18, index: 20, thumb: 22 },
};

function lerpVec3(a, b, t) {
  return a.clone().lerp(b, t);
}

function ensureFingerTip(base, tip, direction, minLength) {
  const delta = tip.clone().sub(base);
  if (delta.length() >= minLength) return tip;
  return base.clone().add(direction.clone().multiplyScalar(minLength));
}

function handFrame(points, side) {
  const spec = HAND_DETAIL_SPECS[side];
  const wrist = toVec3(points[spec.wrist]);
  const elbow = toVec3(points[spec.elbow]);
  const pinky = toVec3(points[spec.pinky]);
  const index = toVec3(points[spec.index]);
  const thumb = toVec3(points[spec.thumb]);
  const fingerMid = lerpVec3(pinky, index, 0.5);
  const forearm = normalizedVec3(wrist.clone().sub(elbow), new THREE.Vector3(0, 1, 0));
  let yAxis = normalizedVec3(fingerMid.clone().sub(wrist), forearm);
  let xAxis = normalizedVec3(index.clone().sub(pinky), new THREE.Vector3(side === "R" ? 1 : -1, 0, 0));
  let zAxis = xAxis.clone().cross(yAxis);
  if (zAxis.lengthSq() < 1e-8) zAxis = new THREE.Vector3(0, 0, 1);
  zAxis.normalize();
  xAxis = yAxis.clone().cross(zAxis).normalize();
  const width = clamp(index.distanceTo(pinky) * 1.25, 0.085, 0.19);
  const length = clamp(wrist.distanceTo(fingerMid) * 0.95, 0.1, 0.22);
  const center = wrist.clone().add(yAxis.clone().multiplyScalar(length * 0.52));
  return { wrist, pinky, index, thumb, xAxis, yAxis, zAxis, width, length, center };
}

function orientEllipsoid(mesh, center, xAxis, yAxis, zAxis, scaleX, scaleY, scaleZ) {
  const basis = new THREE.Matrix4().makeBasis(xAxis, yAxis, zAxis);
  mesh.position.copy(center);
  mesh.quaternion.setFromRotationMatrix(basis);
  mesh.scale.set(scaleX, scaleY, scaleZ);
}

function orientFinger(mesh, start, end) {
  orientCapsuleVec(mesh, start, end);
}

function createHandDetail(side) {
  const palm = makePalmMesh(BODY_COLOR);
  const fingers = Array.from({ length: 5 }, () => makeUnitCapsule(0.0115, BODY_COLOR));
  const tips = Array.from({ length: 5 }, () => makeSphere(0.017, BODY_COLOR, 12, 8));
  return { side, palm, fingers, tips };
}

function updateHandDetail(detail, points, jointStatus) {
  const frame = handFrame(points, detail.side);
  const wristStatus = jointStatus?.wrist || "green";
  const color = wristStatus === "green" ? BODY_COLOR : STATUS_COLOR[wristStatus];
  applyStatusMaterial(detail.palm.material, color, wristStatus);
  orientEllipsoid(
    detail.palm,
    frame.center,
    frame.xAxis,
    frame.yAxis,
    frame.zAxis,
    frame.width * 0.55,
    frame.length * 0.72,
    0.022,
  );

  const fingerBases = [
    frame.wrist.clone().add(frame.xAxis.clone().multiplyScalar(-frame.width * 0.34)).add(frame.yAxis.clone().multiplyScalar(frame.length * 0.36)),
    frame.wrist.clone().add(frame.xAxis.clone().multiplyScalar(-frame.width * 0.12)).add(frame.yAxis.clone().multiplyScalar(frame.length * 0.42)),
    frame.wrist.clone().add(frame.xAxis.clone().multiplyScalar(frame.width * 0.1)).add(frame.yAxis.clone().multiplyScalar(frame.length * 0.43)),
    frame.wrist.clone().add(frame.xAxis.clone().multiplyScalar(frame.width * 0.32)).add(frame.yAxis.clone().multiplyScalar(frame.length * 0.36)),
    frame.wrist.clone().add(frame.xAxis.clone().multiplyScalar(frame.width * 0.42)).add(frame.yAxis.clone().multiplyScalar(frame.length * 0.18)),
  ];
  const fingerTips = [
    frame.pinky,
    lerpVec3(frame.pinky, frame.index, 0.35).add(frame.yAxis.clone().multiplyScalar(0.032)),
    lerpVec3(frame.pinky, frame.index, 0.62).add(frame.yAxis.clone().multiplyScalar(0.038)),
    frame.index,
    frame.thumb,
  ].map((tip, index) => ensureFingerTip(fingerBases[index], tip, frame.yAxis, index === 4 ? 0.06 : 0.085));

  detail.fingers.forEach((finger, index) => {
    applyStatusMaterial(finger.material, color, wristStatus);
    orientFinger(finger, fingerBases[index], fingerTips[index]);
  });
  detail.tips.forEach((tip, index) => {
    applyStatusMaterial(tip.material, color, wristStatus);
    tip.position.copy(fingerTips[index]);
  });
}

function createFigure(scene) {
  const group = new THREE.Group();
  const limbs = BODY_PARTS.map((part) => ({
    part,
    mesh: makeUnitCapsule(part.radius, BODY_COLOR),
  }));
  for (const limb of limbs) group.add(limb.mesh);

  const torsoMesh = makeUnitCapsule(TORSO_RADIUS, BODY_COLOR);
  group.add(torsoMesh);

  const chestMesh = makeSphere(CHEST_RADIUS, BODY_COLOR);
  group.add(chestMesh);

  const pelvisMesh = makeSphere(PELVIS_RADIUS, BODY_SHADOW_COLOR);
  group.add(pelvisMesh);

  const neckMesh = makeUnitCapsule(NECK_RADIUS, BODY_COLOR);
  group.add(neckMesh);

  const headMesh = makeSphere(HEAD_RADIUS, BODY_COLOR, 24, 18);
  group.add(headMesh);

  const handDetails = ["L", "R"].map(createHandDetail);
  for (const hand of handDetails) {
    group.add(hand.palm);
    for (const finger of hand.fingers) group.add(finger);
    for (const tip of hand.tips) group.add(tip);
  }

  const jointMarkers = JOINT_MARKERS.map((marker) => {
    const geometry = new THREE.SphereGeometry(marker.radius, 16, 12);
    const material = new THREE.MeshStandardMaterial({ color: NEUTRAL_COLOR, roughness: 0.5, metalness: 0.03 });
    const mesh = new THREE.Mesh(geometry, material);
    const haloGeometry = new THREE.SphereGeometry(marker.radius * 1.9, 16, 12);
    const haloMaterial = new THREE.MeshBasicMaterial({
      color: 0xff5d5d,
      transparent: true,
      opacity: 0.24,
      depthWrite: false,
    });
    const halo = new THREE.Mesh(haloGeometry, haloMaterial);
    halo.visible = false;
    group.add(mesh);
    group.add(halo);
    return { ...marker, mesh, geometry, halo, haloGeometry };
  });

  const shadowGeometry = new THREE.CircleGeometry(0.22, 24);
  const shadowMaterial = new THREE.MeshBasicMaterial({ color: 0xffb21a, transparent: true, opacity: 0.2 });
  const shadowMesh = new THREE.Mesh(shadowGeometry, shadowMaterial);
  shadowMesh.rotation.x = -Math.PI / 2;
  shadowMesh.position.y = POSE_GROUND_Y;
  group.add(shadowMesh);

  scene.add(group);

  // Optional Krunk figurine layer. When its asset loads, the sliced mesh parts
  // replace the plain capsules; the capsule figure stays as the fallback.
  const krunk = { active: false, bones: [], torsoParts: [], handLimbs: [], group: new THREE.Group() };
  group.add(krunk.group);

  function attachKrunk(data) {
    if (!data || !data.geometries) return false;
    // DoubleSide: the decimated STL parts have inconsistent triangle winding,
    // so single-sided rendering culls the limb faces and only the head shows.
    const material = () =>
      new THREE.MeshStandardMaterial({
        color: KRUNK_BODY_COLOR,
        roughness: 0.62,
        metalness: 0.04,
        side: THREE.DoubleSide,
      });
    for (const [name, bone] of Object.entries(KRUNK_BONES)) {
      // Arms are now full STL (upper_arm + forearm, shoulder->elbow->wrist); the
      // hand ball is not exported, so finger capsules keep the set (托球) shape.
      const geometry = data.geometries[name];
      if (!geometry) continue;
      const mesh = new THREE.Mesh(geometry, material());
      krunk.group.add(mesh);
      krunk.bones.push({ mesh, ...bone });
    }
    for (const name of KRUNK_TORSO_PARTS) {
      const geometry = data.geometries[name];
      if (!geometry) continue;
      const mesh = new THREE.Mesh(geometry, material());
      krunk.group.add(mesh);
      krunk.torsoParts.push({ mesh, name });
    }
    if (!krunk.bones.length) return false;
    krunk.active = true;
    // Hide the capsule body parts the STL replaces, but keep the forearm and
    // finger capsules — they render the hand and fingers (the STL hand is a
    // featureless ball). Recolor the kept capsules to the Krunk white.
    for (const limb of limbs) {
      // Keep the finger capsules (the STL hand is a featureless ball) and the
      // ankle/heel/toe foot capsules (they articulate the foot at the ankle).
      // The STL now covers the forearm, so its capsule is hidden.
      const isFoot = limb.part.b >= 29 && limb.part.b <= 32;
      const keep = limb.part.joint === "wrist" || isFoot;
      limb.mesh.visible = keep;
      if (keep) {
        applyStatusMaterial(limb.mesh.material, KRUNK_BODY_COLOR, "green");
        krunk.handLimbs.push(limb);
      }
    }
    torsoMesh.visible = false;
    chestMesh.visible = false;
    pelvisMesh.visible = false;
    neckMesh.visible = false;
    headMesh.visible = false;
    return true;
  }

  return {
    group,
    attachKrunk,
    setVisible(visible) {
      group.visible = visible;
    },
    update(points, jointStatus) {
      group.visible = true;
      const shoulderMid = midVec3(points[11], points[12]);
      const hipMid = midVec3(points[23], points[24]);

      if (krunk.active) {
        for (const bone of krunk.bones) {
          orientKrunkPart(bone.mesh, toVec3(points[bone.a]), toVec3(points[bone.b]));
          const status = bone.joint ? jointStatus?.[bone.joint] || "green" : "green";
          const color = status === "green" ? KRUNK_BODY_COLOR : STATUS_COLOR[status];
          applyStatusMaterial(bone.mesh.material, color, status);
        }
        const shoulderVec = toVec3(points[12]).sub(toVec3(points[11]));
        const hipVec = toVec3(points[24]).sub(toVec3(points[23]));
        // krunk-parts.json ships no separate hips part: "torso" is ONE rigid
        // mesh spanning pelvis to shoulders. A twisted trunk has a different
        // yaw at each end, and one rigid mesh cannot honour both -- driving it
        // purely from the shoulders would swing the rendered pelvis with them
        // and visually cancel the hip-shoulder separation the choreography just
        // created (40 degrees of it at spike load). The bisector splits the
        // error, leaving each end off by half instead of the pelvis off by all.
        const midTrunkVec = shoulderVec.clone().normalize().add(hipVec.clone().normalize());
        for (const part of krunk.torsoParts) {
          // The head sits above the shoulders, so it follows them directly.
          const facing = part.name === "head" ? shoulderVec : midTrunkVec;
          orientKrunkTorso(part.mesh, hipMid, shoulderMid, facing);
        }
        for (const limb of krunk.handLimbs) {
          orientCapsule(limb.mesh, points[limb.part.a], points[limb.part.b]);
          const status = limb.part.joint ? jointStatus?.[limb.part.joint] || "green" : "green";
          applyStatusMaterial(limb.mesh.material, status === "green" ? KRUNK_BODY_COLOR : STATUS_COLOR[status], status);
        }
      } else {
        for (const limb of limbs) {
          orientCapsule(limb.mesh, points[limb.part.a], points[limb.part.b]);
          const status = limb.part.joint ? jointStatus?.[limb.part.joint] || "green" : "green";
          applyStatusMaterial(limb.mesh.material, statusColor(limb.part.joint, jointStatus), status);
        }
      }

      for (const hand of handDetails) updateHandDetail(hand, points, jointStatus || {});

      const headPos = safeHeadPosition(points, shoulderMid);
      const torsoTop = shoulderMid.clone().lerp(hipMid, 0.12);
      const torsoBottom = shoulderMid.clone().lerp(hipMid, 0.9);
      const chestPos = shoulderMid.clone().lerp(hipMid, 0.2);
      if (!krunk.active) {
        orientCapsuleVec(torsoMesh, torsoTop, torsoBottom);
        chestMesh.position.copy(chestPos);
        pelvisMesh.position.copy(hipMid);
        const neckTop = headPos.clone();
        neckTop.y -= HEAD_RADIUS * 0.62;
        orientCapsuleVec(neckMesh, shoulderMid.clone().lerp(headPos, 0.18), neckTop);
        headMesh.position.copy(headPos);
      }

      for (const marker of jointMarkers) {
        const position = toVec3(points[marker.index]);
        const status = marker.joint ? jointStatus?.[marker.joint] || "green" : "green";
        marker.mesh.position.copy(position);
        if (krunk.active) {
          // In Krunk mode the markers are permanent white ball-joints that cap
          // the seams between the STL parts (and the capsule forearms/fingers),
          // hiding the decimated part edges; they still turn yellow/red to flag.
          applyStatusMaterial(marker.mesh.material, status === "green" ? KRUNK_BODY_COLOR : STATUS_COLOR[status], status);
          marker.mesh.visible = true;
        } else {
          applyStatusMaterial(marker.mesh.material, statusColor(marker.joint, jointStatus), status);
          marker.mesh.visible = status !== "green";
        }
        marker.halo.position.copy(position);
        marker.halo.visible = status === "yellow" || status === "red";
        if (marker.halo.visible) {
          marker.halo.material.color.setHex(RISK_RING_COLOR[status]);
        }
      }

      const feetY = Math.min(toVec3(points[27]).y, toVec3(points[28]).y);
      const rootX = (toVec3(points[23]).x + toVec3(points[24]).x) / 2;
      const rootZ = (toVec3(points[23]).z + toVec3(points[24]).z) / 2;
      shadowMesh.position.set(rootX, POSE_GROUND_Y, rootZ);
      const heightAboveGround = Math.max(0.001, feetY - POSE_GROUND_Y + 0.05);
      const scale = Math.max(0.32, 1 - heightAboveGround * 0.85);
      shadowMesh.scale.set(scale, scale, scale);
    },
    dispose() {
      for (const limb of limbs) limb.mesh.geometry.dispose();
      torsoMesh.geometry.dispose();
      chestMesh.geometry.dispose();
      pelvisMesh.geometry.dispose();
      neckMesh.geometry.dispose();
      headMesh.geometry.dispose();
      for (const hand of handDetails) {
        hand.palm.geometry.dispose();
        hand.palm.material.dispose();
        for (const finger of hand.fingers) {
          finger.geometry.dispose();
          finger.material.dispose();
        }
        for (const tip of hand.tips) {
          tip.geometry.dispose();
          tip.material.dispose();
        }
      }
      for (const marker of jointMarkers) {
        marker.geometry.dispose();
        marker.haloGeometry.dispose();
      }
      shadowGeometry.dispose();
      scene.remove(group);
    },
  };
}

function createBall(scene) {
  const geometry = new THREE.SphereGeometry(0.11, 20, 16);
  const material = new THREE.MeshStandardMaterial({ color: 0xf4f1ea, roughness: 0.5, metalness: 0.02 });
  const mesh = new THREE.Mesh(geometry, material);
  const seamMaterial = new THREE.MeshBasicMaterial({ color: 0x2b2f34 });
  for (const rotation of [0, Math.PI / 2]) {
    const seam = new THREE.Mesh(new THREE.TorusGeometry(0.11, 0.006, 6, 24), seamMaterial);
    seam.rotation.x = rotation;
    mesh.add(seam);
  }
  scene.add(mesh);
  return {
    mesh,
    setPosition(point) {
      mesh.visible = !!point;
      if (point) mesh.position.copy(toVec3(point));
    },
    dispose() {
      geometry.dispose();
      scene.remove(mesh);
    },
  };
}

// ---------------------------------------------------------------------------
// Public viewport: one Three.js scene bound to a container element.
// ---------------------------------------------------------------------------

export function createPoseViewport(container, { cameraDistance = 2.1, framePadding = 1.35 } = {}) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.05, 30);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  container.appendChild(renderer.domElement);

  const cueEl = document.createElement("div");
  cueEl.className = "pose-3d-cue";
  cueEl.hidden = true;
  container.appendChild(cueEl);

  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const keyLight = new THREE.DirectionalLight(0xffffff, 0.9);
  keyLight.position.set(1.2, 2, 1.5);
  scene.add(keyLight);
  const rimLight = new THREE.DirectionalLight(0xbfe8ff, 0.25);
  rimLight.position.set(-1.5, 0.5, -1.5);
  scene.add(rimLight);

  const figure = createFigure(scene);
  figure.setVisible(false);
  // Krunk STL body, rebuilt by tools/build_krunk_parts.py: each pre-existing
  // body-part component is decimated with pymeshlab's quadric edge-collapse
  // (topology-preserving, no spikes), so the parts stay clean and articulate.
  // Falls back to the capsule mannequin if the asset fails to load.
  loadKrunkParts().then((data) => {
    if (data) figure.attachKrunk(data);
  });
  const ball = createBall(scene);
  ball.setPosition(null);

  let view = "front";
  let lookTarget = new THREE.Vector3(0, 0.15, -0.3);
  let distance = cameraDistance;

  function applyCamera() {
    if (view === "side") {
      camera.position.set(lookTarget.x + distance, lookTarget.y + 0.15, lookTarget.z);
    } else {
      camera.position.set(lookTarget.x, lookTarget.y + 0.15, lookTarget.z + distance);
    }
    camera.lookAt(lookTarget);
  }
  applyCamera();

  function resize() {
    const width = Math.max(1, container.clientWidth);
    const height = Math.max(1, container.clientHeight);
    renderer.setSize(width, height, false);
    renderer.domElement.style.width = `${width}px`;
    renderer.domElement.style.height = `${height}px`;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  resize();

  let animation = null;
  function stopAnimation() {
    if (animation && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(animation.frameId);
    }
    animation = null;
  }

  function draw() {
    renderer.render(scene, camera);
  }

  function setCue(text) {
    cueEl.textContent = text || "";
    cueEl.hidden = !text;
  }

  function setStaticPose(landmarks, jointStatus, { caption = "" } = {}) {
    stopAnimation();
    ball.setPosition(null);
    setCue(caption);
    if (!landmarks || landmarks.length < 33) {
      setCue(caption || "沒有可用的 3D 姿勢");
      figure.setVisible(false);
      draw();
      return;
    }
    const displayLandmarks = preparePoseForDisplay(landmarks);
    const bounds = computeFramesBounds([{ points: displayLandmarks }]);
    const framed = frameCamera(bounds, camera.fov, framePadding, camera.aspect);
    lookTarget = framed.center;
    distance = Math.max(framed.distance, cameraDistance);
    applyCamera();
    figure.setVisible(true);
    figure.update(displayLandmarks, jointStatus);
    draw();
  }

  function playDemo(action, { variant = "correct" } = {}) {
    stopAnimation();
    if (typeof requestAnimationFrame !== "function") return;
    figure.setVisible(true);

    const frames = buildSequence(action, variant);
    const bounds = computeFramesBounds(frames);
    const framed = frameCamera(bounds, camera.fov, framePadding, camera.aspect);
    lookTarget = framed.center;
    distance = framed.distance;
    applyCamera();

    const totalDuration = frames.reduce((sum, frame) => sum + frame.hold * DEMO_SLOW_FACTOR, 0);
    const state = { startTime: null, lastDraw: 0 };
    animation = { frameId: 0 };

    const tick = (timestamp) => {
      if (state.startTime === null) state.startTime = timestamp;
      animation.frameId = requestAnimationFrame(tick);
      if (timestamp - state.lastDraw < FRAME_INTERVAL_MS) return;
      state.lastDraw = timestamp;

      const elapsed = (timestamp - state.startTime) % totalDuration;
      let cursor = 0;
      let index = frames.length - 1;
      for (let i = 0; i < frames.length; i += 1) {
        const hold = frames[i].hold * DEMO_SLOW_FACTOR;
        if (elapsed < cursor + hold) {
          index = i;
          break;
        }
        cursor += hold;
      }
      const nextIndex = (index + 1) % frames.length;
      const localT = easeInOut(Math.min(1, (elapsed - cursor) / (frames[index].hold * DEMO_SLOW_FACTOR)));

      const points = lerpTriples(frames[index].points, frames[nextIndex].points, localT);
      figure.update(points, frames[index].jointStatus);
      setCue(frames[index].caption);

      if (frames[index].ball && frames[nextIndex].ball) {
        ball.setPosition(lerpTriple(frames[index].ball, frames[nextIndex].ball, localT));
      } else {
        ball.setPosition(frames[index].ball || frames[nextIndex].ball || null);
      }

      draw();
    };
    animation.frameId = requestAnimationFrame(tick);
  }

  function playPoseSequence(sequence, { caption = "影片分析到的錯誤姿勢", action = "spike" } = {}) {
    stopAnimation();
    if (!sequence?.length || typeof requestAnimationFrame !== "function") {
      setStaticPose(null, null);
      return;
    }

    let frames = preparePoseSequenceForDisplay(sequence, { caption, action });
    if (!frames.length) {
      setStaticPose(null, null);
      return;
    }
    frames = buildSinglePoseMotion(frames);
    figure.setVisible(true);

    const bounds = computeFramesBounds(frames);
    const framed = frameCamera(bounds, camera.fov, framePadding, camera.aspect);
    lookTarget = framed.center;
    distance = Math.max(framed.distance, cameraDistance);
    applyCamera();

    const totalDuration = frames.reduce((sum, frame) => sum + frame.hold * DEMO_SLOW_FACTOR, 0);
    const state = { startTime: null, lastDraw: 0 };
    animation = { frameId: 0 };

    const tick = (timestamp) => {
      if (state.startTime === null) state.startTime = timestamp;
      animation.frameId = requestAnimationFrame(tick);
      if (timestamp - state.lastDraw < FRAME_INTERVAL_MS) return;
      state.lastDraw = timestamp;

      const elapsed = (timestamp - state.startTime) % totalDuration;
      let cursor = 0;
      let index = frames.length - 1;
      for (let i = 0; i < frames.length; i += 1) {
        const hold = frames[i].hold * DEMO_SLOW_FACTOR;
        if (elapsed < cursor + hold) {
          index = i;
          break;
        }
        cursor += hold;
      }
      const nextIndex = (index + 1) % frames.length;
      const localT = easeInOut(Math.min(1, (elapsed - cursor) / (frames[index].hold * DEMO_SLOW_FACTOR)));
      const points = lerpTriples(frames[index].points, frames[nextIndex].points, localT);
      figure.update(points, frames[index].jointStatus);
      if (frames[index].ball && frames[nextIndex].ball) {
        ball.setPosition(lerpTriple(frames[index].ball, frames[nextIndex].ball, localT));
      } else {
        ball.setPosition(frames[index].ball || frames[nextIndex].ball || null);
      }
      setCue(frames[index].caption);
      draw();
    };
    animation.frameId = requestAnimationFrame(tick);
  }

  function playPoseSequenceForVideo(
    sequence,
    {
      caption = "影片中的實際動作",
      loop = false,
      speedFactor = 1,
      action = "spike",
      playbackSeconds = null,
      timeLabel = "source",
    } = {},
  ) {
    stopAnimation();
    if (!sequence?.length || typeof requestAnimationFrame !== "function") {
      setStaticPose(null, null);
      return;
    }

    let frames = preparePoseSequenceForDisplay(sequence, { caption, action });
    if (!frames.length) {
      setStaticPose(null, null);
      return;
    }
    frames = buildSinglePoseMotion(frames);
    figure.setVisible(true);

    const bounds = computeFramesBounds(frames);
    const framed = frameCamera(bounds, camera.fov, framePadding, camera.aspect);
    lookTarget = framed.center;
    distance = Math.max(framed.distance, cameraDistance);
    applyCamera();

    const baseDuration = frames.reduce((sum, frame) => sum + frame.hold, 0);
    const requestedSeconds = Number(playbackSeconds);
    const durationScale = Number.isFinite(requestedSeconds) && requestedSeconds > 0 && baseDuration > 0
      ? (requestedSeconds * 1000) / baseDuration
      : Math.max(0.25, speedFactor);
    const totalDuration = frames.reduce((sum, frame) => sum + frame.hold * durationScale, 0);
    const state = { startTime: null, lastDraw: 0 };
    animation = { frameId: 0 };

    const tick = (timestamp) => {
      if (state.startTime === null) state.startTime = timestamp;
      if (timestamp - state.lastDraw < FRAME_INTERVAL_MS) {
        animation.frameId = requestAnimationFrame(tick);
        return;
      }
      state.lastDraw = timestamp;

      const rawElapsed = timestamp - state.startTime;
      const elapsed = loop ? rawElapsed % totalDuration : Math.min(rawElapsed, Math.max(0, totalDuration - 1));
      let cursor = 0;
      let index = frames.length - 1;
      for (let i = 0; i < frames.length; i += 1) {
        const hold = frames[i].hold * durationScale;
        if (elapsed < cursor + hold) {
          index = i;
          break;
        }
        cursor += hold;
      }
      const nextIndex = (index + 1) % frames.length;
      const localT = easeInOut(Math.min(1, (elapsed - cursor) / (frames[index].hold * durationScale)));
      const points = lerpTriples(frames[index].points, frames[nextIndex].points, localT);
      figure.update(points, frames[index].jointStatus);
      if (frames[index].ball && frames[nextIndex].ball) {
        ball.setPosition(lerpTriple(frames[index].ball, frames[nextIndex].ball, localT));
      } else {
        ball.setPosition(frames[index].ball || frames[nextIndex].ball || null);
      }
      const cue = timeLabel === "relative-seconds"
        ? relativeSecondCaption(elapsed, totalDuration, frames[index].caption, caption)
        : frames[index].caption;
      setCue(cue);
      draw();

      if (!loop && rawElapsed >= totalDuration) {
        animation = null;
        return;
      }
      animation.frameId = requestAnimationFrame(tick);
    };
    animation.frameId = requestAnimationFrame(tick);
  }

  function setView(nextView) {
    view = nextView === "side" ? "side" : "front";
    applyCamera();
    if (!animation) draw();
  }

  function dispose() {
    stopAnimation();
    figure.dispose();
    ball.dispose();
    renderer.dispose();
    if (renderer.domElement.parentNode === container) container.removeChild(renderer.domElement);
    if (cueEl.parentNode === container) container.removeChild(cueEl);
  }

  return { setStaticPose, playDemo, playPoseSequence: playPoseSequenceForVideo, setView, resize, dispose };
}
