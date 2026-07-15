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

const SIMPLE_CYCLES = {
  block: [
    { elbow: 150, knee: 150, shoulder: 55, hold: 450 },
    { elbow: 140, knee: 108, shoulder: 40, hold: 350 },
    { elbow: 178, knee: 172, shoulder: 178, hold: 450 },
  ],
  serve: [
    { elbow: 160, knee: 170, shoulder: 30, hold: 450 },
    { elbow: 125, knee: 165, shoulder: 85, hold: 350 },
    { elbow: 172, knee: 168, shoulder: 172, hold: 450 },
  ],
  receive: [
    { elbow: 170, knee: 160, shoulder: 30, hold: 450 },
    { elbow: 176, knee: 108, shoulder: 72, hold: 500 },
    { elbow: 170, knee: 150, shoulder: 40, hold: 350 },
  ],
  set: [
    { elbow: 148, knee: 158, shoulder: 100, hold: 400 },
    { elbow: 155, knee: 148, shoulder: 152, hold: 350 },
    { elbow: 170, knee: 165, shoulder: 162, hold: 450 },
  ],
};

// Full run-up, jump and hit sequence for the spike demo: alternating left/right
// strides, the mannequin's root translating across the court, and a ball that
// is tossed, struck, and flies away. Stylized reference, not a biomechanical
// simulation.
const SPIKE_SEQUENCE = [
  { elbow: 170, knee: 165, shoulder: 12, root: [0, 0, -1.3], hold: 320, ball: [0.15, -1.3, -0.2] },
  {
    elbow: 165, knee: 155, shoulder: 18, kneeR: 135, hipSwingL: 26, hipSwingR: -22,
    root: [0, 0, -1.0], hold: 220, ball: [0.15, -1.31, -0.16],
  },
  {
    elbow: 158, knee: 150, shoulder: 25, kneeL: 132, hipSwingR: 27, hipSwingL: -23,
    root: [0, 0, -0.65], hold: 210, ball: [0.15, -1.3, -0.1],
  },
  {
    elbow: 148, knee: 140, shoulder: 15, kneeR: 118, hipSwingL: 25, hipSwingR: -20, armSwingL: -20, armSwingR: -20,
    root: [0, 0, -0.28], hold: 200, ball: [0.16, -1.26, -0.04],
  },
  {
    elbow: 148, knee: 100, shoulder: 6, armSwingL: -32, armSwingR: -32,
    root: [0, 0, -0.02], hold: 210, ball: [0.17, -1.2, 0.02],
  },
  {
    elbow: 140, knee: 172, shoulder: 95,
    root: [0, -0.32, 0.05], hold: 200, ball: [0.19, -1.05, 0.06],
  },
  {
    elbow: 178, knee: 175, shoulder: 178, elbowL: 150, shoulderL: 60,
    root: [0, -0.5, 0.1], hold: 170, ballAttach: "wrist_r",
  },
  {
    elbow: 128, knee: 138, shoulder: 55,
    root: [0, -0.16, 0.2], hold: 230, ball: [0.65, -0.55, 1.0],
  },
  { elbow: 165, knee: 115, shoulder: 20, root: [0, 0, 0.12], hold: 320, ball: [1.05, -0.05, 1.75] },
];

