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
    { elbow: 160, knee: 155, shoulder: 95, hold: 720, cue: "攔網預備：膝蓋微彎，雙手在胸前" },
    { elbow: 150, knee: 112, shoulder: 70, hold: 680, cue: "下蹲蓄力：髖、膝、腳踝一起彎" },
    { elbow: 178, knee: 174, shoulder: 178, hold: 820, cue: "向上封網：手臂穿過球，手掌壓住路線" },
    { elbow: 165, knee: 140, shoulder: 120, hold: 620, cue: "落地緩衝：膝蓋對齊腳尖" },
  ],
  serve: [
    { elbow: 160, knee: 170, shoulder: 35, hold: 700, cue: "發球預備：身體側身，非慣用手托球" },
    { elbow: 135, knee: 160, shoulder: 105, hold: 720, cue: "拋球與引臂：肩膀放鬆，不要聳肩" },
    { elbow: 176, knee: 168, shoulder: 172, hold: 760, cue: "最高點擊球：手掌在頭前上方" },
    { elbow: 165, knee: 150, shoulder: 90, hold: 620, cue: "順勢收臂：核心帶動，不硬拉肩膀" },
  ],
  receive: [
    { elbow: 170, knee: 150, shoulder: 55, hold: 700, cue: "接球預備：重心低，腳先到球後面" },
    { elbow: 178, knee: 118, shoulder: 72, hold: 860, cue: "平台鎖穩：手肘伸直，前臂成一整片" },
    { elbow: 176, knee: 135, shoulder: 65, hold: 700, cue: "面向目標：用身體角度送球" },
  ],
  set: [
    { elbow: 150, knee: 158, shoulder: 145, hold: 760, cue: "舉球預備：雙手在額頭上方，手型成三角" },
    { elbow: 158, knee: 146, shoulder: 158, hold: 760, cue: "接球緩衝：手指張開，手腕放鬆" },
    { elbow: 172, knee: 168, shoulder: 168, hold: 820, cue: "腿部送球：膝蓋伸展，球往上走" },
  ],
};

// Full run-up, jump and hit sequence for the spike demo: alternating left/right
// strides, the mannequin's root translating across the court, and a ball that
// is tossed, struck, and flies away. Stylized reference, not a biomechanical
// simulation.
const SPIKE_SEQUENCES = {
  correct: [
  { elbow: 170, knee: 165, shoulder: 12, root: [0, 0, -1.3], hold: 620, cue: "扣球助跑：左腳啟動，眼睛看球", ball: [0.15, -1.3, -0.2] },
  {
    elbow: 165, knee: 155, shoulder: 18, kneeR: 135, hipSwingL: 26, hipSwingR: -22,
    root: [0, 0, -1.0], hold: 520, cue: "扣球腳步 1：左", ball: [0.15, -1.31, -0.16],
  },
  {
    elbow: 158, knee: 150, shoulder: 25, kneeL: 132, hipSwingR: 27, hipSwingL: -23,
    root: [0, 0, -0.65], hold: 520, cue: "扣球腳步 2：右，身體開始蓄力", ball: [0.15, -1.3, -0.1],
  },
  {
    elbow: 148, knee: 140, shoulder: 15, kneeR: 118, hipSwingL: 25, hipSwingR: -20, armSwingL: -20, armSwingR: -20,
    root: [0, 0, -0.28], hold: 520, cue: "扣球腳步 3：左，雙腳準備起跳", ball: [0.16, -1.26, -0.04],
  },
  {
    elbow: 148, knee: 100, shoulder: 6, armSwingL: -32, armSwingR: -32,
    root: [0, 0, -0.02], hold: 560, cue: "擺臂下沉：髖膝一起彎，不要膝蓋內扣", ball: [0.17, -1.2, 0.02],
  },
  {
    elbow: 140, knee: 172, shoulder: 95,
    root: [0, -0.32, 0.05], hold: 520, cue: "起跳：腿部伸展，把身體往上帶", ball: [0.19, -1.05, 0.06],
  },
  {
    elbow: 178, knee: 175, shoulder: 178, elbowL: 150, shoulderL: 60,
    root: [0, -0.5, 0.1], hold: 520, cue: "最高點扣球：手在頭前上方擊球", ballAttach: "wrist_r",
  },
  {
    elbow: 128, knee: 138, shoulder: 55,
    root: [0, -0.16, 0.2], hold: 620, cue: "落地緩衝：雙腳吸收衝擊", ball: [0.65, -0.55, 1.0],
  },
  { elbow: 165, knee: 135, shoulder: 20, root: [0, 0, 0.12], hold: 760, cue: "收尾：維持平衡，準備下一球", ball: [1.05, -0.05, 1.75] },
  ],
};

