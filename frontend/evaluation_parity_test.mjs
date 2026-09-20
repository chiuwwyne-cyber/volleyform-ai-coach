// The browser re-implements the evaluator: local-analyzer.js duplicates the band
// range maths, the issue-code table and the joint aggregation that
// backend/reference_evaluation.py and angle/angle.py own. Nothing checked that the
// two agree, so a backend guard could stay green while the shipped analyser
// diverged -- and it already has diverged, which this test now records.
//
// It runs the REAL local-analyzer.js source against the REAL committed standards.
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const root = process.cwd();
const source = fs.readFileSync(path.join(root, "frontend", "local-analyzer.js"), "utf8");

// --- 1. the high-side ceiling must be capped, and by the kept maximum ----------
assert.ok(/STRAIGHT_LIMB_FLOOR\s*=\s*168/.test(source),
  "local-analyzer must carry the same straight-limb floor as the backend");
assert.ok(/band\.max_kept/.test(source),
  "the ceiling must anchor on max_kept, not the pre-trim max");
assert.ok(/observedMax\s*<\s*STRAIGHT_LIMB_FLOOR/.test(source),
  "the cap must only apply while it still clears the reference, or correct " +
  "technique gets flagged");

// --- 2. the published standards must already reflect the cap ------------------
const standards = JSON.parse(
  fs.readFileSync(path.join(root, "backend", "reference_standards.json"), "utf8"),
).actions;
// Which joints carry a high-side code, mirrored from ACTION_RULES. Kept explicit
// so a change on the backend side shows up here as a failure rather than silently.
const HIGH_SIDE = [
  ["spike", "crouch", "knee"], ["serve", "crouch", "knee"],
  ["block", "crouch", "knee"], ["receive", "contact", "knee"],
  ["set", "contact", "elbow"],
];
for (const [action, phase, joint] of HIGH_SIDE) {
  const band = standards[action]?.phases?.[phase]?.[joint];
  if (!band) continue;
  assert.ok(band.max_kept !== undefined,
    `${action}.${phase}.${joint} is missing max_kept; rebuild the reference`);
  const ceiling = band.accepted_range[1];
  assert.ok(band.max_kept <= ceiling,
    `${action}.${phase}.${joint}: published ceiling ${ceiling} is below the largest ` +
    `kept sample ${band.max_kept}, so a clip the calibration accepted would be flagged`);
}

