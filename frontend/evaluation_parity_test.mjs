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

// --- 4. the joint model is deliberately backend-only, and here is the number ---
// block and set carry a joint elbow/shoulder model (reference_standards.json
// -> joint_model). The backend evaluator runs it. local-analyzer.js does NOT, and
// that is a measured decision rather than an oversight.
//
// The model is fitted on backend-aggregated angles: elbow and shoulder as
// max(left, right). The browser averages the two sides instead -- the divergence
// assertion above. Re-measuring all 38 block and set clips with both aggregations
// (tools/dump_per_side_angles.py) showed what that costs a JOINT model, which is
// much more than it costs a single band:
//
//   set    0 / 21 clips newly flagged, mean Mahalanobis shift +0.01  -> safe
//   block  3 / 17 clips newly flagged, mean Mahalanobis shift +0.37  -> NOT safe
//
// Three assumed-correct block clips would be told their elbow and shoulder do not
// go together, purely because the browser measures the pair differently from the
// model that judges it. Shipping that to the on-device path -- the path real users
// are on -- would be the exact false positive this project weights heaviest.
//
// The root cause is the aggregation divergence, not the model. Fix that first; then
// delete this assertion and run the model in both places.
// The embedded REFERENCE_STANDARDS literal carries joint_model as DATA -- sync_frontend
// copies the whole file across -- so the check has to look at the code around it, not
// at the file as a whole. Stripping the literal first is what makes this assertion
// mean "no code reads it" instead of "the string does not appear".
const dataStart = source.indexOf("const REFERENCE_STANDARDS = {");
const dataEnd = dataStart < 0 ? -1 : source.indexOf("\n};", dataStart);
assert.ok(dataEnd > dataStart, "could not locate the embedded REFERENCE_STANDARDS literal");
const code = source.slice(0, dataStart) + source.slice(dataEnd + 3);
assert.ok(!/joint_model/.test(code),
  "local-analyzer.js now reads joint_model. Before shipping it to the browser, " +
  "re-run tools/dump_per_side_angles.py: with averaged aggregation the block model " +
  "flagged 3 of 17 assumed-correct clips. Either the aggregation now matches the " +
  "backend, or this needs a model fitted on averaged angles.");

console.log("evaluation parity ok");
console.log("checked: straight-limb floor, max_kept anchor, published ceilings, " +
  "known aggregation divergence, joint model kept backend-only");
