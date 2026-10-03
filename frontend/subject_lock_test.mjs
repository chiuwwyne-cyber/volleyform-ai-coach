// Real subject choice from local-analyzer.js on two crowded clips where single-person pose tracked the wrong player.
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const root = process.cwd();
const source = fs.readFileSync(path.join(root, "frontend", "local-analyzer.js"), "utf8");
const fixture = JSON.parse(
  fs.readFileSync(path.join(root, "frontend", "subject_lock_fixture.json"), "utf8"),
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
  `${analyzerSource}\n;globalThis.__t = { trackPeople, subjectTrack, subjectBoxes, framesToRelock };`,
  sandbox,
  { filename: "frontend/local-analyzer.js" },
);
const t = sandbox.__t;
const centreInside = (s, b) => {
  const x = (s[0] + s[2]) / 2;
  const y = (s[1] + s[3]) / 2;
  return x >= b[0] - 0.02 && x <= b[2] + 0.02 && y >= b[1] - 0.02 && y <= b[3] + 0.02;
};

for (const testCase of fixture.cases) {
  const { clip, people, reference } = testCase;

  // Otherwise "picked the right player" could pass on a clip with nobody else in it.
  const crowdedFirstIsWrong = people.some((boxes, i) =>
    boxes.length >= 2 && reference[i] && !centreInside(boxes[0], reference[i]));
  assert.ok(crowdedFirstIsWrong,
    `${clip}: the fixture never puts a bystander first, so it cannot tell choosing from guessing`);

  const subject = t.subjectTrack(t.trackPeople(people), people.length);
  assert.deepStrictEqual([...subject.boxes.keys()].sort((a, b) => a - b), testCase.python_subject_samples,
    `${clip}: the browser tracker and the Python prototype it was measured with picked different samples`);

  const boxes = t.subjectBoxes(people);
  const judged = boxes.flatMap((box, i) => (box && reference[i] ? [i] : []));
  const onPlayer = judged.filter((i) => centreInside(boxes[i], reference[i]));
  assert.ok(judged.length >= reference.filter(Boolean).length * 0.8,
    `${clip}: the subject was found in too few of the samples where the player is known`);
  assert.ok(onPlayer.length >= judged.length * 0.9,
    `${clip}: the chosen subject left the player in samples ${judged.filter((i) => !onPlayer.includes(i))}`);
}

// Someone crossing close to the camera is briefly bigger than the player and must not be chosen.
const player = [0.45, 0.3, 0.55, 0.8, 0.9];
const passerBy = [0.0, 0.0, 0.4, 1.0, 0.9];
const crossing = Array.from({ length: 10 }, (_, i) => (i < 2 ? [passerBy, player] : [player]));
assert.deepStrictEqual(JSON.parse(JSON.stringify(t.subjectBoxes(crossing))), crossing.map(() => player),
  "a large passer-by seen in two samples was chosen over the player seen in all ten");

// Among people seen often enough, presence still counts: a bigger bystander in 5 of 26 samples is not the player.
const bystander = [0.0, 0.1, 0.3, 0.5, 0.9];
const sideline = Array.from({ length: 26 }, (_, i) => (i < 5 ? [bystander, player] : [player]));
assert.deepStrictEqual(JSON.parse(JSON.stringify(t.subjectBoxes(sideline))), sideline.map(() => player),
  "a bystander seen in 5 samples was chosen over the player seen in all 26");

// One person per sample is the common case and must come back untouched.
const alone = [[0.4, 0.2, 0.6, 0.9, 0.9], [0.41, 0.21, 0.61, 0.91, 0.8], [0.42, 0.2, 0.62, 0.9, 0.85]].map((b) => [b]);
assert.deepStrictEqual(JSON.parse(JSON.stringify(t.subjectBoxes(alone))), alone.map(([b]) => b));

// Re-analysis is only for crowded frames whose pose is on someone else.
const poseAt = (x, y) => Array.from({ length: 33 }, () => ({ x, y }));
const other = [0.0, 0.2, 0.2, 0.9, 0.9];
const frames = [
  { people: [player], frame: "jpeg", poseLandmarks: poseAt(0.1, 0.5) },
  { people: [player, other], frame: "jpeg", poseLandmarks: poseAt(0.5, 0.55) },
  { people: [player, other], frame: "jpeg", poseLandmarks: poseAt(0.1, 0.5) },
  { people: [player, other], frame: "jpeg", poseLandmarks: null },
];
assert.deepStrictEqual([...t.framesToRelock(frames, frames.map(() => player))], [2, 3],
  "only crowded frames whose pose is off the player (or missing) may be redone; the rest keep their original pose");

console.log("subject lock ok");
console.log(`checked: ${fixture.cases.length} multi-person clips pick the reference player, port matches the prototype, one-person input untouched`);
