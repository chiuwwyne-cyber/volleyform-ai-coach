// The browser (local-analyzer.js) re-implements the approach-step count that
// backend/footwork.py owns. GitHub Pages has no backend, so a step count that
// only matched in Python would be wrong for every real user. This runs the REAL
// countApproachSteps out of local-analyzer.js against the SAME fixture the
// backend is held to (frontend/footwork_parity_fixture.json).
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const root = process.cwd();
const source = fs.readFileSync(path.join(root, "frontend", "local-analyzer.js"), "utf8");

// --- source-level guards -----------------------------------------------------
// Descriptive only: the browser must never turn footwork into a pass/fail, since
// there is no reference for correct footwork. If a future edit pushes an issue
// code out of the step counter, this fails.
const stepFn = source.slice(
  source.indexOf("function countApproachSteps("),
  source.indexOf("function modalityPayload("),
);
assert.ok(stepFn.length > 0, "countApproachSteps not found in local-analyzer.js");
for (const banned of ["issueCounts", "issue_code", "FEEDBACK[", "severity"]) {
  assert.ok(!stepFn.includes(banned),
    `countApproachSteps references ${banned} -- footwork must stay descriptive, not a judgment`);
}
// The pose modality must actually carry the count, or the browser computes it and
// throws it away.
assert.ok(/approach_steps:\s*approachSteps/.test(source),
  "modalityPayload does not attach approach_steps to the pose modality result");
// Same window/prominence constants as the backend, or the two engines resolve
// different steps from the same clip.
assert.ok(/APPROACH_WINDOW_S:\s*1\.4\b/.test(source), "approach window differs from backend 1.4s");
assert.ok(/MIN_PROMINENCE:\s*0\.06\b/.test(source), "prominence floor differs from backend 0.06");
assert.ok(/MIN_WINDOW_SAMPLES:\s*8\b/.test(source), "reliability sample floor differs from backend 8");

// --- run the real function against the shared fixture ------------------------
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
  `${analyzerSource}\n;globalThis.__footwork = { countApproachSteps, sampleFromLandmarks };`,
  sandbox,
  { filename: "frontend/local-analyzer.js" },
);
const { countApproachSteps, sampleFromLandmarks } = sandbox.__footwork;

const fixture = JSON.parse(
  fs.readFileSync(path.join(root, "frontend", "footwork_parity_fixture.json"), "utf8"),
);
for (const testCase of fixture.cases) {
  // Re-wrap through this realm's Object: the vm sandbox builds objects with a
  // different Object.prototype, which deepStrictEqual counts as unequal even when
  // every field matches. The result is flat, so a spread normalises it.
  const got = { ...countApproachSteps(testCase.samples) };
  assert.deepStrictEqual(got, testCase.expected,
    `case ${testCase.name}: the browser counts approach steps differently than ` +
    "Python does, so the same clip would show two different numbers");
}

// sampleFromLandmarks must drop an off-screen / invisible ankle the same way the
// backend does, or the two build different series before counting.
const lm = Array.from({ length: 33 }, () => ({ x: 0.5, y: 0.5, visibility: 0.9 }));
lm[27] = { x: 0.5, y: 0.999, visibility: 0.9 };  // left ankle off the bottom edge
lm[28] = { x: 0.5, y: 0.8, visibility: 0.1 };    // right ankle invisible
const sample = sampleFromLandmarks(lm, 0.4);
assert.strictEqual(sample.la, null, "off-bottom ankle must be dropped, not read as a contact");
assert.strictEqual(sample.ra, null, "invisible ankle must be dropped, not read as a contact");

console.log("footwork parity ok");
console.log(`checked: descriptive-only guard, shared constants, ${fixture.cases.length} ` +
  "cross-language cases, off-screen ankle drop");
