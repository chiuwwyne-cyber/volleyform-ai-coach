"""Segment the Brave Krunk humanoid STL into articulable body parts.

The mesh is a single fused A-pose figure (Z up, ~100 tall). We classify each
triangle into a body part by anatomical region, then (later) rebase each part
between its two joint anchors so the frontend can pose it like the current
procedural capsules.

Run:
    .venv\\Scripts\\python.exe tools\\segment_krunk.py <path-to-stl>
"""

import json
import os
import struct
import sys

import fast_simplification
import numpy as np

# Each articulable part maps to a proximal->distal pair of MediaPipe pose
# landmarks; the frontend stretches/orients the part between those two points.
# "L"/"R" here are the model's -X/+X sides (mirrored to the person's sides in
# pose-3d.js). torso/hips/head use special anchors handled in the frontend.
PART_BONES = {
    "upper_arm_L": ("shoulder_L", "elbow_L"),
    "forearm_L": ("elbow_L", "wrist_L"),
    "upper_arm_R": ("shoulder_R", "elbow_R"),
    "forearm_R": ("elbow_R", "wrist_R"),
    "thigh_L": ("hip_L", "knee_L"),
    "shin_L": ("knee_L", "ankle_L"),
    "thigh_R": ("hip_R", "knee_R"),
    "shin_R": ("knee_R", "ankle_R"),
}


def load_stl(path):
    with open(path, "rb") as file:
        file.read(80)
        (ntri,) = struct.unpack("<I", file.read(4))
        tris = np.zeros((ntri, 3, 3), np.float32)
        for i in range(ntri):
            file.read(12)  # normal
            for j in range(3):
                tris[i, j] = struct.unpack("<fff", file.read(12))
            file.read(2)  # attribute
    return tris


# Anatomy landmarks in the model's own coordinates, measured from the mesh.
CENTER_X = 2.0
CENTER_Y = -9.0
HEAD_Z = 80.0        # head sphere sits above this
SHOULDER_Z = 74.0    # arms leave the torso around here
ARM_MIN_Z = 44.0     # arms reach down to about here in the A-pose
HIP_Z = 46.0         # top of the shorts / pelvis
LEG_TOP_Z = 42.0     # thighs start below the hip block
ARM_RADIUS = 11.0    # beyond this radius (in XY) at arm height = an arm


def classify(tris):
    cen = tris.mean(1)
    x, y, z = cen[:, 0], cen[:, 1], cen[:, 2]
    r = np.hypot(x - CENTER_X, y - CENTER_Y)
    side_left = x < CENTER_X  # model's -X side

    labels = np.full(len(tris), "torso", dtype=object)

    is_head = z >= HEAD_Z
    is_arm = (~is_head) & (z >= ARM_MIN_Z) & (z < HEAD_Z) & (r >= ARM_RADIUS)
    is_hip = (~is_head) & (~is_arm) & (z >= LEG_TOP_Z) & (z < HIP_Z)
    is_leg = (~is_head) & (~is_arm) & (z < LEG_TOP_Z)

    labels[is_head] = "head"
    labels[is_arm & side_left] = "arm_L"
    labels[is_arm & ~side_left] = "arm_R"
    labels[is_hip] = "hips"
    labels[is_leg & side_left] = "leg_L"
    labels[is_leg & ~side_left] = "leg_R"
    return labels


