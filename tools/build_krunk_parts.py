"""Rebuild the Krunk mannequin parts asset with MeshLab quadric decimation.

The Brave Krunk STL is already authored as 16 separate closed components (head,
neck, chest, hips, upper arms, forearms, hands, thighs, shins, feet). The old
tools/segment_krunk.py sliced one fused mesh by spatial labels and decimated the
open cuts with fast_simplification, which grew spikes and broke a limb.

Here we take each pre-existing component, decimate it with pymeshlab's Quadric
Edge Collapse (topology-preserving, no spikes), then rebase every part into the
normalized frame the frontend expects (proximal joint at origin, distal at Y=1,
unit bone length; torso/head in the hip->shoulder frame). Output schema is
krunk-parts-1, consumed directly by frontend/pose-3d.js.

Anatomy tuning:
  * arms are complete STL (upper_arm + forearm, shoulder->elbow->wrist); the
    hand ball is dropped so finger capsules keep the set (托球) hand shape.
  * feet are NOT baked into the shins -- the shin ends at the ankle and the
    frontend's ankle/heel/toe capsules articulate the foot at the ankle.
  * head is shrunk toward the neck and limbs/torso are slimmed radially so the
    figure reads closer to real human proportions instead of a chunky toy.

Run:
    .venv\\Scripts\\python.exe tools\\build_krunk_parts.py [path-to-stl]
"""

import json
import os
import sys

import numpy as np
import pymeshlab

CENTER_X = 2.0
CENTER_Y = -9.0

# Anatomy proportion knobs (X,Z slim across the bone; Y is the bone axis).
HEAD_SCALE = 0.82     # shrink the big toy head toward the neck
ARM_RADIAL = 0.90     # arm thickness (kept as-is)
LEG_RADIAL = 0.74     # legs are slimmer than the shorts
TORSO_RADIAL = 0.95   # the "shorts"/torso width

FACE_BUDGET = {
    "head": 900, "torso": 800,
    "upper_arm_L": 320, "upper_arm_R": 320,
    "forearm_L": 300, "forearm_R": 300,
    "thigh_L": 460, "thigh_R": 460,
    "shin_L": 440, "shin_R": 440,
}


def _rotation_y_to(dir_vec):
    """Rotation matrix mapping +Y to dir_vec (unit)."""
    y = np.array([0.0, 1.0, 0.0])
    d = dir_vec / (np.linalg.norm(dir_vec) + 1e-9)
    axis = np.cross(y, d)
    s = np.linalg.norm(axis)
    c = float(np.dot(y, d))
    if s < 1e-8:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    axis /= s
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + s * K + (1 - c) * (K @ K)


def load_components(stl_path):
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(stl_path)
    for f in ("meshing_remove_duplicate_vertices", "meshing_remove_null_faces",
              "meshing_remove_unreferenced_vertices"):
        try:
            ms.apply_filter(f)
        except Exception:
            pass
    ms.apply_filter("generate_splitting_by_connected_components")
    comps = []
    for i in range(ms.mesh_number()):
        ms.set_current_mesh(i)
        m = ms.current_mesh()
        if i == 0 or m.face_number() == 0:
            continue
        comps.append((m.vertex_matrix().astype(np.float64), m.face_matrix().astype(np.int64)))
    return comps


def decimate(V, F, target):
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=V, face_matrix=F))
    if F.shape[0] > target:
        ms.apply_filter(
            "meshing_decimation_quadric_edge_collapse",
            targetfacenum=int(target), qualitythr=0.3,
            preserveboundary=True, preservenormal=True, preservetopology=True,
            optimalplacement=True, planarquadric=True, autoclean=True,
        )
    try:
        ms.apply_filter("meshing_re_orient_faces_coherently")
    except Exception:
        pass
    m = ms.current_mesh()
    return m.vertex_matrix().astype(np.float64), m.face_matrix().astype(np.int64)


def merge(meshes):
    Vs, Fs, off = [], [], 0
    for V, F in meshes:
        Vs.append(V)
        Fs.append(F + off)
        off += len(V)
    return np.vstack(Vs), np.vstack(Fs)


def limb_anchors(V, proximal_by):
    """Proximal/distal joint anchors from a limb's principal axis end caps."""
    c = V.mean(0)
    _, _, vt = np.linalg.svd(V - c, full_matrices=False)
    axis = vt[0]
    t = (V - c) @ axis
    span = t.max() - t.min()
    lo = V[t <= t.min() + 0.12 * span].mean(0)
    hi = V[t >= t.max() - 0.12 * span].mean(0)
    if proximal_by == "z":                       # legs: proximal = higher end
        return (lo, hi) if lo[2] > hi[2] else (hi, lo)
    r_lo = np.hypot(lo[0] - CENTER_X, lo[1] - CENTER_Y)   # arms: proximal = nearer centerline
    r_hi = np.hypot(hi[0] - CENTER_X, hi[1] - CENTER_Y)
    return (lo, hi) if r_lo < r_hi else (hi, lo)


def indexed(local_V, F, ndp=4):
    return {"positions": [[round(float(x), ndp) for x in p] for p in local_V],
            "faces": [[int(a), int(b), int(c)] for a, b, c in F]}