// --- 3. record the known frontend/backend divergence --------------------------
// angle/angle.py takes knee = min(left, right) and elbow/shoulder = max(...),
// while local-analyzer.js averages both sides. The same bands are therefore
// applied through a different estimator in the browser. This is NOT fixed; the
// assertion pins the current state so the divergence cannot quietly widen, and
// fails loudly the moment someone changes one side.
assert.ok(/const knee = average\(\[/.test(source),
  "local-analyzer's knee aggregation changed -- if it now matches the backend's " +
  "min(left, right), delete this assertion and the note in the ADR");

// --- 4. the shape checks must exist on BOTH sides ----------------------------
// The app that users actually run is the browser one; GitHub Pages has no
// backend. A check added only to reference_evaluation.py would pass every
// Python test and do nothing for a single user.
assert.ok(/function evaluateShapeChecks\(/.test(source),
  "local-analyzer must implement the shape checks; the backend-only version " +
  "never runs on GitHub Pages");
// Anchored to an indented line, because the unanchored form also matches the
// `function evaluateShapeChecks(entry, frames, segments, ...)` declaration --
// so deleting the only call site left this assertion green. Found by mutation.
assert.ok(/\n\s+evaluateShapeChecks\(entry, frames, segments,/.test(source),
  "evaluateShapeChecks is defined but never called from evaluatePhaseAware");

// The off-screen gate has to come with it, at the same two thresholds. Without
// it the browser judges hands MediaPipe invented below the frame edge.
assert.ok(/OFFSCREEN_MARGIN\s*=\s*0\.1\b/.test(source),
  "local-analyzer's off-screen margin does not match angle.py's 0.10");
assert.ok(/OFFSCREEN_VISIBILITY\s*=\s*0\.5\b/.test(source),
  "local-analyzer's off-screen visibility floor does not match angle.py's 0.5");

// Both SHAPE_LANDMARKS tables must list the same landmarks for the same
// feature, or the two sides gate on different points and disagree about which
// frames are judgeable.
function landmarkTable(text, name, entryPattern) {
  const start = text.indexOf(`${name} = {`);
  assert.ok(start >= 0, `${name} table not found`);
  const body = text.slice(start, text.indexOf("}", start));
  const table = {};
  for (const match of body.matchAll(entryPattern)) {
    table[match[1]] = match[2].split(",").map((n) => Number(n.trim()));
  }
  return table;
}
const anglePy = fs.readFileSync(path.join(root, "angle", "angle.py"), "utf8");
const JS_ENTRY = /^\s{2}([a-z_]+):\s*\[([\d,\s]+)\]/gm;
const PY_ENTRY = /^\s{4}"([a-z_]+)":\s*\(([\d,\s]+)\)/gm;

// Both gate tables, not just the shape one. JOINT_LANDMARKS drives the gate on
// the angle bands -- the 14 checks that have always been live -- so a browser
// listing different landmarks there judges a different set of frames than the
// backend does, on every action.
const tables = {};
for (const name of ["SHAPE_LANDMARKS", "JOINT_LANDMARKS"]) {
  const front = landmarkTable(source, `const ${name}`, JS_ENTRY);
  const back = landmarkTable(anglePy, name, PY_ENTRY);
  assert.deepStrictEqual(Object.keys(front).sort(), Object.keys(back).sort(),
    `${name} lists different keys in local-analyzer.js and angle.py`);
  for (const [key, indices] of Object.entries(back)) {
    assert.deepStrictEqual(front[key], indices,
      `${name}.${key} gates on different landmarks in the browser ` +
      `(${front[key]}) than in Python (${indices})`);
  }
  tables[name] = front;
}
const frontTable = tables.SHAPE_LANDMARKS;

// The gate has to actually be applied to the angle bands in the browser too.
// It was added to the backend first, and a backend-only version protects nobody
// on GitHub Pages.
assert.ok(/landmarksOffscreen\(points, JOINT_LANDMARKS\[joint\]/.test(source),
  "local-analyzer judges joint angles without the off-screen gate, so the " +
  "browser still reports knees computed from ankles MediaPipe invented");

// And every check actually published must be one both sides can measure.
for (const [action, entry] of Object.entries(standards)) {
  for (const key of Object.keys(entry.shape_checks || {})) {
    const feature = key.slice(key.indexOf(".") + 1);
    assert.ok(feature in frontTable,
      `${action} publishes a shape check for ${feature}, which the browser ` +
      "cannot gate and therefore refuses to judge -- the check would be dead");
  }
}

// --- 5. and the two sides must AGREE ON THE NUMBERS ---------------------------
// Everything above compares source text, which can only show the two look alike.
// This runs the real shapeFeatures and landmarksOffscreen out of local-analyzer.js
// against the fixture backend/shape_check_test.py is held to, so a browser that
// judges users by different arithmetic fails here instead of silently shipping.
const fixture = JSON.parse(
  fs.readFileSync(path.join(root, "frontend", "shape_parity_fixture.json"), "utf8"),
);

// local-analyzer.js is an ES module that pulls in MediaPipe. Only the pure
// geometry is under test, so the import and the one import.meta use are stubbed
// and the rest of the real file is evaluated unchanged.
const analyzerSource = source
  .replace(/^import\s*\{[\s\S]*?\}\s*from\s*"[^"]*";/m, "")
  .replace(/^export /gm, "")
  .replace(/import\.meta\.url/g, '"file:///stub/"');
const sandbox = {
  console, Math, Number, Object, Array, JSON, Map, Set, URL, Date,
  isFinite, NaN, performance: { now: () => 0 },
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(
  `${analyzerSource}\n;globalThis.__parity = { shapeFeatures, landmarksOffscreen, SHAPE_LANDMARKS };`,
  sandbox,
  { filename: "frontend/local-analyzer.js" },
);
const browser = sandbox.__parity;

assert.deepStrictEqual(
  Object.fromEntries(Object.entries(browser.SHAPE_LANDMARKS).map(([k, v]) => [k, [...v]])),
  fixture.shape_landmarks,
  "the fixture was generated from a different SHAPE_LANDMARKS; rerun " +
  "tools/make_shape_parity_fixture.py",
);

const round9 = (value) => Number(value.toFixed(9));
for (const testCase of fixture.cases) {
  const measured = Object.fromEntries(
    Object.entries(browser.shapeFeatures(testCase.landmarks)).map(
      ([key, value]) => [key, round9(value)]),
  );
  assert.deepStrictEqual(measured, testCase.features,
    `case ${testCase.name}: the browser computes different shape features than ` +
    "Python does, so the bands were calibrated under one rule and users are " +
    "judged by another");
  for (const [feature, indices] of Object.entries(browser.SHAPE_LANDMARKS)) {
    assert.strictEqual(
      browser.landmarksOffscreen(testCase.landmarks, indices),
      testCase.offscreen[feature],
      `case ${testCase.name}: the browser and Python disagree about whether ` +
      `${feature} is judgeable in this frame`);
  }
}

// --- 6. the hand-pair gate must exist on both sides too ----------------------
// Backend-only again protects nobody: GitHub Pages runs this file. The threshold
// has to match or the browser judges pairs the backend refuses, and vice versa.
assert.ok(/function handPairIsUsable\(/.test(source),
  "local-analyzer must gate the between-hand measures; without it the browser " +
  "flags setting_hand_spacing_bad on one hand detected twice");
assert.ok(/const HAND_PAIR_MIN_SEPARATION = 0\.1\b/.test(source),
  "local-analyzer's hand-pair separation floor does not match the backend's 0.10");
// Called on BOTH branches. receive reads the pair for its platform checks and set
// for its spacing checks; gating one and not the other leaves half the defect.
assert.ok(/if \(handPairIsUsable\(hands\)\) \{/.test(source),
  "the receive branch no longer gates the hand pair");
assert.ok(/if \(!handPairIsUsable\(hands\)\) return;/.test(source),
  "the set branch no longer gates the hand pair");
// And finger_extension must stay OUTSIDE the gate: it describes a single hand,
// so gating it would discard a working check to fix a broken one.
// Anchored inside evaluatePhaseHands. `if (action === "set")` appears four times
// in this file and the first is a different branch entirely, so slicing from it
// left the ordering assertion measuring two unrelated positions -- it passed while
// the gate sat in front of the finger check. Found by mutation.
const handsFn = source.indexOf("function evaluatePhaseHands(");
assert.ok(handsFn >= 0, "evaluatePhaseHands not found");
const setBranch = source.slice(source.indexOf('if (action === "set")', handsFn));
assert.ok(
  setBranch.indexOf("setting_fingers_closed") < setBranch.indexOf("handPairIsUsable"),
  "setting_fingers_closed moved behind the hand-pair gate, but finger extension " +
  "is measured on one hand and survives the pair collapsing");

// --- 7. both sides must estimate pose at the same width ----------------------
// tools/build_reference.py calls pose/pose.py with process_width=640, and 61 of the
// 120 reference clips are wider than that. The browser used to hand MediaPipe the
// video element at its native size, so the standard and the judgement came from
// different pre-processing -- measured on ten high-resolution clips, the phase
// segmenter picked a different frame in 8 of 16 phases, once 25 frames apart.
const buildRef = fs.readFileSync(path.join(root, "tools", "build_reference.py"), "utf8");
const calibWidth = buildRef.match(/process_width=(\d+)/);
assert.ok(calibWidth, "build_reference.py no longer states a process_width");
const browserWidth = source.match(/const PROCESS_WIDTH = (\d+);/);
assert.ok(browserWidth, "local-analyzer.js no longer caps the pose input width");
assert.strictEqual(browserWidth[1], calibWidth[1],
  `the browser estimates pose at ${browserWidth[1]}px while the bands were ` +
  `calibrated at ${calibWidth[1]}px, so the segmenter can pick a different frame`);

// Only downscale. Upscaling a phone video to 640 would invent detail the camera
// never captured, and pose.py returns the frame untouched in that case.
assert.ok(/width <= PROCESS_WIDTH\) return source;/.test(source),
  "sourceAtProcessWidth must pass small frames through untouched, as " +
  "_resize_for_processing does");

// Pose and hands must read the SAME frame. Scaling one and not the other would
// have the two detectors looking at different images of the same instant.
for (const call of ["detectPose(pose, frameSource", "detectHands(hands, frameSource"]) {
  assert.ok(source.includes(call),
    `${call}...) not found -- one detector is still reading the raw video element`);
}
assert.ok(!/detect(Pose|Hands)\((pose|hands), video,/.test(source),
  "a detector is still being handed the video element at native resolution");

console.log("evaluation parity ok");
console.log("checked: straight-limb floor, max_kept anchor, published ceilings, " +
  "known aggregation divergence, both landmark tables, the runtime gate, " +
  "shape checks on both sides, the hand-pair gate, the process width, " +
  `${fixture.cases.length} cross-language numeric cases`);