def _split_limb(tris, mask, low_name, high_name, labels, prox_hint=None, debug=""):
    """Split a limb's triangles into two along the limb's own long axis.

    high_name is the proximal (nearer the body) half, low_name the distal half.
    prox_hint gives the anatomical body-attachment point (shoulder / hip); the
    proximal end of the limb is the triangle nearest it, and the distal tip is
    the farthest triangle from there. Cutting the axis at the midpoint lands on
    the elbow / knee ball of these straight A-pose limbs.
    """
    idx = np.where(mask)[0]
    cen = tris[idx].mean(1)
    if prox_hint is not None:
        # Arm: proximal = nearest the shoulder, distal (hand) = farthest OUT
        # from the body centerline, not merely farthest from the shoulder.
        prox = cen[np.argmin(np.linalg.norm(cen - prox_hint, axis=1))]
        radial = np.hypot(cen[:, 0] - CENTER_X, cen[:, 1] - CENTER_Y)
        dist = cen[np.argmax(radial)]
    else:
        prox = cen[np.argmax(cen[:, 2])]
        dist = cen[np.argmax(np.linalg.norm(cen - prox, axis=1))]
    axis = dist - prox
    length = np.linalg.norm(axis)
    if length < 1e-6:
        return prox, prox, dist
    unit = axis / length
    t = (cen - prox) @ unit  # 0 at prox, length at distal
    perp = np.linalg.norm((cen - prox) - np.outer(t, unit), axis=1)  # thickness

    # Joint = thinnest cross-section in the middle 30-70% of the limb (the waist
    # between the two capsule balls). Falls back to the midpoint if flat.
    cut = length / 2
    lo, hi = 0.32 * length, 0.68 * length
    band = (t >= lo) & (t <= hi)
    if band.sum() >= 8:
        bins = np.linspace(lo, hi, 9)
        thin_t, thin_val = cut, 1e9
        for b0, b1 in zip(bins[:-1], bins[1:]):
            bm = band & (t >= b0) & (t < b1)
            if bm.sum() < 3:
                continue
            val = np.percentile(perp[bm], 75)
            if val < thin_val:
                thin_val, thin_t = val, (b0 + b1) / 2
        cut = thin_t

    for k, tt in zip(idx, t):
        labels[k] = high_name if tt < cut else low_name
    if debug:
        print(f"    {debug}: len={length:.1f} joint@{cut:.1f} "
              f"({100 * cut / length:.0f}%) prox={prox.round(1)} dist={dist.round(1)}")
    joint = prox + unit * cut  # elbow / knee position
    return prox, joint, dist


def refine(tris, labels):
    """Split arm->upper_arm/forearm and leg->thigh/shin; return joint anchors."""
    anchors = {}
    for side in ("L", "R"):
        sx = CENTER_X + (-10.0 if side == "L" else 10.0)
        shoulder_hint = np.array([sx, CENTER_Y, SHOULDER_Z])
        p, j, d = _split_limb(tris, labels == f"arm_{side}",
                              f"forearm_{side}", f"upper_arm_{side}", labels,
                              prox_hint=shoulder_hint, debug=f"arm_{side}")
        anchors[f"shoulder_{side}"] = p
        anchors[f"elbow_{side}"] = j
        anchors[f"wrist_{side}"] = d
        p, j, d = _split_limb(tris, labels == f"leg_{side}",
                              f"shin_{side}", f"thigh_{side}", labels,
                              debug=f"leg_{side}")
        anchors[f"hip_{side}"] = p
        anchors[f"knee_{side}"] = j
        anchors[f"ankle_{side}"] = d
    return anchors


PART_COLORS = {
    "head": (90, 200, 250),
    "torso": (200, 200, 200),
    "hips": (150, 150, 150),
    "upper_arm_L": (60, 180, 90), "forearm_L": (140, 240, 160),
    "upper_arm_R": (230, 160, 40), "forearm_R": (250, 220, 130),
    "thigh_L": (220, 80, 80), "shin_L": (250, 160, 160),
    "thigh_R": (140, 90, 220), "shin_R": (200, 160, 250),
}


def render_labeled(tris, labels, fname, proj="front"):
    import cv2

    verts = tris.reshape(-1, 3)
    minb, maxb = verts.min(0), verts.max(0)
    ctr = (minb + maxb) / 2
    size = (maxb - minb).max()
    H = W = 600
    img = np.full((H, W, 3), 245, np.uint8)
    P = tris - ctr
    if proj == "front":
        u, v, d = P[:, :, 0], P[:, :, 2], P[:, :, 1]
    else:
        u, v, d = P[:, :, 1], P[:, :, 2], -P[:, :, 0]
    order = np.argsort(d.mean(1))
    scale = (H - 80) / size
    for idx in order:
        col = PART_COLORS.get(labels[idx], (0, 0, 0))
        px = (u[idx] * scale + W / 2).astype(np.int32)
        py = (-v[idx] * scale + H / 2).astype(np.int32)
        cv2.fillConvexPoly(img, np.stack([px, py], 1), col[::-1])  # BGR
    cv2.imwrite(fname, img)


def _rotate_about(points, pivot, axis, angle_deg):
    a = np.radians(angle_deg)
    axis = axis / (np.linalg.norm(axis) + 1e-9)
    p = points - pivot
    cos_a, sin_a = np.cos(a), np.sin(a)
    dot = p @ axis
    cross = np.cross(np.broadcast_to(axis, p.shape), p)
    rotated = p * cos_a + cross * sin_a + np.outer(dot, axis) * (1 - cos_a)
    return rotated + pivot


