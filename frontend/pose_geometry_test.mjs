// Geometry regression test for the 3D demo.
//
// The existing frontend test checks that symbols EXIST by regex. That cannot
// catch the failures this file exists for, all of which shipped at least once:
//
//   * the trunk rotating in the landmarks while the torso MESH stayed frozen,
//     because the mesh is oriented by a separate code path
//   * the whole action mirroring, because every check measured |angle| and so
//     could not tell a left turn from a right one
//   * the figure shearing at the waist when the legs lagged the pelvis
//   * a demo pose contradicting the app's own coaching (receive was drawn with
//     120-degree elbows while the cue says to straighten them)
//
// So this runs the REAL buildSequence and the REAL orientation functions
// against the REAL vendored three.js, and asserts on measured geometry.
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const THREE = await import(
  "file://" + path.join(root, "frontend", "vendor", "three", "three.module.min.js").split(path.sep).join("/")
);

const source = fs.readFileSync(path.join(root, "frontend", "pose-3d.js"), "utf8");
const stubbed =
  "const THREE = globalThis.__THREE;\n" +
  source.replace(/^import[^\n]*\n/gm, "").replace(/^export function createPoseViewport[\s\S]*$/m, "") +
  "\nexport { buildSequence, SPIKE_SEQUENCES, CORRECT_CYCLES, orientKrunkPart, orientKrunkTorso, toVec3, midVec3, preparePoseSequenceForDisplay };\n";
const tmp = path.join(process.env.TEMP || root, `pose_geom_${Date.now()}.mjs`);
fs.writeFileSync(tmp, stubbed, "utf8");
globalThis.__THREE = THREE;
const mod = await import("file://" + tmp.split(path.sep).join("/"));
fs.unlinkSync(tmp);

const deg = (r) => (r * 180) / Math.PI;
const norm = (d) => { let v = d; while (v > 180) v -= 360; while (v <= -180) v += 360; return v; };

function framesOf(action) {
  const frames = mod.buildSequence(action, "correct");
  const spec = action === "spike" ? mod.SPIKE_SEQUENCES.correct : mod.CORRECT_CYCLES[action];
  return frames.map((f, i) => ({ ...f, phase: spec[i].spikePhase || spec[i].actionPhase }));
}
const at = (action, phase) => {
  const f = framesOf(action).find((x) => x.phase === phase);
  assert.ok(f, `${action}/${phase} missing`);
  return f.points;
};
const shoulderYaw = (p) => deg(Math.atan2(p[12][2] - p[11][2], p[12][0] - p[11][0]));
const hipYaw = (p) => deg(Math.atan2(p[24][2] - p[23][2], p[24][0] - p[23][0]));
const jointAngle = (a, b, c) => {
  const v1 = a.map((v, i) => v - b[i]);
  const v2 = c.map((v, i) => v - b[i]);
  const n = Math.hypot(...v1) * Math.hypot(...v2);
  if (!n) return 180;
  return deg(Math.acos(Math.max(-1, Math.min(1, v1.reduce((s, v, i) => s + v * v2[i], 0) / n))));
};

// ---- the trunk turns, and squares up again -------------------------------
assert.ok(Math.abs(shoulderYaw(at("spike", "plant"))) > 30, "spike plant must be side-on");
assert.ok(Math.abs(shoulderYaw(at("spike", "load"))) > 45, "spike load must be strongly side-on");
assert.ok(Math.abs(shoulderYaw(at("spike", "contact"))) < 15, "spike contact must square to the net");
assert.ok(Math.abs(shoulderYaw(at("serve", "serve_load"))) > 40, "serve draw must be side-on");
assert.ok(Math.abs(shoulderYaw(at("serve", "serve_contact"))) < 15, "serve contact must square up");

// ---- a block stays square: turning it teaches the error -------------------
for (const phase of ["block_ready", "block_load", "block_rise", "block_press"]) {
  assert.ok(Math.abs(shoulderYaw(at("block", phase))) < 5, `block ${phase} must stay square to the net`);
}

// ---- DIRECTION, not just magnitude: the hitting arm cocks camera-side -----
assert.ok(at("spike", "load")[12][2] - at("spike", "load")[11][2] > 0,
  "spike: hitting shoulder must cock toward the camera, or the action is mirrored");
