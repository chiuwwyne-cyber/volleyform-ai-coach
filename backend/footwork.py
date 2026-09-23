"""Descriptive approach-step count from the pose landmark time-series.

This is DESCRIPTIVE, not a judgment. There is no reference dataset for "correct"
footwork, so this never flags an error -- it only reports how many foot-contacts
precede takeoff, so a player can see their own approach rhythm. A parallel
implementation in frontend/local-analyzer.js must stay in numeric lockstep with
this one (frontend/footwork_parity_fixture.json pins both).

A foot contact is a local MAXIMUM of an ankle's image-y (foot planted lowest in
the frame) with enough prominence, inside the window before takeoff (the highest
wrist). It is reliable only when the sampling in that window is dense enough --
the browser samples the whole clip sparsely, so on a long clip or in phone mode
the window can hold too few frames to resolve steps, and we say so rather than
guess.
"""

L_ANKLE, R_ANKLE = 27, 28
L_HIP, R_HIP, L_SH, R_SH = 23, 24, 11, 12
L_WRIST, R_WRIST = 15, 16

APPROACH_WINDOW_S = 1.4      # look this far back from takeoff for approach steps
MERGE_S = 0.12              # contacts closer than this are the same plant
MIN_PROMINENCE = 0.06       # of torso length; below this is landmark jitter
NEIGHBORHOOD = 3            # samples each side for the prominence baseline
MIN_WINDOW_SAMPLES = 8      # fewer than this in-window -> sampling too sparse


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return None
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def sample_from_landmarks(landmarks, time_seconds):
    """Build one {t, la, ra, wr, torso} sample from image landmarks, or None."""
    if not landmarks or len(landmarks) <= R_ANKLE or time_seconds is None:
        return None

    def y(index):
        return float(landmarks[index].y)

    def vis(index):
        return float(getattr(landmarks[index], "visibility", 1.0))

    la = y(L_ANKLE) if vis(L_ANKLE) >= 0.4 and y(L_ANKLE) < 0.99 else None
    ra = y(R_ANKLE) if vis(R_ANKLE) >= 0.4 and y(R_ANKLE) < 0.99 else None
    hip = (y(L_HIP) + y(R_HIP)) / 2.0
    shoulder = (y(L_SH) + y(R_SH)) / 2.0
    torso = abs(hip - shoulder)
    wrist = min(y(L_WRIST), y(R_WRIST))
    return {"t": float(time_seconds), "la": la, "ra": ra, "wr": wrist, "torso": torso}


def _contacts(window, key, torso_med):
    pts = [(s["t"], s[key]) for s in window if s.get(key) is not None]
    if len(pts) < 3 or not torso_med:
        return []
    ys = [p[1] for p in pts]
    peaks = []
    for i in range(1, len(pts) - 1):
        if ys[i] > ys[i - 1] and ys[i] >= ys[i + 1]:
            lo = max(0, i - NEIGHBORHOOD)
            hi = min(len(ys), i + NEIGHBORHOOD + 1)
            prominence = (ys[i] - min(ys[lo:hi])) / torso_med
            if prominence >= MIN_PROMINENCE:
                peaks.append(pts[i][0])
    merged = []
    for t in peaks:
        if merged and (t - merged[-1]) < MERGE_S:
            continue
        merged.append(t)
    return merged


def count_approach_steps(samples):
    """samples: list of {t, la, ra, wr, torso}. Returns a descriptive dict."""
    valid = [s for s in samples if s and s.get("wr") is not None]
    if len(valid) < 3:
        return {"available": False, "reason": "no_pose", "steps": None,
                "left": None, "right": None, "reliable": False}

    takeoff = min(valid, key=lambda s: s["wr"])
    t0 = takeoff["t"]
    window = [s for s in samples if s and (t0 - APPROACH_WINDOW_S) <= s["t"] <= (t0 + 0.05)]
    torsos = [s["torso"] for s in window if s.get("torso")]
    torso_med = _median(torsos) or 0.15

    left = _contacts(window, "la", torso_med)
    right = _contacts(window, "ra", torso_med)
    steps = len(left) + len(right)
    reliable = len(window) >= MIN_WINDOW_SAMPLES

    span = max(0.0, t0 - (window[0]["t"] if window else t0))
    cadence = round(steps / span, 2) if span > 0.2 and reliable else None
    return {
        "available": True,
        "steps": steps,
        "left": len(left),
        "right": len(right),
        "cadence_per_s": cadence,
        "takeoff_time": round(t0, 2),
        "window_seconds": round(span, 2),
        "samples_in_window": len(window),
        "reliable": reliable,
    }