def render_bent(tris, labels, anchors, fname):
    """Bend both elbows and one knee to check the joint balls hide the seams."""
    import cv2

    bent = tris.copy()
    side_axis = np.array([1.0, 0.0, 0.0])  # bending axis (left-right)
    # Bend forearms up at the elbow (~90 deg), like an attack arm cocking.
    for side, ang in (("L", 90), ("R", 70)):
        m = labels == f"forearm_{side}"
        bent[m] = _rotate_about(bent[m].reshape(-1, 3), anchors[f"elbow_{side}"],
                                side_axis, ang).reshape(-1, 3, 3)
    # Bend one shin back at the knee (~55 deg) like a jump load.
    for side, ang in (("L", 55),):
        m = labels == f"shin_{side}"
        bent[m] = _rotate_about(bent[m].reshape(-1, 3), anchors[f"knee_{side}"],
                                np.array([1.0, 0.0, 0.0]), ang).reshape(-1, 3, 3)

    verts = bent.reshape(-1, 3)
    minb, maxb = verts.min(0), verts.max(0)
    ctr = (minb + maxb) / 2
    size = (maxb - minb).max()
    H = W = 620
    img = np.full((H, W, 3), 245, np.uint8)
    P = bent - ctr
    u, v, d = P[:, :, 1], P[:, :, 2], -P[:, :, 0]  # side view shows the bends
    order = np.argsort(d.mean(1))
    scale = (H - 90) / size
    for idx in order:
        col = PART_COLORS.get(labels[idx], (0, 0, 0))
        px = (u[idx] * scale + W / 2).astype(np.int32)
        py = (-v[idx] * scale + H / 2).astype(np.int32)
        cv2.fillConvexPoly(img, np.stack([px, py], 1), col[::-1])
    cv2.imwrite(fname, img)


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


def _weld(part_tris):
    """Triangle soup (N,3,3) -> indexed (vertices, faces), dropping degenerates."""
    verts = part_tris.reshape(-1, 3)
    uniq, inv = np.unique(np.round(verts, 4), axis=0, return_inverse=True)
    faces = inv.reshape(-1, 3)
    good = (
        (faces[:, 0] != faces[:, 1])
        & (faces[:, 1] != faces[:, 2])
        & (faces[:, 0] != faces[:, 2])
    )
    return uniq.astype(np.float64), faces[good].astype(np.int32)


def _decimate_model_tris(part_tris, reduction):
    """Quadric edge-collapse decimation via fast_simplification.

    Hand-rolled grid methods (corner-snap, vertex clustering, lofting) all left
    surface artifacts on this dense, irregular STL — hollows, shoulder hairs, a
    torn hip seam. A real quadric decimator collapses edges by geometric error,
    so it keeps a clean watertight surface at a fraction of the triangles.
    `reduction` is the fraction of faces to remove (0.85 -> keep ~15%).
    """
    verts, faces = _weld(part_tris)
    if len(faces) < 60:
        return part_tris
    out_v, out_f = fast_simplification.simplify(
        verts, faces, target_reduction=reduction
    )
    if len(out_f) == 0:
        return part_tris
    return out_v[out_f].astype(np.float32)  # back to triangle soup


def _index_geometry(part_tris):
    """Dedup vertices -> (positions[list], faces[list])."""
    verts = part_tris.reshape(-1, 3).astype(np.float64)
    keys = {}
    positions = []
    faces = []
    for f in range(len(part_tris)):
        tri_idx = []
        for k in range(3):
            v = verts[f * 3 + k]
            key = (round(v[0], 4), round(v[1], 4), round(v[2], 4))
            if key not in keys:
                keys[key] = len(positions)
                positions.append([float(v[0]), float(v[1]), float(v[2])])
            tri_idx.append(keys[key])
        if tri_idx[0] == tri_idx[1] or tri_idx[1] == tri_idx[2] or tri_idx[0] == tri_idx[2]:
            continue  # drop degenerate triangle created by grid merge
        faces.append(tri_idx)
    return positions, faces