assert.ok(at("serve", "serve_load")[12][2] - at("serve", "serve_load")[11][2] > 0,
  "serve: hitting shoulder must cock toward the camera");

// ---- the body turns as ONE piece: a big gap shears the rigid torso mesh ---
for (const phase of ["plant", "load", "jump"]) {
  const p = at("spike", phase);
  const separation = Math.abs(norm(shoulderYaw(p) - hipYaw(p)));
  assert.ok(separation < 28,
    `spike ${phase}: hip/shoulder separation ${separation.toFixed(0)} is too wide for a rigid torso mesh`);
}

// ---- the TORSO MESH must actually follow, not just the landmarks ----------
function torsoMeshYaw(points) {
  const mesh = { position: new THREE.Vector3(), scale: new THREE.Vector3(), quaternion: new THREE.Quaternion() };
  mesh.scale.setScalar = function (s) { this.set(s, s, s); };
  const shoulderVec = mod.toVec3(points[12]).sub(mod.toVec3(points[11]));
  const hipVec = mod.toVec3(points[24]).sub(mod.toVec3(points[23]));
  const facing = shoulderVec.clone().normalize().add(hipVec.clone().normalize());
  mod.orientKrunkTorso(mesh, mod.midVec3(points[23], points[24]), mod.midVec3(points[11], points[12]), facing);
  const localX = new THREE.Vector3(1, 0, 0).applyQuaternion(mesh.quaternion);
  return deg(Math.atan2(localX.z, localX.x));
}
const torsoSpread = ["approach", "plant", "load", "contact"].map((ph) => torsoMeshYaw(at("spike", ph)));
assert.ok(Math.max(...torsoSpread) - Math.min(...torsoSpread) > 30,
  "the torso MESH must turn with the trunk, not stay frozen while the arms swing");

// ---- demo poses must not contradict the coaching -------------------------
{
  const p = at("receive", "receive_platform");
  const left = jointAngle(p[11], p[13], p[15]);
  const right = jointAngle(p[12], p[14], p[16]);
  assert.ok(left > 135 && right > 135,
    `receive platform elbows ${left.toFixed(0)}/${right.toFixed(0)} are bent; the app coaches straight arms`);
}

// ---- the replay must not pulse in size -----------------------------------
// The left-hand "your pose" panel was reported for weeks as wandering. The real
// symptom was not translation: the old code prepared EVERY frame on its own
// centre and scale, so a noisy height estimate made the figure swell and shrink
// by 130% of its own size while the limbs swung. Measured on a real analysed
// Pexels spike, the current sequence-aware path holds it to about 22%, which is
// genuine posture change (a crouch shortens shoulder-to-ankle).
{
  const fixture = JSON.parse(
    fs.readFileSync(path.join(root, "frontend", "testdata", "replay_sequence.json"), "utf8"),
  );
  const sequence = fixture.frames.map((f) => ({
    landmarks: f.landmarks, joint_status: f.joint_status,
    time_seconds: f.time_seconds, hold: 720,
  }));
  const prepared = mod.preparePoseSequenceForDisplay(sequence, { caption: "t", action: "spike" });
  assert.ok(prepared.length > 5, "fixture should prepare into a real sequence");
  const midY = (p, a, b) => (p[a][1] + p[b][1]) / 2;
  const heights = prepared.map((f) => Math.abs(midY(f.points, 27, 28) - midY(f.points, 11, 12)));
  const mean = heights.reduce((s, v) => s + v, 0) / heights.length;
  const variation = (Math.max(...heights) - Math.min(...heights)) / mean;
  assert.ok(variation < 0.55,
    `replay figure changes size by ${(variation * 100).toFixed(0)}% of its own height; ` +
    "per-frame rescaling is back and the figure will pulse");
}

// ---- nothing may go non-finite ------------------------------------------
for (const action of ["spike", "serve", "receive", "block", "set"]) {
  for (const f of framesOf(action)) {
    assert.ok(f.points.every((pt) => pt.every(Number.isFinite)), `${action}/${f.phase} has non-finite points`);
  }
}

console.log("pose geometry ok");
console.log("checked: trunk turn, square block, turn direction, one-piece body, torso mesh, receive platform, replay size stability");