def classify(V, zmin, H):
    c = V.mean(0)
    hp = 100 * (c[2] - zmin) / H
    side = "L" if c[0] < CENTER_X else "R"
    radial = np.hypot(c[0] - CENTER_X, c[1] - CENTER_Y)
    if hp > 85:
        return "head"
    if hp > 76:
        return "torso"                            # neck
    if hp > 55:
        if radial < 9:
            return "torso"                        # chest
        if radial < 17:
            return f"upper_arm_{side}"
        if radial < 28:
            return f"forearm_{side}"
        return None                               # hand ball -> finger capsules
    if hp > 38:
        return "torso"                            # hips
    if hp > 20:
        return f"thigh_{side}"
    if hp > 6:
        return f"shin_{side}"
    return None                                   # foot -> ankle/heel/toe capsules


def main():
    stl = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\test\Downloads\Brave Krunk.stl"
    comps = load_components(stl)
    allV = np.vstack([V for V, _ in comps])
    zmin, zmax = allV[:, 2].min(), allV[:, 2].max()
    H = zmax - zmin

    groups = {}
    print("component -> part:")
    for V, F in comps:
        key = classify(V, zmin, H)
        c = V.mean(0)
        print(f"  h={100*(c[2]-zmin)/H:5.1f}%  x={c[0]:6.1f}  "
              f"r={np.hypot(c[0]-CENTER_X, c[1]-CENTER_Y):5.1f}  F={F.shape[0]:5d}  -> {key}")
        if key is not None:
            groups.setdefault(key, []).append((V, F))

    dec = {}
    for key, meshes in groups.items():
        V, F = merge(meshes) if len(meshes) > 1 else meshes[0]
        dec[key] = decimate(V, F, FACE_BUDGET.get(key, 400))

    anchors = {}
    for s in ("L", "R"):
        p, d = limb_anchors(dec[f"upper_arm_{s}"][0], "radial")
        anchors[f"shoulder_{s}"], anchors[f"elbowU_{s}"] = p, d
        p, d = limb_anchors(dec[f"forearm_{s}"][0], "radial")
        anchors[f"elbowF_{s}"], anchors[f"wrist_{s}"] = p, d
        p, d = limb_anchors(dec[f"thigh_{s}"][0], "z")
        anchors[f"hip_{s}"], anchors[f"knee_{s}"] = p, d
        p, d = limb_anchors(dec[f"shin_{s}"][0], "z")
        anchors[f"knee2_{s}"], anchors[f"ankle_{s}"] = p, d

    shoulder_mid = (anchors["shoulder_L"] + anchors["shoulder_R"]) / 2
    hip_mid = (anchors["hip_L"] + anchors["hip_R"]) / 2
    torso_len = float(np.linalg.norm(shoulder_mid - hip_mid))
    figure = {"model_height": float(H), "shoulder_hip": torso_len}

    limb_joint = {
        "upper_arm_L": ("shoulder_L", "elbowU_L"), "upper_arm_R": ("shoulder_R", "elbowU_R"),
        "forearm_L": ("elbowF_L", "wrist_L"), "forearm_R": ("elbowF_R", "wrist_R"),
        "thigh_L": ("hip_L", "knee_L"), "thigh_R": ("hip_R", "knee_R"),
        "shin_L": ("knee2_L", "ankle_L"), "shin_R": ("knee2_R", "ankle_R"),
    }

    parts = {}
    for key, (a_name, b_name) in limb_joint.items():
        V, F = dec[key]
        p, d = anchors[a_name], anchors[b_name]
        length = float(np.linalg.norm(d - p))
        R = _rotation_y_to(d - p).T
        local = (V - p) @ R.T / length
        radial = ARM_RADIAL if "arm" in key else LEG_RADIAL   # legs slimmer than arms
        local[:, 0] *= radial
        local[:, 2] *= radial
        parts[key] = indexed(local, F)

    R = _rotation_y_to(shoulder_mid - hip_mid).T
    V, F = dec["torso"]
    tl = (V - hip_mid) @ R.T / torso_len
    tl[:, 0] *= TORSO_RADIAL
    tl[:, 2] *= TORSO_RADIAL
    parts["torso"] = indexed(tl, F)

    V, F = dec["head"]
    hl = (V - hip_mid) @ R.T / torso_len
    pivot = np.array([hl[:, 0].mean(), hl[:, 1].min(), hl[:, 2].mean()])  # neck junction
    hl = pivot + HEAD_SCALE * (hl - pivot)       # shrink the toy head toward the neck
    parts["head"] = indexed(hl, F)

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "assets", "krunk-parts.json")
    payload = {"format": "krunk-parts-1", "figure": figure, "parts": parts}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    tri = sum(len(v["faces"]) for v in parts.values())
    vtx = sum(len(v["positions"]) for v in parts.values())
    kb = os.path.getsize(out_path) / 1024
    print(f"\nfigure: {figure}")
    print(f"exported {len(parts)} parts, {tri} tris, {vtx} verts, {kb:.0f} KB -> {out_path}")


if __name__ == "__main__":
    main()