function buildSequence(action) {
  if (action === "spike") {
    return SPIKE_SEQUENCE.map((frame) => {
      const points = buildPose(frame);
      let ball = frame.ball;
      if (frame.ballAttach === "wrist_r") ball = points[ARM_CHAIN.R.wrist];
      return { points, ball, hold: frame.hold };
    });
  }
  const spec = SIMPLE_CYCLES[action] || SIMPLE_CYCLES.block;
  return spec.map((frame) => {
    const points = buildPose(frame);
    return { points, ball: points[ARM_CHAIN.R.wrist], hold: frame.hold };
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
function frameCamera(bounds, fovDeg) {
  const center = bounds.min.clone().add(bounds.max).multiplyScalar(0.5);
  const size = bounds.max.clone().sub(bounds.min);
  const halfV = Math.max(size.y / 2, 0.2);
  const halfH = Math.max(size.x, size.z) / 2 || 0.2;
  const halfFov = (fovDeg * Math.PI) / 360;
  const distance = Math.max(halfV, halfH) / Math.tan(halfFov) * 1.35;
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
  { a: 11, b: 13, radius: 0.048, joint: "shoulder" },
  { a: 12, b: 14, radius: 0.048, joint: "shoulder" },
  { a: 13, b: 15, radius: 0.036, joint: "elbow" },
  { a: 14, b: 16, radius: 0.036, joint: "elbow" },
  { a: 15, b: 19, radius: 0.025, joint: "wrist" },
  { a: 16, b: 20, radius: 0.025, joint: "wrist" },
  { a: 23, b: 25, radius: 0.065, joint: "knee" },
  { a: 24, b: 26, radius: 0.065, joint: "knee" },
  { a: 25, b: 27, radius: 0.043, joint: "knee" },
  { a: 26, b: 28, radius: 0.043, joint: "knee" },
  { a: 27, b: 31, radius: 0.03, joint: null },
  { a: 28, b: 32, radius: 0.03, joint: null },
];
const TORSO_RADIUS = 0.13;
const NECK_RADIUS = 0.045;
const HEAD_INDEX = 0;
const HEAD_RADIUS = 0.15;

const NEUTRAL_COLOR = 0xf1e6d3;
const STATUS_COLOR = { green: 0x3ddc84, yellow: 0xffd34f, red: 0xff5d5d };

function statusColor(joint, jointStatus) {
  if (!joint) return NEUTRAL_COLOR;
  return STATUS_COLOR[jointStatus?.[joint] || "green"];
}

function toVec3(point) {
  // Flip y so the y-down landmark convention becomes Three.js's y-up.
  return new THREE.Vector3(point[0], -point[1], point[2]);
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

function makeUnitCapsule(radius, color) {
  const geometry = new THREE.CapsuleGeometry(radius, 1, 4, 8);
  const material = new THREE.MeshStandardMaterial({ color, roughness: 0.65, metalness: 0.04 });
  return new THREE.Mesh(geometry, material);
}

function createFigure(scene) {
  const group = new THREE.Group();
  const limbs = BODY_PARTS.map((part) => ({
    part,
    mesh: makeUnitCapsule(part.radius, NEUTRAL_COLOR),
  }));
  for (const limb of limbs) group.add(limb.mesh);

  const torsoMesh = makeUnitCapsule(TORSO_RADIUS, NEUTRAL_COLOR);
  group.add(torsoMesh);

  const neckMesh = makeUnitCapsule(NECK_RADIUS, NEUTRAL_COLOR);
  group.add(neckMesh);

  const headGeometry = new THREE.SphereGeometry(HEAD_RADIUS, 20, 16);
  const headMaterial = new THREE.MeshStandardMaterial({ color: NEUTRAL_COLOR, roughness: 0.55, metalness: 0.04 });
  const headMesh = new THREE.Mesh(headGeometry, headMaterial);
  group.add(headMesh);

  const shadowGeometry = new THREE.CircleGeometry(0.22, 24);
  const shadowMaterial = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.22 });
  const shadowMesh = new THREE.Mesh(shadowGeometry, shadowMaterial);
  shadowMesh.rotation.x = -Math.PI / 2;
  shadowMesh.position.y = 0.001;
  group.add(shadowMesh);

  scene.add(group);

  return {
    group,
    update(points, jointStatus) {
      for (const limb of limbs) {
        orientCapsule(limb.mesh, points[limb.part.a], points[limb.part.b]);
        limb.mesh.material.color.setHex(statusColor(limb.part.joint, jointStatus));
      }
      const shoulderMid = midVec3(points[11], points[12]);
      const hipMid = midVec3(points[23], points[24]);
      const headPos = toVec3(points[HEAD_INDEX]);
      orientCapsuleVec(torsoMesh, shoulderMid, hipMid);
      orientCapsuleVec(neckMesh, shoulderMid, headPos);
      headMesh.position.copy(headPos);

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
      neckMesh.geometry.dispose();
      headGeometry.dispose();
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

export function createPoseViewport(container, { cameraDistance = 2.1 } = {}) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.05, 30);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  container.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const keyLight = new THREE.DirectionalLight(0xffffff, 0.9);
  keyLight.position.set(1.2, 2, 1.5);
  scene.add(keyLight);
  const rimLight = new THREE.DirectionalLight(0xbfe8ff, 0.25);
  rimLight.position.set(-1.5, 0.5, -1.5);
  scene.add(rimLight);

  const figure = createFigure(scene);
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

  function setStaticPose(landmarks, jointStatus) {
    stopAnimation();
    ball.setPosition(null);
    if (!landmarks || landmarks.length < 33) return;
    const bounds = computeFramesBounds([{ points: landmarks }]);
    const framed = frameCamera(bounds, camera.fov);
    lookTarget = framed.center;
    distance = Math.max(framed.distance, cameraDistance);
    applyCamera();
    figure.update(landmarks, jointStatus);
    draw();
  }

  const FRAME_INTERVAL_MS = 60;

  function playDemo(action) {
    stopAnimation();
    if (typeof requestAnimationFrame !== "function") return;

    const frames = buildSequence(action);
    const bounds = computeFramesBounds(frames);
    const framed = frameCamera(bounds, camera.fov);
    lookTarget = framed.center;
    distance = framed.distance;
    applyCamera();

    const totalDuration = frames.reduce((sum, frame) => sum + frame.hold, 0);
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
        if (elapsed < cursor + frames[i].hold) {
          index = i;
          break;
        }
        cursor += frames[i].hold;
      }
      const nextIndex = (index + 1) % frames.length;
      const localT = easeInOut(Math.min(1, (elapsed - cursor) / frames[index].hold));

      const points = lerpTriples(frames[index].points, frames[nextIndex].points, localT);
      figure.update(points, null);

      if (frames[index].ball && frames[nextIndex].ball) {
        ball.setPosition(lerpTriple(frames[index].ball, frames[nextIndex].ball, localT));
      } else {
        ball.setPosition(null);
      }

      draw();
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
  }

  return { setStaticPose, playDemo, setView, resize, dispose };
}
