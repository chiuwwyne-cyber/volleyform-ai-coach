// The 3D figure's joint colours must say what the report says. Runs the REAL
// buildPoseCompare out of local-analyzer.js on a real clean reference serve.
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const root = process.cwd();
const source = fs.readFileSync(path.join(root, "frontend", "local-analyzer.js"), "utf8");
const fixture = JSON.parse(
  fs.readFileSync(path.join(root, "frontend", "pose_colour_fixture.json"), "utf8"),
);

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
  `${analyzerSource}\n;globalThis.__t = { buildPoseCompare, JOINT_SPECS, JOINT_CHAIN, LEFT_JOINTS, RIGHT_JOINTS, angleBetween };`,
  sandbox,
  { filename: "frontend/local-analyzer.js" },
);
const t = sandbox.__t;
const sequence = [{ landmarks: fixture.landmarks }];
const ALL_GREEN = { elbow: "green", knee: "green", shoulder: "green", wrist: "green" };
const plain = (value) => JSON.parse(JSON.stringify(value));

// Otherwise the assertions below could pass on a frame no rule would ever flag.
const legacyHits = [];
for (const [joint, spec] of Object.entries(t.JOINT_SPECS[fixture.action])) {
  const [names] = t.JOINT_CHAIN[joint];
  for (const side of [t.LEFT_JOINTS, t.RIGHT_JOINTS]) {
    const angle = t.angleBetween(...names.map((name) => fixture.landmarks[side[name]]));
    if (angle < (spec.min ?? -1) || angle > (spec.max ?? 999)) legacyHits.push(joint);
  }
}
assert.ok(legacyHits.length > 0,
  "the fixture no longer violates JOINT_SPECS, so it cannot catch a return to colouring from them");

assert.deepStrictEqual(
  plain(t.buildPoseCompare(fixture.action, null, [], sequence).joint_status),
  ALL_GREEN,
  "a serve whose report is empty must not show yellow/red joints on the 3D figure",
);
assert.deepStrictEqual(
  plain(t.buildPoseCompare(fixture.action, null, ["knee_too_bent"], sequence).joint_status),
  { ...ALL_GREEN, knee: "red" },
  "the 3D figure must colour exactly the report's issues",
);

console.log("pose colour ok");
console.log("checked: fixture violates legacy specs, clean report all green, colours == report");