function setPoint(points, index, x, y, z) {
  points[index] = [x, y, z];
}

function shapeSetHands(points, variant) {
  const head = points[HEAD_INDEX];
  const shoulderCenterX = (points[11][0] + points[12][0]) / 2;
  const z = head[2] + 0.06;
  const wristY = variant === "mistake" ? head[1] + 0.1 : head[1] - 0.18;
  const elbowY = variant === "mistake" ? head[1] + 0.22 : head[1] + 0.04;
  const spread = variant === "mistake" ? 0.22 : 0.12;

  setPoint(points, 13, shoulderCenterX - spread * 1.15, elbowY, z);
  setPoint(points, 14, shoulderCenterX + spread * 1.15, elbowY, z);
  setPoint(points, 15, shoulderCenterX - spread, wristY, z);
  setPoint(points, 16, shoulderCenterX + spread, wristY, z);
  setPoint(points, 17, shoulderCenterX - spread - 0.035, wristY - 0.03, z + 0.015);
  setPoint(points, 18, shoulderCenterX + spread + 0.035, wristY - 0.03, z + 0.015);
  setPoint(points, 19, shoulderCenterX - 0.035, wristY - 0.055, z + 0.02);
  setPoint(points, 20, shoulderCenterX + 0.035, wristY - 0.055, z + 0.02);
  setPoint(points, 21, shoulderCenterX - spread * 0.45, wristY + 0.035, z - 0.005);
  setPoint(points, 22, shoulderCenterX + spread * 0.45, wristY + 0.035, z - 0.005);
}

function shapeReceivePlatform(points, variant) {
  const centerX = (points[23][0] + points[24][0]) / 2;
  const y = variant === "mistake" ? -0.08 : -0.18;
  const z = variant === "mistake" ? -0.02 : -0.08;
  const gap = variant === "mistake" ? 0.2 : 0.045;
  setPoint(points, 13, centerX - 0.2, -0.28, z);
  setPoint(points, 14, centerX + 0.2, -0.28, z);
  setPoint(points, 15, centerX - gap, y, z);
  setPoint(points, 16, centerX + gap, y + (variant === "mistake" ? 0.05 : 0), z);
  setPoint(points, 17, centerX - gap - 0.03, y + 0.03, z);
  setPoint(points, 18, centerX + gap + 0.03, y + 0.03, z);
  setPoint(points, 19, centerX - gap * 0.5, y + 0.045, z);
  setPoint(points, 20, centerX + gap * 0.5, y + 0.045, z);
}

function shapeSpikeContact(points, variant) {
  if (variant !== "correct") return;
  const head = points[HEAD_INDEX];
  setPoint(points, 14, 0.2, head[1] - 0.02, 0.08);
  setPoint(points, 16, 0.26, head[1] - 0.34, 0.12);
  setPoint(points, 18, 0.29, head[1] - 0.36, 0.12);
  setPoint(points, 20, 0.22, head[1] - 0.38, 0.12);
  setPoint(points, 22, 0.28, head[1] - 0.31, 0.1);
}

function applyActionShape(points, action, variant, frame) {
  if (action === "set") shapeSetHands(points, variant);
  if (action === "receive") shapeReceivePlatform(points, variant);
  if (action === "spike" && frame.ballAttach === "wrist_r") shapeSpikeContact(points, variant);
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
  const encoded = CLEAN_REFERENCE_CUES[action]?.[index];
  return encoded ? decodeCue(encoded) : fallback;
}

