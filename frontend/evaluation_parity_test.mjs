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

console.log("evaluation parity ok");
console.log("checked: straight-limb floor, max_kept anchor, published ceilings, " +
  "known aggregation divergence");
