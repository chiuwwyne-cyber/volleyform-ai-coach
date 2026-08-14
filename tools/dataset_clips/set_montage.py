import cv2, json, os, math

# --- 改這裡 -----------------------------------------------------------------
# 讀 <OUT>/set_windows.json，輸出把關圖。**人眼在這一步剔除**：多人入鏡、比賽轉播
# 畫面、球鞋/器材特寫、教學片的錯誤示範。確認後把要留的 index 填進 set_trim.ACCEPT。
SRC = r"C:\path\to\your\set_tutorial.mp4"
OUT = r"C:\path\to\output\dir"
# ---------------------------------------------------------------------------
data = json.load(open(os.path.join(OUT, "set_windows.json")))
wins = data["windows"]

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 29.97
cell_w, cell_h = 210, 150
cols = 6
rows = math.ceil(len(wins) / cols)
montage = 255 * 0 + __import__("numpy").zeros((rows * cell_h, cols * cell_w, 3), dtype="uint8")

for i, w in enumerate(wins):
    mid = (w["start"] + w["end"]) / 2
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(mid * fps))
    ok, frame = cap.read()
    if not ok:
        continue
    frame = cv2.resize(frame, (cell_w, cell_h))
    label = f"#{i} {mid:.0f}s e{w['elbow_avg']:.0f} d{w['dur']:.1f}"
    cv2.rectangle(frame, (0, 0), (cell_w, 16), (0, 0, 0), -1)
    cv2.putText(frame, label, (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 0), 1)
    r, c = divmod(i, cols)
    montage[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = frame
cap.release()
path = os.path.join(OUT, "set_montage.jpg")
cv2.imwrite(path, montage, [cv2.IMWRITE_JPEG_QUALITY, 82])
print(f"saved {path}  ({len(wins)} windows, {rows}x{cols} grid)")