function buildSequence(action, variant = "correct") {
  void variant;
  if (action === "spike") {
    const sequence = SPIKE_SEQUENCES.correct;
    return sequence.map((frame, index) => {
      const points = buildPose(frame);
      applyActionShape(points, action, "correct", frame);
      let ball = frame.ball;
      if (frame.ballAttach === "wrist_r") ball = points[ARM_CHAIN.R.wrist];
      return {
        points,
        ball,
        hold: frame.hold,
        caption: referenceCue(action, index, frame.cue),
        jointStatus: null,
      };
    });
  }
  const spec = CORRECT_CYCLES[action] || CORRECT_CYCLES.block;
  return spec.map((frame, index) => {
    const points = buildPose(frame);
    applyActionShape(points, action, "correct", frame);
    return {
      points,
      ball: points[ARM_CHAIN.R.wrist],
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
function frameCamera(bounds, fovDeg, padding = 1.35) {
  const center = bounds.min.clone().add(bounds.max).multiplyScalar(0.5);
  const size = bounds.max.clone().sub(bounds.min);
  const halfV = Math.max(size.y / 2, 0.2);
  const halfH = Math.max(size.x, size.z) / 2 || 0.2;
  const halfFov = (fovDeg * Math.PI) / 360;
  const distance = Math.max(halfV, halfH) / Math.tan(halfFov) * padding;
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
  { a: 27, b: 31, radius: 0.035, joint: null },
  { a: 28, b: 32, radius: 0.035, joint: null },
];
const BODY_COLOR = 0xf4efe4;
const BODY_SHADOW_COLOR = 0xd7d0c3;
const NECK_RADIUS = 0.038;
const TORSO_RADIUS = 0.17;
const CHEST_RADIUS = 0.14;
const PELVIS_RADIUS = 0.13;
const HEAD_INDEX = 0;
const HEAD_RADIUS = 0.145;

const NEUTRAL_COLOR = 0xf1e6d3;
const STATUS_COLOR = { green: BODY_COLOR, yellow: 0xffd34f, red: 0xff5d5d };
const RISK_RING_COLOR = { yellow: 0xffc43d, red: 0xff3b3b };
const DEMO_SLOW_FACTOR = 1.75;
const FRAME_INTERVAL_MS = 1000 / 60;
const DISPLAY_TARGET_HEIGHT = 1.65;
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

function statusColor(joint, jointStatus) {
  if (!joint) return BODY_COLOR;
  return STATUS_COLOR[jointStatus?.[joint] || "green"];
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

function preparePoseForDisplay(landmarks) {
  if (!landmarks || landmarks.length < 33) return landmarks;
  let raw = landmarks.map((point) => landmarkTriple(point) || [0, 0, 0]);
  if (shouldConvertYUpToYDown(raw)) {
    raw = raw.map((point) => [point[0], -point[1], point[2]]);
  }
  const center = poseDisplayCenter(raw);
  const rawBounds = poseBounds(raw);
  const height = poseDisplayHeight(raw, rawBounds);
  const scale = clamp(DISPLAY_TARGET_HEIGHT / height, 0.4, 5);
  let prepared = raw.map((point) => [
    (point[0] - center[0]) * scale,
    (point[1] - center[1]) * scale,
    (point[2] - center[2]) * scale,
  ]);
  prepared = compressDepth(prepared, DISPLAY_TARGET_HEIGHT * 0.75);

  for (const [leftIdx, rightIdx, width] of MIN_DISPLAY_WIDTHS) {
    enforcePairWidth(prepared, leftIdx, rightIdx, width);
  }
  addFallbackDepth(prepared);
  return prepared;
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
  const shadowMaterial = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.22 });
  const shadowMesh = new THREE.Mesh(shadowGeometry, shadowMaterial);
  shadowMesh.rotation.x = -Math.PI / 2;
  shadowMesh.position.y = 0.001;
  group.add(shadowMesh);

  scene.add(group);

  return {
    group,
    setVisible(visible) {
      group.visible = visible;
    },
    update(points, jointStatus) {
      group.visible = true;
      for (const limb of limbs) {
        orientCapsule(limb.mesh, points[limb.part.a], points[limb.part.b]);
        limb.mesh.material.color.setHex(statusColor(limb.part.joint, jointStatus));
      }
      const shoulderMid = midVec3(points[11], points[12]);
      const hipMid = midVec3(points[23], points[24]);
      const headPos = safeHeadPosition(points, shoulderMid);
      const torsoTop = shoulderMid.clone().lerp(hipMid, 0.12);
      const torsoBottom = shoulderMid.clone().lerp(hipMid, 0.9);
      const chestPos = shoulderMid.clone().lerp(hipMid, 0.2);
      orientCapsuleVec(torsoMesh, torsoTop, torsoBottom);
      chestMesh.position.copy(chestPos);
      pelvisMesh.position.copy(hipMid);
      const neckTop = headPos.clone();
      neckTop.y -= HEAD_RADIUS * 0.62;
      orientCapsuleVec(neckMesh, shoulderMid.clone().lerp(headPos, 0.18), neckTop);
      headMesh.position.copy(headPos);

      for (const marker of jointMarkers) {
        const position = toVec3(points[marker.index]);
        const status = marker.joint ? jointStatus?.[marker.joint] || "green" : "green";
        marker.mesh.position.copy(position);
        marker.mesh.material.color.setHex(statusColor(marker.joint, jointStatus));
        marker.mesh.visible = status !== "green";
        marker.halo.position.copy(position);
        marker.halo.visible = status === "yellow" || status === "red";
        if (marker.halo.visible) {
          marker.halo.material.color.setHex(RISK_RING_COLOR[status]);
        }
      }

      const feetY = Math.max(toVec3(points[27]).y, toVec3(points[28]).y);
      const rootX = (toVec3(points[23]).x + toVec3(points[24]).x) / 2;
      const rootZ = (toVec3(points[23]).z + toVec3(points[24]).z) / 2;
      shadowMesh.position.set(rootX, 0.001, rootZ);
      const heightAboveGround = Math.max(0.001, feetY - shadowMesh.position.y + 0.05);
      const scale = Math.max(0.35, 1 - heightAboveGround * 0.6);
      shadowMesh.scale.set(scale, scale, scale);
    },
    dispose() {
      for (const limb of limbs) limb.mesh.geometry.dispose();
      torsoMesh.geometry.dispose();
      chestMesh.geometry.dispose();
      pelvisMesh.geometry.dispose();
      neckMesh.geometry.dispose();
      headMesh.geometry.dispose();
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
  const ball = createBall(scene);
  ball.setPosition(null);

  let view = "front";
  let lookTarget = new THREE.Vector3(0, 0.15, -0.3);
  let distance = cameraDistance;

  function applyCamera() {
    if (view === "side") {
      camera.position.set(distance, lookTarget.y + 0.15, lookTarget.z);
    } else {
      camera.position.set(0, lookTarget.y + 0.15, lookTarget.z + distance);
    }
    camera.lookAt(lookTarget);
  }
  applyCamera();

  function resize() {
    const width = Math.max(1, container.clientWidth);
    const height = Math.max(1, container.clientHeight);
    renderer.setSize(width, height, false);
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
    const framed = frameCamera(bounds, camera.fov, framePadding);
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
    const framed = frameCamera(bounds, camera.fov, framePadding);
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
        ball.setPosition(null);
      }

      draw();
    };
    animation.frameId = requestAnimationFrame(tick);
  }

  function playPoseSequence(sequence, { caption = "影片分析到的錯誤姿勢" } = {}) {
    stopAnimation();
    if (!sequence?.length || typeof requestAnimationFrame !== "function") {
      setStaticPose(null, null);
      return;
    }

    let frames = sequence
      .filter((frame) => frame.landmarks?.length >= 33)
      .map((frame) => ({
        points: preparePoseForDisplay(frame.landmarks),
        jointStatus: frame.joint_status || frame.jointStatus || {},
        hold: frame.hold || 720,
        caption: frame.caption || caption,
      }));
    if (!frames.length) {
      setStaticPose(null, null);
      return;
    }
    frames = buildSinglePoseMotion(frames);
    figure.setVisible(true);

    const bounds = computeFramesBounds(frames);
    const framed = frameCamera(bounds, camera.fov, framePadding);
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
      ball.setPosition(null);
      setCue(frames[index].caption);
      draw();
    };
    animation.frameId = requestAnimationFrame(tick);
  }

  function playPoseSequenceForVideo(sequence, { caption = "影片中的實際動作", loop = false, speedFactor = 1 } = {}) {
    stopAnimation();
    if (!sequence?.length || typeof requestAnimationFrame !== "function") {
      setStaticPose(null, null);
      return;
    }

    let frames = sequence
      .filter((frame) => frame.landmarks?.length >= 33)
      .map((frame) => ({
        points: preparePoseForDisplay(frame.landmarks),
        jointStatus: frame.joint_status || frame.jointStatus || {},
        hold: frame.hold || 720,
        caption: frame.caption || caption,
      }));
    if (!frames.length) {
      setStaticPose(null, null);
      return;
    }
    frames = buildSinglePoseMotion(frames);
    figure.setVisible(true);

    const bounds = computeFramesBounds(frames);
    const framed = frameCamera(bounds, camera.fov, framePadding);
    lookTarget = framed.center;
    distance = Math.max(framed.distance, cameraDistance);
    applyCamera();

    const durationScale = Math.max(0.25, speedFactor);
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
      ball.setPosition(null);
      setCue(frames[index].caption);
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