def _drop_radial_spikes(local_tris):
    """Drop triangles that spike radially off a limb/torso's Y axis.

    After rebasing, a clean part is a slim tube around +Y (radius well under
    ~0.6 bone-lengths). Vertex clustering can occasionally stitch a face across
    two distant cells, throwing a vertex far out sideways as a thin feather.
    Reject any triangle whose radial (XZ) distance is a clear outlier.
    """
    if len(local_tris) == 0:
        return local_tris
    radial = np.hypot(local_tris[:, :, 0], local_tris[:, :, 2])
    # Even a bulky calf stays under ~0.7; spikes shoot past 1.0. A high per-part
    # median must not lift the cutoff above the spikes, so cap it.
    threshold = min(0.8, max(0.6, 2.0 * float(np.median(radial))))
    keep = radial.max(axis=1) <= threshold
    return local_tris[keep] if keep.any() else local_tris


def export_parts(tris, labels, anchors, out_path, reduction=0.85):
    parts = {}
    # Overall figure scale so the frontend can size the mannequin to the pose.
    hip_mid = (anchors["hip_L"] + anchors["hip_R"]) / 2
    shoulder_mid = (anchors["shoulder_L"] + anchors["shoulder_R"]) / 2
    figure = {"model_height": 100.0, "shoulder_hip": float(np.linalg.norm(shoulder_mid - hip_mid))}

    for part, (a_name, b_name) in PART_BONES.items():
        # The frontend draws the hand/fingers as capsules and skips the STL
        # forearm (a featureless ball), so exporting it just bloats the asset.
        if part in ("forearm_L", "forearm_R"):
            continue
        mask = labels == part
        if mask.sum() == 0:
            continue
        p = anchors[a_name]
        d = anchors[b_name]
        length = float(np.linalg.norm(d - p))
        model = _decimate_model_tris(tris[mask], reduction)
        R = _rotation_y_to(d - p).T  # world->local: align bone dir to +Y
        local = (model - p) @ R.T / length  # proximal at 0, distal at Y=1
        local = _drop_radial_spikes(local)
        positions, faces = _index_geometry(local.astype(np.float32))
        parts[part] = {"positions": positions, "faces": faces}

    # Trunk + head: rebased around the torso axis (shoulder_mid->hip_mid). The
    # torso and hips are decimated together as one mesh so there is no seam or
    # gap at the waist; the head is a ball offset off that axis.
    torso_len = max(figure["shoulder_hip"], 1e-6)
    R = _rotation_y_to(shoulder_mid - hip_mid).T
    trunk_mask = (labels == "torso") | (labels == "hips")
    if trunk_mask.any():
        # Keep the trunk at full STL resolution: it is already low-poly (~1k
        # faces) and its open rims (waist/armpits) fold into a visible crease if
        # decimated at all, so leave it untouched.
        model = tris[trunk_mask]
        local = (model - hip_mid) @ R.T / torso_len
        local = _drop_radial_spikes(local)
        positions, faces = _index_geometry(local.astype(np.float32))
        parts["torso"] = {"positions": positions, "faces": faces}
    head_mask = labels == "head"
    if head_mask.any():
        model = _decimate_model_tris(tris[head_mask], reduction)
        local = (model - hip_mid) @ R.T / torso_len
        positions, faces = _index_geometry(local.astype(np.float32))
        parts["head"] = {"positions": positions, "faces": faces}

    payload = {"format": "krunk-parts-1", "figure": figure, "parts": parts}
    with open(out_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, separators=(",", ":"))
    total_tri = sum(len(v["faces"]) for v in parts.values())
    total_vtx = sum(len(v["positions"]) for v in parts.values())
    size_kb = os.path.getsize(out_path) / 1024
    print(f"exported {len(parts)} parts, {total_tri} tris, {total_vtx} verts, {size_kb:.0f} KB -> {out_path}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\test\Downloads\Brave Krunk.stl"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    tris = load_stl(path)
    labels = classify(tris)
    anchors = refine(tris, labels)
    counts = {}
    for lab in labels:
        counts[lab] = counts.get(lab, 0) + 1
    print("triangle counts per part:")
    for k in sorted(counts):
        print(f"  {k:12s} {counts[k]}")
    try:
        render_labeled(tris, labels, f"{out_dir}/krunk_seg_front.png", "front")
        render_labeled(tris, labels, f"{out_dir}/krunk_seg_side.png", "side")
        render_bent(tris, labels, anchors, f"{out_dir}/krunk_bent.png")
        print("rendered", out_dir)
    except ImportError:
        print("(skipping debug renders: cv2 not installed)")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    export_parts(tris, labels, anchors, os.path.join(root, "frontend", "assets", "krunk-parts.json"))


if __name__ == "__main__":
    main()
