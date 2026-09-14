"""For each leave-one-out false positive, ask whether the segmenter picked a real contact.

A spike contact with a 26-degree shoulder means the arm is hanging by the side.
That is not a borderline-correct spike being flagged -- it is the wrong frame
being measured. Reporting both populations as one "false positive rate" would
overstate how often the app nags a correct player, which is the opposite of a
conservative error.
"""
import json, os, sys
sys.path.append(os.getcwd())
from backend.phase_segmentation import segment_action
from tools.build_reference import _process_clip, DATASET_DIR
from angle.angle import get_angles

res = json.load(open(sys.argv[1], encoding="utf-8"))
targets = {}
for r in res:
    action, phase, joint = r["key"].split(".")
    for d in r["loo_detail"]:
        targets.setdefault((action, d["clip"]), []).append((phase, joint, d["angle"], d["codes"][0]))

print(f"{'clip':<36}{'phase':<8}{'joint':<9}{'angle':>7}{'wrist-nose':>11}{'wrist-shldr':>12}  verdict")
out = []
for (action, clip), items in sorted(targets.items()):
    path = os.path.join(DATASET_DIR, action, clip)
    frames = _process_clip(path)
    segs = segment_action(action, [f["landmarks"] for f in frames])
    for phase, joint, angle, code in items:
        idx = segs.get(phase)
        lm = frames[idx]["landmarks"]
        nose_y = lm[0].y
        wrist_y = min(lm[15].y, lm[16].y)          # higher hand (y grows down)
        sh_y = (lm[11].y + lm[12].y) / 2
        wn = round(wrist_y - nose_y, 3)            # negative = hand above nose
        ws = round(wrist_y - sh_y, 3)              # negative = hand above shoulder
        if phase == "contact" and action in ("spike", "serve", "block", "set"):
            good = wn < 0.0                         # overhead action: hand must be up
        elif phase == "contact" and action == "receive":
            good = ws > 0.0                         # platform: hands below shoulder
        else:
            good = None                             # crouch has no such landmark test
        verdict = "frame OK" if good else ("WRONG FRAME" if good is False else "n/a (crouch)")
        print(f"{action+'/'+clip:<36}{phase:<8}{joint:<9}{angle:>7}{wn:>11}{ws:>12}  {verdict}")
        out.append({"action": action, "clip": clip, "phase": phase, "joint": joint,
                    "angle": angle, "code": code, "wrist_minus_nose": wn,
                    "wrist_minus_shoulder": ws, "frame_ok": good})
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nwritten: {sys.argv[2]}")
