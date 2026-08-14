import cv2, json, os, math, numpy as np

SAFE = r"C:\Users\test\AppData\Local\Temp\claude\C--Users-test-Desktop-volleyball\8c6d2969-18a8-4aa9-a54c-72b0609096ee\scratchpad\src"
OUT = r"C:\Users\test\AppData\Local\Temp\claude\C--Users-test-Desktop-volleyball\8c6d2969-18a8-4aa9-a54c-72b0609096ee\scratchpad"
SRC = os.path.join(SAFE, "vp1.mp4")
events = json.load(open(os.path.join(OUT, "vp1_events.json")))
PICK = [1, 2, 4, 6, 7, 10]

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 25
# for each pick show 3 frames: -0.6s (crouch/prep), peak, +0.3s
cols, cw, ch = 3, 320, 200
rows = len(PICK)
m = np.zeros((rows*ch, cols*cw, 3), dtype="uint8")
for r, idx in enumerate(PICK):
    e = events[idx]
    for c, dt in enumerate((-0.6, 0.0, 0.3)):
        t = max(0, e["peak_t"] + dt)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t*fps))
        ok, fr = cap.read()
        if not ok: continue
        fr = cv2.resize(fr, (cw, ch))
        cv2.rectangle(fr, (0,0), (cw,16), (0,0,0), -1)
        cv2.putText(fr, f"#{idx} {t:.1f}s ({dt:+.1f})", (3,12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0,255,0), 1)
        m[r*ch:(r+1)*ch, c*cw:(c+1)*cw] = fr
cap.release()
p = os.path.join(OUT, "vp1_bigcheck.jpg")
cv2.imwrite(p, m, [cv2.IMWRITE_JPEG_QUALITY, 88])
print("saved", p)
