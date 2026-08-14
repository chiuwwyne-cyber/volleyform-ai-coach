import cv2, math, json, os
from mediapipe import solutions

SRC = r"C:\Users\test\Downloads\videoplayback (10).mp4"
OUT = r"C:\Users\test\AppData\Local\Temp\claude\C--Users-test-Desktop-volleyball\8c6d2969-18a8-4aa9-a54c-72b0609096ee\scratchpad"
STRIDE = 8  # sample ~3.7 fps at 29.97

mp_pose = solutions.pose


def angle(a, b, c):
    # angle at b (degrees) using 2D
    v1 = (a.x - b.x, a.y - b.y)
    v2 = (c.x - b.x, c.y - b.y)
    d = math.hypot(*v1) * math.hypot(*v2)
    if d == 0:
        return 180.0
    cos = max(-1, min(1, (v1[0]*v2[0] + v1[1]*v2[1]) / d))
    return math.degrees(math.acos(cos))


cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 29.97
samples = []  # (time, set_like, gap, elbow_avg, vis)
frame_index = 0
with mp_pose.Pose(static_image_mode=False, model_complexity=0,
                  min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_index += 1
        if frame_index % STRIDE != 0:
            continue
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img.flags.writeable = False
        res = pose.process(img)
        t = frame_index / fps
        if not res.pose_landmarks:
            samples.append((round(t, 2), 0, None, None, 0))
            continue
        lm = res.pose_landmarks.landmark
        nose = lm[0]
        wl, wr = lm[15], lm[16]
        sl, sr = lm[11], lm[12]
        el, er = lm[13], lm[14]
        vis = min(wl.visibility, wr.visibility, sl.visibility, sr.visibility)
        gap = math.hypot(wl.x - wr.x, wl.y - wr.y)
        both_above_nose = max(wl.y, wr.y) < nose.y
        shoulder_y = (sl.y + sr.y) / 2
        both_above_shoulder = max(wl.y, wr.y) < shoulder_y
        elbow_avg = (angle(sl, el, wl) + angle(sr, er, wr)) / 2
        set_like = 1 if (both_above_nose and both_above_shoulder and gap < 0.22 and vis > 0.5) else 0
        samples.append((round(t, 2), set_like, round(gap, 3), round(elbow_avg, 1), round(vis, 2)))
        if frame_index % 2400 == 0:
            print(f"...{t:.0f}s scanned", flush=True)
cap.release()

# group contiguous set_like samples into windows (allow 1 gap sample)
dt = STRIDE / fps
windows = []
i = 0
cur = None
miss = 0
for s in samples:
    if s[1] == 1:
        if cur is None:
            cur = {"start": s[0], "end": s[0], "elbows": [], "gaps": []}
        cur["end"] = s[0]
        if s[3] is not None:
            cur["elbows"].append(s[3])
            cur["gaps"].append(s[2])
        miss = 0
    else:
        if cur is not None:
            miss += 1
            if miss >= 3:  # ~0.8s gap ends a window
                windows.append(cur)
                cur = None
                miss = 0
if cur is not None:
    windows.append(cur)

# keep windows with real duration and bent elbows (set = elbows bent ~ <160)
good = []
for w in windows:
    dur = w["end"] - w["start"]
    eavg = sum(w["elbows"]) / len(w["elbows"]) if w["elbows"] else 180
    gavg = sum(w["gaps"]) / len(w["gaps"]) if w["gaps"] else 1
    w["dur"] = round(dur, 2)
    w["elbow_avg"] = round(eavg, 1)
    w["gap_avg"] = round(gavg, 3)
    if dur >= 0.5 and eavg < 165:
        good.append(w)

json.dump({"fps": fps, "n_samples": len(samples), "windows": good},
          open(os.path.join(OUT, "set_windows.json"), "w"), indent=2)
print(f"\nfps={fps:.2f} samples={len(samples)} raw_windows={len(windows)} good_windows={len(good)}")
for w in good:
    print(f"  {w['start']:7.1f}-{w['end']:7.1f}s  dur={w['dur']:.1f}s  elbow~{w['elbow_avg']:.0f}deg  gap~{w['gap_avg']:.2f}")
