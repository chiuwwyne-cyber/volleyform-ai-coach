"""Generate frontend/footwork_parity_fixture.json.

The backend implementation (backend/footwork.count_approach_steps) is the source
of truth; the fixture stores its output for each case so the frontend mirror in
frontend/local-analyzer.js can be asserted to match exactly. Both
backend/footwork_test.py and frontend/footwork_parity_test.mjs read this file.

Run: .venv\\Scripts\\python.exe tools\\make_footwork_parity_fixture.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from backend.footwork import count_approach_steps  # noqa: E402

OUT = os.path.join(ROOT, "frontend", "footwork_parity_fixture.json")


def two_step(step):
    """A clean 2-step (4-contact) approach sampled every `step` seconds.

    Left foot plants near 0.20s and 0.70s, right foot near 0.45s and 0.95s,
    takeoff (highest wrist) at 1.30s. Ankle-y bumps to 0.93 at a plant and sits
    at 0.85 while the foot swings; the wrist is high only at takeoff.
    """
    L_PLANTS = (0.20, 0.70)
    R_PLANTS = (0.45, 0.95)
    TAKEOFF = 1.30

    def ankle(t, plants):
        y = 0.85
        for p in plants:
            d = abs(t - p)
            if d < step * 0.5:      # the plant sample itself
                y = max(y, 0.93)
            elif d < step * 1.5:    # shoulders of the plant
                y = max(y, 0.88)
        return y

    samples = []
    t = 0.0
    while t <= TAKEOFF + 0.049:
        wr = 0.15 if abs(t - TAKEOFF) < step * 0.5 else 0.50
        samples.append({
            "t": round(t, 3),
            "la": round(ankle(t, L_PLANTS), 3),
            "ra": round(ankle(t, R_PLANTS), 3),
            "wr": wr,
            "torso": 0.15,
        })
        t += step
    return samples


def standing():
    samples = []
    t = 0.0
    while t <= 1.35:
        samples.append({"t": round(t, 3), "la": 0.9, "ra": 0.9,
                        "wr": 0.15 if abs(t - 1.3) < 0.03 else 0.5, "torso": 0.15})
        t += 0.05
    return samples


CASES = {
    "clean_two_step_dense": two_step(0.05),   # ~20 fps -> reliable
    "clean_two_step_sparse": two_step(0.25),  # ~4 fps  -> too sparse to trust
    "standing_still": standing(),
    "no_pose": [{"t": round(i * 0.1, 3), "la": None, "ra": None, "wr": None, "torso": 0.15}
                for i in range(10)],
}

fixture = {
    "_comment": "Backend backend/footwork.py is source of truth; frontend must match. "
                "Regenerate with tools/make_footwork_parity_fixture.py.",
    "cases": [
        {"name": name, "samples": samples, "expected": count_approach_steps(samples)}
        for name, samples in CASES.items()
    ],
}

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(fixture, fh, ensure_ascii=False, indent=2)
    fh.write("\n")

for case in fixture["cases"]:
    print(case["name"], "->", case["expected"])
print("wrote", os.path.relpath(OUT, ROOT))
