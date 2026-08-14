import cv2, json, os

# --- 改這裡 -----------------------------------------------------------------
SRC = r"C:\path\to\your\set_tutorial.mp4"
OUT_DIR = r"C:\Users\test\Desktop\volleyball\dataset\set"
WIN = r"C:\path\to\output\dir\set_windows.json"
# ACCEPT = 看過 set_montage.py 的把關圖後，確定是乾淨單人舉球的 window index。
# 下面這組是 2026-08-14 實際採用的（產出 usertut_set_09..18）。
# ---------------------------------------------------------------------------

wins = json.load(open(WIN))["windows"]
ACCEPT = [3, 8, 10, 11, 12, 13, 26, 28, 31, 32]  # clean single-player set demos (from montage review)
MAX_LEN = 3.5

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 29.97
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
vid_dur = n / fps

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
start_num = 9
made = []
for k, idx in enumerate(ACCEPT):
    win = wins[idx]
    s, e = win["start"], win["end"]
    dur = e - s
    if dur > MAX_LEN:
        mid = (s + e) / 2
        ts, te = mid - MAX_LEN / 2, mid + MAX_LEN / 2
    else:
        ts, te = s - 0.4, e + 0.4
    ts = max(0.0, ts)
    te = min(vid_dur, te)
    fs, fe = int(ts * fps), int(te * fps)
    name = f"usertut_set_{start_num + k:02d}.mp4"
    path = os.path.join(OUT_DIR, name)
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    cap.set(cv2.CAP_PROP_POS_FRAMES, fs)
    written = 0
    for f in range(fs, fe):
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(frame)
        written += 1
    writer.release()
    made.append((name, round(ts, 1), round(te, 1), written, win["elbow_avg"]))
    print(f"{name}  {ts:.1f}-{te:.1f}s  frames={written}  elbow~{win['elbow_avg']:.0f}")
cap.release()
print(f"\nwrote {len(made)} clips to dataset/set/")
