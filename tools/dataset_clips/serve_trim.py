import cv2, os

SAFE = r"C:\Users\test\AppData\Local\Temp\claude\C--Users-test-Desktop-volleyball\8c6d2969-18a8-4aa9-a54c-72b0609096ee\scratchpad\src"
SRC = os.path.join(SAFE, "vp1.mp4")
OUT_DIR = r"C:\Users\test\Desktop\volleyball\dataset\serve"

# (start, end) chosen to sit inside one camera shot, with lead-in for the crouch
# phase and a little follow-through after contact. Verified full-body overhand
# serves only (underhand demo and leg-cropped close-ups excluded).
WINDOWS = [
    (65.5, 66.9),   # peak 66.0 (starts after the 65.3-65.4 scene cut)
    (73.9, 76.2),   # peak 75.4
    (80.6, 82.0),   # peak 81.2
    (84.9, 87.2),   # peak 86.4
    (93.2, 95.5),   # peak 94.7
]

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 25
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*"mp4v")

for i, (ts, te) in enumerate(WINDOWS, start=1):
    name = f"usertut_serve_{i:02d}.mp4"
    path = os.path.join(OUT_DIR, name)
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(ts*fps))
    n = 0
    for _ in range(int((te-ts)*fps)):
        ok, fr = cap.read()
        if not ok: break
        writer.write(fr); n += 1
    writer.release()
    print(f"{name}  {ts:.1f}-{te:.1f}s  frames={n}")
cap.release()
print(f"\nwrote {len(WINDOWS)} serve clips")
